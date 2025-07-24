# Observability Cookbook

Practical recipes for common observability scenarios in LLMgine.

## Table of Contents

1. [Basic Setup](#basic-setup)
2. [Custom Handlers](#custom-handlers)
3. [Filtering and Sampling](#filtering-and-sampling)
4. [OpenTelemetry Integration](#opentelemetry-integration)
5. [Production Patterns](#production-patterns)
6. [Testing Strategies](#testing-strategies)
7. [Performance Optimization](#performance-optimization)

## Basic Setup

### Minimal Configuration

```python
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig

# Just console logging
config = ApplicationConfig(
    enable_console_handler=True,
    enable_file_handler=False
)

bootstrap = ApplicationBootstrap(config)
await bootstrap.bootstrap()
```

### Development Configuration

```python
config = ApplicationConfig(
    enable_console_handler=True,
    enable_file_handler=True,
    file_handler_log_dir="./logs",
    log_level=LogLevel.DEBUG
)
```

### Production Configuration

```python
config = ApplicationConfig(
    enable_console_handler=False,  # Reduce stdout noise
    enable_file_handler=True,
    file_handler_log_dir="/var/log/myapp",
    file_handler_log_filename=f"events-{datetime.now():%Y%m%d}.jsonl",
    log_level=LogLevel.INFO
)
```

## Custom Handlers

### Slack Notification Handler

```python
from llmgine.observability.manager import ObservabilityHandler
from llmgine.messages.events import Event, ErrorEvent
import requests

class SlackHandler(ObservabilityHandler):
    def __init__(self, webhook_url: str, notify_on_errors: bool = True):
        self.webhook_url = webhook_url
        self.notify_on_errors = notify_on_errors
    
    def handle(self, event: Event) -> None:
        if self.notify_on_errors and isinstance(event, ErrorEvent):
            self._send_to_slack(f"🚨 Error: {event.message}")
    
    def _send_to_slack(self, message: str) -> None:
        try:
            requests.post(self.webhook_url, json={"text": message})
        except Exception as e:
            # Don't let handler errors break the system
            logger.error(f"Failed to send to Slack: {e}")
```

### Metrics Handler (Prometheus)

```python
from prometheus_client import Counter, Histogram
import time

class MetricsHandler(ObservabilityHandler):
    def __init__(self):
        self.event_counter = Counter(
            'llmgine_events_total',
            'Total events by type',
            ['event_type']
        )
        self.command_duration = Histogram(
            'llmgine_command_duration_seconds',
            'Command execution time',
            ['command_type']
        )
        self._command_starts = {}
    
    def handle(self, event: Event) -> None:
        event_type = type(event).__name__
        self.event_counter.labels(event_type=event_type).inc()
        
        if isinstance(event, CommandStartedEvent):
            self._command_starts[event.command_id] = time.time()
        
        elif isinstance(event, CommandResultEvent):
            start_time = self._command_starts.pop(event.command_id, None)
            if start_time:
                duration = time.time() - start_time
                self.command_duration.labels(
                    command_type=event.command_type
                ).observe(duration)
```

### Database Handler

```python
import sqlite3
import json
from contextlib import contextmanager

class SQLiteHandler(ObservabilityHandler):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    event_type TEXT,
                    session_id TEXT,
                    timestamp TEXT,
                    data JSON
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session 
                ON events(session_id)
            ''')
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def handle(self, event: Event) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO events 
                (event_id, event_type, session_id, timestamp, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                type(event).__name__,
                str(event.session_id),
                event.timestamp,
                json.dumps(self._event_to_dict(event))
            ))
```

## Filtering and Sampling

### Event Type Filter

```python
class TypeFilterHandler(ObservabilityHandler):
    def __init__(self, handler: ObservabilityHandler, 
                 include_types: set[type] = None,
                 exclude_types: set[type] = None):
        self.handler = handler
        self.include_types = include_types
        self.exclude_types = exclude_types or set()
    
    def handle(self, event: Event) -> None:
        event_type = type(event)
        
        if self.include_types and event_type not in self.include_types:
            return
        
        if event_type in self.exclude_types:
            return
        
        self.handler.handle(event)

# Usage
filtered_handler = TypeFilterHandler(
    create_sync_file_handler(),
    include_types={CommandStartedEvent, CommandResultEvent, ErrorEvent}
)
```

### Sampling Handler

```python
import random
import hashlib

class SamplingHandler(ObservabilityHandler):
    def __init__(self, handler: ObservabilityHandler, 
                 sample_rate: float = 0.1):
        self.handler = handler
        self.sample_rate = sample_rate
    
    def handle(self, event: Event) -> None:
        # Deterministic sampling based on session ID
        session_hash = hashlib.md5(
            str(event.session_id).encode()
        ).hexdigest()
        sample_value = int(session_hash[:8], 16) / 0xFFFFFFFF
        
        if sample_value < self.sample_rate:
            self.handler.handle(event)

# Sample 10% of sessions
sampled = SamplingHandler(create_sync_file_handler(), 0.1)
```

### Rate Limiting Handler

```python
from collections import deque
import time

class RateLimitHandler(ObservabilityHandler):
    def __init__(self, handler: ObservabilityHandler,
                 max_events_per_second: int = 100):
        self.handler = handler
        self.max_rate = max_events_per_second
        self.timestamps = deque(maxlen=max_events_per_second)
    
    def handle(self, event: Event) -> None:
        now = time.time()
        
        # Remove timestamps older than 1 second
        while self.timestamps and self.timestamps[0] < now - 1:
            self.timestamps.popleft()
        
        if len(self.timestamps) < self.max_rate:
            self.timestamps.append(now)
            self.handler.handle(event)
        # Else: drop the event
```

## OpenTelemetry Integration

### Basic OTEL Setup

```python
from llmgine.observability.otel_handler import OpenTelemetryHandler

# Development (console export)
otel_handler = OpenTelemetryHandler(service_name="my-llm-app")
observability.register_handler(otel_handler)
```

### Production OTEL with OTLP

```python
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter
)

def setup_otel_handler() -> OpenTelemetryHandler:
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", 
                           "http://localhost:4317"),
        headers=(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    )
    
    # Setup provider
    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )
    trace.set_tracer_provider(provider)
    
    return OpenTelemetryHandler(
        service_name=os.getenv("SERVICE_NAME", "llmgine-app")
    )
```

### Custom Span Attributes

```python
class EnrichedOTELHandler(OpenTelemetryHandler):
    def handle(self, event: Event) -> None:
        super().handle(event)
        
        # Add custom attributes to current span
        if hasattr(event, 'user_id'):
            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute("user.id", event.user_id)
```

## Production Patterns

### Multi-Handler with Fallback

```python
class FallbackHandler(ObservabilityHandler):
    def __init__(self, primary: ObservabilityHandler,
                 fallback: ObservabilityHandler):
        self.primary = primary
        self.fallback = fallback
    
    def handle(self, event: Event) -> None:
        try:
            self.primary.handle(event)
        except Exception as e:
            logger.error(f"Primary handler failed: {e}")
            try:
                self.fallback.handle(event)
            except Exception as e2:
                logger.error(f"Fallback handler also failed: {e2}")

# Use file handler with console fallback
handler = FallbackHandler(
    primary=create_sync_file_handler("/var/log/app/events.jsonl"),
    fallback=create_sync_console_handler()
)
```

### Buffered Handler (Prepare for Async)

```python
from queue import Queue, Full
import threading

class BufferedHandler(ObservabilityHandler):
    def __init__(self, handler: ObservabilityHandler, 
                 buffer_size: int = 1000):
        self.handler = handler
        self.buffer = Queue(maxsize=buffer_size)
        self.worker_thread = threading.Thread(
            target=self._worker, daemon=True
        )
        self.running = True
        self.worker_thread.start()
    
    def handle(self, event: Event) -> None:
        try:
            self.buffer.put_nowait(event)
        except Full:
            # Log and drop
            logger.warning("Event buffer full, dropping event")
    
    def _worker(self):
        while self.running:
            try:
                event = self.buffer.get(timeout=0.1)
                self.handler.handle(event)
            except Exception:
                continue
    
    def shutdown(self):
        self.running = False
        self.worker_thread.join(timeout=5)
```

### Environment-Based Configuration

```python
def create_production_observability() -> ObservabilityManager:
    manager = ObservabilityManager()
    
    # File handler for persistence
    if os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true':
        file_handler = create_sync_file_handler(
            log_dir=os.getenv('LOG_DIR', '/var/log/app'),
            filename=f"events-{os.getenv('HOSTNAME', 'unknown')}.jsonl"
        )
        manager.register_handler(file_handler)
    
    # OTEL for tracing
    if os.getenv('ENABLE_OTEL', 'false').lower() == 'true':
        otel_handler = setup_otel_handler()
        manager.register_handler(otel_handler)
    
    # Metrics
    if os.getenv('ENABLE_METRICS', 'true').lower() == 'true':
        metrics_handler = MetricsHandler()
        manager.register_handler(metrics_handler)
    
    # Apply sampling in production
    if os.getenv('ENV') == 'production':
        sample_rate = float(os.getenv('SAMPLE_RATE', '0.1'))
        return SampledObservabilityManager(manager, sample_rate)
    
    return manager
```

## Testing Strategies

### Mock Handler for Tests

```python
@pytest.fixture
def mock_observability():
    class MockHandler(ObservabilityHandler):
        def __init__(self):
            self.events = []
            self.call_count = 0
        
        def handle(self, event: Event) -> None:
            self.events.append(event)
            self.call_count += 1
        
        def assert_event_types(self, *expected_types):
            actual_types = [type(e) for e in self.events]
            assert actual_types == list(expected_types)
        
        def get_events_by_type(self, event_type):
            return [e for e in self.events if isinstance(e, event_type)]
    
    handler = MockHandler()
    manager = ObservabilityManager()
    manager.register_handler(handler)
    
    return manager, handler

async def test_my_feature(mock_observability):
    manager, handler = mock_observability
    bus = MessageBus(observability=manager)
    
    # Run test
    await my_feature(bus)
    
    # Assert
    handler.assert_event_types(
        SessionStartEvent,
        CommandStartedEvent,
        CommandResultEvent,
        SessionEndEvent
    )
```

### Capturing Handler Exceptions

```python
class ExceptionCapturingHandler(ObservabilityHandler):
    def __init__(self):
        self.exceptions = []
    
    def handle(self, event: Event) -> None:
        if isinstance(event, ErrorEvent):
            self.exceptions.append(event.exception)
    
    def assert_no_exceptions(self):
        assert not self.exceptions, f"Captured {len(self.exceptions)} exceptions"
```

## Performance Optimization

### Lazy Formatting

```python
class LazyFormattingHandler(ObservabilityHandler):
    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        self.min_level = min_level
    
    def handle(self, event: Event) -> None:
        event_level = getattr(event, 'level', LogLevel.INFO)
        
        if event_level.value < self.min_level.value:
            return  # Skip formatting for filtered events
        
        # Only format if we're going to use it
        formatted = self._format_event(event)
        self._write(formatted)
```

### Batch File Writer

```python
class BatchFileHandler(ObservabilityHandler):
    def __init__(self, file_path: str, batch_size: int = 100,
                 flush_interval: float = 1.0):
        self.file_path = file_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.last_flush = time.time()
        self.lock = threading.Lock()
    
    def handle(self, event: Event) -> None:
        with self.lock:
            self.buffer.append(event)
            
            if (len(self.buffer) >= self.batch_size or 
                time.time() - self.last_flush > self.flush_interval):
                self._flush()
    
    def _flush(self):
        if not self.buffer:
            return
        
        with open(self.file_path, 'a') as f:
            for event in self.buffer:
                json.dump(self._event_to_dict(event), f)
                f.write('\n')
        
        self.buffer.clear()
        self.last_flush = time.time()
```

### Memory-Efficient Ring Buffer

```python
class RingBufferHandler(ObservabilityHandler):
    def __init__(self, size: int = 1000):
        self.buffer = deque(maxlen=size)
    
    def handle(self, event: Event) -> None:
        # Automatically drops oldest when full
        self.buffer.append({
            'type': type(event).__name__,
            'time': event.timestamp,
            'session': str(event.session_id)
        })
    
    def get_recent_events(self, n: int = 100):
        return list(self.buffer)[-n:]
```

## Advanced Patterns

### Circuit Breaker Handler

```python
class CircuitBreakerHandler(ObservabilityHandler):
    def __init__(self, handler: ObservabilityHandler,
                 failure_threshold: int = 5,
                 reset_timeout: float = 60.0):
        self.handler = handler
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def handle(self, event: Event) -> None:
        if self.is_open:
            if (time.time() - self.last_failure_time) > self.reset_timeout:
                self.is_open = False
                self.failure_count = 0
            else:
                return  # Circuit is open, skip
        
        try:
            self.handler.handle(event)
            self.failure_count = 0  # Reset on success
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise
```

### Async Queue Bridge (Preview of Future)

```python
import asyncio
import janus

class AsyncQueueBridge:
    """Preview of queue-based architecture coming in Story 1.2"""
    def __init__(self, handler: ObservabilityHandler):
        self.handler = handler
        self._queue = None
        self._task = None
    
    async def start(self):
        self._queue = janus.Queue()
        self._task = asyncio.create_task(self._worker())
    
    async def _worker(self):
        while True:
            event = await self._queue.async_q.get()
            if event is None:  # Shutdown signal
                break
            
            try:
                await asyncio.to_thread(self.handler.handle, event)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    def observe_event(self, event: Event) -> None:
        """Non-blocking sync API"""
        self._queue.sync_q.put_nowait(event)
    
    async def shutdown(self):
        await self._queue.async_q.put(None)
        await self._task
```

## Next Steps

1. Review the [Architecture Documentation](./observability-architecture.md)
2. Check the [Migration Guide](./observability-migration-guide.md) if upgrading
3. Monitor the [GitHub repository](https://github.com/llmgine/llmgine) for queue-based implementation