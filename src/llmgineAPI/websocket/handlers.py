"""
Concrete WebSocket message handlers.

This module implements specific handlers for each supported
WebSocket message type.

Handlers must return a WSResponse object, which contains the message_id of the request.
"""

from typing import Optional, Dict, Any
import uuid
from fastapi import WebSocket
import logging

from llmgine.llm import SessionID
from llmgineAPI.websocket.base import BaseHandler
from llmgineAPI.models.websocket import (
    PingRequest, PingResponse,
    StatusRequest, StatusResponse,
    CreateSessionRequest, CreateSessionResponse,
    WSMessage,
    WSResponse, WSError, WSErrorCode
)

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
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle ping request."""
        try:
            req = PingRequest.model_validate(message)
        except Exception as e:
            logger.error(f"Error handling ping request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling ping request: {e}",
                    details=None
                )
            )
        timestamp = req.data.timestamp
        return PingResponse(
            type="ping_res",
            message_id=req.message_id,
            data=PingResponse.PingResponseData(timestamp=timestamp)
        )


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
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle status request."""
        try:
            req = StatusRequest.model_validate(message)
        except Exception as e:
            logger.error(f"Error handling status request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling status request: {e}",
                    details=None
                )
            )
        
        session_id = req.data.session_id

        if not session_id:
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message="session_id is required for status request",
                    details=None
                )
            )
        session = self.session_service.get_session(SessionID(session_id))
        if not session:
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.SESSION_NOT_FOUND,
                    message="Session no longer exists",
                    details=None
                )
            )
        
        return StatusResponse(
            type="status_res",
            message_id=req.message_id,
            data=StatusResponse.StatusResponseData(
                session_id=str(session_id),
                status=session.get_status().value,
                created_at=session.created_at,
                last_interaction_at=session.last_interaction_at
            )
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
        message: Dict[str, Any], 
        websocket: WebSocket, 
    ) -> Optional[WSResponse]:
        """Handle create session request."""
        from llmgineAPI.routers.websocket import register_session_to_app
        
        try:
            req = CreateSessionRequest.model_validate(message)
        except Exception as e:
            logger.error(f"Error handling create session request: {e}")
            return WSError(
                type="error",
                message_id=message.get("message_id", str(uuid.uuid4())),
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message=f"Error handling create session request: {e}",
                    details=None
                )
            )
        
        app_id = req.data.app_id
        if not app_id:
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.VALIDATION_ERROR,
                    message="app_id is required for session creation",
                    details=None
                )
            )
        
        # Create new session
        new_session_id = self.session_service.create_session()
        
        if new_session_id is None:
            return WSError(
                type="error",
                message_id=req.message_id,
                data=WSError.WSErrorData(
                    code=WSErrorCode.ENGINE_CREATION_FAILED,
                    message="Failed to create session - maximum sessions reached",
                    details=None
                )
            )
        
        # Register the session to the app_id
        register_session_to_app(app_id, new_session_id)
        
        return CreateSessionResponse(
            type="create_session_res",
            message_id=req.message_id,
            data=CreateSessionResponse.CreateSessionResponseData(
                session_id=str(new_session_id)
            )
        )
