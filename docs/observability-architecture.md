# Observability Architecture

## Overview

The LLMgine observability system provides comprehensive monitoring and tracing capabilities while maintaining a clean separation from the core message bus architecture. This document details the design decisions, current implementation, and future roadmap.

## Design Principles

### 1. Independence from Message Bus
The `ObservabilityManager` operates as a standalone component that:
- Has no dependencies on the message bus
- Prevents circular dependency issues
- Can be tested and evolved independently

### 2. Direct Integration Pattern
Instead of publishing observability events back to the bus:
- The message bus calls `ObservabilityManager.observe_event()` directly
- No additional events are created for observability
- Reduces event amplification and overhead

### 3. Pluggable Handler Architecture
- Simple `ObservabilityHandler` interface
- Easy to add new destinations (file, console, OTEL, etc.)
- Handlers can be registered/unregistered at runtime

## Current Architecture

```
┌─────────────────┐
│   Message Bus   │ (async)
└────────┬────────┘
         │ observe_event()
         ▼
┌─────────────────┐
│ Observability   │ (sync)
│    Manager      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────┐
    ▼         ▼          ▼         ▼
┌────────┐┌────────┐┌────────┐┌────────┐
│Console ││ File   ││ OTEL   ││Custom  │
│Handler ││Handler ││Handler ││Handler │
└────────┘└────────┘└────────┘└────────┘
```

### Components

#### ObservabilityManager
- Central coordinator for all handlers
- Provides `observe_event(event)` method
- Manages handler lifecycle
- Can be enabled/disabled globally

#### Built-in Handlers

| Handler | Purpose | Implementation |
|---------|---------|----------------|
| `SyncConsoleEventHandler` | Logs event summaries to console | Uses Python logging |
| `SyncFileEventHandler` | Writes events to JSONL files | Thread-safe file I/O |
| `OpenTelemetryHandler` | Maps events to traces/spans | OTEL SDK integration |
| `AsyncHandlerAdapter` | Wraps async handlers | Creates event loop per event |

#### Event Mapping (OpenTelemetry)

| Event Type | OTEL Mapping |
|------------|--------------|
| `SessionStartEvent` | New trace |
| `CommandStartedEvent` | New span |
| `CommandResultEvent` | End span + status |
| `LLMCallEvent` | LLM operation span |
| `ToolExecuteResultEvent` | Tool execution span |
| `EventHandlerFailedEvent` | Record exception |
| `SessionEndEvent` | End trace |

## Performance Characteristics

### Synchronous Design Trade-offs

The current implementation uses synchronous handlers for simplicity, but this creates performance implications:

```python
# Current flow (blocking)
async def publish(self, event: Event):
    # This blocks the event loop!
    self._observability.observe_event(event)  # Sync I/O happens here
    
    # Then continue with async work
    await self._event_queue.put(event)
```

### Impact Analysis

| Scenario | Latency Impact | Throughput Impact |
|----------|----------------|-------------------|
| Console logging | ~0.1ms per event | Minimal |
| File writing (SSD) | ~0.5-2ms per event | Lock contention at >1000 events/sec |
| File writing (HDD) | ~5-20ms per event | Severe degradation |
| Network I/O (OTEL) | ~1-100ms per event | Blocks event loop |
| Handler exception | Varies | Error handling overhead |

### Current Limitations

1. **Event Loop Blocking**: Every event blocks the async message bus
2. **No Batching**: Each event triggers individual I/O operations
3. **No Back-pressure**: No mechanism to handle handler overload
4. **Memory Pressure**: Unbounded handler queuing in AsyncHandlerAdapter

## Planned Architecture Evolution

### Phase 1: Queue-Based Decoupling

```
┌─────────────────┐
│   Message Bus   │ (async)
└────────┬────────┘
         │ observe_event() [non-blocking]
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Observability   │      │   Event Queue   │
│    Manager      │─────▶│  (thread-safe)  │
└─────────────────┘      └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │ Worker Threads  │
                         └────────┬────────┘
                                  │
                              Handlers
```

