"""Core message bus implementation for handling commands and events.

The message bus is the central communication mechanism in the application,
providing a way for components to communicate without direct dependencies.
"""

import asyncio
import contextvars
import logging
import traceback
from dataclasses import asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

# Import only what's needed at the module level and use local imports for the rest
# to avoid circular dependencies
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import (
    CommandResultEvent,
    CommandStartedEvent,
    Event,
    EventHandlerFailedEvent,
)
from llmgine.observability.handlers.base import ObservabilityEventHandler

# Get the base logger and wrap it with the adapter
logger = logging.getLogger(__name__)

# Context variable to hold the current session ID
trace: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace", default=None
)
span: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("span", default=None)

TCommand = TypeVar("TCommand", bound=Command)
TEvent = TypeVar("TEvent", bound=Event)
CommandHandler = Callable[[TCommand], CommandResult]
AsyncCommandHandler = Callable[[TCommand], "asyncio.Future[CommandResult]"]
EventHandler = Callable[[TEvent], None]
AsyncEventHandler = Callable[[TEvent], "asyncio.Future[None]"]


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

        self._command_handlers: Dict[str, Dict[Type[Command], AsyncCommandHandler]] = {}
        self._event_handlers: Dict[str, Dict[Type[Event], List[AsyncEventHandler]]] = {}
        self._event_queue: Optional[asyncio.Queue] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._observability_handlers: List[ObservabilityEventHandler] = []
        self._suppress_event_errors: bool = True
        self.event_handler_errors: List[Exception] = []
        logger.info("MessageBus initialized")
        self._initialized = True

    async def reset(self) -> None:
        """
        Stops the bus if running. Reset the message bus to its initial state.
        """
        await self.stop()
        self._command_handlers: Dict[str, Dict[Type[Command], AsyncCommandHandler]] = {}
        self._event_handlers: Dict[str, Dict[Type[Event], List[AsyncEventHandler]]] = {}
        self._event_queue: Optional[asyncio.Queue] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._suppress_event_errors: bool = True
        self._observability_handlers: List[ObservabilityEventHandler] = []
        self.event_handler_errors: List[Exception] = []
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

            if self._event_queue is not None:
                self._processing_task = asyncio.create_task(self._process_events())
                logger.info("MessageBus started")
            else:
                logger.error("Failed to create event queue, MessageBus cannot start")
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
            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
                logger.info("MessageBus stopped successfully")
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"MessageBus stop issue: {type(e).__name__}")
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
        self._observability_handlers.append(handler)

    def register_command_handler(
        self,
        command_type: Type[TCommand],
        handler: CommandHandler,
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
        session_id = session_id or "ROOT"

        if session_id not in self._command_handlers:
            self._command_handlers[session_id] = {}

        async_handler = self._wrap_handler_as_async(handler)

        if command_type in self._command_handlers[session_id]:
            raise ValueError(
                f"Command handler for {command_type} already registered in session {session_id}"
            )

        self._command_handlers[session_id][command_type] = async_handler
        logger.debug(
            f"Registered command handler for {command_type} in session {session_id}"
        )  # TODO test

    def register_event_handler(
        self, event_type: Type[TEvent], handler: EventHandler, session_id: str = "ROOT"
    ) -> None:
        """
        Register an event handler for a specific event type and session.
        Args:
            session_id: The session identifier (or 'ROOT').
            event_type: The type of event to handle.
            handler: The handler function/coroutine.
        """
        session_id = session_id or "ROOT"

        if session_id not in self._event_handlers:
            self._event_handlers[session_id] = {}

        if event_type not in self._event_handlers[session_id]:
            self._event_handlers[session_id][event_type] = []

        async_handler = self._wrap_handler_as_async(handler)
        self._event_handlers[session_id][event_type].append(async_handler)
        logger.debug(f"Registered event handler for {event_type} in session {session_id}")

    def unregister_session_handlers(self, session_id: str) -> None:
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
        self, command_type: Type[TCommand], session_id: str = "ROOT"
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
        self, event_type: Type[TEvent], session_id: str = "ROOT"
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
        if command.session_id is None:
            raise ValueError("Command has no session ID")

        handler = None
        if command.session_id in self._command_handlers:
            handler = self._command_handlers[command.session_id].get(command_type)

        # Default to ROOT handlers if no session-specific handler is found
        if handler is None and "ROOT" in self._command_handlers:
            handler = self._command_handlers["ROOT"].get(command_type)
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
                error=f"{type(e).__name__}: {str(e)}",
                metadata={"exception_details": traceback.format_exc()},
            )
            await self.publish(CommandResultEvent(command_result=failed_result))
            return failed_result

    async def publish(self, event: Event) -> None:
        """
        Publish an event onto the event queue.
        Args:
            event: The event instance to publish.
        """

        logger.info(
            f"Publishing event {type(event).__name__} in session {event.session_id}"
        )

        try:
            await self._event_queue.put(event)
            logger.debug(f"Queued event: {type(event).__name__}")
        except Exception as e:
            logger.error(f"Error queing event: {e}", exc_info=True)

    async def _process_events(self) -> None:
        """
        Process events from the queue indefinitely.
        Handles each event by dispatching to registered handlers.
        """
        logger.info("Event processing loop starting")

        while True:
            try:
                event = await self._event_queue.get()
                logger.debug(f"Dequeued event {type(event).__name__}")

                try:
                    await self._handle_event(event)
                except asyncio.CancelledError:
                    logger.warning("Event handling cancelled")
                    raise
                except Exception:
                    logger.exception(f"Error processing event {type(event).__name__}")
                finally:
                    self._event_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in event processing loop: {e}")
                await asyncio.sleep(0.1)

        logger.info("Event processing loop finished")

    async def ensure_events_processed(self) -> None:
        """
        Ensure all events in the queue are processed.
        """
        while not self._event_queue.empty():
            event = await self._event_queue.get()
            await self._handle_event(event)

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
                handlers.extend(self._event_handlers[event.session_id][event_type])

            # Default to ROOT handlers if no session-specific handler is found
        elif event.session_id != "ROOT":
            # there is no session in event, so we use ROOT handlers if possible
            if "ROOT" in self._event_handlers:
                # there is root handlers, so we use them
                if event_type in self._event_handlers["ROOT"]:
                    handlers.extend(self._event_handlers["ROOT"][event_type])
                    logger.warning(
                        f"Defaulting to ROOT event handler for {event_type} in session {event.session_id}"
                    )

        # handle root handlers
        if event.session_id == "ROOT" and "ROOT" in self._event_handlers:
            if event_type in self._event_handlers["ROOT"]:
                handlers.extend(self._event_handlers["ROOT"][event_type])

        # Global handlers handle all events
        if "GLOBAL" in self._event_handlers:
            if event_type in self._event_handlers["GLOBAL"]:
                handlers.extend(self._event_handlers["GLOBAL"][event_type])
            logger.info(
                f"Using GLOBAL event handlers {self._event_handlers['GLOBAL']} for {event_type} in session{event.session_id}"
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
            f"Dispatching event {event_type} in session {event.session_id} to {len(handlers)} handlers"
        )
        tasks = [asyncio.create_task(handler(event)) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.event_handler_errors.append(result)
                handler_name = getattr(handlers[i], "__qualname__", repr(handlers[i]))
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

    def _wrap_handler_as_async(self, handler: Callable) -> Callable:
        """
        Convert synchronous handlers to asynchronous if needed.
        Args:
            handler: The handler function or coroutine.
        Returns:
            An async-compatible handler.
        """
        if asyncio.iscoroutinefunction(handler):
            return handler

        async def async_wrapper(*args, **kwargs):
            return handler(*args, **kwargs)

        async_wrapper.function = handler

        return async_wrapper
