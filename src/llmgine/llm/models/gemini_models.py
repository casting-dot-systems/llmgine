import os
import uuid
import dotenv
from typing import List, Dict, Optional, Literal, Union, Any
from llmgine.llm.models.model import Model
from llmgine.llm.providers.openrouter import OpenRouterProvider, OpenRouterResponse
from llmgine.llm.providers import Providers
from llmgine.llm.providers.providers import Provider
from llmgine.llm.providers.response import LLMResponse

dotenv.load_dotenv()


class Gemini25FlashPreview:
    """
    Gemini 2.5 Flash Preview
    """

    def __init__(self, provider: Providers) -> None:
        self.id = str(uuid.uuid4())
        self.generate = None
        self._setProvider(provider)

    def _setProvider(self, provider: Providers) -> None:
        """Get the provider and set the generate method."""
        if provider == Providers.OPENROUTER:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            self.model = "google/gemini-2.5-flash-preview"
            self.provider = OpenRouterProvider(
                self.api_key, self.model, "Google AI Studio", self.id
            )
            self.generate = self._generate_from_openrouter
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )

    def _generate_from_openrouter(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Union[Literal["auto", "none", "required"], Dict] = "auto",
        temperature: float = 0.7,
        max_completion_tokens: int = 5068,
    ) -> LLMResponse:
        return self.provider.generate(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
