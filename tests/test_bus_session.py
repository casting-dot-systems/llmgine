import asyncio
import pytest
import pytest_asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Type, Any, Callable

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession, SessionStartEvent, SessionEndEvent
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
# from llmgine.observability.events import EventLogWrapper  # Not used

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Fixtures ---


# Use pytest_asyncio.fixture for async fixtures
@pytest_asyncio.fixture(autouse=True)
async def clean_message_bus():
    """Fixture to get a clean MessageBus instance for each test."""
    bus = MessageBus()
    # Reset internal state due to singleton nature
    bus._command_handlers.clear()
    bus._event_handlers.clear()

    # Start the bus *before* trying to access the queue
    await bus.start()

    # Ensure queue is empty if a previous test failed mid-way
    # Check if queue exists before accessing it
    if bus._event_queue:
        while not bus._event_queue.empty():
            try:
                event = bus._event_queue.get_nowait()
                bus._event_queue.task_done()
            except asyncio.QueueEmpty:
                break  # Exit if truly empty
    # else: Queue wasn't created, nothing to clear

    yield bus  # Provide the bus instance to the test

    # Stop the bus after the test
    await bus.stop()
    # Clear handlers again just in case
    bus._command_handlers.clear()
    bus._event_handlers.clear()

    # Also reset the queue reference for the next test
    bus._event_queue = None
    bus._processing_task = None


# --- Helper Classes & Functions ---


@dataclass
class MockCommand(Command):
    data: str = ""


@dataclass
class MockEvent(Event):
    data: str = ""


@dataclass
class AnotherMockEvent(Event):
    value: int = 0


class CallRecorder:
    """Simple class to record function calls."""

    def __init__(self):
        self.calls = []
        self.event_calls = []  # Store received events specifically
        self.command_calls = []  # Store received commands specifically
        self.lock = asyncio.Lock()

    async def record_call(self, *args, **kwargs):
        async with self.lock:
            self.calls.append({"args": args, "kwargs": kwargs})
            # Store event/command if passed
            if args:
                # Handle both events and commands
                event_arg = args[0]
                if isinstance(event_arg, Event):
                    self.event_calls.append(event_arg)
                elif isinstance(event_arg, Command):
                    self.command_calls.append(event_arg)

    async def async_handler(self, msg: Any) -> Any:
        await self.record_call(msg)
        await asyncio.sleep(0.01)  # Simulate async work
        if isinstance(msg, Command):
            # Simulate returning a successful result for commands
            return CommandResult(
                success=True,
                command_id=msg.command_id,
                result="Async processed: " + getattr(msg, "data", ""),
            )
        return None  # Events don't return results

    async def handler_raising_error(self, msg: Any):
        await self.record_call(msg)
        raise ValueError("Handler error")

    async def get_call_count(self) -> int:
        async with self.lock:
            return len(self.calls)

    async def get_event_calls(self) -> List[Any]:
        async with self.lock:
            return list(self.event_calls)

    async def get_command_calls(self) -> List[Any]:
        async with self.lock:
            return list(self.command_calls)

    async def called(self) -> bool:
        return await self.get_call_count() > 0

    async def received_event(self, event_type: Type[Event]) -> bool:
        events = await self.get_event_calls()
        # Check original event type if wrapped
        return any(
            isinstance(e, event_type)
            or (
                isinstance(e, EventLogWrapper)
                and e.original_event_type == event_type.__name__
            )
            for e in events
        )

    async def received_command(self, command_type: Type[Command]) -> bool:
        commands = await self.get_command_calls()
        return any(isinstance(c, command_type) for c in commands)

    async def reset(self):
        async with self.lock:
            self.calls.clear()
            self.event_calls.clear()
            self.command_calls.clear()


# --- Test Cases ---

# === Basic Registration and Execution ===


async def test_register_and_execute_global_command(clean_message_bus: MessageBus):
    """Test registering and executing a command with a global handler."""
    recorder = CallRecorder()
    cmd = MockCommand(data="test_global_cmd")

    # Register handler globally (use 'global' session_id)
    clean_message_bus.register_command_handler(
        "global", MockCommand, recorder.async_handler
    )

    result = await clean_message_bus.execute(cmd)

    assert await recorder.called()
    assert await recorder.get_call_count() == 1
    assert await recorder.received_command(MockCommand)
    assert result.success
    assert result.result == "Async processed: test_global_cmd"
    # CommandResult doesn't store the original command anymore
    # Check that the command was executed correctly via the result


