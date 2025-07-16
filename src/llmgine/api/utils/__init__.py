"""
API utilities package.

This package contains utility modules for the LLMGine API.
"""

from .error_handler import (
    APIError,
    SessionNotFoundError,
    SessionInvalidError,
    EngineNotFoundError,
    EngineConnectionError,
    ResourceLimitError,
    ValidationError,
    CommandExecutionError,
    EventPublishError,
    create_error_detail,
    handle_api_error,
    handle_unexpected_error
)

__all__ = [
    'APIError',
    'SessionNotFoundError',
    'SessionInvalidError',
    'EngineNotFoundError',
    'EngineConnectionError',
    'ResourceLimitError',
    'ValidationError',
    'CommandExecutionError',
    'EventPublishError',
    'create_error_detail',
    'handle_api_error',
    'handle_unexpected_error'
]