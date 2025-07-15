"""
Performance tests for the MessageBus implementation.

This test suite covers:
- Throughput measurements
- Latency measurements
- Memory usage patterns
- Scalability testing
- Batch processing performance
"""

import asyncio
import pytest
import time
import gc
import psutil
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime, timedelta

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.llm import SessionID


@dataclass
class PerformanceCommand(Command):
    """Command for performance testing."""
    __test__ = False
    payload: str = field(default="test_payload")
    size: int = field(default=1)


@dataclass
class PerformanceEvent(Event):
    """Event for performance testing."""
    __test__ = False
    payload: str = field(default="test_payload")
    size: int = field(default=1)


class PerformanceMetrics:
    """Helper class to collect performance metrics."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.processed_count = 0
        self.start_time = None
        self.end_time = None
        self.processing_times = []
        self.memory_usage = []
        self.errors = []
    
    def start_measurement(self):
        """Start timing measurement."""
        self.start_time = time.time()
        self.record_memory()
    
    def end_measurement(self):
        """End timing measurement."""
        self.end_time = time.time()
        self.record_memory()
    
    def record_processing(self, processing_time: float):
        """Record individual processing time."""
        self.processed_count += 1
        self.processing_times.append(processing_time)
    
    def record_memory(self):
        """Record current memory usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        self.memory_usage.append(memory_info.rss / 1024 / 1024)  # MB
    
    def record_error(self, error: Exception):
        """Record an error."""
        self.errors.append(error)
    
    @property
    def total_time(self) -> float:
        """Total measurement time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def throughput(self) -> float:
        """Events/commands per second."""
        if self.total_time > 0:
            return self.processed_count / self.total_time
        return 0.0
    
    @property
    def avg_processing_time(self) -> float:
        """Average processing time."""
        if self.processing_times:
            return sum(self.processing_times) / len(self.processing_times)
        return 0.0
    
    @property
    def max_processing_time(self) -> float:
        """Maximum processing time."""
        return max(self.processing_times) if self.processing_times else 0.0
    
    @property
    def min_processing_time(self) -> float:
        """Minimum processing time."""
        return min(self.processing_times) if self.processing_times else 0.0
    
    @property
    def memory_growth(self) -> float:
        """Memory growth in MB."""
        if len(self.memory_usage) >= 2:
            return self.memory_usage[-1] - self.memory_usage[0]
        return 0.0


class TestEventThroughput:
    """Test event processing throughput."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = PerformanceMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_high_volume_event_processing(self):
        """Test processing high volume of events."""
        
        async def fast_handler(event: PerformanceEvent) -> None:
            """Fast event handler for performance testing."""
            start_time = time.time()
            # Simulate minimal processing
            await asyncio.sleep(0.001)
            self.metrics.record_processing(time.time() - start_time)
        
        self.bus.register_event_handler(PerformanceEvent, fast_handler)
        await self.bus.start()
        
        # Test with different event counts
        event_counts = [100, 500, 1000]
        
        for count in event_counts:
            self.metrics.reset()
            self.metrics.start_measurement()
            
            # Publish events
            for i in range(count):
                event = PerformanceEvent(payload=f"event_{i}")
                await self.bus.publish(event, await_processing=False)
            
            # Wait for all events to be processed
            await self.bus.ensure_events_processed()
            
            self.metrics.end_measurement()
            
            # Assertions
            assert self.metrics.processed_count == count
            assert self.metrics.throughput > 50  # At least 50 events/second
            assert self.metrics.avg_processing_time < 0.1  # Less than 100ms average
            
            print(f"Events: {count}, Throughput: {self.metrics.throughput:.2f} events/sec, "
                  f"Avg time: {self.metrics.avg_processing_time*1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing performance improvement."""
        
        batch_processed = []
        
        async def batch_handler(event: PerformanceEvent) -> None:
            """Handler that simulates batch processing."""
            batch_processed.append(event.payload)
            if len(batch_processed) >= 10:  # Process in batches of 10
                start_time = time.time()
                # Simulate batch processing
                await asyncio.sleep(0.01)  # 10ms for batch of 10
                self.metrics.record_processing(time.time() - start_time)
                batch_processed.clear()
        
        self.bus.register_event_handler(PerformanceEvent, batch_handler)
        await self.bus.start()
        
        self.metrics.start_measurement()
        
        # Publish 100 events
        for i in range(100):
            event = PerformanceEvent(payload=f"batch_event_{i}")
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        await asyncio.sleep(0.1)  # Allow final batch to process
        
        self.metrics.end_measurement()
        
        # Batch processing should be more efficient
        assert self.metrics.total_time < 2.0  # Should complete in under 2 seconds
        print(f"Batch processing time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_event_handlers(self):
        """Test performance with multiple concurrent handlers."""
        
        handler_metrics = {f"handler_{i}": [] for i in range(5)}
        
        async def concurrent_handler(handler_id: str):
            """Create a handler for concurrent testing."""
            async def handler(event: PerformanceEvent) -> None:
                start_time = time.time()
                # Simulate different processing times
                await asyncio.sleep(0.001 * (int(handler_id.split('_')[1]) + 1))
                handler_metrics[handler_id].append(time.time() - start_time)
            return handler
        
        # Register multiple handlers
        for i in range(5):
            handler_id = f"handler_{i}"
            handler = await concurrent_handler(handler_id)
            self.bus.register_event_handler(PerformanceEvent, handler)
        
        await self.bus.start()
        
        self.metrics.start_measurement()
        
        # Publish events
        for i in range(50):
            event = PerformanceEvent(payload=f"concurrent_event_{i}")
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        self.metrics.end_measurement()
        
        # All handlers should have processed all events
        for handler_id, times in handler_metrics.items():
            assert len(times) == 50
            avg_time = sum(times) / len(times)
            assert avg_time < 0.1  # Each handler should average < 100ms
            print(f"{handler_id}: {len(times)} events, avg {avg_time*1000:.2f}ms")
        
        # Total time should be reasonable for concurrent processing
        assert self.metrics.total_time < 1.0


class TestCommandThroughput:
    """Test command execution throughput."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = PerformanceMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_high_volume_command_execution(self):
        """Test executing high volume of commands."""
        
        async def fast_command_handler(cmd: PerformanceCommand) -> CommandResult:
            """Fast command handler for performance testing."""
            start_time = time.time()
            # Simulate minimal processing
            await asyncio.sleep(0.001)
            self.metrics.record_processing(time.time() - start_time)
            return CommandResult(success=True, command_id=cmd.command_id)
        
        self.bus.register_command_handler(PerformanceCommand, fast_command_handler)
        await self.bus.start()
        
        # Test with different command counts
        command_counts = [50, 100, 200]
        
        for count in command_counts:
            self.metrics.reset()
            self.metrics.start_measurement()
            
            # Execute commands
            tasks = []
            for i in range(count):
                cmd = PerformanceCommand(payload=f"command_{i}")
                task = self.bus.execute(cmd)
                tasks.append(task)
            
            # Wait for all commands to complete
            results = await asyncio.gather(*tasks)
            
            self.metrics.end_measurement()
            
            # Assertions
            assert len(results) == count
            assert all(r.success for r in results)
            assert self.metrics.throughput > 20  # At least 20 commands/second
            
            print(f"Commands: {count}, Throughput: {self.metrics.throughput:.2f} commands/sec")

    @pytest.mark.asyncio
    async def test_command_latency_distribution(self):
        """Test command execution latency distribution."""
        
        execution_times = []
        
        async def timing_handler(cmd: PerformanceCommand) -> CommandResult:
            """Handler that tracks execution time."""
            start_time = time.time()
            # Variable processing time based on payload
            delay = 0.001 * len(cmd.payload)
            await asyncio.sleep(delay)
            execution_times.append(time.time() - start_time)
            return CommandResult(success=True, command_id=cmd.command_id)
        
        self.bus.register_command_handler(PerformanceCommand, timing_handler)
        await self.bus.start()
        
        # Execute commands with different payload sizes
        tasks = []
        for i in range(100):
            payload = "x" * (i % 10 + 1)  # Variable payload size
            cmd = PerformanceCommand(payload=payload)
            tasks.append(self.bus.execute(cmd))
        
        results = await asyncio.gather(*tasks)
        
        # Analyze latency distribution
        assert len(execution_times) == 100
        assert all(r.success for r in results)
        
        avg_latency = sum(execution_times) / len(execution_times)
        max_latency = max(execution_times)
        min_latency = min(execution_times)
        
        # Latency should be reasonable
        assert avg_latency < 0.1
        assert max_latency < 0.2
        assert min_latency < 0.05
        
        print(f"Latency - Avg: {avg_latency*1000:.2f}ms, "
              f"Max: {max_latency*1000:.2f}ms, Min: {min_latency*1000:.2f}ms")


class TestMemoryUsage:
    """Test memory usage patterns."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = PerformanceMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        
        processed_events = []
        
        async def memory_handler(event: PerformanceEvent) -> None:
            """Handler that keeps references to test memory usage."""
            processed_events.append(event.payload)
            # Periodically clear to simulate real-world usage
            if len(processed_events) > 100:
                processed_events.clear()
                gc.collect()
        
        self.bus.register_event_handler(PerformanceEvent, memory_handler)
        await self.bus.start()
        
        self.metrics.start_measurement()
        
        # Publish events in batches and monitor memory
        for batch in range(10):
            batch_start = time.time()
            
            # Publish batch of events
            for i in range(100):
                event = PerformanceEvent(payload=f"batch_{batch}_event_{i}")
                await self.bus.publish(event, await_processing=False)
            
            # Wait for batch to process
            await self.bus.ensure_events_processed()
            
            # Record memory usage
            self.metrics.record_memory()
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        self.metrics.end_measurement()
        
        # Memory usage should remain reasonable
        assert self.metrics.memory_growth < 50  # Less than 50MB growth
        
        print(f"Memory usage - Start: {self.metrics.memory_usage[0]:.2f}MB, "
              f"End: {self.metrics.memory_usage[-1]:.2f}MB, "
              f"Growth: {self.metrics.memory_growth:.2f}MB")

    @pytest.mark.asyncio
    async def test_handler_cleanup_memory(self):
        """Test that handler cleanup doesn't leak memory."""
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        await self.bus.start()
        
        # Create and destroy many sessions with handlers
        for i in range(50):
            session = self.bus.create_session(f"session_{i}")
            
            def handler(event: PerformanceEvent) -> None:
                pass
            
            session.register_event_handler(PerformanceEvent, handler)
            
            # Publish an event
            event = PerformanceEvent(payload=f"session_{i}_event")
            await self.bus.publish(event)
            
            # Clean up session
            self.bus.unregister_session_handlers(SessionID(f"session_{i}"))
            
            # Force garbage collection
            if i % 10 == 0:
                gc.collect()
        
        await self.bus.ensure_events_processed()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal
        assert memory_growth < 20  # Less than 20MB growth
        
        print(f"Handler cleanup - Initial: {initial_memory:.2f}MB, "
              f"Final: {final_memory:.2f}MB, Growth: {memory_growth:.2f}MB")


class TestScalability:
    """Test scalability with increasing load."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_handler_count_scalability(self):
        """Test scalability with increasing number of handlers."""
        
        await self.bus.start()
        
        results = []
        
        # Test with increasing number of handlers
        for handler_count in [1, 5, 10, 20, 50]:
            processed_count = 0
            
            async def counting_handler(event: PerformanceEvent) -> None:
                nonlocal processed_count
                processed_count += 1
            
            # Register handlers
            for i in range(handler_count):
                self.bus.register_event_handler(PerformanceEvent, counting_handler)
            
            # Measure processing time
            start_time = time.time()
            
            # Publish events
            for i in range(10):
                event = PerformanceEvent(payload=f"scale_event_{i}")
                await self.bus.publish(event, await_processing=False)
            
            await self.bus.ensure_events_processed()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Each event should be processed by all handlers
            expected_count = 10 * handler_count
            assert processed_count == expected_count
            
            results.append((handler_count, processing_time, processed_count))
            
            print(f"Handlers: {handler_count}, Time: {processing_time:.3f}s, "
                  f"Processed: {processed_count}")
            
            # Clean up for next iteration
            self.bus._event_handlers[SessionID("ROOT")] = {}
        
        # Processing time should scale reasonably
        # (not exponentially with handler count)
        first_time = results[0][1]
        last_time = results[-1][1]
        time_ratio = last_time / first_time
        handler_ratio = results[-1][0] / results[0][0]
        
        # Time should scale better than linearly with handler count
        assert time_ratio < handler_ratio * 2

    @pytest.mark.asyncio
    async def test_session_count_scalability(self):
        """Test scalability with increasing number of sessions."""
        
        await self.bus.start()
        
        results = []
        
        # Test with increasing number of sessions
        for session_count in [1, 5, 10, 20]:
            session_data = {}
            
            def session_handler(session_id: str):
                def handler(event: PerformanceEvent) -> None:
                    if session_id not in session_data:
                        session_data[session_id] = 0
                    session_data[session_id] += 1
                return handler
            
            # Create sessions and register handlers
            for i in range(session_count):
                session_id = f"session_{i}"
                handler = session_handler(session_id)
                self.bus.register_event_handler(PerformanceEvent, handler, session_id)
            
            # Measure processing time
            start_time = time.time()
            
            # Publish events to each session
            for i in range(session_count):
                session_id = f"session_{i}"
                for j in range(5):
                    event = PerformanceEvent(
                        payload=f"session_{i}_event_{j}",
                        session_id=SessionID(session_id)
                    )
                    await self.bus.publish(event, await_processing=False)
            
            await self.bus.ensure_events_processed()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Each session should have processed 5 events
            assert len(session_data) == session_count
            for session_id, count in session_data.items():
                assert count == 5
            
            results.append((session_count, processing_time))
            
            print(f"Sessions: {session_count}, Time: {processing_time:.3f}s")
            
            # Clean up for next iteration
            for i in range(session_count):
                session_id = f"session_{i}"
                self.bus.unregister_session_handlers(SessionID(session_id))
        
        # Processing time should scale reasonably with session count
        first_time = results[0][1]
        last_time = results[-1][1]
        time_ratio = last_time / first_time
        session_ratio = results[-1][0] / results[0][0]
        
        # Time should scale better than linearly with session count
        assert time_ratio < session_ratio * 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements