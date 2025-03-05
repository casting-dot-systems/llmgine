from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid
from datetime import datetime


@dataclass
class Event:
    """Base class for all events in the system"""

    event_type: str
    data: Any
    event_id: str = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# System events
class SystemEvent(Event):
    """Base class for system events"""

    def __init__(self, event_type: str, data: Any):
        super().__init__(f"system.{event_type}", data)


class SystemStartedEvent(SystemEvent):
    """Event emitted when the system starts"""

    def __init__(self, version: str, config: Dict[str, Any]):
        super().__init__("started", {"version": version, "config": config})


class SystemShutdownEvent(SystemEvent):
    """Event emitted when the system is shutting down"""

    def __init__(self, reason: Optional[str] = None):
        super().__init__("shutdown", {"reason": reason})


# LLM events
class LLMEvent(Event):
    """Base class for LLM-related events"""

    def __init__(self, event_type: str, data: Any):
        super().__init__(f"llm.{event_type}", data)


class LLMRequestEvent(LLMEvent):
    """Event emitted when a request is sent to an LLM"""

    def __init__(
        self, request_id: str, prompt: str, model: str, parameters: Dict[str, Any]
    ):
        super().__init__(
            "request",
            {
                "request_id": request_id,
                "prompt": prompt,
                "model": model,
                "parameters": parameters,
            },
        )


class LLMResponseEvent(LLMEvent):
    """Event emitted when a response is received from an LLM"""

    def __init__(
        self, request_id: str, response: str, model: str, metrics: Dict[str, Any]
    ):
        super().__init__(
            "response",
            {
                "request_id": request_id,
                "response": response,
                "model": model,
                "metrics": metrics,
            },
        )


# Tool events
class ToolEvent(Event):
    """Base class for tool-related events"""

    def __init__(self, event_type: str, data: Any):
        super().__init__(f"tool.{event_type}", data)


class ToolExecutionEvent(ToolEvent):
    """Event emitted when a tool is executed"""

    def __init__(self, tool_name: str, input_data: Any, execution_id: str):
        super().__init__(
            "execution",
            {
                "tool_name": tool_name,
                "input_data": input_data,
                "execution_id": execution_id,
            },
        )


class ToolResultEvent(ToolEvent):
    """Event emitted when a tool execution completes"""

    def __init__(
        self,
        execution_id: str,
        tool_name: str,
        result: Any,
        error: Optional[str] = None,
    ):
        super().__init__(
            "result",
            {
                "execution_id": execution_id,
                "tool_name": tool_name,
                "result": result,
                "error": error,
            },
        )


# User interface events
class UIEvent(Event):
    """Base class for user interface events"""

    def __init__(self, event_type: str, data: Any):
        super().__init__(f"ui.{event_type}", data)


class UserInputEvent(UIEvent):
    """Event emitted when user input is received"""

    def __init__(
        self, input_text: str, input_id: str, metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            "input",
            {
                "input_text": input_text,
                "input_id": input_id,
                "metadata": metadata or {},
            },
        )


class DisplayUpdateEvent(UIEvent):
    """Event emitted when the display needs to be updated"""

    def __init__(self, content: Any, update_id: str, update_type: str):
        super().__init__(
            "display_update",
            {"content": content, "update_id": update_id, "update_type": update_type},
        )
