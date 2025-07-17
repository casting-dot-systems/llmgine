
"""
Session management router for the LLMGine API.

This router handles session lifecycle management including:
- Creating new sessions
- Retrieving session information
- Terminating sessions
- Listing active sessions
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, WebSocket, WebSocketDisconnect
import json
import asyncio

from llmgine.api.models.sessions import (
    SessionCreateResponse,
    SessionEndResponse,
    SessionStatusResponse,
    SessionListResponse
)
from llmgine.api.models.responses import ResponseStatus
from llmgine.api.services.session_service import SessionService
from llmgine.api.utils.error_handler import (
    SessionNotFoundError,
    SessionInvalidError,
    ResourceLimitError,
    ValidationError,
    handle_api_error,
    handle_unexpected_error
)
from llmgine.llm import SessionID
from llmgine.api.routers.dependencies import get_session_service


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


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


@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Path(..., description="Session ID for WebSocket connection"),
    session_service: SessionService = Depends(get_session_service)
):
    """
    WebSocket endpoint for real-time session communication.
    
    Provides a persistent connection for real-time communication with a session.
    Supports bidirectional messaging for commands, events, and status updates.
    
    Args:
        websocket: The WebSocket connection
        session_id: The session ID to connect to
        
    WebSocket Protocol:
        - Incoming messages should be JSON with format: {"type": "command|event|ping", "data": {...}}
        - Outgoing messages follow format: {"type": "response|event|error|pong", "data": {...}}
        - Connection is automatically closed if session becomes invalid
    """
    await websocket.accept()
    
    try:
        # Validate session exists
        session = session_service.get_session(SessionID(session_id))
        if not session:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {
                    "code": "SESSION_NOT_FOUND",
                    "message": f"Session '{session_id}' not found or has expired"
                }
            }))
            await websocket.close(code=4004)
            return
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {
                "session_id": session_id,
                "status": session.get_status().value,
                "message": "WebSocket connection established"
            }
        }))
        
        # Update session activity
        session_service.update_session_last_interaction_at(SessionID(session_id))
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Update session activity
                session_service.update_session_last_interaction_at(SessionID(session_id))

                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    message_data = data.get("data", {})
                    
                    # Update session activity on any message
                    session_service.update_session_last_interaction_at(SessionID(session_id))
                    
                    # Handle different message types
                    if message_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "data": {"timestamp": message_data.get("timestamp")}
                        }))
                    
                    elif message_type == "status":
                        # Get current session status
                        current_session = session_service.get_session(SessionID(session_id))
                        if current_session:
                            await websocket.send_text(json.dumps({
                                "type": "status",
                                "data": {
                                    "session_id": session_id,
                                    "status": current_session.get_status().value,
                                    "created_at": current_session.created_at.isoformat(),
                                    "last_interaction_at": current_session.last_interaction_at.isoformat()
                                }
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "data": {
                                    "code": "SESSION_NOT_FOUND",
                                    "message": "Session no longer exists"
                                }
                            }))
                            break
                    
                    elif message_type == "command":
                        # Handle command execution (placeholder for now)
                        await websocket.send_text(json.dumps({
                            "type": "response",
                            "data": {
                                "message": "Command execution not yet implemented in WebSocket",
                                "command_data": message_data
                            }
                        }))
                    
                    elif message_type == "event":
                        # Handle event publishing (placeholder for now)
                        await websocket.send_text(json.dumps({
                            "type": "response",
                            "data": {
                                "message": "Event publishing not yet implemented in WebSocket",
                                "event_data": message_data
                            }
                        }))
                    
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": {
                                "code": "INVALID_MESSAGE_TYPE",
                                "message": f"Unknown message type: {message_type}"
                            }
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": {
                            "code": "INVALID_JSON",
                            "message": "Message must be valid JSON"
                        }
                    }))
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {
                    "code": "WEBSOCKET_ERROR",
                    "message": f"WebSocket error: {str(e)}"
                }
            }))
        except:
            pass
        finally:
            await websocket.close(code=1011)  # Internal server error