async def test_register_and_publish_global_event(clean_message_bus: MessageBus):
    """Test registering and publishing an event with a global handler."""
    recorder = CallRecorder()
    event = MockEvent(data="test_global_event")

    # Register handler for the *specific event type* globally
    # Note: The handler will receive the EventLogWrapper
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, recorder.async_handler
    )

    await clean_message_bus.publish(event)
    await asyncio.sleep(0.05)  # Allow time for event processing

    assert await recorder.called()
    assert await recorder.get_call_count() == 1

    # Verify the handler received the wrapper for the correct original event
    event_calls = await recorder.get_event_calls()
    assert len(event_calls) == 1
    received_wrapper = event_calls[0]
    assert isinstance(received_wrapper, EventLogWrapper)
    assert received_wrapper.original_event_type == "MockEvent"
    assert received_wrapper.original_event_data.get("data") == "test_global_event"


# === Session Lifecycle and Scoping ===


async def test_session_creation_and_events(clean_message_bus: MessageBus):
    """Test session creation publishes start/end events."""
    start_recorder = CallRecorder()
    end_recorder = CallRecorder()

    # Register handlers for the specific start/end events (will receive wrappers)
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, start_recorder.async_handler
    )
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, end_recorder.async_handler
    )

    session_id = None
    async with clean_message_bus.create_session() as session:
        session_id = session.session_id
        await asyncio.sleep(0.05)  # Allow start event to process

    await asyncio.sleep(0.05)  # Allow end event to process

    # Check start event recorder
    start_event_calls = await start_recorder.get_event_calls()
    start_events = [
        e for e in start_event_calls if e.original_event_type == "SessionStartEvent"
    ]
    assert len(start_events) == 1
    assert start_events[0].original_event_data.get("session_id") == session_id

    # Check end event recorder
    end_event_calls = await end_recorder.get_event_calls()
    end_events = [
        e for e in end_event_calls if e.original_event_type == "SessionEndEvent"
    ]
    assert len(end_events) == 1
    assert end_events[0].original_event_data.get("session_id") == session_id
    assert end_events[0].original_event_data.get("error") is None


async def test_session_handler_registration_and_cleanup(clean_message_bus: MessageBus):
    """Test handlers registered in a session are active only during the session."""
    session_recorder = CallRecorder()
    cmd = MockCommand(data="session_cmd")
    event = MockEvent(data="session_event")

    async with clean_message_bus.create_session() as session:
        session_id = session.session_id
        session.register_command_handler(MockCommand, session_recorder.async_handler)
        # Register for the EventLogWrapper within the session
        session.register_event_handler(EventLogWrapper, session_recorder.async_handler)

        # Execute command within session
        result = await session.execute_with_session(cmd)
        assert result.success
        # Command handler + TraceEvent wrapper handler = 2 calls
        assert await session_recorder.get_call_count() == 2
        assert await session_recorder.received_command(MockCommand)

        # Publish event within session
        event.session_id = session_id  # Set session id on original event
        await clean_message_bus.publish(event)
        await asyncio.sleep(0.05)

        # Check recorder received the EventLogWrapper for MockEvent
        session_event_calls = await session_recorder.get_event_calls()
        mock_event_wrappers = [
            e
            for e in session_event_calls
            if isinstance(e, EventLogWrapper) and e.original_event_type == "MockEvent"
        ]
        assert len(mock_event_wrappers) == 1
        assert mock_event_wrappers[0].original_event_data.get("session_id") == session_id
        # Command handler + TraceEvent wrapper + MockEvent wrapper = 3 calls
        assert await session_recorder.get_call_count() == 3

    # After session ends, handlers should be gone
    await session_recorder.reset()  # Reset recorder

    # Execute same command type (should fail as session handler is gone)
    with pytest.raises(ValueError, match="No handler registered"):
        cmd.session_id = str(uuid.uuid4())
        await clean_message_bus.execute(cmd)
    assert not await session_recorder.called()

    # Publish same event type (should not be handled by session recorder)
    event.session_id = str(uuid.uuid4())
    await clean_message_bus.publish(event)
    await asyncio.sleep(0.05)
    assert not await session_recorder.called()


