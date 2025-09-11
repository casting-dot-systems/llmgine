class ToolError(Exception):
    """Base class for tool-related errors."""


class ToolRegistrationError(ToolError):
    pass


class ToolValidationError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass


class ToolTimeoutError(ToolExecutionError):
    pass