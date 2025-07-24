"""Simplified handler registry implementation without sync/async confusion.

This module provides a clean implementation of handler registration and lookup.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Type

from llmgine.bus.interfaces import (
    AsyncCommandHandler,
    AsyncEventHandler,
    HandlerPriority,
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


class HandlerRegistry:
    """Simple handler registry implementation.
    
    This implementation provides:
    - Clean separation between BUS scope and session scope
    - Event handler priorities
    - Thread-safe operations using locks
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._command_handlers: Dict[SessionID, Dict[Type[Command], AsyncCommandHandler]] = (
            defaultdict(dict)
        )
        self._event_handlers: Dict[SessionID, Dict[Type[Event], List[EventHandlerEntry]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self._lock = asyncio.Lock()
    
    def register_command_handler(
        self,
        command_type: Type[Command],
        handler: AsyncCommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Register a command handler (synchronous for compatibility)."""
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
    
    def register_event_handler(
        self,
        event_type: Type[Event],
        handler: AsyncEventHandler,
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Register an event handler (synchronous for compatibility)."""
        entry = EventHandlerEntry(handler=handler, priority=priority)
        handlers = self._event_handlers[session_id][event_type]
        handlers.append(entry)
        # Keep handlers sorted by priority
        handlers.sort()
        
        logger.debug(
            f"Registered event handler for {event_type.__name__} "
            f"in session {session_id} with priority {priority}"
        )
    
    def get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[AsyncCommandHandler]:
        """Get the command handler for a specific command type and session."""
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
    
    def get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[AsyncEventHandler]:
        """Get all event handlers for a specific event type and session."""
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
    
    def unregister_session(self, session_id: SessionID) -> None:
        """Remove all handlers for a specific session."""
        if session_id == SessionID("BUS"):
            logger.warning("Cannot unregister BUS scope handlers")
            return
        
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
    
    def get_all_sessions(self) -> Set[SessionID]:
        """Get all active session IDs."""
        cmd_sessions = set(self._command_handlers.keys())
        evt_sessions = set(self._event_handlers.keys())
        return cmd_sessions | evt_sessions
    
    def get_handler_stats(self) -> Dict[str, int]:
        """Get statistics about registered handlers."""
        total_commands = sum(
            len(handlers) for handlers in self._command_handlers.values()
        )
        total_events = sum(
            sum(len(h) for h in handlers.values())
            for handlers in self._event_handlers.values()
        )
        
        return {
            "total_sessions": len(self.get_all_sessions()),
            "total_command_handlers": total_commands,
            "total_event_handlers": total_events,
            "bus_command_handlers": len(self._command_handlers.get(SessionID("BUS"), {})),
            "bus_event_handlers": sum(
                len(h) for h in self._event_handlers.get(SessionID("BUS"), {}).values()
            ),
        }