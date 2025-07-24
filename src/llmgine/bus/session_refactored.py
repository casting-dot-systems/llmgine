"""Refactored session management for the message bus.

This module provides improved session handling with better integration
with the refactored message bus.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type, Union, TYPE_CHECKING

from llmgine.bus.interfaces import HandlerPriority
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

if TYPE_CHECKING:
    from llmgine.bus.bus import MessageBus


@dataclass
class SessionStartEvent(Event):
    """Event published when a session starts."""
    pass


@dataclass
class SessionEndEvent(Event):
    """Event published when a session ends."""
    
    error: Optional[Exception] = None
    duration_seconds: float = 0.0


class BusSession:
    """Improved async session for the message bus.
    
    Sessions provide:
    - Scoped handler registration with automatic cleanup
    - Session-specific command and event handling
    - Performance tracking and metrics
    - Better integration with async context managers
    
    Usage:
        # As context manager
        async with bus.session() as session:
            session.register_event_handler(MyEvent, handler)
            result = await session.execute(MyCommand())
        
        # Manual lifecycle
        session = bus.create_session()
        await session.start()
        try:
            # Use session
        finally:
            await session.end()
    """
    
    def __init__(self, bus: "MessageBus", id: Optional[str] = None):
        """Initialize a new bus session.
        
        Args:
            bus: The message bus instance
            id: Optional session ID (auto-generated if not provided)
        """
        self.session_id = SessionID(id or str(uuid.uuid4()))
        self.bus = bus
        self.start_time = time.time()
        self._active = False
        self._handler_count = 0
    
    async def start(self) -> "BusSession":
        """Start the session and publish start event."""
        if self._active:
            raise RuntimeError("Session is already active")
        
        self._active = True
        self._start_time = time.time()
        
        # Publish session start event
        await self.bus.publish(
            SessionStartEvent(session_id=self.session_id),
            await_processing=False,
        )
        
        return self
    
    async def end(self, error: Optional[Exception] = None) -> None:
        """End the session and clean up resources."""
        if not self._active:
            return
        
        try:
            # Calculate session duration
            duration = time.time() - self.start_time
            
            # Unregister all handlers for this session
            self.bus.unregister_session_handlers(self.session_id)
            
            # Publish session end event
            await self.bus.publish(
                SessionEndEvent(
                    session_id=self.session_id,
                    error=error,
                    duration_seconds=duration,
                ),
                await_processing=False,
            )
            
        finally:
            self._active = False
    
    # --- Async Context Manager ---
    
    async def __aenter__(self) -> "BusSession":
        """Enter the session context."""
        return await self.start()
    
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Exit the session context."""
        await self.end(error=exc_value if exc_type else None)
    
    # --- Handler Registration ---
    
    def register_event_handler(
        self,
        event_type: Type[Event],
        handler: Union[Callable[[Event], None], Callable[[Event], Any]],
        priority: int = HandlerPriority.NORMAL,
    ) -> "BusSession":
        """Register an event handler for this session.
        
        Args:
            event_type: The type of event to handle
            handler: The handler function
            priority: Handler priority (lower = higher priority)
            
        Returns:
            Self for method chaining
        """
        if not self._active:
            raise RuntimeError("Cannot register handlers on inactive session")
        
        self.bus.register_event_handler(
            event_type, handler, self.session_id, priority
        )
        self._handler_count += 1
        
        return self
    
    def register_command_handler(
        self,
        command_type: Type[Command],
        handler: Union[
            Callable[[Command], CommandResult],
            Callable[[Command], Any],
        ],
    ) -> "BusSession":
        """Register a command handler for this session.
        
        Args:
            command_type: The type of command to handle
            handler: The handler function
            
        Returns:
            Self for method chaining
        """
        if not self._active:
            raise RuntimeError("Cannot register handlers on inactive session")
        
        self.bus.register_command_handler(
            command_type, handler, self.session_id
        )
        self._handler_count += 1
        
        return self
    
    # --- Command Execution ---
    
    async def execute(self, command: Command) -> CommandResult:
        """Execute a command with this session's context.
        
        Args:
            command: The command to execute
            
        Returns:
            The command result
        """
        if not self._active:
            raise RuntimeError("Cannot execute commands on inactive session")
        
        # Set session ID on the command
        command.session_id = self.session_id
        
        # Execute via the bus
        return await self.bus.execute(command)
    
    # --- Event Publishing ---
    
    async def publish(self, event: Event, await_processing: bool = True) -> None:
        """Publish an event with this session's context.
        
        Args:
            event: The event to publish
            await_processing: Whether to wait for event processing
        """
        if not self._active:
            raise RuntimeError("Cannot publish events on inactive session")
        
        # Set session ID on the event
        event.session_id = self.session_id
        
        # Publish via the bus
        await self.bus.publish(event, await_processing)
    
    # --- Session Information ---
    
    @property
    def is_active(self) -> bool:
        """Check if the session is active."""
        return self._active
    
    @property
    def duration(self) -> float:
        """Get the session duration in seconds."""
        return time.time() - self.start_time
    
    @property
    def handler_count(self) -> int:
        """Get the number of handlers registered in this session."""
        return self._handler_count
    
    def __repr__(self) -> str:
        """String representation of the session."""
        status = "active" if self._active else "inactive"
        return (
            f"BusSession(id={self.session_id}, status={status}, "
            f"handlers={self._handler_count}, duration={self.duration:.2f}s)"
        )