"""Tests for bus session functionality with the refactored message bus."""

import asyncio
import pytest
import pytest_asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Type, Any, Callable

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession, SessionStartEvent, SessionEndEvent
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


# Test fixtures
@dataclass
class MockCommand(Command):
    """A mock command for testing."""
    data: str = ""  # Provide default


@dataclass
class MockEvent(Event):
    """A mock event for testing."""
    data: str = ""  # Provide default


class CallRecorder:
    """Helper to record function calls for testing."""
    
    def __init__(self):
        self.calls: List[dict] = []
        self.event_calls: List[Event] = []
        self.command_calls: List[Command] = []
    
    async def record_call(self, *args, **kwargs):
        """Record a call with its arguments."""
        self.calls.append({"args": args, "kwargs": kwargs})
        # Store event/command if passed
        if args:
            msg = args[0]
            if isinstance(msg, Event):
                self.event_calls.append(msg)
            elif isinstance(msg, Command):
                self.command_calls.append(msg)
    
    async def async_handler(self, msg: Any) -> Any:
        """Async handler that records calls."""
        await self.record_call(msg)
        await asyncio.sleep(0.01)  # Simulate async work
        if isinstance(msg, Command):
            # Return a successful result for commands
            return CommandResult(
                success=True,
                command_id=msg.command_id,
                result=f"Processed: {getattr(msg, 'data', '')}",
            )
        return None  # Events don't return results
    
    async def handler_raising_error(self, msg: Any):
        """Handler that always raises an error."""
        await self.record_call(msg)
        raise ValueError("Handler error")
    
    async def called(self) -> bool:
        """Check if the handler was called."""
        return len(self.calls) > 0
    
    async def get_call_count(self) -> int:
        """Get the number of calls."""
        return len(self.calls)
    
    async def get_event_calls(self) -> List[Event]:
        """Get all event calls."""
        return self.event_calls
    
    async def received_command(self, command_type: Type[Command]) -> bool:
        """Check if a specific command type was received."""
        return any(isinstance(cmd, command_type) for cmd in self.command_calls)


