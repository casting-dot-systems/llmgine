from typing import Optional
from pydantic import BaseModel

from llmgine.api.models.responses import ResponseStatus
from llmgine.messages.commands import CommandResult

class CommandExecuteResponse(BaseModel):
    """Response model for command execution"""
    command_id: str
    session_id: str
    command_result: Optional[CommandResult] = None
    status: ResponseStatus
    error: Optional[str] = None
