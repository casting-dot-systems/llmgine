"""Handler registry implementation for the message bus.

This module provides a clean implementation of handler registration and lookup,
replacing the complex nested dictionary approach with a more maintainable design.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Type

from llmgine.bus.interfaces import (
    AsyncCommandHandler,
    AsyncEventHandler,
    HandlerPriority,
    IHandlerRegistry,
)
from llmgine.llm import SessionID
from llmgine.messages.commands import Command
from llmgine.messages.events import Event


logger = logging.getLogger(__name__)


@dataclass
class EventHandlerEntry:
    """Entry for an event handler with priority."""
    
    handler: AsyncEventHandler
    priority: int = HandlerPriority.NORMAL
    
    def __lt__(self, other: "EventHandlerEntry") -> bool:
        """Sort by priority (lower number = higher priority)."""
        return self.priority < other.priority


@dataclass
class HandlerRegistry(IHandlerRegistry):
    """Thread-safe handler registry implementation.
    
    This implementation simplifies handler management by:
    - Removing the confusing ROOT/GLOBAL distinction
    - Using a single "BUS" scope for bus-wide handlers
    - Providing clear session-scoped handler registration
    - Supporting handler priorities for event handlers
    """
    
    _command_handlers: Dict[SessionID, Dict[Type[Command], AsyncCommandHandler]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    _event_handlers: Dict[SessionID, Dict[Type[Event], List[EventHandlerEntry]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def register_command_handler(
        self,
        command_type: Type[Command],
        handler: AsyncCommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Register a command handler for a specific command type and session.
        
        Args:
            command_type: The type of command to handle
            handler: The async handler function
            session_id: Session scope (defaults to "BUS" for bus-wide)
            
        Raises:
            ValueError: If a handler is already registered for this command/session
        """
        async with self._lock:
            if command_type in self._command_handlers[session_id]:
                raise ValueError(
                    f"Command handler for {command_type.__name__} already registered "
                    f"in session {session_id}"
                )
            
            self._command_handlers[session_id][command_type] = handler
            logger.debug(
                f"Registered command handler for {command_type.__name__} "
                f"in session {session_id}"
            )
    
    async def register_event_handler(
        self,
        event_type: Type[Event],
        handler: AsyncEventHandler,
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Register an event handler for a specific event type and session.
        
        Args:
            event_type: The type of event to handle
            handler: The async handler function
            session_id: Session scope (defaults to "BUS" for bus-wide)
            priority: Handler priority (lower number = higher priority)
        """
        async with self._lock:
            entry = EventHandlerEntry(handler=handler, priority=priority)
            handlers = self._event_handlers[session_id][event_type]
            handlers.append(entry)
            # Keep handlers sorted by priority
            handlers.sort()
            
            logger.debug(
                f"Registered event handler for {event_type.__name__} "
                f"in session {session_id} with priority {priority}"
            )
    
    async def get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[AsyncCommandHandler]:
        """Get the command handler for a specific command type and session.
        
        Args:
            command_type: The type of command
            session_id: Session to check first
            
        Returns:
            The handler if found, None otherwise
            
        Note:
            If no session-specific handler is found, falls back to BUS scope
        """
        async with self._lock:
            # Try session-specific handler first
            handler = self._command_handlers.get(session_id, {}).get(command_type)
            
            # Fall back to BUS scope if not found and session is not BUS
            if handler is None and session_id != SessionID("BUS"):
                handler = self._command_handlers.get(SessionID("BUS"), {}).get(command_type)
                if handler:
                    logger.debug(
                        f"Using BUS-scoped handler for {command_type.__name__} "
                        f"(no handler in session {session_id})"
                    )
            
            return handler
    
    async def get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[AsyncEventHandler]:
        """Get all event handlers for a specific event type and session.
        
        Args:
            event_type: The type of event
            session_id: Session to get handlers for
            
        Returns:
            List of handlers (session-specific + BUS scope), sorted by priority
            
        Note:
            Returns both session-specific and BUS-scoped handlers
        """
        async with self._lock:
            handlers: List[EventHandlerEntry] = []
            
            # Get session-specific handlers
            if session_id in self._event_handlers:
                handlers.extend(self._event_handlers[session_id].get(event_type, []))
            
            # Add BUS-scoped handlers if session is not BUS
            if session_id != SessionID("BUS") and SessionID("BUS") in self._event_handlers:
                handlers.extend(self._event_handlers[SessionID("BUS")].get(event_type, []))
            
            # Sort by priority and extract handler functions
            handlers.sort()
            return [entry.handler for entry in handlers]
    
    async def unregister_session(self, session_id: SessionID) -> None:
        """Remove all handlers for a specific session.
        
        Args:
            session_id: Session to clean up
            
        Note:
            BUS scope handlers are never removed by this method
        """
        if session_id == SessionID("BUS"):
            logger.warning("Cannot unregister BUS scope handlers")
            return
            
        async with self._lock:
            # Remove command handlers
            num_cmd = len(self._command_handlers.get(session_id, {}))
            if session_id in self._command_handlers:
                del self._command_handlers[session_id]
            
            # Remove event handlers  
            num_evt = sum(
                len(handlers) 
                for handlers in self._event_handlers.get(session_id, {}).values()
            )
            if session_id in self._event_handlers:
                del self._event_handlers[session_id]
            
            if num_cmd > 0 or num_evt > 0:
                logger.info(
                    f"Unregistered session {session_id}: "
                    f"{num_cmd} command handlers, {num_evt} event handlers"
                )
    
    async def get_all_sessions(self) -> Set[SessionID]:
        """Get all active session IDs."""
        async with self._lock:
            cmd_sessions = set(self._command_handlers.keys())
            evt_sessions = set(self._event_handlers.keys())
            return cmd_sessions | evt_sessions
    
    async def get_handler_stats(self) -> Dict[str, int]:
        """Get statistics about registered handlers."""
        async with self._lock:
            total_commands = sum(
                len(handlers) for handlers in self._command_handlers.values()
            )
            total_events = sum(
                sum(len(h) for h in handlers.values())
                for handlers in self._event_handlers.values()
            )
            
            return {
                "total_sessions": len(await self.get_all_sessions()),
                "total_command_handlers": total_commands,
                "total_event_handlers": total_events,
                "bus_command_handlers": len(self._command_handlers.get(SessionID("BUS"), {})),
                "bus_event_handlers": sum(
                    len(h) for h in self._event_handlers.get(SessionID("BUS"), {}).values()
                ),
            }
    
    # IHandlerRegistry interface implementation (sync versions)
    def register_command_handler(
        self,
        command_type: Type[Command],
        handler: AsyncCommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Synchronous wrapper for async register_command_handler."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context, can't use run_until_complete
            task = asyncio.create_task(
                self.async_register_command_handler(command_type, handler, session_id)
            )
            # For sync interface, we'll just schedule it
            return
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                self.async_register_command_handler(command_type, handler, session_id)
            )
            loop.close()
    
    def register_event_handler(
        self,
        event_type: Type[Event],
        handler: AsyncEventHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Synchronous wrapper for async register_event_handler."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            task = asyncio.create_task(
                self.async_register_event_handler(event_type, handler, session_id)
            )
            return
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                self.async_register_event_handler(event_type, handler, session_id)
            )
            loop.close()
    
    def get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[AsyncCommandHandler]:
        """Synchronous wrapper for async get_command_handler."""
        try:
            loop = asyncio.get_running_loop()
            # In async context, return None for now
            # This is a limitation of the sync interface
            return None
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.async_get_command_handler(command_type, session_id)
            )
            loop.close()
            return result
    
    def get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[AsyncEventHandler]:
        """Synchronous wrapper for async get_event_handlers."""
        try:
            loop = asyncio.get_running_loop()
            # In async context, return empty list for now
            # This is a limitation of the sync interface
            return []
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.async_get_event_handlers(event_type, session_id)
            )
            loop.close()
            return result
    
    def unregister_session(self, session_id: SessionID) -> None:
        """Synchronous wrapper for async unregister_session."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            task = asyncio.create_task(self.async_unregister_session(session_id))
            return
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.async_unregister_session(session_id))
            loop.close()
    
    # Add prefixed async methods to match the async interface
    async_register_command_handler = register_command_handler
    async_register_event_handler = register_event_handler  
    async_get_command_handler = get_command_handler
    async_get_event_handlers = get_event_handlers
    async_unregister_session = unregister_session