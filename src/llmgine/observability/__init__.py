"""
Observability module for LLMgine
"""

import logging
import json
import time
import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid
import threading
from dataclasses import dataclass


@dataclass
class LogEvent:
    """Event for logging"""
    message: str
    event_type: str
    metadata: Optional[Dict[str, Any]] = None


class Imprint:
    """Mock class for recording events"""
    def __init__(self):
        self.events = []
        
    def emit(self, event: LogEvent):
        """Record an event"""
        self.events.append(event)
        
    def get_events(self):
        """Get all recorded events"""
        return self.events
        
    def clear(self):
        """Clear all recorded events"""
        self.events = []


# Global imprint instance
imprint = Imprint()


class Metrics:
    """Collects and stores metrics"""

    def __init__(self):
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def record(
        self, metric_name: str, value: Any, tags: Optional[Dict[str, str]] = None
    ):
        """Record a metric value"""
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []

            self.metrics[metric_name].append(
                {"value": value, "timestamp": time.time(), "tags": tags or {}}
            )

    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics matching the filters"""
        with self._lock:
            if metric_name is not None:
                if metric_name not in self.metrics:
                    return {}
                metrics_to_check = {metric_name: self.metrics[metric_name]}
            else:
                metrics_to_check = self.metrics.copy()

            result = {}

            for name, values in metrics_to_check.items():
                filtered_values = []

                for value in values:
                    # Check time range
                    if start_time is not None and value["timestamp"] < start_time:
                        continue
                    if end_time is not None and value["timestamp"] > end_time:
                        continue

                    # Check tags
                    if tags is not None:
                        match = True
                        for tag_key, tag_value in tags.items():
                            if (
                                tag_key not in value["tags"]
                                or value["tags"][tag_key] != tag_value
                            ):
                                match = False
                                break
                        if not match:
                            continue

                    filtered_values.append(value)

                if filtered_values:
                    result[name] = filtered_values

            return result


class LogEntry:
    """Represents a log entry"""

    def __init__(self, level: str, message: str, context: Dict[str, Any] = None):
        self.id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.datetime = datetime.utcfromtimestamp(self.timestamp).isoformat()
        self.level = level
        self.message = message
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the log entry to a dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": self.datetime,
            "level": self.level,
            "message": self.message,
            "context": self.context,
        }

    def to_json(self) -> str:
        """Convert the log entry to JSON"""
        return json.dumps(self.to_dict())


class Logger:
    """Custom logger that supports structured logging"""

    # Log levels
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __init__(self, name: str, handlers: List[Callable[[LogEntry], None]] = None):
        self.name = name
        self.handlers = handlers or []

        # Set up Python's standard logging as one of the handlers
        self.py_logger = logging.getLogger(name)
        self.add_handler(self._python_log_handler)

    def _python_log_handler(self, entry: LogEntry):
        """Log to Python's standard logging"""
        level_map = {
            self.DEBUG: logging.DEBUG,
            self.INFO: logging.INFO,
            self.WARNING: logging.WARNING,
            self.ERROR: logging.ERROR,
            self.CRITICAL: logging.CRITICAL,
        }
        level = level_map.get(entry.level, logging.INFO)

        self.py_logger.log(level, entry.message, extra={"context": entry.context})

    def add_handler(self, handler: Callable[[LogEntry], None]):
        """Add a log handler"""
        self.handlers.append(handler)

    def log(self, level: str, message: str, context: Dict[str, Any] = None):
        """Log a message"""
        entry = LogEntry(level, message, context)

        for handler in self.handlers:
            try:
                handler(entry)
            except Exception as e:
                self.py_logger.error(f"Error in log handler: {e}")

    def debug(self, message: str, context: Dict[str, Any] = None):
        """Log a debug message"""
        self.log(self.DEBUG, message, context)

    def info(self, message: str, context: Dict[str, Any] = None):
        """Log an info message"""
        self.log(self.INFO, message, context)

    def warning(self, message: str, context: Dict[str, Any] = None):
        """Log a warning message"""
        self.log(self.WARNING, message, context)

    def error(self, message: str, context: Dict[str, Any] = None):
        """Log an error message"""
        self.log(self.ERROR, message, context)

    def critical(self, message: str, context: Dict[str, Any] = None):
        """Log a critical message"""
        self.log(self.CRITICAL, message, context)


