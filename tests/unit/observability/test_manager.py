"""Unit tests for the ObservabilityManager."""

import pytest
from unittest.mock import Mock, patch
from llmgine.observability.manager import ObservabilityManager, ObservabilityHandler
from llmgine.messages.events import Event


class MockEvent(Event):
    """Mock event for testing."""
    def __init__(self, name: str):
        self.name = name


class MockHandler(ObservabilityHandler):
    """Mock handler for testing."""
    def __init__(self):
        self.events = []
        self.should_fail = False
    
    def handle(self, event: Event) -> None:
        if self.should_fail:
            raise Exception("Handler error")
        self.events.append(event)


class TestObservabilityManager:
    """Test suite for ObservabilityManager."""
    
    def test_init(self):
        """Test manager initialization."""
        manager = ObservabilityManager()
        assert manager.handler_count == 0
        assert manager._enabled is True
    
    def test_register_handler(self):
        """Test handler registration."""
        manager = ObservabilityManager()
        handler1 = MockHandler()
        handler2 = MockHandler()
        
        manager.register_handler(handler1)
        assert manager.handler_count == 1
        
        manager.register_handler(handler2)
        assert manager.handler_count == 2
        
        # Duplicate registration should be ignored
        manager.register_handler(handler1)
        assert manager.handler_count == 2
    
    def test_unregister_handler(self):
        """Test handler unregistration."""
        manager = ObservabilityManager()
        handler1 = MockHandler()
        handler2 = MockHandler()
        
        manager.register_handler(handler1)
        manager.register_handler(handler2)
        assert manager.handler_count == 2
        
        manager.unregister_handler(handler1)
        assert manager.handler_count == 1
        
        # Unregistering non-existent handler should be safe
        manager.unregister_handler(handler1)
        assert manager.handler_count == 1
    
    def test_observe_event(self):
        """Test event observation."""
        manager = ObservabilityManager()
        handler1 = MockHandler()
        handler2 = MockHandler()
        
        manager.register_handler(handler1)
        manager.register_handler(handler2)
        
        event = MockEvent("test_event")
        manager.observe_event(event)
        
        assert len(handler1.events) == 1
        assert handler1.events[0] == event
        assert len(handler2.events) == 1
        assert handler2.events[0] == event
    
    def test_observe_event_when_disabled(self):
        """Test that events are not observed when disabled."""
        manager = ObservabilityManager()
        handler = MockHandler()
        manager.register_handler(handler)
        
        manager.set_enabled(False)
        
        event = MockEvent("test_event")
        manager.observe_event(event)
        
        assert len(handler.events) == 0
    
    def test_handler_error_isolation(self):
        """Test that handler errors don't affect other handlers."""
        manager = ObservabilityManager()
        handler1 = MockHandler()
        handler2 = MockHandler()
        handler3 = MockHandler()
        
        handler1.should_fail = True  # This handler will raise an exception
        
        manager.register_handler(handler1)
        manager.register_handler(handler2)
        manager.register_handler(handler3)
        
        event = MockEvent("test_event")
        
        # Should not raise despite handler1 failing
        manager.observe_event(event)
        
        # Other handlers should still receive the event
        assert len(handler2.events) == 1
        assert len(handler3.events) == 1
    
    def test_clear_handlers(self):
        """Test clearing all handlers."""
        manager = ObservabilityManager()
        
        manager.register_handler(MockHandler())
        manager.register_handler(MockHandler())
        assert manager.handler_count == 2
        
        manager.clear_handlers()
        assert manager.handler_count == 0
    
    @patch('llmgine.observability.manager.logger')
    def test_logging(self, mock_logger):
        """Test that appropriate logging occurs."""
        manager = ObservabilityManager()
        handler = MockHandler()
        
        # Test registration logging
        manager.register_handler(handler)
        mock_logger.debug.assert_called_with("Registered observability handler: MockHandler")
        
        # Test enable/disable logging
        manager.set_enabled(False)
        mock_logger.info.assert_called_with("Observability disabled")
        
        manager.set_enabled(True)
        mock_logger.info.assert_called_with("Observability enabled")
        
        # Test error logging
        handler.should_fail = True
        manager.observe_event(MockEvent("test"))
        mock_logger.error.assert_called()