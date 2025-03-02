class WorkflowError(Exception):
    """Base class for all workflow exceptions"""
    pass

class WorkflowExecutionError(WorkflowError):
    """Raised when there is an error executing a workflow"""
    pass

class BlockExecutionError(WorkflowError):
    """Raised when there is an error executing a block"""
    pass

class CompileError(WorkflowError):
    """Raised when there is an error compiling data in a socket or plug"""
    pass

class SocketError(WorkflowError):
    """Raised when there is an error with socket operations"""
    pass

class ValidationError(WorkflowError):
    """Raised when validation fails"""
    pass

class QueueError(WorkflowError):
    """Raised when there is an error with the workflow queue"""
    pass

class CompileIncompleteSocketError(CompileError):
    """Raised when trying to compile a socket that has incomplete data"""
    pass
