from typing import Any, Dict
from pydantic import BaseModel

class ToolCall(BaseModel):
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
