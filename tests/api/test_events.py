"""
Unit tests for the events API endpoints.

This module contains comprehensive tests for event management endpoints
including event publishing, retrieval, and listing with pagination.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from llmgine.api.main import app
from llmgine.api.models.responses import ResponseStatus
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event
from llmgine.llm import SessionID


class TestEventEndpoints:
    """Test suite for event management endpoints."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
        self.mock_message_bus = Mock(spec=MessageBus)
        self.session_id = "test-session-123"
        
        # Mock session validation
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
    
    def test_publish_event_success(self):
        """Test successful event publishing."""
        # Arrange
        event_id = "test-event-123"
        event_data = {
            "event_id": event_id,
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        # Mock async publish method
        self.mock_message_bus.publish = AsyncMock()
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
        
        # Verify service calls
        self.mock_session_service.update_session_last_interaction_at.assert_called_once_with(SessionID(self.session_id))
        self.mock_message_bus.publish.assert_called_once()
    
    def test_publish_event_session_mismatch(self):
        """Test event publishing with session ID mismatch."""
        # Arrange
        event_id = "test-event-123"
        wrong_session_id = "wrong-session-456"
        event_data = {
            "event_id": event_id,
            "session_id": wrong_session_id,  # Different from URL session_id
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
        assert "does not match" in data["error"]
        
        # Verify message bus was not called
        self.mock_message_bus.publish.assert_not_called()
    
    def test_publish_event_exception(self):
        """Test event publishing with exception during publishing."""
        # Arrange
        event_id = "test-event-123"
        event_data = {
            "event_id": event_id,
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        # Mock publish method to raise exception
        self.mock_message_bus.publish = AsyncMock(side_effect=Exception("Event publishing failed"))
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
        assert "Event publishing failed" in data["error"]
    
    def test_get_events_success(self):
        """Test successful event retrieval with pagination."""
        # Arrange
        mock_events = [
            Mock(spec=Event, event_id="event-1", event_type="test_event"),
            Mock(spec=Event, event_id="event-2", event_type="test_event"),
            Mock(spec=Event, event_id="event-3", event_type="test_event")
        ]
        
        self.mock_message_bus.get_events = AsyncMock(return_value=mock_events)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/?limit=10&offset=0")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["total"] == 3
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["events"]) == 3
        
        self.mock_message_bus.get_events.assert_called_once_with(SessionID(self.session_id))
    
    def test_get_events_pagination(self):
        """Test event retrieval with pagination parameters."""
        # Arrange
        mock_events = [
            Mock(spec=Event, event_id=f"event-{i}", event_type="test_event")
            for i in range(10)
        ]
        
        self.mock_message_bus.get_events = AsyncMock(return_value=mock_events)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/?limit=5&offset=2")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 5
        assert data["offset"] == 2
        assert len(data["events"]) == 5
    
    def test_get_events_empty_list(self):
        """Test event retrieval with empty event list."""
        # Arrange
        self.mock_message_bus.get_events = AsyncMock(return_value=[])
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["total"] == 0
        assert len(data["events"]) == 0
    
    def test_get_events_exception(self):
        """Test event retrieval with exception."""
        # Arrange
        self.mock_message_bus.get_events = AsyncMock(side_effect=Exception("Database error"))
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["total"] == 0
        assert len(data["events"]) == 0
        assert "Database error" in data["error"]
    
    def test_get_event_success(self):
        """Test successful single event retrieval."""
        # Arrange
        event_id = "test-event-123"
        mock_event = Mock(spec=Event, event_id=event_id, event_type="test_event")
        mock_events = [mock_event]
        
        self.mock_message_bus.get_events = AsyncMock(return_value=mock_events)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/{event_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
    
    def test_get_event_not_found(self):
        """Test single event retrieval for non-existent event."""
        # Arrange
        event_id = "nonexistent-event"
        other_event = Mock(spec=Event, event_id="other-event", event_type="test_event")
        mock_events = [other_event]
        
        self.mock_message_bus.get_events = AsyncMock(return_value=mock_events)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/{event_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
        assert "not found" in data["error"]
    
    def test_get_event_exception(self):
        """Test single event retrieval with exception."""
        # Arrange
        event_id = "test-event-123"
        self.mock_message_bus.get_events = AsyncMock(side_effect=Exception("Database error"))
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/events/{event_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["event_id"] == event_id
        assert data["session_id"] == self.session_id
        assert "Database error" in data["error"]


class TestEventValidation:
    """Test suite for event validation and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
        self.mock_message_bus = Mock(spec=MessageBus)
        self.session_id = "test-session-123"
        
        # Mock session validation
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
    
    def test_event_missing_required_fields(self):
        """Test event publishing with missing required fields."""
        # Test missing event_id
        event_data = {
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing session_id
        event_data = {
            "event_id": "test-event-123",
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_event_invalid_json(self):
        """Test event publishing with invalid JSON."""
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                data="invalid json"
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_pagination_parameter_validation(self):
        """Test pagination parameter validation for event listing."""
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            # Test invalid limit values
            response = self.client.get(f"/api/sessions/{self.session_id}/events/?limit=0")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            response = self.client.get(f"/api/sessions/{self.session_id}/events/?limit=101")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test negative offset
            response = self.client.get(f"/api/sessions/{self.session_id}/events/?offset=-1")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_event_empty_data(self):
        """Test event publishing with empty data."""
        event_data = {
            "event_id": "test-event-123",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {}
        }
        
        self.mock_message_bus.publish = AsyncMock()
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
    
    def test_event_large_data(self):
        """Test event publishing with large data payload."""
        large_data = "x" * 10000  # 10KB of data
        event_data = {
            "event_id": "test-event-123",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"large_field": large_data}
        }
        
        self.mock_message_bus.publish = AsyncMock()
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
    
    def test_event_special_characters(self):
        """Test event publishing with special characters in data."""
        event_data = {
            "event_id": "test-event-123",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {
                "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
                "unicode": "测试unicode字符",
                "newlines": "line1\nline2\nline3"
            }
        }
        
        self.mock_message_bus.publish = AsyncMock()
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value


class TestEventConcurrency:
    """Test suite for event publishing concurrency scenarios."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
        self.mock_message_bus = Mock(spec=MessageBus)
        self.session_id = "test-session-123"
        
        # Mock session validation
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
    
    def test_concurrent_event_publishing(self):
        """Test concurrent event publishing handling."""
        # Arrange
        event_data_1 = {
            "event_id": "event-1",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"message": "event 1"}
        }
        
        event_data_2 = {
            "event_id": "event-2",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"message": "event 2"}
        }
        
        self.mock_message_bus.publish = AsyncMock()
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            
            response_1 = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data_1
            )
            
            response_2 = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data_2
            )
        
        # Assert
        assert response_1.status_code == status.HTTP_201_CREATED
        assert response_2.status_code == status.HTTP_201_CREATED
        
        data_1 = response_1.json()
        data_2 = response_2.json()
        
        assert data_1["event_id"] == "event-1"
        assert data_2["event_id"] == "event-2"
        assert data_1["status"] == ResponseStatus.SUCCESS.value
        assert data_2["status"] == ResponseStatus.SUCCESS.value
        
        # Verify both events were published
        assert self.mock_message_bus.publish.call_count == 2
    
    def test_session_interaction_updates_on_event_operations(self):
        """Test that session interaction is updated for event operations."""
        # Arrange
        event_data = {
            "event_id": "test-event-123",
            "session_id": self.session_id,
            "event_type": "test_event",
            "data": {"key": "value"}
        }
        
        self.mock_message_bus.publish = AsyncMock()
        self.mock_message_bus.get_events = AsyncMock(return_value=[])
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            
            # Publish event
            response = self.client.post(
                f"/api/sessions/{self.session_id}/events/",
                json=event_data
            )
            assert response.status_code == status.HTTP_201_CREATED
            
            # Get events
            response = self.client.get(f"/api/sessions/{self.session_id}/events/")
            assert response.status_code == status.HTTP_200_OK
            
            # Get specific event
            response = self.client.get(f"/api/sessions/{self.session_id}/events/test-event-123")
            assert response.status_code == status.HTTP_200_OK
        
        # Assert
        # Session interaction should be updated for each operation
        assert self.mock_session_service.update_session_last_interaction_at.call_count == 3
        
        # All calls should be with the same session ID
        for call in self.mock_session_service.update_session_last_interaction_at.call_args_list:
            assert call[0][0] == SessionID(self.session_id)