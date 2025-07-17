from pydantic import Field
from typing import Any, Dict, Optional

from openai.types.chat import ChatCompletion

from llmgine.llm.providers.providers import Providers
from llmgine.messages.events import Event


class LLMResponseEvent(Event):
    call_id: str = Field(default_factory=str)
    raw_response: Optional[ChatCompletion] = None
    error: Optional[str] = None


class LLMCallEvent(Event):
    model_id: str = Field(default_factory=str)
    call_id: str = Field(default_factory=str)
    provider: Optional[Providers] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
