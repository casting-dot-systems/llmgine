"""File handler for logging observability events to JSONL."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from llmgine.observability.events import ObservabilityBaseEvent, EventLogWrapper
from llmgine.observability.handlers.base import ObservabilityEventHandler

logger = logging.getLogger(__name__)


class FileEventHandler(ObservabilityEventHandler):
    """Logs all received observability events to a JSONL file."""

    def __init__(self, log_dir: str = "logs", filename: Optional[str] = None, **kwargs: Any):
        """Initialize the JSON file handler.

        Args:
            log_dir: Directory to write log files.
            filename: Optional specific filename (if None, uses timestamp).
        """
        super().__init__(**kwargs)
        self.log_dir = Path(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        if filename:
            self.log_file = self.log_dir / filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = self.log_dir / f"events_{timestamp}.jsonl"

        self._file_lock = asyncio.Lock()
        logger.info(f"FileEventHandler initialized. Logging events to: {self.log_file}")

    async def handle(self, event: EventLogWrapper) -> None:
        """Handle the wrapped event by writing its original data to the log file."""
        if not isinstance(event, EventLogWrapper):
            logger.warning(f"FileEventHandler received non-wrapper event: {type(event)}. Skipping.")
            return

        try:
            log_data = event.original_event_data
            
            log_data['wrapper_id'] = event.id
            log_data['wrapper_timestamp'] = event.timestamp
            log_data['original_event_type'] = event.original_event_type

            async with self._file_lock:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_data, default=str, indent=4) + "\n")
        except Exception as e:
            logger.error(f"Error writing wrapped event data to file: {e}", exc_info=True)

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event (dataclass or object) to a dictionary for serialization.
        Handles nested objects, dataclasses, and Enums.
        """
        if hasattr(event, "to_dict") and callable(event.to_dict):
            try:
                return event.to_dict()
            except Exception:
                logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)
                # Fall through

        try:
            # Use dataclasses.asdict with a factory to handle nested conversion
            return asdict(event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x})
        except TypeError:
            pass # Not a dataclass

        if hasattr(event, "__dict__"):
            return {k: self._convert_value(v) for k, v in event.__dict__.items()}

        logger.warning(f"Could not serialize event of type {type(event)} to dict, using repr().")
        return {"event_repr": repr(event)}

    def _convert_value(self, value: Any) -> Any:
        """Helper for _event_to_dict to handle nested structures and special types."""
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return {k: self._convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._convert_value(item) for item in value]
        elif hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
             # Recursively convert nested objects/dataclasses
             return self._event_to_dict(value)
        else:
            # Attempt to convert other types to string as a fallback
            return str(value) 