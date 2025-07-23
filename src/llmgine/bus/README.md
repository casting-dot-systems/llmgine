# Message Bus

A clean, production-ready async message bus implementation for handling commands and events in Python applications.

## Overview

The LLMgine Message Bus provides a robust foundation for building event-driven architectures with clear separation between commands (operations to perform) and events (things that happened). It features automatic session management, middleware support, resilience patterns, and comprehensive observability.

## Key Features

- **Async-First Design**: Built on Python's asyncio for high-performance concurrent operations
- **Clean Architecture**: Clear separation between commands and events with type-safe handlers
- **Session Management**: Automatic cleanup of session-scoped handlers with context managers
- **Middleware Pipeline**: Extensible middleware for cross-cutting concerns
- **Resilience Patterns**: Built-in retry logic, circuit breakers, and dead letter queues
- **Backpressure Handling**: Configurable strategies for managing high load
- **Event Batching**: Efficient batch processing with configurable size and timeout
- **Observability**: Automatic event logging and metrics collection
- **Type Safety**: Full type hints and runtime validation with Pydantic

## Architecture

### Core Components

1. **MessageBus**: The main entry point for command execution and event publishing
2. **Commands**: Represent operations to perform (handled by exactly one handler)
3. **Events**: Represent things that happened (can have multiple listeners)
4. **Sessions**: Provide scoped handler registration with automatic cleanup
5. **Registry**: Manages handler registration and lookup with proper scoping

### Handler Scopes

The bus uses two clear scopes for handler registration:

- **Bus Scope**: Handlers persist for the lifetime of the bus (application-wide)
- **Session Scope**: Handlers are automatically cleaned up when the session ends

## Installation

The message bus is part of the LLMgine framework:

```bash
pip install llmgine
```

## Basic Usage

### Simple Command/Event Example

```python
from dataclasses import dataclass
from llmgine.bus import MessageBus
from llmgine.messages import Command, CommandResult, Event

# Define a command
@dataclass
class CreateUserCommand(Command):
    username: str
    email: str

# Define an event
@dataclass
class UserCreatedEvent(Event):
    user_id: str
    username: str

# Command handler
async def handle_create_user(cmd: CreateUserCommand) -> CommandResult:
    # Business logic here
    user_id = await create_user_in_db(cmd.username, cmd.email)
    
    # Publish event for other systems
    event = UserCreatedEvent(
        user_id=user_id,
        username=cmd.username,
        session_id=cmd.session_id
    )
    await bus.publish(event)
    
    return CommandResult(
        success=True,
        command_id=cmd.command_id,
        result={"user_id": user_id}
    )

# Event handler
async def send_welcome_email(event: UserCreatedEvent) -> None:
    await email_service.send_welcome(event.user_id)

# Usage
async def main():
    bus = MessageBus()
    await bus.start()
    
    # Register handlers
    bus.register_command_handler(CreateUserCommand, handle_create_user)
    bus.register_event_handler(UserCreatedEvent, send_welcome_email)
    
    # Execute command
    cmd = CreateUserCommand(username="alice", email="alice@example.com")
    result = await bus.execute(cmd)
    
    await bus.stop()
```

### Session Management

```python
# Sessions provide scoped handler registration
async def process_import_job(job_id: str):
    bus = MessageBus()
    await bus.start()
    
    # Create session for this import job
    async with bus.session(f"import-{job_id}") as session:
        # Register job-specific handlers
        session.register_event_handler(
            RowProcessedEvent,
            lambda e: update_progress(job_id, e.row_count)
        )
        
        # Process the import
        for batch in read_import_file(job_id):
            cmd = ProcessBatchCommand(
                batch_data=batch,
                session_id=session.session_id
            )
            await session.execute(cmd)
        
    # Session handlers automatically cleaned up here
```

### Middleware

```python
from llmgine.bus.middleware import LoggingMiddleware, MetricsMiddleware

# Add middleware for all commands
bus.add_command_middleware(LoggingMiddleware())
bus.add_command_middleware(MetricsMiddleware())

# Custom middleware
class ValidationMiddleware:
    async def __call__(self, cmd: Command, next_handler):
        # Validate command before execution
        if not is_valid(cmd):
            raise ValueError("Invalid command")
        return await next_handler(cmd)

bus.add_command_middleware(ValidationMiddleware())
```

