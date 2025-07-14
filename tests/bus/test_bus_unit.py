"""
Comprehensive unit tests for the MessageBus implementation.

This test suite covers:
- Basic bus functionality
- Handler registration and management
- Event processing
- Command execution
- Timeout handling
- Error handling
- Session management
- Singleton behavior
"""

import asyncio
import pytest
import pytest_asyncio
from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import Mock, AsyncMock

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event, SessionStartEvent, SessionEndEvent
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.llm import SessionID
from datetime import datetime, timedelta


@dataclass
class TestCommand(Command):
    """Test command for unit tests."""
    __test__ = False
    data: str = field(default="test_data")


@dataclass
class TestEvent(Event):
    """Test event for unit tests."""
    __test__ = False
    data: str = field(default="test_data")


@dataclass
class TestScheduledEvent(ScheduledEvent):
    """Test scheduled event for unit tests."""
    __test__ = False
    data: str = field(default="test_data")


class TestMessageBusBasics:
    """Test basic MessageBus functionality."""

    def test_singleton_behavior(self):
        """Test that MessageBus follows singleton pattern."""
        bus1 = MessageBus()
        bus2 = MessageBus()
        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_bus_start_stop(self):
        """Test basic start/stop functionality."""
        bus = MessageBus()
        await bus.reset()
        
        # Initially not running
        assert bus._processing_task is None
        assert bus._event_queue is None
        
        # Start bus
        await bus.start()
        assert bus._processing_task is not None
        assert bus._event_queue is not None
        
        # Stop bus
        await bus.stop()
        assert bus._processing_task is None
        
        await bus.reset()

    @pytest.mark.asyncio
    async def test_bus_reset(self):
        """Test bus reset functionality."""
        bus = MessageBus()
        await bus.start()
        
        # Register a handler
        def test_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        bus.register_command_handler(TestCommand, test_handler)
        assert TestCommand in bus._command_handlers[SessionID("ROOT")]
        
        # Reset should clear handlers
        await bus.reset()
        assert not bus._command_handlers
        assert not bus._event_handlers

    def test_handler_timeout_configuration(self):
        """Test handler timeout configuration."""
        bus = MessageBus()
        
        # Default timeout
        assert bus._handler_timeout == 30.0
        
        # Set new timeout
        bus.set_handler_timeout(60.0)
        assert bus._handler_timeout == 60.0

    def test_error_suppression_control(self):
        """Test error suppression configuration."""
        bus = MessageBus()
        
        # Default is suppressed
        assert bus._suppress_event_errors is True
        
        # Unsuppress
        bus.unsuppress_event_errors()
        assert bus._suppress_event_errors is False
        
        # Suppress again
        bus.suppress_event_errors()
        assert bus._suppress_event_errors is True


