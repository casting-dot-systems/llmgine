# Observability Migration Guide

This guide helps you migrate from the old EventLogWrapper-based observability to the new standalone ObservabilityManager.

## What Changed?

### Old Architecture (Pre-1.1)
```
Message Bus → EventLogWrapper → Message Bus → Observability Handlers
                    ↑
            (Circular dependency)
```

- Events were wrapped in `EventLogWrapper` objects
- Observability events were published back to the message bus
- Potential for infinite loops and event amplification
- Performance overhead from double event processing

### New Architecture (1.1+)
```
Message Bus → ObservabilityManager → Handlers
         (Direct call, no events)
```

- Direct observation without event wrapping
- No observability events on the bus
- Better performance and no circular dependencies
- Simpler mental model

## Breaking Changes

### 1. EventLogWrapper Removed

**Before:**
```python
from llmgine.observability.events import EventLogWrapper

# Events were automatically wrapped
bus.register_event_handler("global", EventLogWrapper, handler)
```

**After:**
```python
# No wrapper needed - handlers receive original events
from llmgine.observability.handlers import ConsoleEventHandler

observability = ObservabilityManager()
observability.register_handler(ConsoleEventHandler())
bus = MessageBus(observability=observability)
```

### 2. Handler Registration Changed

**Before:**
```python
# Registered on message bus
bus.register_observability_handler(ConsoleEventHandler())
```

**After:**
```python
# Registered on ObservabilityManager
observability = ObservabilityManager()
observability.register_handler(create_sync_console_handler())
bus = MessageBus(observability=observability)
```

### 3. Handler Interface Changed

**Before (Async):**
```python
class MyHandler(ObservabilityEventHandler):
    async def handle(self, event: Event) -> None:
        # Async implementation
        await self.process(event)
```

**After (Sync):**
```python
class MyHandler(ObservabilityHandler):
    def handle(self, event: Event) -> None:
        # Sync implementation
        self.process(event)
```

To use existing async handlers, wrap them:
```python
from llmgine.observability.handlers.adapters import AsyncHandlerAdapter

async_handler = MyAsyncHandler()
sync_adapter = AsyncHandlerAdapter(async_handler)
observability.register_handler(sync_adapter)
```

## Step-by-Step Migration

### 1. Update Imports

```python
# Remove
from llmgine.observability.events import EventLogWrapper

# Add
from llmgine.observability.manager import ObservabilityManager
from llmgine.observability.handlers.adapters import (
    create_sync_console_handler,
    create_sync_file_handler
)
```

### 2. Update Bootstrap Code

**Before:**
```python
bus = MessageBus()
bus.register_observability_handler(ConsoleEventHandler())
bus.register_observability_handler(FileEventHandler())
```

**After:**
```python
observability = ObservabilityManager()
observability.register_handler(create_sync_console_handler())
observability.register_handler(create_sync_file_handler())
bus = MessageBus(observability=observability)
```

Or use ApplicationBootstrap (recommended):
```python
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig

config = ApplicationConfig(
    enable_console_handler=True,
    enable_file_handler=True
)
bootstrap = ApplicationBootstrap(config)
await bootstrap.bootstrap()
```

### 3. Update Custom Handlers

**Option A: Convert to Sync**
```python
# Before
class MyAsyncHandler(ObservabilityEventHandler):
    async def handle(self, event: Event) -> None:
        async with aiofiles.open('log.txt', 'a') as f:
            await f.write(f"{event}\n")

# After
class MySyncHandler(ObservabilityHandler):
    def handle(self, event: Event) -> None:
        with open('log.txt', 'a') as f:
            f.write(f"{event}\n")
```

**Option B: Use Adapter**
```python
from llmgine.observability.handlers.adapters import AsyncHandlerAdapter

handler = AsyncHandlerAdapter(MyAsyncHandler())
observability.register_handler(handler)
```

### 4. Update Tests

