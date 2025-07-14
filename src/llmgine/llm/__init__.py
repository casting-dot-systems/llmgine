import asyncio
from typing import Any, Callable, Dict, List, NewType, Union, Literal

# TODO use _type


# Type for tool function
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]
AsyncOrSyncToolFunction = Union[ToolFunction, AsyncToolFunction]


ModelFormattedDictTool = NewType("ModelFormattedDictTool", dict[str, Any])
ContextType = NewType("ContextType", List[Dict[str, Any]])

ModelNameStr = NewType("ModelNameStr", str)

# TODO There is not way this is the right place to put this>
SessionID = NewType("SessionID", str)
EngineID = NewType("EngineID", str)

LLMConversation = NewType("LLMConversation", List[Dict[str, Any]])

ToolChoiceType = Literal[
    "auto", "none", "required"
]  # TODO an enum would be better, otherwise "none" will have lots of search collisions
ToolChoiceOrDictType = Union[
    ToolChoiceType, Dict[str, Any]
]  # TODO this Dict[str, Any] might be ModelFormattedDictTool? # TODO could rename
