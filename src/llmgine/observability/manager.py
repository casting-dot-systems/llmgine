"""Standalone observability manager - no message bus dependency."""

import logging
from typing import List

from llmgine.messages.events import Event

logger = logging.getLogger(__name__)


class ObservabilityHandler:
    """Base interface for observability handlers.
    
    Note: This is synchronous to avoid blocking the message bus.
    """
    
    def handle(self, event: Event) -> None:
        """Handle an event for observability purposes.
        
        Args:
            event: The event to observe
        """
        raise NotImplementedError


class ObservabilityManager:
    """Standalone observability manager - no message bus dependency.
    
    This manager is called directly by the message bus to observe events
    without creating circular dependencies or additional event overhead.
    """
    
    def __init__(self) -> None:
        """Initialize the observability manager."""
        self._handlers: List[ObservabilityHandler] = []
        self._enabled = True
    
    def register_handler(self, handler: ObservabilityHandler) -> None:
        """Register an observability handler.
        
        Args:
            handler: The handler to register
        """
        if handler not in self._handlers:
            self._handlers.append(handler)
            logger.debug(f"Registered observability handler: {handler.__class__.__name__}")
    
    def unregister_handler(self, handler: ObservabilityHandler) -> None:
        """Unregister an observability handler.
        
        Args:
            handler: The handler to unregister
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            logger.debug(f"Unregistered observability handler: {handler.__class__.__name__}")
    
    def observe_event(self, event: Event) -> None:
        """Called directly by message bus - no event publishing.
        
        Args:
            event: The event to observe
        """
        if not self._enabled:
            return
            
        for handler in self._handlers:
            try:
                handler.handle(event)
            except Exception as e:
                # Log but don't propagate errors to avoid disrupting the message bus
                logger.error(
                    f"Error in observability handler {handler.__class__.__name__}: {e}",
                    exc_info=True
                )
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable observability.
        
        Args:
            enabled: Whether observability should be enabled
        """
        self._enabled = enabled
        logger.info(f"Observability {'enabled' if enabled else 'disabled'}")
    
    def clear_handlers(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()
        logger.debug("Cleared all observability handlers")
    
    @property
    def handler_count(self) -> int:
        """Get the number of registered handlers."""
        return len(self._handlers)
