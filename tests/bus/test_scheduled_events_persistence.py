"""Integration tests for scheduled event persistence with MessageBus.

This module tests the integration between the message bus and the SQLAlchemy
database persistence layer, focusing on:
- Scheduled event restoration across bus restarts
- Best-effort persistence that doesn't break bus operation
- Integration with existing bus functionality
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from llmgine.bus.bus import MessageBus
from llmgine.database.database import reset_engine, drop_all
from llmgine.messages.events import Event
from llmgine.messages.scheduled_events import ScheduledEvent


class ScheduledEventWithData(ScheduledEvent):
    """Test scheduled event with custom data for testing."""

    def __init__(self, test_data: str = "test", **kwargs: Any):
        super().__init__(**kwargs)
        self.test_data = test_data

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["test_data"] = self.test_data
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledEventWithData":
        return cls(
            test_data=data.get("test_data", "test"),
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]) if "scheduled_time" in data else datetime.now(),
        )


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database state before each test."""
    reset_engine()
    yield
    try:
        drop_all()
    except Exception:
        pass
    reset_engine()


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestScheduledEventsPersistence:
    """Test scheduled events persistence with message bus."""

    @pytest.mark.asyncio
    async def test_scheduled_events_saved_on_stop(self, temp_db_path):
        """Test that scheduled events are saved when bus is stopped."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Register test event class
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["ScheduledEventWithData"] = ScheduledEventWithData

            bus = MessageBus()
            await bus.start()

            # Create future scheduled events
            future_time = datetime.now() + timedelta(hours=1)
            events = [
                ScheduledEventWithData(test_data="event1", scheduled_time=future_time),
                ScheduledEventWithData(test_data="event2", scheduled_time=future_time),
            ]

            # Publish events to the bus
            for event in events:
                await bus.publish(event, await_processing=False)

            # Verify events are in the queue
            assert bus._event_queue.qsize() == 2

            # Stop the bus (should save events)
            await bus.stop()

            # Verify events were saved by creating new bus and checking restoration
            new_bus = MessageBus()
            await new_bus.start()

            # Events should be restored to the new bus
            assert new_bus._event_queue.qsize() == 2

            await new_bus.stop()

    @pytest.mark.asyncio
    async def test_scheduled_events_loaded_on_start(self, temp_db_path):
        """Test that scheduled events are loaded when bus is started."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["ScheduledEventWithData"] = ScheduledEventWithData

            # First bus: publish and stop
            bus1 = MessageBus()
            await bus1.start()

            future_time = datetime.now() + timedelta(hours=1)
            events = [
                ScheduledEventWithData(test_data="persistent1", scheduled_time=future_time),
                ScheduledEventWithData(test_data="persistent2", scheduled_time=future_time),
            ]

            for event in events:
                await bus1.publish(event, await_processing=False)

            await bus1.stop()

            # Second bus: should restore events on start
            bus2 = MessageBus()
            await bus2.start()

            # Verify events were restored
            assert bus2._event_queue.qsize() == 2

            await bus2.stop()

    @pytest.mark.asyncio
    async def test_only_scheduled_events_are_persisted(self, temp_db_path):
        """Test that only scheduled events are persisted, not regular events."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            bus = MessageBus()
            await bus.start()

            # Create mixed events
            future_time = datetime.now() + timedelta(hours=1)
            scheduled_event = ScheduledEventWithData(test_data="scheduled", scheduled_time=future_time)
            regular_event = Event()

            await bus.publish(scheduled_event, await_processing=False)
            await bus.publish(regular_event, await_processing=False)

            # Original queue should have both events
            assert bus._event_queue.qsize() == 2

            await bus.stop()

            # New bus should only restore scheduled event
            new_bus = MessageBus()
            await new_bus.start()

            # Only the scheduled event should be restored
            assert new_bus._event_queue.qsize() == 1

            await new_bus.stop()

    @pytest.mark.asyncio
    async def test_processed_events_are_not_persisted(self, temp_db_path):
        """Test that processed events are not persisted."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["ScheduledEventWithData"] = ScheduledEventWithData

            bus = MessageBus()

            # Set up event handler
            processed_events: List[Event] = []

            def handler(event: Event):
                processed_events.append(event)

            bus.register_event_handler(ScheduledEventWithData, handler)

            await bus.start()

            # Create event scheduled for immediate processing
            immediate_time = datetime.now() - timedelta(seconds=1)  # Past time
            event = ScheduledEventWithData(test_data="immediate", scheduled_time=immediate_time)

            await bus.publish(event, await_processing=False)

            # Wait for processing
            await asyncio.sleep(0.1)
            await bus.wait_for_events()

            # Verify event was processed
            assert len(processed_events) == 1

            await bus.stop()

            # New bus should not restore processed event
            new_bus = MessageBus()
            await new_bus.start()

            assert new_bus._event_queue.qsize() == 0

            await new_bus.stop()

    @pytest.mark.asyncio
    async def test_database_error_does_not_break_bus(self, temp_db_path):
        """Test that database errors don't break bus operation."""
        # Use invalid database URL to trigger errors
        with patch.dict(os.environ, {"LLMGINE_DB_URL": "invalid://invalid"}):
            bus = MessageBus()

            # Starting bus should succeed despite database errors
            await bus.start()

            # Publishing events should succeed despite database errors
            future_time = datetime.now() + timedelta(hours=1)
            event = ScheduledEvent(scheduled_time=future_time)

            # This should not raise an exception
            await bus.publish(event, await_processing=False)

            # Stopping bus should succeed despite database errors
            await bus.stop()

    @pytest.mark.asyncio
    async def test_events_restored_in_correct_order(self, temp_db_path):
        """Test that events are restored in scheduled time order."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["ScheduledEventWithData"] = ScheduledEventWithData

            bus1 = MessageBus()
            await bus1.start()

            # Create events with different scheduled times
            base_time = datetime.now() + timedelta(hours=1)
            events = [
                ScheduledEventWithData(test_data="third", scheduled_time=base_time + timedelta(hours=2)),
                ScheduledEventWithData(test_data="first", scheduled_time=base_time),
                ScheduledEventWithData(test_data="second", scheduled_time=base_time + timedelta(hours=1)),
            ]

            for event in events:
                await bus1.publish(event, await_processing=False)

            await bus1.stop()

            # New bus should restore events in scheduled time order
            bus2 = MessageBus()
            processed_events: List[ScheduledEventWithData] = []

            def handler(event: Event):
                if isinstance(event, ScheduledEventWithData):
                    processed_events.append(event)

            bus2.register_event_handler(ScheduledEventWithData, handler)
            await bus2.start()

            # Process events immediately by setting past scheduled times
            # We'll simulate this by draining the queue and checking order
            restored_events = []
            while not bus2._event_queue.empty():
                event = await bus2._event_queue.get()
                restored_events.append(event)
                bus2._event_queue.task_done()

            # Verify order (earliest first)
            assert len(restored_events) == 3
            assert restored_events[0].test_data == "first"
            assert restored_events[1].test_data == "second"
            assert restored_events[2].test_data == "third"

            await bus2.stop()

    @pytest.mark.asyncio
    async def test_multiple_bus_instances_share_persistence(self, temp_db_path):
        """Test that multiple bus instances share the same persistence store."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["ScheduledEventWithData"] = ScheduledEventWithData

            # First bus saves events
            bus1 = MessageBus()
            await bus1.start()

            future_time = datetime.now() + timedelta(hours=1)
            event1 = ScheduledEventWithData(test_data="from_bus1", scheduled_time=future_time)
            await bus1.publish(event1, await_processing=False)

            await bus1.stop()

            # Second bus adds more events
            bus2 = MessageBus()
            await bus2.start()

            event2 = ScheduledEventWithData(test_data="from_bus2", scheduled_time=future_time)
            await bus2.publish(event2, await_processing=False)

            # Bus2 should have both events (1 restored + 1 new)
            assert bus2._event_queue.qsize() == 2

            await bus2.stop()

            # Third bus should restore both events
            bus3 = MessageBus()
            await bus3.start()

            assert bus3._event_queue.qsize() == 2

            await bus3.stop()


