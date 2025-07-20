"""
WebSocket handler registry.

This module provides the registry for managing and creating
WebSocket message handlers.
"""

from typing import Optional
from llmgineAPI.websocket.base import WebSocketManager
from llmgineAPI.websocket.handlers import (
    PingHandler,
    StatusHandler,
    CommandHandler,
    EventHandler
)
from llmgineAPI.services.session_service import SessionService
from llmgineAPI.core.extensibility import global_handler_registry, ExtensibleAPIFactory


def create_websocket_manager(
    session_service: SessionService, 
    api_factory: Optional[ExtensibleAPIFactory] = None
) -> WebSocketManager:
    """
    Create and configure a WebSocket manager with all handlers.
    
    Args:
        session_service: The session service instance
        api_factory: Optional API factory with custom handlers
        
    Returns:
        Configured WebSocket manager
    """
    # Use the handler registry from the API factory if provided, otherwise use global registry
    handler_registry = api_factory.handler_registry if api_factory else global_handler_registry
    
    # Create manager with the appropriate handler registry
    manager = WebSocketManager(session_service, handler_registry)
    
    # Register core handlers manually (these aren't in the extensible registry)
    manager.register_handler(PingHandler(session_service))
    manager.register_handler(StatusHandler(session_service))
    manager.register_handler(CommandHandler(session_service))
    manager.register_handler(EventHandler(session_service))
    
    return manager