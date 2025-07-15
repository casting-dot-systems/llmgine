"""
Event management router for the LLMGine API.

This router handles:
- Publishing events to the message bus
- Retrieving events for a session
- Getting specific event details
- # TODO: Real-time event streaming via WebSocket
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from llmgine.api.models.events import EventFetchResponse
from llmgine.llm import SessionID
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.bus.bus import MessageBus
from llmgine.api.models import EventPublishResponse, EventListResponse, EventPublishStatus
from llmgine.messages.events import Event

router = APIRouter(prefix="/api/sessions/{session_id}/events", tags=["events"])


# Dependency injection
def get_session_service() -> SessionService:
    """Get the session service singleton"""
    return SessionService()

def get_message_bus() -> MessageBus:
    """Get the message bus singleton"""
    return MessageBus()

def validate_session(session_id: str, session_service: SessionService = Depends(get_session_service)) -> SessionID:
    """Validate that the session exists and is active"""
    session = session_service.get_session(SessionID(session_id))
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    if session.get_status() == SessionStatus.FAILED:
        raise HTTPException(status_code=400, detail=f"Session {session_id} has failed status")
    
    return SessionID(session_id)

@router.post("/", response_model=EventPublishResponse, status_code=201)
async def publish_event(
    session_id: str,
    event_request: Event,
    session_service: SessionService = Depends(get_session_service),
    message_bus: MessageBus = Depends(get_message_bus),
    _: SessionID = Depends(validate_session)
):
    """
    Publish an event to the message bus for a specific session.
    
    Args:
        session_id: The session ID
        event_request: The event data to publish
        
    Returns:
        The published event details
    """
    try:
        # Update session last interaction time
        session_service.update_session_last_interaction_at(SessionID(session_id))
        
        # Check if event session_id matches the session_id
        if event_request.session_id != session_id:
            return EventPublishResponse(
                event_id=event_request.event_id,
                session_id=session_id,
                status=EventPublishStatus.FAILED,
                error=f"Event session_id {event_request.session_id} does not match session_id {session_id}"
            )
        
        # Publish to message bus
        await message_bus.publish(event_request)
        
        # For now, we'll return the event data as if it was published
        return EventPublishResponse(
            event_id=event_request.event_id,
            session_id=session_id,
            status=EventPublishStatus.PUBLISHED
        )
        
    except Exception as e:
        return EventPublishResponse(
            event_id=event_request.event_id,
            session_id=session_id,
            status=EventPublishStatus.FAILED,
            error=f"Failed to publish event: {str(e)}"
        )

@router.get("/", response_model=EventListResponse)
async def get_events(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    session_service: SessionService = Depends(get_session_service),
    _: SessionID = Depends(validate_session),
    message_bus: MessageBus = Depends(get_message_bus)
):
    """
    Get events for a specific session with optional filtering and pagination.
    
    Args:
        session_id: The session ID
        limit: Maximum number of events to return
        offset: Number of events to skip
        event_type: Filter by event type
        
    Returns:
        List of events with pagination info
    """
    try:
        # Update session last interaction time
        session_service.update_session_last_interaction_at(SessionID(session_id))
        
        events: List[Event] = await message_bus.get_events(SessionID(session_id))

        # Apply pagination
        total = len(events)
        paginated_events = events[offset:offset + limit]
        
        
        return EventListResponse(
            events=paginated_events,
            total=total,
            limit=limit,
            offset=offset,
            status=EventPublishStatus.PUBLISHED
        )
        
    except Exception as e:
        return EventListResponse(
            events=[],
            total=0,
            limit=limit,
            offset=offset,
            status=EventPublishStatus.FAILED,
            error=f"Failed to retrieve events: {str(e)}"
        )

@router.get("/{event_id}", response_model=EventFetchResponse)
async def get_event(
    session_id: str,
    event_id: str,
    session_service: SessionService = Depends(get_session_service),
    _: SessionID = Depends(validate_session),
    message_bus: MessageBus = Depends(get_message_bus)
):
    """
    Get a specific event by its ID.
    
    Args:
        session_id: The session ID
        event_id: The event ID
        
    Returns:
        The event details
    """
    try:
        # Update session last interaction time
        session_service.update_session_last_interaction_at(SessionID(session_id))
        
        events: List[Event] = await message_bus.get_events(SessionID(session_id))

        event: Optional[Event] = next((e for e in events if e.event_id == event_id), None)

        if event is None:
            return EventFetchResponse(
                event_id=event_id,
                session_id=session_id,
                status=EventPublishStatus.FAILED,
                error=f"Event {event_id} not found"
            )
        
        return EventFetchResponse(
            event_id=event.event_id,
            session_id=session_id,
            status=EventPublishStatus.PUBLISHED
        )
        
    except Exception as e:
        return EventFetchResponse(
            event_id=event_id,
            session_id=session_id,
            status=EventPublishStatus.FAILED,
            error=f"Failed to retrieve event: {str(e)}"
        )

# @router.websocket("/stream")
# async def stream_events(
#     websocket: WebSocket,
#     session_id: str,
#     session_service: SessionService = Depends(get_session_service)
# ):
#     """
#     WebSocket endpoint for real-time event streaming.
    
#     Args:
#         websocket: The WebSocket connection
#         session_id: The session ID
#     """
#     try:
#         await websocket.accept()
        
#         # Validate session
#         session = session_service.get_session(SessionID(session_id))
#         if not session:
#             await websocket.send_text('{"error": "Session not found"}')
#             await websocket.close()
#             return
        
#         # Update session last interaction time
#         session_service.update_session_last_interaction_at(SessionID(session_id))
        
#         # This is a placeholder - you'll need to implement actual event streaming
#         # For now, we'll send a connection confirmation
#         await websocket.send_text('{"type": "connected", "session_id": "' + session_id + '"}')
        
#         # Keep connection alive and handle incoming messages
#         while True:
#             try:
#                 # Wait for any message from client (ping/pong or disconnect)
#                 data = await websocket.receive_text()
                
#                 # Handle ping/pong
#                 if data == "ping":
#                     await websocket.send_text("pong")
                    
#             except WebSocketDisconnect:
#                 break
                
#     except Exception as e:
#         try:
#             await websocket.send_text(f'{{"error": "Stream error: {str(e)}"}}')
#         except:
#             pass
#         finally:
#             await websocket.close()

