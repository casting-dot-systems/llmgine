"""
WebSocket message models for the LLMGine API.

This module defines Pydantic models for WebSocket communication
including request/response models and error handling.

Applications can create new request and response models by extending the WSMessage and WSResponse classes.
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WSErrorCode(Enum):
    """WebSocket error codes."""
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INVALID_ENGINE_TYPE = "INVALID_ENGINE_TYPE"
    ENGINE_CREATION_FAILED = "ENGINE_CREATION_FAILED"
    INVALID_MESSAGE_TYPE = "INVALID_MESSAGE_TYPE"
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"

# ---------------------------------------------- Base Classes ----------------------------------------------
class WSMessage(BaseModel):
    """Base WebSocket message model."""
    type: str = Field(..., description="Message type identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")


class WSResponse(BaseModel):
    """Base WebSocket response model."""
    type: str = Field(..., description="Response type identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response payload")


# ---------------------------------------------- Request Models ----------------------------------------------
class PingRequest(WSMessage):
    """Ping request to test connection."""
    def __init__(self, timestamp: str = Field(..., description="Timestamp of the ping")):
        super().__init__(type="ping", data={"timestamp": timestamp})

class GetEngineTypesRequest(WSMessage):
    """Request to get available engine types."""
    def __init__(self):
        super().__init__(type="get_engine_types", data={})

class LinkEngineRequest(WSMessage):
    """Request to link an engine to the session."""
    def __init__(self, engine_type: str):
        super().__init__(type="link_engine", data={"engine_type": engine_type})

class StatusRequest(WSMessage):
    """Request to get session status."""
    def __init__(self):
        super().__init__(type="status", data={})

class CommandRequest(WSMessage):
    """Request to execute a command."""
    def __init__(self, command: str, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(type="command", data={"command": command, "parameters": parameters})

class EventRequest(WSMessage):
    """Request to publish an event."""
    def __init__(self, event_type: str, event_payload: Optional[Dict[str, Any]] = None):
        super().__init__(type="event", data={"event_type": event_type, "event_payload": event_payload})


# ---------------------------------------------- Response Models ----------------------------------------------
class WSError(WSResponse):
    """WebSocket error response model."""
    def __init__(self, code: WSErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(type="error", data={"code": code.value, "message": message, "details": details})

class PingResponse(WSResponse):
    """Ping response."""
    def __init__(self, timestamp: Optional[str] = None):
        super().__init__(type="ping_res", data={"timestamp": timestamp or datetime.now().isoformat()})
    
class ConnectedResponse(WSResponse):
    """Connection established response."""
    def __init__(self, session_id: str, status: str):
        super().__init__(type="connected", data={"session_id": session_id, "status": status})
    
class GetEngineTypesResponse(WSResponse):
    """Engine types response."""
    def __init__(self, engine_types: list[str]):
        super().__init__(type="get_engine_types_res", data={"engine_types": engine_types})
    
class LinkEngineResponse(WSResponse):
    """Link engine response."""
    def __init__(self, engine_id: str):
        super().__init__(type="link_engine_res", data={"engine_id": engine_id})
    

class StatusResponse(WSResponse):
    """Status response."""
    def __init__(self, session_id: str, status: str, created_at: datetime, last_interaction_at: datetime):
        super().__init__(type="status_res", data={"session_id": session_id, "status": status, "created_at": created_at.isoformat(), "last_interaction_at": last_interaction_at.isoformat()})
    

class CommandResponse(WSResponse):
    """Command response."""
    def __init__(self, message: str, command_data: Optional[Dict[str, Any]] = None, result: Optional[Any] = None):
        super().__init__(type="command_res", data={"message": message, "command_data": command_data, "result": result})
    
class EventResponse(WSResponse):
    """Event response."""
    def __init__(self, message: str, event_data: Optional[Dict[str, Any]] = None, event_id: Optional[str] = None):
        super().__init__(type="event_res", data={"message": message, "event_data": event_data, "event_id": event_id})


# Union types for validation
WSRequestMessage = Union[
    PingRequest,
    GetEngineTypesRequest,
    LinkEngineRequest,
    StatusRequest,
    CommandRequest,
    EventRequest
]

WSResponseMessage = Union[
    PingResponse,
    ConnectedResponse,
    GetEngineTypesResponse,
    LinkEngineResponse,
    StatusResponse,
    CommandResponse,
    EventResponse,
    WSError
]