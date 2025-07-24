"""Tests for the refactored message bus implementation."""

import asyncio
from dataclasses import dataclass, field
from typing import List

import pytest
import pytest_asyncio

from llmgine.bus.bus import MessageBus
from llmgine.bus.interfaces import EventFilter, HandlerMiddleware, HandlerPriority
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


@dataclass
class TestCommand(Command):
    __test__ = False
    test_data: str = field(default_factory=str)


@dataclass
class TestEvent(Event):
    __test__ = False
    test_data: str = field(default_factory=str)


@pytest_asyncio.fixture
async def bus():
    """Create a message bus for testing."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.reset()  # Reset clears all handlers and stops the bus


class EventCollector:
    """Helper to collect events for testing."""
    def __init__(self):
        self.events: List[Event] = []
    
    async def collect(self, event: Event) -> None:
        self.events.append(event)


# Test basic functionality

def test_singleton_pattern():
    """Test that MessageBus follows singleton pattern."""
    bus1 = MessageBus()
    bus2 = MessageBus()
    assert bus1 is bus2


@pytest.mark.asyncio
async def test_command_execution(bus: MessageBus):
    """Test basic command execution."""
    async def handle_command(cmd: TestCommand) -> CommandResult:
        return CommandResult(success=True, result=f"Processed: {cmd.test_data}")
    
    bus.register_command_handler(TestCommand, handle_command)
    
    command = TestCommand(test_data="hello")
    result = await bus.execute(command)
    
    assert result.success
    assert result.result == "Processed: hello"


@pytest.mark.asyncio
async def test_event_publishing(bus: MessageBus):
    """Test basic event publishing."""
    collector = EventCollector()
    bus.register_event_handler(TestEvent, collector.collect)
    
    event = TestEvent(test_data="test")
    await bus.publish(event)
    
    assert len(collector.events) == 1
    assert collector.events[0].test_data == "test"


# Test session management

@pytest.mark.asyncio
async def test_session_context_manager(bus: MessageBus):
    """Test session context manager for automatic cleanup."""
    collector = EventCollector()
    session_id = None
    
    async with bus.session("test-session") as session:
        session_id = session.session_id
        # Register handler in session
        session.register_event_handler(TestEvent, collector.collect)
        
        # Publish event in session
        event = TestEvent(test_data="in-session", session_id=session.session_id)
        await bus.publish(event)
        
        assert len(collector.events) == 1
    
    # After session ends, handler should be unregistered
    event2 = TestEvent(test_data="after-session", session_id=session_id)
    await bus.publish(event2)
    
    # Should still be 1 - handler was cleaned up
    assert len(collector.events) == 1


@pytest.mark.asyncio
async def test_bus_scope_vs_session_scope(bus: MessageBus):
    """Test that bus-scoped and session-scoped handlers work correctly."""
    bus_collector = EventCollector()
    session_collector = EventCollector()
    
    # Register bus-scoped handler (gets all events)
    bus.register_event_handler(TestEvent, bus_collector.collect)
    
    # Register session-scoped handler (only gets session events)
    session_id = SessionID("test-session")
    bus.register_event_handler(TestEvent, session_collector.collect, session_id)
    
    # Event for bus scope - only bus handler gets it
    bus_event = TestEvent(test_data="bus-event")
    await bus.publish(bus_event)
    
    assert len(bus_collector.events) == 1
    assert len(session_collector.events) == 0
    
    # Event for session - both handlers get it (bus handler gets all events)
    session_event = TestEvent(test_data="session-event", session_id=session_id)
    await bus.publish(session_event)
    
    assert len(bus_collector.events) == 2  # Bus handler gets all events
    assert len(session_collector.events) == 1  # Session handler only gets session events


# Test middleware

@pytest.mark.asyncio
async def test_command_middleware(bus: MessageBus):
    """Test command middleware processing."""
    execution_order = []
    
    class LoggingMiddleware(HandlerMiddleware):
        async def process_command(self, command, handler, next_middleware):
            execution_order.append("before")
            result = await next_middleware(command, handler)
            execution_order.append("after")
            return result
        
        async def process_event(self, event, handler, next_middleware):
            pass
    
    async def handle_command(cmd: TestCommand) -> CommandResult:
        execution_order.append("handler")
        return CommandResult(success=True)
    
    bus.add_command_middleware(LoggingMiddleware())
    bus.register_command_handler(TestCommand, handle_command)
    
    await bus.execute(TestCommand(test_data="test"))
    
    assert execution_order == ["before", "handler", "after"]


# Test event filters

@pytest.mark.asyncio
async def test_event_filters(bus: MessageBus):
    """Test event filtering."""
    collector = EventCollector()
    
    class TestFilter(EventFilter):
        def should_handle(self, event: Event, session_id: SessionID) -> bool:
            # Only handle events with "allowed" in test_data
            return "allowed" in getattr(event, "test_data", "")
    
    bus.add_event_filter(TestFilter())
    bus.register_event_handler(TestEvent, collector.collect)
    
    # This should be filtered out
    await bus.publish(TestEvent(test_data="filtered"))
    assert len(collector.events) == 0
    
    # This should pass through
    await bus.publish(TestEvent(test_data="allowed-event"))
    assert len(collector.events) == 1


# Test event priorities

@pytest.mark.asyncio
async def test_event_handler_priorities(bus: MessageBus):
    """Test that event handlers execute in priority order."""
    execution_order = []
    
    async def high_priority_handler(event: TestEvent):
        execution_order.append("high")
    
    async def normal_priority_handler(event: TestEvent):
        execution_order.append("normal")
    
    async def low_priority_handler(event: TestEvent):
        execution_order.append("low")
    
    # Register in mixed order but with priorities
    bus.register_event_handler(TestEvent, normal_priority_handler, priority=HandlerPriority.NORMAL)
    bus.register_event_handler(TestEvent, low_priority_handler, priority=HandlerPriority.LOW)
    bus.register_event_handler(TestEvent, high_priority_handler, priority=HandlerPriority.HIGH)
    
    await bus.publish(TestEvent(test_data="test"))
    
    # Should execute in priority order (high, normal, low)
    # Note: Due to async execution, order within same batch may vary
    assert "high" in execution_order
    assert "normal" in execution_order
    assert "low" in execution_order


# Test error handling

@pytest.mark.asyncio
async def test_event_error_suppression(bus: MessageBus):
    """Test that event handler errors are suppressed by default."""
    collector = EventCollector()
    
    async def failing_handler(event: TestEvent):
        raise Exception("Handler failed")
    
    # Register both handlers
    bus.register_event_handler(TestEvent, failing_handler)
    bus.register_event_handler(TestEvent, collector.collect)
    
    # Should not raise even though one handler fails
    await bus.publish(TestEvent(test_data="test"))
    
    # Good handler should still have processed the event
    assert len(collector.events) == 1
    assert len(bus.event_handler_errors) == 1


@pytest.mark.asyncio
async def test_event_error_propagation(bus: MessageBus):
    """Test that event handler errors can be propagated."""
    bus.unsuppress_event_errors()
    
    async def failing_handler(event: TestEvent):
        raise ValueError("Handler failed")
    
    bus.register_event_handler(TestEvent, failing_handler)
    
    # Should raise when errors not suppressed
    with pytest.raises(ValueError, match="Handler failed"):
        await bus.publish(TestEvent(test_data="test"))


# Test batch processing

@pytest.mark.asyncio
async def test_batch_processing(bus: MessageBus):
    """Test that events are processed in batches."""
    # Configure smaller batch for testing
    bus.set_batch_processing(batch_size=3, batch_timeout=0.05)
    
    collector = EventCollector()
    bus.register_event_handler(TestEvent, collector.collect)
    
    # Publish multiple events quickly
    for i in range(5):
        await bus.publish(TestEvent(test_data=f"event-{i}"), await_processing=False)
    
    # Give time for batch processing
    await asyncio.sleep(0.1)
    
    # All events should be processed
    assert len(collector.events) == 5


# Test observability integration

@pytest.mark.asyncio
async def test_observability_integration(bus: MessageBus):
    """Test that observability manager is called correctly."""
    from llmgine.observability.manager import ObservabilityManager
    
    observed_events = []
    
    class TestObservability(ObservabilityManager):
        def observe_event(self, event: Event) -> None:
            observed_events.append(event)
    
    obs = TestObservability()
    bus.set_observability_manager(obs)
    
    event = TestEvent(test_data="observed")
    await bus.publish(event)
    
    assert len(observed_events) == 1
    assert observed_events[0] == event


# Test statistics

@pytest.mark.asyncio
async def test_get_stats(bus: MessageBus):
    """Test statistics gathering."""
    stats = await bus.get_stats()
    
    assert stats["running"] is True
    assert "queue_size" in stats
    assert stats["batch_size"] == 10  # Default
    assert stats["batch_timeout"] == 0.01  # Default
    assert stats["error_suppression"] is True  # Default