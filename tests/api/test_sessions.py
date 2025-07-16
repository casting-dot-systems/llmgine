"""
Unit tests for the sessions API endpoints.

This module contains comprehensive tests for session management endpoints
including creation, retrieval, listing, termination, and WebSocket functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from llmgine.api.main import app
from llmgine.api.models.responses import ResponseStatus
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.llm import SessionID
from llmgine.api.routers.dependencies import get_session_service


class TestSessionEndpoints:
    """Test suite for session management endpoints."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
        
    def test_create_session_success(self):
        """Test successful session creation."""
        # Arrange
        session_id = SessionID("test-session-123")
        self.mock_session_service.create_session.return_value = session_id
        self.mock_session_service.max_sessions = 100
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service
        
        try:
            # Act
            response = self.client.post("/api/sessions/")

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["status"] == ResponseStatus.SUCCESS.value
            assert data["session_id"] == str(session_id)
            assert data["message"] == "Session created successfully"
            self.mock_session_service.create_session.assert_called_once()
        finally:
            # Clean up
            app.dependency_overrides.clear()
    
    def test_create_session_max_limit_reached(self):
        """Test session creation when maximum limit is reached."""
        # Arrange
        self.mock_session_service.create_session.return_value = None
        self.mock_session_service.max_sessions = 100
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.post("/api/sessions/")
        
        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "RESOURCE_LIMIT_EXCEEDED"
        assert "Maximum sessions limit (100) exceeded" in data["error"]["message"]
    
    def test_get_session_status_success(self):
        """Test successful session status retrieval."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        mock_session.created_at = datetime.fromisoformat("2023-01-01T00:00:00")
        mock_session.last_interaction_at = datetime.fromisoformat("2023-01-01T00:05:00")
        
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.get(f"/api/sessions/{session_id}")
            print(response.json())
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == SessionStatus.RUNNING.value
        self.mock_session_service.get_session.assert_called_once_with(SessionID(session_id))
    
    def test_get_session_status_not_found(self):
        """Test session status retrieval for non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        self.mock_session_service.get_session.return_value = None
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.get(f"/api/sessions/{session_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "SESSION_NOT_FOUND"
        assert session_id in data["error"]["message"]
    
    def test_list_sessions_success(self):
        """Test successful session listing with pagination."""
        # Arrange
        mock_sessions = {
            SessionID("session-1"): Mock(get_status=Mock(return_value=SessionStatus.RUNNING)),
            SessionID("session-2"): Mock(get_status=Mock(return_value=SessionStatus.IDLE))
        }
        
        # Set up mock session timestamps
        for session in mock_sessions.values():
            session.created_at = datetime.fromisoformat("2023-01-01T00:00:00")
            session.last_interaction_at = datetime.fromisoformat("2023-01-01T00:05:00")
        
        self.mock_session_service.get_all_sessions.return_value = mock_sessions
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.get("/api/sessions/?limit=10&offset=0")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["sessions"]) == 2
        
        # Check session data format
        session_data = data["sessions"][0]
        assert "session_id" in session_data
        assert "status" in session_data
        assert "created_at" in session_data
        assert "last_interaction_at" in session_data
    
    def test_list_sessions_pagination(self):
        """Test session listing with pagination parameters."""
        # Arrange
        mock_sessions = {
            SessionID(f"session-{i}"): Mock(
                get_status=Mock(return_value=SessionStatus.RUNNING),
                created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
                last_interaction_at=datetime.fromisoformat("2023-01-01T00:05:00")
            )
            for i in range(5)
        }
        
        self.mock_session_service.get_all_sessions.return_value = mock_sessions
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.get("/api/sessions/?limit=2&offset=1")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["sessions"]) == 2
    
    def test_terminate_session_success(self):
        """Test successful session termination."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.delete(f"/api/sessions/{session_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["session_id"] == session_id
        assert data["message"] == "Session terminated successfully"
        
        self.mock_session_service.get_session.assert_called_once_with(SessionID(session_id))
        self.mock_session_service.delete_session.assert_called_once_with(SessionID(session_id))
    
    def test_terminate_session_not_found(self):
        """Test session termination for non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        self.mock_session_service.get_session.return_value = None
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            response = self.client.delete(f"/api/sessions/{session_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "SESSION_NOT_FOUND"
        assert session_id in data["error"]["message"]
        
        self.mock_session_service.delete_session.assert_not_called()


class TestSessionValidation:
    """Test suite for session validation edge cases."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
    
    def test_pagination_parameter_validation(self):
        """Test pagination parameter validation."""
        # Test invalid limit values
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            # Limit too low
            response = self.client.get("/api/sessions/?limit=0")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Limit too high
            response = self.client.get("/api/sessions/?limit=101")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Negative offset
            response = self.client.get("/api/sessions/?offset=-1")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_concurrent_session_creation(self):
        """Test concurrent session creation behavior."""
        # This test would need async testing capabilities
        # For now, we'll test the synchronous behavior
        
        # Arrange
        self.mock_session_service.create_session.side_effect = [
            SessionID("session-1"),
            SessionID("session-2"),
            None  # Third call hits limit
        ]
        self.mock_session_service.max_sessions = 2
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            # First two should succeed
            response1 = self.client.post("/api/sessions/")
            assert response1.status_code == status.HTTP_201_CREATED
            
            response2 = self.client.post("/api/sessions/")
            assert response2.status_code == status.HTTP_201_CREATED
            
            # Third should fail due to limit
            response3 = self.client.post("/api/sessions/")
            assert response3.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestWebSocketEndpoint:
    """Test suite for WebSocket endpoint functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_session_service = Mock(spec=SessionService)
    
    def test_websocket_connection_success(self):
        """Test successful WebSocket connection."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Should receive connection confirmation
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert data["data"]["session_id"] == session_id
                assert data["data"]["status"] == SessionStatus.RUNNING.value
                
                # Update session interaction should be called
                self.mock_session_service.update_session_last_interaction_at.assert_called()
    
    def test_websocket_connection_invalid_session(self):
        """Test WebSocket connection with invalid session."""
        # Arrange
        session_id = "invalid-session"
        self.mock_session_service.get_session.return_value = None
        
        # Override the FastAPI dependency
        from llmgine.api.main import app
        from llmgine.api.routers.dependencies import get_session_service
        
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Should receive error message
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert data["data"]["code"] == "SESSION_NOT_FOUND"
                assert session_id in data["data"]["message"]
    
    def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong functionality."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send ping
                websocket.send_json({"type": "ping", "data": {"timestamp": "123456789"}})
                
                # Should receive pong
                data = websocket.receive_json()
                assert data["type"] == "pong"
                assert data["data"]["timestamp"] == "123456789"
    
    def test_websocket_status_request(self):
        """Test WebSocket status request functionality."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        mock_session.created_at = datetime.fromisoformat("2023-01-01T00:00:00")
        mock_session.last_interaction_at = datetime.fromisoformat("2023-01-01T00:05:00")
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send status request
                websocket.send_json({"type": "status", "data": {}})
                
                # Should receive status response
                data = websocket.receive_json()
                assert data["type"] == "status"
                assert data["data"]["session_id"] == session_id
                assert data["data"]["status"] == SessionStatus.RUNNING.value
                assert "created_at" in data["data"]
                assert "last_interaction_at" in data["data"]
    
    def test_websocket_invalid_message_type(self):
        """Test WebSocket handling of invalid message types."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependency
        from llmgine.api.main import app
        from llmgine.api.routers.dependencies import get_session_service
        
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send invalid message type
                websocket.send_json({"type": "invalid", "data": {}})
                
                # Should receive error response
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert data["data"]["code"] == "INVALID_MESSAGE_TYPE"
                assert "invalid" in data["data"]["message"]
    
    def test_websocket_invalid_json(self):
        """Test WebSocket handling of invalid JSON."""
        # Arrange
        session_id = "test-session-123"
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
        
        # Override the FastAPI dependencies
        app.dependency_overrides[get_session_service] = lambda: self.mock_session_service

        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service):
            with self.client.websocket_connect(f"/api/sessions/{session_id}/ws") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send invalid JSON
                websocket.send_text("invalid json")
                
                # Should receive error response
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert data["data"]["code"] == "INVALID_JSON"
                assert "valid JSON" in data["data"]["message"]