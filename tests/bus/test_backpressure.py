"""Tests for backpressure handling in the message bus."""

import asyncio
import pytest
import pytest_asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from unittest.mock import Mock

from llmgine.bus.backpressure import (
    BoundedEventQueue,
    BackpressureStrategy,
    QueueMetrics
)
from llmgine.bus.resilience import ResilientMessageBus
from llmgine.messages.events import Event
from llmgine.llm import SessionID


@dataclass
class TestEvent(Event):
    """Simple test event."""
    __test__ = False
    test_data: str = field(default="test")


@pytest_asyncio.fixture
async def bounded_queue():
    """Create a bounded queue for testing."""
    queue = BoundedEventQueue[TestEvent](
        maxsize=10,
        high_water_mark=0.8,  # 8 items
        low_water_mark=0.5,   # 5 items
        strategy=BackpressureStrategy.DROP_OLDEST
    )
    yield queue


class TestBoundedEventQueue:
    """Test bounded event queue functionality."""

    @pytest.mark.asyncio
    async def test_normal_operation(self, bounded_queue):
        """Test normal queue operations without overflow."""
        # Add items
        for i in range(5):
            event = TestEvent(session_id=SessionID("test"), test_data=f"event_{i}")
            assert await bounded_queue.put(event) is True
        
        assert bounded_queue.qsize() == 5
        assert bounded_queue.metrics.total_enqueued == 5
        assert bounded_queue.metrics.total_dropped == 0
        
        # Remove items
        for i in range(5):
            event = await bounded_queue.get()
            assert event.test_data == f"event_{i}"
        
        assert bounded_queue.empty()
        assert bounded_queue.metrics.total_dequeued == 5

    @pytest.mark.asyncio
    async def test_high_water_mark_activation(self, bounded_queue):
        """Test backpressure activation at high water mark."""
        # Mock callbacks
        high_water_called = False
        low_water_called = False
        
        def on_high():
            nonlocal high_water_called
            high_water_called = True
            
        def on_low():
            nonlocal low_water_called
            low_water_called = True
        
        bounded_queue._on_high_water = on_high
        bounded_queue._on_low_water = on_low
        
        # Fill to high water mark (8 items)
        for i in range(8):
            await bounded_queue.put(TestEvent(session_id=SessionID("test")))
        
        assert high_water_called
        assert bounded_queue.is_backpressure_active
        assert bounded_queue.metrics.high_water_mark_hits == 1
        
        # Drain to low water mark (5 items)
        for _ in range(3):
            await bounded_queue.get()
        
        assert low_water_called
        assert not bounded_queue.is_backpressure_active

    @pytest.mark.asyncio
    async def test_drop_oldest_strategy(self):
        """Test DROP_OLDEST overflow strategy."""
        queue = BoundedEventQueue[TestEvent](
            maxsize=5,
            strategy=BackpressureStrategy.DROP_OLDEST
        )
        
        # Fill queue
        for i in range(5):
            await queue.put(TestEvent(test_data=f"old_{i}"))
        
        # Add new items when full - should drop oldest
        for i in range(3):
            assert await queue.put(TestEvent(test_data=f"new_{i}")) is True
        
        assert queue.qsize() == 5
        assert queue.metrics.total_dropped == 3
        assert queue.metrics.total_enqueued == 8
        
        # Verify oldest items were dropped
        items = []
        while not queue.empty():
            items.append((await queue.get()).test_data)
        
        assert items == ["old_3", "old_4", "new_0", "new_1", "new_2"]

    @pytest.mark.asyncio
    async def test_reject_new_strategy(self):
        """Test REJECT_NEW overflow strategy."""
        queue = BoundedEventQueue[TestEvent](
            maxsize=5,
            strategy=BackpressureStrategy.REJECT_NEW
        )
        
        # Fill queue
        for i in range(5):
            assert await queue.put(TestEvent(test_data=f"item_{i}")) is True
        
        # Try to add new items when full - should reject
        for i in range(3):
            assert await queue.put(TestEvent(test_data=f"rejected_{i}")) is False
        
        assert queue.qsize() == 5
        assert queue.metrics.total_rejected == 3
        assert queue.metrics.total_dropped == 0

    @pytest.mark.asyncio
    async def test_adaptive_rate_limit_strategy(self):
        """Test ADAPTIVE_RATE_LIMIT overflow strategy."""
        queue = BoundedEventQueue[TestEvent](
            maxsize=5,
            strategy=BackpressureStrategy.ADAPTIVE_RATE_LIMIT
        )
        
        # Fill queue
        for i in range(5):
            await queue.put(TestEvent())
        
        # Try to add when full - should reject and increase delay
        assert await queue.put(TestEvent()) is False
        
        # Verify rate limit delay increases
        assert queue._rate_limit_delay > 0
        initial_delay = queue._rate_limit_delay
        
        # Another rejection should increase delay further
        assert await queue.put(TestEvent()) is False
        assert queue._rate_limit_delay > initial_delay
        
        # Now test that the delay is actually applied
        # First drain one item to make space
        await queue.get()
        
        # Now put should succeed but with delay
        start_time = datetime.now()
        assert await queue.put(TestEvent()) is True
        elapsed = (datetime.now() - start_time).total_seconds()
        # Should have waited at least the rate limit delay
        assert elapsed >= queue._rate_limit_delay * 0.9  # Allow 10% tolerance

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent put/get operations."""
        queue = BoundedEventQueue[TestEvent](
            maxsize=100,
            strategy=BackpressureStrategy.DROP_OLDEST
        )
        
        async def producer(n: int):
            for i in range(50):
                await queue.put(TestEvent(test_data=f"producer_{n}_item_{i}"))
                await asyncio.sleep(0.001)
        
        async def consumer():
            items = []
            for _ in range(100):
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    items.append(item)
                except asyncio.TimeoutError:
                    break
            return items
        
        # Run producers and consumer concurrently
        producer1_task = asyncio.create_task(producer(1))
        producer2_task = asyncio.create_task(producer(2))
        consumer_task = asyncio.create_task(consumer())
        
        await asyncio.gather(producer1_task, producer2_task)
        items = await consumer_task
        
        # Should have processed items from both producers
        assert len(items) > 0
        producer1_items = [i for i in items if "producer_1" in i.test_data]
        producer2_items = [i for i in items if "producer_2" in i.test_data]
        assert len(producer1_items) > 0
        assert len(producer2_items) > 0

    @pytest.mark.asyncio
    async def test_queue_metrics(self, bounded_queue):
        """Test queue metrics tracking."""
        # Initial state
        metrics = bounded_queue.metrics
        assert metrics.current_size == 0
        assert metrics.total_enqueued == 0
        
        # Add items
        for i in range(5):
            await bounded_queue.put(TestEvent())
        
        metrics = bounded_queue.metrics
        assert metrics.current_size == 5
        assert metrics.total_enqueued == 5
        assert metrics.max_size_reached == 5
        
        # Remove items
        for _ in range(2):
            await bounded_queue.get()
        
        metrics = bounded_queue.metrics
        assert metrics.current_size == 3
        assert metrics.total_dequeued == 2


class TestResilientMessageBusWithBackpressure:
    """Test ResilientMessageBus with backpressure handling."""

    @pytest_asyncio.fixture
    async def resilient_bus_with_backpressure(self):
        """Create a resilient bus with small queue for testing."""
        # Clear singleton
        if hasattr(ResilientMessageBus, '_instance'):
            ResilientMessageBus._instance = None
        
        bus = ResilientMessageBus(
            event_queue_size=10,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST
        )
        await bus.start()
        yield bus
        await bus.stop()
        
        if hasattr(ResilientMessageBus, '_instance'):
            ResilientMessageBus._instance = None

    @pytest.mark.asyncio
    async def test_event_queue_backpressure(self, resilient_bus_with_backpressure):
        """Test that event queue handles backpressure correctly."""
        bus = resilient_bus_with_backpressure
        
        # Publish many events quickly
        for i in range(15):
            event = TestEvent(session_id=SessionID("test"), test_data=f"event_{i}")
            await bus.publish(event, await_processing=False)
        
        # Get queue metrics
        metrics = bus.get_queue_metrics()
        assert metrics is not None
        assert metrics["total_enqueued"] <= 15  # Some may have been dropped
        assert metrics["current_size"] <= 10  # Queue size limit
        
        # If using DROP_OLDEST, dropped count should be > 0
        if metrics["total_enqueued"] < 15:
            assert metrics["total_dropped"] > 0

    @pytest.mark.asyncio
    async def test_different_backpressure_strategies(self):
        """Test different backpressure strategies."""
        strategies = [
            BackpressureStrategy.DROP_OLDEST,
            BackpressureStrategy.REJECT_NEW,
            BackpressureStrategy.ADAPTIVE_RATE_LIMIT
        ]
        
        for strategy in strategies:
            # Clear singleton
            if hasattr(ResilientMessageBus, '_instance'):
                ResilientMessageBus._instance = None
                
            bus = ResilientMessageBus(
                event_queue_size=5,
                backpressure_strategy=strategy
            )
            await bus.start()
            
            # Fill queue beyond capacity
            for i in range(10):
                await bus.publish(TestEvent(test_data=f"{strategy.value}_{i}"), await_processing=False)
            
            metrics = bus.get_queue_metrics()
            assert metrics is not None
            
            if strategy == BackpressureStrategy.DROP_OLDEST:
                assert metrics["total_dropped"] > 0
            elif strategy == BackpressureStrategy.REJECT_NEW:
                assert metrics["total_rejected"] > 0
            
            await bus.stop()