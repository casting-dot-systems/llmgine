"""
Edge case tests for the MessageBus implementation.

This test suite covers:
- Boundary conditions
- Race conditions
- Unusual usage patterns
- Error edge cases
- Resource cleanup edge cases
"""

import asyncio
import pytest
import threading
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event, EventHandlerFailedEvent
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.llm import SessionID


@dataclass
class EdgeCaseCommand(Command):
    """Command for edge case testing."""
    __test__ = False
    data: Any = field(default=None)


@dataclass
class EdgeCaseEvent(Event):
    """Event for edge case testing."""
    __test__ = False
    data: Any = field(default=None)


class TestBoundaryConditions:
    """Test boundary conditions."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_empty_handlers(self):
        """Test behavior with empty handlers."""
        
        # Command with no handler
        await self.bus.start()
        
        command = EdgeCaseCommand(data="no_handler")
        with pytest.raises(ValueError, match="No handler registered"):
            await self.bus.execute(command)
        
        # Event with no handler (should not fail)
        event = EdgeCaseEvent(data="no_handler")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        # Should complete without error

    @pytest.mark.asyncio
    async def test_none_values(self):
        """Test handling of None values."""
        
        def none_command_handler(cmd: EdgeCaseCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id, result=None)
        
        def none_event_handler(event: EdgeCaseEvent) -> None:
            pass
        
        self.bus.register_command_handler(EdgeCaseCommand, none_command_handler)
        self.bus.register_event_handler(EdgeCaseEvent, none_event_handler)
        await self.bus.start()
        
        # Command with None data
        command = EdgeCaseCommand(data=None)
        result = await self.bus.execute(command)
        assert result.success is True
        assert result.result is None
        
        # Event with None data
        event = EdgeCaseEvent(data=None)
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()

    @pytest.mark.asyncio
    async def test_large_payloads(self):
        """Test handling of large payloads."""
        
        processed_sizes = []
        
        def large_command_handler(cmd: EdgeCaseCommand) -> CommandResult:
            size = len(str(cmd.data)) if cmd.data else 0
            processed_sizes.append(size)
            return CommandResult(success=True, command_id=cmd.command_id, result=size)
        
        def large_event_handler(event: EdgeCaseEvent) -> None:
            size = len(str(event.data)) if event.data else 0
            processed_sizes.append(size)
        
        self.bus.register_command_handler(EdgeCaseCommand, large_command_handler)
        self.bus.register_event_handler(EdgeCaseEvent, large_event_handler)
        await self.bus.start()
        
        # Test with increasingly large payloads
        sizes = [1, 100, 1000, 10000, 100000]
        
        for size in sizes:
            large_data = "x" * size
            
            # Test command
            command = EdgeCaseCommand(data=large_data)
            result = await self.bus.execute(command)
            assert result.success is True
            assert result.result == size
            
            # Test event
            event = EdgeCaseEvent(data=large_data)
            await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle all sizes
        assert len(processed_sizes) == len(sizes) * 2  # Commands + events
        assert max(processed_sizes) == 100000

    @pytest.mark.asyncio
    async def test_extreme_session_ids(self):
        """Test with extreme session IDs."""
        
        processed_sessions = []
        
        def session_handler(event: EdgeCaseEvent) -> None:
            processed_sessions.append(str(event.session_id))
        
        self.bus.register_event_handler(EdgeCaseEvent, session_handler)
        await self.bus.start()
        
        # Test various extreme session IDs
        extreme_ids = [
            "",  # Empty string
            " ",  # Single space
            "a" * 1000,  # Very long ID
            "session with spaces",  # Spaces
            "session\nwith\nnewlines",  # Newlines
            "session\twith\ttabs",  # Tabs
            "session-with-unicode-🚀",  # Unicode
            "123456789",  # Numeric
            "ROOT",  # Reserved name
            "GLOBAL",  # Reserved name
        ]
        
        for session_id in extreme_ids:
            event = EdgeCaseEvent(
                data=f"test_data_{session_id}",
                session_id=SessionID(session_id)
            )
            await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle all extreme IDs
        assert len(processed_sessions) == len(extreme_ids)

    @pytest.mark.asyncio
    async def test_zero_timeout(self):
        """Test with zero timeout."""
        
        processed_count = 0
        
        async def instant_handler(event: EdgeCaseEvent) -> None:
            nonlocal processed_count
            processed_count += 1
        
        async def slow_handler(event: EdgeCaseEvent) -> None:
            await asyncio.sleep(0.1)  # Will timeout
        
        self.bus.register_event_handler(EdgeCaseEvent, instant_handler)
        self.bus.register_event_handler(EdgeCaseEvent, slow_handler)
        self.bus.set_handler_timeout(0.0)  # Zero timeout
        await self.bus.start()
        
        event = EdgeCaseEvent(data="timeout_test")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Instant handler should work, slow handler should timeout
        assert processed_count == 1
        assert len(self.bus.event_handler_errors) > 0
        assert any(isinstance(e, asyncio.TimeoutError) for e in self.bus.event_handler_errors)


class TestRaceConditions:
    """Test race conditions and threading issues."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_concurrent_handler_registration(self):
        """Test concurrent handler registration."""
        
        registration_results = []
        
        def register_handler(handler_id: int):
            """Register a handler with specific ID."""
            def handler(event: EdgeCaseEvent) -> None:
                pass
            
            try:
                self.bus.register_event_handler(EdgeCaseEvent, handler, f"session_{handler_id}")
                registration_results.append(f"success_{handler_id}")
            except Exception as e:
                registration_results.append(f"error_{handler_id}_{type(e).__name__}")
        
        # Register handlers concurrently
        tasks = []
        for i in range(20):
            task = asyncio.create_task(asyncio.to_thread(register_handler, i))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # All registrations should succeed
        assert len(registration_results) == 20
        assert all(r.startswith("success_") for r in registration_results)

    @pytest.mark.asyncio
    async def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        
        async def start_stop_cycle():
            """Perform start/stop cycle."""
            try:
                await self.bus.start()
                await asyncio.sleep(0.01)
                await self.bus.stop()
                return "success"
            except Exception as e:
                return f"error_{type(e).__name__}"
        
        # Run multiple start/stop cycles concurrently
        tasks = [start_stop_cycle() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Should handle concurrent start/stop gracefully
        success_count = sum(1 for r in results if r == "success")
        assert success_count >= 1  # At least one should succeed

    @pytest.mark.asyncio
    async def test_handler_modification_during_execution(self):
        """Test modifying handlers during event processing."""
        
        processed_events = []
        
        async def modifying_handler(event: EdgeCaseEvent) -> None:
            """Handler that modifies the registry."""
            processed_events.append(event.data)
            
            # Try to register another handler during execution
            def new_handler(e: EdgeCaseEvent) -> None:
                processed_events.append(f"new_{e.data}")
            
            self.bus.register_event_handler(EdgeCaseEvent, new_handler, "new_session")
        
        self.bus.register_event_handler(EdgeCaseEvent, modifying_handler)
        await self.bus.start()
        
        # Publish events
        for i in range(5):
            event = EdgeCaseEvent(data=f"event_{i}")
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        
        # Should handle modification during execution
        assert len(processed_events) >= 5  # At least original events

    @pytest.mark.asyncio
    async def test_session_cleanup_race(self):
        """Test race condition in session cleanup."""
        
        session_events = []
        
        def session_handler(event: EdgeCaseEvent) -> None:
            session_events.append(event.data)
        
        await self.bus.start()
        
        # Create session and register handler
        session = self.bus.create_session("race_session")
        session.register_event_handler(EdgeCaseEvent, session_handler)
        
        # Publish event and immediately clean up session
        event = EdgeCaseEvent(data="race_event", session_id=SessionID("race_session"))
        publish_task = self.bus.publish(event, await_processing=False)
        cleanup_task = asyncio.create_task(
            asyncio.to_thread(self.bus.unregister_session_handlers, SessionID("race_session"))
        )
        
        # Wait for both operations
        await asyncio.gather(publish_task, cleanup_task, return_exceptions=True)
        await self.bus.ensure_events_processed()
        
        # Should handle race condition gracefully (no crashes)
        # Event might or might not be processed depending on timing


class TestUnusualUsagePatterns:
    """Test unusual usage patterns."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_recursive_event_publishing(self):
        """Test recursive event publishing."""
        
        recursion_depth = 0
        max_depth = 5
        
        async def recursive_handler(event: EdgeCaseEvent) -> None:
            nonlocal recursion_depth
            recursion_depth += 1
            
            if recursion_depth < max_depth:
                # Publish another event recursively
                nested_event = EdgeCaseEvent(data=f"nested_{recursion_depth}")
                await self.bus.publish(nested_event)
        
        self.bus.register_event_handler(EdgeCaseEvent, recursive_handler)
        await self.bus.start()
        
        # Start recursion
        initial_event = EdgeCaseEvent(data="initial")
        await self.bus.publish(initial_event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle recursion up to max depth
        assert recursion_depth == max_depth

    @pytest.mark.asyncio
    async def test_command_executing_commands(self):
        """Test commands that execute other commands."""
        
        execution_chain = []
        
        async def chain_command_handler(cmd: EdgeCaseCommand) -> CommandResult:
            """Handler that executes other commands."""
            execution_chain.append(cmd.data)
            
            if cmd.data == "start":
                # Execute next command in chain
                next_cmd = EdgeCaseCommand(data="middle")
                await self.bus.execute(next_cmd)
            elif cmd.data == "middle":
                # Execute final command
                final_cmd = EdgeCaseCommand(data="end")
                await self.bus.execute(final_cmd)
            
            return CommandResult(success=True, command_id=cmd.command_id)
        
        self.bus.register_command_handler(EdgeCaseCommand, chain_command_handler)
        await self.bus.start()
        
        # Start command chain
        start_cmd = EdgeCaseCommand(data="start")
        result = await self.bus.execute(start_cmd)
        
        assert result.success is True
        assert execution_chain == ["start", "middle", "end"]

    @pytest.mark.asyncio
    async def test_event_handler_registering_handlers(self):
        """Test event handlers that register more handlers."""
        
        dynamic_registrations = []
        
        def dynamic_handler(event: EdgeCaseEvent) -> None:
            """Handler that registers more handlers."""
            dynamic_registrations.append(event.data)
            
            # Register a new handler dynamically
            def new_handler(e: EdgeCaseEvent) -> None:
                dynamic_registrations.append(f"dynamic_{e.data}")
            
            session_id = f"dynamic_{len(dynamic_registrations)}"
            self.bus.register_event_handler(EdgeCaseEvent, new_handler, session_id)
        
        self.bus.register_event_handler(EdgeCaseEvent, dynamic_handler)
        await self.bus.start()
        
        # Publish initial event
        event = EdgeCaseEvent(data="trigger")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle dynamic registration
        assert "trigger" in dynamic_registrations

    @pytest.mark.asyncio
    async def test_handler_with_side_effects(self):
        """Test handlers with various side effects."""
        
        side_effects = []
        
        def side_effect_handler(event: EdgeCaseEvent) -> None:
            """Handler with side effects."""
            # Modify global state
            side_effects.append(event.data)
            
            # File I/O (simulate)
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"test data")
                temp_file = f.name
            
            # Clean up
            os.unlink(temp_file)
            
            # Memory allocation
            large_list = [i for i in range(1000)]
            del large_list
        
        self.bus.register_event_handler(EdgeCaseEvent, side_effect_handler)
        await self.bus.start()
        
        # Publish multiple events
        for i in range(10):
            event = EdgeCaseEvent(data=f"side_effect_{i}")
            await self.bus.publish(event, await_processing=False)
        
        await self.bus.ensure_events_processed()
        
        # Should handle side effects
        assert len(side_effects) == 10


class TestErrorEdgeCases:
    """Test error edge cases."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_exception_in_exception_handler(self):
        """Test exception in exception handler."""
        
        def failing_handler(event: EdgeCaseEvent) -> None:
            """Handler that always fails."""
            raise RuntimeError("Primary failure")
        
        def failing_error_handler(event: EventHandlerFailedEvent) -> None:
            """Error handler that also fails."""
            raise RuntimeError("Error handler failure")
        
        self.bus.register_event_handler(EdgeCaseEvent, failing_handler)
        self.bus.register_event_handler(EventHandlerFailedEvent, failing_error_handler)
        await self.bus.start()
        
        # Publish event that will cause cascading failures
        event = EdgeCaseEvent(data="cascade_test")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle cascading failures gracefully
        assert len(self.bus.event_handler_errors) > 0

    @pytest.mark.asyncio
    async def test_handler_modifying_event(self):
        """Test handler modifying the event object."""
        
        modified_events = []
        
        def modifying_handler(event: EdgeCaseEvent) -> None:
            """Handler that modifies the event."""
            # Modify event data
            original_data = event.data
            event.data = f"modified_{original_data}"
            modified_events.append(event.data)
        
        def reading_handler(event: EdgeCaseEvent) -> None:
            """Handler that reads the event."""
            modified_events.append(f"read_{event.data}")
        
        self.bus.register_event_handler(EdgeCaseEvent, modifying_handler)
        self.bus.register_event_handler(EdgeCaseEvent, reading_handler)
        await self.bus.start()
        
        event = EdgeCaseEvent(data="original")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle event modification
        assert len(modified_events) == 2
        assert any("modified_original" in e for e in modified_events)

    @pytest.mark.asyncio
    async def test_invalid_handler_types(self):
        """Test registering invalid handler types."""
        
        # Test with non-callable
        with pytest.raises(Exception):
            self.bus.register_event_handler(EdgeCaseEvent, "not_callable")
        
        # Test with wrong signature (should still work but might fail at runtime)
        def wrong_signature():
            pass
        
        self.bus.register_event_handler(EdgeCaseEvent, wrong_signature)
        await self.bus.start()
        
        # Publishing event should cause error
        event = EdgeCaseEvent(data="wrong_sig_test")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should record error
        assert len(self.bus.event_handler_errors) > 0

    @pytest.mark.asyncio
    async def test_memory_error_handling(self):
        """Test handling of memory errors."""
        
        def memory_exhausting_handler(event: EdgeCaseEvent) -> None:
            """Handler that tries to exhaust memory."""
            try:
                # Try to allocate huge amount of memory
                huge_list = [0] * (10**8)  # This might cause MemoryError
                del huge_list
            except MemoryError:
                # Handle gracefully
                pass
        
        self.bus.register_event_handler(EdgeCaseEvent, memory_exhausting_handler)
        await self.bus.start()
        
        event = EdgeCaseEvent(data="memory_test")
        await self.bus.publish(event)
        
        await self.bus.ensure_events_processed()
        
        # Should handle memory errors gracefully (no crash)


class TestCleanupEdgeCases:
    """Test resource cleanup edge cases."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())

    def teardown_method(self):
        """Cleanup after each test."""
        asyncio.run(self.bus.stop())

    @pytest.mark.asyncio
    async def test_cleanup_with_pending_events(self):
        """Test cleanup with pending events in queue."""
        
        processed_events = []
        
        async def slow_handler(event: EdgeCaseEvent) -> None:
            """Slow handler."""
            await asyncio.sleep(0.1)
            processed_events.append(event.data)
        
        self.bus.register_event_handler(EdgeCaseEvent, slow_handler)
        await self.bus.start()
        
        # Publish many events
        for i in range(10):
            event = EdgeCaseEvent(data=f"pending_{i}")
            await self.bus.publish(event, await_processing=False)
        
        # Stop bus immediately (events may still be pending)
        await self.bus.stop()
        
        # Should handle cleanup gracefully
        # Some events might not be processed due to shutdown

    @pytest.mark.asyncio
    async def test_multiple_resets(self):
        """Test multiple reset operations."""
        
        def test_handler(event: EdgeCaseEvent) -> None:
            pass
        
        for i in range(5):
            # Register handler
            self.bus.register_event_handler(EdgeCaseEvent, test_handler)
            
            # Start bus
            await self.bus.start()
            
            # Publish event
            event = EdgeCaseEvent(data=f"reset_test_{i}")
            await self.bus.publish(event)
            
            # Reset
            await self.bus.reset()
        
        # Should handle multiple resets gracefully
        assert len(self.bus._event_handlers) == 0
        assert len(self.bus._command_handlers) == 0

    @pytest.mark.asyncio
    async def test_session_cleanup_with_active_handlers(self):
        """Test session cleanup with active handlers."""
        
        active_handlers = []
        
        async def long_running_handler(event: EdgeCaseEvent) -> None:
            """Long-running handler."""
            active_handlers.append("started")
            await asyncio.sleep(0.5)
            active_handlers.append("finished")
        
        await self.bus.start()
        
        # Register handler for session
        self.bus.register_event_handler(EdgeCaseEvent, long_running_handler, "cleanup_test")
        
        # Publish event
        event = EdgeCaseEvent(data="cleanup_test", session_id=SessionID("cleanup_test"))
        await self.bus.publish(event, await_processing=False)
        
        # Immediately clean up session
        await asyncio.sleep(0.1)  # Let handler start
        self.bus.unregister_session_handlers(SessionID("cleanup_test"))
        
        # Wait for handler to finish
        await asyncio.sleep(0.5)
        
        # Should handle cleanup with active handlers
        assert "started" in active_handlers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements