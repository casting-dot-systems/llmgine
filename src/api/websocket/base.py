"""
Base classes for WebSocket message handlers.

This module provides abstract base classes and utilities for
handling WebSocket messages in a structured way.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from fastapi import WebSocket
from pydantic import ValidationError
import json
import logging

from api.models.websocket import WSMessage, WSResponse, WSError, WSErrorCode
from api.services.session_service import SessionService
from llmgine.llm import SessionID

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
    
    def __init__(self, session_service: SessionService):
        """Initialize the manager with required services."""
        self.session_service = session_service
        self.handlers: Dict[str, BaseHandler] = {}
    
    def register_handler(self, handler: BaseHandler) -> None:
        """Register a message handler."""
        self.handlers[handler.message_type] = handler
        logger.info(f"Registered handler for message type: {handler.message_type}")
    
    async def process_message(
        self, 
        raw_message: str, 
        websocket: WebSocket, 
        session_id: SessionID
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
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                return WSError(
                    WSErrorCode.INVALID_JSON,
                    "Message must be valid JSON"
                )
            
            # Extract message type
            message_type = data.get("type")
            if not message_type:
                return WSError(
                    WSErrorCode.VALIDATION_ERROR,
                    "Message must include 'type' field"
                )
            
            # Find handler
            handler = self.handlers.get(message_type)
            if not handler:
                return WSError(
                    WSErrorCode.INVALID_MESSAGE_TYPE,
                    f"Unknown message type: {message_type}"
                )
            
            # Validate message
            try:
                validated_message = handler.validate_message(data)
            except ValidationError as e:
                return WSError(
                    WSErrorCode.VALIDATION_ERROR,
                    f"Validation failed: {str(e)}"
                )
            
            # Update session activity
            self.session_service.update_session_last_interaction_at(session_id)
            
            # Handle message
            return await handler.handle(validated_message, websocket, session_id)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return WSError(
                WSErrorCode.WEBSOCKET_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def send_response(self, websocket: WebSocket, response: WSResponse) -> None:
        """Send a response through the WebSocket."""
        try:
            await websocket.send_text(response.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            raise