# Story 1.7: Implement Async Observability Queue

## Status
Draft

## Story
As a platform engineer,
I want observability to use a queue-and-worker pattern,
So that event observation never blocks the message bus event loop.

## Context
The current synchronous observability handlers work well for development but will cause performance issues in production. Every `observe_event()` call performs I/O synchronously, which blocks the async message bus. This story implements a queue-based approach that maintains the existing API while moving blocking operations to background threads.

## Acceptance Criteria
1. Create `ObservabilityQueue` that buffers events without blocking
2. Implement worker thread(s) that process events from the queue
3. Maintain existing `observe_event()` API (non-breaking change)
4. Add graceful shutdown that flushes pending events
5. Add back-pressure handling (configurable drop/block behavior)
6. Add metrics for queue depth and handler performance
7. Ensure thread-safe operation

## Technical Details

### Architecture
```
Message Bus (async) → ObservabilityManager.observe_event() → Queue (non-blocking)
                                                                 ↓
                                                          Worker Thread(s)
                                                                 ↓
                                                          Sync Handlers
```

### Implementation Approach
```python
class ObservabilityManager:
    def __init__(self, max_queue_size: int = 10000, num_workers: int = 1):
        self._queue = Queue(maxsize=max_queue_size)
        self._workers = []
        self._running = False
        self._start_workers(num_workers)
    
    def observe_event(self, event: Event) -> None:
        """Non-blocking enqueue"""
        try:
            self._queue.put_nowait(event)
        except QueueFull:
            self._handle_backpressure(event)
    
    def _worker_loop(self):
        """Background thread processing events"""
        while self._running:
            try:
                event = self._queue.get(timeout=0.1)
                for handler in self._handlers:
                    handler.handle(event)
            except QueueEmpty:
                continue
```

### Back-pressure Options
- `drop_oldest`: Remove oldest event when queue full
- `drop_newest`: Reject new events when queue full  
- `block`: Convert to blocking put (degrades gracefully)

## Testing Requirements
1. Unit tests for queue operations
2. Thread safety tests with concurrent producers
3. Back-pressure behavior tests
4. Graceful shutdown tests
5. Performance benchmarks comparing sync vs queued

## Dev Notes
- Use standard library `queue.Queue` for thread safety
- Consider `janus` library for async/sync queue bridge if needed
- Add prometheus metrics via `prometheus_client` (optional dependency)
- Ensure worker threads are daemon threads for clean shutdown

## Tasks / Subtasks
- [ ] Create ObservabilityQueue implementation (AC: 1)
  - [ ] Implement thread-safe queue with configurable size
  - [ ] Add put_nowait with back-pressure handling
  - [ ] Write unit tests
- [ ] Implement worker thread management (AC: 2)
  - [ ] Create worker thread pool
  - [ ] Implement worker loop with error handling
  - [ ] Add thread lifecycle management
- [ ] Update ObservabilityManager (AC: 3, 4)
  - [ ] Integrate queue into observe_event()
  - [ ] Add graceful shutdown with queue flush
  - [ ] Maintain backward compatibility
- [ ] Add back-pressure strategies (AC: 5)
  - [ ] Implement drop_oldest, drop_newest, block modes
  - [ ] Make strategy configurable
  - [ ] Add tests for each strategy
- [ ] Add observability metrics (AC: 6)
  - [ ] Queue depth gauge
  - [ ] Handler execution time histogram
  - [ ] Dropped events counter
- [ ] Integration and performance testing (AC: 7)
  - [ ] Thread safety verification
  - [ ] Performance benchmarks
  - [ ] Load testing with high event rates

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