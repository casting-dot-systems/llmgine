"""Integration tests for the observability system."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.messages.commands import Command
from llmgine.messages.events import CommandStartedEvent, CommandResultEvent, Event
from llmgine.observability.manager import ObservabilityManager, ObservabilityHandler


class MockHandler(ObservabilityHandler):
    """Mock handler for testing."""
    def __init__(self):
        self.events = []
    
    def handle(self, event):
        self.events.append(event)


@pytest.mark.asyncio
class TestObservabilityIntegration:
    """Integration tests for the observability system."""
    
    async def test_message_bus_calls_observability_directly(self):
        """Test that message bus calls ObservabilityManager directly."""
        # Create mock handler
        mock_handler = MockHandler()
        
        # Create ObservabilityManager and register handler
        observability = ObservabilityManager()
        observability.register_handler(mock_handler)
        
        # Create message bus with observability
        bus = MessageBus(observability=observability)
        await bus.start()
        
        try:
            # Publish an event
            event = Event(session_id="test-session")
            await bus.publish(event)
            
            # Verify the handler received the event directly (not via bus events)
            assert len(mock_handler.events) == 1
            assert mock_handler.events[0] == event
        finally:
            await bus.stop()
    
    async def test_no_observability_events_published(self):
        """Test that no observability events are published back to the message bus."""
        observability = ObservabilityManager()
        bus = MessageBus(observability=observability)
        await bus.start()
        
        # Track all events published to the bus
        published_events = []
        
        async def track_event(event):
            published_events.append(event)
        
        # Register handler to track all events
        bus.register_event_handler(Event, track_event)
        
        try:
            # Publish a regular event
            event = Event(session_id="test-session")
            await bus.publish(event)
            
            # Only the original event should be in the bus
            # No observability-related events should be published
            assert len(published_events) == 1
            assert published_events[0] == event
        finally:
            await bus.stop()
    
    async def test_no_circular_dependencies(self):
        """Test that there are no circular dependencies between bus and observability."""
        # This test passes if we can import and instantiate without issues
        from llmgine.observability.manager import ObservabilityManager
        from llmgine.bus.bus import MessageBus
        
        # Create instances in both orders
        obs1 = ObservabilityManager()
        bus1 = MessageBus(observability=obs1)
        
        bus2 = MessageBus()
        obs2 = ObservabilityManager()
        bus2.set_observability_manager(obs2)
        
        # No exceptions should be raised
        assert obs1 is not None
        assert bus1 is not None
        assert obs2 is not None
        assert bus2 is not None
    
    async def test_bootstrap_integration(self):
        """Test that ApplicationBootstrap correctly sets up observability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config with file handler
            config = ApplicationConfig(
                enable_console_handler=False,
                enable_file_handler=True,
                file_handler_log_dir=tmpdir,
                file_handler_log_filename="test.jsonl"
            )
            
            # Bootstrap application
            bootstrap = ApplicationBootstrap(config)
            await bootstrap.bootstrap()
            
            try:
                # Verify observability is set up
                assert bootstrap.observability is not None
                assert bootstrap.observability.handler_count == 1  # File handler
                
                # Publish an event
                bus = bootstrap.message_bus
                event = Event(session_id="test-session")
                await bus.publish(event)
                
                # Give a moment for file to be written
                await asyncio.sleep(0.1)
                
                # Verify event was logged to file
                log_file = Path(tmpdir) / "test.jsonl"
                assert log_file.exists()
                
                with open(log_file) as f:
                    content = f.read()
                    assert "Event" in content
                    assert "test-session" in content
            finally:
                await bootstrap.shutdown()
    
    async def test_observability_handler_isolation(self):
        """Test that handler errors don't affect the message bus."""
        # Create a handler that raises an exception
        class FailingHandler(ObservabilityHandler):
            def handle(self, event):
                raise Exception("Handler error")
        
        observability = ObservabilityManager()
        observability.register_handler(FailingHandler())
        
        bus = MessageBus(observability=observability)
        await bus.start()
        
        try:
            # Track events
            received_events = []
            
            async def track_event(event):
                received_events.append(event)
            
            bus.register_event_handler(Event, track_event)
            
            # Publish event - handler error should not prevent normal processing
            event = Event(session_id="test-session")
            await bus.publish(event)
            
            # Event should still be processed normally
            assert len(received_events) == 1
            assert received_events[0] == event
        finally:
            await bus.stop()
    
    async def test_observability_can_be_disabled(self):
        """Test that observability can be disabled."""
        mock_handler = MockHandler()
        observability = ObservabilityManager()
        observability.register_handler(mock_handler)
        
        # Disable observability
        observability.set_enabled(False)
        
        bus = MessageBus(observability=observability)
        await bus.start()
        
        try:
            # Publish event
            event = Event(session_id="test-session")
            await bus.publish(event)
            
            # Handler should not receive event
            assert len(mock_handler.events) == 0
        finally:
            await bus.stop()