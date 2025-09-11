"""OpenTelemetry handler for observability."""

import logging
from contextvars import ContextVar
from typing import Any, Dict, Optional

from llmgine.bus.session import SessionEndEvent, SessionStartEvent
from llmgine.llm.tools.tool_events import ToolExecuteResultEvent
from llmgine.messages.events import (
    CommandResultEvent,
    CommandStartedEvent,
    Event,
    EventHandlerFailedEvent,
)
from llmgine.observability.manager import ObservabilityHandler

logger = logging.getLogger(__name__)

# Expose OTEL symbols at module scope so tests can patch them even if OTEL isn't installed
try:
    from opentelemetry import trace as _trace
    from opentelemetry.trace import Status as _Status, StatusCode as _StatusCode
except Exception:  # pragma: no cover - safe fallback when OTEL not installed
    class _Dummy:
        def __getattr__(self, _name):  # allow any attribute access
            return self
        def __call__(self, *args, **kwargs):  # allow calling
            return self
    _trace = _Dummy()
    _Status = _Dummy()
    _StatusCode = _Dummy()

# Provide patch points for tests
trace = _trace
Status = _Status
StatusCode = _StatusCode

# Context variables to track current trace and spans
current_trace: ContextVar[Optional[Any]] = ContextVar("current_trace", default=None)
current_spans: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_spans", default=None
)