class TestEventLoggingIntegration:
    """Test optional event logging integration with message bus."""

    @pytest.mark.asyncio
    async def test_event_logging_disabled_by_default(self, temp_db_path):
        """Test that event logging is disabled by default."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            bus = MessageBus()
            await bus.start()

            # Publish various events
            await bus.publish(Event(), await_processing=False)
            await bus.publish(ScheduledEvent(), await_processing=False)

            await bus.stop()

            # Verify no events were logged to database
            from llmgine.database.database import DatabaseEngine, EventRecord
            engine = DatabaseEngine.get_engine()
            session = DatabaseEngine.get_session()
            try:
                records = session.query(EventRecord).all()
                assert len(records) == 0
            finally:
                session.close()

    @pytest.mark.asyncio
    async def test_event_logging_when_enabled(self, temp_db_path):
        """Test that event logging works when enabled."""
        with patch.dict(os.environ, {
            "LLMGINE_DB_URL": f"sqlite:///{temp_db_path}",
            "LLMGINE_PERSIST_EVENTS": "1",
        }):
            bus = MessageBus()
            await bus.start()

            # Publish events
            regular_event = Event()
            scheduled_event = ScheduledEvent()

            await bus.publish(regular_event, await_processing=False)
            await bus.publish(scheduled_event, await_processing=False)

            # Wait for processing
            await asyncio.sleep(0.1)

            await bus.stop()

            # Verify events were logged to database
            from llmgine.database.database import DatabaseEngine, EventRecord
            engine = DatabaseEngine.get_engine()
            session = DatabaseEngine.get_session()
            try:
                records = session.query(EventRecord).all()
                assert len(records) == 2

                # Verify event IDs match
                logged_ids = {record.event_id for record in records}
                expected_ids = {regular_event.event_id, scheduled_event.event_id}
                assert logged_ids == expected_ids
            finally:
                session.close()

    @pytest.mark.asyncio
    async def test_event_logging_error_does_not_break_bus(self, temp_db_path):
        """Test that event logging errors don't break bus operation."""
        with patch.dict(os.environ, {
            "LLMGINE_DB_URL": "invalid://invalid",
            "LLMGINE_PERSIST_EVENTS": "1",
        }):
            bus = MessageBus()
            await bus.start()

            # This should not raise an exception despite invalid database
            await bus.publish(Event(), await_processing=False)

            await bus.stop()


