"""
WebSocket router for the LLMGine API.

This router handles WebSocket connections for real-time session communication,
including connection registration, server-initiated messaging, and cleanup.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import uuid
from typing import Dict, Set
from threading import RLock

from llmgineAPI.models.websocket import WSError, WSErrorCode, ConnectedResponse
from llmgineAPI.services.session_service import SessionService
from llmgineAPI.services.engine_service import EngineService
from llmgineAPI.websocket.registry import create_websocket_manager
from llmgineAPI.websocket.connection_registry import get_connection_registry
from llmgineAPI.core.messaging_api import MessagingAPIWithEvents
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID

router = APIRouter(prefix="/api", tags=["websocket"])

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get global registry instances
connection_registry = get_connection_registry()

def register_session_to_app(app_id: str, session_id: SessionID) -> None:
    """Register a session to an app_id."""
    connection_registry.register_session_to_app(app_id, session_id)

def unregister_session_from_app(app_id: str, session_id: SessionID) -> None:
    """Unregister a session from an app_id."""
    connection_registry.unregister_session_from_app(app_id, session_id)

def cleanup_app_sessions(app_id: str) -> None:
    """Clean up all sessions associated with an app_id when WebSocket disconnects."""
    session_ids = connection_registry.get_app_sessions(app_id)
    if not session_ids:
        logger.info(f"No sessions found for app {app_id}")
        return
    
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
            
            # Unregister session handlers
            message_bus = MessageBus()
            message_bus.unregister_session_handlers(SessionID(session_id))
            logger.info(f"Unregistered session handlers for session {session_id}")
            
            # Delete the session (this also calls unregister_engine internally)
            session_service.delete_session(session_id)
            logger.info(f"Deleted session {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    logger.info(f"Completed cleanup for app {app_id}")

def get_app_sessions(app_id: str) -> Set[SessionID]:
    """Get all session IDs for an app_id."""
    return connection_registry.get_app_sessions(app_id)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for real-time session communication.
    
    Provides a persistent connection for real-time communication with a session,
    including support for server-initiated messaging.
    
    Args:
        websocket: The WebSocket connection
        
    WebSocket Protocol:
        - All messages must be valid JSON
        - Request format: {"type": "<message_type>", "message_id": "<uuid>", "data": {...}}
        - Response format: {"type": "<response_type>", "message_id": "<uuid>", "data": {...}}
        - Error format: {"type": "error", "message_id": "<uuid>", "data": {"code": "<error_code>", "message": "<message>"}}
        
    Supported Message Types:
        Client-Initiated:
            - ping: Test connection
            - status: Get session status  
            - create_session: Create a new session
        
        Server-Initiated:
            - server_request: Server request requiring response
            - notification: Fire-and-forget server notification
            - server_ping: Server-initiated ping
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    # Generate unique app_id for this frontend application
    app_id = str(uuid.uuid4())
    
    # Initialize messaging API for server-initiated messages
    messaging_api = MessagingAPIWithEvents(connection_registry)
    
    try:
        # Register connection in the registry
        connection_registry.register_connection(app_id, websocket)
        logger.info(f"Registered WebSocket connection for app {app_id}")
        
        # Get API factory from app state (if available)
        api_factory = getattr(websocket.app.state, 'api_factory', None)
        
        # Create WebSocket manager with handlers and messaging support
        session_service = SessionService()
        ws_manager = create_websocket_manager(
            session_service, 
            api_factory, 
            connection_registry, 
            messaging_api
        )
        
        # Notify messaging API about connection
        await messaging_api.notify_connection_established(app_id)
        
        # Send connection confirmation with app_id
        connected_response = ConnectedResponse(
            type="connected",
            message_id=str(uuid.uuid4()),
            data=ConnectedResponse.ConnectedResponseData(
                app_id=app_id,
                status="connected"
            )
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
                    print(f"Sending response: {response}")
                    await ws_manager.send_response(websocket, response)
                    print(f"Response sent: {response}")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for app {app_id}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for app {app_id}: {e}")
        try:
            error_response = WSError(
                type="error",
                message_id=str(uuid.uuid4()),
                data=WSError.WSErrorData(
                    code=WSErrorCode.WEBSOCKET_ERROR,
                    message=f"WebSocket error: {str(e)}",
                    details=None
                )
            )
            await websocket.send_text(error_response.model_dump_json())
        except:
            pass
        finally:
            await websocket.close(code=1011)  # Internal server error
    
    finally:
        # Notify messaging API about disconnection
        try:
            await messaging_api.notify_connection_closed(app_id)
        except Exception as e:
            logger.error(f"Error notifying connection closed: {e}")
        
        # Clean up WebSocket manager resources
        ws_manager.cleanup_on_disconnect(app_id)
        
        # Clean up all sessions and engines associated with this app_id
        logger.info(f"Cleaning up app {app_id} on WebSocket closure")
        cleanup_app_sessions(app_id)
        
        # Unregister connection from registry
        connection_registry.unregister_connection(app_id)
        logger.info(f"Unregistered WebSocket connection for app {app_id}")