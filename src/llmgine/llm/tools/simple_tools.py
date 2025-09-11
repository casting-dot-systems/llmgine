"""
Simplified tool management for litellm.
Handles tool registration, conversion to OpenAI format, and execution.
"""

import asyncio
import inspect
import json
from typing import Any, Callable, Dict, List

from llmgine.llm.tools.toolCall import ToolCall


class SimpleToolManager:
    """Simple tool manager that works directly with litellm."""
    
    def __init__(self):
        """Initialize empty tool registry."""
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
    
    def register_tool(self, func: Callable) -> None:
        """
        Register a function as a tool.
        Automatically generates OpenAI-format schema from function signature.
        """
        name = func.__name__
        self.tools[name] = func
        
        # Generate schema from function signature
        schema = self._generate_tool_schema(func)
        self.tool_schemas.append(schema)
    
    def _generate_tool_schema(self, func: Callable) -> Dict[str, Any]:
        """Generate OpenAI-format tool schema from function signature."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or f"Function {func.__name__}"
        
        # Parse parameters
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Get type hint
            param_type = "string"  # default
            if param.annotation != inspect.Parameter.empty:
                type_hint = param.annotation
                if type_hint == int:
                    param_type = "integer"
                elif type_hint == float:
                    param_type = "number"
                elif type_hint == bool:
                    param_type = "boolean"
                elif type_hint == list or type_hint == List:
                    param_type = "array"
                elif type_hint == dict or type_hint == Dict:
                    param_type = "object"
            
            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }
            
            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        # Return OpenAI format
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in OpenAI format for litellm."""
        return self.tool_schemas
    
    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call."""
        if tool_call.name not in self.tools:
            return f"Error: Tool '{tool_call.name}' not found"
        
        func = self.tools[tool_call.name]
        
        try:
            # Parse arguments
            if isinstance(tool_call.arguments, str):
                args = json.loads(tool_call.arguments)
            else:
                args = tool_call.arguments
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = func(**args)
            
            return str(result)
        except Exception as e:
            return f"Error executing {tool_call.name}: {e!s}"
    
    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[str]:
        """Execute multiple tool calls."""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool_call(tool_call)
            results.append(result)
        return results


def tool(func: Callable) -> Callable:
    """
    Decorator to mark a function as a tool.
    This is optional - functions can be registered directly.
    """
    func._is_tool = True
    return func


def register_tools_from_module(manager: SimpleToolManager, module: Any) -> None:
    """
    Register all functions marked with @tool decorator from a module.
    """
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, '_is_tool'):
            manager.register_tool(obj)
