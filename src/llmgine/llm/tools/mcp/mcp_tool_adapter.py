from typing import List

from mcp import ListToolsResult

from llmgine.llm import ModelFormattedDictTool


class ToolAdapter:
    def __init__(self, llm_model_name: str):
        self.llm_model_name: str = llm_model_name

    def convert_tools(self, tools: ListToolsResult) -> List[ModelFormattedDictTool]:
        # Determine provider based on model name
        if self._is_openai_model(self.llm_model_name):
            return self.convert_openai_tools(tools)
        elif self._is_anthropic_model(self.llm_model_name):
            return self.convert_anthropic_tools(tools)
        elif self._is_gemini_model(self.llm_model_name):
            return self.convert_gemini_tools(tools)
        else:
            # Default to OpenAI format for unknown models
            return self.convert_openai_tools(tools)

    def _is_openai_model(self, model: str) -> bool:
        """Check if model is an OpenAI model."""
        openai_prefixes = ["gpt-", "o1-", "text-davinci", "text-curie", "text-babbage", "text-ada"]
        return any(model.startswith(prefix) for prefix in openai_prefixes)

    def _is_anthropic_model(self, model: str) -> bool:
        """Check if model is an Anthropic model."""
        return model.startswith("claude-")

    def _is_gemini_model(self, model: str) -> bool:
        """Check if model is a Gemini model."""
        return model.startswith("gemini-")

    def convert_openai_tools(
        self, tools: ListToolsResult
    ) -> List[ModelFormattedDictTool]:
        # TODO: Implement OpenAI tool format conversion
        return []

    def convert_anthropic_tools(
        self, tools: ListToolsResult
    ) -> List[ModelFormattedDictTool]:
        # TODO: Implement Anthropic tool format conversion
        return []

    def convert_gemini_tools(
        self, tools: ListToolsResult
    ) -> List[ModelFormattedDictTool]:
        # TODO: Implement Gemini tool format conversion
        return []
