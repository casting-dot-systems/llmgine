"""
Session-related Pydantic models for the LLMGine API.

This module defines request and response models for session management
endpoints including creation, termination, and status queries.
"""

from typing import Optional
from pydantic import Field
from datetime import datetime

from llmgineAPI.models.responses import BaseResponse
from llmgineAPI.services.session_service import Session


class SessionCreateResponse(BaseResponse):
    """Response model for session creation."""
    session_id: Optional[str] = Field(None, description="Unique identifier for the created session")


class SessionEndResponse(BaseResponse):
    """Response model for session termination."""
    session_id: str = Field(..., description="Unique identifier of the terminated session")


class SessionStatusResponse(BaseResponse):
    """Response model for session status queries."""
    session_id: str = Field(..., description="Unique identifier of the session")
    created_at: datetime = Field(..., description="Timestamp when the session was created")
    last_interaction_at: datetime = Field(..., description="Timestamp of the last interaction")


class SessionListResponse(BaseResponse):
    """Response model for listing sessions."""
    sessions: list[Session] = Field(default_factory=list, description="List of active sessions")
    total: int = Field(0, description="Total number of sessions")
    limit: int = Field(50, description="Maximum number of sessions returned")
    offset: int = Field(0, description="Number of sessions skipped")