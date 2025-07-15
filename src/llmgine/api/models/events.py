from pydantic import BaseModel
from typing import List, Optional

from llmgine.messages.events import Event
from llmgine.api.models.responses import ResponseStatus

class EventPublishResponse(BaseModel):
    """Response model for event data"""
    event_id: str
    session_id: str
    status: ResponseStatus
    error: Optional[str] = None

class EventListResponse(BaseModel):
    """Response model for list of events"""
    events: List[Event]
    total: int
    limit: int
    offset: int
    status: ResponseStatus
    error: Optional[str] = None

class EventFetchResponse(BaseModel):
    """Response model for fetching an event"""
    event_id: str
    session_id: str
    status: ResponseStatus
    error: Optional[str] = None