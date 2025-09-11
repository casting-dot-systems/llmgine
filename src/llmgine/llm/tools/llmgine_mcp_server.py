"""
LLMgine MCP Server - Exposes LLMgine tools through MCP protocol.

This server allows any-mcp clients to access LLMgine tools through the standard MCP interface,
enabling integration with the broader MCP ecosystem while preserving LLMgine's tool capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.toolCall import ToolCall

logger = logging.getLogger(__name__)


class LLMgineMCPServer:
    """
    MCP Server that exposes LLMgine tools through the Model Context Protocol.
    
    This server acts as a bridge between LLMgine's tool system and any-mcp clients,
    allowing LLMgine tools to be used by any MCP-compatible system.
    """
    
    def __init__(self, tool_manager: Optional[ToolManager] = None):
        """
        Initialize the LLMgine MCP server.
        
        Args:
            tool_manager: Optional existing ToolManager instance. If None, creates a new one.
        """
        self.tool_manager = tool_manager or ToolManager()
        self._server = None
        self._initialized = False
    
    def register_llmgine_tool(self, func) -> None:
        """
        Register a LLMgine tool with the MCP server.
        
        Args:
            func: Function to register as a tool
        """
        self.tool_manager.register_tool(func)
        logger.info(f"Registered LLMgine tool: {func.__name__}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available LLMgine tools in MCP format.
        
        Returns:
            List of tool descriptions compatible with MCP protocol
        """
        tools = []
        schemas = self.tool_manager.parse_tools_to_list() or []
        
        for schema in schemas:
            if "function" in schema:
                func_info = schema["function"]
                # Convert LLMgine tool schema to MCP format
                mcp_tool = {
                    "name": func_info["name"],
                    "description": func_info.get("description", ""),
                    "inputSchema": func_info.get("parameters", {})
                }
                tools.append(mcp_tool)
        
        logger.debug(f"Listed {len(tools)} LLMgine tools for MCP")
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a LLMgine tool via MCP protocol.
        
        Args:
            name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result in MCP format
        """
        try:
            # Create a ToolCall object for LLMgine compatibility
            tool_call = ToolCall(
                id="mcp-tool-call",
                name=name,
                arguments=arguments
            )
            
            # Execute the tool using LLMgine's tool manager
            result = await self.tool_manager.execute_tool_call(tool_call)
            
            # Format result for MCP
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result) if result is not None else "Tool executed successfully"
                    }
                ]
            }
            
        except Exception as e:
            error_msg = f"Error executing tool {name}: {e!s}"
            logger.error(error_msg)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": error_msg
                    }
                ],
                "isError": True
            }
    
    async def initialize(self) -> bool:
        """
        Initialize the MCP server.
        
        Returns:
            True if initialization was successful
        """
        if self._initialized:
            return True
        
        try:
            # Initialize the underlying tool manager if it has MCP capabilities
            if hasattr(self.tool_manager, 'initialize_mcp'):
                await self.tool_manager.initialize_mcp()
            
            self._initialized = True
            logger.info("LLMgine MCP server initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLMgine MCP server: {e}")
            return False
    
    async def run_stdio(self):
        """
        Run the MCP server with stdio transport.
        
        This method would typically be called by any-mcp to start the server.
        In a full implementation, this would handle the MCP protocol communication.
        """
        try:
            # Try to import MCP server dependencies
            try:
                from mcp.server import Server
                from mcp.server.stdio import stdio_server
                from mcp.types import TextContent, Tool
            except ImportError:
                logger.error("MCP server dependencies not available")
                return
            
            # Create MCP server instance
            server = Server("llmgine-tools")
            
            @server.list_tools()
            async def handle_list_tools() -> List[Tool]:
                tools = await self.list_tools()
                return [
                    Tool(
                        name=tool["name"],
                        description=tool["description"],
                        inputSchema=tool["inputSchema"]
                    )
                    for tool in tools
                ]
            
            @server.call_tool()
            async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
                result = await self.call_tool(name, arguments)
                content = result.get("content", [])
                return [
                    TextContent(type="text", text=item["text"])
                    for item in content
                    if item.get("type") == "text"
                ]
            
            # Run the server
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream)
                
        except Exception as e:
            logger.error(f"Error running LLMgine MCP server: {e}")
    
    async def cleanup(self):
        """Clean up server resources."""
        try:
            if hasattr(self.tool_manager, 'cleanup_mcp_servers'):
                await self.tool_manager.cleanup_mcp_servers()
            
            self._initialized = False
            logger.info("LLMgine MCP server cleaned up")
            
        except Exception as e:
            logger.error(f"Error during LLMgine MCP server cleanup: {e}")


def create_llmgine_mcp_server(tools: Optional[List] = None) -> LLMgineMCPServer:
    """
    Factory function to create and configure a LLMgine MCP server.
    
    Args:
        tools: Optional list of tools to register with the server
        
    Returns:
        Configured LLMgineMCPServer instance
    """
    server = LLMgineMCPServer()
    
    # Register provided tools
    if tools:
        for tool in tools:
            server.register_llmgine_tool(tool)
    
    return server


async def main():
    """
    Main entry point for running the LLMgine MCP server standalone.
    
    This allows the server to be run directly as an MCP server process.
    """
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create server with basic setup
    server = create_llmgine_mcp_server()
    await server.initialize()
    
    try:
        logger.info("Starting LLMgine MCP server...")
        await server.run_stdio()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
