"""
WebSocket handler registry.

This module provides the registry for managing and creating
WebSocket message handlers.
"""

from api.websocket.base import WebSocketManager
from api.websocket.handlers import (
    PingHandler,
    StatusHandler,
    CommandHandler,
    EventHandler
)
from api.services.session_service import SessionService


def create_websocket_manager(session_service: SessionService) -> WebSocketManager:
    """
    Create and configure a WebSocket manager with all handlers.
    
    Args:
        session_service: The session service instance
        
    Returns:
        Configured WebSocket manager
    """
    manager = WebSocketManager(session_service)
    
    # Register all handlers
    manager.register_handler(PingHandler(session_service))
    manager.register_handler(StatusHandler(session_service))
    manager.register_handler(CommandHandler(session_service))
    manager.register_handler(EventHandler(session_service))
    
    return manager