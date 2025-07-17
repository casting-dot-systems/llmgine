"""
Unit tests for the engines API endpoints.

This module contains comprehensive tests for engine management endpoints
including creation, listing, retrieval, connection, and disconnection.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from llmgine.api.main import app
from llmgine.api.models.responses import ResponseStatus
from llmgine.api.services.engine_service import EngineService
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.api.utils.error_handler import SessionIDValidationError
from llmgine.llm import EngineID, SessionID
from llmgine.llm.engine.engine import Engine, EngineStatus
from llmgine.api.routers.dependencies import get_engine_service, validate_session


class TestEngineEndpoints:
    """Test suite for engine management endpoints."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_engine_service = Mock(spec=EngineService)
        self.mock_session_service = Mock(spec=SessionService)
        self.session_id = "test-session-123"
        
        # Mock session validation
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
    
    def test_create_engine_success(self):
        """Test successful engine creation."""
        # Arrange
        engine_id = EngineID("test-engine-123")
        engine = Engine()

        self.mock_engine_service.create_engine.return_value = engine_id
        self.mock_engine_service.max_engines = 10
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)

        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/",
                json={"engine": engine.model_dump()}
            )
            print(response.json())
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["engine_id"] == str(engine_id)
        assert data["message"] == "Engine created successfully"
        self.mock_engine_service.create_engine.assert_called_once()
    
    def test_create_engine_max_limit_reached(self):
        """Test engine creation when maximum limit is reached."""
        # Arrange
        self.mock_engine_service.create_engine.return_value = None
        self.mock_engine_service.max_engines = 10
        engine = Engine()

        # Override the FastAPI dependency
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)

        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/",
                json={"engine": engine.model_dump()}
            )

        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "RESOURCE_LIMIT_EXCEEDED"
        assert "Maximum engines limit (10) exceeded" in data["error"]["message"]
    
    def test_list_engines_success(self):
        """Test successful engine listing with pagination."""
        # Arrange
        mock_engines = {
            EngineID("engine-1"): Mock(spec=Engine, engine_id=EngineID("engine-1"), status=EngineStatus.RUNNING),
            EngineID("engine-2"): Mock(spec=Engine, engine_id=EngineID("engine-2"), status=EngineStatus.IDLE)
        }
        
        self.mock_engine_service.get_all_engines.return_value = mock_engines
        
        # Override the FastAPI dependency
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)

        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/?limit=10&offset=0")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["engines"]) == 2
        assert data["message"] == "Engines listed successfully, from 0 to 10 of 2"
    
    def test_list_engines_pagination(self):
        """Test engine listing with pagination parameters."""
        # Arrange
        mock_engines = {
            EngineID(f"engine-{i}"): Mock(spec=Engine, engine_id=EngineID(f"engine-{i}"), status=EngineStatus.RUNNING)
            for i in range(5)
        }
        
        self.mock_engine_service.get_all_engines.return_value = mock_engines
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service

        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/?limit=2&offset=1")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["engines"]) == 2
        assert data["message"] == "Engines listed successfully, from 1 to 3 of 5"
    
    def test_get_engine_success(self):
        """Test successful engine retrieval."""
        # Arrange
        engine_id = "test-engine-123"
        mock_engine = Engine()
        
        self.mock_engine_service.get_engine.return_value = mock_engine
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/{engine_id}")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["engine"] == mock_engine.model_dump()
        self.mock_engine_service.get_engine.assert_called_once_with(EngineID(engine_id))
    
    def test_get_engine_not_found(self):
        """Test engine retrieval for non-existent engine."""
        # Arrange
        engine_id = "nonexistent-engine"
        self.mock_engine_service.get_engine.return_value = None
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/{engine_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "ENGINE_NOT_FOUND"
        assert engine_id in data["error"]["message"]
    
    def test_connect_engine_success(self):
        """Test successful engine connection."""
        # Arrange
        engine_id = "test-engine-123"
        self.mock_engine_service.register_engine.return_value = EngineID(engine_id)
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/connect",
                json={"engine_id": engine_id}
            )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["engine_id"] == engine_id
        assert data["message"] == "Engine connected successfully"
        
        self.mock_engine_service.register_engine.assert_called_once_with(
            SessionID(self.session_id),
            EngineID(engine_id)
        )
    
    def test_connect_engine_not_found(self):
        """Test engine connection for non-existent engine."""
        # Arrange
        engine_id = "nonexistent-engine"
        self.mock_engine_service.register_engine.return_value = None
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/connect",
                json={"engine_id": engine_id}
            )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "ENGINE_CONNECTION_FAILED"
        assert engine_id in data["error"]["message"]
    
    def test_disconnect_engine_success(self):
        """Test successful engine disconnection."""
        # Arrange
        engine_id = "test-engine-123"
        self.mock_engine_service.unregister_engine.return_value = EngineID(engine_id)
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.delete(f"/api/sessions/{self.session_id}/engines/disconnect")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["engine_id"] == engine_id
        assert data["message"] == "Engine disconnected successfully"
        
        self.mock_engine_service.unregister_engine.assert_called_once_with(SessionID(self.session_id))
    
    def test_disconnect_engine_not_connected(self):
        """Test engine disconnection when no engine is connected."""
        # Arrange
        self.mock_engine_service.unregister_engine.return_value = None
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.delete(f"/api/sessions/{self.session_id}/engines/disconnect")
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "ENGINE_CONNECTION_FAILED"
        assert self.session_id in data["error"]["message"]


