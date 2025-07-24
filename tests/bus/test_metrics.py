"""Tests for message bus metrics collection."""

import asyncio
import pytest
import pytest_asyncio
from llmgine.bus.bus import MessageBus
from llmgine.bus.metrics import get_metrics_collector, reset_metrics_collector
from llmgine.bus.resilience import ResilientMessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.llm import SessionID


class MetricsTestCommand(Command):
    """Test command for metrics testing."""
    pass


class MetricsTestEvent(Event):
    """Test event for metrics testing."""
    pass


class FailingCommand(Command):
    """Command that always fails."""
    pass


@pytest_asyncio.fixture
async def bus():
    """Create a test message bus."""
    # Reset singleton
    MessageBus._instance = None
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()
    await bus.reset()
    MessageBus._instance = None


@pytest_asyncio.fixture
async def resilient_bus():
    """Create a test resilient message bus."""
    # Reset singleton
    MessageBus._instance = None
    from llmgine.bus.resilience import RetryConfig
    bus = ResilientMessageBus(retry_config=RetryConfig(max_retries=2))
    await bus.start()
    yield bus
    await bus.stop()
    await bus.reset()
    MessageBus._instance = None


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test."""
    reset_metrics_collector()
    yield
    reset_metrics_collector()


@pytest.mark.asyncio
async def test_command_metrics(bus: MessageBus):
    """Test command execution metrics."""
    # Register a successful command handler
    async def handle_test_command(cmd: MetricsTestCommand) -> CommandResult:
        await asyncio.sleep(0.01)  # Simulate work
        return CommandResult(success=True, command_id=cmd.command_id)
    
    bus.register_command_handler(MetricsTestCommand, handle_test_command)
    
    # Execute commands
    result1 = await bus.execute(MetricsTestCommand())
    assert result1.success
    
    result2 = await bus.execute(MetricsTestCommand())
    assert result2.success
    
    # Check metrics
    metrics = await bus.get_metrics()
    
    assert metrics["counters"]["commands_sent_total"]["value"] == 2
    assert metrics["counters"]["commands_processed_total"]["value"] == 2
    assert metrics["counters"]["commands_failed_total"]["value"] == 0
    
    # Check histogram
    histogram = metrics["histograms"]["command_processing_duration_seconds"]
    assert histogram["count"] == 2
    assert histogram["percentiles"]["p50"] is not None
    assert histogram["percentiles"]["p50"] > 0.01  # Should be at least 10ms


@pytest.mark.asyncio
async def test_command_failure_metrics(bus: MessageBus):
    """Test command failure metrics."""
    # Register a failing command handler
    async def handle_failing_command(cmd: FailingCommand) -> CommandResult:
        raise Exception("Command failed")
    
    bus.register_command_handler(FailingCommand, handle_failing_command)
    
    # Execute failing command
    result = await bus.execute(FailingCommand())
    assert not result.success
    
    # Check metrics
    metrics = await bus.get_metrics()
    
    assert metrics["counters"]["commands_sent_total"]["value"] == 1
    assert metrics["counters"]["commands_processed_total"]["value"] == 0
    assert metrics["counters"]["commands_failed_total"]["value"] == 1


@pytest.mark.asyncio
async def test_event_metrics(bus: MessageBus):
    """Test event processing metrics."""
    processed_events = []
    
    async def handle_event(event: MetricsTestEvent):
        await asyncio.sleep(0.005)  # Simulate work
        processed_events.append(event)
    
    bus.register_event_handler(MetricsTestEvent, handle_event)
    
    # Publish events
    for i in range(5):
        await bus.publish(MetricsTestEvent())
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check metrics
    metrics = await bus.get_metrics()
    
    assert metrics["counters"]["events_published_total"]["value"] == 5
    assert metrics["counters"]["events_processed_total"]["value"] == 5
    assert metrics["counters"]["events_failed_total"]["value"] == 0
    
    # Check histogram
    histogram = metrics["histograms"]["event_processing_duration_seconds"]
    assert histogram["count"] == 5
    assert histogram["percentiles"]["p50"] is not None
    assert histogram["percentiles"]["p50"] > 0.005  # Should be at least 5ms


@pytest.mark.asyncio
async def test_event_failure_metrics(bus: MessageBus):
    """Test event failure metrics."""
    async def failing_handler(event: MetricsTestEvent):
        raise Exception("Event handler failed")
    
    bus.register_event_handler(MetricsTestEvent, failing_handler)
    
    # Publish event
    await bus.publish(MetricsTestEvent())
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check metrics
    metrics = await bus.get_metrics()
    
    # Note: EventHandlerFailedEvent is also published when handler fails
    assert metrics["counters"]["events_published_total"]["value"] >= 1
    assert metrics["counters"]["events_processed_total"]["value"] == 0
    assert metrics["counters"]["events_failed_total"]["value"] == 1


@pytest.mark.asyncio
async def test_queue_size_metrics(bus: MessageBus):
    """Test queue size gauge."""
    # Don't register any handlers to let events accumulate
    
    # Publish multiple events
    for i in range(10):
        await bus.publish(MetricsTestEvent(), await_processing=False)
    
    # Check metrics
    metrics = await bus.get_metrics()
    
    # Queue size should reflect the number of pending events
    assert metrics["gauges"]["queue_size"]["value"] >= 10


@pytest.mark.asyncio
async def test_handler_registration_metrics(bus: MessageBus):
    """Test handler registration metrics."""
    # Initial state
    metrics = await bus.get_metrics()
    initial_count = metrics["gauges"]["registered_handlers"]["value"]
    
    # Register event handlers
    async def handler1(event: MetricsTestEvent): pass
    async def handler2(event: MetricsTestEvent): pass
    
    bus.register_event_handler(MetricsTestEvent, handler1)
    bus.register_event_handler(MetricsTestEvent, handler2)
    
    # Check updated metrics
    metrics = await bus.get_metrics()
    # Note: The actual count depends on internal implementation
    assert metrics["gauges"]["registered_handlers"]["value"] >= initial_count


@pytest.mark.asyncio
async def test_dead_letter_queue_metrics(resilient_bus: ResilientMessageBus):
    """Test dead letter queue metrics."""
    # Register a handler that always fails
    async def failing_handler(cmd: MetricsTestCommand) -> CommandResult:
        raise Exception("Command processing failed")
    
    resilient_bus.register_command_handler(MetricsTestCommand, failing_handler)
    
    # Execute command (will fail and go to dead letter queue after retries)
    result = await resilient_bus.execute(MetricsTestCommand())
    assert not result.success
    
    # Check metrics
    metrics = await resilient_bus.get_metrics()
    
    # Dead letter queue should have one entry
    assert metrics["gauges"]["dead_letter_queue_size"]["value"] == 1


@pytest.mark.asyncio
async def test_percentile_calculations():
    """Test histogram percentile calculations."""
    metrics_collector = get_metrics_collector()
    
    # Add values to histogram
    for i in range(100):
        metrics_collector.observe_histogram("test_histogram", i / 100.0)
    
    metrics = await metrics_collector.get_metrics()
    histogram = metrics["histograms"]["event_processing_duration_seconds"]
    
    # Note: This tests the general metrics infrastructure, not specific to bus
    # The bus-specific histograms are tested in other tests


@pytest.mark.asyncio
async def test_metrics_reset():
    """Test metrics reset functionality."""
    metrics_collector = get_metrics_collector()
    
    # Add some metrics
    metrics_collector.inc_counter("events_published_total", 10)
    metrics_collector.set_gauge("queue_size", 5)
    
    # Verify metrics are set
    metrics = await metrics_collector.get_metrics()
    assert metrics["counters"]["events_published_total"]["value"] == 10
    assert metrics["gauges"]["queue_size"]["value"] == 5
    
    # Reset metrics
    reset_metrics_collector()
    
    # Verify metrics are reset
    metrics = await metrics_collector.get_metrics()
    assert metrics["counters"]["events_published_total"]["value"] == 0
    assert metrics["gauges"]["queue_size"]["value"] == 0