from dataclasses import dataclass, field
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
)

from llmgine.bus.interfaces import HandlerPriority
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

CommandHandler = Callable[[Command], Awaitable[CommandResult]]
EventHandler = Callable[[Event], Awaitable[None]]


@dataclass(order=True)
class EventHandlerEntry:
    priority: int
    handler: EventHandler = field(compare=False)


class HandlerRegistry:
    """
    Async-friendly handler registry that supports BUS scope and per-session scope.
    """
    def __init__(self) -> None:
        # Command handlers: either BUS or session-scoped
        self._bus_command_handlers: Dict[Type[Command], CommandHandler] = {}
        self._session_command_handlers: Dict[SessionID, Dict[Type[Command], CommandHandler]] = {}
        # Event handlers: BUS and session-scoped lists with priority ordering
        self._bus_event_handlers: Dict[Type[Event], List[EventHandlerEntry]] = {}
        self._session_event_handlers: Dict[SessionID, Dict[Type[Event], List[EventHandlerEntry]]] = {}

    # ------------------- Command handlers -------------------
    def register_command_handler(
        self,
        command_type: Type[Command],
        handler: CommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Synchronous version for backwards compatibility."""
        if session_id == SessionID("BUS"):
            if command_type in self._bus_command_handlers:
                raise ValueError(f"Command handler for {command_type.__name__} already registered")
            self._bus_command_handlers[command_type] = handler
        else:
            self._session_command_handlers.setdefault(session_id, {})
            if command_type in self._session_command_handlers[session_id]:
                raise ValueError(
                    f"Command handler for {command_type.__name__} already registered in session {session_id}"
                )
            self._session_command_handlers[session_id][command_type] = handler

    async def async_register_command_handler(
        self,
        command_type: Type[Command],
        handler: CommandHandler,
        session_id: SessionID = SessionID("BUS"),
    ) -> None:
        """Async version for testing."""
        self.register_command_handler(command_type, handler, session_id)

    def get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[CommandHandler]:
        """Synchronous version for backwards compatibility."""
        # prefer session-specific, fallback to BUS
        if session_id in self._session_command_handlers:
            if command_type in self._session_command_handlers[session_id]:
                return self._session_command_handlers[session_id][command_type]
        return self._bus_command_handlers.get(command_type)

    async def async_get_command_handler(
        self,
        command_type: Type[Command],
        session_id: SessionID,
    ) -> Optional[CommandHandler]:
        """Async version for testing."""
        return self.get_command_handler(command_type, session_id)

    # ------------------- Event handlers -------------------
    def register_event_handler(
        self,
        event_type: Type[Event],
        handler: EventHandler,
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Synchronous version for backwards compatibility."""
        entry = EventHandlerEntry(priority=int(priority), handler=handler)
        if session_id == SessionID("BUS"):
            self._bus_event_handlers.setdefault(event_type, [])
            self._bus_event_handlers[event_type].append(entry)
            self._bus_event_handlers[event_type].sort()
        else:
            self._session_event_handlers.setdefault(session_id, {})
            self._session_event_handlers[session_id].setdefault(event_type, [])
            self._session_event_handlers[session_id][event_type].append(entry)
            self._session_event_handlers[session_id][event_type].sort()

    async def async_register_event_handler(
        self,
        event_type: Type[Event],
        handler: EventHandler,
        session_id: SessionID = SessionID("BUS"),
        priority: int = HandlerPriority.NORMAL,
    ) -> None:
        """Async version for testing."""
        self.register_event_handler(event_type, handler, session_id, priority)

    def get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[EventHandler]:
        """Synchronous version for backwards compatibility."""
        handlers: List[EventHandlerEntry] = []
        # BUS handlers first (will be executed as well as session-scoped)
        handlers.extend(self._bus_event_handlers.get(event_type, []))
        # Session handlers if any
        if session_id in self._session_event_handlers:
            handlers.extend(self._session_event_handlers[session_id].get(event_type, []))
        # return in priority order
        return [e.handler for e in sorted(handlers)]

    async def async_get_event_handlers(
        self,
        event_type: Type[Event],
        session_id: SessionID,
    ) -> List[EventHandler]:
        """Async version for testing."""
        return self.get_event_handlers(event_type, session_id)

    # ------------------- Maintenance & Stats -------------------
    def unregister_session(self, session_id: SessionID) -> None:
        """Synchronous version for backwards compatibility."""
        if session_id == SessionID("BUS"):
            # Explicitly do nothing for BUS scope
            return
        self._session_command_handlers.pop(session_id, None)
        self._session_event_handlers.pop(session_id, None)

    async def async_unregister_session(self, session_id: SessionID) -> None:
        """Async version for testing."""
        self.unregister_session(session_id)

    def get_all_sessions(self) -> Set[SessionID]:
        """Synchronous version for backwards compatibility."""
        sessions: Set[SessionID] = set(self._session_command_handlers.keys()) | set(self._session_event_handlers.keys())
        sessions.add(SessionID("BUS"))
        return sessions

    async def async_get_all_sessions(self) -> Set[SessionID]:
        """Async version for testing."""
        return self.get_all_sessions()

    def get_handler_stats(self) -> Dict[str, int]:
        """Synchronous version for backwards compatibility."""
        total_cmd_bus = len(self._bus_command_handlers)
        total_evt_bus = sum(len(lst) for lst in self._bus_event_handlers.values())
        total_cmd_sessions = sum(len(d) for d in self._session_command_handlers.values())
        total_evt_sessions = sum(len(lst) for sess in self._session_event_handlers.values() for lst in sess.values())
        return {
            "total_sessions": len(self.get_all_sessions()),
            "total_command_handlers": total_cmd_bus + total_cmd_sessions,
            "total_event_handlers": total_evt_bus + total_evt_sessions,
            "bus_command_handlers": total_cmd_bus,
            "bus_event_handlers": total_evt_bus,
        }

    async def async_get_handler_stats(self) -> Dict[str, int]:
        """Async version for testing."""
        return self.get_handler_stats()
