# POST /api/sessions
# - Create a new session
# - Returns session_id

# DELETE /api/sessions/{session_id}
# - End a session and cleanup handlers

# GET /api/sessions/{session_id}/status
# - Get session status and metadata

"""
Session management router for the LLMGine API.

This router handles:
- Creating a new session
- Ending a session
- Getting session status and metadata
"""

from typing import Optional
from fastapi import APIRouter, Depends

from llmgine.api.services.session_service import SessionService
from llmgine.llm import SessionID
from llmgine.api.models import SessionCreateResponse, ResponseStatus


router = APIRouter(prefix="/api/sessions", tags=["sessions"])

def get_session_service() -> SessionService:
    """Get the session service singleton"""
    return SessionService()

@router.post("/create", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    session_service: SessionService = Depends(get_session_service)
):
    """
    Create a new session
    """
    session_id : Optional[SessionID] = session_service.create_session()

    if session_id is None:
        return SessionCreateResponse(
            session_id=str(session_id),
            status=ResponseStatus.FAILED,
            error=f"Failed to create session: Max sessions reached"
        )
    else:
        return SessionCreateResponse(
            session_id=str(session_id),
            status=ResponseStatus.SUCCESS
        )
