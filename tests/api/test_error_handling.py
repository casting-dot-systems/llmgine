"""
Unit tests for the error handling utilities.

This module contains comprehensive tests for the error handling utilities
including custom exceptions, error detail creation, and HTTP exception handling.
"""

import pytest
from fastapi import HTTPException

from llmgine.api.utils.error_handler import (
    APIError,
    SessionNotFoundError,
    SessionInvalidError,
    EngineNotFoundError,
    EngineConnectionError,
    ResourceLimitError,
    ValidationError,
    CommandExecutionError,
    EventPublishError,
    create_error_detail,
    handle_api_error,
    handle_unexpected_error
)
from llmgine.api.models.responses import ResponseStatus, ErrorDetail


class TestAPIError:
    """Test suite for the base APIError class."""
    
    def test_api_error_creation(self):
        """Test basic APIError creation with required parameters."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message",
            status_code=400
        )
        
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.status_code == 400
        assert error.field is None
        assert error.context == {}
    
    def test_api_error_creation_with_optional_params(self):
        """Test APIError creation with optional parameters."""
        context = {"key": "value", "number": 42}
        error = APIError(
            code="TEST_ERROR",
            message="Test error message",
            status_code=422,
            field="test_field",
            context=context
        )
        
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.status_code == 422
        assert error.field == "test_field"
        assert error.context == context
    
    def test_api_error_default_status_code(self):
        """Test APIError with default status code."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message"
        )
        
        assert error.status_code == 400


class TestSpecificErrors:
    """Test suite for specific error classes."""
    
    def test_session_not_found_error(self):
        """Test SessionNotFoundError creation and properties."""
        session_id = "test-session-123"
        error = SessionNotFoundError(session_id)
        
        assert error.code == "SESSION_NOT_FOUND"
        assert session_id in error.message
        assert error.status_code == 404
        assert error.context["session_id"] == session_id
    
    def test_session_invalid_error(self):
        """Test SessionInvalidError creation and properties."""
        session_id = "test-session-123"
        current_status = "FAILED"
        error = SessionInvalidError(session_id, current_status)
        
        assert error.code == "SESSION_INVALID_STATE"
        assert session_id in error.message
        assert current_status in error.message
        assert error.status_code == 400
        assert error.context["session_id"] == session_id
        assert error.context["current_status"] == current_status
    
    def test_engine_not_found_error(self):
        """Test EngineNotFoundError creation and properties."""
        engine_id = "test-engine-123"
        error = EngineNotFoundError(engine_id)
        
        assert error.code == "ENGINE_NOT_FOUND"
        assert engine_id in error.message
        assert error.status_code == 404
        assert error.context["engine_id"] == engine_id
    
    def test_engine_connection_error(self):
        """Test EngineConnectionError creation and properties."""
        engine_id = "test-engine-123"
        reason = "Engine already connected"
        error = EngineConnectionError(engine_id, reason)
        
        assert error.code == "ENGINE_CONNECTION_FAILED"
        assert engine_id in error.message
        assert reason in error.message
        assert error.status_code == 400
        assert error.context["engine_id"] == engine_id
        assert error.context["reason"] == reason
    
    def test_resource_limit_error(self):
        """Test ResourceLimitError creation and properties."""
        resource_type = "sessions"
        limit = 100
        error = ResourceLimitError(resource_type, limit)
        
        assert error.code == "RESOURCE_LIMIT_EXCEEDED"
        assert resource_type in error.message
        assert str(limit) in error.message
        assert error.status_code == 429
        assert error.context["resource_type"] == resource_type
        assert error.context["limit"] == limit
    
    def test_validation_error(self):
        """Test ValidationError creation and properties."""
        field = "test_field"
        message = "Field is required"
        value = "invalid_value"
        error = ValidationError(field, message, value)
        
        assert error.code == "VALIDATION_ERROR"
        assert field in error.message
        assert message in error.message
        assert error.status_code == 422
        assert error.field == field
        assert error.context["value"] == value
    
    def test_validation_error_without_value(self):
        """Test ValidationError creation without value."""
        field = "test_field"
        message = "Field is required"
        error = ValidationError(field, message)
        
        assert error.code == "VALIDATION_ERROR"
        assert field in error.message
        assert message in error.message
        assert error.status_code == 422
        assert error.field == field
        assert error.context == {}
    
    def test_command_execution_error(self):
        """Test CommandExecutionError creation and properties."""
        command_id = "test-command-123"
        reason = "Command timeout"
        error = CommandExecutionError(command_id, reason)
        
        assert error.code == "COMMAND_EXECUTION_FAILED"
        assert command_id in error.message
        assert reason in error.message
        assert error.status_code == 500
        assert error.context["command_id"] == command_id
        assert error.context["reason"] == reason
    
    def test_event_publish_error(self):
        """Test EventPublishError creation and properties."""
        event_id = "test-event-123"
        reason = "Event bus unavailable"
        error = EventPublishError(event_id, reason)
        
        assert error.code == "EVENT_PUBLISH_FAILED"
        assert event_id in error.message
        assert reason in error.message
        assert error.status_code == 500
        assert error.context["event_id"] == event_id
        assert error.context["reason"] == reason