class TestEngineValidation:
    """Test suite for engine validation and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_engine_service = Mock(spec=EngineService)
        self.mock_session_service = Mock(spec=SessionService)
        self.session_id = "test-session-123"
        
        # Mock session validation
        mock_session = Mock()
        mock_session.get_status.return_value = SessionStatus.RUNNING
        self.mock_session_service.get_session.return_value = mock_session
    
    def test_pagination_parameter_validation(self):
        """Test pagination parameter validation for engine listing."""
        # Mock session validation
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            # Test invalid limit values
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/?limit=0")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/?limit=101")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test negative offset
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/?offset=-1")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_invalid_engine_id_format(self):
        """Test handling of invalid engine ID formats."""
        # Test with various invalid engine IDs
        invalid_ids = ["   ", "engine with spaces", "engine/with/slashes"]
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        self.mock_engine_service.get_engine.return_value = None

        for invalid_id in invalid_ids:
            with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
                 patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
                response = self.client.get(f"/api/sessions/{self.session_id}/engines/{invalid_id}")
                # Should still attempt to look up the engine
                print(response.json())
                assert response.status_code in [status.HTTP_404_NOT_FOUND]
    
    def test_engine_connection_race_condition(self):
        """Test engine connection race condition handling."""
        # Arrange
        engine_id = "test-engine-123"
        
        # Simulate race condition: first call succeeds, second fails
        self.mock_engine_service.register_engine.side_effect = [
            EngineID(engine_id),
            None  # Second call fails (already connected)
        ]
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act & Assert
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            # First connection should succeed
            response1 = self.client.post(
                f"/api/sessions/{self.session_id}/engines/connect",
                json={"engine_id": engine_id}
            )
            assert response1.status_code == status.HTTP_200_OK
            
            # Second connection should fail
            response2 = self.client.post(
                f"/api/sessions/{self.session_id}/engines/connect",
                json={"engine_id": engine_id}
            )
            assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_session_id(self):
        """Test engine operations with invalid session ID."""
        # Arrange
        invalid_session_id = "invalid-session"
        app.dependency_overrides.clear()

        # Mock session validation failure
        with patch('llmgine.api.routers.dependencies.validate_session'):
            # Test engine creation
            response = self.client.post(
                f"/api/sessions/{invalid_session_id}/engines/",
                json={"engine": Engine().model_dump()}
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Test engine listing
            response = self.client.get(f"/api/sessions/{invalid_session_id}/engines/")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

class TestEngineServiceErrors:
    """Test suite for engine service error handling."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.mock_engine_service = Mock(spec=EngineService)
        self.session_id = "test-session-123"
        
        # Mock session validation
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            pass
    
    def test_engine_service_exception_handling(self):
        """Test handling of engine service exceptions."""
        # Arrange
        self.mock_engine_service.get_all_engines.side_effect = Exception("Database connection failed")
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.get(f"/api/sessions/{self.session_id}/engines/")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "unexpected error" in data["error"]["message"]
    
    def test_engine_creation_service_exception(self):
        """Test handling of engine creation service exceptions."""
        # Arrange
        self.mock_engine_service.create_engine.side_effect = Exception("Engine initialization failed")
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/",
                json={"engine_type": "test", "config": {}}
            )
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "INTERNAL_ERROR"
    
    def test_engine_connection_service_exception(self):
        """Test handling of engine connection service exceptions."""
        # Arrange
        engine_id = "test-engine-123"
        self.mock_engine_service.register_engine.side_effect = Exception("Registration failed")
        
        app.dependency_overrides[validate_session] = lambda: SessionID(self.session_id)
        app.dependency_overrides[get_engine_service] = lambda: self.mock_engine_service
        # Act
        with patch('llmgine.api.routers.dependencies.get_engine_service', return_value=self.mock_engine_service), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/engines/connect",
                json={"engine_id": engine_id}
            )
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()["detail"]
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["error"]["code"] == "INTERNAL_ERROR"