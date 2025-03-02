from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4


class Event(ABC):
    """Base class for all events in the system.
    
    Events represent something that has happened in the system.
    Multiple subscribers can listen to and react to events.
    """
    event_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not hasattr(self, 'event_id'):
            self.event_id = str(uuid4())

class BlockEvent(Event):

    
    





