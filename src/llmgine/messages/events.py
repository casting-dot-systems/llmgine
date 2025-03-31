"""Events used in the system.

This module defines events that can be published on the message bus.
Events represent things that have happened in the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from llmgine.messages.commands import Command, CommandResult


@dataclass
class Event:
    """Base class for all events in the system.
    
    Events represent things that have happened in the system.
    Multiple handlers can process each event.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

# @dataclass
# class LogEvent(Event):
#     """Event emitted when a log message is created."""
    
#     message: str = ""
#     level: str = "info"
#     metadata: Dict[str, Any] = field(default_factory=dict)


# @dataclass
# class CommandResult(Event):
#     """Result of a command execution."""
#     original_command: Command = field(default_factory=Command)
#     success: bool = False
#     result: Any = None
#     error: Optional[str] = None
#     execution_time_ms: Optional[float] = None


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
            "function": {
                "name": self.name,
                "arguments": self.arguments
            }
        }


@dataclass
class LLMResponse:
    """Response from an LLM, following OpenAI format for consistency."""
    
    # Main content
    content: Optional[str] = None
    role: str = "assistant"
    
    # Model information
    model: str = "unknown"
    
    # Completion information
    finish_reason: Optional[str] = None
    
    # Function/tool calling
    tool_calls: Optional[List[ToolCall]] = None
    
    # Usage statistics
    usage: Optional[Dict[str, int]] = None
    
    # Raw response for provider-specific data
    raw_response: Optional[Dict[str, Any]] = None
    
    def has_tool_calls(self) -> bool:
        """Check if the response contains tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0
    
    def extract_text(self) -> str:
        """Extract the text content from the response.
        
        Returns:
            The content string or an empty string if content is None
        """
        return self.content or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the response to a dictionary."""
        result = {
            "role": self.role,
            "model": self.model
        }
        
        if self.content:
            result["content"] = self.content
            
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
            
        if self.finish_reason:
            result["finish_reason"] = self.finish_reason
            
        if self.usage:
            result["usage"] = self.usage
            
        return result