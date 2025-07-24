"""
Metrics collection infrastructure for the message bus.

Provides counters, histograms, and gauges for monitoring bus operations
with minimal performance impact.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from weakref import WeakKeyDictionary


class MetricType(Enum):
    """Types of metrics supported."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricValue:
    """Container for a metric value with metadata."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """A monotonically increasing counter metric."""
    name: str
    description: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def inc(self, value: float = 1.0) -> None:
        """Increment the counter by the given value."""
        if value < 0:
            raise ValueError("Counter can only be incremented by non-negative values")
        self.value += value
    
    def get(self) -> float:
        """Get the current counter value."""
        return self.value


@dataclass
class Histogram:
    """A histogram for tracking value distributions."""
    name: str
    description: str
    buckets: List[float] = field(default_factory=lambda: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    values: List[float] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def observe(self, value: float) -> None:
        """Record a value in the histogram."""
        self.values.append(value)
    
    def get_percentile(self, percentile: float) -> Optional[float]:
        """Get a specific percentile from the histogram."""
        if not self.values:
            return None
        
        if not 0 <= percentile <= 100:
            raise ValueError(f"Percentile must be between 0 and 100, got {percentile}")
        
        sorted_values = sorted(self.values)
        # Use proper percentile calculation with interpolation
        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]
        
        # Calculate the exact position
        pos = (n - 1) * percentile / 100
        lower_index = int(pos)
        upper_index = min(lower_index + 1, n - 1)
        
        # Interpolate if needed
        if lower_index == upper_index:
            return sorted_values[lower_index]
        
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        fraction = pos - lower_index
        
        return lower_value + fraction * (upper_value - lower_value)
    
    def get_bucket_counts(self) -> Dict[float, int]:
        """Get counts for each bucket."""
        bucket_counts = {bucket: 0 for bucket in self.buckets}
        bucket_counts[float('inf')] = 0
        
        for value in self.values:
            for bucket in self.buckets:
                if value <= bucket:
                    bucket_counts[bucket] += 1
                    break
            else:
                bucket_counts[float('inf')] += 1
        
        return bucket_counts
    
    def clear(self) -> None:
        """Clear all recorded values."""
        self.values.clear()


@dataclass
class Gauge:
    """A gauge metric that can go up and down."""
    name: str
    description: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        """Set the gauge to a specific value."""
        self.value = value
    
    def inc(self, value: float = 1.0) -> None:
        """Increment the gauge by the given value."""
        self.value += value
    
    def dec(self, value: float = 1.0) -> None:
        """Decrement the gauge by the given value."""
        self.value -= value
    
    def get(self) -> float:
        """Get the current gauge value."""
        return self.value


class MetricsCollector:
    """Centralized metrics collection for the message bus."""
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._lock = asyncio.Lock()
        
        # Initialize standard metrics
        self._init_standard_metrics()
    
    def _init_standard_metrics(self) -> None:
        """Initialize the standard bus metrics."""
        # Counters
        self.register_counter(
            "events_published_total",
            "Total number of events published to the bus"
        )
        self.register_counter(
            "events_processed_total", 
            "Total number of events successfully processed"
        )
        self.register_counter(
            "events_failed_total",
            "Total number of events that failed processing"
        )
        self.register_counter(
            "commands_sent_total",
            "Total number of commands sent to the bus"
        )
        self.register_counter(
            "commands_processed_total",
            "Total number of commands successfully processed"
        )
        self.register_counter(
            "commands_failed_total",
            "Total number of commands that failed processing"
        )
        
        # Histograms
        self.register_histogram(
            "event_processing_duration_seconds",
            "Time taken to process events in seconds"
        )
        self.register_histogram(
            "command_processing_duration_seconds",
            "Time taken to process commands in seconds"
        )
        
        # Gauges
        self.register_gauge(
            "queue_size",
            "Current number of events in the queue"
        )
        self.register_gauge(
            "backpressure_active",
            "Whether backpressure is currently active (1 or 0)"
        )
        self.register_gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)"
        )
        self.register_gauge(
            "dead_letter_queue_size",
            "Current number of events in the dead letter queue"
        )
        self.register_gauge(
            "active_sessions",
            "Number of active sessions"
        )
        self.register_gauge(
            "registered_handlers",
            "Total number of registered event handlers"
        )
    
    def register_counter(self, name: str, description: str) -> Counter:
        """Register a new counter metric."""
        if name in self._counters:
            return self._counters[name]
        
        counter = Counter(name, description)
        self._counters[name] = counter
        return counter
    
    def register_histogram(self, name: str, description: str, buckets: Optional[List[float]] = None) -> Histogram:
        """Register a new histogram metric."""
        if name in self._histograms:
            return self._histograms[name]
        
        histogram = Histogram(name, description)
        if buckets:
            histogram.buckets = buckets
        self._histograms[name] = histogram
        return histogram
    
    def register_gauge(self, name: str, description: str) -> Gauge:
        """Register a new gauge metric."""
        if name in self._gauges:
            return self._gauges[name]
        
        gauge = Gauge(name, description)
        self._gauges[name] = gauge
        return gauge
    
    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        if name in self._counters:
            self._counters[name].inc(value)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a value in a histogram metric."""
        if name in self._histograms:
            self._histograms[name].observe(value)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric to a specific value."""
        if name in self._gauges:
            self._gauges[name].set(value)
    
    def inc_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a gauge metric."""
        if name in self._gauges:
            self._gauges[name].inc(value)
    
    def dec_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement a gauge metric."""
        if name in self._gauges:
            self._gauges[name].dec(value)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        async with self._lock:
            metrics = {
                "counters": {},
                "histograms": {},
                "gauges": {}
            }
            
            # Export counters
            for name, counter in self._counters.items():
                metrics["counters"][name] = {
                    "description": counter.description,
                    "value": counter.get()
                }
            
            # Export histograms
            for name, histogram in self._histograms.items():
                metrics["histograms"][name] = {
                    "description": histogram.description,
                    "count": len(histogram.values),
                    "sum": sum(histogram.values) if histogram.values else 0,
                    "percentiles": {
                        "p50": histogram.get_percentile(50),
                        "p95": histogram.get_percentile(95),
                        "p99": histogram.get_percentile(99)
                    },
                    "buckets": histogram.get_bucket_counts()
                }
            
            # Export gauges
            for name, gauge in self._gauges.items():
                metrics["gauges"][name] = {
                    "description": gauge.description,
                    "value": gauge.get()
                }
            
            return metrics
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        for counter in self._counters.values():
            counter.value = 0.0
        
        for histogram in self._histograms.values():
            histogram.clear()
        
        for gauge in self._gauges.values():
            gauge.value = 0.0


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.observe_histogram(self.metric_name, duration, self.labels)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector (useful for testing)."""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.reset()