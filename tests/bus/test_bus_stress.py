"""
Stress tests for the MessageBus implementation.

This test suite covers:
- High concurrency scenarios
- Resource exhaustion conditions
- Error recovery under stress
- Memory pressure handling
- Timeout stress testing
"""

import asyncio
import pytest
import time
import gc
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event, EventHandlerFailedEvent
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.llm import SessionID


@dataclass
class StressCommand(Command):
    """Command for stress testing."""
    __test__ = False
    payload: str = field(default="stress_payload")
    delay: float = field(default=0.0)
    should_fail: bool = field(default=False)


@dataclass
class StressEvent(Event):
    """Event for stress testing."""
    __test__ = False
    payload: str = field(default="stress_payload")
    delay: float = field(default=0.0)
    should_fail: bool = field(default=False)


class StressTestMetrics:
    """Metrics collection for stress tests."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.commands_executed = 0
        self.commands_failed = 0
        self.events_processed = 0
        self.events_failed = 0
        self.timeouts = 0
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.max_concurrent = 0
        self.current_concurrent = 0
    
    def start_test(self):
        """Start test timing."""
        self.start_time = time.time()
    
    def end_test(self):
        """End test timing."""
        self.end_time = time.time()
    
    def record_command_success(self):
        """Record successful command execution."""
        self.commands_executed += 1
    
    def record_command_failure(self):
        """Record failed command execution."""
        self.commands_failed += 1
    
    def record_event_success(self):
        """Record successful event processing."""
        self.events_processed += 1
    
    def record_event_failure(self):
        """Record failed event processing."""
        self.events_failed += 1
    
    def record_timeout(self):
        """Record timeout occurrence."""
        self.timeouts += 1
    
    def record_error(self, error: Exception):
        """Record error."""
        self.errors.append(error)
    
    def enter_concurrent(self):
        """Enter concurrent execution."""
        self.current_concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.current_concurrent)
    
    def exit_concurrent(self):
        """Exit concurrent execution."""
        self.current_concurrent -= 1
    
    @property
    def total_time(self) -> float:
        """Total test time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def total_operations(self) -> int:
        """Total operations performed."""
        return self.commands_executed + self.commands_failed + self.events_processed + self.events_failed
    
    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        total = self.total_operations
        if total > 0:
            successes = self.commands_executed + self.events_processed
            return (successes / total) * 100
        return 0.0


