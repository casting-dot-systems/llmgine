"""
Response models and status enums for the LLMGine API.

This module provides standardized response models and status enums
for consistent API responses across all endpoints.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ResponseStatus(Enum):
    """Enumeration of possible response statuses."""
    SUCCESS = "success"
    FAILED = "failed"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    field: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    status: ResponseStatus
    error: Optional[ErrorDetail] = None
    message: Optional[str] = None
    