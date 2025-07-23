"""Core message bus implementation for handling commands and events.

This module provides a clean, production-ready message bus with:
- Session-scoped and bus-scoped handler management
- Async event processing with batching
- Middleware and filter support
- Error recovery and observability
"""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
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
from llmgine.bus.registry_simple import HandlerRegistry
from llmgine.bus.session import BusSession
from llmgine.bus.utils import is_async_function
from llmgine.database.database import get_and_delete_unfinished_events, save_unfinished_events
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
    _lock = asyncio.Lock()
    
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
        self._event_queue: Optional[asyncio.Queue[Event]] = cast(
            Optional[asyncio.Queue[Event]], event_queue
        )
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
        
        # Performance settings
        self._batch_size = 10
        self._batch_timeout = 0.01
        
        self._initialized = True
        logger.info("MessageBus initialized")
    
    # --- Lifecycle Management ---
    
    async def start(self) -> None:
        """Start the message bus event processing."""
        async with self._lock:
            if self._running:
                logger.warning("MessageBus is already running")
                return
            
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
            
            await self._load_scheduled_events()
            
            self._running = True
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("MessageBus started")
    
    async def stop(self) -> None:
        """Stop the message bus event processing."""
        async with self._lock:
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
            
            await self._save_scheduled_events()
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
        if not is_async_function(handler):
            handler = self._wrap_sync_command_handler(
                cast(Callable[[Command], CommandResult], handler)
            )
        
        self._registry.register_command_handler(
            command_type, cast(AsyncCommandHandler, handler), session_id
        )
    
    def register_event_handler(
        self,
        event_type: Type[EventType],
        handler: Union[AsyncEventHandler, Callable[[Event], None]],
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Register an event handler."""
        if not is_async_function(handler):
            handler = self._wrap_sync_event_handler(
                cast(Callable[[Event], None], handler)
            )
        
        # Check if registry supports priority
        if hasattr(self._registry, "register_event_handler"):
            params = getattr(self._registry.register_event_handler, "__code__", None)
            if params and "priority" in params.co_varnames:
                self._registry.register_event_handler(
                    event_type, cast(AsyncEventHandler, handler), session_id, priority
                )
                return
        
        self._registry.register_event_handler(
            event_type, cast(AsyncEventHandler, handler), session_id
        )
    
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
        command_type = type(command)
        
        handler = self._registry.get_command_handler(command_type, command.session_id)
        if handler is None:
            error_msg = f"No handler registered for command {command_type.__name__}"
            logger.error(error_msg)
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
            
            result = await self._execute_with_middleware(command, handler)
            
            await self.publish(
                CommandResultEvent(command_result=result, session_id=command.session_id),
                await_processing=False,
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error executing command {command_type.__name__}: {e}")
            failed_result = CommandResult(
                success=False,
                command_id=command.command_id,
                error=f"{type(e).__name__}: {e!s}",
                metadata={"traceback": traceback.format_exc()},
            )
            await self.publish(
                CommandResultEvent(
                    command_result=failed_result,
                    session_id=command.session_id
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
        if self._event_queue is None:
            logger.warning("Event queue not initialized, event will be lost")
            return
        
        if self._observability:
            self._observability.observe_event(event)
        
        for filter_func in self._event_filters:
            if not filter_func.should_handle(event, event.session_id):
                logger.debug(
                    f"Event {type(event).__name__} filtered out by "
                    f"{type(filter_func).__name__}"
                )
                return
        
        await self._event_queue.put(event)
        
        if await_processing and not isinstance(event, ScheduledEvent):
            await self.wait_for_events()
    
    async def wait_for_events(self) -> None:
        """Wait for all current events to be processed."""
        if self._event_queue is None:
            return
        
        events_to_process = []
        scheduled_events = []
        
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                if isinstance(event, ScheduledEvent) and event.scheduled_time > datetime.now():
                    scheduled_events.append(event)
                else:
                    events_to_process.append(event)
            except asyncio.QueueEmpty:
                break
        
        for event in scheduled_events:
            await self._event_queue.put(event)
        
        if events_to_process:
            await self._process_event_batch(events_to_process)
    
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
        
        while len(batch) < self._batch_size and asyncio.get_event_loop().time() < deadline:
            try:
                timeout = max(0, deadline - asyncio.get_event_loop().time())
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=timeout
                )
                
                if isinstance(event, ScheduledEvent):
                    if event.scheduled_time > datetime.now():
                        await self._event_queue.put(event)
                        continue
                
                batch.append(event)
                
            except asyncio.TimeoutError:
                break
        
        return batch
    
    async def _process_event_batch(self, batch: List[Event]) -> None:
        """Process a batch of events."""
        tasks = []
        
        for event in batch:
            event_type = type(event)
            handlers = self._registry.get_event_handlers(event_type, event.session_id)
            
            if not handlers:
                logger.debug(
                    f"No handlers for {event_type.__name__} in session {event.session_id}"
                )
                continue
            
            for handler in handlers:
                task = asyncio.create_task(
                    self._handle_event_with_middleware(event, handler)
                )
                tasks.append((task, event, handler))
        
        if tasks:
            results = await asyncio.gather(
                *[task for task, _, _ in tasks],
                return_exceptions=True
            )
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    _, event, handler = tasks[i]
                    await self._handle_event_error(event, handler, result)
    
    async def _handle_event_with_middleware(
        self,
        event: Event,
        handler: AsyncEventHandler,
    ) -> None:
        """Handle event through middleware chain."""
        async def execute_handler(evt: Event, h: AsyncEventHandler) -> None:
            await h(evt)
        
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
        self.event_handler_errors.append(error)
        handler_name = getattr(handler, "__qualname__", repr(handler))
        
        logger.exception(
            f"Error in handler '{handler_name}' for {type(event).__name__}: {error}"
        )
        
        if not self._suppress_event_errors:
            raise error
        
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
    async def session(self, session_id: Optional[str] = None) -> AsyncIterator[BusSession]:
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
        
        events = get_and_delete_unfinished_events()
        for event in events:
            await self._event_queue.put(event)
        
        if events:
            logger.info(f"Loaded {len(events)} scheduled events")
    
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
            method = getattr(self._registry, "get_handler_stats")
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
    
    def excepthook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
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