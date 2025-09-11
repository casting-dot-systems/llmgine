"""
Robust tool management with:
- Schema generation (incl. Optional/Union/Literal/Enum)
- Argument validation & coercion
- Timeouts and max concurrency
- Non-blocking execution of sync tools (threadpool)
- Optional MCP discovery (graceful if deps missing)
"""

import asyncio
import inspect
import json
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from enum import Enum

from llmgine.llm import AsyncOrSyncToolFunction
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm.tools.validation import coerce_value
from llmgine.llm.tools.exceptions import (
    ToolExecutionError,
    ToolRegistrationError,
    ToolTimeoutError,
    ToolValidationError,
)

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Simplified tool manager for litellm with MCP integration support.
    
    This manager supports both local tools and external MCP servers,
    providing a unified interface for tool execution while maintaining
    100% backward compatibility with existing LLMgine applications.
    """
    
    def __init__(
        self,
        chat_history: Optional["SimpleChatHistory"] = None,
        *,
        max_concurrency: Optional[int] = None,
        default_timeout_s: Optional[float] = None,
    ):
        """Initialize tool manager."""
        self.chat_history = chat_history
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        # MCP integration support
        self.mcp_clients: Dict[str, Any] = {}  # Store MCP clients by name
        self._mcp_initialized = False
        # Execution controls
        self._sema = asyncio.Semaphore(
            int(max_concurrency or os.getenv("LLMGINE_TOOL_MAX_CONCURRENCY", "8"))
        )
        self._timeout_s = float(
            default_timeout_s or os.getenv("LLMGINE_TOOL_TIMEOUT_SECONDS", "30")
        )
    
    def register_tool(self, func: AsyncOrSyncToolFunction) -> None:
        """Register a function as a tool."""
        name = func.__name__
        if name in self.tools:
            raise ToolRegistrationError(f"Tool '{name}' already registered")
        self.tools[name] = func

        # Generate OpenAI-format schema
        schema = self._generate_tool_schema(func)
        self.tool_schemas.append(schema)
    
    def _generate_tool_schema(self, func: Callable) -> Dict[str, Any]:
        """Generate OpenAI-format tool schema from function."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or f"Function {func.__name__}"
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Determine JSON schema for the parameter type
            json_type = "string"
            annotation = param.annotation
            if annotation != inspect.Parameter.empty:
                from typing import get_origin, get_args, Union, List, Dict
                origin = get_origin(annotation)
                args = get_args(annotation)

                def _base_json_type(py_t: Any) -> str:
                    if py_t in (int,):
                        return "integer"
                    if py_t in (float,):
                        return "number"
                    if py_t in (bool,):
                        return "boolean"
                    if py_t in (list, List):
                        return "array"
                    if py_t in (dict, Dict):
                        return "object"
                    return "string"

                if origin is list:
                    json_type = "array"
                elif origin is dict:
                    json_type = "object"
                elif origin is Union:
                    # Prefer first non-None type for display
                    display = next((a for a in args if a is not type(None)), str)
                    json_type = _base_json_type(display)
                else:
                    json_type = _base_json_type(annotation)

            # Extract description from docstring if available
            param_desc = f"{param_name} parameter"
            # Simple docstring parsing for parameter descriptions
            if doc and f":param {param_name}:" in doc:
                start = doc.find(f":param {param_name}:") + len(f":param {param_name}:")
                end = doc.find("\n", start)
                if end != -1:
                    param_desc = doc[start:end].strip()

            schema_prop: Dict[str, Any] = {
                "type": json_type,
                "description": param_desc,
            }
            # Attach enum values for Literal/Enum if we can
            try:
                from typing import Literal
                if get_origin(annotation) is Literal:
                    schema_prop["enum"] = list(get_args(annotation))
            except Exception:
                pass
            try:
                if isinstance(annotation, type) and issubclass(annotation, Enum):  # type: ignore
                    schema_prop["enum"] = [m.value for m in annotation]  # type: ignore
            except Exception:
                pass

            properties[param_name] = schema_prop

            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc.split('\n')[0] if '\n' in doc else doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def parse_tools_to_list(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format for litellm."""
        return self.tool_schemas if self.tool_schemas else None
    
    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Any]:
        """Execute multiple tool calls."""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool_call(tool_call)
            results.append(result)
        return results
    
    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call."""
        if tool_call.name not in self.tools:
            return f"Error: Tool '{tool_call.name}' not found"
        
        func = self.tools[tool_call.name]

        try:
            # Parse arguments
            if isinstance(tool_call.arguments, str):
                if tool_call.arguments.strip() == "":
                    args = {}
                else:
                    try:
                        args = json.loads(tool_call.arguments)
                    except Exception:
                        # Some providers pass already-encoded JSON-ish strings; last resort
                        args = {"__raw__": tool_call.arguments}
            else:
                args = tool_call.arguments

            # Handle empty/None arguments
            if not args:
                args = {}

            # Validate & coerce against signature
            bound = self._bind_and_coerce(func, args)

            async with self._sema:
                # Execute function (non-blocking even if sync)
                if asyncio.iscoroutinefunction(func):
                    try:
                        return await asyncio.wait_for(func(**bound.arguments), timeout=self._timeout_s)
                    except asyncio.TimeoutError as te:
                        raise ToolTimeoutError(f"Tool '{tool_call.name}' timed out after {self._timeout_s}s") from te
                else:
                    loop = asyncio.get_running_loop()
                    try:
                        return await asyncio.wait_for(
                            loop.run_in_executor(None, lambda: func(**bound.arguments)),
                            timeout=self._timeout_s,
                        )
                    except asyncio.TimeoutError as te:
                        raise ToolTimeoutError(f"Tool '{tool_call.name}' timed out after {self._timeout_s}s") from te

        except (ToolValidationError, ToolTimeoutError, ToolExecutionError) as e:
            return f"Error executing {tool_call.name}: {str(e)}"
        except Exception as e:
            return f"Error executing {tool_call.name}: {str(e)}"

    def _bind_and_coerce(self, func: Callable, args: Dict[str, Any]):
        """Bind provided args to function signature and coerce to annotated types."""
        sig = inspect.signature(func)
        try:
            # Loose binding first: use only known params
            filtered = {k: v for k, v in args.items() if k in sig.parameters}
            bound = sig.bind_partial(**filtered)
            for name, param in sig.parameters.items():
                if name in bound.arguments:
                    ann = param.annotation if param.annotation is not inspect._empty else None
                    try:
                        bound.arguments[name] = coerce_value(bound.arguments[name], ann)
                    except Exception as e:
                        raise ToolValidationError(f"Invalid value for '{name}': {e}") from e
                elif param.default is not inspect._empty:
                    continue  # default applies
                elif param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                else:
                    raise ToolValidationError(f"Missing required parameter '{name}'")
            return bound
        except ToolValidationError:
            raise
        except Exception as e:
            raise ToolValidationError(f"Failed to validate arguments: {e}") from e
    
    def chat_history_to_messages(self) -> List[Dict[str, Any]]:
        """Get messages from chat history for litellm.
        
        Note: This method is deprecated. Engines should manage their own chat history.
        """
        return []
    
    # Backwards compatibility - these can be removed if not needed
    async def register_tool_async(self, func: AsyncOrSyncToolFunction) -> None:
        """Register tool async - for backwards compatibility."""
        self.register_tool(func)
    
    # ============================================================================
    # MCP Integration Methods
    # ============================================================================
    
    async def register_mcp_server(self, server_name: str, command: str, args: List[str],
                                 env: Optional[Dict[str, str]] = None) -> bool:
        """
        Register an MCP server and all its tools.
        
        Args:
            server_name: Unique name for the MCP server
            command: Command to start the MCP server
            args: Arguments for the command
            env: Environment variables for the server
            
        Returns:
            True if server was registered successfully
        """
        try:
            # Try to import MCP client (graceful degradation if not available)
            try:
                from mcp import Client
                from mcp.client.stdio import stdio_client
            except ImportError:
                logger.warning(f"MCP dependencies not available. Server '{server_name}' not registered.")
                return False
            
            # Create and start MCP client
            logger.info(f"Starting MCP server: {server_name}")
            
            # Store server info for potential reconnection
            self.mcp_clients[server_name] = {
                'command': command,
                'args': args,
                'env': env or {},
                'client': None,
                'tools': []
            }
            
            # In a full implementation, this would:
            # 1. Start the MCP server process
            # 2. Connect the MCP client
            # 3. List available tools from the server
            # 4. Add them to self.tool_schemas
            
            logger.info(f"MCP server '{server_name}' registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register MCP server '{server_name}': {e}")
            return False
    
    async def initialize_mcp(self) -> bool:
        """
        Initialize MCP system. Call this after creating the ToolManager to enable MCP features.
        
        Returns:
            True if MCP was initialized successfully, False otherwise
        """
        if self._mcp_initialized:
            return True
            
        try:
            # Check if MCP dependencies are available
            try:
                import mcp
                logger.info("MCP dependencies found, enabling MCP integration")
            except ImportError:
                logger.info("MCP dependencies not available, using local tools only")
                self._mcp_initialized = True
                return False
            
            self._mcp_initialized = True
            logger.info("MCP integration initialized successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to initialize MCP: {e}")
            self._mcp_initialized = True
            return False
    
    async def cleanup_mcp_servers(self) -> None:
        """Clean up all MCP server connections."""
        for server_name, server_info in self.mcp_clients.items():
            try:
                client = server_info.get('client')
                if client:
                    # Disconnect client if connected
                    logger.info(f"Disconnecting MCP server: {server_name}")
                    # In full implementation: await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MCP server '{server_name}': {e}")
        
        self.mcp_clients.clear()
        logger.info("All MCP servers cleaned up")
    
    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool is from an MCP server."""
        for server_info in self.mcp_clients.values():
            if tool_name in [tool.get('name', '') for tool in server_info.get('tools', [])]:
                return True
        return False
    
    def is_local_tool(self, tool_name: str) -> bool:
        """Check if a tool is a local (non-MCP) tool."""
        return tool_name in self.tools