**Implementation Strategy:**
```python
class ObservabilityManager:
    def __init__(self, queue_size=10000, num_workers=2):
        self._queue = Queue(maxsize=queue_size)
        self._workers = []
        self._start_workers(num_workers)
    
    def observe_event(self, event: Event) -> None:
        """Non-blocking enqueue"""
        try:
            self._queue.put_nowait(event)
        except QueueFull:
            self._dropped_events.inc()
```

### Phase 2: Async-Native Design

Add parallel async API while maintaining compatibility:

```python
class ObservabilityManager:
    async def aobserve_event(self, event: Event) -> None:
        """Async observation for async handlers"""
        tasks = [
            handler.ahandle(event) 
            for handler in self._async_handlers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def observe_event(self, event: Event) -> None:
        """Sync API creates background task"""
        asyncio.create_task(self.aobserve_event(event))
```

### Phase 3: Advanced Features

1. **Batching & Compression**
   - Buffer events for batch writing
   - Compress JSONL files
   - Aggregate similar events

2. **Sampling & Filtering**
   - Configurable sample rates
   - Event type filtering
   - Dynamic rate adjustment

3. **External Queues**
   - Redis Streams support
   - Kafka integration
   - Cloud queue services

## Migration Path

### For Library Users

Current code continues to work:
```python
# This doesn't change
bus = MessageBus(observability=observability_manager)
```

### For Handler Developers

Prepare for async-first:
```python
class MyHandler(ObservabilityHandler):
    def handle(self, event: Event) -> None:
        # Current sync implementation
        pass
    
    async def ahandle(self, event: Event) -> None:
        # Future async implementation
        await self.async_process(event)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLMGINE_OBSERVABILITY_ENABLED` | `true` | Global enable/disable |
| `LLMGINE_OBSERVABILITY_QUEUE_SIZE` | `10000` | Max queued events |
| `LLMGINE_OBSERVABILITY_WORKERS` | `2` | Worker thread count |
| `LLMGINE_OBSERVABILITY_SAMPLE_RATE` | `1.0` | Event sampling (0.0-1.0) |

### Programmatic Configuration

```python
from llmgine.observability import ObservabilityConfig

config = ObservabilityConfig(
    enabled=True,
    queue_size=50000,
    num_workers=4,
    back_pressure_strategy="drop_oldest",
    sample_rate=0.1  # Sample 10% in production
)

observability = ObservabilityManager(config)
```

## Best Practices

### Do's
- ✅ Keep handlers lightweight
- ✅ Handle errors gracefully
- ✅ Use sampling in production
- ✅ Monitor handler performance
- ✅ Implement timeouts

### Don'ts
- ❌ Don't perform heavy computation in handlers
- ❌ Don't make synchronous network calls
- ❌ Don't retry failed operations indefinitely
- ❌ Don't accumulate unbounded state

## Monitoring Observability

The observability system should itself be observable:

```python
# Exposed metrics (Prometheus format)
llmgine_observability_events_total{handler="console"} 12345
llmgine_observability_events_dropped_total 67
llmgine_observability_queue_size 234
llmgine_observability_handler_duration_seconds{handler="file",quantile="0.99"} 0.005
```

## Comparison with Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| **Current (Direct Sync)** | Simple, no queues | Blocks event loop |
| **Queue + Workers** | Non-blocking, bounded memory | Thread overhead |
| **Fully Async** | Best performance | Complex error handling |
| **External Service** | Scalable, durable | Network dependency |

## Future Considerations

1. **Structured Events**: Move from free-form to schema-validated events
2. **Event Sourcing**: Optional durability for event replay
3. **Distributed Tracing**: Correlation IDs across services
4. **Custom Metrics**: Beyond tracing to business metrics

## References

- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [asyncio Queue](https://docs.python.org/3/library/asyncio-queue.html)