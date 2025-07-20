"""
Concrete WebSocket message handlers.

This module implements specific handlers for each supported
WebSocket message type.
"""

from typing import Optional
from fastapi import WebSocket
from pydantic import BaseModel
import logging

from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.models.websocket import (
    PingRequest, PingResponse,
    StatusRequest, StatusResponse,
    CommandRequest, CommandResponse,
    EventRequest, EventResponse,
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
    def request_model(self) -> type[BaseModel]:
        return PingRequest
    
    async def handle(
        self, 
        message: PingRequest, 
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
    def request_model(self) -> type[BaseModel]:
        return StatusRequest
    
    async def handle(
        self, 
        message: StatusRequest, 
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


class CommandHandler(BaseHandler):
    """Handler for command execution requests."""
    
    @property
    def message_type(self) -> str:
        return "command"
    
    @property
    def request_model(self) -> type[BaseModel]:
        return CommandRequest
    
    async def handle(
        self, 
        message: CommandRequest, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle command request."""
        return CommandResponse(
            message="Command execution not yet implemented in WebSocket",
            command_data={"command": message.data.command, "parameters": message.data.parameters}
        )


class EventHandler(BaseHandler):
    """Handler for event publishing requests."""
    
    @property
    def message_type(self) -> str:
        return "event"
    
    @property
    def request_model(self) -> type[BaseModel]:
        return EventRequest
    
    async def handle(
        self, 
        message: EventRequest, 
        websocket: WebSocket, 
        session_id: SessionID
    ) -> Optional[WSResponse]:
        """Handle event request."""
        return EventResponse(
            message="Event publishing not yet implemented in WebSocket",
            event_data=message.data
        )