class TestBestEffortBehavior:
    """Test best-effort behavior under various error conditions."""

    @pytest.mark.asyncio
    async def test_partial_failure_during_save(self, temp_db_path):
        """Test that partial failures during save are handled gracefully."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            bus = MessageBus()
            await bus.start()

            # Add a valid scheduled event
            future_time = datetime.now() + timedelta(hours=1)
            event = ScheduledEvent(scheduled_time=future_time)
            await bus.publish(event, await_processing=False)

            # Corrupt the database connection before stopping
            # (This simulates database becoming unavailable)
            from llmgine.database.database import DatabaseEngine
            if DatabaseEngine._engine:
                DatabaseEngine._engine.dispose()

            # Stop should not raise an exception
            await bus.stop()

    @pytest.mark.asyncio
    async def test_partial_failure_during_load(self, temp_db_path):
        """Test that partial failures during load are handled gracefully."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # First, save some events successfully
            bus1 = MessageBus()
            await bus1.start()

            future_time = datetime.now() + timedelta(hours=1)
            event = ScheduledEvent(scheduled_time=future_time)
            await bus1.publish(event, await_processing=False)

            await bus1.stop()

            # Now corrupt the database and try to start new bus
            # Change database URL to invalid one to simulate connection failure
            with patch.dict(os.environ, {"LLMGINE_DB_URL": "invalid://invalid"}):
                # Force database engine reset to recognize the URL change
                reset_engine()

                bus2 = MessageBus()
                # Start should not raise an exception
                await bus2.start()

                # Bus should start with empty queue since load failed
                assert bus2._event_queue.qsize() == 0

                await bus2.stop()

    @pytest.mark.asyncio
    async def test_bus_functionality_preserved_with_persistence_errors(self, temp_db_path):
        """Test that core bus functionality works even with persistence errors."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": "invalid://invalid"}):
            bus = MessageBus()
            processed_events: List[Event] = []

            def handler(event: Event):
                processed_events.append(event)

            bus.register_event_handler(Event, handler)
            await bus.start()

            # Bus should still process regular events normally
            event = Event()
            await bus.publish(event)

            # Verify event was processed despite persistence errors
            assert len(processed_events) == 1
            assert processed_events[0].event_id == event.event_id

            await bus.stop()