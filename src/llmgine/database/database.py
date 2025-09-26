"""SQLAlchemy ORM-based database module for LLMgine message bus persistence.

This module provides:
- SQLAlchemy ORM models for scheduled events and optional event logging
- Environment variable configuration
- Support for both SQLite (default) and PostgreSQL
- Schema creation for Postgres, table prefixes for SQLite
- Public API for scheduled event persistence
- Test helpers for development/testing
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateSchema, DDL

from llmgine.messages.events import Event
from llmgine.messages.scheduled_events import EVENT_CLASSES, ScheduledEvent

logger = logging.getLogger(__name__)

# SQLAlchemy ORM setup
Base = declarative_base()


class ScheduledEventRecord(Base):
    """SQLAlchemy model for storing scheduled events."""

    __tablename__ = "scheduled_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), nullable=False)
    event_class_name = Column(String(255), nullable=False)
    event_data = Column(JSON, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now())


class EventRecord(Base):
    """SQLAlchemy model for optional event logging."""

    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), nullable=False)
    event_class_name = Column(String(255), nullable=False)
    event_data = Column(Text, nullable=False)  # JSON string
    session_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now())


class DatabaseConfig:
    """Configuration for database connection and schema handling."""

    def __init__(self):
        # Database URL configuration
        self.db_url = os.getenv("LLMGINE_DB_URL", "sqlite:///./message_bus.db")

        # Schema configuration (for PostgreSQL)
        self.schema = os.getenv("LLMGINE_DB_SCHEMA", "message_bus")

        # Event persistence toggle
        self.persist_events = os.getenv("LLMGINE_PERSIST_EVENTS", "0") == "1"

        # Determine if we're using PostgreSQL
        self.is_postgres = self.db_url.startswith("postgresql")

        logger.debug(f"Database config - URL: {self.db_url}, Schema: {self.schema}, "
                    f"Persist events: {self.persist_events}, Is Postgres: {self.is_postgres}")

    def has_changed(self, other_config: "DatabaseConfig") -> bool:
        """Check if configuration has changed from another config instance."""
        return (
            self.db_url != other_config.db_url
            or self.schema != other_config.schema
            or self.persist_events != other_config.persist_events
        )


class DatabaseEngine:
    """Singleton database engine manager with schema support."""

    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _config: Optional[DatabaseConfig] = None
    _schema_created = False

    @classmethod
    def get_config(cls) -> DatabaseConfig:
        """Get database configuration."""
        new_config = DatabaseConfig()

        # If config has changed, reset engine to use new configuration
        if cls._config is not None and new_config.has_changed(cls._config):
            logger.debug("Database configuration changed, resetting engine")
            cls.reset_engine()

        cls._config = new_config
        return cls._config

    @classmethod
    def get_engine(cls) -> Engine:
        """Get database engine, creating if necessary."""
        if cls._engine is None:
            config = cls.get_config()

            # Handle invalid database URLs gracefully
            try:
                cls._engine = create_engine(config.db_url)
                cls._session_factory = sessionmaker(bind=cls._engine)
                cls._ensure_schema_and_tables()
            except Exception as e:
                logger.warning(f"Failed to create database engine: {e}")
                # Return a mock engine that will fail gracefully
                raise RuntimeError(f"Database engine creation failed: {e}")

        return cls._engine

    @classmethod
    def get_session(cls) -> Session:
        """Get database session."""
        if cls._session_factory is None:
            cls.get_engine()  # Initialize engine and session factory
        return cls._session_factory()

    @classmethod
    def _ensure_schema_and_tables(cls) -> None:
        """Ensure database schema and tables exist."""
        if cls._schema_created:
            return

        config = cls.get_config()
        engine = cls._engine

        try:
            # For PostgreSQL, create schema if it doesn't exist and set schema on tables
            if config.is_postgres:
                with engine.begin() as conn:  # Use begin() for automatic transaction
                    try:
                        # Check if schema exists
                        schema_exists = conn.execute(
                            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                            {"schema": config.schema}
                        ).fetchone()

                        if not schema_exists:
                            conn.execute(CreateSchema(config.schema))
                            logger.debug(f"Created schema '{config.schema}'")
                        else:
                            logger.debug(f"Schema '{config.schema}' already exists")
                    except Exception as e:
                        logger.warning(f"Schema creation error (may be handled by database): {e}")

                # Set table schema for PostgreSQL
                ScheduledEventRecord.__table__.schema = config.schema
                EventRecord.__table__.schema = config.schema

                # Create all tables for PostgreSQL
                Base.metadata.create_all(engine)
            else:
                # For SQLite, modify table names to include schema prefix
                prefix = config.schema.replace(".", "_") + "_"

                # Create new table instances with prefixed names if not already set
                if not ScheduledEventRecord.__table__.name.startswith(prefix):
                    ScheduledEventRecord.__table__.name = f"{prefix}scheduled_events"
                    EventRecord.__table__.name = f"{prefix}event_log"

                # Create tables with the new names
                Base.metadata.create_all(engine)

            cls._schema_created = True
            logger.debug("Database tables created/verified")

        except Exception as e:
            logger.warning(f"Error creating database schema/tables (continuing with best-effort): {e}")
            # Don't raise - make this truly best-effort
            cls._schema_created = True  # Mark as created to avoid repeated attempts

    @classmethod
    def reset_engine(cls) -> None:
        """Reset engine for testing (test helper)."""
        if cls._engine:
            cls._engine.dispose()
        cls._engine = None
        cls._session_factory = None
        cls._config = None
        cls._schema_created = False

    @classmethod
    def drop_all(cls) -> None:
        """Drop all tables (test helper)."""
        if cls._engine:
            Base.metadata.drop_all(cls._engine)
            cls._schema_created = False


# Public API functions

def save_unfinished_events(events: List[ScheduledEvent]) -> None:
    """Save unfinished scheduled events to persistent storage.

    This is a best-effort operation that should not raise exceptions
    that could break the message bus operation.

    Args:
        events: List of ScheduledEvent instances to persist
    """
    if not events:
        return

    try:
        engine = DatabaseEngine.get_engine()
        session = DatabaseEngine.get_session()

        try:
            records = []
            for event in events:
                # Convert event to dictionary for JSON storage
                event_data = event.to_dict()

                # Ensure datetime objects are converted to strings for JSON serialization
                if 'timestamp' in event_data and isinstance(event_data['timestamp'], datetime):
                    event_data['timestamp'] = event_data['timestamp'].isoformat()
                if 'scheduled_time' in event_data and isinstance(event_data['scheduled_time'], datetime):
                    event_data['scheduled_time'] = event_data['scheduled_time'].isoformat()

                record = ScheduledEventRecord(
                    event_id=event.event_id,
                    event_class_name=event.__class__.__name__,
                    event_data=event_data,
                    scheduled_time=event.scheduled_time,
                )
                records.append(record)

            session.add_all(records)
            session.commit()
            logger.info(f"Saved {len(events)} scheduled events to database")

        finally:
            session.close()

    except Exception as e:
        logger.warning(f"Failed to save scheduled events (best-effort, continuing): {e}")
        # Best-effort: don't raise exceptions that could break the bus


def get_and_delete_unfinished_events() -> List[ScheduledEvent]:
    """Retrieve and delete all unfinished scheduled events from storage.

    Returns:
        List of ScheduledEvent instances that were restored from storage
    """
    events: List[ScheduledEvent] = []

    try:
        engine = DatabaseEngine.get_engine()
        session = DatabaseEngine.get_session()

        try:
            # Query all scheduled event records
            records = session.query(ScheduledEventRecord).order_by(
                ScheduledEventRecord.scheduled_time
            ).all()

            # Convert records back to ScheduledEvent objects
            for record in records:
                try:
                    event_class = EVENT_CLASSES.get(record.event_class_name)
                    if event_class:
                        # Reconstruct event from stored data
                        event = event_class.from_dict(record.event_data)
                        events.append(event)
                    else:
                        logger.warning(f"Unknown event class: {record.event_class_name}")
                except Exception as e:
                    logger.error(f"Failed to reconstruct event {record.id}: {e}")
                    continue

            # Delete all records after successful reconstruction
            if records:
                session.query(ScheduledEventRecord).delete()
                session.commit()
                logger.info(f"Retrieved and deleted {len(events)} scheduled events")

        finally:
            session.close()

    except Exception as e:
        logger.warning(f"Failed to retrieve scheduled events (best-effort, returning empty): {e}")
        return []

    return events


def persist_event(event: Event) -> None:
    """Optionally persist an event to the event log.

    This function only persists events if LLMGINE_PERSIST_EVENTS=1.
    It's a best-effort operation that should not raise exceptions.

    Args:
        event: Event instance to persist
    """
    try:
        config = DatabaseEngine.get_config()

        # Early return if event persistence is disabled
        if not config.persist_events:
            return

        engine = DatabaseEngine.get_engine()
        session = DatabaseEngine.get_session()

        try:
            # Convert event to dictionary and then to JSON string
            event_dict = event.to_dict()
            event_data_json = json.dumps(event_dict, default=str)

            # Convert timestamp string to datetime object if needed
            timestamp_dt = event.timestamp
            if isinstance(timestamp_dt, str):
                timestamp_dt = datetime.fromisoformat(timestamp_dt)

            record = EventRecord(
                event_id=event.event_id,
                event_class_name=event.__class__.__name__,
                event_data=event_data_json,
                session_id=str(event.session_id) if event.session_id else None,
                timestamp=timestamp_dt,
            )

            session.add(record)
            session.commit()
            logger.debug(f"Persisted event {event.event_id} to event log")

        finally:
            session.close()

    except Exception as e:
        logger.debug(f"Failed to persist event {getattr(event, 'event_id', 'unknown')} (best-effort, ignored): {e}")
        # Best-effort: don't raise exceptions that could break the bus


# Test helpers (for development and testing only)

def reset_engine() -> None:
    """Reset the database engine (test helper).

    This should only be used in tests to reset database state.
    """
    DatabaseEngine.reset_engine()


def drop_all() -> None:
    """Drop all database tables (test helper).

    This should only be used in tests to clean up database state.
    """
    DatabaseEngine.drop_all()