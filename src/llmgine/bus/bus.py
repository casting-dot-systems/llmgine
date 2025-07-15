"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import os
import sys
import asyncio
import contextvars
from datetime import datetime
import logging
import traceback
from types import TracebackType
from typing import (
    Any,
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

from llmgine.bus.session import BusSession
from llmgine.bus.utils import is_async_function
from llmgine.llm import SessionID
from llmgine.messages.approvals import ApprovalCommand, execute_approval_command
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    CommandResultEvent,
    CommandStartedEvent,
    Event,
    EventHandlerFailedEvent,
    SessionStartEvent,
    SessionEndEvent,
)
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.observability.handlers.base import ObservabilityEventHandler
from llmgine.database.database import get_and_delete_unfinished_events, save_unfinished_events

# Get the base logger and wrap it with the adapter
logger = logging.getLogger(__name__)

# TODO: add tracing and span context using contextvars
trace: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace", default=None
)
span: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("span", default=None)

# Type variables for command and event handlers
CommandType = TypeVar("CommandType", bound=Command)
CommandHandler = Callable[[Command], CommandResult]
AsyncCommandHandler = Callable[[Command], Awaitable[CommandResult]]
EventType = TypeVar("EventType", bound=Event)
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Awaitable[None]]


# Combined types
AsyncOrSyncCommandHandler = Union[AsyncCommandHandler, CommandHandler]