### Event Filters

```python
# Only process events matching certain criteria
from llmgine.bus.filters import TypeFilter, SessionFilter

# Only handle specific event types
bus.add_event_filter(
    TypeFilter(allowed_types=[UserCreatedEvent, UserUpdatedEvent])
)

# Only handle events from specific sessions
bus.add_event_filter(
    SessionFilter(allowed_sessions=["import-123", "import-456"])
)
```

## Advanced Features

### Resilient Message Bus

For production systems requiring fault tolerance:

```python
from llmgine.bus.resilience import ResilientMessageBus, RetryConfig

bus = ResilientMessageBus(
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=3
    ),
    max_dead_letter_size=1000
)

# Failed commands are automatically retried
# Circuit breakers prevent cascading failures
# Dead letter queue captures permanently failed commands
```

### Backpressure Handling

Manage high load with configurable strategies:

```python
from llmgine.bus.backpressure import BackpressureStrategy

bus = ResilientMessageBus(
    event_queue_size=10000,
    backpressure_strategy=BackpressureStrategy.ADAPTIVE_RATE_LIMIT
)

# Available strategies:
# - DROP_OLDEST: Drop oldest events when queue is full
# - REJECT_NEW: Reject new events when queue is full
# - ADAPTIVE_RATE_LIMIT: Dynamically adjust acceptance rate
```

### Event Priorities

Control event processing order:

```python
# Higher priority handlers execute first
bus.register_event_handler(
    CriticalEvent,
    handle_critical,
    priority=100  # Default is 50
)

bus.register_event_handler(
    CriticalEvent,
    handle_logging,
    priority=10  # Runs after critical handler
)
```

### Batch Processing

Configure event batching for performance:

```python
bus = MessageBus(
    batch_size=100,      # Process up to 100 events at once
    batch_timeout=0.1    # Or after 100ms timeout
)
```

## Testing

The bus includes utilities for testing:

```python
from llmgine.bus.testing import FakeMessageBus

async def test_user_creation():
    # Use fake bus for testing
    bus = FakeMessageBus()
    
    # Register handler
    bus.register_command_handler(CreateUserCommand, handle_create_user)
    
    # Execute command
    cmd = CreateUserCommand(username="test", email="test@example.com")
    result = await bus.execute(cmd)
    
    # Verify result
    assert result.success
    assert "user_id" in result.result
    
    # Check published events
    events = bus.get_published_events(UserCreatedEvent)
    assert len(events) == 1
    assert events[0].username == "test"
```

## Performance Considerations

1. **Batch Size**: Larger batches improve throughput but increase latency
2. **Queue Size**: Balance memory usage with burst capacity
3. **Handler Performance**: Keep handlers fast; offload heavy work to background tasks
4. **Session Cleanup**: Use sessions appropriately to avoid memory leaks
5. **Event Volume**: Use filters to reduce unnecessary event processing

## Best Practices

1. **Command/Event Naming**: Use clear, action-oriented names (CreateUser, UserCreated)
2. **Handler Idempotency**: Design handlers to be safely retryable
3. **Error Handling**: Let exceptions bubble up; the bus handles retry logic
4. **Event Granularity**: Prefer fine-grained events for flexibility
5. **Session Usage**: Use sessions for request-scoped or job-scoped operations
6. **Middleware Order**: Add middleware in order of execution priority
7. **Type Safety**: Always use proper type hints for better IDE support

## Migration from Legacy Bus

If migrating from the old bus implementation:

1. Replace `ROOT` session references with `BUS` or proper session IDs
2. Remove any backward compatibility imports
3. Update handler registration to use the new scoping model
4. Test thoroughly as the new implementation has stricter validation

## See Also

- [Full API Documentation](./api.md)
- [Architecture Deep Dive](./ARCHITECTURE.md)
- [Examples](./examples/)
- [Contributing Guide](../../CONTRIBUTING.md)