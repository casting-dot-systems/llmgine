from typing import Callable, Optional, Type, Any
import asyncio
import time
import uuid
import contextvars

# Import Event directly to avoid circular import
from llmgine.messages.events import Event, SessionStartEvent, SessionEndEvent
from llmgine.messages.commands import Command, CommandResult
from llmgine.llm import SessionID


class BusSession:
    """An **async** session for the message bus.

    Sessions group related operations and handlers together, allowing for
    automatic cleanup when the session ends.

    Usage:
        async with message_bus.create_session() as session:
            session.register_event_handler(EventType, handler_func)
            # Do work with the session...
            # On exit, all handlers are automatically unregistered
    """

    def __init__(self, id: Optional[str] = None):
        """Initialize a new bus session with a unique ID."""
        self.session_id = id or str(uuid.uuid4())
        self.start_time = time.time()
        self._bus = None  # Will be set lazily
        self._active = True

    @property
    def bus(self):
        """Get the message bus instance (lazy loading to avoid circular imports)."""
        if self._bus is None:
            from llmgine.bus.bus import MessageBus
            self._bus = MessageBus()
        return self._bus

    async def __aenter__(self):
        """Start the session and publish a session start event."""

        # Publish a session start event and await it
        await self.bus.publish(SessionStartEvent(session_id=self.session_id))
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Clean up the session, unregistering all handlers and publishing end event."""
        if not self._active:
            return

        try:
            # Unregister all event and command handlers for this session (synchronous)
            self.bus.unregister_session_handlers(self.session_id)

            # Publish session end event and await it
            end_event = SessionEndEvent(
                session_id=self.session_id, error=exc_value if exc_type else None
            )
            await self.bus.publish(end_event)

        finally:
            # Ensure the session is marked inactive even if cleanup fails
            self._active = False

    def register_event_handler(
        self, event_type: Type[Event], handler: Callable[[Event], Any]
    ):
        """Register an event handler for this session.

        Args:
            event_type: The type of event to handle
            handler: The handler function for events of this type
        """
        if not self._active:
            raise RuntimeError("Cannot register handlers on an inactive session")

        # Pass session_id explicitly to the bus registration method
        self.bus.register_event_handler(self.session_id, event_type, handler)
        return self  # For method chaining

    def register_command_handler(
        self, command_type: Type[Command], handler: Callable[[Command], CommandResult]
    ):
        """Register a command handler for this session.

        Args:
            command_type: The type of command to handle
            handler: The handler function for commands of this type
        """
        if not self._active:
            raise RuntimeError("Cannot register handlers on an inactive session")

        # Pass session_id explicitly to the bus registration method
        self.bus.register_command_handler(self.session_id, command_type, handler)
        return self  # For method chaining

    async def execute_with_session(self, command: Command) -> Any:
        """Execute a command with this session's ID.

        This is a helper method that sets the session_id on the command
        before executing it via the message bus and awaits the result.

        Args:
            command: The command to execute

        Returns:
            The result of the command execution
        """
        if not self._active:
            raise RuntimeError("Cannot execute commands on an inactive session")

        # Set session ID on the command
        command.session_id = self.session_id

        # Execute via the bus and await the result directly
        return await self.bus.execute(command)
