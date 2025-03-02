import logging
import asyncio
from typing import Dict, List, Callable, Type, Optional, Union, Any
from concurrent.futures import ThreadPoolExecutor

from .commands import Command
from .events import Event


logger = logging.getLogger(__name__)


class CommandHandlerNotFound(Exception):
    """Raised when no handler is found for a command."""
    pass


class MessageBusException(Exception):
    """Base exception for message bus errors."""
    pass


class MessageBus:
    """Message bus for dispatching commands and publishing events.
    
    This implementation follows the CQRS pattern, separating command handling
    (which may modify state) from event handling (which reacts to state changes).
    
    The bus is implemented as a singleton to ensure a single point of message
    dispatching throughout the application.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the message bus with empty handler collections."""
        self._event_subscribers: Dict[str, List[Callable]] = {}
        self._command_handlers: Dict[Type, Callable] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._pending_events: List[Event] = []
        logger.info("Message bus initialized")

    def subscribe_event(self, event_type: str, handler: Callable):
        """Subscribe a handler to events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The callable that will be invoked when an event of this type is emitted
        """
        if event_type not in self._event_subscribers:
            self._event_subscribers[event_type] = []
        self._event_subscribers[event_type].append(handler)
        logger.debug(f"Handler {handler.__name__} subscribed to event type {event_type}")

    def register_command(self, command_type: Type, handler: Callable):
        """Register a handler for a specific command type.
        
        Args:
            command_type: The type of command to handle
            handler: The callable that will be invoked when a command of this type is dispatched
        """
        self._command_handlers[command_type] = handler
        logger.debug(f"Handler {handler.__name__} registered for command {command_type.__name__}")

    def emit(self, event: Event):
        """Emit an event to all its subscribers.
        
        Args:
            event: The event to emit
        """
        logger.debug(f"Emitting event: {event.event_type} (ID: {event.event_id})")
        
        if event.event_type in self._event_subscribers:
            for handler in self._event_subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error handling event {event.event_type} in {handler.__name__}: {str(e)}", exc_info=True)
        else:
            logger.debug(f"No subscribers found for event type: {event.event_type}")

    async def emit_async(self, event: Event):
        """Emit an event asynchronously to all its subscribers.
        
        Args:
            event: The event to emit
        """
        logger.debug(f"Emitting event asynchronously: {event.event_type} (ID: {event.event_id})")
        
        if event.event_type in self._event_subscribers:
            tasks = []
            for handler in self._event_subscribers[event.event_type]:
                task = asyncio.create_task(self._run_async(handler, event))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.debug(f"No subscribers found for event type: {event.event_type}")

    async def _run_async(self, handler: Callable, event: Event):
        """Run a handler asynchronously using the thread pool executor."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, handler, event)
        except Exception as e:
            logger.error(f"Error in async handler {handler.__name__}: {str(e)}", exc_info=True)

    def add_pending_event(self, event: Event):
        """Add an event to the pending events list.
        
        Args:
            event: The event to add
        """
        self._pending_events.append(event)
        
    def process_pending_events(self):
        """Process all pending events."""
        events = self._pending_events.copy()
        self._pending_events.clear()
        
        for event in events:
            self.emit(event)
        
        return events

    def dispatch(self, command: Command) -> Any:
        """Dispatch a command to its registered handler.
        
        Args:
            command: The command to dispatch
            
        Returns:
            The result of the command handler
            
        Raises:
            CommandHandlerNotFound: If no handler is registered for the command type
        """
        command_type = type(command)
        logger.debug(f"Dispatching command: {command_type.__name__} (ID: {command.command_id})")
        
        if command_type not in self._command_handlers:
            error_msg = f"No handler registered for command {command_type.__name__}"
            logger.error(error_msg)
            raise CommandHandlerNotFound(error_msg)
        
        handler = self._command_handlers[command_type]
        
        try:
            result = handler(command)
            
            # Process any pending events
            self.process_pending_events()
            
            return result
        except Exception as e:
            logger.error(f"Error handling command {command_type.__name__}: {str(e)}", exc_info=True)
            raise

    async def dispatch_async(self, command: Command) -> Any:
        """Dispatch a command asynchronously to its registered handler.
        
        Args:
            command: The command to dispatch
            
        Returns:
            The result of the command handler
            
        Raises:
            CommandHandlerNotFound: If no handler is registered for the command type
        """
        command_type = type(command)
        logger.debug(f"Dispatching command asynchronously: {command_type.__name__} (ID: {command.command_id})")
        
        if command_type not in self._command_handlers:
            error_msg = f"No handler registered for command {command_type.__name__}"
            logger.error(error_msg)
            raise CommandHandlerNotFound(error_msg)
        
        handler = self._command_handlers[command_type]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, handler, command)
            
            # Process any pending events asynchronously
            events = self.process_pending_events()
            
            return result
        except Exception as e:
            logger.error(f"Error handling command asynchronously {command_type.__name__}: {str(e)}", exc_info=True)
            raise


# Singleton instance for global access
message_bus = MessageBus()
