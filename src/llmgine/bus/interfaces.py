"""Interfaces and protocols for the message bus system.

This module defines the contracts for extensible message bus components.
"""

from abc import ABC, abstractmethod
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
    Protocol,
    runtime_checkable,
)

from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


# Type aliases for handlers
CommandType = TypeVar("CommandType", bound=Command)
EventType = TypeVar("EventType", bound=Event)
AsyncCommandHandler = Callable[[Command], Awaitable[CommandResult]]
AsyncEventHandler = Callable[[Event], Awaitable[None]]


@runtime_checkable
class IHandlerRegistry(Protocol):
    """Protocol for managing command and event handlers."""
    
    def register_command_handler(
        self,
        command_type: Type[CommandType],
        handler: AsyncCommandHandler,
        session_id: SessionID,
    ) -> None:
        """Register a command handler for a specific command type and session."""
        ...
    
    def register_event_handler(
        self,
        event_type: Type[EventType],
        handler: AsyncEventHandler,
        session_id: SessionID,
    ) -> None:
        """Register an event handler for a specific event type and session."""
        ...
    
    def get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[AsyncCommandHandler]:
        """Get the command handler for a specific command type and session."""
        ...
    
    def get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[AsyncEventHandler]:
        """Get all event handlers for a specific event type and session."""
        ...
    
    def unregister_session(self, session_id: SessionID) -> None:
        """Remove all handlers for a specific session."""
        ...


@runtime_checkable
class IEventQueue(Protocol):
    """Protocol for event queue operations."""
    
    async def put(self, event: Event) -> None:
        """Add an event to the queue."""
        ...
    
    async def get(self) -> Event:
        """Get an event from the queue, blocking if necessary."""
        ...
    
    def qsize(self) -> int:
        """Return the approximate size of the queue."""
        ...
    
    def empty(self) -> bool:
        """Return True if the queue is empty."""
        ...
    
    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete."""
        ...


@runtime_checkable
class IMessageBus(Protocol):
    """Protocol for the core message bus interface."""
    
    async def start(self) -> None:
        """Start the message bus event processing."""
        ...
    
    async def stop(self) -> None:
        """Stop the message bus event processing."""
        ...
    
    async def execute(self, command: Command) -> CommandResult:
        """Execute a command and return its result."""
        ...
    
    async def publish(self, event: Event) -> None:
        """Publish an event to be processed asynchronously."""
        ...
    
    def register_command_handler(
        self,
        command_type: Type[CommandType],
        handler: AsyncCommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Register a command handler."""
        ...
    
    def register_event_handler(
        self,
        event_type: Type[EventType],
        handler: AsyncEventHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Register an event handler."""
        ...


class HandlerMiddleware(ABC):
    """Abstract base class for handler middleware."""
    
    @abstractmethod
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Process a command through the middleware chain."""
        pass
    
    @abstractmethod
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Process an event through the middleware chain."""
        pass


class EventFilter(ABC):
    """Abstract base class for event filters."""
    
    @abstractmethod
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Determine if an event should be handled."""
        pass


class HandlerPriority:
    """Priority levels for event handlers."""
    
    HIGHEST = 0
    HIGH = 10
    NORMAL = 50
    LOW = 90
    LOWEST = 100