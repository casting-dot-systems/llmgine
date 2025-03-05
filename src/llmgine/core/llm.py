from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from ..bus.events import LLMRequestEvent, LLMResponseEvent
import uuid


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate_text(self, prompt: str, parameters: Dict[str, Any]) -> str:
        """Generate text with the given prompt and parameters"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the LLM provider"""
        pass

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get the list of supported models"""
        pass


class LLMRouter:
    """Routes requests to appropriate LLM providers"""

    def __init__(self, message_bus=None):
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self.message_bus = message_bus

    def register_provider(self, provider: LLMProvider, is_default: bool = False):
        """Register an LLM provider"""
        provider_name = provider.get_name()
        self.providers[provider_name] = provider

        if is_default or self.default_provider is None:
            self.default_provider = provider_name

    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get a specific provider or the default one"""
        if provider_name is None:
            if self.default_provider is None:
                raise ValueError("No default provider set")
            return self.providers[self.default_provider]

        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not registered")

        return self.providers[provider_name]

    def generate_text(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        parameters: Dict[str, Any] = None,
    ) -> str:
        """Generate text using the specified provider and model"""
        parameters = parameters or {}
        provider = self.get_provider(provider_name)

        # If a model is specified, add it to the parameters
        if model is not None:
            parameters["model"] = model

        request_id = str(uuid.uuid4())

        # Emit request event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "llm.request",
                LLMRequestEvent(
                    request_id=request_id,
                    prompt=prompt,
                    model=model or "default",
                    parameters=parameters,
                ),
            )

        # Generate the response
        response = provider.generate_text(prompt, parameters)

        # Emit response event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "llm.response",
                LLMResponseEvent(
                    request_id=request_id,
                    response=response,
                    model=model or "default",
                    metrics={"tokens": len(response.split())},  # Simple metric
                ),
            )

        return response

    def list_providers(self) -> List[str]:
        """List all registered providers"""
        return list(self.providers.keys())

    def list_models(self, provider_name: Optional[str] = None) -> Dict[str, List[str]]:
        """List all models for all providers or a specific provider"""
        if provider_name:
            provider = self.get_provider(provider_name)
            return {provider_name: provider.get_supported_models()}

        models = {}
        for name, provider in self.providers.items():
            models[name] = provider.get_supported_models()

        return models


# Example LLM provider implementation
class DummyLLMProvider(LLMProvider):
    """A dummy LLM provider for testing"""

    def generate_text(self, prompt: str, parameters: Dict[str, Any]) -> str:
        """Generate a simple echo response"""
        return f"Echo: {prompt}"

    def get_name(self) -> str:
        return "dummy"

    def get_supported_models(self) -> List[str]:
        return ["dummy-small", "dummy-medium", "dummy-large"]
