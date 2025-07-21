"""
Base classes for WebSocket message handlers.

This module provides abstract base classes and utilities for
handling WebSocket messages in a structured way.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
from fastapi import WebSocket
from pydantic import ValidationError
import json
import logging

from llmgineAPI.models.websocket import WSMessage, WSResponse, WSError, WSErrorCode
from llmgineAPI.services.session_service import SessionService
from llmgine.llm import SessionID

if TYPE_CHECKING:
    from llmgineAPI.core.extensibility import ExtensibleHandlerRegistry

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
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """
        Handle the incoming message and return a response.
        
        Args:
            message: The validated message object
            websocket: The WebSocket connection
            session_id: The session ID
            
        Returns:
            Optional response to send back to the client
        """
        pass
    
    def validate_message(self, raw_data: Dict[str, Any]) -> WSMessage:
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
            return self.request_model(**raw_data)
        except ValidationError as e:
            logger.error(f"Validation error for {self.message_type}: {e}")
            raise


class WebSocketManager:
    """Manages WebSocket message routing and handling."""
    
    def __init__(self, session_service: SessionService, handler_registry: Optional["ExtensibleHandlerRegistry"] = None):
        """Initialize the manager with required services."""
        self.session_service = session_service
        self.handlers: Dict[str, BaseHandler] = {}
        
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
            session_id: The session ID
            
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
                    WSErrorCode.INVALID_JSON,
                    "Message must be valid JSON"
                )
            
            # Extract message_id if available
            message_id = data.get("message_id")
            
            # Get session id from data
            session_id = data.get("session_id")
            if not session_id:
                return WSError(
                    WSErrorCode.VALIDATION_ERROR,
                    "Message must include 'session_id' field",
                    message_id=message_id
                )
            
            # Validate session id
            session_service = SessionService()
            session = session_service.get_session(session_id)
            if not session:
                return WSError(
                    WSErrorCode.SESSION_NOT_FOUND,
                    f"Session '{session_id}' not found or has expired",
                    message_id=message_id
                )
            
            # Extract message type
            print(f"Data: {data}")
            message_type = data.get("type")
            if not message_type:
                return WSError(
                    WSErrorCode.VALIDATION_ERROR,
                    "Message must include 'type' field",
                    message_id=message_id
                )
            
            # Find handler

            handler = self.handlers.get(message_type)
            if not handler:
                return WSError(
                    WSErrorCode.INVALID_MESSAGE_TYPE,
                    f"Unknown message type: {message_type}",
                    message_id=message_id
                )
            print(f"Handler: {handler}")
            # Validate message
            try:
                validated_message = handler.validate_message(data.get("data", {}))
            except ValidationError as e:
                return WSError(
                    WSErrorCode.VALIDATION_ERROR,
                    f"Validation failed: {str(e)}",
                    message_id=message_id
                )
            print(f"Validated message: {validated_message}")
            # Update session activity
            self.session_service.update_session_last_interaction_at(session_id)
            
            # Handle message
            return await handler.handle(validated_message, websocket, session_id)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return WSError(
                WSErrorCode.WEBSOCKET_ERROR,
                f"Internal error: {str(e)}",
                message_id=data.get("message_id") if 'data' in locals() else None
            )
    
    async def send_response(self, websocket: WebSocket, response: WSResponse) -> None:
        """Send a response through the WebSocket."""
        try:
            await websocket.send_text(response.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            raise