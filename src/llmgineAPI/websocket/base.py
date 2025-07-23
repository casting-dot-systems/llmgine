"""
Base classes for WebSocket message handlers.

This module provides abstract base classes and utilities for
handling WebSocket messages in a structured way.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
import uuid
from fastapi import WebSocket
from pydantic import ValidationError
import json
import logging

from llmgineAPI.models.websocket import WSMessage, WSResponse, WSError, WSErrorCode
from llmgineAPI.services.session_service import SessionService

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