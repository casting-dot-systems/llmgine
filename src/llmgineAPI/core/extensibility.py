"""
Extensibility framework for custom engines and message types.

This module provides base classes and patterns that other projects
can use to extend the API with custom functionality.

Architecture:
    The extensibility framework follows a plugin-style architecture where:
    1. Projects define custom message types using CustomMessageMixin
    2. Projects create handlers extending BaseHandler
    3. ExtensibleAPIFactory registers and manages custom components
    4. The main app integrates custom functionality seamlessly

Usage Example:
    ```python
    # 1. Define custom message
    class CustomRequest(WSMessage, CustomMessageMixin):
        def __init__(self, data: str):
            super().__init__(type="custom", data={"data": data})
    
    # 2. Create handler
    class CustomHandler(BaseHandler):
        @property
        def message_type(self) -> str:
            return "custom"
        
        @property
        def request_model(self) -> type[WSMessage]:
            return CustomRequest
        
        async def handle(self, message, websocket, session_id):
            # Custom logic here
            return CustomResponse(...)
    
    # 3. Register with factory
    config = EngineConfiguration(engine_name="MyEngine")
    factory = ExtensibleAPIFactory(config)
    factory.register_custom_handler("custom", CustomHandler)
    
    # 4. Create app with extensions
    app = create_app(api_factory=factory)
    ```

Key Components:
    - CustomMessageMixin: Mixin for creating custom message types
    - ExtensibleHandlerRegistry: Registry for managing handlers
    - EngineConfiguration: Base configuration with extensibility
    - ExtensibleAPIFactory: Factory for creating customized APIs

Thread Safety:
    All registry operations are thread-safe. Handler instances are created
    per WebSocket manager to avoid shared state issues.
"""

from typing import Dict, Type, Any, Optional, List, Callable
from pydantic import BaseModel
from fastapi import APIRouter

from llmgineAPI.websocket.base import BaseHandler

class ExtensibleHandlerRegistry:
    """
    Registry for custom message handlers that can be extended by external projects.
    """
    
    def __init__(self):
        self._handlers: Dict[str, Type[BaseHandler]] = {}
        self._custom_handlers: Dict[str, Type[BaseHandler]] = {}
    
    def register_core_handler(self, message_type: str, handler_class: Type[BaseHandler]) -> None:
        """Register a core handler (used by the base API)."""
        self._handlers[message_type] = handler_class
    
    def register_custom_handler(self, message_type: str, handler_class: Type[BaseHandler]) -> None:
        """Register a custom handler (used by extending projects)."""
        self._custom_handlers[message_type] = handler_class
    
    def get_handler(self, message_type: str) -> Optional[Type[BaseHandler]]:
        """Get handler for a message type, checking custom handlers first."""
        return self._custom_handlers.get(message_type) or self._handlers.get(message_type)
    
    def get_all_handlers(self) -> Dict[str, Type[BaseHandler]]:
        """Get all registered handlers (core + custom)."""
        return {**self._handlers, **self._custom_handlers}
    
    def list_custom_message_types(self) -> List[str]:
        """List all custom message types."""
        return list(self._custom_handlers.keys())


class EngineConfiguration(BaseModel):
    """
    Base configuration model for engine-specific settings.
    
    Projects can extend this to add their own configuration fields.
    """
    
    engine_name: str
    api_version: str = "1.0.0"
    custom_settings: Dict[str, Any] = {}
    
    class Config:
        extra = "allow"  # Allow additional fields


