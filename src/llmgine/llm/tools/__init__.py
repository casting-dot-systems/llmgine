"""
Simplified tools for litellm with MCP integration support.

This module provides tool management capabilities with optional MCP
(Model Context Protocol) integration for interoperability with the
broader MCP ecosystem.
"""

from llmgine.llm.tools.llmgine_mcp_server import (
    LLMgineMCPServer,
    create_llmgine_mcp_server,
)
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.toolCall import ToolCall

__all__ = [
    "LLMgineMCPServer",
    "ToolCall",
    "ToolManager",
    "create_llmgine_mcp_server",
]
