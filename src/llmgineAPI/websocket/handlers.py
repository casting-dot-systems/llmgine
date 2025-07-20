"""
Concrete WebSocket message handlers.

This module implements specific handlers for each supported
WebSocket message type.
"""

from typing import Optional
from fastapi import WebSocket
import logging

from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.models.websocket import (
    PingRequest, PingResponse,
    StatusRequest, StatusResponse,
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
        return PingResponse(timestamp=timestamp)


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
                "Session no longer exists"
            )
        
        return StatusResponse(
            session_id=str(session_id),
            status=session.get_status().value,
            created_at=session.created_at,
            last_interaction_at=session.last_interaction_at
        )
