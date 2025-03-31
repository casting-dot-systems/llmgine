"""Events used in the observability system.

These events provide a structured way to represent logs, metrics, and traces.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid


class LogLevel(Enum):
    """Standard log levels."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ObservabilityBaseEvent:
    """Base class for all observability events."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: Optional[str] = None


@dataclass
class LogEvent(ObservabilityBaseEvent):
    """Event for logs."""
    
    level: LogLevel = LogLevel.INFO
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

class ToolManagerLogEvent(LogEvent):
    """Event for tool manager logs."""

@dataclass
class Metric:
    """A metric measurement."""
    
    name: str
    value: Union[int, float]
    unit: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricEvent(ObservabilityBaseEvent):
    """Event for metric reporting."""
    
    metrics: List[Metric] = field(default_factory=list)


@dataclass
class SpanContext:
    """Context for distributed tracing."""
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None


@dataclass
class TraceEvent(ObservabilityBaseEvent):
    """Event for distributed tracing."""
    
    name: str = ""
    span_context: SpanContext = field(default_factory=SpanContext)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"

# --- Define EventLogWrapper --- 
@dataclass(kw_only=True)
class EventLogWrapper(ObservabilityBaseEvent):
    """Wraps any other event for generic file logging."""
    original_event_type: str
    original_event_data: Dict[str, Any]