@pytest_asyncio.fixture
async def clean_message_bus():
    """Provide a clean message bus for each test."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()
    # Reset singleton for next test
    await bus.reset()


class TestBusSession:
    """Test suite for bus session functionality."""
    
    async def test_register_and_execute_command(self, clean_message_bus: MessageBus):
        """Test registering and executing a command."""
        recorder = CallRecorder()
        cmd = MockCommand(data="test_command")
        
        # Register handler using standard API
        clean_message_bus.register_command_handler(
            MockCommand, recorder.async_handler
        )
        
        result = await clean_message_bus.execute(cmd)
        
        assert await recorder.called()
        assert await recorder.get_call_count() == 1
        assert await recorder.received_command(MockCommand)
        assert result.success
        assert result.result == "Processed: test_command"
    
    async def test_register_and_publish_event(self, clean_message_bus: MessageBus):
        """Test registering and publishing an event."""
        recorder = CallRecorder()
        event = MockEvent(data="test_event")
        
        # Register handler for the event type
        clean_message_bus.register_event_handler(
            MockEvent, recorder.async_handler
        )
        
        await clean_message_bus.publish(event)
        await asyncio.sleep(0.05)  # Allow time for event processing
        
        assert await recorder.called()
        assert await recorder.get_call_count() == 1
        
        # Verify the handler received the event
        event_calls = await recorder.get_event_calls()
        assert len(event_calls) == 1
        assert event_calls[0].data == "test_event"
    
    async def test_session_lifecycle_events(self, clean_message_bus: MessageBus):
        """Test that session start and end events are published."""
        start_recorder = CallRecorder()
        end_recorder = CallRecorder()
        
        # Register handlers for session events
        clean_message_bus.register_event_handler(
            SessionStartEvent, start_recorder.async_handler
        )
        clean_message_bus.register_event_handler(
            SessionEndEvent, end_recorder.async_handler
        )
        
        # Create and use a session
        async with clean_message_bus.create_session() as session:
            # Session is active
            pass
        
        # Give time for events to process
        await asyncio.sleep(0.05)
        
        # Both events should have been published
        assert await start_recorder.called()
        assert await end_recorder.called()
    
    async def test_session_scoped_handlers(self, clean_message_bus: MessageBus):
        """Test that session-scoped handlers are properly isolated."""
        global_recorder = CallRecorder()
        session_recorder = CallRecorder()
        
        # Register global handler
        clean_message_bus.register_event_handler(
            MockEvent, global_recorder.async_handler
        )
        
        # Create session and register session-specific handler
        async with clean_message_bus.create_session() as session:
            session.register_event_handler(MockEvent, session_recorder.async_handler)
            
            # Publish event within session
            event = MockEvent(data="test_event")
            event.session_id = session.session_id
            await clean_message_bus.publish(event)
            
            await asyncio.sleep(0.05)
        
        # Both handlers should have been called
        assert await global_recorder.called()
        assert await session_recorder.called()
        
        # Publish event after session ends
        await clean_message_bus.publish(MockEvent(data="after_session"))
        await asyncio.sleep(0.05)
        
        # Only global handler should be called for new event
        assert await global_recorder.get_call_count() == 2
        assert await session_recorder.get_call_count() == 1
    
    async def test_session_command_execution(self, clean_message_bus: MessageBus):
        """Test executing commands through a session."""
        recorder = CallRecorder()
        
        # Register handler
        clean_message_bus.register_command_handler(
            MockCommand, recorder.async_handler
        )
        
        # Execute command through session
        async with clean_message_bus.create_session() as session:
            cmd = MockCommand(data="session_command")
            result = await session.execute_with_session(cmd)
            
            assert result.success
            assert result.result == "Processed: session_command"
        
        # Verify the command had the session ID
        assert await recorder.called()
        cmd_calls = recorder.command_calls
        assert len(cmd_calls) == 1
        assert cmd_calls[0].session_id == session.session_id
    
    async def test_session_cleanup_on_error(self, clean_message_bus: MessageBus):
        """Test that session handlers are cleaned up even on error."""
        recorder = CallRecorder()
        
        try:
            async with clean_message_bus.create_session() as session:
                session.register_event_handler(MockEvent, recorder.async_handler)
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Handler should be cleaned up - publish event
        await clean_message_bus.publish(MockEvent(data="after_error"))
        await asyncio.sleep(0.05)
        
        # Handler should not have been called
        assert not await recorder.called()
    
    async def test_multiple_sessions(self, clean_message_bus: MessageBus):
        """Test multiple concurrent sessions."""
        recorders = [CallRecorder() for _ in range(3)]
        sessions = []
        
        # Create multiple sessions
        for i, recorder in enumerate(recorders):
            session = clean_message_bus.create_session()
            await session.__aenter__()
            sessions.append(session)
            session.register_event_handler(MockEvent, recorder.async_handler)
        
        # Publish event - all should receive it
        await clean_message_bus.publish(MockEvent(data="broadcast"))
        await asyncio.sleep(0.05)
        
        # All recorders should have been called
        for recorder in recorders:
            assert await recorder.called()
            assert await recorder.get_call_count() == 1
        
        # Clean up sessions
        for session in sessions:
            await session.__aexit__(None, None, None)
    
    async def test_error_suppression(self, clean_message_bus: MessageBus):
        """Test error suppression in event handlers."""
        good_recorder = CallRecorder()
        bad_recorder = CallRecorder()
        
        # Register both good and bad handlers
        clean_message_bus.register_event_handler(
            MockEvent, bad_recorder.handler_raising_error
        )
        clean_message_bus.register_event_handler(
            MockEvent, good_recorder.async_handler
        )
        
        # Publish event - should not raise despite bad handler
        await clean_message_bus.publish(MockEvent(data="test"))
        await asyncio.sleep(0.05)
        
        # Good handler should still be called
        assert await good_recorder.called()
        assert await bad_recorder.called()
        
        # Check that error was recorded
        assert len(clean_message_bus.event_handler_errors) > 0