"""
WebSocket message models for the LLMGine API.

This module defines Pydantic models for WebSocket communication
including request/response models and error handling.

Usage:
    Basic WebSocket message structure:
    {
        "type": "message_type",
        "message_id": "unique-id-123",
        "data": { ... }
    }

    Response structure:
    {
        "type": "response_type",
        "message_id": "unique-id-123",  # Same ID as request
        "data": { ... }
    }

    Creating custom messages:
    ```python
    class CustomRequest(WSMessage):
        def __init__(self, custom_field: str, message_id: Optional[str] = None):
            super().__init__(
                type="custom_request",
                message_id=message_id or str(uuid.uuid4()),
                data={"custom_field": custom_field}
            )
    
    class CustomResponse(WSResponse):
        def __init__(self, result: str, message_id: Optional[str] = None):
            super().__init__(
                type="custom_response",
                message_id=message_id,
                data={"result": result}
            )
    ```

Request-Response Mapping:
    Each request generates a unique message_id (UUID4) if not provided.
    The corresponding response includes the same message_id for mapping.
    Frontend applications can use this to match responses to requests.

Message Types:
    - ping: Test WebSocket connection
    - status: Get session status
    - create_session: Create a new session

Error Handling:
    All errors return WSError with error code and message.
    WebSocket connections are automatically closed on critical errors.

Applications can create new request and response models by extending the WSMessage and WSResponse classes.
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel
from enum import Enum

class WSErrorCode(Enum):
    """WebSocket error codes."""
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    ENGINE_NOT_FOUND = "ENGINE_NOT_FOUND"
    INVALID_ENGINE_TYPE = "INVALID_ENGINE_TYPE"
    ENGINE_CREATION_FAILED = "ENGINE_CREATION_FAILED"
    INVALID_MESSAGE_TYPE = "INVALID_MESSAGE_TYPE"
    INVALID_JSON = "INVALID_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"

# ---------------------------------------------- Base Classes ----------------------------------------------
class WSMessage(BaseModel):
    """Base WebSocket message model."""
    type: str
    message_id: str
    data: Any


class WSResponse(BaseModel):
    """Base WebSocket response model."""
    type: str
    message_id: str
    data: Any


# ---------------------------------------------- Request Models ----------------------------------------------
class PingRequest(WSMessage):
    """Ping request to test connection."""
    class PingRequestData(BaseModel):
        timestamp: str
    
    type: str = "ping"
    message_id: str
    data: PingRequestData

class StatusRequest(WSMessage):
    """Request to get session status."""
    class StatusRequestData(BaseModel):
        session_id: str
    
    type: str = "status"
    message_id: str
    data: StatusRequestData

class CreateSessionRequest(WSMessage):
    """Request to create a new session."""
    class CreateSessionRequestData(BaseModel):
        app_id: str
    
    type: str = "create_session"
    message_id: str
    data: CreateSessionRequestData

# ---------------------------------------------- Response Models ----------------------------------------------
class WSError(WSResponse):
    """WebSocket error response model."""
    class WSErrorData(BaseModel):
        code: WSErrorCode
        message: str
        details: Optional[Dict[str, Any]] = None
    
    type: str = "error"
    message_id: str
    data: WSErrorData

class PingResponse(WSResponse):
    """Ping response."""
    class PingResponseData(BaseModel):
        timestamp: str
    
    type: str = "ping_res"
    message_id: str
    data: PingResponseData

# Response for initial websocket connection
class ConnectedResponse(WSResponse):
    """Connection established response."""
    class ConnectedResponseData(BaseModel):
        app_id: str
        status: str
    
    type: str = "connected"
    message_id: str
    data: ConnectedResponseData
       

class StatusResponse(WSResponse):
    """Status response."""
    class StatusResponseData(BaseModel):
        session_id: str
        status: str
        created_at: str
        last_interaction_at: str
    
    type: str = "status_res"
    message_id: str
    data: StatusResponseData

class CreateSessionResponse(WSResponse):
    """Create session response."""
    class CreateSessionResponseData(BaseModel):
        session_id: str
    
    type: str = "create_session_res"
    message_id: str
    data: CreateSessionResponseData



# Union types for validation
WSRequestMessage = Union[
    PingRequest,
    StatusRequest,
    CreateSessionRequest,
]

WSResponseMessage = Union[
    PingResponse,
    ConnectedResponse,
    StatusResponse,
    CreateSessionResponse,
    WSError
]