**Before:**
```python
# Test received EventLogWrapper
def test_observability():
    events = []
    bus.register_event_handler("global", EventLogWrapper, 
                              lambda e: events.append(e))
    
    bus.publish(MyEvent())
    assert isinstance(events[0], EventLogWrapper)
    assert events[0].original_event_type == "MyEvent"
```

**After:**
```python
# Test with ObservabilityManager
def test_observability():
    handler = MockHandler()
    observability = ObservabilityManager()
    observability.register_handler(handler)
    
    bus = MessageBus(observability=observability)
    bus.publish(MyEvent())
    
    assert len(handler.events) == 1
    assert isinstance(handler.events[0], MyEvent)
```

## Common Patterns

### Testing with Observability

```python
class TestHandler(ObservabilityHandler):
    def __init__(self):
        self.events = []
    
    def handle(self, event: Event) -> None:
        self.events.append(event)

@pytest.fixture
def observability():
    obs = ObservabilityManager()
    handler = TestHandler()
    obs.register_handler(handler)
    return obs, handler

async def test_my_feature(observability):
    obs_manager, handler = observability
    bus = MessageBus(observability=obs_manager)
    
    # Test your feature
    await bus.publish(MyEvent())
    
    # Assert on captured events
    assert len(handler.events) == 1
```

### Conditional Handlers

```python
# Development vs Production
if os.getenv('ENV') == 'production':
    handler = create_sync_file_handler(
        log_dir='/var/log/myapp',
        filename='events.jsonl'
    )
else:
    handler = create_sync_console_handler()

observability.register_handler(handler)
```

### Custom Filtering

```python
class FilteredHandler(ObservabilityHandler):
    def __init__(self, base_handler, event_types):
        self.base_handler = base_handler
        self.event_types = event_types
    
    def handle(self, event: Event) -> None:
        if type(event) in self.event_types:
            self.base_handler.handle(event)

# Only log specific events
handler = FilteredHandler(
    create_sync_file_handler(),
    {CommandStartedEvent, CommandResultEvent}
)
```

## Troubleshooting

### Issue: Import Errors
```
ImportError: cannot import name 'EventLogWrapper'
```
**Solution:** Remove all references to EventLogWrapper. Events are no longer wrapped.

### Issue: Async Handler Errors
```
RuntimeError: This event loop is already running
```
**Solution:** Use AsyncHandlerAdapter or convert to sync handlers.

### Issue: Missing Events
**Check:**
1. ObservabilityManager is passed to MessageBus
2. Handlers are registered before publishing events
3. Observability is not disabled (`manager.set_enabled(True)`)

### Issue: Performance Degradation
**Solution:** You may be experiencing the synchronous I/O bottleneck. Consider:
1. Reducing logging verbosity
2. Using faster storage (SSD vs HDD)
3. Waiting for the queue-based implementation (Story 1.2)

## Best Practices

1. **Use ApplicationBootstrap** - Handles setup correctly
2. **Keep handlers simple** - Complex logic belongs elsewhere
3. **Test with mock handlers** - Don't do real I/O in tests
4. **Plan for async** - The sync API is temporary
5. **Monitor performance** - Track handler execution time

## Future-Proofing

The observability API will evolve to support async operations:

```python
# Future API (Phase 2)
class ObservabilityManager:
    # Sync API (current)
    def observe_event(self, event: Event) -> None: ...
    
    # Async API (future)
    async def aobserve_event(self, event: Event) -> None: ...

# Your handler can prepare
class FutureReadyHandler(ObservabilityHandler):
    def handle(self, event: Event) -> None:
        # Sync implementation
        pass
    
    async def ahandle(self, event: Event) -> None:
        # Async implementation (optional)
        pass
```

## Need Help?

1. Check the [Observability README](../src/llmgine/observability/README.md)
2. Review the [Architecture Documentation](./observability-architecture.md)
3. See example implementations in [tests](../tests/unit/observability/)
4. Open an issue for migration problems