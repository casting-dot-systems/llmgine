"""
Simplified tools for litellm with MCP integration support.

This module provides tool management capabilities with optional MCP
(Model Context Protocol) integration for interoperability with the
broader MCP ecosystem.
"""

from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm.tools.llmgine_mcp_server import LLMgineMCPServer, create_llmgine_mcp_server

__all__ = [
    "ToolCall",
    "ToolManager",
    "LLMgineMCPServer", 
    "create_llmgine_mcp_server",
]