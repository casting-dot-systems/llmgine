from typing import Optional
from pydantic import BaseModel

from llmgine.api.models.responses import ResponseStatus

class SessionCreateResponse(BaseModel):
    """Response model for session creation"""
    session_id: str
    status: ResponseStatus
    error: Optional[str] = None

class SessionEndResponse(BaseModel):
    """Response model for session end"""
    session_id: str
    status: ResponseStatus
    error: Optional[str] = None