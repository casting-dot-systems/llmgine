"""
WebSocket handler registry.

This module provides the registry for managing and creating
WebSocket message handlers with server messaging support.
"""

from typing import Optional, TYPE_CHECKING
from llmgineAPI.websocket.base import WebSocketManager
from llmgineAPI.websocket.handlers import (
    PingHandler,
    StatusHandler,
    CreateSessionHandler,
)
from llmgineAPI.services.session_service import SessionService
from llmgineAPI.core.extensibility import global_handler_registry, ExtensibleAPIFactory

if TYPE_CHECKING:
    from llmgineAPI.websocket.connection_registry import ConnectionRegistry
    from llmgineAPI.core.messaging_api import MessagingAPIWithEvents


def create_websocket_manager(
    session_service: SessionService, 
    api_factory: Optional[ExtensibleAPIFactory] = None,
    connection_registry: Optional["ConnectionRegistry"] = None,
    messaging_api: Optional["MessagingAPIWithEvents"] = None
) -> WebSocketManager:
    """
    Create and configure a WebSocket manager with all handlers and server messaging support.
    
    Args:
        session_service: The session service instance
        api_factory: Optional API factory with custom handlers
        connection_registry: Optional connection registry for server messaging
        messaging_api: Optional messaging API for server-initiated messages
        
    Returns:
        Configured WebSocket manager with server messaging capabilities
    """
    # Use the handler registry from the API factory if provided, otherwise use global registry
    handler_registry = api_factory.handler_registry if api_factory else global_handler_registry
    
    # Create manager with the appropriate handler registry and messaging support
    manager = WebSocketManager(
        session_service=session_service,
        handler_registry=handler_registry,
        connection_registry=connection_registry,
        messaging_api=messaging_api
    )
    
    # Register core handlers manually (these aren't in the extensible registry)
    manager.register_handler(PingHandler(session_service))
    manager.register_handler(StatusHandler(session_service))
    manager.register_handler(CreateSessionHandler(session_service))
    
    # Set up messaging API connection with factory if available
    if api_factory and messaging_api:
        api_factory._set_messaging_api(messaging_api)
    
    return manager