class OpenTelemetryHandler(ObservabilityHandler):
    """Handler that maps events to OpenTelemetry traces and spans."""

    def __init__(self, service_name: str = "llmgine", **kwargs: Any):
        """Initialize the OpenTelemetry handler.

        Args:
            service_name: Name of the service for OpenTelemetry
            **kwargs: Additional configuration options
        """
        self.service_name = service_name
        self._tracer = None
        self._initialized = False

        # Try to initialize OpenTelemetry
        self._initialize_otel()

    def _initialize_otel(self) -> None:
        """Initialize OpenTelemetry if available."""
        try:
            from opentelemetry import trace  # local import to avoid hard dependency
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,
                ConsoleSpanExporter,
            )
            from opentelemetry.semconv.resource import ResourceAttributes

            # Create resource with service name
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name
            })

            # Create and configure tracer provider
            provider = TracerProvider(resource=resource)

            # Add console exporter for now (can be configured later)
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

            # Set as global tracer provider
            trace.set_tracer_provider(provider)

            # Get tracer
            self._tracer = trace.get_tracer(__name__)
            self._initialized = True

            logger.info(f"OpenTelemetry initialized for service: {self.service_name}")

        except ImportError:
            logger.warning(
                "OpenTelemetry libraries not installed. "
                "Install with: pip install 'llmgine[opentelemetry]'"
            )
            self._initialized = False

    def handle(self, event: Event) -> None:
        """Handle an event by mapping it to OpenTelemetry operations.

        Args:
            event: The event to handle
        """
        if not self._initialized:
            return

        event_type = type(event)

        # Map events to OpenTelemetry operations
        if event_type == SessionStartEvent:
            # Start new trace
            span = self._tracer.start_span(
                name=f"session_{event.session_id}",
                attributes={
                    "session.id": str(event.session_id),
                    "event.id": event.event_id,
                },
            )
            # Store in context
            token = trace.set_span_in_context(span)
            current_trace.set(token)
            spans = current_spans.get() or {}
            spans[str(event.session_id)] = span
            current_spans.set(spans)

        elif event_type == CommandStartedEvent:
            # Start new span for command
            cmd = getattr(event, "command", None)
            cmd_type = type(cmd).__name__ if cmd is not None else "unknown"
            cmd_id = getattr(cmd, "command_id", "unknown")
            parent_context = current_trace.get()
            span = self._tracer.start_span(
                name=f"command_{cmd_type}",
                context=parent_context,
                attributes={
                    "command.type": cmd_type,
                    "command.id": cmd_id,
                    "session.id": str(event.session_id),
                    "event.id": event.event_id,
                },
            )
            # Store span
            spans = current_spans.get() or {}
            spans[cmd_id] = span
            current_spans.set(spans)

        elif event_type == CommandResultEvent:
            # End command span
            spans = current_spans.get() or {}
            result = getattr(event, "command_result", None)
            cmd_id = getattr(result, "command_id", None)
            span = spans.get(cmd_id) if cmd_id else None
            if span:
                # Add result attributes
                span.set_attribute("command.success", getattr(result, "success", False))
                if hasattr(result, "result"):
                    span.set_attribute("command.result_type", type(result.result).__name__)

                # Set status
                if getattr(result, "success", False):
                    span.set_status(Status(StatusCode.OK))
                else:
                    span.set_status(Status(StatusCode.ERROR, "Command failed"))

                span.end()
                # Remove from tracking
                if cmd_id in spans:
                    del spans[cmd_id]
                current_spans.set(spans)

        # LLM events removed - using litellm directly now
        # elif event_type == LLMCallEvent:
        #     # Start span for LLM call
        #     parent_context = current_trace.get()
        #     span = self._tracer.start_span(
        #         name=f"llm_call_{event.model if hasattr(event, 'model') else 'unknown'}",
        #         context=parent_context,
        #         attributes={
        #             "llm.model": event.model if hasattr(event, "model") else "unknown",
        #             "llm.provider": event.provider
        #             if hasattr(event, "provider")
        #             else "unknown",
        #             "session.id": str(event.session_id),
        #             "event.id": event.event_id,
        #         },
        #     )
        #     # Store span
        #     spans = current_spans.get() or {}
        #     spans[f"llm_{event.event_id}"] = span
        #     current_spans.set(spans)

        elif event_type == ToolExecuteResultEvent:
            # Handle tool execution result
            parent_context = current_trace.get()
            # Create a span for the tool execution
            span = self._tracer.start_span(
                name=f"tool_{getattr(event, 'tool_name', 'unknown')}",
                context=parent_context,
                attributes={
                    "tool.name": getattr(event, "tool_name", "unknown"),
                    "tool.call_id": getattr(event, "tool_call_id", "unknown")
                    if hasattr(event, "tool_call_id")
                    else "unknown",
                    "session.id": str(event.session_id),
                    "event.id": event.event_id,
                },
            )

            # Add result data
            if hasattr(event, "tool_result"):
                span.set_attribute("tool.has_result", True)
                # optionally attach 'execution_succeed'
                if hasattr(event, "execution_succeed"):
                    span.set_attribute("tool.execution_succeed", bool(event.execution_succeed))

            span.set_status(Status(StatusCode.OK))
            span.end()

        # LLM events removed - using litellm directly now
        # elif event_type == LLMResponseEvent:
        #     # Handle LLM response
        #     spans = current_spans.get() or {}
        #     # Find corresponding LLM call span
        #     for span_id, span in list(spans.items()):
        #         if span_id.startswith("llm_"):
        #             # Add response attributes
        #             if hasattr(event, "content"):
        #                 span.set_attribute("llm.response_length", len(event.content))
        #             if hasattr(event, "finish_reason"):
        #                 span.set_attribute("llm.finish_reason", event.finish_reason)
        #
        #             span.set_status(Status(StatusCode.OK))
        #             span.end()
        #             # Remove from tracking
        #             del spans[span_id]
        #             current_spans.set(spans)
        #             break

        elif event_type == EventHandlerFailedEvent:
            # Record handler failure
            spans = current_spans.get() or {}
            # Record on most recent span
            if spans:
                # Get the most recent span
                span = list(spans.values())[-1]
                span.record_exception(
                    exception=Exception(f"Handler failed: {getattr(event, 'handler', 'unknown')}"),
                    attributes={
                        "handler.name": getattr(event, "handler", "unknown"),
                        "handler.exception": str(event.exception)
                        if hasattr(event, "exception")
                        else "unknown",
                        "session.id": str(event.session_id),
                    },
                )
                span.set_status(Status(StatusCode.ERROR, "Event handler failed"))

        elif event_type == SessionEndEvent:
            # End session trace
            spans = current_spans.get() or {}
            session_span = spans.get(str(event.session_id))
            if session_span:
                session_span.set_status(Status(StatusCode.OK))
                session_span.end()
                # Clear context
                del spans[str(event.session_id)]
                current_spans.set(spans)
                if not spans:
                    current_trace.set(None)
