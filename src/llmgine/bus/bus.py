from typing import Dict, List, Callable, Any
from abc import ABC, abstractmethod


class Bus(ABC):
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, message_type: str, callback: Callable):
        """Subscribe to a specific message type with a callback function"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(callback)

    @abstractmethod
    def publish(self, message_type: str, data: Any):
        """Publish a message to all subscribers"""
        pass


class EventBus(Bus):
    def publish(self, event_type: str, data: Any):
        """Publish an event to all subscribers asynchronously"""
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                # In a real implementation, you might want to use asyncio or threading
                # to make this truly asynchronous
                callback(data)

        # Also publish to wildcard subscribers
        if "*" in self.subscribers:
            for callback in self.subscribers["*"]:
                callback((event_type, data))


class CommandBus(Bus):
    def publish(self, command_type: str, data: Any):
        """Execute a command synchronously with the first registered handler"""
        if command_type in self.subscribers:
            if len(self.subscribers[command_type]) > 0:
                # For commands, we usually have a single handler
                return self.subscribers[command_type][0](data)
            else:
                raise ValueError(f"No handler registered for command {command_type}")
        else:
            raise ValueError(f"Command type {command_type} not registered")


class MessageBus:
    def __init__(self):
        self.event_bus = EventBus()
        self.command_bus = CommandBus()

    def subscribe_to_event(self, event_type: str, callback: Callable):
        """Subscribe to an event"""
        self.event_bus.subscribe(event_type, callback)

    def publish_event(self, event_type: str, data: Any):
        """Publish an event"""
        self.event_bus.publish(event_type, data)

    def register_command_handler(self, command_type: str, handler: Callable):
        """Register a command handler"""
        self.command_bus.subscribe(command_type, handler)

    def execute_command(self, command_type: str, data: Any):
        """Execute a command"""
        return self.command_bus.publish(command_type, data)
