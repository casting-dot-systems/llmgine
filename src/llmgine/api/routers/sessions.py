
"""
Session management router for the LLMGine API.

This router handles:
- Creating a new session
- Ending a session
- Getting session status and metadata
"""

from typing import Optional
from fastapi import APIRouter, Depends

from llmgine.api.models.sessions import SessionEndResponse
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

@router.post("/{session_id}/end", response_model=SessionEndResponse, status_code=200)
async def end_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionEndResponse:
    """
    End a session
    """
    session_service.delete_session(SessionID(session_id))
    
    return SessionEndResponse(
        session_id=str(session_id),
        status=ResponseStatus.SUCCESS
    )

