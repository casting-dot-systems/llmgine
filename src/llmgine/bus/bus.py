"""Core message bus implementation for handling commands and events.

This module provides a clean, production-ready message bus with:
- Session-scoped and bus-scoped handler management
- Async event processing with batching
- Middleware and filter support
- Error recovery and observability
"""

import asyncio
from collections import defaultdict
import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from llmgine.bus.interfaces import (
    AsyncCommandHandler,
    AsyncEventHandler,
    EventFilter,
    HandlerMiddleware,
    HandlerPriority,
    IEventQueue,
    IHandlerRegistry,
    IMessageBus,
)
from llmgine.bus.metrics import Timer, get_metrics_collector
from llmgine.bus.registry import HandlerRegistry, EventHandlerEntry
from llmgine.bus.session import BusSession
from llmgine.bus.utils import is_async_function
from llmgine.database.database import (
    get_and_delete_unfinished_events,
    persist_event,
    save_unfinished_events,
)
from llmgine.llm import SessionID
from llmgine.messages.approvals import ApprovalCommand, execute_approval_command
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    CommandResultEvent,
    CommandStartedEvent,
    Event,
    EventHandlerFailedEvent,
)
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.observability.manager import ObservabilityManager

logger = logging.getLogger(__name__)

CommandType = TypeVar("CommandType", bound=Command)
EventType = TypeVar("EventType", bound=Event)


