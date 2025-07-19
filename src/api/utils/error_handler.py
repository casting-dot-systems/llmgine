"""
Error handling utilities for the LLMGine API.

This module provides standardized error handling utilities to ensure
consistent error responses across all API endpoints.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException
from api.models.responses import ErrorDetail, ResponseStatus


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.context = context or {}
        super().__init__(message)

class SessionIDValidationError(APIError):
    """Raised when a session ID is invalid."""
    
    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_ID_INVALID",
            message=f"Session ID '{session_id}' is invalid, it should be a valid uuid",
            status_code=400,
            context={"session_id": session_id}
        )


class SessionNotFoundError(APIError):
    """Raised when a session is not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session '{session_id}' not found or has expired",
            status_code=404,
            context={"session_id": session_id}
        )


class SessionInvalidError(APIError):
    """Raised when a session is in an invalid state."""
    
    def __init__(self, session_id: str, current_status: str):
        super().__init__(
            code="SESSION_INVALID_STATE",
            message=f"Session '{session_id}' is in '{current_status}' state and cannot be used",
            status_code=400,
            context={"session_id": session_id, "current_status": current_status}
        )


class EngineNotFoundError(APIError):
    """Raised when an engine is not found."""
    
    def __init__(self, engine_id: str):
        super().__init__(
            code="ENGINE_NOT_FOUND",
            message=f"Engine '{engine_id}' not found",
            status_code=404,
            context={"engine_id": engine_id}
        )


class EngineConnectionError(APIError):
    """Raised when engine connection fails."""
    
    def __init__(self, engine_id: str, reason: str):
        super().__init__(
            code="ENGINE_CONNECTION_FAILED",
            message=f"Failed to connect to engine '{engine_id}': {reason}",
            status_code=400,
            context={"engine_id": engine_id, "reason": reason}
        )


class ResourceLimitError(APIError):
    """Raised when a resource limit is exceeded."""
    
    def __init__(self, resource_type: str, limit: int):
        super().__init__(
            code="RESOURCE_LIMIT_EXCEEDED",
            message=f"Maximum {resource_type} limit ({limit}) exceeded",
            status_code=429,
            context={"resource_type": resource_type, "limit": limit}
        )


class ValidationError(APIError):
    """Raised when request validation fails."""
    
    def __init__(self, field: str, message: str, value: Any = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=f"Validation failed for field '{field}': {message}",
            status_code=422,
            field=field,
            context={"value": value} if value is not None else None
        )


class CommandExecutionError(APIError):
    """Raised when command execution fails."""
    
    def __init__(self, command_id: str, reason: str):
        super().__init__(
            code="COMMAND_EXECUTION_FAILED",
            message=f"Command '{command_id}' execution failed: {reason}",
            status_code=500,
            context={"command_id": command_id, "reason": reason}
        )


class EventPublishError(APIError):
    """Raised when event publishing fails."""
    
    def __init__(self, event_id: str, reason: str):
        super().__init__(
            code="EVENT_PUBLISH_FAILED",
            message=f"Event '{event_id}' publishing failed: {reason}",
            status_code=500,
            context={"event_id": event_id, "reason": reason}
        )


def create_error_detail(error: APIError) -> ErrorDetail:
    """Create an ErrorDetail from an APIError."""
    return ErrorDetail(
        code=error.code,
        message=error.message,
        field=error.field,
        context=error.context
    )


def handle_api_error(error: APIError) -> HTTPException:
    """Convert an APIError to an HTTPException."""
    return HTTPException(
        status_code=error.status_code,
        detail={
            "status": ResponseStatus.FAILED.value,
            "error": create_error_detail(error).model_dump()
        }
    )


def handle_unexpected_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Handle unexpected errors with a generic response."""
    error_detail = ErrorDetail(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        context=context or {}
    )
    
    return HTTPException(
        status_code=500,
        detail={
            "status": ResponseStatus.FAILED.value,
            "error": error_detail.model_dump()
        }
    )