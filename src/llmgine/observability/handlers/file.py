"""File handler for logging events to JSONL."""

import asyncio
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from llmgine.messages.events import Event
from llmgine.observability.handlers.base import ObservabilityEventHandler

logger = logging.getLogger(__name__)


class FileEventHandler(ObservabilityEventHandler):
    """Logs all received events to a JSONL file."""

    def __init__(
        self, log_dir: str = "logs", filename: Optional[str] = None, **kwargs: Any
    ):
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

    async def handle(self, event: Event) -> None:
        """Handle the event by writing its data directly to the log file."""
        try:
            # Convert the event to dictionary for serialization
            log_data = self._event_to_dict(event)

            # Add event metadata
            log_data["event_type"] = type(event).__name__

            # Make sure parent directory exists
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            async with self._file_lock:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_data, default=str, indent=4) + "\n")
        except Exception as e:
            logger.error(f"Error writing event data to file: {e}", exc_info=True)

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event (dataclass or object) to a dictionary for serialization.
        Handles nested objects, dataclasses, and Enums.
        """
        # if hasattr(event, "to_dict") and callable(event.to_dict):
        #     try:
        #         return event.to_dict()
        #     except Exception:
        #         logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)
        #         # Fall through

        try:
            # Use dataclasses.asdict with a factory to handle nested conversion
            return asdict(
                event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x}
            )
        except TypeError:
            pass  # Not a dataclass

        if hasattr(event, "__dict__"):
            return {k: self._convert_value(v) for k, v in event.__dict__.items()}

        logger.warning(
            f"Could not serialize event of type {type(event)} to dict, using repr()."
        )
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
        elif hasattr(value, "__dataclass_fields__"):
            # Only handle dataclasses to avoid recursive conversion loops
            try:
                return self._event_to_dict(value)
            except Exception:
                return str(value)
        else:
            # Fallback for other objects: use string representation to prevent infinite recursion
            return str(value)