class TestHandlerRegistration:
    """Test handler registration and management."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def test_register_command_handler_success(self):
        """Test successful command handler registration."""
        def test_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        # Register to ROOT
        self.bus.register_command_handler(TestCommand, test_handler)
        assert TestCommand in self.bus._command_handlers[SessionID("ROOT")]
        
        # Register to specific session
        self.bus.register_command_handler(TestCommand, test_handler, "SESSION_1")
        assert TestCommand in self.bus._command_handlers[SessionID("SESSION_1")]

    def test_register_command_handler_duplicate_raises_error(self):
        """Test that duplicate command handler registration raises error."""
        def test_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        # Register first handler
        self.bus.register_command_handler(TestCommand, test_handler)
        
        # Try to register another handler for same command type
        with pytest.raises(ValueError, match="already registered"):
            self.bus.register_command_handler(TestCommand, test_handler)

    def test_register_event_handler_success(self):
        """Test successful event handler registration."""
        def test_handler(event: TestEvent) -> None:
            pass
        
        # Register to ROOT
        self.bus.register_event_handler(TestEvent, test_handler)
        assert TestEvent in self.bus._event_handlers[SessionID("ROOT")]
        assert len(self.bus._event_handlers[SessionID("ROOT")][TestEvent]) == 1
        
        # Register another handler (events can have multiple handlers)
        self.bus.register_event_handler(TestEvent, test_handler)
        assert len(self.bus._event_handlers[SessionID("ROOT")][TestEvent]) == 2

    def test_async_handler_wrapping(self):
        """Test that sync handlers are properly wrapped as async."""
        def sync_command_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        def sync_event_handler(event: TestEvent) -> None:
            pass
        
        # Register sync handlers
        self.bus.register_command_handler(TestCommand, sync_command_handler)
        self.bus.register_event_handler(TestEvent, sync_event_handler)
        
        # Should be wrapped as async
        cmd_handler = self.bus._command_handlers[SessionID("ROOT")][TestCommand]
        event_handler = self.bus._event_handlers[SessionID("ROOT")][TestEvent][0]
        
        assert hasattr(cmd_handler, '_is_wrapped')
        assert hasattr(event_handler, '_is_wrapped')

    def test_unregister_session_handlers(self):
        """Test unregistering all handlers for a session."""
        def test_cmd_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        def test_event_handler(event: TestEvent) -> None:
            pass
        
        # Register handlers for a session
        self.bus.register_command_handler(TestCommand, test_cmd_handler, "SESSION_1")
        self.bus.register_event_handler(TestEvent, test_event_handler, "SESSION_1")
        
        # Verify handlers exist
        assert SessionID("SESSION_1") in self.bus._command_handlers
        assert SessionID("SESSION_1") in self.bus._event_handlers
        
        # Unregister all handlers for session
        self.bus.unregister_session_handlers(SessionID("SESSION_1"))
        
        # Verify handlers are removed
        assert SessionID("SESSION_1") not in self.bus._command_handlers
        assert SessionID("SESSION_1") not in self.bus._event_handlers


class TestCommandExecution:
    """Test command execution functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test successful command execution."""
        def test_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id, result=f"processed_{cmd.data}")
        
        self.bus.register_command_handler(TestCommand, test_handler)
        await self.bus.start()
        
        command = TestCommand(data="test_input")
        result = await self.bus.execute(command)
        
        assert result.success is True
        assert result.result == "processed_test_input"
        assert result.command_id == command.command_id
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_execute_command_not_found(self):
        """Test command execution with no registered handler."""
        await self.bus.start()
        
        command = TestCommand(data="test_input")
        
        with pytest.raises(ValueError, match="No handler registered"):
            await self.bus.execute(command)
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_execute_command_handler_error(self):
        """Test command execution with handler error."""
        def failing_handler(cmd: TestCommand) -> CommandResult:
            raise RuntimeError("Handler failed")
        
        self.bus.register_command_handler(TestCommand, failing_handler)
        await self.bus.start()
        
        command = TestCommand(data="test_input")
        result = await self.bus.execute(command)
        
        assert result.success is False
        assert "RuntimeError: Handler failed" in result.error
        assert result.command_id == command.command_id
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_execute_command_timeout(self):
        """Test command execution with timeout."""
        async def slow_handler(cmd: TestCommand) -> CommandResult:
            await asyncio.sleep(2.0)  # Longer than timeout
            return CommandResult(success=True, command_id=cmd.command_id)
        
        self.bus.register_command_handler(TestCommand, slow_handler)
        self.bus.set_handler_timeout(0.1)  # Very short timeout
        await self.bus.start()
        
        command = TestCommand(data="test_input")
        result = await self.bus.execute(command)
        
        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.command_id == command.command_id
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_execute_command_session_fallback(self):
        """Test command execution falls back to ROOT handlers."""
        def root_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id, result="from_root")
        
        # Register handler only for ROOT
        self.bus.register_command_handler(TestCommand, root_handler)
        await self.bus.start()
        
        # Execute command with different session
        command = TestCommand(data="test_input", session_id=SessionID("SESSION_1"))
        result = await self.bus.execute(command)
        
        assert result.success is True
        assert result.result == "from_root"
        
        await self.bus.stop()


class TestEventProcessing:
    """Test event processing functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    @pytest.mark.asyncio
    async def test_publish_and_process_event(self):
        """Test event publishing and processing."""
        processed_events = []
        
        def test_handler(event: TestEvent) -> None:
            processed_events.append(event.data)
        
        self.bus.register_event_handler(TestEvent, test_handler)
        await self.bus.start()
        
        # Publish event
        event = TestEvent(data="test_data")
        await self.bus.publish(event)
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        assert len(processed_events) == 1
        assert processed_events[0] == "test_data"
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_multiple_event_handlers(self):
        """Test that multiple handlers can process the same event."""
        processed_events = []
        
        def handler1(event: TestEvent) -> None:
            processed_events.append(f"handler1_{event.data}")
        
        def handler2(event: TestEvent) -> None:
            processed_events.append(f"handler2_{event.data}")
        
        self.bus.register_event_handler(TestEvent, handler1)
        self.bus.register_event_handler(TestEvent, handler2)
        await self.bus.start()
        
        # Publish event
        event = TestEvent(data="test_data")
        await self.bus.publish(event)
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        assert len(processed_events) == 2
        assert "handler1_test_data" in processed_events
        assert "handler2_test_data" in processed_events
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_event_handler_error_suppressed(self):
        """Test that event handler errors are suppressed by default."""
        processed_events = []
        
        def failing_handler(event: TestEvent) -> None:
            raise RuntimeError("Handler failed")
        
        def working_handler(event: TestEvent) -> None:
            processed_events.append(event.data)
        
        self.bus.register_event_handler(TestEvent, failing_handler)
        self.bus.register_event_handler(TestEvent, working_handler)
        await self.bus.start()
        
        # Publish event
        event = TestEvent(data="test_data")
        await self.bus.publish(event)
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Working handler should still process
        assert len(processed_events) == 1
        assert processed_events[0] == "test_data"
        
        # Error should be recorded
        assert len(self.bus.event_handler_errors) > 0
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_event_handler_timeout(self):
        """Test event handler timeout."""
        processed_events = []
        
        async def slow_handler(event: TestEvent) -> None:
            await asyncio.sleep(2.0)  # Longer than timeout
            processed_events.append(event.data)
        
        async def fast_handler(event: TestEvent) -> None:
            processed_events.append(f"fast_{event.data}")
        
        self.bus.register_event_handler(TestEvent, slow_handler)
        self.bus.register_event_handler(TestEvent, fast_handler)
        self.bus.set_handler_timeout(0.1)  # Very short timeout
        await self.bus.start()
        
        # Publish event
        event = TestEvent(data="test_data")
        await self.bus.publish(event)
        
        # Wait a bit for processing
        await asyncio.sleep(0.2)
        
        # Fast handler should work, slow handler should timeout
        assert "fast_test_data" in processed_events
        assert "test_data" not in processed_events
        
        # Timeout error should be recorded
        assert len(self.bus.event_handler_errors) > 0
        assert any(isinstance(err, asyncio.TimeoutError) for err in self.bus.event_handler_errors)
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_scheduled_event_processing(self):
        """Test scheduled event processing."""
        processed_events = []
        
        def test_handler(event: TestScheduledEvent) -> None:
            processed_events.append(event.data)
        
        self.bus.register_event_handler(TestScheduledEvent, test_handler)
        await self.bus.start()
        
        # Schedule event for near future
        scheduled_time = datetime.now() + timedelta(milliseconds=100)
        event = TestScheduledEvent(data="scheduled_data", scheduled_time=scheduled_time)
        await self.bus.publish(event)
        
        # Should not be processed immediately
        await asyncio.sleep(0.05)
        assert len(processed_events) == 0
        
        # Should be processed after scheduled time
        await asyncio.sleep(0.1)
        assert len(processed_events) == 1
        assert processed_events[0] == "scheduled_data"
        
        await self.bus.stop()


