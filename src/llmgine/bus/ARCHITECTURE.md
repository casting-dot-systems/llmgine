# Message Bus Architecture

This document provides a detailed architectural overview of the LLMgine Message Bus implementation.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Handler Resolution](#handler-resolution)
5. [Session Management](#session-management)
6. [Event Processing Pipeline](#event-processing-pipeline)
7. [Resilience Patterns](#resilience-patterns)
8. [Performance Optimizations](#performance-optimizations)
9. [Metrics and Monitoring](#metrics-and-monitoring)
10. [Extension Points](#extension-points)

## Core Concepts

### Commands vs Events

The message bus distinguishes between two fundamental message types:

**Commands**:
- Represent intentions to perform an action
- Have exactly one handler
- Return a result (success/failure + data)
- Examples: CreateUser, UpdateInventory, ProcessPayment

**Events**:
- Represent facts about what has happened
- Can have zero or more handlers
- Fire-and-forget (no return value)
- Examples: UserCreated, InventoryUpdated, PaymentProcessed

### Message Flow

```
Command Flow:
Client -> Command -> MessageBus -> Middleware -> Handler -> CommandResult

Event Flow:
Publisher -> Event -> MessageBus -> Filters -> Middleware -> Handlers (async)
```

## Component Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                         MessageBus                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Registry   │  │  Middleware  │  │  Event Queue    │  │
│  │             │  │              │  │                 │  │
│  │ - Commands  │  │ - Command    │  │ - Async queue   │  │
│  │ - Events    │  │ - Event      │  │ - Batch proc    │  │
│  │ - Sessions  │  │              │  │ - Backpressure  │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                                                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Filters    │  │ Observability│  │    Sessions     │  │
│  │             │  │              │  │                 │  │
│  │ - Type      │  │ - Logging    │  │ - Context mgr   │  │
│  │ - Session   │  │ - Metrics    │  │ - Auto cleanup  │  │
│  │ - Custom    │  │ - Events     │  │ - Scoped hdlrs  │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Class Hierarchy

```python
# Core interfaces
IMessageBus (Protocol)
├── MessageBus          # Standard implementation
└── ResilientMessageBus # With retry/circuit breaker

IRegistry (Protocol)
├── SimpleRegistry      # Default implementation
└── CustomRegistry      # User extensions

# Message types
Message (base)
├── Command
│   ├── CreateCommand
│   ├── UpdateCommand
│   └── DeleteCommand
└── Event
    ├── DomainEvent
    ├── SystemEvent
    └── IntegrationEvent
```

## Data Flow

### Command Execution Flow

```python
# 1. Client creates command
cmd = CreateUserCommand(username="alice", email="alice@example.com")

# 2. Bus routes to handler through middleware
result = await bus.execute(cmd)
```

Internally:
```
execute(cmd)
  ├── Validate command type
  ├── Find handler in registry
  ├── Apply command middleware chain
  ├── Execute handler
  ├── Publish CommandStartedEvent
  ├── Publish CommandResultEvent
  └── Return CommandResult
```

### Event Publishing Flow

```python
# 1. Publisher creates event
event = UserCreatedEvent(user_id="123", username="alice")

# 2. Bus queues event for async processing
await bus.publish(event)
```

Internally:
```
publish(event)
  ├── Apply event filters
  ├── Queue event (with backpressure handling)
  └── Return immediately (fire-and-forget)

process_events() [async loop]
  ├── Batch events from queue
  ├── Group by type
  ├── Find handlers in registry
  ├── Apply event middleware
  ├── Execute handlers concurrently
  └── Handle errors (log, continue)
```

## Handler Resolution

The registry uses a two-level lookup system:

### Command Handlers

```python
# Registration priority:
# 1. Session-specific handler
# 2. Bus-level handler

registry[session_id][CommandType] -> handler
registry["BUS"][CommandType] -> handler
```

### Event Handlers

```python
# All matching handlers are called:
# 1. Session-specific handlers (if session matches)
# 2. Bus-level handlers

handlers = []
handlers.extend(registry[event.session_id][EventType])
handlers.extend(registry["BUS"][EventType])

# Sort by priority and execute
```

## Session Management

Sessions provide scoped handler registration with automatic cleanup:

### Session Lifecycle

```python
async with bus.session("job-123") as session:
    # 1. Create session
    #    - Generate session ID
    #    - Initialize session registry
    #    - Publish SessionStartEvent
    
    # 2. Use session
    session.register_command_handler(ProcessItem, handler)
    await session.execute(ProcessItemCommand())
    
    # 3. Cleanup (automatic)
    #    - Unregister all session handlers
    #    - Clear session state
    #    - Publish SessionEndEvent
```

### Session Internals

```python
class BusSession:
    def __init__(self, bus: IMessageBus, session_id: SessionID):
        self.bus = bus
        self.session_id = session_id
        self._cleanup_tasks = []
    
    async def __aenter__(self):
        await self.bus.publish(SessionStartEvent(session_id=self.session_id))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Unregister all handlers
        self.bus.registry.unregister_session(self.session_id)
        await self.bus.publish(SessionEndEvent(session_id=self.session_id))
```

## Event Processing Pipeline

### Batch Processing

Events are processed in batches for efficiency:

```python
# Configuration
batch_size = 100      # Max events per batch
batch_timeout = 0.1   # Max wait time (seconds)

# Processing loop
async def _process_events(self):
    while self._running:
        batch = await self._collect_batch()
        if batch:
            await self._process_batch(batch)
```

### Concurrent Execution

Event handlers execute concurrently within priority groups:

```python
# Group handlers by priority
priority_groups = defaultdict(list)
for handler in handlers:
    priority_groups[handler.priority].append(handler)

# Execute priority groups in order
for priority in sorted(priority_groups.keys(), reverse=True):
    group_handlers = priority_groups[priority]
    await asyncio.gather(
        *[handler(event) for handler in group_handlers],
        return_exceptions=True
    )
```

## Resilience Patterns

### Retry Logic

The ResilientMessageBus implements exponential backoff with jitter:

```python
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 0.1
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True

# Retry calculation
delay = min(
    config.initial_delay * (config.exponential_base ** attempt),
    config.max_delay
)
if config.jitter:
    delay *= random.uniform(0.5, 1.5)
```

### Circuit Breaker

Prevents cascading failures by failing fast:

```python
class CircuitBreaker:
    # States: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    
    async def call(self, func):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError()
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

### Dead Letter Queue

Captures permanently failed commands:

```python
class DeadLetterEntry:
    command: Command
    error: str
    attempts: int
    first_attempted: datetime
    last_attempted: datetime

# After max retries exceeded
if attempts > config.max_retries:
    await self._add_to_dead_letter(command, error)
    return CommandResult(
        success=False,
        error=f"Command failed after {attempts} attempts",
        metadata={"dead_letter": True}
    )
```

## Performance Optimizations

### Event Batching

Events are collected and processed in batches:

```python
async def _collect_batch(self) -> List[Event]:
    batch = []
    deadline = time.time() + self.batch_timeout
    
    while len(batch) < self.batch_size:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
            
        try:
            event = await asyncio.wait_for(
                self._event_queue.get(),
                timeout=remaining
            )
            batch.append(event)
        except asyncio.TimeoutError:
            break
    
    return batch
```

### Handler Caching

Registry lookups are optimized with caching:

```python
# Cache handler lookups
@lru_cache(maxsize=1024)
def _get_handler_key(
    message_type: Type[Message],
    session_id: SessionID
) -> HandlerKey:
    return (message_type.__name__, session_id)
```

### Backpressure Strategies

Three strategies for handling queue overflow:

1. **DROP_OLDEST**: Maintains newest events
2. **REJECT_NEW**: Preserves event order
3. **ADAPTIVE_RATE_LIMIT**: Dynamically adjusts acceptance rate

```python
class BoundedEventQueue:
    async def put(self, item: Event) -> bool:
        if self._queue.full():
            if self.strategy == BackpressureStrategy.DROP_OLDEST:
                self._queue.get_nowait()  # Drop oldest
                self._dropped_count += 1
            elif self.strategy == BackpressureStrategy.REJECT_NEW:
                self._rejected_count += 1
                return False
            elif self.strategy == BackpressureStrategy.ADAPTIVE_RATE_LIMIT:
                self._rate_limit *= 1.5  # Increase delay
                return False
        
        await self._queue.put(item)
        return True
```

## Metrics and Monitoring

### Metrics Architecture

The bus provides comprehensive metrics collection with minimal performance impact:

```
┌─────────────────────────────────────────────────────────────┐
│                     MetricsCollector                        │
├─────────────────────────────────────────────────────────────┤
│ Counters:                                                   │
│ - events_published_total                                    │
│ - events_processed_total                                    │
│ - events_failed_total                                       │
│ - commands_sent_total                                       │
│ - commands_processed_total                                  │
│ - commands_failed_total                                     │
├─────────────────────────────────────────────────────────────┤
│ Histograms:                                                 │
│ - event_processing_duration_seconds                         │
│ - command_processing_duration_seconds                       │
├─────────────────────────────────────────────────────────────┤
│ Gauges:                                                     │
│ - queue_size                                                │
│ - backpressure_active                                       │
│ - circuit_breaker_state                                     │
│ - dead_letter_queue_size                                    │
│ - active_sessions                                           │
│ - registered_handlers                                       │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

Metrics are collected at key points in the message flow:

1. **Command Execution**:
   - Increment `commands_sent_total` on execute()
   - Time execution with `command_processing_duration_seconds`
   - Update `commands_processed_total` or `commands_failed_total`

2. **Event Publishing**:
   - Increment `events_published_total` on publish()
   - Update `queue_size` gauge

3. **Event Processing**:
   - Time handler execution with `event_processing_duration_seconds`
   - Update `events_processed_total` or `events_failed_total`

4. **Resilience Features**:
   - Track `circuit_breaker_state` transitions
   - Monitor `dead_letter_queue_size`
   - Update `backpressure_active` on threshold crossing

### Performance Considerations

Metrics collection is designed for minimal overhead:

- **Lock-free counters**: Simple atomic increments
- **Sampling support**: Histograms can be sampled in production
- **Lazy calculation**: Percentiles computed only on request
- **Context managers**: Zero-allocation timing with `Timer`

### Export Formats

The metrics can be exported in various formats:

```python
# Prometheus format
events_published_total 1000
command_processing_duration_seconds_bucket{le="0.01"} 200
command_processing_duration_seconds_bucket{le="0.05"} 700

# JSON format (for custom dashboards)
{
    "timestamp": "2024-01-20T10:30:00Z",
    "counters": {...},
    "histograms": {...},
    "gauges": {...}
}
```

## Extension Points

### Custom Middleware

```python
class TimingMiddleware:
    async def __call__(self, message: Message, next_handler):
        start = time.time()
        try:
            result = await next_handler(message)
            return result
        finally:
            duration = time.time() - start
            logger.info(f"{message.__class__.__name__} took {duration:.3f}s")
```

### Custom Filters

```python
class RateLimitFilter:
    def __init__(self, max_per_second: int):
        self.max_per_second = max_per_second
        self.window = []
    
    async def __call__(self, event: Event) -> bool:
        now = time.time()
        self.window = [t for t in self.window if now - t < 1.0]
        
        if len(self.window) >= self.max_per_second:
            return False  # Reject event
        
        self.window.append(now)
        return True  # Accept event
```

### Custom Registry

```python
class PersistentRegistry(IRegistry):
    """Registry that persists handlers to database."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self._cache = {}
    
    def register_command_handler(self, command_type, handler, session_id):
        # Save to database
        self.db.save_handler(command_type, handler, session_id)
        # Update cache
        self._cache[(command_type, session_id)] = handler
```

## Thread Safety

The message bus is designed for concurrent use:

- **Singleton Pattern**: Thread-safe instance creation
- **Asyncio Queues**: Handle concurrent access
- **Immutable Messages**: No shared mutable state
- **Session Isolation**: Each session has its own registry namespace

## Error Handling Philosophy

1. **Commands**: Errors are captured and returned in CommandResult
2. **Events**: Errors are logged but don't stop other handlers
3. **Middleware**: Can intercept and handle errors
4. **Resilience**: Automatic retry with backoff for transient failures

## Future Considerations

1. **Distributed Bus**: Multi-node message bus with network transport
2. **Persistence**: Durable message queues for reliability
3. **Monitoring**: Built-in metrics and tracing
4. **Schema Evolution**: Versioned message schemas
5. **Security**: Message encryption and authentication