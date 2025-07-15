"""
Dependency injection for the LLMGine API.

This module provides dependencies for the API routes.
"""

from fastapi import Depends, HTTPException

from llmgine.api.services.engine_service import EngineService
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID


def get_session_service() -> SessionService:
    """Get the session service singleton"""
    return SessionService()

def get_engine_service() -> EngineService:
    """Get the engine service singleton"""
    return EngineService()

def get_message_bus() -> MessageBus:
    """Get the message bus singleton"""
    return MessageBus()

def validate_session(session_id: str, session_service: SessionService = Depends(get_session_service)) -> SessionID:
    """Validate that the session exists and is active"""
    session = session_service.get_session(SessionID(session_id))
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    if session.get_status() == SessionStatus.FAILED:
        raise HTTPException(status_code=400, detail=f"Session {session_id} has failed status")
    
    return SessionID(session_id)