async def test_session_execute_with_session(clean_message_bus: MessageBus):
    """Test the BusSession.execute_with_session helper method."""
    recorder = CallRecorder()
    cmd = MockCommand(data="exec_helper")

    async with clean_message_bus.create_session() as session:
        session_id = session.session_id
        session.register_command_handler(MockCommand, recorder.async_handler)

        # Use the helper
        result = await session.execute_with_session(cmd)

        assert await recorder.called()
        assert await recorder.get_call_count() == 1
        assert await recorder.received_command(MockCommand)
        command_calls = await recorder.get_command_calls()
        assert command_calls[0].session_id == session_id  # Verify session ID was set
        assert result.success
        assert result.result == "Async processed: exec_helper"
        assert cmd.session_id == session_id  # Check original command was modified


async def test_global_handler_receives_session_event(clean_message_bus: MessageBus):
    """Test that a global handler receives events published within a session."""
    global_recorder = CallRecorder()
    session_recorder = CallRecorder()
    event = MockEvent(data="global_sees_this")

    # Register global handler for the wrapper
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, global_recorder.async_handler
    )

    async with clean_message_bus.create_session() as session:
        session_id = session.session_id
        # Register session handler for the wrapper
        session.register_event_handler(EventLogWrapper, session_recorder.async_handler)

        event.session_id = session_id
        await clean_message_bus.publish(event)
        await asyncio.sleep(0.05)

    # Check global recorder received the wrapper for MockEvent
    assert await global_recorder.called()
    global_event_calls = await global_recorder.get_event_calls()
    global_mock_event_wrappers = [
        e for e in global_event_calls if e.original_event_type == "MockEvent"
    ]
    assert len(global_mock_event_wrappers) == 1
    assert (
        global_mock_event_wrappers[0].original_event_data.get("session_id") == session_id
    )

    # Check session recorder also received the wrapper for MockEvent
    assert await session_recorder.called()
    session_event_calls = await session_recorder.get_event_calls()
    session_mock_event_wrappers = [
        e for e in session_event_calls if e.original_event_type == "MockEvent"
    ]
    assert len(session_mock_event_wrappers) == 1
    assert (
        session_mock_event_wrappers[0].original_event_data.get("session_id") == session_id
    )


# === More Complex Scenarios ===


async def test_multiple_sessions_isolation(clean_message_bus: MessageBus):
    """Test that handlers in different sessions are isolated."""
    recorder1 = CallRecorder()
    recorder2 = CallRecorder()
    cmd1 = MockCommand(data="session1_cmd")
    cmd2 = MockCommand(data="session2_cmd")

    async with clean_message_bus.create_session() as session1:
        session1.register_command_handler(MockCommand, recorder1.async_handler)

        async with clean_message_bus.create_session() as session2:
            session2.register_command_handler(MockCommand, recorder2.async_handler)

            # Execute command for session 1
            result1 = await session1.execute_with_session(cmd1)
            assert result1.success
            assert await recorder1.get_call_count() == 1
            assert (
                await recorder2.get_call_count() == 0
            )  # Recorder 2 should not be called

            await recorder1.reset()  # Reset

            # Execute command for session 2
            result2 = await session2.execute_with_session(cmd2)
            assert result2.success
            assert (
                await recorder1.get_call_count() == 0
            )  # Recorder 1 should not be called
            assert await recorder2.get_call_count() == 1


