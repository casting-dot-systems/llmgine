"""Unit tests for synchronous observability handlers."""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from llmgine.messages.events import Event
from llmgine.observability.handlers.console_sync import SyncConsoleEventHandler
from llmgine.observability.handlers.file_sync import SyncFileEventHandler


class TestSyncConsoleEventHandler:
    """Test suite for SyncConsoleEventHandler."""
    
    @patch('llmgine.observability.handlers.console_sync.logger')
    def test_handle_basic_event(self, mock_logger):
        """Test handling a basic event."""
        handler = SyncConsoleEventHandler()
        event = Event(event_id="test-123", session_id="session-456")
        
        handler.handle(event)
        
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO
        assert "Event" in call_args[0][1]
        assert "test-123" in call_args[0][1]
        assert "session-456" in call_args[0][1]
    
    @patch('llmgine.observability.handlers.console_sync.logger')
    def test_handle_event_with_metadata(self, mock_logger):
        """Test handling event with metadata."""
        handler = SyncConsoleEventHandler()
        event = Event(event_id="test-123", session_id="session-456")
        event.metadata.update({"source": "test", "command_type": "TestCommand"})
        
        handler.handle(event)
        
        call_args = mock_logger.log.call_args[0][1]
        assert "source=test" in call_args
        assert "command_type=TestCommand" in call_args
    
    @patch('llmgine.observability.handlers.console_sync.logger')
    def test_handle_event_formatting_error(self, mock_logger):
        """Test that formatting errors are handled gracefully."""
        handler = SyncConsoleEventHandler()
        event = Event(event_id="test-123")
        
        # Make metadata access raise an exception
        event.metadata = property(lambda self: (_ for _ in ()).throw(Exception("Metadata error")))
        
        handler.handle(event)
        
        # Should still log the basic message
        assert mock_logger.log.called
        # Should log the error
        mock_logger.error.assert_called_once()


class TestSyncFileEventHandler:
    """Test suite for SyncFileEventHandler."""
    
    def test_init_creates_log_directory(self):
        """Test that initialization creates the log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "test_logs"
            handler = SyncFileEventHandler(log_dir=str(log_dir))
            
            assert log_dir.exists()
            assert handler.log_file.parent == log_dir
    
    def test_handle_writes_event_to_file(self):
        """Test that events are written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SyncFileEventHandler(log_dir=tmpdir, filename="test.jsonl")
            event = Event(event_id="test-123", session_id="session-456")
            
            handler.handle(event)
            
            # Read and verify the log file
            log_file = Path(tmpdir) / "test.jsonl"
            assert log_file.exists()
            
            with open(log_file) as f:
                line = f.readline()
                data = json.loads(line)
                
            assert data["event_type"] == "Event"
            assert data["event_id"] == "test-123"
            assert data["session_id"] == "session-456"
    
    def test_handle_multiple_events(self):
        """Test handling multiple events appends to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SyncFileEventHandler(log_dir=tmpdir, filename="test.jsonl")
            
            events = [
                Event(event_id="event-1"),
                Event(event_id="event-2"),
                Event(event_id="event-3")
            ]
            
            for event in events:
                handler.handle(event)
            
            # Verify all events were written
            log_file = Path(tmpdir) / "test.jsonl"
            with open(log_file) as f:
                lines = f.readlines()
            
            assert len(lines) == 3
            for i, line in enumerate(lines):
                data = json.loads(line)
                assert data["event_id"] == f"event-{i+1}"
    
    def test_thread_safety(self):
        """Test that file handler is thread-safe."""
        import threading
        import time
        
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SyncFileEventHandler(log_dir=tmpdir, filename="test.jsonl")
            
            # Function to write events from a thread
            def write_events(thread_id: int):
                for i in range(10):
                    event = Event(event_id=f"thread-{thread_id}-event-{i}")
                    handler.handle(event)
                    time.sleep(0.001)  # Small delay to encourage interleaving
            
            # Create and start threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=write_events, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify all events were written
            log_file = Path(tmpdir) / "test.jsonl"
            with open(log_file) as f:
                lines = f.readlines()
            
            assert len(lines) == 50  # 5 threads * 10 events each
            
            # Verify all events are valid JSON
            for line in lines:
                data = json.loads(line)
                assert "thread-" in data["event_id"]
    
    def test_handle_complex_event(self):
        """Test that events with complex fields are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SyncFileEventHandler(log_dir=tmpdir, filename="test.jsonl")
            
            # Create an event with complex metadata
            event = Event()
            event.metadata["complex_data"] = {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "obj": object()  # Will be converted to string
            }
            
            # Should not crash
            handler.handle(event)
            
            # Verify the file was written
            log_file = Path(tmpdir) / "test.jsonl"
            assert log_file.exists()
            
            with open(log_file) as f:
                line = f.readline()
                data = json.loads(line)
            
            # Check the complex data was serialized
            assert "metadata" in data
            assert "complex_data" in data["metadata"]
            assert data["metadata"]["complex_data"]["nested"]["key"] == "value"
            assert data["metadata"]["complex_data"]["list"] == [1, 2, 3]
            # The object should have been converted to a string
            assert isinstance(data["metadata"]["complex_data"]["obj"], str)