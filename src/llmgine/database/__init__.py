"""Database package for LLMgine message bus persistence.

This package provides SQLAlchemy ORM-based persistence for:
- Scheduled events (for restoration across restarts)
- Optional event logging (when LLMGINE_PERSIST_EVENTS=1)

Public API:
- save_unfinished_events(): Save scheduled events to storage
- get_and_delete_unfinished_events(): Restore scheduled events from storage
- persist_event(): Optionally log events to persistent storage

Configuration via environment variables:
- LLMGINE_DB_URL: Database URL (default: sqlite:///./message_bus.db)
- LLMGINE_DB_SCHEMA: Schema name for Postgres (default: message_bus)
- LLMGINE_PERSIST_EVENTS: Enable event logging (default: 0)
"""

from llmgine.database.database import (
    get_and_delete_unfinished_events,
    persist_event,
    save_unfinished_events,
    # Test helpers - only import if needed for testing
    drop_all,
    reset_engine,
)

__all__ = [
    "save_unfinished_events",
    "get_and_delete_unfinished_events",
    "persist_event",
    "reset_engine",
    "drop_all",
]