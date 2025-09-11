"""
LLM-types placeholder (framework no longer owns LLM logic).

Keep minimal shared type aliases used by bus/messages/tools so the rest of the
framework (message bus, observability, tools/MCP) remains stable. Engines
should directly use third-party frameworks (e.g., litellm, pydantic-ai).
"""

import asyncio
from typing import Any, Callable, Dict, List, Literal, NewType, Union

# Type definitions for tool functions
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]
AsyncOrSyncToolFunction = Union[ToolFunction, AsyncToolFunction]

# Type definitions for LLM-related data structures
ModelFormattedDictTool = NewType("ModelFormattedDictTool", dict[str, Any])
ContextType = NewType("ContextType", List[Dict[str, Any]])
ModelNameStr = NewType("ModelNameStr", str)
SessionID = NewType("SessionID", str)
LLMConversation = NewType("LLMConversation", List[Dict[str, Any]])

# Tool choice types
ToolChoiceType = Literal["auto", "none", "required"]
ToolChoiceOrDictType = Union[ToolChoiceType, Dict[str, Any]]
