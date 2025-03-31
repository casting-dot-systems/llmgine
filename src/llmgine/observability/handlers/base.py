"""Base class for observability event handlers."""

from abc import ABC, abstractmethod
from typing import Any

from llmgine.observability.events import ObservabilityBaseEvent


class ObservabilityEventHandler(ABC):
    """Base class for handlers that process observability events from the MessageBus."""

    def __init__(self, **kwargs: Any) -> None:
        # Allow for configuration parameters
        pass

    @abstractmethod
    async def handle(self, event: ObservabilityBaseEvent) -> None:
        """Process an incoming observability event.

        Args:
            event: The event received from the MessageBus.
        """
        pass

    def __repr__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}()" 