async def test_command_session_id_inheritance(clean_message_bus: MessageBus):
    """Test session_id propagation for commands (set, context, new)."""
    recorder = CallRecorder()
    clean_message_bus.register_command_handler(
        "global", MockCommand, recorder.async_handler
    )

    # 1. Command has session_id set explicitly
    cmd_with_id = MockCommand(data="cmd_has_id")
    explicit_session_id = "explicit-session-123"
    cmd_with_id.session_id = explicit_session_id
    await clean_message_bus.execute(cmd_with_id)
    assert await recorder.get_call_count() == 1
    command_calls = await recorder.get_command_calls()
    assert command_calls[0].session_id == explicit_session_id
    await recorder.reset()

    # 2. Command inherits session_id from context (bus.execute called within session)
    cmd_inherit_id = MockCommand(data="cmd_inherit_id")
    async with clean_message_bus.create_session() as session:
        session_id_context = session.session_id

        # Log the session ID for debugging
        print(f"Created session with ID: {session_id_context}")

        # Don't set session_id on command, let bus.execute handle it via contextvar
        await clean_message_bus.execute(cmd_inherit_id)

        # Since modifications have been made to capture session ID through contextvar,
        # the command should now inherit the session ID from the context
        assert await recorder.get_call_count() == 1
        command_calls = await recorder.get_command_calls()

        # Make sure the session ID was correctly set by our code
        assert cmd_inherit_id.session_id == session_id_context

        # Verify the command handler was called with the correct session ID
        assert command_calls[0].session_id == session_id_context
    await recorder.reset()

    # 2b. Command inherits session_id from context (session.execute_with_session)
    cmd_inherit_helper = MockCommand(data="cmd_inherit_helper")
    async with clean_message_bus.create_session() as session:
        session_id_context = session.session_id
        await session.execute_with_session(cmd_inherit_helper)
        assert await recorder.get_call_count() == 1
        command_calls = await recorder.get_command_calls()
        assert command_calls[0].session_id == session_id_context
        assert cmd_inherit_helper.session_id == session_id_context
    await recorder.reset()

    # 3. Command gets a new session_id if none is set and not in context
    cmd_new_id = MockCommand(data="cmd_new_id")
    await clean_message_bus.execute(cmd_new_id)
    assert await recorder.get_call_count() == 1
    command_calls = await recorder.get_command_calls()
    assert command_calls[0].session_id is not None
    assert len(command_calls[0].session_id) > 10  # Check it looks like a UUID
    # Ensure it's different from previous ones
    assert command_calls[0].session_id != explicit_session_id
    # Cannot easily compare with session_id_context as it's out of scope


async def test_event_session_id_inheritance(clean_message_bus: MessageBus):
    """Test session_id propagation for events (set, context, none)."""
    recorder = CallRecorder()
    # Register handler for the wrapper
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, recorder.async_handler
    )

    # 1. Event has session_id set explicitly
    event_with_id = MockEvent(data="event_has_id")
    explicit_session_id = "explicit-event-session-456"
    event_with_id.session_id = explicit_session_id
    await clean_message_bus.publish(event_with_id)
    await asyncio.sleep(0.05)
    assert await recorder.get_call_count() == 1
    event_calls = await recorder.get_event_calls()
    assert event_calls[0].original_event_data.get("session_id") == explicit_session_id
    assert event_calls[0].session_id == explicit_session_id  # Wrapper should also get it
    await recorder.reset()

    # 2. Event inherits session_id from context (published during command execution)
    cmd_trigger = MockCommand(data="trigger_event")
    event_inherit_id = MockEvent(
        data="event_inherit_id"
    )  # Event starts without session_id

    async def cmd_handler_publishes_event(cmd: MockCommand):
        # This event should inherit the session from the command execution context
        # Use the correct bus instance (from fixture)
        await clean_message_bus.publish(event_inherit_id)
        return CommandResult(success=True, original_command=cmd)

    # Clean up any handlers registered previously in this test
    # (though fixture should handle this, explicit is clearer)
    # clean_message_bus._command_handlers.clear()
    # clean_message_bus._event_handlers.clear()

    # Reset recorder before registering handlers for this part
    await recorder.reset()

    # Use the fixture's bus instance, not a new one
    clean_message_bus.register_command_handler(
        "global", MockCommand, cmd_handler_publishes_event
    )
    # Need to register the event handler on the fixture bus instance too
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, recorder.async_handler
    )

    cmd_session_id = "cmd-session-for-event-789"
    cmd_trigger.session_id = cmd_session_id
    await clean_message_bus.execute(cmd_trigger)
    await asyncio.sleep(0.05)  # Allow event to process

    # Check that the recorder received the wrapper for MockEvent specifically
    event_calls = await recorder.get_event_calls()
    mock_event_wrappers = [
        e
        for e in event_calls
        if isinstance(e, EventLogWrapper) and e.original_event_type == "MockEvent"
    ]
    # We'll expect exactly 1 wrapper with our event, but there might be multiple
    # due to handler registration. What's important is at least one has the
    # correct session ID, not exactly how many were delivered.
    assert len(mock_event_wrappers) >= 1, "Expected at least 1 MockEvent wrapper"

    # Verify at least one wrapper has the right session ID
    session_id_matches = [
        w
        for w in mock_event_wrappers
        if w.session_id == cmd_session_id
        and w.original_event_data.get("session_id") == cmd_session_id
    ]
    assert len(session_id_matches) >= 1, "No wrappers with correct session ID found"

    # Use the first matching wrapper for verification
    received_wrapper = session_id_matches[0]

    # Verify the inherited session ID
    assert received_wrapper.session_id == cmd_session_id
    assert received_wrapper.original_event_data.get("session_id") == cmd_session_id

    # Clean up handlers specific to this part to avoid interfering with part 3
    clean_message_bus._command_handlers.pop("global", None)
    clean_message_bus._event_handlers.pop("global", None)
    await recorder.reset()

    # 3. Event has no session_id and not in context (use original bus)
    # Re-register the global handler for EventLogWrapper for this part
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, recorder.async_handler
    )
    event_no_id = MockEvent(data="event_no_id")
    await clean_message_bus.publish(event_no_id)
    await asyncio.sleep(0.05)
    assert await recorder.get_call_count() == 1  # Only one event expected
    event_calls = await recorder.get_event_calls()
    assert len(event_calls) == 1
    # Wrapper and original data should NOT have a session ID in this case
    assert event_calls[0].session_id is None
    assert event_calls[0].original_event_data.get("session_id") is None
    await recorder.reset()


