# Story 1.3: Observability Code-Level Improvements

## Status
Draft

## Story
As a developer,
I want to improve the efficiency and correctness of observability handlers,
So that the system performs better even before moving to async patterns.

## Context
Several quick improvements can be made to the existing observability code:
1. AsyncHandlerAdapter creates a new event loop per event (expensive)
2. File handler repeatedly calls asdict() on nested objects
3. LogLevel enum exists but isn't wired to actual logging
4. OpenTelemetryHandler uses nested ContextVars that can leak memory

## Acceptance Criteria
1. Fix AsyncHandlerAdapter to reuse a single background event loop
2. Optimize file handler's JSON serialization
3. Wire LogLevel to Python logging levels
4. Use WeakValueDictionary for span storage in OTEL handler
5. Add configurable sampling for high-volume scenarios

## Technical Details

### AsyncHandlerAdapter Fix
```python
class AsyncHandlerAdapter(ObservabilityHandler):
    def __init__(self, async_handler):
        self._async_handler = async_handler
        self._loop = None
        self._thread = None
        self._start_background_loop()
    
    def _start_background_loop(self):
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_forever()
        
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        # Wait for loop to be ready
        while self._loop is None:
            time.sleep(0.01)
    
    def handle(self, event):
        asyncio.run_coroutine_threadsafe(
            self._async_handler.handle(event), 
            self._loop
        )
```

### File Handler Optimization
- Cache serialization of frequently seen event types
- Use orjson for faster JSON encoding (optional dependency)
- Batch multiple events per write when possible

### LogLevel Integration
```python
LOG_LEVEL_MAP = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL
}

# In console handler:
log_level = LOG_LEVEL_MAP.get(
    getattr(event, 'level', LogLevel.INFO),
    logging.INFO
)
logger.log(log_level, message)
```

## Tasks / Subtasks
- [ ] Fix AsyncHandlerAdapter (AC: 1)
  - [ ] Implement background event loop thread
  - [ ] Use run_coroutine_threadsafe()
  - [ ] Add cleanup on shutdown
- [ ] Optimize file handler (AC: 2)
  - [ ] Add orjson as optional dependency
  - [ ] Implement efficient serialization
  - [ ] Consider event batching
- [ ] Wire LogLevel enum (AC: 3)
  - [ ] Add level attribute to events
  - [ ] Map to Python logging levels
  - [ ] Update console handler
- [ ] Fix OTEL memory leaks (AC: 4)
  - [ ] Replace ContextVar dict with WeakValueDictionary
  - [ ] Add span timeout/cleanup
  - [ ] Test for memory leaks
- [ ] Add sampling configuration (AC: 5)
  - [ ] Implement sample_rate (0.0-1.0)
  - [ ] Add event type filtering
  - [ ] Make configurable via environment

## Dev Notes
- These are backward-compatible improvements
- Consider feature flags for new behavior
- Benchmark before/after for each optimization
- Document any new configuration options

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-23 | 1.0 | Initial story creation | James |

## Dev Agent Record

### Agent Model Used
- Model: 

### Debug Log References
- Session: 

### Completion Notes List
- 

### File List
- 

## QA Results
- 