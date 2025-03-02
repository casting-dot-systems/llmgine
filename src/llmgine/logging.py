from loguru import logger as loguru_logger
from datetime import datetime
from .messages.bus import message_bus
from .messages.events import Event
from .messages.commands import Command

class LoggingHandler:
    def __init__(self, log_file: str = "logs/workflows.log", rotation: str = "500 MB"):
        loguru_logger.add(log_file, rotation=rotation)
        self.logger = loguru_logger
        self.subscribe()

    def subscribe(self):
        message_bus.subscribe_event("*", self.handle_any_event)

    def handle_event(self, event: Event):
        log_data = {"event_type": event.event_type, "timestamp": datetime.now().isoformat(), **event.data}
        self.logger.info(f"Event: {event.event_type} | {log_data}")

    def handle_any_event(self, event: Event):
        if event.event_type not in message_bus._event_subscribers or len(message_bus._event_subscribers[event.event_type]) == 1:
            log_data = {"event_type": event.event_type, "timestamp": datetime.now().isoformat(), **event.data}
            self.logger.warning(f"Unhandled event: {event.event_type} | {log_data}")

    def log_command(self, command: Command):
        command_type = type(command).__name__
        log_data = {"command": str(command), "timestamp": datetime.now().isoformat()}
        self.logger.info(f"Command: {command_type} | {log_data}")
        message_bus._command_handlers[type(command)](command)

# Initialize logging
logger = LoggingHandler()