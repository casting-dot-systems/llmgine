"""
Unit tests for the commands API endpoints.

This module contains comprehensive tests for command execution endpoints
including command execution, validation, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status

from llmgine.api.main import app
from llmgine.api.models.responses import ResponseStatus
from llmgine.api.services.session_service import SessionService, SessionStatus
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.llm import SessionID


class TestCommandEndpoints:
    """Test suite for command execution endpoints."""
    
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
    
    def test_execute_command_success(self):
        """Test successful command execution."""
        # Arrange
        command_id = "test-command-123"
        command_data = {
            "command_id": command_id,
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        mock_command_result = Mock(spec=CommandResult)
        mock_command_result.success = True
        mock_command_result.result = {"output": "test result"}
        
        # Mock async execute method
        self.mock_message_bus.execute = AsyncMock(return_value=mock_command_result)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
        assert data["command_id"] == command_id
        assert data["session_id"] == self.session_id
        assert data["command_result"] == mock_command_result
        
        # Verify service calls
        self.mock_session_service.update_session_last_interaction_at.assert_called_once_with(SessionID(self.session_id))
        self.mock_message_bus.execute.assert_called_once()
    
    def test_execute_command_session_mismatch(self):
        """Test command execution with session ID mismatch."""
        # Arrange
        command_id = "test-command-123"
        wrong_session_id = "wrong-session-456"
        command_data = {
            "command_id": command_id,
            "session_id": wrong_session_id,  # Different from URL session_id
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["command_id"] == command_id
        assert data["session_id"] == self.session_id
        assert "does not match" in data["error"]
        
        # Verify message bus was not called
        self.mock_message_bus.execute.assert_not_called()
    
    def test_execute_command_execution_exception(self):
        """Test command execution with exception during execution."""
        # Arrange
        command_id = "test-command-123"
        command_data = {
            "command_id": command_id,
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        # Mock execute method to raise exception
        self.mock_message_bus.execute = AsyncMock(side_effect=Exception("Command execution failed"))
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.FAILED.value
        assert data["command_id"] == command_id
        assert data["session_id"] == self.session_id
        assert "Command execution failed" in data["error"]
    
    def test_execute_command_invalid_session(self):
        """Test command execution with invalid session."""
        # Arrange
        command_id = "test-command-123"
        invalid_session_id = "invalid-session"
        command_data = {
            "command_id": command_id,
            "session_id": invalid_session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        # Mock session validation failure
        with patch('llmgine.api.routers.dependencies.validate_session', side_effect=Exception("Session not found")):
            response = self.client.post(
                f"/api/sessions/{invalid_session_id}/commands/",
                json=command_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestCommandValidation:
    """Test suite for command validation and edge cases."""
    
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
    
    def test_command_missing_required_fields(self):
        """Test command execution with missing required fields."""
        # Test missing command_id
        command_data = {
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test missing session_id
        command_data = {
            "command_id": "test-command-123",
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_command_invalid_json(self):
        """Test command execution with invalid JSON."""
        with patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                data="invalid json"
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_command_empty_parameters(self):
        """Test command execution with empty parameters."""
        command_data = {
            "command_id": "test-command-123",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {}
        }
        
        mock_command_result = Mock(spec=CommandResult)
        mock_command_result.success = True
        mock_command_result.result = {"output": "test result"}
        self.mock_message_bus.execute = AsyncMock(return_value=mock_command_result)
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
    
    def test_command_special_characters(self):
        """Test command execution with special characters in parameters."""
        command_data = {
            "command_id": "test-command-123",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {
                "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
                "unicode": "测试unicode字符",
                "newlines": "line1\nline2\nline3"
            }
        }
        
        mock_command_result = Mock(spec=CommandResult)
        mock_command_result.success = True
        mock_command_result.result = {"output": "test result"}
        self.mock_message_bus.execute = AsyncMock(return_value=mock_command_result)
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value
    
    def test_command_large_payload(self):
        """Test command execution with large payload."""
        large_data = "x" * 10000  # 10KB of data
        command_data = {
            "command_id": "test-command-123",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"large_data": large_data}
        }
        
        mock_command_result = Mock(spec=CommandResult)
        mock_command_result.success = True
        mock_command_result.result = {"output": "test result"}
        self.mock_message_bus.execute = AsyncMock(return_value=mock_command_result)
        
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            response = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == ResponseStatus.SUCCESS.value


class TestCommandConcurrency:
    """Test suite for command execution concurrency scenarios."""
    
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
    
    def test_concurrent_command_execution(self):
        """Test concurrent command execution handling."""
        # Arrange
        command_data_1 = {
            "command_id": "command-1",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        command_data_2 = {
            "command_id": "command-2",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value2"}
        }
        
        mock_command_result_1 = Mock(spec=CommandResult)
        mock_command_result_1.success = True
        mock_command_result_1.result = {"output": "result 1"}
        
        mock_command_result_2 = Mock(spec=CommandResult)
        mock_command_result_2.success = True
        mock_command_result_2.result = {"output": "result 2"}
        
        self.mock_message_bus.execute = AsyncMock(side_effect=[mock_command_result_1, mock_command_result_2])
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            
            response_1 = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data_1
            )
            
            response_2 = self.client.post(
                f"/api/sessions/{self.session_id}/commands/",
                json=command_data_2
            )
        
        # Assert
        assert response_1.status_code == status.HTTP_200_OK
        assert response_2.status_code == status.HTTP_200_OK
        
        data_1 = response_1.json()
        data_2 = response_2.json()
        
        assert data_1["command_id"] == "command-1"
        assert data_2["command_id"] == "command-2"
        assert data_1["status"] == ResponseStatus.SUCCESS.value
        assert data_2["status"] == ResponseStatus.SUCCESS.value
        
        # Verify both commands were executed
        assert self.mock_message_bus.execute.call_count == 2
    
    def test_session_interaction_updates(self):
        """Test that session interaction is updated for each command."""
        # Arrange
        command_data = {
            "command_id": "test-command-123",
            "session_id": self.session_id,
            "command_type": "test_command",
            "parameters": {"param1": "value1"}
        }
        
        mock_command_result = Mock(spec=CommandResult)
        mock_command_result.success = True
        mock_command_result.result = {"output": "test result"}
        self.mock_message_bus.execute = AsyncMock(return_value=mock_command_result)
        
        # Act
        with patch('llmgine.api.routers.dependencies.get_session_service', return_value=self.mock_session_service), \
             patch('llmgine.api.routers.dependencies.get_message_bus', return_value=self.mock_message_bus), \
             patch('llmgine.api.routers.dependencies.validate_session', return_value=SessionID(self.session_id)):
            
            # Execute multiple commands
            for i in range(3):
                command_data["command_id"] = f"command-{i}"
                response = self.client.post(
                    f"/api/sessions/{self.session_id}/commands/",
                    json=command_data
                )
                assert response.status_code == status.HTTP_200_OK
        
        # Assert
        # Session interaction should be updated for each command
        assert self.mock_session_service.update_session_last_interaction_at.call_count == 3
        
        # All calls should be with the same session ID
        for call in self.mock_session_service.update_session_last_interaction_at.call_args_list:
            assert call[0][0] == SessionID(self.session_id)