class TestErrorDetailCreation:
    """Test suite for error detail creation utilities."""
    
    def test_create_error_detail(self):
        """Test creation of ErrorDetail from APIError."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message",
            status_code=400,
            field="test_field",
            context={"key": "value"}
        )
        
        detail = create_error_detail(error)
        
        assert isinstance(detail, ErrorDetail)
        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test error message"
        assert detail.field == "test_field"
        assert detail.context == {"key": "value"}
    
    def test_create_error_detail_minimal(self):
        """Test creation of ErrorDetail with minimal APIError."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message"
        )
        
        detail = create_error_detail(error)
        
        assert isinstance(detail, ErrorDetail)
        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test error message"
        assert detail.field is None
        assert detail.context == {}


class TestHTTPExceptionHandling:
    """Test suite for HTTP exception handling utilities."""
    
    def test_handle_api_error(self):
        """Test conversion of APIError to HTTPException."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message",
            status_code=400,
            field="test_field",
            context={"key": "value"}
        )
        
        http_exception = handle_api_error(error)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 400
        assert http_exception.detail["status"] == ResponseStatus.FAILED.value
        assert http_exception.detail["error"]["code"] == "TEST_ERROR"
        assert http_exception.detail["error"]["message"] == "Test error message"
        assert http_exception.detail["error"]["field"] == "test_field"
        assert http_exception.detail["error"]["context"] == {"key": "value"}
    
    def test_handle_api_error_with_specific_error_types(self):
        """Test handling of specific error types."""
        # Test SessionNotFoundError
        session_error = SessionNotFoundError("test-session-123")
        http_exception = handle_api_error(session_error)
        
        assert http_exception.status_code == 404
        assert http_exception.detail["error"]["code"] == "SESSION_NOT_FOUND"
        
        # Test ResourceLimitError
        resource_error = ResourceLimitError("sessions", 100)
        http_exception = handle_api_error(resource_error)
        
        assert http_exception.status_code == 429
        assert http_exception.detail["error"]["code"] == "RESOURCE_LIMIT_EXCEEDED"
        
        # Test ValidationError
        validation_error = ValidationError("field", "message", "value")
        http_exception = handle_api_error(validation_error)
        
        assert http_exception.status_code == 422
        assert http_exception.detail["error"]["code"] == "VALIDATION_ERROR"
        assert http_exception.detail["error"]["field"] == "field"
    
    def test_handle_unexpected_error(self):
        """Test handling of unexpected errors."""
        unexpected_error = Exception("Something went wrong")
        context = {"operation": "test_operation", "param": "value"}
        
        http_exception = handle_unexpected_error(unexpected_error, context)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 500
        assert http_exception.detail["status"] == ResponseStatus.FAILED.value
        assert http_exception.detail["error"]["code"] == "INTERNAL_ERROR"
        assert http_exception.detail["error"]["message"] == "An unexpected error occurred"
        assert http_exception.detail["error"]["context"] == context
    
    def test_handle_unexpected_error_without_context(self):
        """Test handling of unexpected errors without context."""
        unexpected_error = Exception("Something went wrong")
        
        http_exception = handle_unexpected_error(unexpected_error)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 500
        assert http_exception.detail["status"] == ResponseStatus.FAILED.value
        assert http_exception.detail["error"]["code"] == "INTERNAL_ERROR"
        assert http_exception.detail["error"]["message"] == "An unexpected error occurred"
        assert http_exception.detail["error"]["context"] == {}


class TestErrorHandlingEdgeCases:
    """Test suite for error handling edge cases."""
    
    def test_error_with_none_context(self):
        """Test error creation with None context."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message",
            context=None
        )
        
        assert error.context == {}
    
    def test_error_with_empty_string_values(self):
        """Test error creation with empty string values."""
        error = APIError(
            code="",
            message="",
            field=""
        )
        
        assert error.code == ""
        assert error.message == ""
        assert error.field == ""
    
    def test_error_with_special_characters(self):
        """Test error creation with special characters."""
        special_message = "Error with special chars: !@#$%^&*()_+-=[]{}|;:,.<>?"
        error = APIError(
            code="SPECIAL_ERROR",
            message=special_message
        )
        
        assert error.message == special_message
        
        detail = create_error_detail(error)
        assert detail.message == special_message
    
    def test_error_with_unicode_characters(self):
        """Test error creation with Unicode characters."""
        unicode_message = "Unicode error: 测试错误消息"
        error = APIError(
            code="UNICODE_ERROR",
            message=unicode_message
        )
        
        assert error.message == unicode_message
        
        detail = create_error_detail(error)
        assert detail.message == unicode_message
    
    def test_large_context_data(self):
        """Test error creation with large context data."""
        large_context = {
            "large_field": "x" * 1000,
            "nested": {
                "level1": {
                    "level2": {
                        "data": list(range(100))
                    }
                }
            }
        }
        
        error = APIError(
            code="LARGE_CONTEXT_ERROR",
            message="Error with large context",
            context=large_context
        )
        
        assert error.context == large_context
        
        detail = create_error_detail(error)
        assert detail.context == large_context
    
    def test_error_inheritance(self):
        """Test that custom errors inherit from APIError properly."""
        session_error = SessionNotFoundError("test-session")
        engine_error = EngineNotFoundError("test-engine")
        
        assert isinstance(session_error, APIError)
        assert isinstance(engine_error, APIError)
        assert isinstance(session_error, Exception)
        assert isinstance(engine_error, Exception)
    
    def test_error_string_representation(self):
        """Test string representation of errors."""
        error = APIError(
            code="TEST_ERROR",
            message="Test error message"
        )
        
        # The string representation should be the message
        assert str(error) == "Test error message"
        
        session_error = SessionNotFoundError("test-session-123")
        assert "test-session-123" in str(session_error)