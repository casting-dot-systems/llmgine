"""
Integration tests for the MessageBus implementation.

This test suite covers:
- Complex event/command workflows
- Multi-session interactions
- Observability integration
- Real-world usage patterns
- End-to-end scenarios
"""

import asyncio
import pytest
import pytest_asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime, timedelta

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event, CommandStartedEvent, CommandResultEvent, EventHandlerFailedEvent
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.observability.handlers.base import ObservabilityEventHandler
from llmgine.llm import SessionID


@dataclass
class WorkflowCommand(Command):
    """Command that triggers a workflow."""
    __test__ = False
    task_id: str = field(default="task_1")
    steps: List[str] = field(default_factory=list)


@dataclass
class WorkflowEvent(Event):
    """Event representing a workflow step."""
    __test__ = False
    task_id: str = field(default="task_1")
    step: str = field(default="step_1")
    data: Any = field(default=None)


@dataclass
class NotificationEvent(Event):
    """Event for notifications."""
    __test__ = False
    message: str = field(default="")
    priority: str = field(default="normal")


class TestObservabilityHandler(ObservabilityEventHandler):
    """Test observability handler that records events."""
    
    def __init__(self):
        super().__init__()
        self.recorded_events: List[Event] = []
    
    async def handle(self, event: Event) -> None:
        """Record the event."""
        self.recorded_events.append(event)


class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.workflow_state: Dict[str, Any] = {}
        self.notifications: List[str] = []

    @pytest.mark.asyncio
    async def test_multi_step_workflow(self):
        """Test a complex multi-step workflow."""
        
        # Workflow command handler
        def workflow_handler(cmd: WorkflowCommand) -> CommandResult:
            self.workflow_state[cmd.task_id] = {
                'status': 'started',
                'steps': cmd.steps,
                'current_step': 0
            }
            return CommandResult(success=True, command_id=cmd.command_id)
        
        # Workflow event handler
        async def workflow_event_handler(event: WorkflowEvent) -> None:
            task_state = self.workflow_state.get(event.task_id)
            if task_state:
                task_state['current_step'] += 1
                task_state['status'] = f'completed_step_{event.step}'
                
                # Trigger next step if available
                if task_state['current_step'] < len(task_state['steps']):
                    next_step = task_state['steps'][task_state['current_step']]
                    next_event = WorkflowEvent(
                        task_id=event.task_id,
                        step=next_step,
                        data=f"data_for_{next_step}"
                    )
                    await self.bus.publish(next_event)
                else:
                    # Workflow complete
                    task_state['status'] = 'completed'
                    await self.bus.publish(NotificationEvent(
                        message=f"Workflow {event.task_id} completed"
                    ))
        
        # Notification handler
        def notification_handler(event: NotificationEvent) -> None:
            self.notifications.append(event.message)
        
        # Register handlers
        self.bus.register_command_handler(WorkflowCommand, workflow_handler)
        self.bus.register_event_handler(WorkflowEvent, workflow_event_handler)
        self.bus.register_event_handler(NotificationEvent, notification_handler)
        
        await self.bus.start()
        
        # Start workflow
        command = WorkflowCommand(
            task_id="complex_task",
            steps=["step_1", "step_2", "step_3"]
        )
        result = await self.bus.execute(command)
        assert result.success is True
        
        # Trigger first step
        first_event = WorkflowEvent(task_id="complex_task", step="step_1")
        await self.bus.publish(first_event)
        
        # Wait for workflow to complete
        await asyncio.sleep(0.5)
        
        # Check final state
        final_state = self.workflow_state["complex_task"]
        assert final_state['status'] == 'completed'
        assert final_state['current_step'] == 3
        assert len(self.notifications) == 1
        assert "Workflow complex_task completed" in self.notifications[0]
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """Test multiple concurrent workflows."""
        
        def workflow_handler(cmd: WorkflowCommand) -> CommandResult:
            self.workflow_state[cmd.task_id] = {
                'status': 'started',
                'session_id': cmd.session_id
            }
            return CommandResult(success=True, command_id=cmd.command_id)
        
        def workflow_event_handler(event: WorkflowEvent) -> None:
            task_state = self.workflow_state.get(event.task_id)
            if task_state:
                task_state['status'] = f'processed_{event.step}'
                task_state['data'] = event.data
        
        self.bus.register_command_handler(WorkflowCommand, workflow_handler)
        self.bus.register_event_handler(WorkflowEvent, workflow_event_handler)
        
        await self.bus.start()
        
        # Start multiple workflows concurrently
        tasks = []
        for i in range(5):
            task_id = f"task_{i}"
            session_id = f"session_{i}"
            
            async def run_workflow(tid, sid):
                cmd = WorkflowCommand(task_id=tid, session_id=SessionID(sid))
                await self.bus.execute(cmd)
                
                event = WorkflowEvent(
                    task_id=tid,
                    step=f"step_{tid}",
                    data=f"data_{tid}",
                    session_id=SessionID(sid)
                )
                await self.bus.publish(event)
            
            tasks.append(run_workflow(task_id, session_id))
        
        # Run all workflows concurrently
        await asyncio.gather(*tasks)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check all workflows completed
        assert len(self.workflow_state) == 5
        for i in range(5):
            task_id = f"task_{i}"
            assert task_id in self.workflow_state
            assert self.workflow_state[task_id]['status'] == f'processed_step_{task_id}'
        
        await self.bus.stop()


