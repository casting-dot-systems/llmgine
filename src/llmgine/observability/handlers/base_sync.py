"""Base class for synchronous observability handlers."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from llmgine.messages.events import Event


class SyncObservabilityHandler(ABC):
    """Base class for synchronous observability handlers.
    
    This is the new base class that handlers should implement to work with
    the standalone ObservabilityManager. It uses synchronous methods to avoid
    blocking the message bus.
    """
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the handler with optional configuration."""
        pass
    
    @abstractmethod
    def handle(self, event: Event) -> None:
        """Process an incoming event synchronously.
        
        Args:
            event: The event to process
        """
        pass
    
    def event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event to a dictionary representation for logging.
        
        Args:
            event: The event to convert
            
        Returns:
            Dictionary representation of the event
        """
        # Use to_dict method if available
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                pass
        
        # Try dataclasses.asdict
        try:
            from dataclasses import asdict
            return asdict(event)
        except (TypeError, ImportError):
            pass
        
        # Use __dict__
        if hasattr(event, "__dict__"):
            return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
        
        # Fallback
        return {"event_repr": repr(event)}
    
    def __repr__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}()"
