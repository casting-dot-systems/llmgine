# POST /api/sessions/{session_id}/commands
# - Execute a command on the message bus
# - Body: Command data (command_type, parameters, metadata)

# GET /api/sessions/{session_id}/commands/{command_id}
# - Get command execution status and result

# POST /api/sessions/{session_id}/commands/batch
# - Execute multiple commands in sequence

"""
Command management router for the LLMGine API.

This router handles:
- Executing a command on the message bus
- Getting command execution status and result
- Executing multiple commands in sequence
"""

from fastapi import APIRouter, Depends

from llmgine.api.models import ResponseStatus, CommandExecuteResponse
from llmgine.api.services.session_service import SessionService
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.api.routers.dependencies import validate_session, get_session_service, get_message_bus
from llmgine.llm import SessionID

router = APIRouter(prefix="/api/sessions/{session_id}/commands", tags=["commands"])

@router.post("/", response_model=CommandExecuteResponse, status_code=200)
async def execute_command(
    session_id: str,
    command: Command,
    session_service: SessionService = Depends(get_session_service),
    message_bus: MessageBus = Depends(get_message_bus),
    _: SessionID = Depends(validate_session)
) -> CommandExecuteResponse:
    """
    Execute a command on the message bus
    """

    try:
        # Update session last interaction time
        session_service.update_session_last_interaction_at(SessionID(session_id))
        
        # Check if event session_id matches the session_id
        if command.session_id != session_id:
            return CommandExecuteResponse(
                command_id=command.command_id,
                session_id=session_id,
                status=ResponseStatus.FAILED,
                error=f"Command session_id {command.session_id} does not match session_id {session_id}"
            )
        
        # Execute command
        command_result : CommandResult = await message_bus.execute(command)
        
    except Exception as e:
        return CommandExecuteResponse(
            command_id=command.command_id,
            session_id=session_id,
            status=ResponseStatus.FAILED,
            error=str(e)
        )

    return CommandExecuteResponse(
        command_id=command.command_id,
        session_id=session_id,
        command_result=command_result,
        status=ResponseStatus.SUCCESS
    )
