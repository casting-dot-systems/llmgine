"""Unit tests for OpenTelemetryHandler."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from llmgine.observability.otel_handler import OpenTelemetryHandler
from llmgine.messages.events import (
    Event,
    CommandStartedEvent,
    CommandResultEvent,
    EventHandlerFailedEvent
)
from llmgine.bus.session import SessionStartEvent, SessionEndEvent
from llmgine.llm.tools.tool_events import ToolExecuteResultEvent
from llmgine.llm.providers.events import LLMResponseEvent, LLMCallEvent


class TestOpenTelemetryHandler:
    """Test suite for OpenTelemetryHandler."""
    
    @patch('llmgine.observability.otel_handler.logger')
    def test_init_without_otel_installed(self, mock_logger):
        """Test initialization when OpenTelemetry is not installed."""
        with patch.dict('sys.modules', {'opentelemetry': None}):
            handler = OpenTelemetryHandler()
            
            assert handler._initialized is False
            assert handler._tracer is None
            mock_logger.warning.assert_called_once()
    
    def test_handle_without_initialization(self):
        """Test that handle returns early when not initialized."""
        handler = OpenTelemetryHandler()
        handler._initialized = False
        
        # Should not crash
        event = SessionStartEvent(session_id="test-session")
        handler.handle(event)  # No exception should be raised
    
    @patch('llmgine.observability.otel_handler.trace')
    def test_session_start_event(self, mock_trace):
        """Test handling SessionStartEvent."""
        # Mock OpenTelemetry components
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer
        
        # Create and handle event
        event = SessionStartEvent(session_id="test-session-123")
        handler.handle(event)
        
        # Verify span was created
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        assert "session_test-session-123" in call_args[1]['name']
        assert call_args[1]['attributes']['session.id'] == "test-session-123"
    
    @patch('llmgine.observability.otel_handler.current_trace')
    def test_command_started_event(self, mock_current_trace):
        """Test handling CommandStartedEvent."""
        # Mock tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer
        
        # Create and handle event
        event = CommandStartedEvent(
            session_id="test-session",
            command_id="cmd-123",
            command_type="TestCommand"
        )
        handler.handle(event)
        
        # Verify span was created
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        assert "command_TestCommand" in call_args[1]['name']
        assert call_args[1]['attributes']['command.type'] == "TestCommand"
        assert call_args[1]['attributes']['command.id'] == "cmd-123"
    
    @patch('llmgine.observability.otel_handler.current_spans')
    @patch('llmgine.observability.otel_handler.Status')
    @patch('llmgine.observability.otel_handler.StatusCode')
    def test_command_result_event_success(self, mock_status_code, mock_status, mock_current_spans):
        """Test handling successful CommandResultEvent."""
        # Mock span
        mock_span = Mock()
        mock_current_spans.get.return_value = {"cmd-123": mock_span}
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        
        # Create and handle event
        event = CommandResultEvent(
            session_id="test-session",
            command_id="cmd-123",
            success=True
        )
        handler.handle(event)
        
        # Verify span was updated and ended
        mock_span.set_attribute.assert_called_with("command.success", True)
        mock_span.set_status.assert_called_once()
        mock_span.end.assert_called_once()
    
    def test_llm_call_event(self):
        """Test handling LLMCallEvent."""
        # Mock tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer
        
        # Create and handle event - using actual event attributes
        event = LLMCallEvent(
            session_id="test-session",
            model="gpt-4",
            provider="openai"
        )
        handler.handle(event)
        
        # Verify span was created
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        assert "llm_call_" in call_args[1]['name']
    
    @patch('llmgine.observability.otel_handler.Status')
    @patch('llmgine.observability.otel_handler.StatusCode')
    def test_tool_execute_result_event(self, mock_status_code, mock_status):
        """Test handling ToolExecuteResultEvent."""
        # Mock tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer
        
        # Create and handle event
        event = ToolExecuteResultEvent(
            session_id="test-session",
            tool_name="TestTool",
            tool_call_id="call-789",
            result={"data": "test"}
        )
        handler.handle(event)
        
        # Verify span was created and ended
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        assert "tool_TestTool" in call_args[1]['name']
        mock_span.end.assert_called_once()
    
    @patch('llmgine.observability.otel_handler.current_spans')
    def test_event_handler_failed_event(self, mock_current_spans):
        """Test handling EventHandlerFailedEvent."""
        # Mock span
        mock_span = Mock()
        mock_current_spans.get.return_value = {"some_span": mock_span}
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        
        # Create and handle event
        event = EventHandlerFailedEvent(
            session_id="test-session",
            handler_name="TestHandler",
            exception=Exception("Test error")
        )
        handler.handle(event)
        
        # Verify exception was recorded
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()
    
    @patch('llmgine.observability.otel_handler.current_spans')
    @patch('llmgine.observability.otel_handler.Status')
    @patch('llmgine.observability.otel_handler.StatusCode')
    def test_session_end_event(self, mock_status_code, mock_status, mock_current_spans):
        """Test handling SessionEndEvent."""
        # Mock span
        mock_span = Mock()
        mock_current_spans.get.return_value = {"test-session": mock_span}
        
        handler = OpenTelemetryHandler()
        handler._initialized = True
        
        # Create and handle event
        event = SessionEndEvent(session_id="test-session")
        handler.handle(event)
        
        # Verify span was ended
        mock_span.set_status.assert_called_once()
        mock_span.end.assert_called_once()
    
    def test_event_mapping_completeness(self):
        """Test that all specified event types are handled."""
        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = Mock()
        
        # List of events that should be handled
        event_types = [
            SessionStartEvent,
            SessionEndEvent,
            CommandStartedEvent,
            CommandResultEvent,
            LLMCallEvent,
            LLMResponseEvent,
            ToolExecuteResultEvent,
            EventHandlerFailedEvent
        ]
        
        # Verify each event type can be handled without error
        for event_type in event_types:
            # Create appropriate mock event
            if hasattr(event_type, '__name__'):
                # Should not raise exception
                event = Mock(spec=event_type)
                event.session_id = "test"
                event.event_id = "test-id"
                handler.handle(event)