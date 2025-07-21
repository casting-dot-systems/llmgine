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

from typing import Any, Dict, Optional, Union, NewType
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

MESSAGE_ID = NewType("MESSAGE_ID", str)

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
    type: str = Field(..., description="Message type identifier")
    message_id: MESSAGE_ID = Field(default_factory=lambda: MESSAGE_ID(str(uuid.uuid4())), description="Unique message identifier for request-response mapping")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")


class WSResponse(BaseModel):
    """Base WebSocket response model."""
    type: str = Field(..., description="Response type identifier")
    message_id: MESSAGE_ID = Field(..., description="Message ID this response corresponds to (for request-response mapping)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response payload")


# ---------------------------------------------- Request Models ----------------------------------------------
class PingRequest(WSMessage):
    """Ping request to test connection."""
    def __init__(self, timestamp: str, message_id: Optional[MESSAGE_ID] = None):
        super().__init__(
            type="ping", 
            message_id=message_id or MESSAGE_ID(str(uuid.uuid4())),
            data={"timestamp": timestamp}
        )

class StatusRequest(WSMessage):
    """Request to get session status."""
    def __init__(self, message_id: Optional[MESSAGE_ID] = None):
        super().__init__(
            type="status",
            message_id=message_id or MESSAGE_ID(str(uuid.uuid4())),
            data={}
        )

class CreateSessionRequest(WSMessage):
    """Request to create a new session."""
    def __init__(self, app_id: str, message_id: Optional[MESSAGE_ID] = None):
        super().__init__(
            type="create_session",
            message_id=message_id or MESSAGE_ID(str(uuid.uuid4())),
            data={"app_id": app_id}
        )

# ---------------------------------------------- Response Models ----------------------------------------------
class WSError(WSResponse):
    """WebSocket error response model."""
    def __init__(self, code: WSErrorCode, message: str, message_id: MESSAGE_ID, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            type="error",
            message_id=message_id,
            data={"code": code.value, "message": message, "details": details}
        )

class PingResponse(WSResponse):
    """Ping response."""
    def __init__(self, message_id: MESSAGE_ID, timestamp: Optional[str] = None):
        super().__init__(
            type="ping_res",
            message_id=message_id,
            data={"timestamp": timestamp or datetime.now().isoformat()}
        )

# Response for initial websocket connection
class ConnectedResponse(WSResponse):
    """Connection established response."""
    def __init__(self, app_id: str, status: str, message_id: MESSAGE_ID):
        super().__init__(
            type="connected",
            message_id=message_id,
            data={"app_id": app_id, "status": status}
        )
       

class StatusResponse(WSResponse):
    """Status response."""
    def __init__(self, session_id: str, status: str, created_at: str, last_interaction_at: str, message_id: MESSAGE_ID):
        super().__init__(
            type="status_res",
            message_id=message_id,
            data={
                "session_id": session_id,
                "status": status,
                "created_at": created_at,
                "last_interaction_at": last_interaction_at
            }
        )

class CreateSessionResponse(WSResponse):
    """Create session response."""
    def __init__(self, session_id: str, message_id: MESSAGE_ID):
        super().__init__(
            type="create_session_res",
            message_id=message_id,
            data={"session_id": session_id}
        )



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