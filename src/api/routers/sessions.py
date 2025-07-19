
"""
Session management router for the LLMGine API.

This router handles session lifecycle management including:
- Creating new sessions
- Retrieving session information
- Terminating sessions
- Listing active sessions
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
import logging

from llmgine.llm import SessionID

from api.models.sessions import (
    SessionCreateResponse,
    SessionEndResponse,
    SessionStatusResponse,
    SessionListResponse
)
from api.models.responses import ResponseStatus
from api.services.session_service import SessionService
from api.utils.error_handler import (
    SessionNotFoundError,
    ResourceLimitError,
    ValidationError,
    handle_api_error,
    handle_unexpected_error
)
from api.routers.dependencies import get_session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    session_service: SessionService = Depends(get_session_service)
) -> SessionCreateResponse:
    """
    Create a new session.
    
    Creates a new session and returns its unique identifier.
    Sessions are automatically monitored for activity and cleaned up
    when they become idle.
    
    Returns:
        SessionCreateResponse: Contains the new session ID and status
        
    Raises:
        ResourceLimitError: When maximum session limit is reached
    """
    try:
        session_id: Optional[SessionID] = session_service.create_session()
        if session_id is None:
            raise ResourceLimitError("sessions", session_service.max_sessions)
        
        return SessionCreateResponse(
            session_id=str(session_id),
            status=ResponseStatus.SUCCESS,
            message="Session created successfully"
        )
        
    except ResourceLimitError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "create_session"})


@router.get("/{session_id}", response_model=SessionStatusResponse, status_code=200)
async def get_session_status(
    session_id: str = Path(..., description="Session ID to retrieve"),
    session_service: SessionService = Depends(get_session_service)
) -> SessionStatusResponse:
    """
    Get detailed information about a specific session.
    
    Args:
        session_id: Unique identifier of the session
        
    Returns:
        SessionStatusResponse: Session details including status and timestamps
        
    Raises:
        SessionNotFoundError: When session doesn't exist
    """
    try:
        session = session_service.get_session(SessionID(session_id))
        
        if session is None:
            raise SessionNotFoundError(session_id)
            
        return SessionStatusResponse(
            session_id=session_id,
            status=session.get_status().value,
            created_at=session.created_at,
            last_interaction_at=session.last_interaction_at
        )
        
    except SessionNotFoundError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "get_session_status", "session_id": session_id})


@router.get("/", response_model=SessionListResponse, status_code=200)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    session_service: SessionService = Depends(get_session_service)
) -> SessionListResponse:
    """
    List all active sessions with pagination.
    
    Args:
        limit: Maximum number of sessions to return (1-100)
        offset: Number of sessions to skip for pagination
        
    Returns:
        SessionListResponse: List of sessions with pagination metadata
    """
    try:
        # validate limit and offset
        if limit < 1 or limit > 100:
            raise ValidationError("limit", "Limit must be between 1 and 100", limit)
        if offset < 0:
            raise ValidationError("offset", "Offset must be greater than or equal to 0", offset)
        

        all_sessions = session_service.get_all_sessions()
        
        # Convert sessions to dict format for response
        sessions_list = []
        for session_id, session in all_sessions.items():
            sessions_list.append({
                "session_id": str(session_id),
                "status": session.get_status().value,
                "created_at": session.created_at.isoformat(),
                "last_interaction_at": session.last_interaction_at.isoformat()
            })
        
        # Apply pagination
        total = len(sessions_list)
        paginated_sessions = sessions_list[offset:offset + limit]
        
        return SessionListResponse(
            sessions=paginated_sessions,
            total=total,
            limit=limit,
            offset=offset,
            status=ResponseStatus.SUCCESS
        )
        
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "list_sessions"})


@router.delete("/{session_id}", response_model=SessionEndResponse, status_code=200)
async def terminate_session(
    session_id: str = Path(..., description="Session ID to terminate"),
    session_service: SessionService = Depends(get_session_service)
) -> SessionEndResponse:
    """
    Terminate a session and clean up associated resources.
    
    This will disconnect any connected engines and remove the session
    from the active sessions list.
    
    Args:
        session_id: Unique identifier of the session to terminate
        
    Returns:
        SessionEndResponse: Confirmation of session termination
        
    Raises:
        SessionNotFoundError: When session doesn't exist
    """
    try:
        # Check if session exists before attempting to delete
        session = session_service.get_session(SessionID(session_id))
        if session is None:
            raise SessionNotFoundError(session_id)
        
        session_service.delete_session(SessionID(session_id))
        
        return SessionEndResponse(
            session_id=session_id,
            status=ResponseStatus.SUCCESS,
            message="Session terminated successfully"
        )
        
    except SessionNotFoundError as e:
        raise handle_api_error(e)
    except Exception as e:
        raise handle_unexpected_error(e, {"operation": "terminate_session", "session_id": session_id})