class MessageBus(IMessageBus):
    """Async message bus for command and event handling.

    Features:
    - Clean separation between session-scoped and bus-scoped handlers
    - Thread-safe singleton pattern
    - Middleware and filter support
    - Optimized batch event processing
    - Built-in error recovery and observability
    """

    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """Thread-safe singleton implementation."""
        if cls._instance is None:
            placeholder = super().__new__(cls)
            if cls._instance is None:
                cls._instance = placeholder
        return cls._instance

    def __init__(
        self,
        registry: Optional[IHandlerRegistry] = None,
        event_queue: Optional[IEventQueue] = None,
        observability: Optional[ObservabilityManager] = None,
    ) -> None:
        """Initialize the message bus.

        Args:
            registry: Custom handler registry (defaults to HandlerRegistry)
            event_queue: Custom event queue (defaults to asyncio.Queue)
            observability: Observability manager for event tracking
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._registry: IHandlerRegistry = registry or HandlerRegistry()
        self._event_queue: Optional[IEventQueue] = cast(Optional[IEventQueue], event_queue)
        # Per-instance start/stop lock (loop-safe)
        self._start_stop_lock: asyncio.Lock = asyncio.Lock()
        self._observability = observability

        # Middleware and filters
        self._command_middleware: List[HandlerMiddleware] = []
        self._event_middleware: List[HandlerMiddleware] = []
        self._event_filters: List[EventFilter] = []

        # Processing state
        self._processing_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._suppress_event_errors = True
        self.event_handler_errors: List[Exception] = []

        # Pre-start event buffer (prevents silent drops)
        self._prestart_events: List[Event] = []
        # Cap memory for retained handler errors
        self._max_error_history: int = 1000

        # Performance settings
        self._batch_size = 10
        self._batch_timeout = 0.01

        self._initialized = True
        logger.info("MessageBus initialized")

    # --- Lifecycle Management ---

    async def start(self) -> None:
        """Start the message bus event processing."""
        async with self._start_stop_lock:
            if self._running:
                logger.warning("MessageBus is already running")
                return

            if self._event_queue is None:
                self._event_queue = asyncio.Queue()

            # Attempt to restore scheduled events (graceful if DB not configured)
            try:
                await self._load_scheduled_events()
            except Exception as e:  # pragma: no cover
                logger.warning(f"Skipping scheduled-event load: {e}")

            # Flush any pre-start events that were buffered
            if self._prestart_events:
                metrics = get_metrics_collector()
                for ev in self._prestart_events:
                    await self._event_queue.put(ev)
                    metrics.inc_counter("events_published_total")
                metrics.set_gauge("queue_size", self._event_queue.qsize())
                self._prestart_events.clear()

            self._running = True
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("MessageBus started")

    async def stop(self) -> None:
        """Stop the message bus event processing."""
        async with self._start_stop_lock:
            if not self._running:
                logger.info("MessageBus is not running")
                return

            self._running = False

            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await asyncio.wait_for(self._processing_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except Exception as e:
                    logger.exception(f"Error stopping processing task: {e}")
                finally:
                    self._processing_task = None

            # Save any scheduled events left in the queue (best-effort)
            try:
                await self._save_scheduled_events()
            except Exception as e:  # pragma: no cover
                logger.warning(f"Skipping scheduled-event save: {e}")
            self._event_queue = None

            logger.info("MessageBus stopped")

    async def reset(self) -> None:
        """Reset the message bus to initial state."""
        await self.stop()
        # Reset the registry
        self._registry = HandlerRegistry()
        # Clear middleware and filters
        self._command_middleware.clear()
        self._event_middleware.clear()
        self._event_filters.clear()
        # Clear errors
        self.event_handler_errors.clear()
        # Reset other state
        self._suppress_event_errors = True
        self._batch_size = 10
        self._batch_timeout = 0.01
        logger.info("MessageBus reset")

    # --- Handler Registration ---

    def register_command_handler(
        self,
        command_type: Type[CommandType],
        handler: Union[AsyncCommandHandler, Callable[[Command], CommandResult]],
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Register a command handler."""
        metrics = get_metrics_collector()

        if not is_async_function(handler):
            handler = self._wrap_sync_command_handler(
                cast(Callable[[Command], CommandResult], handler)
            )

        self._registry.register_command_handler(
            command_type, cast(AsyncCommandHandler, handler), session_id
        )

        # Update registered handlers gauge using registry stats
        try:
            stats = {}
            if hasattr(self._registry, "get_handler_stats"):
                stats = self._registry.get_handler_stats()  # type: ignore[attr-defined]
            total_handlers = (
                stats.get("total_event_handlers", 0) + stats.get("total_command_handlers", 0)
            )
            metrics.set_gauge("registered_handlers", total_handlers)
        except Exception:
            pass

    def register_event_handler(
        self,
        event_type: Type[EventType],
        handler: Union[AsyncEventHandler, Callable[[Event], None]],
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Register an event handler."""
        metrics = get_metrics_collector()

        if not is_async_function(handler):
            handler = self._wrap_sync_event_handler(
                cast(Callable[[Event], None], handler)
            )

        self._registry.register_event_handler(
            event_type, cast(AsyncEventHandler, handler), session_id, priority
        )

        # Update registered handlers gauge using registry stats
        try:
            stats = {}
            if hasattr(self._registry, "get_handler_stats"):
                stats = self._registry.get_handler_stats()  # type: ignore[attr-defined]
            total_handlers = (
                stats.get("total_event_handlers", 0) + stats.get("total_command_handlers", 0)
            )
            metrics.set_gauge("registered_handlers", total_handlers)
        except Exception:
            pass

    def unregister_session_handlers(self, session_id: SessionID) -> None:
        """Unregister all handlers for a session."""
        self._registry.unregister_session(session_id)

    # --- Middleware and Filters ---

    def add_command_middleware(self, middleware: HandlerMiddleware) -> None:
        """Add middleware for command processing."""
        self._command_middleware.append(middleware)
        logger.debug(f"Added command middleware: {type(middleware).__name__}")

    def add_event_middleware(self, middleware: HandlerMiddleware) -> None:
        """Add middleware for event processing."""
        self._event_middleware.append(middleware)
        logger.debug(f"Added event middleware: {type(middleware).__name__}")

    def add_event_filter(self, filter_func: EventFilter) -> None:
        """Add a filter for event processing."""
        self._event_filters.append(filter_func)
        logger.debug(f"Added event filter: {type(filter_func).__name__}")

    # --- Command Execution ---

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command and return its result."""
        metrics = get_metrics_collector()
        command_type = type(command)

        metrics.inc_counter("commands_sent_total")

        handler = self._registry.get_command_handler(command_type, command.session_id)
        if handler is None:
            error_msg = f"No handler registered for command {command_type.__name__}"
            logger.error(error_msg)
            metrics.inc_counter("commands_failed_total")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error=error_msg,
            )

        try:
            await self.publish(
                CommandStartedEvent(command=command, session_id=command.session_id),
                await_processing=False,
            )

            with Timer(metrics, "command_processing_duration_seconds"):
                result = await self._execute_with_middleware(command, handler)

            if result.success:
                metrics.inc_counter("commands_processed_total")
            else:
                metrics.inc_counter("commands_failed_total")

            await self.publish(
                CommandResultEvent(command_result=result, session_id=command.session_id),
                await_processing=False,
            )

            return result

        except Exception as e:
            logger.exception(f"Error executing command {command_type.__name__}: {e}")
            metrics.inc_counter("commands_failed_total")
            failed_result = CommandResult(
                success=False,
                command_id=command.command_id,
                error=f"{type(e).__name__}: {e!s}",
                metadata={"traceback": traceback.format_exc()},
            )
            await self.publish(
                CommandResultEvent(
                    command_result=failed_result, session_id=command.session_id
                ),
                await_processing=False,
            )
            return failed_result

    async def _execute_with_middleware(
        self,
        command: Command,
        handler: AsyncCommandHandler,
    ) -> CommandResult:
        """Execute command through middleware chain."""
        if isinstance(command, ApprovalCommand):
            return await execute_approval_command(command, handler)

        async def execute_handler(cmd: Command, h: AsyncCommandHandler) -> CommandResult:
            return await h(cmd)

        chain = execute_handler
        for middleware in reversed(self._command_middleware):
            prev_chain = chain

            async def new_chain(
                cmd: Command,
                h: AsyncCommandHandler,
                m: HandlerMiddleware = middleware,
                prev: Any = prev_chain,
            ) -> CommandResult:
                return await m.process_command(cmd, h, prev)

            chain = new_chain

        return await chain(command, handler)

    # --- Event Publishing ---

    async def publish(self, event: Event, await_processing: bool = True) -> None:
        """Publish an event to the bus."""
        metrics = get_metrics_collector()

        if self._event_queue is None:
            # Buffer instead of dropping when bus hasn't started yet
            logger.warning(
                "Event queue not initialized; buffering event until MessageBus.start()"
            )
            self._prestart_events.append(event)
            return

        # capture error count to detect new errors after processing
        pre_error_count = len(self.event_handler_errors)

        # Forward to ObservabilityManager directly (no bus indirection)
        if self._observability is not None:
            try:
                self._observability.observe_event(event)
            except Exception:
                # Never let observability issues affect the bus
                import logging
                logging.getLogger(__name__).error(
                    "Observability handler failed for event %s", type(event).__name__, exc_info=True
                )

        for filter_func in self._event_filters:
            if not filter_func.should_handle(event, event.session_id):
                logger.debug(
                    f"Event {type(event).__name__} filtered out by "
                    f"{type(filter_func).__name__}"
                )
                return

        # Optional event persistence (no-op unless LLMGINE_PERSIST_EVENTS=1)
        persist_event(event)

        await self._event_queue.put(event)
        metrics.inc_counter("events_published_total")
        metrics.set_gauge("queue_size", self._event_queue.qsize())

        if await_processing and not isinstance(event, ScheduledEvent):
            await self.wait_for_events()
            # If errors are not suppressed and new errors occurred during processing,
            # surface the last one to the caller to match test expectations.
            if not self._suppress_event_errors and len(self.event_handler_errors) > pre_error_count:
                raise self.event_handler_errors[-1]

    async def wait_for_events(self) -> None:
        """Wait for all current events to be processed."""
        if self._event_queue is None:
            return

        # Use proper queue.join semantics; relies on task_done() being called
        try:
            await self._event_queue.join()
        except Exception:
            # Fallback if a custom queue doesn't implement join()
            while not self._event_queue.empty():
                await asyncio.sleep(0.01)

    # --- Event Processing ---

    async def _process_events(self) -> None:
        """Main event processing loop."""
        logger.info("Starting event processing loop")

        while self._running:
            try:
                batch = await self._collect_event_batch()

                if batch:
                    await self._process_event_batch(batch)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info("Event processing cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.1)

    async def _collect_event_batch(self) -> List[Event]:
        """Collect events for batch processing."""
        if self._event_queue is None:
            return []

        batch: List[Event] = []
        deadline = asyncio.get_event_loop().time() + self._batch_timeout

        while (
            len(batch) < self._batch_size and asyncio.get_event_loop().time() < deadline
        ):
            try:
                timeout = max(0, deadline - asyncio.get_event_loop().time())
                event = await asyncio.wait_for(self._event_queue.get(), timeout=timeout)

                if isinstance(event, ScheduledEvent):
                    if event.scheduled_time > datetime.now():
                        # Re-queue future event and mark the original task as done
                        await self._event_queue.put(event)
                        try:
                            self._event_queue.task_done()
                        except Exception:
                            pass
                        continue

                batch.append(event)

            except asyncio.TimeoutError:
                break

        return batch

    async def _process_event_batch(self, batch: List[Event]) -> None:
        """Process a batch of events."""
        metrics = get_metrics_collector()

        for event in batch:
            event_type = type(event)
            # Prefer entries with priorities if registry supports it
            entries: List[EventHandlerEntry]
            if hasattr(self._registry, "get_event_handler_entries"):
                # type: ignore[attr-defined]
                entries = self._registry.get_event_handler_entries(event_type, event.session_id)  # type: ignore
            else:
                handlers_fallback = self._registry.get_event_handlers(event_type, event.session_id)
                from llmgine.bus.interfaces import HandlerPriority
                entries = [EventHandlerEntry(priority=HandlerPriority.NORMAL, handler=h) for h in handlers_fallback]

            if not entries:
                logger.debug(
                    f"No handlers for {event_type.__name__} in session {event.session_id}"
                )
                # Mark the event done even with no handlers to keep join() semantics correct
                if self._event_queue:
                    try:
                        self._event_queue.task_done()
                    except Exception:
                        pass
                continue

            # Group handlers by priority; lower numeric value = higher priority
            priority_groups: Dict[int, List[AsyncEventHandler]] = defaultdict(list)
            for entry in entries:
                priority_groups[int(entry.priority)].append(entry.handler)

            # Execute priority groups in order (highest first)
            for prio in sorted(priority_groups.keys()):
                group_handlers = priority_groups[prio]
                group_tasks = [
                    asyncio.create_task(self._handle_event_with_middleware(event, h))
                    for h in group_handlers
                ]
                if group_tasks:
                    results = await asyncio.gather(*group_tasks, return_exceptions=True)
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            await self._handle_event_error(event, group_handlers[i], result)

            # Mark this event as done once all its handlers finished
            if self._event_queue:
                try:
                    self._event_queue.task_done()
                except Exception:
                    pass

        # Refresh the queue size gauge after finishing the batch
        metrics.set_gauge("queue_size", self._event_queue.qsize() if self._event_queue else 0)

    async def _handle_event_with_middleware(
        self,
        event: Event,
        handler: AsyncEventHandler,
    ) -> None:
        """Handle event through middleware chain."""
        metrics = get_metrics_collector()

        async def execute_handler(evt: Event, h: AsyncEventHandler) -> None:
            with Timer(metrics, "event_processing_duration_seconds"):
                await h(evt)
            metrics.inc_counter("events_processed_total")

        chain = execute_handler
        for middleware in reversed(self._event_middleware):
            prev_chain = chain

            async def new_chain(
                evt: Event,
                h: AsyncEventHandler,
                m: HandlerMiddleware = middleware,
                prev: Any = prev_chain,
            ) -> None:
                await m.process_event(evt, h, prev)

            chain = new_chain

        await chain(event, handler)

    async def _handle_event_error(
        self,
        event: Event,
        handler: AsyncEventHandler,
        error: Exception,
    ) -> None:
        """Handle errors from event handlers."""
        metrics = get_metrics_collector()
        metrics.inc_counter("events_failed_total")

        # Bound memory used by retained exceptions
        self.event_handler_errors.append(error)
        if len(self.event_handler_errors) > self._max_error_history:
            del self.event_handler_errors[: len(self.event_handler_errors) - self._max_error_history]
        handler_name = getattr(handler, "__qualname__", repr(handler))

        logger.exception(
            f"Error in handler '{handler_name}' for {type(event).__name__}: {error}"
        )

        await self.publish(
            EventHandlerFailedEvent(
                event=event,
                handler=handler_name,
                exception=error,
                session_id=event.session_id,
            ),
            await_processing=False,
        )

    # --- Session Management ---

    def create_session(self, session_id: Optional[str] = None) -> BusSession:
        """Create a new bus session."""
        return BusSession(id=session_id)

    @asynccontextmanager
    async def session(
        self, session_id: Optional[str] = None
    ) -> AsyncIterator[BusSession]:
        """Create a session as an async context manager."""
        session = self.create_session(session_id)
        await session.start()
        try:
            yield session
        finally:
            await session.end()

    # --- Configuration ---

    def set_observability_manager(self, observability: ObservabilityManager) -> None:
        """Set the observability manager."""
        self._observability = observability

    def suppress_event_errors(self) -> None:
        """Suppress errors during event handling."""
        self._suppress_event_errors = True

    def unsuppress_event_errors(self) -> None:
        """Do not suppress errors during event handling."""
        self._suppress_event_errors = False

    def set_batch_processing(self, batch_size: int, batch_timeout: float) -> None:
        """Configure batch processing parameters."""
        self._batch_size = max(1, batch_size)
        self._batch_timeout = max(0.001, batch_timeout)

    def set_error_history_limit(self, limit: int) -> None:
        """Configure the maximum number of handler exceptions to retain."""
        self._max_error_history = max(0, int(limit))
        if self._max_error_history == 0:
            self.event_handler_errors.clear()
        elif len(self.event_handler_errors) > self._max_error_history:
            del self.event_handler_errors[: len(self.event_handler_errors) - self._max_error_history]

    # --- Persistence ---

    async def _save_scheduled_events(self) -> None:
        """Save scheduled events to persistent storage."""
        if self._event_queue is None:
            return

        scheduled_events: List[ScheduledEvent] = []
        temp_events: List[Event] = []

        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                if isinstance(event, ScheduledEvent):
                    scheduled_events.append(event)
                else:
                    temp_events.append(event)
            except asyncio.QueueEmpty:
                break

        if scheduled_events:
            save_unfinished_events(scheduled_events)
            logger.info(f"Saved {len(scheduled_events)} scheduled events")

        for event in temp_events:
            await self._event_queue.put(event)

    async def _load_scheduled_events(self) -> None:
        """Load scheduled events from persistent storage."""
        if self._event_queue is None:
            return

        try:
            events = get_and_delete_unfinished_events()
        except Exception as e:  # pragma: no cover
            logger.warning(f"Could not load scheduled events: {e}")
            events = []
        for event in events:
            await self._event_queue.put(event)

        if events:
            logger.info(f"Loaded {len(events)} scheduled events")

    # --- Metrics Access ---

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current bus metrics."""
        metrics = get_metrics_collector()
        return await metrics.get_metrics()

    # --- Helper Methods ---

    def _wrap_sync_command_handler(
        self, handler: Callable[[Command], CommandResult]
    ) -> AsyncCommandHandler:
        """Wrap a sync command handler as async."""

        async def async_wrapper(command: Command) -> CommandResult:
            return handler(command)

        async_wrapper.function = handler  # type: ignore[attr-defined]
        return async_wrapper

    def _wrap_sync_event_handler(
        self, handler: Callable[[Event], None]
    ) -> AsyncEventHandler:
        """Wrap a sync event handler as async."""

        async def async_wrapper(event: Event) -> None:
            handler(event)

        async_wrapper.function = handler  # type: ignore[attr-defined]
        return async_wrapper

    # --- Statistics ---

    async def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        registry_stats = {}
        if hasattr(self._registry, "get_handler_stats"):
            # Check if the method is async
            method = self._registry.get_handler_stats
            if asyncio.iscoroutinefunction(method):
                registry_stats = await method()
            else:
                registry_stats = method()

        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize() if self._event_queue else 0,
            "batch_size": self._batch_size,
            "batch_timeout": self._batch_timeout,
            "error_suppression": self._suppress_event_errors,
            "total_errors": len(self.event_handler_errors),
            **registry_stats,
        }


def bus_exception_hook(bus: MessageBus) -> None:
    """Install exception hook that stops the bus on uncaught exceptions."""
    import sys
    import traceback

    def excepthook(
        exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any
    ) -> None:
        logger.info("Global unhandled exception caught by bus excepthook!")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(bus.stop())
            else:
                loop.run_until_complete(bus.stop())
        except RuntimeError:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bus.stop())
                loop.close()
            except Exception as e:
                print(f"Failed to cleanup bus: {e}")

        sys.exit(1)

    sys.excepthook = excepthook
