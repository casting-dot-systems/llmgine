"""
Test configuration and fixtures for API tests.

This module provides common test fixtures and configuration
for all API endpoint tests.
"""

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient

from llmgine.api.main import app
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.api.services.engine_service import EngineService
from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID, EngineID


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_session_service():
    """Create a mock session service."""
    service = Mock(spec=SessionService)
    service.max_sessions = 100
    service.idle_timeout = 300
    service.delete_idle_timeout = 600
    return service


@pytest.fixture
def mock_engine_service():
    """Create a mock engine service."""
    service = Mock(spec=EngineService)
    service.max_engines = 10
    service.idle_timeout = 3000
    service.delete_idle_timeout = 6000
    return service


@pytest.fixture
def mock_message_bus():
    """Create a mock message bus."""
    return Mock(spec=MessageBus)


@pytest.fixture
def test_session_id():
    """Provide a test session ID."""
    return "test-session-123"


@pytest.fixture
def test_engine_id():
    """Provide a test engine ID."""
    return "test-engine-123"


@pytest.fixture
def mock_session(test_session_id):
    """Create a mock session object."""
    session = Mock()
    session.get_session_id.return_value = SessionID(test_session_id)
    session.get_status.return_value = SessionStatus.RUNNING
    session.created_at = "2023-01-01T00:00:00"
    session.last_interaction_at = "2023-01-01T00:05:00"
    session.update_last_interaction_at = Mock()
    session.update_status = Mock()
    return session


@pytest.fixture
def mock_engine(test_engine_id):
    """Create a mock engine object."""
    engine = Mock()
    engine.engine_id = EngineID(test_engine_id)
    engine.status = "RUNNING"
    engine.updated_at = "2023-01-01T00:00:00"
    return engine


@pytest.fixture
def valid_session_setup(mock_session_service, mock_session, test_session_id):
    """Set up a valid session for testing."""
    mock_session_service.get_session.return_value = mock_session
    return mock_session_service


@pytest.fixture
def invalid_session_setup(mock_session_service):
    """Set up an invalid session for testing."""
    mock_session_service.get_session.return_value = None
    return mock_session_service


@pytest.fixture
def sample_command_data(test_session_id):
    """Provide sample command data for testing."""
    return {
        "command_id": "test-command-123",
        "session_id": test_session_id,
        "command_type": "test_command",
        "parameters": {"param1": "value1", "param2": "value2"}
    }


@pytest.fixture
def sample_event_data(test_session_id):
    """Provide sample event data for testing."""
    return {
        "event_id": "test-event-123",
        "session_id": test_session_id,
        "event_type": "test_event",
        "data": {"key": "value", "timestamp": "2023-01-01T00:00:00"}
    }


@pytest.fixture
def sample_engine_data():
    """Provide sample engine data for testing."""
    return {
        "engine_type": "test_engine",
        "config": {
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "edge_case: marks tests as edge case tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


# Common test utilities
class APITestHelpers:
    """Helper utilities for API testing."""
    
    @staticmethod
    def assert_error_response(response, expected_status_code, expected_error_code):
        """Assert that a response contains the expected error information."""
        assert response.status_code == expected_status_code
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"]["code"] == expected_error_code
    
    @staticmethod
    def assert_success_response(response, expected_status_code):
        """Assert that a response is successful."""
        assert response.status_code == expected_status_code
        data = response.json()
        assert data["status"] == "success"
    
    @staticmethod
    def create_paginated_response_assertions(response, expected_total, expected_limit, expected_offset):
        """Assert paginated response structure."""
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] == expected_total
        assert data["limit"] == expected_limit
        assert data["offset"] == expected_offset
        assert isinstance(data.get("sessions", data.get("engines", data.get("events", []))), list)


@pytest.fixture
def api_helpers():
    """Provide API test helpers."""
    return APITestHelpers