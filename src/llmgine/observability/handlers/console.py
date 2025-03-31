"""Console handler for printing observability events."""

import logging
from typing import Any

from llmgine.observability.events import ObservabilityBaseEvent, MetricEvent, TraceEvent
from llmgine.observability.handlers.base import ObservabilityEventHandler

logger = logging.getLogger(__name__) # Use standard logger


class ConsoleEventHandler(ObservabilityEventHandler):
    """Prints a summary of observability events to the console using standard logging."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Could add level filtering here if needed

    async def handle(self, event: ObservabilityBaseEvent) -> None:
        """Process the event and print its representation to the console logger."""
        
        # Default representation for unknown event types
        log_level = logging.INFO
        message = f"[OBS EVENT] Type={type(event).__name__}, ID={event.id}"
        
        try:
            if isinstance(event, MetricEvent):
                # Special formatting for MetricEvent
                messages = []
                for metric in event.metrics:
                    unit_str = f" {metric.unit}" if metric.unit else ""
                    tags_str = " " + " ".join(f"{k}={v}" for k, v in metric.tags.items()) if metric.tags else ""
                    messages.append(f"METRIC {metric.name}={metric.value}{unit_str}{tags_str}")
                message = f"[OBS EVENT] {', '.join(messages)}"
            
            elif isinstance(event, TraceEvent):
                # Special formatting for TraceEvent (similar to before)
                if event.start_time and not event.end_time:
                    message = (
                        f"TRACE START: {event.name} [trace={event.span_context.trace_id[:8]}] "
                        f"[span={event.span_context.span_id[:8]}] "
                        f"(parent={event.span_context.parent_span_id[:8] if event.span_context.parent_span_id else 'None'})"
                    )
                elif event.end_time:
                    duration = f" ({event.duration_ms:.2f}ms)" if event.duration_ms is not None else ""
                    message = (
                        f"TRACE END: {event.name} [trace={event.span_context.trace_id[:8]}] "
                        f"[span={event.span_context.span_id[:8]}] {event.status}{duration}"
                    )
                else:
                     # For trace events that are not start/end (e.g., annotations)
                     message = f"TRACE EVENT: {event.name} [trace={event.span_context.trace_id[:8]}] [span={event.span_context.span_id[:8]}] Attributes: {event.attributes}"

            # Could add specific formatting for LogEvent here too if desired
            # elif isinstance(event, LogEvent): ...

        except Exception as e:
            logger.error(f"Error formatting event in ConsoleEventHandler: {e}", exc_info=True)
            # Fall back to default message

        # Log the formatted message using the standard logger
        logger.log(log_level, message) 