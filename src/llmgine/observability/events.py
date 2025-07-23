"""Event types specific to the observability system.

This module contains event types used primarily for observability purposes,
such as logging, tracing, and metrics.
"""

from dataclasses import dataclass
from enum import Enum

from llmgine.messages.events import Event


class LogLevel(Enum):
    """Standard log levels for observability system."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ObservabilityBaseEvent(Event):
    """Base class for all observability-related events.

    This is the parent class for all events that are specifically for
    observability purposes rather than domain logic. Handlers can register
    for this type to receive all observability events.
    """

    level: LogLevel = LogLevel.INFO
