import asyncio
from datetime import datetime, timedelta
import pytest
from llmgine.bus.bus import MessageBus
from llmgine.messages.approvals import ApprovalAcceptedEvent, ApprovalCommand, ApprovalDeniedEvent, ApprovalExpiredEvent, ApprovalResult, ApprovalStatus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

async def approval_command_handler(command: Command) -> CommandResult:
    if isinstance(command, ApprovalCommand):
        print(f"Approval command received: {command}")
        num = await asyncio.to_thread(input, "Press 1 to accept, 0 to deny:")
        if num == "1":
            return ApprovalResult(success=True, approval_status=ApprovalStatus.APPROVED)
        else:
            return ApprovalResult(success=True, approval_status=ApprovalStatus.DENIED)
    else:
        return CommandResult(success=False, error="Invalid command type")  

async def approval_command_accept_callback(event: Event) -> None:
    print(f"✅ APPROVAL ACCEPTED CALLBACK CALLED: {event}")
    await asyncio.sleep(1)
    print("✅ Approval command accepted callback done")

async def approval_command_deny_callback(event: Event) -> None:
    print(f"❌ APPROVAL DENIED CALLBACK CALLED: {event}")
    await asyncio.sleep(1)
    print("❌ Approval command denied callback done")

async def approval_command_expired_callback(event: Event) -> None:
    print(f"Approval command expired: {event}")
    await asyncio.sleep(1)
        
    # Replace the expired command with a new one - but don't wait for it
    bus = MessageBus()
    replacement_command = ApprovalCommand(
        approver="test_approver", 
        expires_at=datetime.now() + timedelta(seconds=3), 
        on_approval_callback=ApprovalAcceptedEvent(), 
        on_denial_callback=ApprovalDeniedEvent(),
        on_expiry_callback=ApprovalExpiredEvent()
    )

    # Use create_task to avoid stacking function calls
    await bus.execute(replacement_command)
    print("Replacement command submitted (non-blocking)")
    print("Approval command expired callback done")

@pytest.mark.asyncio
async def test_approval_command_automated():
    """Test approval command with automated responses."""
    bus = MessageBus()
    await bus.start()
    
    # Handler that automatically approves
    async def auto_approve_handler(command: Command) -> CommandResult:
        if isinstance(command, ApprovalCommand):
            await asyncio.sleep(0.1)  # Simulate processing
            return ApprovalResult(success=True, approval_status=ApprovalStatus.APPROVED)
        return CommandResult(success=False, error="Invalid command type")
    
    # Track callback execution
    callback_executed = {"accepted": False, "denied": False, "expired": False}
    
    async def on_accepted(event: Event) -> None:
        callback_executed["accepted"] = True
    
    async def on_denied(event: Event) -> None:
        callback_executed["denied"] = True
        
    async def on_expired(event: Event) -> None:
        callback_executed["expired"] = True
    
    bus.register_command_handler(ApprovalCommand, auto_approve_handler)
    bus.register_event_handler(ApprovalAcceptedEvent, on_accepted)
    bus.register_event_handler(ApprovalDeniedEvent, on_denied)
    bus.register_event_handler(ApprovalExpiredEvent, on_expired)
    
    # Create and execute approval command
    approval_cmd = ApprovalCommand(
        approver="test_approver",
        expires_at=datetime.now() + timedelta(seconds=5),
        on_approval_callback=ApprovalAcceptedEvent(),
        on_denial_callback=ApprovalDeniedEvent(),
        on_expiry_callback=ApprovalExpiredEvent()
    )
    
    result = await bus.execute(approval_cmd)
    assert result.success is True
    assert isinstance(result, ApprovalResult)
    assert result.approval_status == ApprovalStatus.APPROVED
    
    # Give time for events to process
    await asyncio.sleep(0.2)
    
    # Check that accepted callback was executed
    assert callback_executed["accepted"] is True
    assert callback_executed["denied"] is False
    assert callback_executed["expired"] is False
    
    await bus.stop()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test requires interactive input")
async def test_approval_command():
    bus = MessageBus()
    await bus.start()

    bus.register_command_handler(ApprovalCommand, approval_command_handler)
    bus.register_event_handler(ApprovalAcceptedEvent, approval_command_accept_callback)
    bus.register_event_handler(ApprovalDeniedEvent, approval_command_deny_callback)
    bus.register_event_handler(ApprovalExpiredEvent, approval_command_expired_callback)

    command = ApprovalCommand(approver="test_approver", 
                              expires_at=datetime.now() + timedelta(seconds=3), 
                              on_approval_callback=ApprovalAcceptedEvent(), 
                              on_denial_callback=ApprovalDeniedEvent(),
                              on_expiry_callback=ApprovalExpiredEvent())

    await bus.execute(command)


# Alternative: Command queue approach
command_queue: asyncio.Queue[Command] = asyncio.Queue()

async def process_command_queue():
    """Process commands from the queue one at a time."""
    while True:
        try:
            command: Command = await command_queue.get()
            bus = MessageBus()
            await bus.execute(command)
            command_queue.task_done()
        except Exception as e:
            print(f"Error processing command: {e}")

async def approval_command_expired_callback_with_queue(event: Event) -> None:
    """Alternative callback that uses a queue to prevent stacking."""
    print(f"Approval command expired: {event}")
    
    replacement_command = ApprovalCommand(
        approver="test_approver", 
        expires_at=datetime.now() + timedelta(seconds=3), 
        on_approval_callback=ApprovalAcceptedEvent(), 
        on_denial_callback=ApprovalDeniedEvent(),
        on_expiry_callback=ApprovalExpiredEvent()
    )
    
    # Add to queue instead of executing directly
    await command_queue.put(replacement_command)
    print("Replacement command added to queue")

if __name__ == "__main__":
    asyncio.run(test_approval_command())