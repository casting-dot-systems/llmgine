"""
Base classes for WebSocket message handlers.

This module provides abstract base classes and utilities for
handling WebSocket messages in a structured way, including support
for server-initiated messaging.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
import uuid
import asyncio
from fastapi import WebSocket
from pydantic import ValidationError
import json
import logging

from llmgineAPI.models.websocket import (
    WSMessage, WSResponse, WSError, WSErrorCode, 
    ServerResponse, ServerPongResponse
)
from llmgineAPI.services.session_service import SessionService

if TYPE_CHECKING:
    from llmgineAPI.core.extensibility import ExtensibleHandlerRegistry
    from llmgineAPI.websocket.connection_registry import ConnectionRegistry
    from llmgineAPI.core.messaging_api import ServerMessagingAPI

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Abstract base class for WebSocket message handlers."""
    
    def __init__(self, session_service: SessionService):
        """Initialize the handler with required services."""
        self.session_service = session_service
    
    @property
    @abstractmethod
    def message_type(self) -> str:
        """The message type this handler processes."""
        pass
    
    @property
    @abstractmethod
    def request_model(self) -> type[WSMessage]:
        """The Pydantic model for validating incoming requests."""
        pass
    
    @abstractmethod
    async def handle(
        self, 
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """
        Handle the incoming message and return a response.
        
        Args:
            message: The validated message object
            websocket: The WebSocket connection
            
        Returns:
            Optional response to send back to the client
        """
        pass
    
    def validate_message(self, raw_data: Dict[str, Any]) -> None:
        """
        Validate the raw message data against the request model.
        
        Args:
            raw_data: Raw message data from the client
            
        Returns:
            Validated message object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            self.request_model(**raw_data)
        except ValidationError as e:
            logger.error(f"Validation error for {self.message_type}: {e}")
            raise


class WebSocketManager:
    """Manages WebSocket message routing and handling, including server-initiated messaging."""
    
    def __init__(
        self, 
        session_service: SessionService, 
        handler_registry: Optional["ExtensibleHandlerRegistry"] = None,
        connection_registry: Optional["ConnectionRegistry"] = None,
        messaging_api: Optional["ServerMessagingAPI"] = None
    ):
        """Initialize the manager with required services."""
        self.session_service = session_service
        self.handlers: Dict[str, BaseHandler] = {}
        self.connection_registry = connection_registry
        self.messaging_api = messaging_api
        
        # Set up bidirectional reference with messaging API
        if self.messaging_api:
            self.messaging_api.set_websocket_manager(self)
        
        # If a handler registry is provided, populate handlers from it
        if handler_registry:
            self._populate_handlers_from_registry(handler_registry)
    
    def _populate_handlers_from_registry(self, handler_registry: "ExtensibleHandlerRegistry") -> None:
        """Populate handlers from the extensible handler registry."""
        all_handler_classes = handler_registry.get_all_handlers()
        for message_type, handler_class in all_handler_classes.items():
            # Instantiate the handler with session service
            handler_instance = handler_class(self.session_service)
            self.handlers[message_type] = handler_instance
            logger.info(f"Registered handler from registry for message type: {message_type}")
    
    def register_handler(self, handler: BaseHandler) -> None:
        """Register a message handler."""
        self.handlers[handler.message_type] = handler
        logger.info(f"Registered handler for message type: {handler.message_type}")
    
    async def process_message(
        self, 
        raw_message: str, 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """
        Process an incoming WebSocket message.
        
        Args:
            raw_message: Raw JSON message from the client
            websocket: The WebSocket connection
            
        Returns:
            Response to send back to the client, or None if no response needed
        """
        try:
            # Parse JSON
            print(f"Raw message: {raw_message}")
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                return WSError(
                    type="error",
                    message_id=str(uuid.uuid4()),
                    data=WSError.WSErrorData(
                        code=WSErrorCode.INVALID_JSON,
                        message="Message must be valid JSON",
                        details=None
                    )
                )
            
            print(f"Data: {data}")
            # Extract message_id if available
            message_id = data.get("message_id")
            
            # Extract message type
            message_type = data.get("type")
            if not message_type:
                return WSError(
                    type="error",
                    message_id=message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.VALIDATION_ERROR,
                        message="Message must include 'type' field",
                        details=None
                    )
                )
            
            # Check if this is a response to a server-initiated request
            if self.messaging_api and message_id:
                if message_type in ["server_response", "server_pong"]:
                    # Try to resolve as server request response
                    try:
                        if message_type == "server_response":
                            response = ServerResponse(
                                response_type=data.get("data", {}).get("response_type", "unknown"),
                                data=data.get("data", {}),
                                message_id=message_id
                            )
                        elif message_type == "server_pong":
                            response = ServerPongResponse(
                                timestamp=data.get("data", {}).get("timestamp", ""),
                                server_timestamp=data.get("data", {}).get("server_timestamp", ""),
                                message_id=message_id
                            )
                        else:
                            response = WSResponse(
                                type=message_type,
                                message_id=message_id,
                                data=data.get("data", {})
                            )
                        
                        # Try to resolve pending request
                        if self.messaging_api.resolve_pending_request(message_id, response):
                            logger.debug(f"Resolved server request {message_id}")
                            return None  # No further processing needed
                    except Exception as e:
                        logger.error(f"Error processing server response {message_id}: {e}")
                        # Continue with normal processing if server response handling fails

            # Get session id from data
            if message_type != "create_session":
                session_id = data.get("data", {}).get("session_id")
                
                if not session_id:
                    return WSError(
                        type="error",
                        message_id=message_id,
                        data=WSError.WSErrorData(
                            code=WSErrorCode.VALIDATION_ERROR,
                            message="Message must include 'session_id' field",
                            details=None
                        )
                    )


                # Validate session id
                session_service = SessionService()
                session = session_service.get_session(session_id)


                if not session:
                    return WSError(
                        type="error",
                        message_id=message_id,
                        data=WSError.WSErrorData(
                            code=WSErrorCode.SESSION_NOT_FOUND,
                            message=f"Session '{session_id}' not found or has expired",
                            details=None
                        )
                    )
                print("here2")
            


            # Find handler
            print(f"Handlers: {self.handlers}")
            handler = self.handlers.get(message_type)
            if not handler:
                return WSError(
                    type="error",
                    message_id=message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.INVALID_MESSAGE_TYPE,
                        message=f"Unknown message type: {message_type}",
                        details=None
                    )
                )
            print(f"Handler: {handler}")
            # Validate message
            try:
                handler.validate_message(data)
            except ValidationError as e:
                return WSError(
                    type="error",
                    message_id=message_id,
                    data=WSError.WSErrorData(
                        code=WSErrorCode.VALIDATION_ERROR,
                        message=f"Validation failed: {str(e)}",
                        details=None
                    )
                )
            print(f"Validated message: {data}")
            # Update session activity
            if message_type != "create_session":
                self.session_service.update_session_last_interaction_at(data.get("session_id"))
            
            # Handle message
            return await handler.handle(data, websocket)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return WSError(
                type="error",
                message_id=str(uuid.uuid4()),
                data=WSError.WSErrorData(
                    code=WSErrorCode.WEBSOCKET_ERROR,
                    message=f"Internal error: {str(e)}",
                    details=None
                )
            )
    
    async def send_response(self, websocket: WebSocket, response: WSResponse) -> None:
        """Send a response through the WebSocket."""
        try:
            await websocket.send_text(response.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            raise
    
    def cleanup_on_disconnect(self, app_id: str) -> None:
        """
        Clean up resources when a WebSocket disconnects.
        
        Args:
            app_id: The app ID that disconnected
        """
        if self.messaging_api:
            # Cancel any pending server requests for this connection
            self.messaging_api.cancel_pending_requests(f"Connection {app_id} disconnected")
            logger.info(f"Cancelled pending requests for disconnected app {app_id}")
        
        # Clean up completed request futures periodically
        if self.messaging_api:
            cleaned = self.messaging_api.cleanup_completed_requests()
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} completed request futures")
    
    def get_messaging_stats(self) -> Dict[str, Any]:
        """
        Get statistics about messaging operations.
        
        Returns:
            Dictionary with messaging statistics
        """
        stats = {
            "handlers_registered": len(self.handlers),
            "connection_registry_available": self.connection_registry is not None,
            "messaging_api_available": self.messaging_api is not None,
        }
        
        if self.messaging_api:
            stats.update({
                "pending_requests": self.messaging_api.get_pending_request_count(),
                "connected_apps": len(self.messaging_api.get_connected_apps()) if hasattr(self.messaging_api, 'get_connected_apps') else 0
            })
        
        if self.connection_registry:
            health_info = self.connection_registry.get_health_info()
            stats.update({
                "total_connections": health_info["total_connections"],
                "total_sessions": health_info["total_sessions"]
            })
        
        return stats