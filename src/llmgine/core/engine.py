from typing import Dict, Any, List, Optional, Callable
from .llm import LLMRouter
from .tools import ToolManager
from .context import ContextManager
from ..bus.bus import MessageBus
from ..bus.events import SystemStartedEvent, SystemShutdownEvent
import logging
import os
import threading
import signal
import time


class Engine:
    """Main engine that orchestrates all components of the llmgine"""

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        context_manager: Optional[ContextManager] = None,
        tool_manager: Optional[ToolManager] = None,
        message_bus: Optional[MessageBus] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Set up configuration
        self.config = config or {}

        # Create the message bus first so other components can use it
        self.message_bus = message_bus or MessageBus()

        # Create other components
        self.context_manager = context_manager or ContextManager(
            message_bus=self.message_bus
        )
        self.llm_router = llm_router or LLMRouter(message_bus=self.message_bus)
        self.tool_manager = tool_manager or ToolManager(message_bus=self.message_bus)

        # Set up event hooks
        self._setup_event_hooks()

        # Set up shutdown handling
        self._running = False
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

        # Store a few useful things for easy access
        self.LLM = self.llm_router
        self.Context = self.context_manager
        self.Tools = self.tool_manager

    def _setup_event_hooks(self):
        """Set up event hooks for the engine"""
        # Subscribe to system shutdown events
        self.message_bus.subscribe_to_event(
            "system.shutdown", self._handle_shutdown_event
        )

        # Subscribe to wildcard events for logging (if enabled)
        if self.config.get("enable_event_logging", False):
            self.message_bus.subscribe_to_event("*", self._log_event)

    def _log_event(self, event_data):
        """Log an event"""
        event_type, data = event_data
        self.logger.debug(f"Event: {event_type}, Data: {data}")

    def _handle_shutdown_event(self, event_data):
        """Handle a shutdown event"""
        self.logger.info(f"Shutdown requested via event: {event_data}")
        self._shutdown_requested = True

    def _handle_interrupt(self, signum, frame):
        """Handle an interrupt signal"""
        self.logger.info(f"Interrupt signal received: {signum}")
        self._shutdown_requested = True

    def start(self):
        """Start the engine"""
        if self._running:
            self.logger.warning("Engine is already running")
            return

        self._running = True
        self._shutdown_requested = False

        # Emit system started event
        self.message_bus.publish_event(
            "system.started",
            SystemStartedEvent(
                version=self.config.get("version", "0.1.0"), config=self.config
            ),
        )

        self.logger.info("Engine started")

        # Run until shutdown is requested
        try:
            while self._running and not self._shutdown_requested:
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown the engine"""
        if not self._running:
            self.logger.warning("Engine is not running")
            return

        self._running = False

        # Emit system shutdown event
        self.message_bus.publish_event(
            "system.shutdown", SystemShutdownEvent(reason="manual_shutdown")
        )

        self.logger.info("Engine shut down")

    def execute_custom_logic(self, logic_function: Callable):
        """Execute custom logic with access to engine components"""
        return logic_function(
            llm=self.llm_router,
            context=self.context_manager,
            tools=self.tool_manager,
            message_bus=self.message_bus,
        )

    def add_event_handler(self, event_type: str, handler: Callable):
        """Add an event handler"""
        self.message_bus.subscribe_to_event(event_type, handler)

    def add_command_handler(self, command_type: str, handler: Callable):
        """Add a command handler"""
        self.message_bus.register_command_handler(command_type, handler)

    def process_user_input(
        self, input_text: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Process user input"""
        # Add to chat history
        self.context_manager.add_chat_message("user", input_text, metadata)

        # Emit user input event
        self.message_bus.publish_event(
            "ui.input", {"input_text": input_text, "metadata": metadata or {}}
        )

        # The actual processing logic would typically be implemented in a
        # custom handler registered for the ui.input event

    def generate_response(self, prompt: str, **kwargs):
        """Generate a response using the LLM"""
        response = self.llm_router.generate_text(prompt, **kwargs)

        # Add to chat history
        self.context_manager.add_chat_message("assistant", response)

        # Emit display event
        self.message_bus.publish_event(
            "ui.display", {"content": response, "type": "text"}
        )

        return response
