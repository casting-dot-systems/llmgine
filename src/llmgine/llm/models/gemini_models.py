import os
import uuid
import dotenv
from typing import List, Dict, Optional, Any
from llmgine.llm.models.model import Model
from llmgine.llm.providers.openrouter import OpenRouterProvider
from llmgine.llm.providers import Providers
from llmgine.llm.providers.response import LLMResponse
from llmgine.llm import ToolChoiceOrDictType, ModelFormattedDictTool

dotenv.load_dotenv()


class Gemini25FlashPreview(Model):
    """
    Gemini 2.5 Flash Preview
    """

    def __init__(self, provider: Providers) -> None:
        self.id : str = str(uuid.uuid4())
        self.generate : Optional[Any] = None
        self._setProvider(provider)

    def _setProvider(self, provider: Providers) -> None:
        """Get the provider and set the generate method."""
        if provider == Providers.OPENROUTER:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            self.model = "google/gemini-2.5-flash-preview"
            assert self.api_key is not None, "OPENROUTER_API_KEY is not set"
            self.provider = OpenRouterProvider(
                self.api_key, self.model, "Google AI Studio", self.id
            )
            self.generate = self._generate_from_openrouter
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )

    async def _generate_from_openrouter(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[ModelFormattedDictTool]] = None,
        tool_choice: ToolChoiceOrDictType = "auto",
        temperature: float = 0.7,
        max_completion_tokens: int = 5068,
    ) -> LLMResponse:
        

        tmp = await self.provider.generate(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
        #assert isinstance(tmp, LLMResponse), "tmp is not an LLMResponse"
        return tmp

