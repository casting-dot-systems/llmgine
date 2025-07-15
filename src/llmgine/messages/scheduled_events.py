from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Type, override
from pydantic import Field

from llmgine.messages.events import Event


@dataclass
class ScheduledEvent(Event):
    """Base class for all scheduled events.
    
    Scheduled events are placed in the message bus and are processed
    at a specific time.
    Scheduled time must be provided. 
    If not, the event will be treated as a regular event.
    """
    scheduled_time: datetime = Field(default_factory=lambda: datetime.now())

    @override
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary.
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "session_id": self.session_id,
            "scheduled_time": self.scheduled_time.isoformat()
        }
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> "ScheduledEvent":
        """
        Create a ScheduledEvent from a dictionary.
        """
        if "scheduled_time" in event_dict:
            event_dict["scheduled_time"] = datetime.fromisoformat(event_dict["scheduled_time"])
        return cls(**event_dict)
    
# Container for all scheduled event classes
EVENT_CLASSES: Dict[str, Type[ScheduledEvent]] = {"ScheduledEvent": ScheduledEvent}

def register_scheduled_event_class(cls: Type[ScheduledEvent]) -> Type[ScheduledEvent]:
    """Decorator to automatically register event classes."""
    EVENT_CLASSES[cls.__name__] = cls
    return cls