class MessageBus:
    """Async message bus for command and event handling (Singleton).

    This is a simplified implementation of the Command Bus and Event Bus patterns,
    allowing for decoupled communication between components.
    """

    # --- Singleton Pattern ---
    _instance: Optional["MessageBus"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MessageBus":
        """
        Ensure only one instance is created (Singleton pattern).
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the message bus (only once).
        Sets up handler storage, event queue, and observability handlers.
        """
        if getattr(self, "_initialized", False):
            return

        self._command_handlers: Dict[
            SessionID, Dict[Type[Command], AsyncCommandHandler]
        ] = {}
        self._event_handlers: Dict[
            SessionID, Dict[Type[Event], List[AsyncEventHandler]]
        ] = {}
        self._event_queue: Optional[asyncio.Queue[Event]] = None
        self._processing_task: Optional[asyncio.Task[None]] = None
        self._observability_handlers: List[ObservabilityEventHandler] = []
        self._suppress_event_errors: bool = True
        self.event_handler_errors: List[Exception] = []
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._new_event_signal: asyncio.Event = asyncio.Event()
        self._handler_timeout: float = 30.0  # Default 30 second timeout
        logger.info("MessageBus initialized")
        self._initialized = True
        self.data_dir = os.path.dirname(os.path.abspath(__file__))

    async def reset(self) -> None:
        """
        Stops the bus if running. Reset the message bus to its initial state.
        """
        await self.stop()
        # Clear all handlers
        self._command_handlers.clear()
        self._event_handlers.clear()
        self.event_handler_errors.clear()
        self._observability_handlers.clear()
        # Create new event objects to avoid event loop binding issues
        self._shutdown_event = asyncio.Event()
        self._new_event_signal = asyncio.Event()
        # Reset to defaults
        self._handler_timeout = 30.0
        self._suppress_event_errors = True
        logger.info("MessageBus reset")

    def suppress_event_errors(self) -> None:
        """
        Surpress errors during event handling.
        """
        self._suppress_event_errors = True

    def unsuppress_event_errors(self) -> None:
        """
        Unsupress errors during event handling.
        """
        self._suppress_event_errors = False

    def set_handler_timeout(self, timeout: float) -> None:
        """
        Set the timeout for event and command handlers.
        
        Args:
            timeout: Timeout in seconds for handlers to complete
        """
        self._handler_timeout = timeout
        logger.info(f"Handler timeout set to {timeout} seconds")

        """
        Register an observability handler for this message bus.
        Registers the handler for both general and specific observability events.
        """

    def create_session(self, id_input: Optional[str] = None) -> BusSession:
        """
        Create a new session for grouping related commands and events.
        Args:
            id: Optional session identifier. If not provided, one will be generated.
        Returns:
            A new BusSession instance.
        """
        return BusSession(id=id_input)

    async def start(self) -> None:
        """
        Start the message bus event processing loop.
        Creates the event queue and launches the event processing task if not already running.
        """
        if self._processing_task is None:
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
                logger.info("Event queue created")
            await self._load_queue()
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("MessageBus started")
        else:
            logger.warning("MessageBus already running")

    async def stop(self) -> None:
        """
        Stop the message bus event processing loop.
        Cancels the event processing task and cleans up.
        """
        if self._processing_task:
            logger.info("Stopping message bus...")
            self._shutdown_event.set()
            
            await self._dump_queue()
            self._event_queue = None

            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
                logger.info("MessageBus stopped successfully")
            except asyncio.CancelledError:
                logger.info("MessageBus task cancelled successfully")
            except Exception as e:
                logger.exception(f"Error during MessageBus shutdown: {e}")
            finally:
                self._processing_task = None
        else:
            logger.info("MessageBus already stopped or never started")

    def register_observability_handler(self, handler: ObservabilityEventHandler) -> None:
        """
        Register an observability handler for a specific session.
        """
        # TODO: add tracing and span
        # TODO: add option to await or not await
        self._observability_handlers.append(handler)

    def register_command_handler(
        self,
        command_type: Type[CommandType],
        handler: AsyncOrSyncCommandHandler,
        session_id: str = "ROOT",
    ) -> None:
        """
        Register a command handler for a specific command type and session.
        Args:
            session_id: The session identifier (or 'ROOT').
            command_type: The type of command to handle.
            handler: The handler function/coroutine.
        Raises:
            ValueError: If a handler is already registered for the command in this session.
        """

        if session_id not in self._command_handlers:
            self._command_handlers[SessionID(session_id)] = {}

        # Check if handler is already wrapped
        if not is_async_function(handler):
            # Only wrap if not already wrapped
            if not hasattr(handler, '_is_wrapped'):
                handler = self._wrap_command_handler_as_async(cast(CommandHandler, handler))

        if command_type in self._command_handlers[SessionID(session_id)]:
            raise ValueError(
                f"Command handler for {command_type} already registered in session {session_id}"
            )

        self._command_handlers[SessionID(session_id)][command_type] = cast(
            AsyncCommandHandler, handler
        )
        logger.debug(
            f"Registered command handler for {command_type} in session {session_id}"
        )  # TODO test

    def register_event_handler(
        self,
        event_type: Type[EventType],
        handler: Union[AsyncEventHandler, EventHandler],
        session_id: SessionID = SessionID("ROOT"),
    ) -> None:
        """
        Register an event handler for a specific event type and session.
        Args:
            session_id: The session identifier (or 'ROOT').
            event_type: The type of event to handle.
            handler: The handler function/coroutine.
        """

        if session_id not in self._event_handlers:
            self._event_handlers[SessionID(session_id)] = {}

        if event_type not in self._event_handlers[SessionID(session_id)]:
            self._event_handlers[SessionID(session_id)][event_type] = []

        # Check if handler is already wrapped
        if not is_async_function(handler):
            # Only wrap if not already wrapped
            if not hasattr(handler, '_is_wrapped'):
                handler = self._wrap_event_handler_as_async(cast(EventHandler, handler))

        self._event_handlers[SessionID(session_id)][event_type].append(
            cast(AsyncEventHandler, handler)
        )
        logger.debug(f"Registered event handler for {event_type} in session {session_id}")

    def unregister_session_handlers(self, session_id: SessionID) -> None:
        """
        Unregister all command and event handlers for a specific session.
        Args:
            session_id: The session identifier.
        """
        command_handlers_removed = 0
        event_handlers_removed = 0
        
        if session_id in self._command_handlers:
            command_handlers_removed = len(self._command_handlers[session_id])
            del self._command_handlers[session_id]
            logger.debug(
                f"Unregistered {command_handlers_removed} command handlers for session {session_id}"
            )

        if session_id in self._event_handlers:
            event_handlers_removed = sum(
                len(handlers) for handlers in self._event_handlers[session_id].values()
            )
            del self._event_handlers[session_id]
            logger.debug(
                f"Unregistered {event_handlers_removed} event handlers for session {session_id}"
            )
            
        if command_handlers_removed == 0 and event_handlers_removed == 0:
            logger.debug(f"No handlers to unregister for session {session_id}")

    def unregister_command_handler(
        self, command_type: Type[CommandType], session_id: str = "ROOT"
    ) -> None:
        """
        Unregister a command handler for a specific command type and session.
        Args:
            command_type: The type of command.
            session_id: The session identifier (default 'ROOT').
        """
        if session_id in self._command_handlers:
            if command_type in self._command_handlers[session_id]:
                del self._command_handlers[session_id][command_type]
                logger.debug(
                    f"Unregistered command handler for {command_type} in session {session_id}"
                )
        else:
            raise ValueError(
                f"No command handlers to unregister for session {session_id}"
            )

    def unregister_event_handlers(
        self, event_type: Type[EventType], session_id: SessionID = SessionID("ROOT")
    ) -> None:
        """
        Unregister an event handler for a specific event type and session.
        Args:
            event_type: The type of event.
            session_id: The session identifier (default 'ROOT').
        """
        if session_id in self._event_handlers:
            if event_type in self._event_handlers[session_id]:
                del self._event_handlers[session_id][event_type]
                logger.debug(
                    f"Unregistered event handler for {event_type} in session {session_id}"
                )
        else:
            raise ValueError(f"No event handlers to unregister for session {session_id}")

    # --- Command Execution and Event Publishing ---

    async def execute(self, command: Command) -> CommandResult:
        """
        Execute a command and return its result.
        Args:
            command: The command instance to execute.
        Returns:
            CommandResult: The result of command execution.
        Raises:
            ValueError: If no handler is registered for the command type.
        """
        command_type = type(command)

        handler = None
        if command.session_id in self._command_handlers:
            handler = self._command_handlers[command.session_id].get(command_type)

        # Default to ROOT handlers if no session-specific handler is found
        if handler is None and SessionID("ROOT") in self._command_handlers:
            handler = self._command_handlers[SessionID("ROOT")].get(command_type)
            logger.warning(
                f"Defaulting to ROOT command handler for {command_type.__name__} in session {command.session_id}"
            )

        if handler is None:
            logger.error(
                f"No handler registered for command type {command_type.__name__}"
            )
            raise ValueError(f"No handler registered for command {command_type.__name__}")

        try:
            logger.info(f"Executing command {command_type.__name__}")
            await self.publish(
                CommandStartedEvent(command=command, session_id=command.session_id)
            )
            
            # Execute command with timeout
            if isinstance(command, ApprovalCommand):
                result: CommandResult = await asyncio.wait_for(
                    execute_approval_command(command, handler), 
                    timeout=self._handler_timeout
                )
            else:
                result: CommandResult = await asyncio.wait_for(
                    handler(command), 
                    timeout=self._handler_timeout
                )
            
            logger.info(f"Command {command_type.__name__} executed successfully")
            await self.publish(
                CommandResultEvent(command_result=result, session_id=command.session_id)
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"Command {command_type.__name__} timed out after {self._handler_timeout} seconds")
            failed_result = CommandResult(
                success=False,
                command_id=command.command_id,
                error=f"Handler timeout after {self._handler_timeout} seconds",
                metadata={"timeout": self._handler_timeout},
            )
            await self.publish(CommandResultEvent(command_result=failed_result))
            return failed_result
        except Exception as e:
            logger.exception(f"Error executing command {command_type.__name__}: {e}")
            failed_result = CommandResult(
                success=False,
                command_id=command.command_id,
                error=f"{type(e).__name__}: {e!s}",
                metadata={"exception_details": traceback.format_exc()},
            )
            await self.publish(CommandResultEvent(command_result=failed_result))
            return failed_result

    async def publish(self, event: Event, await_processing: bool = True) -> None:
        """
        Publish an event onto the event queue.
        Args:
            event: The event instance to publish.
        """

        logger.info(
            f"Publishing event {type(event).__name__} in session {event.session_id}"
        )

        try:
            if self._event_queue is None:
                raise ValueError("Event queue is not initialized")
            await self._event_queue.put(event)
            self._new_event_signal.set()
            logger.debug(f"Queued event: {type(event).__name__}")
        except Exception as e:
            logger.error(f"Error queing event: {e}", exc_info=True)
        finally:
            if not isinstance(event, ScheduledEvent) and await_processing:
                await self.ensure_events_processed()

    async def _process_events(self) -> None:
        """
        Process events from the queue indefinitely.
        Handles each event by dispatching to registered handlers.
        Uses efficient event-driven waiting and batch processing.
        """
        logger.info("Event processing loop starting")
        BATCH_SIZE = 10  # Process up to 10 events per batch
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for events or shutdown signal
                if self._event_queue is None or self._event_queue.empty():
                    await asyncio.wait(
                        [
                            asyncio.create_task(self._new_event_signal.wait()),
                            asyncio.create_task(self._shutdown_event.wait())
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Clear the signal for next iteration
                    self._new_event_signal.clear()
                    
                    # Check if we should shutdown
                    if self._shutdown_event.is_set():
                        break
                
                # Process events in batches for better performance
                batch_count = 0
                events_to_requeue = []
                next_scheduled_time = None
                
                while (not self._event_queue.empty() and 
                       batch_count < BATCH_SIZE and 
                       not self._shutdown_event.is_set()):
                    
                    try:
                        event = await self._event_queue.get()
                        batch_count += 1
                        logger.debug(f"Dequeued event {type(event).__name__}")

                        # Check if scheduled event is due
                        if isinstance(event, ScheduledEvent):
                            now = datetime.now()
                            if event.scheduled_time > now:
                                events_to_requeue.append(event)
                                # Track the earliest scheduled time for delay calculation
                                if next_scheduled_time is None or event.scheduled_time < next_scheduled_time:
                                    next_scheduled_time = event.scheduled_time
                                logger.debug(f"Event {type(event).__name__} is scheduled for {event.scheduled_time}, will requeue")
                                continue

                        # Handle the event
                        try:
                            await self._handle_event(event)
                        except Exception:
                            logger.exception(f"Error processing event {type(event).__name__}")
                        finally:
                            self._event_queue.task_done()
                            
                    except asyncio.CancelledError:
                        logger.info("Event processing batch cancelled")
                        raise
                
                # Requeue scheduled events that aren't due yet
                for event in events_to_requeue:
                    await self._event_queue.put(event)
                    self._event_queue.task_done()
                    
                # If we have scheduled events, add a small delay to avoid busy waiting
                if next_scheduled_time:
                    delay = min(0.1, max(0.01, (next_scheduled_time - datetime.now()).total_seconds()))
                    if delay > 0:
                        await asyncio.sleep(delay)

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                raise
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                # Brief pause before retrying on error
                await asyncio.sleep(0.1)
                
        logger.info("Event processing loop shutting down")


    async def ensure_events_processed(self) -> None:
        """
        Ensure all non-scheduled events in the queue are processed.
        Signals the event processor to wake up and process events.
        """
        if self._event_queue is None:
            return

        # Signal the event processor to wake up
        self._new_event_signal.set()
        
        # Give a brief moment for events to be processed
        await asyncio.sleep(0.01)
        
        # Wait for current events to be processed (with timeout)
        max_wait = 1.0  # Maximum 1 second wait
        start_time = asyncio.get_event_loop().time()
        
        while (not self._event_queue.empty() and 
               (asyncio.get_event_loop().time() - start_time) < max_wait):
            await asyncio.sleep(0.01)

    async def _handle_event(self, event: Event) -> None:
        """
        Handle a single event by calling all registered handlers.
        Args:
            event: The event instance to handle.
        """
        event_type = type(event)

        handlers = []
        # handle session specific handlers
        if event.session_id in self._event_handlers and event.session_id != "ROOT":
            if event_type in self._event_handlers[event.session_id]:
                session_handlers = self._event_handlers[event.session_id][event_type]
                if session_handlers:  # Only if there are actually handlers
                    handlers.extend(session_handlers)  # type: ignore

        # Default to ROOT handlers if no session-specific handler is found
        if not handlers and event.session_id != "ROOT":
            # there is no session handlers, so we use ROOT handlers if possible
            if SessionID("ROOT") in self._event_handlers:
                # there are root handlers, so we use them
                if event_type in self._event_handlers[SessionID("ROOT")]:
                    handlers.extend(self._event_handlers[SessionID("ROOT")][event_type])  # type: ignore
                    logger.warning(
                        f"Defaulting to ROOT event handler for {event_type} in session {event.session_id}"
                    )

        # handle root handlers
        if event.session_id == "ROOT" and SessionID("ROOT") in self._event_handlers:
            if event_type in self._event_handlers[SessionID("ROOT")]:
                handlers.extend(self._event_handlers[SessionID("ROOT")][event_type])  # type: ignore

        # Global handlers handle all events
        if SessionID("GLOBAL") in self._event_handlers:
            if event_type in self._event_handlers[SessionID("GLOBAL")]:
                handlers.extend(self._event_handlers[SessionID("GLOBAL")][event_type])  # type: ignore
            logger.info(
                f"Using GLOBAL event handlers {self._event_handlers[SessionID('GLOBAL')]} for {event_type} in session{event.session_id}"
            )

        if not handlers:
            logger.debug(
                f"No non-observability handler registered for event type {event_type}"
            )

        for handler in self._observability_handlers:
            logger.debug(
                f"Dispatching event {event_type} in session {event.session_id} to observability handler {handler.__class__.__name__}"
            )
            try:
                await handler.handle(event)
            except Exception as e:
                logger.exception(
                    f"Error in observability handler {handler.__name__}: {e}"
                )
                if not self._suppress_event_errors:
                    raise e
                else:
                    self.event_handler_errors.append(e)

        logger.debug(
            f"Dispatching event {event_type} in session {event.session_id} to {len(handlers)} handlers"  # type: ignore
        )
        # Create timeout-wrapped tasks for handlers
        timeout_tasks = [
            asyncio.create_task(asyncio.wait_for(handler(event), timeout=self._handler_timeout))
            for handler in handlers
        ]
        results = await asyncio.gather(*timeout_tasks, return_exceptions=True)  # type: ignore
        for i, result in enumerate(results):  # type: ignore
            if isinstance(result, Exception):
                self.event_handler_errors.append(result)
                handler_name = getattr(handlers[i], "__qualname__", repr(handlers[i]))  # type: ignore
                
                if isinstance(result, asyncio.TimeoutError):
                    logger.error(
                        f"Handler '{handler_name}' for {event_type} timed out after {self._handler_timeout} seconds"
                    )
                else:
                    logger.exception(
                        f"Error in handler '{handler_name}' for {event_type}: {result}"
                    )
                    
                if not self._suppress_event_errors:
                    raise result
                else:
                    await self.publish(
                        EventHandlerFailedEvent(
                            event=event, handler=handler_name, exception=result
                        )
                    )

    def _wrap_event_handler_as_async(self, handler: EventHandler) -> AsyncEventHandler:
        async def async_wrapper(event: Event):
            return handler(event)

        async_wrapper.function = handler  # type: ignore[attr-defined]
        async_wrapper._is_wrapped = True  # type: ignore[attr-defined]

        return async_wrapper

    def _wrap_command_handler_as_async(
        self, handler: CommandHandler
    ) -> AsyncCommandHandler:
        async def async_wrapper(command: Command):
            return handler(command)

        async_wrapper.function = handler  # type: ignore[attr-defined]
        async_wrapper._is_wrapped = True  # type: ignore[attr-defined]

        return async_wrapper

    async def _dump_queue(self) -> None:
        """
        Dump the event queue to a file.
        """
        if self._event_queue is None:
            return
        
        events : List[ScheduledEvent] = []
        while not self._event_queue.empty():
            event = await self._event_queue.get() # type: ignore
            if isinstance(event, ScheduledEvent):
                events.append(event)
        save_unfinished_events(events)

    async def _load_queue(self) -> None:
        """
        Load the event queue from a file.
        """
        if self._event_queue is None:
            return
        events : List[ScheduledEvent] = get_and_delete_unfinished_events()
        for event in events:
            await self._event_queue.put(event) # type: ignore

    async def get_events(self, session_id: SessionID) -> List[Event]:
        """
        Get all events for a session without removing them from the queue.
        """

        async with asyncio.Lock():
            
            if self._event_queue is None:
                return []
            
            events: List[Event] = []
            temp_events: List[Event] = []
            
            # Get all events from the queue temporarily
            while not self._event_queue.empty():
                event = await self._event_queue.get()
                temp_events.append(event)
                if event.session_id == session_id:
                    events.append(event)
            
            # Put all events back into the queue
            for event in temp_events:
                await self._event_queue.put(event)
            
        return events

def bus_exception_hook(bus: MessageBus) -> None:
    """
    Allows the bus to cleanup when an exception is raised globally.
    """
    def bus_excepthook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
        logger.info("Global unhandled exception caught by bus excepthook!")
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a task to stop the bus
                loop.create_task(bus.stop())
            else:
                # If loop is not running, run the stop method
                loop.run_until_complete(bus.stop())
        except RuntimeError:
            # No event loop available, try to create one
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bus.stop())
                loop.close()
            except Exception as e:
                print(f"Failed to cleanup bus: {e}")
        
        # Exit the program
        sys.exit(1)
    sys.excepthook = bus_excepthook