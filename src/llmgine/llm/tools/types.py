import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, Union

# Type for tool function
ToolFunction = Callable[..., Any]
AsyncToolFunction = Callable[..., "asyncio.Future[Any]"]
AsyncOrSyncToolFunction = Union[ToolFunction, AsyncToolFunction]


# TODO this is a class not really a type probably put into seperate file


@dataclass
class ToolCall:
    """Represents a tool call from an LLM."""

    id: str
    type: str = "function"
    name: str = ""
    arguments: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool call to dictionary format."""
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.name, "arguments": self.arguments},
        }