class TestSessionManagement:
    """Test session management functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test session creation and basic functionality."""
        session = self.bus.create_session("test_session")
        assert session.session_id == "test_session"
        assert session._active is True

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session as context manager."""
        session_events = []
        
        def session_handler(event: SessionStartEvent) -> None:
            session_events.append("start")
        
        def session_end_handler(event: SessionEndEvent) -> None:
            session_events.append("end")
        
        self.bus.register_event_handler(SessionStartEvent, session_handler)
        self.bus.register_event_handler(SessionEndEvent, session_end_handler)
        await self.bus.start()
        
        async with self.bus.create_session("test_session") as session:
            assert session._active is True
            await asyncio.sleep(0.1)  # Let events process
        
        # Session should be inactive after exit
        assert session._active is False
        
        await asyncio.sleep(0.1)  # Let events process
        assert "start" in session_events
        assert "end" in session_events
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_session_handler_registration(self):
        """Test registering handlers through session."""
        processed_events = []
        
        def test_handler(event: TestEvent) -> None:
            processed_events.append(event.data)
        
        await self.bus.start()
        
        async with self.bus.create_session("test_session") as session:
            session.register_event_handler(TestEvent, test_handler)
            
            # Publish event
            event = TestEvent(data="session_data", session_id=SessionID("test_session"))
            await self.bus.publish(event)
            
            await asyncio.sleep(0.1)
            assert len(processed_events) == 1
            assert processed_events[0] == "session_data"
        
        # After session ends, handler should be unregistered
        # and events should not be processed
        event = TestEvent(data="after_session", session_id=SessionID("test_session"))
        await self.bus.publish(event)
        
        await asyncio.sleep(0.1)
        assert len(processed_events) == 1  # Still only one event
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_session_command_execution(self):
        """Test command execution through session."""
        def test_handler(cmd: TestCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id, result="session_result")
        
        await self.bus.start()
        
        async with self.bus.create_session("test_session") as session:
            session.register_command_handler(TestCommand, test_handler)
            
            # Execute command through session
            command = TestCommand(data="session_command")
            result = await session.execute_with_session(command)
            
            assert result.success is True
            assert result.result == "session_result"
            assert command.session_id == "test_session"
        
        await self.bus.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])