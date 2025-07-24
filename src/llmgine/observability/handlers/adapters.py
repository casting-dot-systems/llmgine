"""Adapters to make async handlers work with the synchronous ObservabilityManager."""

import asyncio
from typing import Any

from llmgine.messages.events import Event
from llmgine.observability.handlers.base import ObservabilityEventHandler
from llmgine.observability.handlers.console_sync import SyncConsoleEventHandler
from llmgine.observability.handlers.file_sync import SyncFileEventHandler
from llmgine.observability.manager import ObservabilityHandler


class AsyncHandlerAdapter(ObservabilityHandler):
    """Adapter to make async ObservabilityEventHandler work with sync ObservabilityManager."""
    
    def __init__(self, async_handler: ObservabilityEventHandler):
        """Initialize with an async handler.
        
        Args:
            async_handler: The async handler to adapt
        """
        self._async_handler = async_handler
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def handle(self, event: Event) -> None:
        """Handle event synchronously by running async handler in event loop.
        
        Args:
            event: The event to handle
        """
        # Try to get the current running loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            asyncio.create_task(self._async_handler.handle(event))
        except RuntimeError:
            # No running loop, run synchronously
            asyncio.run(self._async_handler.handle(event))


# Convenience functions to create sync versions of handlers
def create_sync_console_handler(**kwargs: Any) -> SyncConsoleEventHandler:
    """Create a synchronous console event handler.
    
    Args:
        **kwargs: Configuration options
        
    Returns:
        A synchronous console handler
    """
    return SyncConsoleEventHandler(**kwargs)


def create_sync_file_handler(log_dir: str = "logs", filename: str | None = None, **kwargs: Any) -> SyncFileEventHandler:
    """Create a synchronous file event handler.
    
    Args:
        log_dir: Directory for log files
        filename: Optional specific filename
        **kwargs: Additional configuration options
        
    Returns:
        A synchronous file handler
    """
    return SyncFileEventHandler(log_dir=log_dir, filename=filename, **kwargs)
