# Event-Driven Architecture in LLMgine

LLMgine is built on a robust event-driven architecture centered around two primary buses:

1. **ObservabilityBus** - Manages logging, metrics, and tracing across the application
2. **MessageBus** - Handles command execution and event distribution

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    Application Bootstrap                    │
│                                                             │
└───────────────────┬─────────────────────┬─────────────────┘
                    │                     │
    ┌───────────────▼───────────────┐     │
    │                               │     │
    │       ObservabilityBus        │     │
    │                               │     │
    └───────────────┬───────────────┘     │
                    │                     │
    ┌───────────────▼───────────────┐     │
    │                               │     │
    │         MessageBus            │◄────┘
    │                               │
    └───────────────────────────────┘
```

### ObservabilityBus

The ObservabilityBus serves as the foundation for all observability concerns, including:

- **Logging**: Structured log events with levels, context, and source information
- **Metrics**: Numerical measurements with units and dimensions
- **Tracing**: Distributed tracing capabilities for request flows

### MessageBus

The MessageBus is responsible for:

- **Command Processing**: Executing commands via registered handlers
- **Event Publishing**: Distributing events to all interested subscribers
- **Integrated Observability**: Automatically logging all events to a JSONL file, generating command execution traces, and optionally logging metrics/traces to the console.

## Event Flow

```
┌─────────────┐
│             │  Command     ┌──────────────┐      Result      ┌─────────────┐
│   Client    ├─────────────►│  MessageBus  ├─────────────────►│  Handler    │
│             │              └──────┬───────┘                  └──────┬──────┘
└─────────────┘                     │                                 │
                                    │ CommandEvent                    │
                                    ▼                                 │
                          ┌──────────────────┐                       │
                          │                  │◄──────────────────────┘
                          │ ObservabilityBus │  CommandResultEvent
                          │                  │
                          └─────────┬────────┘
                                    │ 
                                    │ Logs, Metrics, Traces
                                    ▼
                          ┌──────────────────┐
                          │  Storage/Output  │
                          └──────────────────┘
```

## Commands and Events

### Commands

Commands represent intentions to perform actions:

```python
@dataclass
class Command:
    """Base class for all commands."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Each command has a single handler and produces a result:

```python
@dataclass
class CommandResult:
    """Result of command execution."""
    
    command_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Events

Events represent things that have happened:

```python
@dataclass
class Event:
    """Base class for all events."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Events have zero or more handlers.

## Integration Example

Here's how to use the event-driven architecture in your application:

```python
from llmgine.bootstrap import ApplicationBootstrap
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

# Define your commands
@dataclass
class MyCommand(Command):
    param1: str
    param2: int

# Define your events
@dataclass
class MyEvent(Event):
    data: str

# Create your application
class MyApplication(ApplicationBootstrap):
    def _register_command_handlers(self):
        self.register_command_handler(MyCommand, self.handle_my_command)
    
    def _register_event_handlers(self):
        self.register_event_handler(MyEvent, self.handle_my_event)
    
    def handle_my_command(self, command: MyCommand) -> CommandResult:
        # Process the command
        return CommandResult(
            command_id=command.id,
            success=True,
            result="Command processed"
        )
    
    def handle_my_event(self, event: MyEvent) -> None:
        # Process the event
        self.obs_bus.log(LogLevel.INFO, f"Event handled: {event.data}")
```

## Initialization

The application bootstrap initializes both buses in the correct order:

```python
# Initialize the application
app = MyApplication()

# Start everything
await app.bootstrap()

# Execute commands
result = await app.message_bus.execute(MyCommand(param1="value", param2=42))

# Publish events
await app.message_bus.publish(MyEvent(data="Something happened"))

# When done
await app.shutdown()
```

## Benefits

This event-driven architecture provides several benefits:

1. **Loose Coupling**: Components communicate via messages, not direct dependencies
2. **Observability**: All operations are automatically logged, measured, and traced
3. **Extensibility**: New handlers can be registered for existing commands and events
4. **Testability**: Easy to test components in isolation
5. **Resilience**: Failures in one component don't necessarily impact others