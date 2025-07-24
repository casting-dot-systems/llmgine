"""Tests for the handler registry implementation."""

import asyncio
import pytest
from typing import Type

from llmgine.bus.interfaces import HandlerPriority
from llmgine.bus.registry import EventHandlerEntry, HandlerRegistry
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


# Test fixtures
class TestCommand(Command):
    """Test command for unit tests."""
    value: str = "test"


class TestEvent(Event):
    """Test event for unit tests."""
    value: str = "test"


async def test_command_handler(cmd: Command) -> CommandResult:
    """Test command handler."""
    return CommandResult(success=True, command_id=cmd.command_id)


async def test_event_handler(evt: Event) -> None:
    """Test event handler."""
    pass


class TestHandlerRegistry:
    """Test suite for HandlerRegistry."""
    
    @pytest.mark.asyncio
    async def test_register_command_handler(self):
        """Test command handler registration."""
        registry = HandlerRegistry()
        
        # Register handler
        await registry.register_command_handler(
            TestCommand, test_command_handler
        )
        
        # Verify registration
        handler = await registry.get_command_handler(
            TestCommand, SessionID("BUS")
        )
        assert handler == test_command_handler
    
    @pytest.mark.asyncio
    async def test_duplicate_command_handler_raises(self):
        """Test that registering duplicate command handlers raises error."""
        registry = HandlerRegistry()
        
        # Register handler
        await registry.register_command_handler(
            TestCommand, test_command_handler
        )
        
        # Try to register again
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_command_handler(
                TestCommand, test_command_handler
            )
    
    @pytest.mark.asyncio
    async def test_register_event_handler(self):
        """Test event handler registration."""
        registry = HandlerRegistry()
        
        # Register handler
        await registry.register_event_handler(
            TestEvent, test_event_handler
        )
        
        # Verify registration
        handlers = await registry.get_event_handlers(
            TestEvent, SessionID("BUS")
        )
        assert len(handlers) == 1
        assert handlers[0] == test_event_handler
    
    @pytest.mark.asyncio
    async def test_event_handler_priority(self):
        """Test event handler priority ordering."""
        registry = HandlerRegistry()
        
        # Create handlers with different priorities
        async def high_priority_handler(evt: Event) -> None:
            pass
        
        async def low_priority_handler(evt: Event) -> None:
            pass
        
        # Register with different priorities
        await registry.register_event_handler(
            TestEvent, low_priority_handler,
            priority=HandlerPriority.LOW
        )
        await registry.register_event_handler(
            TestEvent, high_priority_handler,
            priority=HandlerPriority.HIGH
        )
        
        # Verify order (high priority first)
        handlers = await registry.get_event_handlers(
            TestEvent, SessionID("BUS")
        )
        assert len(handlers) == 2
        assert handlers[0] == high_priority_handler
        assert handlers[1] == low_priority_handler
    
    @pytest.mark.asyncio
    async def test_session_scoped_handlers(self):
        """Test session-scoped handler registration."""
        registry = HandlerRegistry()
        session_id = SessionID("test-session")
        
        # Register session-specific handler
        await registry.register_command_handler(
            TestCommand, test_command_handler, session_id
        )
        
        # Verify it's found for the session
        handler = await registry.get_command_handler(
            TestCommand, session_id
        )
        assert handler == test_command_handler
        
        # Verify it's not found for other sessions
        handler = await registry.get_command_handler(
            TestCommand, SessionID("other-session")
        )
        assert handler is None
    
    @pytest.mark.asyncio
    async def test_bus_scope_fallback(self):
        """Test fallback to BUS scope when session handler not found."""
        registry = HandlerRegistry()
        
        # Register BUS-scoped handler
        await registry.register_command_handler(
            TestCommand, test_command_handler, SessionID("BUS")
        )
        
        # Should find it for any session
        handler = await registry.get_command_handler(
            TestCommand, SessionID("any-session")
        )
        assert handler == test_command_handler
    
    @pytest.mark.asyncio
    async def test_unregister_session(self):
        """Test unregistering all handlers for a session."""
        registry = HandlerRegistry()
        session_id = SessionID("test-session")
        
        # Register handlers
        await registry.register_command_handler(
            TestCommand, test_command_handler, session_id
        )
        await registry.register_event_handler(
            TestEvent, test_event_handler, session_id
        )
        
        # Verify they exist
        assert await registry.get_command_handler(TestCommand, session_id) is not None
        assert len(await registry.get_event_handlers(TestEvent, session_id)) > 0
        
        # Unregister session
        await registry.unregister_session(session_id)
        
        # Verify they're gone
        assert await registry.get_command_handler(TestCommand, session_id) is None
        assert len(await registry.get_event_handlers(TestEvent, session_id)) == 0
    
    @pytest.mark.asyncio
    async def test_cannot_unregister_bus_scope(self):
        """Test that BUS scope cannot be unregistered."""
        registry = HandlerRegistry()
        
        # Register BUS handler
        await registry.register_command_handler(
            TestCommand, test_command_handler, SessionID("BUS")
        )
        
        # Try to unregister BUS scope
        await registry.unregister_session(SessionID("BUS"))
        
        # Handler should still exist
        handler = await registry.get_command_handler(
            TestCommand, SessionID("BUS")
        )
        assert handler == test_command_handler
    
    @pytest.mark.asyncio
    async def test_get_all_sessions(self):
        """Test retrieving all active sessions."""
        registry = HandlerRegistry()
        
        # Register handlers in different sessions
        await registry.register_command_handler(
            TestCommand, test_command_handler, SessionID("session1")
        )
        await registry.register_event_handler(
            TestEvent, test_event_handler, SessionID("session2")
        )
        
        # Get all sessions
        sessions = await registry.get_all_sessions()
        assert SessionID("session1") in sessions
        assert SessionID("session2") in sessions
    
    @pytest.mark.asyncio
    async def test_get_handler_stats(self):
        """Test getting handler statistics."""
        registry = HandlerRegistry()
        
        # Register various handlers
        await registry.register_command_handler(
            TestCommand, test_command_handler, SessionID("BUS")
        )
        await registry.register_event_handler(
            TestEvent, test_event_handler, SessionID("session1")
        )
        await registry.register_event_handler(
            TestEvent, test_event_handler, SessionID("session1")
        )
        
        # Get stats
        stats = await registry.get_handler_stats()
        
        assert stats["total_sessions"] >= 2  # BUS + session1
        assert stats["total_command_handlers"] == 1
        assert stats["total_event_handlers"] == 2
        assert stats["bus_command_handlers"] == 1
        assert stats["bus_event_handlers"] == 0
    
    def test_event_handler_entry_sorting(self):
        """Test EventHandlerEntry sorting by priority."""
        entries = [
            EventHandlerEntry(handler=test_event_handler, priority=50),
            EventHandlerEntry(handler=test_event_handler, priority=10),
            EventHandlerEntry(handler=test_event_handler, priority=90),
        ]
        
        sorted_entries = sorted(entries)
        
        assert sorted_entries[0].priority == 10
        assert sorted_entries[1].priority == 50
        assert sorted_entries[2].priority == 90