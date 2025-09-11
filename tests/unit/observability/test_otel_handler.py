"""Unit tests for OpenTelemetryHandler."""

from unittest.mock import Mock, patch

from llmgine.bus.session import SessionEndEvent, SessionStartEvent
from llmgine.llm.tools.tool_events import ToolExecuteResultEvent
from llmgine.messages.events import (
    CommandResultEvent,
    CommandStartedEvent,
    EventHandlerFailedEvent,
)
from llmgine.observability.otel_handler import OpenTelemetryHandler


class TestOpenTelemetryHandler:
    """Test suite for OpenTelemetryHandler."""

    @patch("llmgine.observability.otel_handler.logger")
    def test_init_without_otel_installed(self, mock_logger):
        """Test initialization when OpenTelemetry is not installed."""
        with patch.dict("sys.modules", {"opentelemetry": None}):
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

    @patch("llmgine.observability.otel_handler.trace")
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
        assert "session_test-session-123" in call_args[1]["name"]
        assert call_args[1]["attributes"]["session.id"] == "test-session-123"

    @patch("llmgine.observability.otel_handler.current_trace")
    def test_command_started_event(self, mock_current_trace):
        """Test handling CommandStartedEvent."""
        # Mock tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer

        # Fake command object with required attributes
        class _Cmd:
            command_id = "cmd-123"

        # Create and handle event
        event = CommandStartedEvent(session_id="test-session", command=_Cmd())
        handler.handle(event)

        # Verify span was created
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        # We don't assert exact command type name (depends on object),
        # but we do assert the prefix and attributes are set
        assert call_args[1]["name"].startswith("command_")
        assert call_args[1]["attributes"]["command.id"] == "cmd-123"

    @patch("llmgine.observability.otel_handler.current_spans")
    @patch("llmgine.observability.otel_handler.Status")
    @patch("llmgine.observability.otel_handler.StatusCode")
    def test_command_result_event_success(
        self, mock_status_code, mock_status, mock_current_spans
    ):
        """Test handling successful CommandResultEvent."""
        # Mock span
        mock_span = Mock()
        mock_current_spans.get.return_value = {"cmd-123": mock_span}

        handler = OpenTelemetryHandler()
        handler._initialized = True

        # Create and handle event
        class _CR:
            command_id = "cmd-123"
            success = True
            result = {"ok": True}

        event = CommandResultEvent(session_id="test-session", command_result=_CR())
        handler.handle(event)

        # Verify span was updated and ended
        mock_span.set_attribute.assert_any_call("command.success", True)
        mock_span.set_status.assert_called_once()
        mock_span.end.assert_called_once()

    @patch("llmgine.observability.otel_handler.Status")
    @patch("llmgine.observability.otel_handler.StatusCode")
    def test_tool_execute_result_event(self, mock_status_code, mock_status):
        """Test handling ToolExecuteResultEvent."""
        # Mock tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        handler = OpenTelemetryHandler()
        handler._initialized = True
        handler._tracer = mock_tracer

        # Create and handle event (updated fields)
        event = ToolExecuteResultEvent(
            session_id="test-session",
            tool_name="TestTool",
            tool_call_id="call-789",
            execution_succeed=True,
            tool_info={"name": "TestTool"},
            tool_args={"param": "value"},
            tool_result='{"data":"test"}',
        )
        handler.handle(event)

        # Verify span was created and ended
        mock_tracer.start_span.assert_called_once()
        call_args = mock_tracer.start_span.call_args
        assert "tool_TestTool" in call_args[1]["name"]
        mock_span.end.assert_called_once()

    @patch("llmgine.observability.otel_handler.current_spans")
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
            handler="TestHandler",
            exception=Exception("Test error"),
        )
        handler.handle(event)

        # Verify exception was recorded
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()

    @patch("llmgine.observability.otel_handler.current_spans")
    @patch("llmgine.observability.otel_handler.Status")
    @patch("llmgine.observability.otel_handler.StatusCode")
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
        events = [
            SessionStartEvent(session_id="s"),
            SessionEndEvent(session_id="s"),
            CommandStartedEvent(session_id="s", command=type("C", (), {"command_id": "c"})()), 
            CommandResultEvent(session_id="s", command_result=type("R", (), {"command_id": "c", "success": True})()), 
            ToolExecuteResultEvent(session_id="s", tool_name="t", tool_call_id="tc"),
            EventHandlerFailedEvent(session_id="s", handler="h", exception=Exception("x")),
        ]

        for ev in events:
            handler.handle(ev)  # Should not raise