class TestObservabilityIntegration:
    """Test observability handler integration."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.observability_handler = TestObservabilityHandler()

    @pytest.mark.asyncio
    async def test_observability_records_all_events(self):
        """Test that observability handler records all events."""
        
        def test_command_handler(cmd: WorkflowCommand) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        def test_event_handler(event: WorkflowEvent) -> None:
            pass
        
        # Register handlers
        self.bus.register_command_handler(WorkflowCommand, test_command_handler)
        self.bus.register_event_handler(WorkflowEvent, test_event_handler)
        self.bus.register_observability_handler(self.observability_handler)
        
        await self.bus.start()
        
        # Execute command (should generate CommandStartedEvent and CommandResultEvent)
        command = WorkflowCommand(task_id="obs_test")
        await self.bus.execute(command)
        
        # Publish event
        event = WorkflowEvent(task_id="obs_test", step="obs_step")
        await self.bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check recorded events
        recorded_events = self.observability_handler.recorded_events
        assert len(recorded_events) >= 3  # CommandStarted, CommandResult, WorkflowEvent
        
        # Check for specific event types
        event_types = [type(e).__name__ for e in recorded_events]
        assert "CommandStartedEvent" in event_types
        assert "CommandResultEvent" in event_types
        assert "WorkflowEvent" in event_types
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_observability_handles_errors(self):
        """Test observability handler with error events."""
        
        def failing_event_handler(event: WorkflowEvent) -> None:
            raise RuntimeError("Handler failed")
        
        self.bus.register_event_handler(WorkflowEvent, failing_event_handler)
        self.bus.register_observability_handler(self.observability_handler)
        
        await self.bus.start()
        
        # Publish event that will cause handler to fail
        event = WorkflowEvent(task_id="error_test", step="error_step")
        await self.bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check for error event
        recorded_events = self.observability_handler.recorded_events
        event_types = [type(e).__name__ for e in recorded_events]
        assert "EventHandlerFailedEvent" in event_types
        
        # Find the error event
        error_event = next(e for e in recorded_events if isinstance(e, EventHandlerFailedEvent))
        assert error_event.event is not None
        assert error_event.exception is not None
        assert "Handler failed" in str(error_event.exception)
        
        await self.bus.stop()


class TestMultiSessionInteractions:
    """Test interactions between multiple sessions."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.session_data: Dict[str, List[str]] = {}

    @pytest.mark.asyncio
    async def test_session_isolation(self):
        """Test that sessions are properly isolated."""
        
        def session_command_handler(cmd: WorkflowCommand) -> CommandResult:
            session_id = str(cmd.session_id)
            if session_id not in self.session_data:
                self.session_data[session_id] = []
            self.session_data[session_id].append(f"cmd_{cmd.task_id}")
            return CommandResult(success=True, command_id=cmd.command_id)
        
        def session_event_handler(event: WorkflowEvent) -> None:
            session_id = str(event.session_id)
            if session_id not in self.session_data:
                self.session_data[session_id] = []
            self.session_data[session_id].append(f"evt_{event.step}")
        
        await self.bus.start()
        
        # Create multiple sessions
        async with self.bus.create_session("session_1") as session1:
            session1.register_command_handler(WorkflowCommand, session_command_handler)
            session1.register_event_handler(WorkflowEvent, session_event_handler)
            
            async with self.bus.create_session("session_2") as session2:
                session2.register_command_handler(WorkflowCommand, session_command_handler)
                session2.register_event_handler(WorkflowEvent, session_event_handler)
                
                # Execute commands in each session
                cmd1 = WorkflowCommand(task_id="task1")
                result1 = await session1.execute_with_session(cmd1)
                assert result1.success is True
                
                cmd2 = WorkflowCommand(task_id="task2")
                result2 = await session2.execute_with_session(cmd2)
                assert result2.success is True
                
                # Publish events to each session
                event1 = WorkflowEvent(step="step1", session_id=SessionID("session_1"))
                await self.bus.publish(event1)
                
                event2 = WorkflowEvent(step="step2", session_id=SessionID("session_2"))
                await self.bus.publish(event2)
                
                # Wait for processing
                await asyncio.sleep(0.1)
        
        # Check session isolation
        assert "session_1" in self.session_data
        assert "session_2" in self.session_data
        
        session1_data = self.session_data["session_1"]
        session2_data = self.session_data["session_2"]
        
        assert "cmd_task1" in session1_data
        assert "evt_step1" in session1_data
        assert "cmd_task2" not in session1_data
        assert "evt_step2" not in session1_data
        
        assert "cmd_task2" in session2_data
        assert "evt_step2" in session2_data
        assert "cmd_task1" not in session2_data
        assert "evt_step1" not in session2_data
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_global_handlers_receive_all_events(self):
        """Test that GLOBAL handlers receive events from all sessions."""
        
        global_events = []
        
        def global_handler(event: WorkflowEvent) -> None:
            global_events.append(f"global_{event.step}_{event.session_id}")
        
        def session_handler(event: WorkflowEvent) -> None:
            global_events.append(f"session_{event.step}_{event.session_id}")
        
        # Register global handler
        self.bus.register_event_handler(WorkflowEvent, global_handler, "GLOBAL")
        
        await self.bus.start()
        
        # Create sessions with their own handlers
        async with self.bus.create_session("session_1") as session1:
            session1.register_event_handler(WorkflowEvent, session_handler)
            
            async with self.bus.create_session("session_2") as session2:
                session2.register_event_handler(WorkflowEvent, session_handler)
                
                # Publish events from different sessions
                event1 = WorkflowEvent(step="step1", session_id=SessionID("session_1"))
                await self.bus.publish(event1)
                
                event2 = WorkflowEvent(step="step2", session_id=SessionID("session_2"))
                await self.bus.publish(event2)
                
                # Wait for processing
                await asyncio.sleep(0.1)
        
        # Global handler should receive all events
        global_event_strs = [e for e in global_events if e.startswith("global_")]
        assert len(global_event_strs) == 2
        assert "global_step1_session_1" in global_event_strs
        assert "global_step2_session_2" in global_event_strs
        
        # Session handlers should only receive their own events
        session_event_strs = [e for e in global_events if e.startswith("session_")]
        assert len(session_event_strs) == 2
        assert "session_step1_session_1" in session_event_strs
        assert "session_step2_session_2" in session_event_strs
        
        await self.bus.stop()


