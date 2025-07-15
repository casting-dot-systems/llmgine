"""Approval system for the message bus.

This module defines approval commands and events that allows for
asynchronous approval workflows where commands can be approved or denied
before execution.
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Awaitable, Callable, Optional

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Use this enum for navigating the approval workflow
class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

class ApprovalCommand(Command):
    """Command to request approval for an action.
    
    This command should be handled by an approval handler that will:
    1. Create an approval request
    2. Send it to the specified approval location (e.g. email, slack, etc.)
    3. Wait for approval result
    4. Execute the callback command based on approval result
    """
    
    approver: Optional[str] = None
    expires_at: Optional[datetime] = None
    on_approval_callback: Optional[Event] = None
    on_denial_callback: Optional[Event] = None
    on_expiry_callback: Optional[Event] = None

    def is_expired(self) -> bool:
        """Check if the approval request has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class ApprovalResult(CommandResult):
    """Result of an approval command execution."""
    
    approval_status: ApprovalStatus = ApprovalStatus.PENDING

class ApprovalRequestEvent(Event):
    """Event emitted when an approval request is created."""
    
    approval_command: Optional[ApprovalCommand] = None

class ApprovalAcceptedEvent(Event):
    """Event emitted when an approval request receives a response."""
    pass

class ApprovalDeniedEvent(Event):
    """Event emitted when an approval request receives a response."""
    pass

class ApprovalExpiredEvent(Event):
    """Event emitted when an approval request expires."""
    pass

async def execute_approval_command(
    command: ApprovalCommand, 
    handler: Callable[[Command], Awaitable[CommandResult]],
) -> ApprovalResult:
    """Execute an approval command and return the result.
    
    This function continuously checks for approval while monitoring expiry.
    It will return an EXPIRED result if the command expires before approval.
    
    Args:
        command: The approval command to execute
        handler: Async handler that processes the approval command
    
    Returns:
        ApprovalResult with the final status
    """
    from llmgine.bus import MessageBus
    
    # Start the approval process
    approval_task = asyncio.create_task(handler(command)) # type: ignore
    bus = MessageBus()

    try:
        # Wait for either approval or expiry
        while not command.is_expired():
            print("Waiting for approval...")
            # Check if approval task is done
            if approval_task.done():
                print("Approval task done")
                result = approval_task.result() # type: ignore
                # Ensure result is an ApprovalResult
                if isinstance(result, ApprovalResult):
                    # Handle callbacks based on approval status
                    if result.approval_status == ApprovalStatus.APPROVED and command.on_approval_callback:
                        await bus.publish(command.on_approval_callback)
                    elif result.approval_status == ApprovalStatus.DENIED and command.on_denial_callback:
                        await bus.publish(command.on_denial_callback)
                    
                    return result

            # Wait before checking again
            await asyncio.sleep(1)
        
        # Command expired, cancel the approval task
        approval_task.cancel()
        print("Approval task cancelled")
        
        # Handle expiry callback - but don't wait for it to complete
        if command.on_expiry_callback:
            print("Publishing expiry callback")
            # Use create_task to avoid blocking and stacking
            await asyncio.create_task(bus.publish(command.on_expiry_callback))
            print("Expiry callback published")

        print("Returning expired result")
        # Return expired result immediately
        return ApprovalResult(
            success=False,
            command_id=command.command_id,
            approval_status=ApprovalStatus.EXPIRED,
            error="Approval request expired"
        )
        
    except asyncio.CancelledError:
        # Task was cancelled
        return ApprovalResult(
            success=False,
            command_id=command.command_id,
            approval_status=ApprovalStatus.EXPIRED,
            error="Approval request was cancelled"
        )
    except Exception as e:
        # Handle any other exceptions
        return ApprovalResult(
            success=False,
            command_id=command.command_id,
            approval_status=ApprovalStatus.DENIED,
            error=f"Approval request failed: {str(e)}"
        )