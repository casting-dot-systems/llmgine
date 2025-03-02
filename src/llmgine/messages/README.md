# LLMgine Message System

This package implements a lightweight command and event system for the LLMgine project, following clean architecture and domain-driven design principles.

## Overview

The message system is built on two core concepts:

1. **Commands**: Represent intentions to change the system state. Each command has exactly one handler.
2. **Events**: Represent things that have happened in the system. Multiple subscribers can react to events.

This implementation uses a message bus to decouple consumers and producers of messages, following the Command Query Responsibility Segregation (CQRS) pattern.

## Components

### Message Bus (`bus.py`)

- Single entry point for command dispatching and event emission
- Implements a singleton pattern to ensure a single instance throughout the application
- Supports both synchronous and asynchronous operations
- Manages pending events from command handlers

### Commands (`commands.py`)

- Base `Command` class for all commands
- Concrete command implementations for common operations
- Each command represents a clear intention to change state

### Events (`events.py`)

- Base `Event` class for all events
- Event type hierarchy for different domains (resources, workflows, system)
- Events include metadata like timestamps and unique IDs

### Handlers (`handlers.py`)

- Command handlers that process commands and produce events
- Event subscribers that react to specific event types
- Handler registration mechanism

## Usage

### Basic Usage

```python
from llmgine.messages.bus import message_bus
from llmgine.messages.commands import CreateResourceCommand
from llmgine.messages.handlers import register_handlers

# Register all handlers
register_handlers()

# Create and dispatch a command
command = CreateResourceCommand(
    resource_type="example", 
    resource_data={"name": "Example Resource"}
)
resource_id = message_bus.dispatch(command)
```

### Asynchronous Usage

```python
import asyncio
from llmgine.messages.bus import message_bus
from llmgine.messages.commands import UpdateResourceCommand

async def update_resource():
    command = UpdateResourceCommand(
        resource_id="res_123",
        resource_type="example",
        resource_data={"name": "Updated Resource"}
    )
    await message_bus.dispatch_async(command)

asyncio.run(update_resource())
```

### Custom Command Handlers

```python
from llmgine.messages.bus import message_bus
from llmgine.messages.commands import Command
from dataclasses import dataclass

@dataclass
class CustomCommand(Command):
    parameter: str

def handle_custom_command(command):
    # Implement command handling logic
    print(f"Handling custom command with parameter: {command.parameter}")
    
    # Add events to the message bus if needed
    message_bus.add_pending_event(some_event)
    
    return True

# Register handler
message_bus.register_command(CustomCommand, handle_custom_command)
```

### Event Subscribers

```python
from llmgine.messages.bus import message_bus
from llmgine.messages.events import ResourceCreatedEvent

def on_resource_created(event: ResourceCreatedEvent):
    print(f"Resource created: {event.resource_id}")

# Subscribe to event
message_bus.subscribe_event("resource.created", on_resource_created)
```

## Best Practices

1. **Keep commands and events immutable**: Once created, they should not be modified
2. **Use descriptive naming**: Command and event names should clearly indicate their purpose
3. **Follow single responsibility**: Each command should do exactly one thing
4. **Validate input early**: Validate command data before processing
5. **Handle errors appropriately**: Use proper error handling in command handlers
6. **Use value objects**: Where appropriate, use value objects within commands and events
7. **Implement idempotency**: Commands should be designed to be idempotent when possible
8. **Design for eventual consistency**: Events may be processed asynchronously
9. **Don't share state**: Command handlers and event subscribers should be stateless

## Examples

See `example.py` for complete usage examples of the message system. 