"""Synchronous console handler for printing event information."""

import logging
from typing import Any

from llmgine.messages.events import Event
from llmgine.observability.handlers.base_sync import SyncObservabilityHandler

logger = logging.getLogger(__name__)


class SyncConsoleEventHandler(SyncObservabilityHandler):
    """Synchronous handler that prints event summaries to console using standard logging."""
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the console handler."""
        super().__init__(**kwargs)
    
    def handle(self, event: Event) -> None:
        """Process the event and print relevant information to the console logger."""
        event_type = type(event).__name__
        
        # Default representation for standard events
        log_level = logging.INFO
        message = f"[EVENT] {event_type}, ID={event.event_id}"
        
        try:
            # Add session_id to message if available
            if hasattr(event, "session_id") and event.session_id:
                message += f", Session={event.session_id}"
            
            # Add any other relevant attributes
            if hasattr(event, "metadata") and event.metadata:
                # Extract a few key metadata items to display
                meta_display = []
                for key in ["source", "command_type", "event_type"]:
                    if key in event.metadata:
                        meta_display.append(f"{key}={event.metadata[key]}")
                
                if meta_display:
                    message += f" [{', '.join(meta_display)}]"
        
        except Exception as e:
            logger.error(
                f"Error formatting event in SyncConsoleEventHandler: {e}", exc_info=True
            )
            # Fall back to default message
        
        # Log the formatted message using the standard logger
        logger.log(log_level, message)
