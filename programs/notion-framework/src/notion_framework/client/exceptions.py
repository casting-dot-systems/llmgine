"""Exception classes for the Notion Framework."""

from typing import Any, Dict, Optional


class NotionFrameworkError(Exception):
    """Base exception for all Notion Framework errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotionAPIError(NotionFrameworkError):
    """Raised when the Notion API returns an error."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.error_code = error_code


class NotionAuthError(NotionAPIError):
    """Raised when authentication with Notion API fails."""
    
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401, error_code="unauthorized")


class NotionRateLimitError(NotionAPIError):
    """Raised when Notion API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None) -> None:
        super().__init__(message, status_code=429, error_code="rate_limited")
        self.retry_after = retry_after


class NotionValidationError(NotionFrameworkError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field


class SchemaError(NotionFrameworkError):
    """Raised when there are issues with database schema analysis."""
    
    def __init__(self, message: str, database_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.database_id = database_id


class CodeGenerationError(NotionFrameworkError):
    """Raised when code generation fails."""
    
    def __init__(self, message: str, template: Optional[str] = None) -> None:
        super().__init__(message)
        self.template = template
