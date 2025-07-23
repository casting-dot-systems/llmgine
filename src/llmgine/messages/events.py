"""Events used in the system.

This module defines events that can be published on the message bus.
Events represent things that have happened in the system.
"""

import inspect
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from types import FrameType
from typing import Any, Dict, Optional, override

from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult


@dataclass
class Event:
    """Base class for all events in the system.

    Events represent things that have happened in the system.
    Multiple handlers can process each event.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: SessionID = field(default_factory=lambda: SessionID("BUS"))

    def __post_init__(self) -> None:
        # Add metadata about where this event was created
        tmp: Optional[Any] = inspect.currentframe()
        assert tmp is not None
        frame: FrameType = tmp.f_back
        if frame:
            module = frame.f_globals.get("__name__", "unknown")
            function = frame.f_code.co_name
            line = frame.f_lineno
            self.metadata["emitted_from"] = f"{module}.{function}:{line}"
        else:
            self.metadata["emitted_from"] = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> "Event":
        """
        Create an Event from a dictionary.
        """
        return cls(**event_dict)


@dataclass
class EventHandlerFailedEvent(Event):
    """Event emitted when an event handler fails."""

    event: Optional[Event] = None
    handler: Optional[str] = None
    exception: Optional[Exception] = None


@dataclass
class CommandStartedEvent(Event):
    """Event emitted when a command is started."""

    command: Optional[Command] = None


@dataclass
class CommandResultEvent(Event):
    """Event emitted when a command result is created."""

    command_result: Optional[CommandResult] = None
