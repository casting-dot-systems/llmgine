from dataclasses import dataclass, field
from typing import Any, Dict

from llmgine.llm.providers.providers import Providers
from llmgine.messages.events import Event


@dataclass
class LLMResponseEvent(Event):
    call_id: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error: Exception = None


@dataclass
class LLMCallEvent(Event):
    model_id: str = ""
    call_id: str = ""
    provider: Providers = None
    payload: Dict[str, Any] = field(default_factory=dict)
