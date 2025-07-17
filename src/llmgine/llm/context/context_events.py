from typing import Any, Dict, List
from pydantic import Field

from llmgine.messages.events import Event


class ContextEvent(Event):
    """Base class for all context events."""

    engine_id: str = ""
    context_manager_id: str = ""


class ChatHistoryRetrievedEvent(ContextEvent):
    """Event for when chat history is retrieved."""

    context: List[Dict[str, Any]] = Field(default_factory=list)


class ChatHistoryUpdatedEvent(ContextEvent):
    """Event for when chat history is updated."""

    context: List[Dict[str, Any]] = Field(default_factory=list)
