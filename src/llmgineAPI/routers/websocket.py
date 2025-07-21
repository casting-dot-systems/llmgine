"""
WebSocket router for the LLMGine API.

This router handles WebSocket connections for real-time session communication.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import uuid
from typing import Dict, Set
from threading import RLock

from llmgineAPI.models.websocket import WSError, WSErrorCode, ConnectedResponse, MESSAGE_ID
from llmgineAPI.services.session_service import SessionService
from llmgineAPI.services.engine_service import EngineService
from llmgineAPI.websocket.registry import create_websocket_manager
from llmgine.llm import SessionID

router = APIRouter(prefix="/api", tags=["websocket"])

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global static mapping for app_id to session_ids
# This is shared across all WebSocket connections
_app_session_mapping: Dict[str, Set[SessionID]] = {}
_app_mapping_lock = RLock()

def register_session_to_app(app_id: str, session_id: SessionID) -> None:
    """Register a session to an app_id."""
    with _app_mapping_lock:
        if app_id not in _app_session_mapping:
            _app_session_mapping[app_id] = set()
        _app_session_mapping[app_id].add(session_id)
        logger.info(f"Registered session {session_id} to app {app_id}")

def unregister_session_from_app(app_id: str, session_id: SessionID) -> None:
    """Unregister a session from an app_id."""
    with _app_mapping_lock:
        if app_id in _app_session_mapping:
            _app_session_mapping[app_id].discard(session_id)
            if not _app_session_mapping[app_id]:  # Remove empty app entries
                del _app_session_mapping[app_id]
            logger.info(f"Unregistered session {session_id} from app {app_id}")

def cleanup_app_sessions(app_id: str) -> None:
    """Clean up all sessions associated with an app_id when WebSocket disconnects."""
    with _app_mapping_lock:
        if app_id not in _app_session_mapping:
            logger.info(f"No sessions found for app {app_id}")
            return
        
        session_ids = _app_session_mapping[app_id].copy()
        logger.info(f"Cleaning up {len(session_ids)} sessions for app {app_id}")
        
        # Get service instances
        session_service = SessionService()
        engine_service = EngineService()
        
        # Delete all sessions and their associated engines
        for session_id in session_ids:
            try:
                # Get the registered engine for this session (if any)
                registered_engine = engine_service.get_registered_engine(session_id)
                if registered_engine:
                    # Unregister and delete the engine
                    engine_service.unregister_engine(session_id)
                    engine_service.delete_engine(registered_engine.engine_id)
                    logger.info(f"Deleted engine {registered_engine.engine_id} for session {session_id}")
                
                # Delete the session (this also calls unregister_engine internally)
                session_service.delete_session(session_id)
                logger.info(f"Deleted session {session_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {e}")
        
        # Remove the app_id entry
        del _app_session_mapping[app_id]
        logger.info(f"Completed cleanup for app {app_id}")

def get_app_sessions(app_id: str) -> Set[SessionID]:
    """Get all session IDs for an app_id."""
    with _app_mapping_lock:
        return _app_session_mapping.get(app_id, set()).copy()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
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
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    # Generate unique app_id for this frontend application
    app_id = str(uuid.uuid4())
    
    try:
        # Get API factory from app state (if available)
        api_factory = getattr(websocket.app.state, 'api_factory', None)
        
        # Create WebSocket manager with handlers
        session_service = SessionService()
        ws_manager = create_websocket_manager(session_service, api_factory)
        
        # Send connection confirmation with app_id
        connected_response = ConnectedResponse(
            app_id=app_id,
            status="connected",
            message_id=MESSAGE_ID(str(uuid.uuid4()))
        )
        await ws_manager.send_response(websocket, connected_response)
        logger.info(f"Connection confirmation sent for app {app_id}")
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                raw_message = await websocket.receive_text()
                logger.debug(f"Received message: {raw_message}")
                
                # Process message through manager
                response = await ws_manager.process_message(
                    raw_message, websocket
                )
                
                # Send response if one was generated
                if response:
                    await ws_manager.send_response(websocket, response)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for app {app_id}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for app {app_id}: {e}")
        try:
            error_response = WSError(
                WSErrorCode.WEBSOCKET_ERROR,
                f"WebSocket error: {str(e)}",
                MESSAGE_ID(str(uuid.uuid4()))
            )
            await websocket.send_text(error_response.model_dump_json())
        except:
            pass
        finally:
            await websocket.close(code=1011)  # Internal server error
    
    finally:
        # Clean up all sessions and engines associated with this app_id
        logger.info(f"Cleaning up app {app_id} on WebSocket closure")
        cleanup_app_sessions(app_id)