"""
WebSocket router for the LLMGine API.

This router handles WebSocket connections for real-time session communication.
"""

from fastapi import APIRouter, Depends, Path, WebSocket, WebSocketDisconnect
import logging

from llmgineAPI.models.websocket import WSError, WSErrorCode, ConnectedResponse
from llmgineAPI.services.session_service import SessionService
from llmgine.llm import SessionID
from llmgineAPI.routers.dependencies import get_session_service
from llmgineAPI.websocket.registry import create_websocket_manager

router = APIRouter(prefix="/api/sessions", tags=["websocket"])

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Path(..., description="Session ID for WebSocket connection"),
    session_service: SessionService = Depends(get_session_service)
):
    """
    WebSocket endpoint for real-time session communication.
    
    Provides a persistent connection for real-time communication with a session.
    Uses structured message handling with Pydantic validation for type safety.
    
    Args:
        websocket: The WebSocket connection
        session_id: The session ID to connect to
        
    WebSocket Protocol:
        - All messages must be valid JSON
        - Request format: {"type": "<message_type>", "data": {...}}
        - Response format: {"type": "<response_type>", "data": {...}}
        - Error format: {"type": "error", "data": {"code": "<error_code>", "message": "<message>"}}
        
    Supported Message Types:
        - ping: Test connection
        - get_engine_types: Get available engine types
        - link_engine: Create and link an engine to session
        - status: Get session status
        - command: Execute a command (placeholder)
        - event: Publish an event (placeholder)
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    try:
        # Validate session exists
        session_id_obj = SessionID(session_id)
        session = session_service.get_session(session_id_obj)

        if not session:
            error_response = WSError(
                WSErrorCode.SESSION_NOT_FOUND,
                f"Session '{session_id}' not found or has expired"
            )
            await websocket.send_text(error_response.model_dump_json())
            await websocket.close(code=4004)
            return
        
        # Get API factory from app state (if available)
        api_factory = getattr(websocket.app.state, 'api_factory', None)
        
        # Create WebSocket manager with handlers
        ws_manager = create_websocket_manager(session_service, api_factory)
        
        # Send connection confirmation
        connected_response = ConnectedResponse(
            session_id=session_id,
            status=session.get_status().value
        )
        await ws_manager.send_response(websocket, connected_response)
        logger.info("Connection confirmation sent")
        
        # Update session activity
        session_service.update_session_last_interaction_at(session_id_obj)
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                raw_message = await websocket.receive_text()
                logger.debug(f"Received message: {raw_message}")
                
                # Process message through manager
                response = await ws_manager.process_message(
                    raw_message, websocket, session_id_obj
                )
                
                # Send response if one was generated
                if response:
                    await ws_manager.send_response(websocket, response)
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            error_response = WSError(
                WSErrorCode.WEBSOCKET_ERROR,
                f"WebSocket error: {str(e)}"
            )
            await websocket.send_text(error_response.model_dump_json())
        except:
            pass
        finally:
            await websocket.close(code=1011)  # Internal server error