class TestHighConcurrency:
    """Test high concurrency scenarios."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = StressTestMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self):
        """Test executing many commands concurrently."""
        
        async def stress_command_handler(cmd: StressCommand) -> CommandResult:
            """Handler that simulates variable processing time."""
            self.metrics.enter_concurrent()
            try:
                if cmd.should_fail:
                    self.metrics.record_command_failure()
                    raise RuntimeError(f"Intentional failure for {cmd.command_id}")
                
                if cmd.delay > 0:
                    await asyncio.sleep(cmd.delay)
                
                self.metrics.record_command_success()
                return CommandResult(success=True, command_id=cmd.command_id)
            finally:
                self.metrics.exit_concurrent()
        
        self.bus.register_command_handler(StressCommand, stress_command_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Create many concurrent command executions
        tasks = []
        for i in range(100):
            # Random delay and failure rate
            delay = random.uniform(0.001, 0.01)
            should_fail = random.random() < 0.1  # 10% failure rate
            
            cmd = StressCommand(
                payload=f"concurrent_cmd_{i}",
                delay=delay,
                should_fail=should_fail
            )
            
            task = self.bus.execute(cmd)
            tasks.append(task)
        
        # Wait for all commands to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.metrics.end_test()
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, CommandResult) and r.success]
        failed_results = [r for r in results if isinstance(r, CommandResult) and not r.success]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Assertions
        assert len(results) == 100
        assert len(successful_results) + len(failed_results) + len(exceptions) == 100
        assert self.metrics.max_concurrent > 10  # Should have high concurrency
        assert self.metrics.total_time < 2.0  # Should complete quickly due to concurrency
        
        print(f"Concurrent commands - Total: {len(results)}, "
              f"Successful: {len(successful_results)}, "
              f"Failed: {len(failed_results)}, "
              f"Exceptions: {len(exceptions)}, "
              f"Max concurrent: {self.metrics.max_concurrent}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self):
        """Test processing many events concurrently."""
        
        async def stress_event_handler(event: StressEvent) -> None:
            """Handler that simulates variable processing time."""
            self.metrics.enter_concurrent()
            try:
                if event.should_fail:
                    self.metrics.record_event_failure()
                    raise RuntimeError(f"Intentional failure for {event.event_id}")
                
                if event.delay > 0:
                    await asyncio.sleep(event.delay)
                
                self.metrics.record_event_success()
            finally:
                self.metrics.exit_concurrent()
        
        self.bus.register_event_handler(StressEvent, stress_event_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Publish many events rapidly
        for i in range(200):
            delay = random.uniform(0.001, 0.005)
            should_fail = random.random() < 0.05  # 5% failure rate
            
            event = StressEvent(
                payload=f"concurrent_event_{i}",
                delay=delay,
                should_fail=should_fail
            )
            
            await self.bus.publish(event, await_processing=False)
        
        # Wait for all events to be processed
        await self.bus.ensure_events_processed()
        await asyncio.sleep(0.5)  # Additional time for processing
        
        self.metrics.end_test()
        
        # Assertions
        total_processed = self.metrics.events_processed + self.metrics.events_failed
        assert total_processed == 200
        assert self.metrics.max_concurrent > 5  # Should have concurrent processing
        assert self.metrics.success_rate > 90  # Should have high success rate
        
        print(f"Concurrent events - Processed: {self.metrics.events_processed}, "
              f"Failed: {self.metrics.events_failed}, "
              f"Success rate: {self.metrics.success_rate:.1f}%, "
              f"Max concurrent: {self.metrics.max_concurrent}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self):
        """Test mixing commands and events under high concurrency."""
        
        async def mixed_command_handler(cmd: StressCommand) -> CommandResult:
            """Command handler that publishes events."""
            self.metrics.enter_concurrent()
            try:
                await asyncio.sleep(0.001)
                
                # Publish related event
                event = StressEvent(payload=f"from_cmd_{cmd.command_id}")
                await self.bus.publish(event, await_processing=False)
                
                self.metrics.record_command_success()
                return CommandResult(success=True, command_id=cmd.command_id)
            finally:
                self.metrics.exit_concurrent()
        
        async def mixed_event_handler(event: StressEvent) -> None:
            """Event handler that might execute commands."""
            self.metrics.enter_concurrent()
            try:
                await asyncio.sleep(0.001)
                
                # Occasionally execute a command
                if random.random() < 0.1:  # 10% chance
                    cmd = StressCommand(payload=f"from_event_{event.event_id}")
                    await self.bus.execute(cmd)
                
                self.metrics.record_event_success()
            finally:
                self.metrics.exit_concurrent()
        
        self.bus.register_command_handler(StressCommand, mixed_command_handler)
        self.bus.register_event_handler(StressEvent, mixed_event_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Mix of commands and events
        tasks = []
        
        for i in range(50):
            # Execute command
            cmd = StressCommand(payload=f"mixed_cmd_{i}")
            tasks.append(self.bus.execute(cmd))
            
            # Publish event
            event = StressEvent(payload=f"mixed_event_{i}")
            tasks.append(self.bus.publish(event, await_processing=False))
        
        # Wait for all operations
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.bus.ensure_events_processed()
        await asyncio.sleep(0.5)  # Additional processing time
        
        self.metrics.end_test()
        
        # Should handle mixed operations well
        assert self.metrics.commands_executed >= 50
        assert self.metrics.events_processed >= 50
        assert self.metrics.max_concurrent > 10
        
        print(f"Mixed operations - Commands: {self.metrics.commands_executed}, "
              f"Events: {self.metrics.events_processed}, "
              f"Max concurrent: {self.metrics.max_concurrent}, "
              f"Time: {self.metrics.total_time:.2f}s")


class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = StressTestMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test behavior under memory pressure."""
        
        large_objects = []
        
        async def memory_intensive_handler(event: StressEvent) -> None:
            """Handler that creates large objects."""
            # Create large object (1MB)
            large_data = "x" * (1024 * 1024)
            large_objects.append(large_data)
            
            # Occasionally clean up to simulate real usage
            if len(large_objects) > 50:
                large_objects.clear()
                gc.collect()
            
            self.metrics.record_event_success()
        
        self.bus.register_event_handler(StressEvent, memory_intensive_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Publish many events that create large objects
        for i in range(100):
            event = StressEvent(payload=f"memory_event_{i}")
            await self.bus.publish(event, await_processing=False)
            
            # Brief pause to allow processing
            if i % 10 == 0:
                await asyncio.sleep(0.01)
        
        await self.bus.ensure_events_processed()
        
        self.metrics.end_test()
        
        # Should handle memory pressure gracefully
        assert self.metrics.events_processed == 100
        assert len(self.metrics.errors) == 0
        
        print(f"Memory pressure - Events: {self.metrics.events_processed}, "
              f"Errors: {len(self.metrics.errors)}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_handler_limit_stress(self):
        """Test with extreme number of handlers."""
        
        processed_counts = {}
        
        async def counting_handler(handler_id: int):
            """Create a unique handler."""
            async def handler(event: StressEvent) -> None:
                if handler_id not in processed_counts:
                    processed_counts[handler_id] = 0
                processed_counts[handler_id] += 1
                await asyncio.sleep(0.001)  # Small delay
            return handler
        
        await self.bus.start()
        
        # Register many handlers
        handler_count = 100
        for i in range(handler_count):
            handler = await counting_handler(i)
            self.bus.register_event_handler(StressEvent, handler)
        
        self.metrics.start_test()
        
        # Publish events
        event_count = 10
        for i in range(event_count):
            event = StressEvent(payload=f"multi_handler_event_{i}")
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        
        self.metrics.end_test()
        
        # Each event should be processed by all handlers
        assert len(processed_counts) == handler_count
        for handler_id, count in processed_counts.items():
            assert count == event_count
        
        total_processed = sum(processed_counts.values())
        expected_total = handler_count * event_count
        assert total_processed == expected_total
        
        print(f"Handler limit stress - Handlers: {handler_count}, "
              f"Events: {event_count}, "
              f"Total processed: {total_processed}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_session_limit_stress(self):
        """Test with extreme number of sessions."""
        
        session_counts = {}
        
        def session_handler(session_id: str):
            """Create session-specific handler."""
            def handler(event: StressEvent) -> None:
                if session_id not in session_counts:
                    session_counts[session_id] = 0
                session_counts[session_id] += 1
            return handler
        
        await self.bus.start()
        
        # Create many sessions
        session_count = 100
        for i in range(session_count):
            session_id = f"stress_session_{i}"
            handler = session_handler(session_id)
            self.bus.register_event_handler(StressEvent, handler, session_id)
        
        self.metrics.start_test()
        
        # Publish events to random sessions
        for i in range(200):
            session_id = f"stress_session_{random.randint(0, session_count - 1)}"
            event = StressEvent(
                payload=f"session_event_{i}",
                session_id=SessionID(session_id)
            )
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        
        self.metrics.end_test()
        
        # Should handle many sessions efficiently
        total_processed = sum(session_counts.values())
        assert total_processed == 200
        assert len(session_counts) <= session_count
        
        print(f"Session limit stress - Sessions: {session_count}, "
              f"Events: 200, "
              f"Active sessions: {len(session_counts)}, "
              f"Total processed: {total_processed}, "
              f"Time: {self.metrics.total_time:.2f}s")


class TestErrorRecovery:
    """Test error recovery under stress."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = StressTestMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_cascading_failure_recovery(self):
        """Test recovery from cascading failures."""
        
        failure_count = 0
        recovery_count = 0
        
        async def failing_handler(event: StressEvent) -> None:
            """Handler that fails frequently but recovers."""
            nonlocal failure_count, recovery_count
            
            if event.payload.startswith("fail_"):
                failure_count += 1
                raise RuntimeError(f"Cascade failure {failure_count}")
            else:
                recovery_count += 1
        
        def error_recovery_handler(event: EventHandlerFailedEvent) -> None:
            """Handler that processes failure events."""
            self.metrics.record_error(event.exception)
        
        self.bus.register_event_handler(StressEvent, failing_handler)
        self.bus.register_event_handler(EventHandlerFailedEvent, error_recovery_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Publish mix of failing and successful events
        for i in range(100):
            if i % 3 == 0:  # 33% failure rate
                event = StressEvent(payload=f"fail_{i}")
            else:
                event = StressEvent(payload=f"success_{i}")
            
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        
        self.metrics.end_test()
        
        # Should handle failures gracefully
        assert failure_count > 0
        assert recovery_count > 0
        assert failure_count + recovery_count == 100
        assert len(self.metrics.errors) == failure_count
        
        print(f"Cascading failure recovery - Failures: {failure_count}, "
              f"Recoveries: {recovery_count}, "
              f"Errors recorded: {len(self.metrics.errors)}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_timeout_storm_recovery(self):
        """Test recovery from timeout storms."""
        
        timeout_count = 0
        success_count = 0
        
        async def timeout_prone_handler(event: StressEvent) -> None:
            """Handler that occasionally times out."""
            nonlocal timeout_count, success_count
            
            if event.payload.startswith("slow_"):
                # This will timeout with short timeout setting
                await asyncio.sleep(1.0)
                timeout_count += 1
            else:
                await asyncio.sleep(0.001)
                success_count += 1
        
        self.bus.register_event_handler(StressEvent, timeout_prone_handler)
        self.bus.set_handler_timeout(0.1)  # Very short timeout
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Publish mix of slow and fast events
        for i in range(50):
            if i % 5 == 0:  # 20% slow events
                event = StressEvent(payload=f"slow_{i}")
            else:
                event = StressEvent(payload=f"fast_{i}")
            
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        await asyncio.sleep(0.5)  # Allow timeouts to occur
        
        self.metrics.end_test()
        
        # Should handle timeouts gracefully
        timeout_errors = [e for e in self.bus.event_handler_errors if isinstance(e, asyncio.TimeoutError)]
        assert len(timeout_errors) > 0  # Should have timeout errors
        assert success_count > 0  # Should have successful events
        
        print(f"Timeout storm recovery - Timeouts: {len(timeout_errors)}, "
              f"Successes: {success_count}, "
              f"Total errors: {len(self.bus.event_handler_errors)}, "
              f"Time: {self.metrics.total_time:.2f}s")


class TestScheduledEventStress:
    """Test scheduled events under stress."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.metrics = StressTestMetrics()

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_many_scheduled_events(self):
        """Test with many scheduled events."""
        
        processed_events = []
        
        def scheduled_handler(event: ScheduledEvent) -> None:
            """Handler for scheduled events."""
            if hasattr(event, 'data'):
                processed_events.append(event.data)
        
        self.bus.register_event_handler(ScheduledEvent, scheduled_handler)
        await self.bus.start()
        
        self.metrics.start_test()
        
        # Schedule many events
        base_time = datetime.now()
        for i in range(100):
            scheduled_time = base_time + timedelta(milliseconds=i * 10)  # 10ms apart
            event = ScheduledEvent(scheduled_time=scheduled_time)
            event.data = f"scheduled_{i}"
            await self.bus.publish(event, await_processing=False)
        
        # Wait for all events to be processed
        await asyncio.sleep(2.0)
        
        self.metrics.end_test()
        
        # Should process all scheduled events
        assert len(processed_events) == 100
        
        # Should be processed in order
        for i, data in enumerate(processed_events):
            assert data == f"scheduled_{i}"
        
        print(f"Many scheduled events - Processed: {len(processed_events)}, "
              f"Time: {self.metrics.total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_scheduled_event_backlog(self):
        """Test handling of scheduled event backlog."""
        
        processed_events = []
        
        def backlog_handler(event: ScheduledEvent) -> None:
            """Handler that processes backlog."""
            if hasattr(event, 'data'):
                processed_events.append((event.data, datetime.now()))
        
        self.bus.register_event_handler(ScheduledEvent, backlog_handler)
        await self.bus.start()
        
        # Schedule many events for the past (should process immediately)
        past_time = datetime.now() - timedelta(seconds=1)
        for i in range(50):
            event = ScheduledEvent(scheduled_time=past_time)
            event.data = f"backlog_{i}"
            await self.bus.publish(event, await_processing=False)
        
        # Schedule events for the future
        future_time = datetime.now() + timedelta(milliseconds=100)
        for i in range(50):
            event = ScheduledEvent(scheduled_time=future_time)
            event.data = f"future_{i}"
            await self.bus.publish(event, await_processing=False)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Should process all events
        assert len(processed_events) == 100
        
        # Backlog events should be processed first
        backlog_events = [e for e in processed_events if e[0].startswith("backlog_")]
        future_events = [e for e in processed_events if e[0].startswith("future_")]
        
        assert len(backlog_events) == 50
        assert len(future_events) == 50
        
        print(f"Scheduled event backlog - Backlog: {len(backlog_events)}, "
              f"Future: {len(future_events)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements