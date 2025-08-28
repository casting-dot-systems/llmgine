"""Default handler for unhandled events in the message bus.

This module provides a default handler that logs all events that don't have
any registered handlers to a JSON file for debugging and monitoring purposes.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from llmgine.messages.events import Event

logger = logging.getLogger(__name__)


class DefaultEventHandler:
    """Default handler for events that have no registered handlers.
    
    This handler logs all unhandled events to a JSON file in the logs directory
    for debugging and monitoring purposes.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        """Initialize the default handler.
        
        Args:
            logs_dir: Directory to store log files
        """
        self.logs_dir = Path(logs_dir)
        self.log_file = self.logs_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize log file if it doesn't exist
        if not self.log_file.exists():
            with open(self.log_file, 'w') as f:
                json.dump([], f)
    
    async def handle_unhandled_event(self, event: Event) -> None:
        """Handle an event that has no registered handlers.
        
        Args:
            event: The unhandled event to log
        """
        try:
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": type(event).__name__,
                "event_id": event.event_id,
                "session_id": str(event.session_id),
                "event_timestamp": event.timestamp,
                "event_data": self._serialize_event_data(event),
                "metadata": event.metadata
            }
            
            # Read existing logs
            existing_logs = []
            if self.log_file.exists():
                try:
                    with open(self.log_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            existing_logs = json.loads(content)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # Add new entry
            existing_logs.append(log_entry)
            
            # Keep only the last 1000 entries to prevent file from growing too large
            if len(existing_logs) > 1000:
                existing_logs = existing_logs[-1000:]
            
            # Write back to file
            with open(self.log_file, 'w') as f:
                json.dump(existing_logs, f, indent=2, default=str)
            
            logger.info(
                f"Logged unhandled event: {type(event).__name__} "
                f"(ID: {event.event_id}, Session: {event.session_id})"
            )
            
        except Exception as e:
            logger.error(f"Failed to log unhandled event {type(event).__name__}: {e}")
    
    def _serialize_event_data(self, event: Event) -> Dict[str, Any]:
        """Serialize event data for JSON logging.
        
        Args:
            event: The event to serialize
            
        Returns:
            Dictionary representation of the event data
        """
        try:
            # Get all attributes except the base Event attributes
            event_dict = event.model_dump()
            
            # Remove standard Event fields to avoid duplication
            for field in ['event_id', 'timestamp', 'metadata', 'session_id']:
                event_dict.pop(field, None)
            
            return event_dict
            
        except Exception as e:
            logger.warning(f"Failed to serialize event data for {type(event).__name__}: {e}")
            return {"serialization_error": str(e)}
    
    def get_unhandled_events_count(self) -> int:
        """Get the count of unhandled events logged.
        
        Returns:
            Number of unhandled events logged
        """
        try:
            if not self.log_file.exists():
                return 0
            
            with open(self.log_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return 0
                logs = json.loads(content)
                return len(logs)
                
        except Exception as e:
            logger.error(f"Failed to get unhandled events count: {e}")
            return 0
    
    def get_recent_unhandled_events(self, limit: int = 10) -> list:
        """Get recent unhandled events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent unhandled events
        """
        try:
            if not self.log_file.exists():
                return []
            
            with open(self.log_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                logs = json.loads(content)
                return logs[-limit:]
                
        except Exception as e:
            logger.error(f"Failed to get recent unhandled events: {e}")
            return []


# Global default handler instance
_default_handler = None


def get_default_handler() -> DefaultEventHandler:
    """Get the global default handler instance.
    
    Returns:
        The global DefaultEventHandler instance
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = DefaultEventHandler()
    return _default_handler