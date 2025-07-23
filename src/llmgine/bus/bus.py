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
)
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.observability.manager import ObservabilityManager
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

    def __init__(self, observability: Optional[ObservabilityManager] = None) -> None:
        """
        Initialize the message bus (only once).
        Sets up handler storage, event queue, and observability.
        
        Args:
            observability: Optional ObservabilityManager instance
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
        self._observability: Optional[ObservabilityManager] = observability
        self._suppress_event_errors: bool = True
        self.event_handler_errors: List[Exception] = []
        logger.info("MessageBus initialized")
        self._initialized = True
        self.data_dir = os.path.dirname(os.path.abspath(__file__))

    async def reset(self) -> None:
        """
        Stops the bus if running. Reset the message bus to its initial state.
        """
        await self.stop()
        self.__init__()
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
            self._processing_task.cancel()
            
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

    def set_observability_manager(self, observability: ObservabilityManager) -> None:
        """
        Set the observability manager for this message bus.
        
        Args:
            observability: The ObservabilityManager instance
        """
        self._observability = observability

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

        if not is_async_function(handler):
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

        if not is_async_function(handler):
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
        if session_id not in self._command_handlers:
            logger.debug(f"No command handlers to unregister for session {session_id}")
            return

        if session_id in self._command_handlers:
            num_cmd_handlers = len(self._command_handlers[session_id])
            del self._command_handlers[session_id]
            logger.debug(
                f"Unregistered {num_cmd_handlers} command handlers for session {session_id}"
            )

        if session_id in self._event_handlers:
            num_event_handlers = sum(
                len(handlers) for handlers in self._event_handlers[session_id].values()
            )
            del self._event_handlers[session_id]
            logger.debug(
                f"Unregistered {num_event_handlers} event handlers for session {session_id}"
            )

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
            if isinstance(command, ApprovalCommand):
                result: CommandResult = await execute_approval_command(command, handler)
            else:
                result: CommandResult = await handler(command)
            
            logger.info(f"Command {command_type.__name__} executed successfully")
            await self.publish(
                CommandResultEvent(command_result=result, session_id=command.session_id)
            )
            return result

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

        # Direct call to observability - no event publishing
        if self._observability:
            self._observability.observe_event(event)

        try:
            if self._event_queue is None:
                raise ValueError("Event queue is not initialized")
            await self._event_queue.put(event)
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
        """
        logger.info("Event processing loop starting")

        while True:
            try:
                total_events = self._event_queue.qsize() # type: ignore
                while not self._event_queue.empty() and total_events > 0: # type: ignore
                    try:
                        total_events -= 1
                        event = await self._event_queue.get()  # type: ignore
                        logger.debug(f"Dequeued event {type(event).__name__}")

                        # if a scheduled event is not yet due, we queue it again
                        if isinstance(event, ScheduledEvent) and event.scheduled_time > datetime.now():
                            await self._event_queue.put(event) # type: ignore
                            logger.debug(f"Event {type(event).__name__} is scheduled for {event.scheduled_time}, queuing again")
                            continue

                        try:
                            await self._handle_event(event)
                        except asyncio.CancelledError:
                            logger.warning("Event handling cancelled")
                            raise
                        except Exception:
                            logger.exception(f"Error processing event {type(event).__name__}")
                        finally:
                            self._event_queue.task_done()  # type: ignore
                    except asyncio.CancelledError:
                        logger.info("Event processing loop cancelled")
                        raise
                
                # Leave time for other processes to run
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                raise
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.1)


    async def ensure_events_processed(self) -> None:
        """
        Ensure all non-scheduled events in the queue are processed.
        """
        if self._event_queue is None:
            return

        temp_queue: List[Event] = []
        while not self._event_queue.empty():
            event = await self._event_queue.get()
            if isinstance(event, ScheduledEvent) and event.scheduled_time > datetime.now():
                temp_queue.append(event)  # Save scheduled events for re-queuing
            else:
                await self._handle_event(event)
        # Re-queue scheduled events
        for event in temp_queue:
            await self._event_queue.put(event)

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
                handlers.extend(self._event_handlers[event.session_id][event_type])  # type: ignore

            # Default to ROOT handlers if no session-specific handler is found
        elif event.session_id != "ROOT":
            # there is no session in event, so we use ROOT handlers if possible
            if SessionID("ROOT") in self._event_handlers:
                # there is root handlers, so we use them
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

        # Observability is called in publish(), so we don't need to call it here again

        logger.debug(
            f"Dispatching event {event_type} in session {event.session_id} to {len(handlers)} handlers"  # type: ignore
        )
        tasks = [asyncio.create_task(handler(event)) for handler in handlers]  # type: ignore
        results = await asyncio.gather(*tasks, return_exceptions=True)  # type: ignore
        for i, result in enumerate(results):  # type: ignore
            if isinstance(result, Exception):
                self.event_handler_errors.append(result)
                handler_name = getattr(handlers[i], "__qualname__", repr(handlers[i]))  # type: ignore
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

        return async_wrapper

    def _wrap_command_handler_as_async(
        self, handler: CommandHandler
    ) -> AsyncCommandHandler:
        async def async_wrapper(command: Command):
            return handler(command)

        async_wrapper.function = handler  # type: ignore[attr-defined]

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