class TestScheduledEventIntegration:
    """Test scheduled event integration."""

    def setup_method(self):
        """Setup for each test method."""
        self.bus = MessageBus()
        asyncio.run(self.bus.reset())
        self.processed_events: List[str] = []

    @pytest.mark.asyncio
    async def test_scheduled_event_ordering(self):
        """Test that scheduled events are processed in correct order."""
        
        def scheduled_handler(event: ScheduledEvent) -> None:
            if hasattr(event, 'data'):
                self.processed_events.append(event.data)
        
        self.bus.register_event_handler(ScheduledEvent, scheduled_handler)
        await self.bus.start()
        
        # Schedule events with different times
        base_time = datetime.now()
        
        # Schedule in reverse order
        event3 = ScheduledEvent(scheduled_time=base_time + timedelta(milliseconds=300))
        event3.data = "event3"
        
        event1 = ScheduledEvent(scheduled_time=base_time + timedelta(milliseconds=100))
        event1.data = "event1"
        
        event2 = ScheduledEvent(scheduled_time=base_time + timedelta(milliseconds=200))
        event2.data = "event2"
        
        # Publish in random order
        await self.bus.publish(event2)
        await self.bus.publish(event3)
        await self.bus.publish(event1)
        
        # Wait for all events to be processed
        await asyncio.sleep(0.5)
        
        # Events should be processed in chronological order
        assert len(self.processed_events) == 3
        assert self.processed_events[0] == "event1"
        assert self.processed_events[1] == "event2"
        assert self.processed_events[2] == "event3"
        
        await self.bus.stop()

    @pytest.mark.asyncio
    async def test_mixed_regular_and_scheduled_events(self):
        """Test mixing regular and scheduled events."""
        
        def regular_handler(event: WorkflowEvent) -> None:
            self.processed_events.append(f"regular_{event.step}")
        
        def scheduled_handler(event: ScheduledEvent) -> None:
            if hasattr(event, 'data'):
                self.processed_events.append(f"scheduled_{event.data}")
        
        self.bus.register_event_handler(WorkflowEvent, regular_handler)
        self.bus.register_event_handler(ScheduledEvent, scheduled_handler)
        await self.bus.start()
        
        # Publish regular event
        regular_event = WorkflowEvent(step="immediate")
        await self.bus.publish(regular_event)
        
        # Schedule event for later
        scheduled_event = ScheduledEvent(
            scheduled_time=datetime.now() + timedelta(milliseconds=100)
        )
        scheduled_event.data = "delayed"
        await self.bus.publish(scheduled_event)
        
        # Publish another regular event
        regular_event2 = WorkflowEvent(step="immediate2")
        await self.bus.publish(regular_event2)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Regular events should be processed immediately
        # Scheduled event should be processed after delay
        assert len(self.processed_events) == 3
        assert "regular_immediate" in self.processed_events
        assert "regular_immediate2" in self.processed_events
        assert "scheduled_delayed" in self.processed_events
        
        # Regular events should come first
        first_two = self.processed_events[:2]
        assert "regular_immediate" in first_two
        assert "regular_immediate2" in first_two
        assert self.processed_events[2] == "scheduled_delayed"
        
        await self.bus.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])