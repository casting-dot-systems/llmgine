"""Tests for SQLAlchemy ORM-based event persistence.

This module tests the database module functionality including:
- SQLAlchemy ORM models
- Environment variable configuration
- Schema creation for both SQLite and PostgreSQL
- Event persistence and retrieval
- Best-effort error handling
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import patch

import pytest
from sqlalchemy import text

from llmgine.database.database import (
    DatabaseConfig,
    DatabaseEngine,
    EventRecord,
    ScheduledEventRecord,
    drop_all,
    get_and_delete_unfinished_events,
    persist_event,
    reset_engine,
    save_unfinished_events,
)
from llmgine.messages.events import Event
from llmgine.messages.scheduled_events import ScheduledEvent


class CustomTestEvent(Event):
    """Test event class for testing."""

    def __init__(self, test_data: str = "test", **kwargs: Any):
        super().__init__(**kwargs)
        self.test_data = test_data

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["test_data"] = self.test_data
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomTestEvent":
        return cls(
            test_data=data.get("test_data", "test"),
            event_id=data.get("event_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
        )


class CustomTestScheduledEvent(ScheduledEvent):
    """Test scheduled event class for testing."""

    def __init__(self, test_data: str = "scheduled_test", **kwargs: Any):
        super().__init__(**kwargs)
        self.test_data = test_data

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["test_data"] = self.test_data
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomTestScheduledEvent":
        return cls(
            test_data=data.get("test_data", "scheduled_test"),
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


class TestDatabaseConfig:
    """Test database configuration handling."""

    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = DatabaseConfig()
            assert config.db_url == "sqlite:///./message_bus.db"
            assert config.schema == "message_bus"
            assert config.persist_events is False
            assert config.is_postgres is False

    def test_custom_config(self):
        """Test custom configuration from environment variables."""
        env_vars = {
            "LLMGINE_DB_URL": "postgresql://user:pass@localhost/test",
            "LLMGINE_DB_SCHEMA": "custom_schema",
            "LLMGINE_PERSIST_EVENTS": "1",
        }
        with patch.dict(os.environ, env_vars):
            config = DatabaseConfig()
            assert config.db_url == "postgresql://user:pass@localhost/test"
            assert config.schema == "custom_schema"
            assert config.persist_events is True
            assert config.is_postgres is True

    def test_postgres_detection(self):
        """Test PostgreSQL URL detection."""
        postgres_urls = [
            "postgresql://localhost/test",
            "postgresql+psycopg2://user:pass@host/db",
        ]
        for url in postgres_urls:
            with patch.dict(os.environ, {"LLMGINE_DB_URL": url}):
                config = DatabaseConfig()
                assert config.is_postgres is True

    def test_sqlite_detection(self):
        """Test SQLite URL detection."""
        sqlite_urls = [
            "sqlite:///./test.db",
            "sqlite:///:memory:",
        ]
        for url in sqlite_urls:
            with patch.dict(os.environ, {"LLMGINE_DB_URL": url}):
                config = DatabaseConfig()
                assert config.is_postgres is False


class TestDatabaseEngine:
    """Test database engine management."""

    def test_sqlite_engine_creation(self, temp_db_path):
        """Test SQLite engine creation and table setup."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            engine = DatabaseEngine.get_engine()
            assert engine is not None

            # Verify tables exist
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                table_names = {row[0] for row in result.fetchall()}
                assert "message_bus_scheduled_events" in table_names
                assert "message_bus_event_log" in table_names

    def test_sqlite_schema_prefix(self, temp_db_path):
        """Test SQLite uses schema as table prefix."""
        with patch.dict(os.environ, {
            "LLMGINE_DB_URL": f"sqlite:///{temp_db_path}",
            "LLMGINE_DB_SCHEMA": "custom.schema",
        }):
            engine = DatabaseEngine.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                table_names = {row[0] for row in result.fetchall()}
                assert "custom_schema_scheduled_events" in table_names
                assert "custom_schema_event_log" in table_names

    def test_engine_singleton(self, temp_db_path):
        """Test engine singleton behavior."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            engine1 = DatabaseEngine.get_engine()
            engine2 = DatabaseEngine.get_engine()
            assert engine1 is engine2

    def test_session_creation(self, temp_db_path):
        """Test database session creation."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            session = DatabaseEngine.get_session()
            assert session is not None
            session.close()

    def test_reset_engine(self, temp_db_path):
        """Test engine reset functionality."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            engine1 = DatabaseEngine.get_engine()
            reset_engine()
            engine2 = DatabaseEngine.get_engine()
            assert engine1 is not engine2


class TestScheduledEventPersistence:
    """Test scheduled event persistence functionality."""

    def test_save_and_retrieve_scheduled_events(self, temp_db_path):
        """Test saving and retrieving scheduled events."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Register test event class
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["CustomTestScheduledEvent"] = CustomTestScheduledEvent

            # Create test events
            future_time = datetime.now() + timedelta(hours=1)
            events = [
                CustomTestScheduledEvent(test_data="event1", scheduled_time=future_time),
                CustomTestScheduledEvent(test_data="event2", scheduled_time=future_time),
            ]

            # Save events
            save_unfinished_events(events)

            # Retrieve events
            retrieved_events = get_and_delete_unfinished_events()

            # Verify events
            assert len(retrieved_events) == 2
            assert all(isinstance(event, CustomTestScheduledEvent) for event in retrieved_events)
            assert {event.test_data for event in retrieved_events} == {"event1", "event2"}

            # Verify events are deleted after retrieval
            second_retrieval = get_and_delete_unfinished_events()
            assert len(second_retrieval) == 0

    def test_save_empty_events_list(self, temp_db_path):
        """Test saving empty events list."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            save_unfinished_events([])
            # Should not raise any errors

    def test_retrieve_events_ordered_by_time(self, temp_db_path):
        """Test events are retrieved in scheduled time order."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            from llmgine.messages.scheduled_events import EVENT_CLASSES
            EVENT_CLASSES["CustomTestScheduledEvent"] = CustomTestScheduledEvent

            # Create events with different scheduled times
            base_time = datetime.now()
            events = [
                CustomTestScheduledEvent(test_data="later", scheduled_time=base_time + timedelta(hours=2)),
                CustomTestScheduledEvent(test_data="earlier", scheduled_time=base_time + timedelta(hours=1)),
                CustomTestScheduledEvent(test_data="middle", scheduled_time=base_time + timedelta(hours=1.5)),
            ]

            save_unfinished_events(events)
            retrieved_events = get_and_delete_unfinished_events()

            # Verify order
            assert len(retrieved_events) == 3
            assert retrieved_events[0].test_data == "earlier"
            assert retrieved_events[1].test_data == "middle"
            assert retrieved_events[2].test_data == "later"

    def test_unknown_event_class_handling(self, temp_db_path):
        """Test handling of unknown event classes."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Manually insert a record with unknown event class
            engine = DatabaseEngine.get_engine()
            session = DatabaseEngine.get_session()

            try:
                record = ScheduledEventRecord(
                    event_id="test-id",
                    event_class_name="UnknownEventClass",
                    event_data={"test": "data"},
                    scheduled_time=datetime.now(),
                )
                session.add(record)
                session.commit()

                # Retrieving should handle unknown class gracefully
                events = get_and_delete_unfinished_events()
                assert len(events) == 0  # Unknown events are skipped
            finally:
                session.close()


class TestEventLogging:
    """Test optional event logging functionality."""

    def test_persist_event_disabled_by_default(self, temp_db_path):
        """Test event persistence is disabled by default."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            event = CustomTestEvent(test_data="test_event")
            persist_event(event)

            # Verify no event was persisted
            engine = DatabaseEngine.get_engine()
            session = DatabaseEngine.get_session()
            try:
                records = session.query(EventRecord).all()
                assert len(records) == 0
            finally:
                session.close()

    def test_persist_event_when_enabled(self, temp_db_path):
        """Test event persistence when enabled."""
        with patch.dict(os.environ, {
            "LLMGINE_DB_URL": f"sqlite:///{temp_db_path}",
            "LLMGINE_PERSIST_EVENTS": "1",
        }):
            # Force engine initialization first
            engine = DatabaseEngine.get_engine()

            event = CustomTestEvent(test_data="test_event")
            persist_event(event)

            # Verify event was persisted
            session = DatabaseEngine.get_session()
            try:
                records = session.query(EventRecord).all()
                assert len(records) == 1
                record = records[0]
                assert record.event_id == event.event_id
                assert record.event_class_name == "CustomTestEvent"
                assert json.loads(record.event_data)["test_data"] == "test_event"
            finally:
                session.close()


