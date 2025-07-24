"""Bootstrap utilities for application initialization.

Provides a way to bootstrap the application components including
the observability bus and the message bus.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Generic, Optional, Type, TypeVar

from llmgine.bus.bus import MessageBus
from llmgine.bus.session import BusSession
from llmgine.messages.commands import Command
from llmgine.messages.events import Event
from llmgine.observability.events import LogLevel
from llmgine.observability.manager import ObservabilityManager
from llmgine.observability.handlers.adapters import (
    create_sync_console_handler,
    create_sync_file_handler,
)

logger = logging.getLogger(__name__)

# Type definitions
TConfig = TypeVar("TConfig")


# --- Basic Logging Setup Function ---
def setup_basic_logging(level: LogLevel = LogLevel.INFO):
    """Configure basic Python logging to the console."""
    log_level_map = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }
    logging_level = log_level_map.get(level, logging.INFO)

    # Configure logging with session_id support
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        # stream=sys.stdout # Optionally direct to stdout instead of stderr
    )

    logger.info(f"Basic logging configured with level {logging_level}")


@dataclass
class ApplicationConfig:
    """Base configuration for applications."""

    # General application config
    name: str = "application"
    description: str = "application description"

    # --- Standard Logging Config ---
    # Controls standard Python logging setup (not MessageBus handlers)
    log_level: LogLevel = LogLevel.INFO

    # --- Observability Handler Config ---
    enable_console_handler: bool = True
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs"
    file_handler_log_filename: Optional[str] = None  # Default: timestamped events.jsonl
    # custom_handlers: List[ObservabilityEventHandler] = field(default_factory=list) # For adding other handlers


class ApplicationBootstrap(Generic[TConfig]):
    """Bootstrap for application initialization.

    Handles setting up the message bus and registering configured
    observability event handlers.
    """

    def __init__(self, config: TConfig = ApplicationConfig()):
        """Initialize the bootstrap.

        Args:
            config: Application configuration
        """
        self.config = config

        # --- Configure Standard Logging ---
        # Get log level from config, default to INFO
        log_level_config = getattr(self.config, "log_level", LogLevel.INFO)
        setup_basic_logging(level=log_level_config)
        # --- End Logging Config ---

        # --- Initialize ObservabilityManager ---
        self.observability = ObservabilityManager()
        
        # --- Initialize MessageBus with ObservabilityManager ---
        self.message_bus = MessageBus(observability=self.observability)

    async def bootstrap(self) -> None:
        """Bootstrap the application.

        Starts the message bus, and registers handlers.
        """
        logger.info(
            "Application bootstrap started", extra={"component": "ApplicationBootstrap"}
        )

        # Start message bus
        await self.message_bus.start()

        # Register command and event handlers
        self._register_observability_handlers()
        self._register_command_handlers()
        self._register_event_handlers()

        logger.info(
            "Application bootstrap completed", extra={"component": "ApplicationBootstrap"}
        )

    async def shutdown(self) -> None:
        """Shutdown the application components."""
        # Close the primary session (using __aexit__ since it's an async context manager)
        if hasattr(self, "primary_session") and self.primary_session._active:
            await self.primary_session.__aexit__(None, None, None)

        # Stop message bus
        await self.message_bus.stop()

        logger.info(
            "Application shutdown complete", extra={"component": "ApplicationBootstrap"}
        )

    def _register_observability_handlers(self) -> None:
        """Register observability handlers with the ObservabilityManager."""
        if self.config.enable_console_handler:
            self.observability.register_handler(create_sync_console_handler())
        if self.config.enable_file_handler:
            log_dir = getattr(self.config, 'file_handler_log_dir', 'logs')
            filename = getattr(self.config, 'file_handler_log_filename', None)
            self.observability.register_handler(
                create_sync_file_handler(log_dir=log_dir, filename=filename)
            )

    def _register_command_handlers(self) -> None:
        """Register command handlers with the message bus.

        Override this method to register your engine's command handlers.
        """
        pass

    def _register_event_handlers(self) -> None:
        """Register event handlers with the message bus.

        Override this method to register your engine's event handlers.
        """
        pass

    def register_command_handler(
        self, command_type: Type[Command], handler: Callable
    ) -> None:
        """Register a command handler with the message bus.

        Args:
            command_type: The type of command to handle
            handler: The function that handles the command
        """
        # Use the primary session as the default
        self.primary_session.register_command_handler(command_type, handler)

    def register_event_handler(self, event_type: Type[Event], handler: Callable) -> None:
        """Register an event handler with the message bus.

        Args:
            event_type: The type of event to handle
            handler: The function that handles the event
        """
        # Use the primary session as the default
        self.primary_session.register_event_handler(event_type, handler)

    def create_session(self) -> BusSession:
        """Create a new session for session-specific handlers.

        Returns:
            A new BusSession that can be used as a context manager
        """
        return self.message_bus.create_session()


class CommandBootstrap(ApplicationBootstrap[TConfig]):
    """Legacy bootstrap class for backward compatibility."""

    pass
