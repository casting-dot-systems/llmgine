# Observability Module

The observability module provides a standalone, extensible system for monitoring and tracing events in the LLMgine framework without creating circular dependencies or performance overhead.

## Architecture Overview

The observability system is designed with the following principles:

1. **Standalone Operation**: The `ObservabilityManager` operates independently of the message bus to avoid circular dependencies
2. **Direct Integration**: The message bus calls the observability manager directly, not through event publishing
3. **Synchronous Handlers**: All observability handlers are synchronous (see [Performance Considerations](#performance-considerations))
4. **Extensible Design**: New handlers can be easily added by implementing the `ObservabilityHandler` interface

### Current Limitations

⚠️ **Important**: The current implementation uses synchronous handlers that block the caller. This is suitable for development and low-volume scenarios but can cause performance issues in production. See [Planned Improvements](#planned-improvements) for the roadmap to address this.

## Components

### ObservabilityManager

The central component that manages all observability handlers:

```python
from llmgine.observability.manager import ObservabilityManager

# Create manager
observability = ObservabilityManager()

# Register handlers
observability.register_handler(handler)

# Observe events (called by message bus)
observability.observe_event(event)

# Control observability
observability.set_enabled(False)  # Disable temporarily
```

### Handlers

#### Built-in Handlers

1. **SyncConsoleEventHandler**: Logs event summaries to console
2. **SyncFileEventHandler**: Logs events to JSONL files
3. **OpenTelemetryHandler**: Maps events to OpenTelemetry traces and spans

#### Creating Custom Handlers

```python
from llmgine.observability.manager import ObservabilityHandler
from llmgine.messages.events import Event

class MyCustomHandler(ObservabilityHandler):
    def handle(self, event: Event) -> None:
        # Process event synchronously
        print(f"Observed: {event}")
```

### Integration with Message Bus

The message bus is initialized with an ObservabilityManager:

```python
from llmgine.bus.bus import MessageBus
from llmgine.observability.manager import ObservabilityManager

# Create observability
observability = ObservabilityManager()
observability.register_handler(SyncFileEventHandler())

# Create message bus with observability
bus = MessageBus(observability=observability)
```

## OpenTelemetry Integration

The OpenTelemetryHandler provides automatic tracing for LLMgine applications:

### Installation

```bash
pip install llmgine[opentelemetry]
```

### Event Mapping

- `SessionStartEvent` → New trace
- `CommandStartedEvent` → New span
- `CommandResultEvent` → End span with status
- `LLMCallEvent` → LLM operation span
- `ToolExecuteResultEvent` → Tool execution span
- `EventHandlerFailedEvent` → Record exception

### Usage

```python
from llmgine.observability.otel_handler import OpenTelemetryHandler

# Create and register handler
otel_handler = OpenTelemetryHandler(service_name="my-llm-app")
observability.register_handler(otel_handler)
```

## Bootstrap Integration

The ApplicationBootstrap automatically sets up observability:

```python
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig

config = ApplicationConfig(
    enable_console_handler=True,
    enable_file_handler=True,
    file_handler_log_dir="logs"
)

bootstrap = ApplicationBootstrap(config)
await bootstrap.bootstrap()  # Observability is configured automatically
```

## Benefits

1. **No Circular Dependencies**: Observability doesn't use the message bus
2. **Better Performance**: No additional events are published for observability
3. **Cleaner Architecture**: Clear separation of concerns
4. **Easy Testing**: Handlers can be tested independently
5. **Flexible Configuration**: Enable/disable handlers as needed

## Performance Considerations

### Current Implementation Trade-offs

| Aspect | Development Impact | Production Impact |
|--------|-------------------|-------------------|
| **Synchronous I/O** | Negligible on local machines | Can cause event loop stalls and latency spikes |
| **No Batching** | Fine for tens of events/sec | Lock contention and overhead at hundreds of events/sec |
| **AsyncHandlerAdapter** | Works but creates new loop per event | High CPU overhead, potential deadlocks |
| **No Sampling** | All events logged | Storage and processing costs scale linearly |

### When to Use Current Implementation

✅ **Good for:**
- Development and testing environments
- CLI tools and scripts
- Low-volume applications (<100 events/sec)
- Jupyter notebooks (avoids event loop conflicts)

❌ **Not recommended for:**
- High-throughput production services
- Latency-sensitive applications
- Services with bursty event patterns

## Planned Improvements

### Phase 1: Queue-Based Architecture (Story 1.2)
Implement a non-blocking queue pattern while maintaining the current API:

```
Message Bus → ObservabilityManager.observe_event() → Queue (non-blocking)
                                                         ↓
                                                   Worker Thread(s)
                                                         ↓
                                                   Sync Handlers
```

**Benefits:**
- Zero blocking in the event loop
- Configurable back-pressure handling
- Graceful shutdown with queue flush
- Backward compatible API

### Phase 2: Performance Optimizations (Story 1.3)
- **AsyncHandlerAdapter**: Reuse single background event loop
- **File Handler**: Batch writes and optimize JSON serialization
- **Sampling**: Configurable rate limiting and filtering
- **Metrics**: Queue depth, handler latency, drop rates

### Phase 3: Async-First Design (Future)
- Add `aobserve_event()` for native async handlers
- Support for async I/O libraries (aiofiles, httpx)
- Built-in batching and compression
- External queue support (Redis, Kafka)

## Migration Guide

The observability module is designed for incremental improvement. Current code will continue to work as we implement the queue-based architecture. To prepare for future improvements:

1. **Keep handlers lightweight** - Avoid complex processing in handlers
2. **Use sampling** - Plan for high-volume scenarios
3. **Monitor performance** - Track handler execution times
4. **Design for failure** - Handle errors gracefully without retries