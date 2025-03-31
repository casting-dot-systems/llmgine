"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import asyncio
from datetime import datetime
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast, Union
from dataclasses import asdict
from enum import Enum
import contextvars

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    Event,
)
from llmgine.observability.events import (
    ObservabilityBaseEvent as ObservabilityBaseEvent,
    Metric,
    MetricEvent,
    SpanContext,
    TraceEvent,
    uuid,
    EventLogWrapper
)

logger = logging.getLogger(__name__)

# Context variable to hold the current span context
current_span_context: contextvars.ContextVar[Optional[SpanContext]] = contextvars.ContextVar(
    "current_span_context", default=None
)

TCommand = TypeVar("TCommand", bound=Command)
TEvent = TypeVar("TEvent", bound=Event | ObservabilityBaseEvent)
CommandHandler = Callable[[TCommand], CommandResult]
AsyncCommandHandler = Callable[[TCommand], "asyncio.Future[CommandResult]"]
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


class MessageBus:
    """Async message bus for command and event handling (Singleton).

    This implements the Command Bus and Event Bus patterns, allowing
    for decoupled communication between components.
    """

    # --- Singleton Pattern --- 
    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(MessageBus, cls).__new__(cls)
            # Mark as not initialized yet, __init__ will handle it
            cls._instance._initialized = False 
        return cls._instance
    # --- End Singleton Pattern ---

    def __init__(self):
        """Initialize the message bus (only once)."""
        # --- Singleton Initialization Guard ---
        if hasattr(self, '_initialized') and self._initialized:
            return 
        # --- End Guard ---
        
        self._command_handlers: Dict[Type[Command], AsyncCommandHandler] = {}
        self._event_handlers: Dict[Type[Event | ObservabilityBaseEvent], List[AsyncEventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None

        logger.info("MessageBus initialized (Observability via registered handlers)")
        
        # --- Mark as initialized --- 
        self._initialized = True

    async def start(self) -> None:
        """Start the message bus event processing loop."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("MessageBus started", extra={"component": "MessageBus"})

    async def stop(self) -> None:
        """Stop the message bus event processing loop."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("MessageBus stopped", extra={"component": "MessageBus"})

    def register_command_handler(
        self, command_type: Type[TCommand], handler: CommandHandler
    ) -> None:
        """Register a command handler for a specific command type.

        Args:
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        async_handler = self._wrap_sync_command_handler(handler)
        if command_type in self._command_handlers:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered"
            )

        self._command_handlers[command_type] = async_handler
        logger.debug(
            f"Registered command handler for {command_type.__name__}",
            extra={"component": "MessageBus", "handler_type": "sync"},
        )

    def register_async_command_handler(
        self, command_type: Type[TCommand], handler: AsyncCommandHandler
    ) -> None:
        """Register an async command handler for a specific command type.

        Args:
            command_type: The type of command to handle
            handler: The async function that handles the command
        """
        if command_type in self._command_handlers:
            raise ValueError(
                f"Command handler for {command_type.__name__} already registered"
            )

        self._command_handlers[command_type] = handler
        logger.debug(
            f"Registered async command handler for {command_type.__name__}",
            extra={"component": "MessageBus", "handler_type": "async"},
        )

    def register_event_handler(
        self, event_type: Type[TEvent], handler: EventHandler
    ) -> None:
        """Register a sync event handler for app events or observability events."""
        async_handler = self._wrap_sync_event_handler(handler)
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(async_handler)
        logger.debug(
            f"Registered event handler for {event_type.__name__}",
            extra={"component": "MessageBus", "handler_type": "sync"},
        )

    def register_async_event_handler(
        self, event_type: Type[TEvent], handler: AsyncEventHandler
    ) -> None:
        """Register an async event handler for app events or observability events."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.debug(
            f"Registered async event handler for {event_type.__name__}",
            extra={"component": "MessageBus", "handler_type": "async"},
        )

    # --- Explicit Observability Methods ---

    async def start_span(
        self,
        name: str,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None, # Allow overriding the source
    ) -> SpanContext:
        """Starts a new trace span and publishes the start event."""
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            # Try getting from context var if not explicitly passed
            ctx_parent = current_span_context.get()
            if ctx_parent:
                trace_id = ctx_parent.trace_id
                parent_span_id = ctx_parent.span_id
            else:
                trace_id = str(uuid.uuid4())
                parent_span_id = None

        span_id = str(uuid.uuid4())
        span_context = SpanContext(
            trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id
        )

        start_event = TraceEvent(
            name=name,
            span_context=span_context,
            start_time=datetime.now().isoformat(),
            attributes=attributes or {},
            source=source or "MessageBus.start_span", # Default source
        )
        await self.publish(start_event)
        return span_context

    async def end_span(
        self,
        span_context: SpanContext,
        name: str, # Name needed again to ensure consistency
        status: str = "OK",
        attributes: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        source: Optional[str] = None, # Allow overriding the source
    ) -> None:
        """Ends a trace span, calculates duration, and publishes the end event."""
        # We need the start event to calculate duration reliably,
        # but storing it is complex. Let's approximate or accept inaccuracy.
        # A better way would involve passing start_time or retrieving the start event.
        # For now, we'll mark duration as None or calculate if possible (requires storing start times)
        # This implementation won't calculate duration accurately without start time.

        final_attributes = attributes or {}
        if error:
            status = "EXCEPTION"
            final_attributes.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ),
            })

        end_event = TraceEvent(
            name=name,
            span_context=span_context,
            end_time=datetime.now().isoformat(),
            duration_ms=None, # Duration calculation requires start time
            status=status,
            attributes=final_attributes,
            source=source or "MessageBus.end_span", # Default source
        )
        await self.publish(end_event)

    async def emit_metric(
        self,
        name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        source: Optional[str] = None, # Allow overriding the source
    ) -> None:
        """Creates and publishes a single metric event."""
        metric = Metric(name=name, value=value, unit=unit, tags=tags or {})
        metric_event = MetricEvent(
            metrics=[metric], 
            source=source or "MessageBus.emit_metric" # Default source
        )
        await self.publish(metric_event)

    # --- End Explicit Observability Methods ---

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command, automatically managing a trace span using contextvars."""
        command_type = type(command)
        handler = self._command_handlers.get(command_type)

        if not handler:
            error_msg = f"No handler registered for command type {command_type.__name__}"
            logger.error(error_msg, extra={"component": "MessageBus"})
            # Consider publishing an error event/trace here as well
            raise ValueError(error_msg)

        # --- Tracing Setup --- 
        span_name = f"Execute Command: {command_type.__name__}"
        parent_context = current_span_context.get() # Get context from parent caller
        span_context: Optional[SpanContext] = None # Initialize
        token: Optional[contextvars.Token] = None
        start_time = time.time() # For duration calculation

        try:
            span_attributes = {
                "command_id": command.id,
                "command_type": command_type.__name__,
                "command_metadata": getattr(command, 'metadata', {}),
            }
            span_context = await self.start_span(
                name=span_name,
                parent_context=parent_context, # Pass parent context here
                attributes=span_attributes,
                source="MessageBus.execute",
            )
            # Set the context for the duration of the handler execution
            token = current_span_context.set(span_context)

            # --- Execute Handler --- 
            result = await handler(command)
            # --- End Execute Handler ---

            # --- Tracing Teardown (Success) --- 
            execution_time_ms = (time.time() - start_time) * 1000
            end_attributes = {
                "success": result.success,
                "error_details": result.error if not result.success else None,
            }
            # Manually create the end event to include duration
            end_trace_event = TraceEvent(
                name=span_name,
                span_context=span_context,
                end_time=datetime.now().isoformat(),
                duration_ms=execution_time_ms,
                status="OK" if result.success else "ERROR",
                attributes=end_attributes,
                source="MessageBus.execute",
            )
            await self.publish(end_trace_event)
            # No need to call self.end_span as we manually created the event

            return result

        except Exception as e:
            # --- Tracing Teardown (Exception) --- 
            execution_time_ms = (time.time() - start_time) * 1000
            # Ensure span_context exists before trying to end span
            if span_context:
                 error_attributes = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "stack_trace": "".join(traceback.format_exception(type(e), e, e.__traceback__)),
                }
                 # Manually create the end event to include duration and error
                 exception_trace_event = TraceEvent(
                    name=span_name,
                    span_context=span_context,
                    end_time=datetime.now().isoformat(),
                    duration_ms=execution_time_ms,
                    status="EXCEPTION",
                    attributes=error_attributes,
                    source="MessageBus.execute",
                 )
                 await self.publish(exception_trace_event)
                 # No need to call self.end_span

            logger.exception(
                f"Unhandled exception executing command {command_type.__name__}: {str(e)}",
                extra={
                    "component": "MessageBus",
                    "command_id": command.id,
                },
            )
            raise e # Re-raise the exception
        finally:
            # Reset the context variable even if errors occurred
            if token:
                current_span_context.reset(token)

    async def publish(self, event: Event | ObservabilityBaseEvent) -> None:
        """Wraps event, publishes wrapper, and publishes the original event (unless it's the wrapper itself)."""
        original_event_type_name = type(event).__name__
        
        # Avoid wrapping a wrapper
        if isinstance(event, EventLogWrapper):
            # If someone accidentally publishes a wrapper, just queue it directly
            # primarily for the FileHandler, though this shouldn't be standard practice.
            await self._event_queue.put(event)
            logger.warning("An EventLogWrapper was published directly. This is unusual.")
            return
            
        # Serialize the original event
        # Use a try-except block as serialization might fail for complex objects
        original_event_data = {}
        try:
            original_event_data = self._event_to_dict(event)
        except Exception as e:
            logger.error(
                f"Failed to serialize original event {original_event_type_name} for wrapper: {e}",
                extra={"event_id": getattr(event, 'id', 'N/A')}, 
                exc_info=True
            )
            original_event_data = {"error": "Serialization failed", "event_repr": repr(event)}

        # Create the wrapper event
        wrapper_event = EventLogWrapper(
            source="MessageBus.publish",
            original_event_type=original_event_type_name,
            original_event_data=original_event_data
        )

        # Always publish the wrapper event to the queue
        await self._event_queue.put(wrapper_event)

        # Always queue the original event (unless it was already a wrapper)
        # This allows handlers listening for specific original types (like ConsoleHandler 
        # listening for BaseEvent, or App handlers listening for AppEvent) to receive them.
        await self._event_queue.put(event)

    async def _process_events(self) -> None:
        """Process events from the queue indefinitely."""
        while True:
            event = await self._event_queue.get()
            try:
                await self._handle_event(event)
            except Exception:
                logger.exception(
                    f"Unhandled error processing event {type(event).__name__}",
                    extra={"component": "MessageBus", "event_id": getattr(event, 'id', 'N/A')},
                )
            finally:
                self._event_queue.task_done()

    async def _handle_event(self, event: Event | ObservabilityBaseEvent) -> None:
        """Dispatch an event to all registered handlers listening for its type or parent types."""
        event_type = type(event)
        handlers_to_run: List[AsyncEventHandler] = []

        for registered_type, handlers in self._event_handlers.items():
            if issubclass(event_type, registered_type):
                handlers_to_run.extend(handlers)

        if handlers_to_run:
            logger.debug(f"Dispatching event {event_type.__name__} to {len(handlers_to_run)} handlers",
                         extra={"component": "MessageBus", "event_id": getattr(event, 'id', 'N/A')})

            results = await asyncio.gather(
                *(handler(event) for handler in handlers_to_run), return_exceptions=True
            )

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = getattr(handlers_to_run[i], '__qualname__', repr(handlers_to_run[i]))
                    logger.exception(
                        f"Error in event handler '{handler_name}' for {event_type.__name__}: {result}",
                        extra={"component": "MessageBus", "event_id": getattr(event, 'id', 'N/A')},
                    )
        else:
            logger.debug(f"No handlers registered for event type {event_type.__name__} or its parents",
                         extra={"component": "MessageBus", "event_id": getattr(event, 'id', 'N/A')})

    def _wrap_sync_command_handler(self, handler: CommandHandler) -> AsyncCommandHandler:
        """Wrap a synchronous command handler to run in an executor."""
        if asyncio.iscoroutinefunction(handler):
            return cast(AsyncCommandHandler, handler)

        async def async_handler(command: Command) -> CommandResult:
            return handler(command)

        return async_handler

    def _wrap_sync_event_handler(self, handler: EventHandler) -> AsyncEventHandler:
        """Wrap a synchronous event handler to run in an executor."""
        if asyncio.iscoroutinefunction(handler):
            return cast(AsyncEventHandler, handler)

        async def async_handler(event: Event) -> None:
            handler(event)

        return async_handler

    def _event_to_dict(self, event: Any) -> Dict[str, Any]:
        """Convert an event (dataclass or object) to a dictionary for serialization."""
        # Prefers a custom to_dict if available
        if hasattr(event, "to_dict") and callable(event.to_dict):
             try:
                return event.to_dict()
             except Exception:
                logger.warning(f"Error calling to_dict on {type(event)}", exc_info=True)
                # Fall through to other methods

        # Use dataclasses.asdict if possible
        try:
            return asdict(event, dict_factory=lambda x: {k: self._convert_value(v) for k, v in x})
        except TypeError:
            pass # Not a dataclass

        # Handle basic objects with __dict__, excluding private/protected attrs
        if hasattr(event, "__dict__"):
            return {k: self._convert_value(v) for k, v in event.__dict__.items() if not k.startswith('_')}

        # Fallback for unknown types
        logger.warning(f"Could not serialize event of type {type(event)} to dict, using repr().")
        return {"event_repr": repr(event)}

    def _convert_value(self, value: Any) -> Any:
        """Helper for _event_to_dict to handle nested structures and special types."""
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            # Ensure keys are strings for JSON compatibility
            return {str(k): self._convert_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple, set)): # Handle sets too
            return [self._convert_value(item) for item in value]
        elif hasattr(value, "to_dict") and callable(value.to_dict):
             # Use custom to_dict for nested objects if available
            try:
                return value.to_dict()
            except Exception:
                 logger.warning(f"Error calling nested to_dict on {type(value)}", exc_info=True)
                 # Fall through to other methods
        elif hasattr(value, "__dict__") or hasattr(value, "__dataclass_fields__"):
             # Recursively convert nested objects/dataclasses
             return self._event_to_dict(value)
        else:
            # Attempt to convert other types to string
            try:
                return str(value)
            except Exception:
                logger.warning(f"Could not convert type {type(value)} to string, using repr()")
                return repr(value)
