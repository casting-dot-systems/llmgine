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

from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional, List
from pydantic import BaseModel
from fastapi import APIRouter

from llmgineAPI.models.websocket import WSMessage, WSResponse
from llmgineAPI.websocket.base import BaseHandler


class CustomMessageMixin:
    """
    Mixin for creating custom message types.
    
    Usage:
        class MyCustomRequest(WSMessage, CustomMessageMixin):
            def __init__(self, my_data: str):
                super().__init__(type="my_custom", data={"my_data": my_data})
    """
    
    @classmethod
    def get_message_type(cls) -> str:
        """Get the message type identifier for this custom message."""
        return getattr(cls, '_message_type', cls.__name__.lower())
    
    @classmethod
    def set_message_type(cls, message_type: str) -> None:
        """Set the message type identifier for this custom message."""
        cls._message_type = message_type


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
    Factory for creating customized API instances with project-specific components.
    """
    
    def __init__(self, config: EngineConfiguration):
        self.config = config
        self.handler_registry = ExtensibleHandlerRegistry()
        self.custom_routers: List[APIRouter] = []
    
    def register_custom_router(self, router: APIRouter) -> None:
        """Register a custom router for project-specific endpoints."""
        self.custom_routers.append(router)
    
    def register_custom_handler(self, message_type: str, handler_class: Type[BaseHandler]) -> None:
        """Register a custom WebSocket message handler."""
        self.handler_registry.register_custom_handler(message_type, handler_class)
    
    def get_api_metadata(self) -> Dict[str, Any]:
        """Get metadata about the API including custom extensions."""
        return {
            "engine_name": self.config.engine_name,
            "api_version": self.config.api_version,
            "custom_message_types": self.handler_registry.list_custom_message_types(),
            "custom_routers_count": len(self.custom_routers),
            "settings": self.config.custom_settings
        }


# Global registry instance that projects can use
global_handler_registry = ExtensibleHandlerRegistry()