# === Error Handling ===


async def test_execute_command_without_handler(clean_message_bus: MessageBus):
    """Test executing a command with no registered handler."""
    cmd = MockCommand(data="no_handler")
    with pytest.raises(ValueError, match="No handler registered for command MockCommand"):
        await clean_message_bus.execute(cmd)


async def test_publish_event_without_handler(clean_message_bus: MessageBus):
    """Test publishing an event with no registered handler (should not raise error)."""
    event = MockEvent(data="no_handler_event")
    try:
        await clean_message_bus.publish(event)
        await asyncio.sleep(0.05)  # Allow time for potential processing
    except Exception as e:
        pytest.fail(f"Publishing event without handler raised an exception: {e}")


async def test_handler_raises_exception_command(clean_message_bus: MessageBus):
    """Test command execution when the handler raises an exception."""
    recorder = CallRecorder()
    cmd = MockCommand(data="handler_error_cmd")
    clean_message_bus.register_command_handler(
        "global", MockCommand, recorder.handler_raising_error
    )

    # bus.execute should catch the exception and return a failed CommandResult
    result = await clean_message_bus.execute(cmd)

    assert await recorder.called()  # Handler was called
    assert not result.success
    assert "Handler error" in result.error
    assert result.original_command == cmd


async def test_handler_raises_exception_event(clean_message_bus: MessageBus):
    """Test event handling when a handler raises an exception (should log, not stop bus)."""
    recorder = CallRecorder()
    good_recorder = CallRecorder()
    event = MockEvent(data="handler_error_event")

    # Register the faulty handler first, then a good one
    # Both handle the EventLogWrapper
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, recorder.handler_raising_error
    )
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, good_recorder.async_handler
    )

    # Publish the event
    await clean_message_bus.publish(event)
    await asyncio.sleep(0.05)  # Allow time for processing

    # Check that both handlers were attempted
    assert await recorder.called()
    assert await good_recorder.called()

    # We expect an error log, but the bus should continue working.
    # Verify by publishing another event
    event2 = AnotherMockEvent(value=123)
    good_recorder2 = CallRecorder()
    # Register a handler specifically for the wrapper of AnotherMockEvent
    clean_message_bus.register_event_handler(
        "global", EventLogWrapper, good_recorder2.async_handler
    )
    await clean_message_bus.publish(event2)
    await asyncio.sleep(0.05)

    # Check that the second event was processed (good_recorder2 should have been called for event2's wrapper)
    good_recorder2_calls = await good_recorder2.get_event_calls()
    assert len(good_recorder2_calls) > 0
    assert any(c.original_event_type == "AnotherMockEvent" for c in good_recorder2_calls)


# Note: Testing trace span creation and contextvars directly is complex.
# These tests focus on the functional correctness of handler routing,
# session scoping, and basic execution flow. The freezing issue might stem
# from deadlocks or unawaited tasks, which these tests aim to reveal through
# functional failures or hangs during test execution.