class ExtensibleAPIFactory:
    """
    Factory for creating customized API instances with project-specific components
    and server messaging capabilities.
    """
    
    def __init__(self, config: EngineConfiguration):
        self.config = config
        self.handler_registry = ExtensibleHandlerRegistry()
        self.custom_routers: List[APIRouter] = []
        self._messaging_api: Optional[Any] = None  # Will be set during app creation
        self._connection_callbacks: Dict[str, List[Callable]] = {
            'connect': [],
            'disconnect': []
        }
        self._session_callbacks: Dict[str, List[Callable]] = {
            'session_created': [],
            'session_destroyed': []
        }
    
    def register_custom_router(self, router: APIRouter) -> None:
        """Register a custom router for project-specific endpoints."""
        self.custom_routers.append(router)
    
    def register_custom_handler(self, message_type: str, handler_class: Type[BaseHandler]) -> None:
        """Register a custom WebSocket message handler."""
        self.handler_registry.register_custom_handler(message_type, handler_class)
    
    def register_connection_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for connection events.
        
        Args:
            event: 'connect' or 'disconnect'
            callback: Async function to call with app_id
        """
        if event in self._connection_callbacks:
            self._connection_callbacks[event].append(callback)
            # If messaging API is already available, register with it
            if self._messaging_api and hasattr(self._messaging_api, 'register_connection_callback'):
                self._messaging_api.register_connection_callback(event, callback)
        else:
            raise ValueError(f"Unknown connection event: {event}")
    
    def register_session_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for session events.
        
        Args:
            event: 'session_created' or 'session_destroyed'  
            callback: Async function to call with app_id and session_id
        """
        if event in ['session_created', 'session_destroyed']:
            self._session_callbacks[event].append(callback)
            # If messaging API is already available, register with it
            if self._messaging_api and hasattr(self._messaging_api, 'register_session_callback'):
                self._messaging_api.register_session_callback(event, callback)
        else:
            raise ValueError(f"Unknown session event: {event}")
    
    def _set_messaging_api(self, messaging_api: Any) -> None:
        """
        Set the messaging API instance (called during app initialization).
        
        Args:
            messaging_api: The messaging API instance
        """
        self._messaging_api = messaging_api
        
        # Register any callbacks that were registered before the API was available
        if hasattr(messaging_api, 'register_connection_callback'):
            for event, callbacks in self._connection_callbacks.items():
                for callback in callbacks:
                    messaging_api.register_connection_callback(event, callback)
        
        if hasattr(messaging_api, 'register_session_callback'):
            for event, callbacks in self._session_callbacks.items():
                for callback in callbacks:
                    messaging_api.register_session_callback(event, callback)
    
    def get_messaging_api(self) -> Any:
        """
        Get the messaging API for sending server-initiated messages.
        
        Returns:
            The messaging API instance
            
        Raises:
            RuntimeError: If messaging API not initialized
        """
        if not self._messaging_api:
            raise RuntimeError("Messaging API not initialized. Create app first.")
        return self._messaging_api
    
    async def send_to_app(self, app_id: str, message_type: str, data: Dict[str, Any]) -> None:
        """
        Send message to specific app (convenience method).
        
        Args:
            app_id: Target app identifier
            message_type: Type of message to send
            data: Message payload
        """
        messaging_api = self.get_messaging_api()
        await messaging_api.send_to_app(app_id, message_type, data)
    
    async def send_to_app_and_wait(
        self, 
        app_id: str, 
        message_type: str, 
        data: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Any:
        """
        Send message to specific app and wait for response.
        
        Args:
            app_id: Target app identifier
            message_type: Type of message to send
            data: Message payload
            timeout: Timeout in seconds
            
        Returns:
            Response message
        """
        messaging_api = self.get_messaging_api()
        return await messaging_api.send_to_app_and_wait(app_id, message_type, data, timeout)
    
    async def send_to_session(
        self, 
        session_id: Any, 
        message_type: str, 
        data: Dict[str, Any]
    ) -> None:
        """
        Send message to specific session.
        
        Args:
            session_id: Target session identifier
            message_type: Type of message to send
            data: Message payload
        """
        messaging_api = self.get_messaging_api()
        await messaging_api.send_to_session(session_id, message_type, data)
    
    async def broadcast(
        self, 
        message_type: str, 
        data: Dict[str, Any], 
        exclude_apps: Optional[List[str]] = None
    ) -> int:
        """
        Broadcast message to all connected apps.
        
        Args:
            message_type: Type of message to send
            data: Message payload
            exclude_apps: Optional list of app IDs to exclude
            
        Returns:
            Number of apps message was sent to
        """
        messaging_api = self.get_messaging_api()
        exclude_set = set(exclude_apps) if exclude_apps else None
        return await messaging_api.broadcast(message_type, data, exclude_set)
    
    def get_connected_apps(self) -> List[str]:
        """
        Get list of all connected app IDs.
        
        Returns:
            List of connected app identifiers
        """
        if not self._messaging_api:
            return []
        return self._messaging_api.get_connected_apps()
    
    def is_app_connected(self, app_id: str) -> bool:
        """
        Check if an app is currently connected.
        
        Args:
            app_id: The app identifier to check
            
        Returns:
            True if app is connected, False otherwise
        """
        if not self._messaging_api:
            return False
        return self._messaging_api.is_app_connected(app_id)
    
    def get_api_metadata(self) -> Dict[str, Any]:
        """Get metadata about the API including custom extensions."""
        metadata = {
            "engine_name": self.config.engine_name,
            "api_version": self.config.api_version,
            "custom_message_types": self.handler_registry.list_custom_message_types(),
            "custom_routers_count": len(self.custom_routers),
            "settings": self.config.custom_settings,
            "messaging_api_available": self._messaging_api is not None,
            "connection_callbacks_registered": {
                event: len(callbacks) for event, callbacks in self._connection_callbacks.items()
            },
            "session_callbacks_registered": {
                event: len(callbacks) for event, callbacks in self._session_callbacks.items()
            }
        }
        
        if self._messaging_api:
            try:
                metadata["connected_apps"] = len(self.get_connected_apps())
            except:
                metadata["connected_apps"] = 0
        
        return metadata


# Global registry instance that projects can use
global_handler_registry = ExtensibleHandlerRegistry()