# Story 1.4: Comprehensive Test Coverage - Core Components with Performance

## Story
As a maintainer,
I want comprehensive test coverage and performance benchmarks for core components,
so that I can ensure reliability and maintain performance SLAs.

## Context
Current test coverage is insufficient with only 8 test files for 59 source files. Core components like the message bus, observability handlers, and session management need comprehensive testing for production readiness.

## Acceptance Criteria
1. Achieve >80% test coverage for message bus components
2. Add integration tests for complete command/event flows
3. Create comprehensive tests for all observability handlers
4. Test error handling and edge cases in bus operations
5. Add performance benchmarks achieving 10k events/sec target
6. Create stress tests for graceful degradation scenarios
7. Add chaos testing for handler failures and recovery
8. Set up continuous performance monitoring in CI

## Integration Verification
- IV1: All existing tests continue to pass
- IV2: Test execution time remains under 5 minutes
- IV3: Tests can run in isolation without external dependencies

## Technical Details

### Test Coverage Targets by Module
1. **Message Bus (src/llmgine/bus/)**
   - `bus.py`: Unit tests for all public methods
   - `session.py`: Session lifecycle tests
   - Error handling and edge cases
   - Concurrent operation tests

2. **Messages (src/llmgine/messages/)**
   - Command/Event serialization tests
   - Metadata handling tests
   - Type validation tests

3. **Observability (src/llmgine/observability/)**
   - FileEventHandler: File I/O and formatting tests
   - ConsoleEventHandler: Output formatting tests
   - Event filtering and routing tests

4. **Context Management**
   - InMemoryContextManager: CRUD operations
   - SimpleChatHistory: Message management
   - Context overflow handling

### Integration Test Scenarios
1. Complete command execution flow
2. Event propagation across handlers
3. Session creation and cleanup
4. Error propagation and handling
5. Concurrent session management

### Performance Benchmarks
```python
# Performance targets:
- Event publishing: 10,000+ events/second
- Command execution: <10ms p99 latency
- Session operations: <1ms per operation
- Memory usage: <100MB for 100k events
- Handler processing: <5ms per handler

# Benchmark scenarios:
1. Sustained load test (10k events/sec for 10 minutes)
2. Burst test (50k events in 1 second)
3. Mixed workload (commands + events)
4. Concurrent session test (1000 active sessions)
5. Handler failure recovery test
```

### Stress Testing Scenarios
1. **Queue Overflow**: Push events faster than consumption
2. **Handler Crashes**: Random handler failures during processing
3. **Memory Pressure**: Limited memory with high event rate
4. **CPU Saturation**: Max out CPU with complex handlers
5. **Network Delays**: Simulate slow handlers

### Chaos Testing Framework
```python
# tests/chaos/bus_chaos.py
class ChaosTestFramework:
    async def inject_handler_failure(self, failure_rate: float):
        """Randomly fail handlers at specified rate"""
    
    async def inject_latency(self, min_ms: int, max_ms: int):
        """Add random latency to handlers"""
    
    async def inject_memory_pressure(self):
        """Consume memory to test behavior under pressure"""
```

## Testing Requirements
1. Use pytest-cov for coverage reporting
2. Add pytest-benchmark for performance tests
3. Create test fixtures for common scenarios
4. Mock external dependencies appropriately
5. Add CI integration with coverage badges