class TestErrorHandling:
    """Test error handling and best-effort behavior."""

    def test_save_events_with_invalid_database(self):
        """Test save events handles database errors gracefully."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": "invalid://invalid"}):
            events = [ScheduledEvent()]
            # Should not raise exception
            save_unfinished_events(events)

    def test_retrieve_events_with_invalid_database(self):
        """Test retrieve events handles database errors gracefully."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": "invalid://invalid"}):
            # Should not raise exception and return empty list
            events = get_and_delete_unfinished_events()
            assert events == []

    def test_persist_event_with_invalid_database(self):
        """Test persist event handles database errors gracefully."""
        with patch.dict(os.environ, {
            "LLMGINE_DB_URL": "invalid://invalid",
            "LLMGINE_PERSIST_EVENTS": "1",
        }):
            event = CustomTestEvent()
            # Should not raise exception
            persist_event(event)

    def test_malformed_event_data_handling(self, temp_db_path):
        """Test handling of malformed event data during retrieval."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Manually insert malformed data
            engine = DatabaseEngine.get_engine()
            session = DatabaseEngine.get_session()

            try:
                record = ScheduledEventRecord(
                    event_id="malformed",
                    event_class_name="ScheduledEvent",
                    event_data={"invalid": "data"},  # Missing required fields
                    scheduled_time=datetime.now(),
                )
                session.add(record)
                session.commit()

                # Should handle malformed data gracefully
                events = get_and_delete_unfinished_events()
                # Malformed events are skipped, but transaction still succeeds
                assert len(events) == 0
            finally:
                session.close()


class TestHelpers:
    """Test helper functions for development/testing."""

    def test_reset_engine_helper(self, temp_db_path):
        """Test reset_engine helper function."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Create engine
            engine1 = DatabaseEngine.get_engine()

            # Reset using helper
            reset_engine()

            # Verify new engine is created
            engine2 = DatabaseEngine.get_engine()
            assert engine1 is not engine2

    def test_drop_all_helper(self, temp_db_path):
        """Test drop_all helper function."""
        with patch.dict(os.environ, {"LLMGINE_DB_URL": f"sqlite:///{temp_db_path}"}):
            # Create tables
            engine = DatabaseEngine.get_engine()

            # Drop tables using helper
            drop_all()

            # Verify tables are dropped (in SQLite, check sqlite_master)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                table_names = {row[0] for row in result.fetchall()}
                # Tables should be dropped, but sqlite_master itself remains
                assert "message_bus_scheduled_events" not in table_names
                assert "message_bus_event_log" not in table_names