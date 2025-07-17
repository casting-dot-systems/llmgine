
import os
import uuid
from anthropic import AsyncAnthropic
import dotenv
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from llmgine.bootstrap import ApplicationConfig
from llmgine.llm.models.model import Model
from llmgine.llm.providers.anthropic import AnthropicProvider, AnthropicResponse
from llmgine.llm.providers import Providers
from llmgine.llm.providers.response import LLMResponse
import instructor
from llmgine.llm import ToolChoiceOrDictType, ModelFormattedDictTool

dotenv.load_dotenv()

class Claude35Haiku(Model):
    """
    Claude 3.5 Haiku
    """

    def __init__(self, provider: Providers) -> None:
        self.id = str(uuid.uuid4())
        self.generate = None
        self._setProvider(provider)

    def _setProvider(self, provider: Providers) -> None:
        """Get the provider and set the generate method."""
        if provider == Providers.ANTHROPIC:
            self.api_key = os.getenv("ANTHROPIC_API_KEY") or ""
            self.model = "claude-3-5-haiku-20241022"
            self.provider = AnthropicProvider(
                self.api_key, self.model, self.id
            )
            self.generate = self._generate_from_anthropic
            self.instructor = None
        else:
            raise ValueError(
                f"Provider {provider} not supported for {self.__class__.__name__}"
            )

    async def _generate_from_anthropic(
        self,   
        messages: List[Dict[str, Any]],
        tools: Optional[List[ModelFormattedDictTool]] = None,
        tool_choice: ToolChoiceOrDictType = "auto",
        temperature: float = 0.7,
        max_completion_tokens: int = 5068,
        response_format: Optional[Dict[str, Any]] = None,
        thinking_enabled: bool = False,
        thinking_budget: Optional[int] = None,
        instruct: bool = False,
        response_model: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not instruct:
            result = await self.provider.generate(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                response_format=response_format,
                thinking_enabled=thinking_enabled,
                thinking_budget=thinking_budget,
                **kwargs,
            )
        else:
            if not self.instructor:
                self.instructor = instructor.from_anthropic(AsyncAnthropic())
            result = await self.instructor.messages.generate(
                messages=messages,
                response_model=response_model,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                **kwargs,
            )
            result = AnthropicResponse(result)
        return result



class HowAmI(BaseModel):
    emotion: str
    reason: str

async def main() -> None:
    from llmgine.bootstrap import ApplicationBootstrap
    app = ApplicationBootstrap(ApplicationConfig(enable_console_handler=False))
    await app.bootstrap()
    model = Claude35Haiku(Providers.ANTHROPIC)
    response = await model.generate(messages=[{"role": "user", "content": "Hello, how are you?"}], instruct=True, response_model=HowAmI)
    print(response.content)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