class FileLogHandler:
    """Handles logging to a file"""

    def __init__(self, log_file: str, formatter: Callable[[LogEntry], str] = None):
        self.log_file = log_file
        self.formatter = formatter or self._default_formatter

        # Create the log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def _default_formatter(self, entry: LogEntry) -> str:
        """Default log formatter"""
        return f"[{entry.datetime}] [{entry.level}] {entry.message} {json.dumps(entry.context) if entry.context else ''}"

    def __call__(self, entry: LogEntry):
        """Handle a log entry"""
        formatted = self.formatter(entry)

        with open(self.log_file, "a") as f:
            f.write(formatted + "\n")


class Observability:
    """Main observability class that manages logging and metrics"""

    def __init__(self, message_bus=None, config: Dict[str, Any] = None):
        self.message_bus = message_bus
        self.config = config or {}

        # Set up metrics
        self.metrics = Metrics()

        # Set up logging
        self.loggers: Dict[str, Logger] = {}
        self.default_logger = self.get_logger("default")

        # Set up event handlers if message bus is available
        if message_bus:
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers for observability"""
        # Subscribe to all events for metrics
        self.message_bus.subscribe_to_event("*", self._handle_event)

    def _handle_event(self, event_data):
        """Handle an event"""
        event_type, data = event_data

        # Record metrics
        self.metrics.record(
            metric_name=f"event.{event_type}", value=1, tags={"event_type": event_type}
        )

        # Log the event if configured
        if self.config.get("log_events", False):
            self.default_logger.debug(f"Event: {event_type}", {"event_data": data})

    def get_logger(self, name: str) -> Logger:
        """Get or create a logger"""
        if name in self.loggers:
            return self.loggers[name]

        logger = Logger(name)

        # Add file handler if configured
        log_file = self.config.get("log_file")
        if log_file:
            logger.add_handler(FileLogHandler(log_file))

        self.loggers[name] = logger
        return logger

    def record_metric(
        self, metric_name: str, value: Any, tags: Optional[Dict[str, str]] = None
    ):
        """Record a metric"""
        self.metrics.record(metric_name, value, tags)

    def get_metrics(self, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics"""
        return self.metrics.get_metrics(**kwargs)

    def log(
        self,
        level: str,
        message: str,
        context: Dict[str, Any] = None,
        logger_name: str = "default",
    ):
        """Log a message"""
        logger = self.get_logger(logger_name)
        logger.log(level, message, context)

    def start_span(self, name: str, tags: Optional[Dict[str, str]] = None) -> "Span":
        """Start a tracing span"""
        return Span(self, name, tags)


class Span:
    """Represents a tracing span"""

    def __init__(
        self,
        observability: Observability,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.observability = observability
        self.name = name
        self.tags = tags or {}
        self.start_time = time.time()
        self.end_time = None
        self.spans: List[Span] = []

        # Log span start
        self.observability.log(
            Logger.DEBUG, f"Span started: {name}", {"span": name, "tags": tags}
        )

    def __enter__(self):
        """Enter the span context"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context"""
        self.finish()

    def add_tag(self, key: str, value: str):
        """Add a tag to the span"""
        self.tags[key] = value

    def start_child(self, name: str, tags: Optional[Dict[str, str]] = None) -> "Span":
        """Start a child span"""
        span = Span(self.observability, name, tags)
        self.spans.append(span)
        return span

    def finish(self):
        """Finish the span"""
        if self.end_time is not None:
            return

        self.end_time = time.time()
        duration = self.end_time - self.start_time

        # Record metrics
        self.observability.record_metric(
            metric_name="span.duration",
            value=duration,
            tags={"span": self.name, **self.tags},
        )

        # Log span end
        self.observability.log(
            Logger.DEBUG,
            f"Span finished: {self.name} ({duration:.3f}s)",
            {"span": self.name, "duration": duration, "tags": self.tags},
        )


__all__ = ["Logger", "Observability", "LogEntry", "FileLogHandler", "Span", "Metrics"]