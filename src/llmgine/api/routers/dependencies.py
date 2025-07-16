"""
Dependency injection for the LLMGine API.

This module provides dependency injection functions for API routes,
including service singletons and request validation.
"""

import re
from fastapi import Depends

from llmgine.api.services.engine_service import EngineService
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.api.utils.error_handler import (
    SessionIDValidationError,
    SessionNotFoundError,
    SessionInvalidError,
    handle_api_error,
    handle_unexpected_error
)
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID


def get_session_service() -> SessionService:
    """
    Get the session service singleton.
    
    Returns:
        SessionService: The global session service instance
    """
    return SessionService()


def get_engine_service() -> EngineService:
    """
    Get the engine service singleton.
    
    Returns:
        EngineService: The global engine service instance
    """
    return EngineService()


def get_message_bus() -> MessageBus:
    """
    Get the message bus singleton.
    
    Returns:
        MessageBus: The global message bus instance
    """
    return MessageBus()


def validate_session(
    session_id: str, 
    session_service: SessionService = Depends(get_session_service)
) -> SessionID:
    """
    Validate that a session exists and is in a valid state.
    
    Args:
        session_id: The session ID to validate
        session_service: The session service instance
        
    Returns:
        SessionID: The validated session ID
        
    Raises:
        SessionNotFoundError: When session doesn't exist
        SessionInvalidError: When session is in an invalid state
    """
    try:
        #TODO: check if session_id is a valid uuid
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', session_id):
            raise SessionIDValidationError(session_id)
        
        session = session_service.get_session(SessionID(session_id))
        if not session:
            raise SessionNotFoundError(session_id)
        
        if session.get_status() == SessionStatus.FAILED:
            raise SessionInvalidError(session_id, session.get_status().value)
        
        return SessionID(session_id)
        
    except (SessionNotFoundError, SessionInvalidError) as e:
        raise handle_api_error(e)
    
    except (SessionIDValidationError, Exception) as e:
        raise handle_unexpected_error(e)
