"""
Concrete WebSocket message handlers.

This module implements specific handlers for each supported
WebSocket message type.

Handlers must return a WSResponse object, which contains the message_id of the request.
"""

from typing import Optional
from fastapi import WebSocket
import logging

from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.models.websocket import (
    PingRequest, PingResponse,
    StatusRequest, StatusResponse,
    CreateSessionRequest, CreateSessionResponse,
    WSMessage,
    WSResponse, WSError, WSErrorCode
)
from llmgine.llm import SessionID

logger = logging.getLogger(__name__)


class PingHandler(BaseHandler):
    """Handler for ping messages."""
    
    @property
    def message_type(self) -> str:
        return "ping"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return PingRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle ping request."""
        timestamp = message.data["timestamp"]
        return PingResponse(timestamp=timestamp, message_id=message.message_id)


class StatusHandler(BaseHandler):
    """Handler for session status requests."""
    
    @property
    def message_type(self) -> str:
        return "status"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return StatusRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle status request."""
        session = self.session_service.get_session(session_id)
        
        if not session:
            return WSError(
                WSErrorCode.SESSION_NOT_FOUND,
                "Session no longer exists",
                message_id=message.message_id
            )
        
        return StatusResponse(
            session_id=str(session_id),
            status=session.get_status().value,
            created_at=session.created_at,
            last_interaction_at=session.last_interaction_at,
            message_id=message.message_id
        )


class CreateSessionHandler(BaseHandler):
    """Handler for creating new sessions."""
    
    @property
    def message_type(self) -> str:
        return "create_session"
    
    @property
    def request_model(self) -> type[WSMessage]:
        return CreateSessionRequest
    
    async def handle(
        self, 
        message: WSMessage, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle create session request."""
        from llmgineAPI.routers.websocket import register_session_to_app
        
        app_id = message.data.get("app_id")
        if not app_id:
            return WSError(
                WSErrorCode.VALIDATION_ERROR,
                "app_id is required for session creation",
                message_id=message.message_id
            )
        
        # Create new session
        new_session_id = self.session_service.create_session()
        
        if new_session_id is None:
            return WSError(
                WSErrorCode.ENGINE_CREATION_FAILED,
                "Failed to create session - maximum sessions reached",
                message_id=message.message_id
            )
        
        # Register the session to the app_id
        register_session_to_app(app_id, new_session_id)
        
        return CreateSessionResponse(session_id=str(new_session_id), message_id=message.message_id)
