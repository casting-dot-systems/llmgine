#!/usr/bin/env python3
"""
Performance benchmark suite for the LLMgine Message Bus.

Targets:
- Throughput: 10,000+ events/second sustained
- Latency: <10ms p99 for event publishing
- Memory: Bounded memory usage under load
- CPU: Linear scaling with event rate
"""

import asyncio
import time
import statistics
import random
import psutil
import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llmgine.bus.bus import MessageBus
from llmgine.bus.resilience import ResilientMessageBus
from llmgine.bus.backpressure import BoundedEventQueue, BackpressureStrategy
from llmgine.bus.metrics import get_metrics_collector, reset_metrics_collector
from llmgine.messages.events import Event
from llmgine.messages.commands import Command


# Benchmark Events and Commands
@dataclass
class BenchmarkEvent(Event):
    """Event for performance testing."""
    payload: Dict[str, Any] = field(default_factory=dict)
    bench_timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkCommand(Command):
    """Command for performance testing."""
    operation: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    bench_timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    test_name: str
    duration_seconds: float
    total_operations: int
    throughput_ops_per_sec: float
    latencies_ms: List[float]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    memory_start_mb: float
    memory_peak_mb: float
    memory_end_mb: float
    cpu_percent_avg: float
    errors: int = 0
    notes: str = ""


class BenchmarkRunner:
    """Runs performance benchmarks for the message bus."""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()
        
    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
        
    def calculate_percentiles(self, values: List[float]) -> tuple[float, float, float]:
        """Calculate p50, p95, p99 percentiles."""
        if not values:
            return 0.0, 0.0, 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        p50 = sorted_values[int(n * 0.5)]
        p95 = sorted_values[int(n * 0.95)]
        p99 = sorted_values[int(n * 0.99)]
        return p50, p95, p99
    
    async def benchmark_sustained_throughput(self, target_ops: int = 100000, target_rate: int = 10000) -> BenchmarkResult:
        """Test sustained throughput targeting 10k events/sec."""
        print(f"\n🚀 Running Sustained Throughput Benchmark")
        print(f"   Target: {target_ops:,} operations at {target_rate:,} ops/sec")
        
        bus = MessageBus()
        latencies: List[float] = []
        processed = 0
        errors = 0
        
        # Handler that tracks processing
        async def handler(event: BenchmarkEvent) -> None:
            nonlocal processed
            processed += 1
            # Simulate minimal work
            await asyncio.sleep(0)
        
        bus.register_event_handler(BenchmarkEvent, handler)
        
        # Start the message bus
        await bus.start()
        
        # Memory and CPU tracking
        memory_start = self.get_memory_mb()
        memory_peak = memory_start
        cpu_samples: List[float] = []
        
        # CPU monitoring task
        async def monitor_resources():
            nonlocal memory_peak
            while processed < target_ops:
                cpu_samples.append(self.process.cpu_percent(interval=0.1))
                memory_peak_new = self.get_memory_mb()
                if memory_peak_new > memory_peak:
                    memory_peak = memory_peak_new
                await asyncio.sleep(0.1)
        
        monitor_task = asyncio.create_task(monitor_resources())
        
        # Rate limiter for controlled throughput
        rate_limiter = asyncio.Semaphore(target_rate // 10)  # Allow bursts of 1/10th the target rate
        
        start_time = time.time()
        
        # Publisher coroutine
        async def publish_events():
            nonlocal errors
            for i in range(target_ops):
                async with rate_limiter:
                    try:
                        publish_start = time.time()
                        await bus.publish(BenchmarkEvent(
                            payload={"index": i, "data": "x" * 100}
                        ))
                        publish_time = (time.time() - publish_start) * 1000  # Convert to ms
                        latencies.append(publish_time)
                    except Exception as e:
                        errors += 1
                        print(f"Error publishing event {i}: {e}")
                    
                    # Release rate limiter after delay to maintain target rate
                    asyncio.create_task(self._release_after_delay(rate_limiter, 1.0 / target_rate))
        
        # Run publisher
        await publish_events()
        
        # Wait for all events to be processed
        while processed < target_ops - errors:
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Stop monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        memory_end = self.get_memory_mb()
        
        # Calculate results
        throughput = processed / duration
        p50, p95, p99 = self.calculate_percentiles(latencies)
        cpu_avg = statistics.mean(cpu_samples) if cpu_samples else 0.0
        
        result = BenchmarkResult(
            test_name="Sustained Throughput",
            duration_seconds=duration,
            total_operations=processed,
            throughput_ops_per_sec=throughput,
            latencies_ms=latencies[:1000],  # Store first 1000 for analysis
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            memory_start_mb=memory_start,
            memory_peak_mb=memory_peak,
            memory_end_mb=memory_end,
            cpu_percent_avg=cpu_avg,
            errors=errors,
            notes=f"Target rate: {target_rate} ops/sec"
        )
        
        # Stop the bus
        await bus.stop()
        
        self.results.append(result)
        return result
    
    async def _release_after_delay(self, semaphore: asyncio.Semaphore, delay: float):
        """Release semaphore after delay."""
        await asyncio.sleep(delay)
        semaphore.release()
    
    async def benchmark_latency_under_load(self, ops_per_batch: int = 1000, num_batches: int = 10) -> BenchmarkResult:
        """Measure latency percentiles under various load conditions."""
        print(f"\n⏱️  Running Latency Benchmark")
        print(f"   Batches: {num_batches} x {ops_per_batch} operations")
        
        bus = MessageBus()
        all_latencies: List[float] = []
        processed = 0
        
        async def handler(event: BenchmarkEvent) -> None:
            nonlocal processed
            processed += 1
            # Simulate variable work
            await asyncio.sleep(random.uniform(0, 0.001))
        
        bus.register_event_handler(BenchmarkEvent, handler)
        
        # Start the message bus
        await bus.start()
        
        memory_start = self.get_memory_mb()
        memory_peak = memory_start
        cpu_samples: List[float] = []
        
        start_time = time.time()
        
        for batch in range(num_batches):
            batch_latencies: List[float] = []
            
            # Vary load between batches
            if batch % 3 == 0:
                # High load batch
                concurrent_ops = ops_per_batch
            elif batch % 3 == 1:
                # Medium load batch
                concurrent_ops = ops_per_batch // 2
            else:
                # Low load batch
                concurrent_ops = ops_per_batch // 10
            
            # Publish events concurrently
            tasks = []
            for i in range(concurrent_ops):
                publish_start = time.time()
                task = bus.publish(BenchmarkEvent(
                    payload={"batch": batch, "index": i}
                ))
                tasks.append((task, publish_start))
            
            # Wait for all publishes to complete and measure latency
            for task, publish_start in tasks:
                await task
                publish_time = (time.time() - publish_start) * 1000
                batch_latencies.append(publish_time)
            
            all_latencies.extend(batch_latencies)
            
            # Monitor resources
            cpu_samples.append(self.process.cpu_percent(interval=0))
            current_memory = self.get_memory_mb()
            if current_memory > memory_peak:
                memory_peak = current_memory
        
        # Wait for processing to complete
        total_expected = sum(ops_per_batch if i % 3 == 0 else 
                           ops_per_batch // 2 if i % 3 == 1 else 
                           ops_per_batch // 10 
                           for i in range(num_batches))
        
        while processed < total_expected:
            await asyncio.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        memory_end = self.get_memory_mb()
        
        # Calculate results
        p50, p95, p99 = self.calculate_percentiles(all_latencies)
        cpu_avg = statistics.mean(cpu_samples) if cpu_samples else 0.0
        
        result = BenchmarkResult(
            test_name="Latency Under Load",
            duration_seconds=duration,
            total_operations=processed,
            throughput_ops_per_sec=processed / duration,
            latencies_ms=all_latencies[:1000],
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            memory_start_mb=memory_start,
            memory_peak_mb=memory_peak,
            memory_end_mb=memory_end,
            cpu_percent_avg=cpu_avg,
            notes="Variable load test with high/medium/low batches"
        )
        
        # Stop the bus
        await bus.stop()
        
        self.results.append(result)
        return result
    
    async def benchmark_memory_stability(self, duration_seconds: int = 30, rate: int = 5000) -> BenchmarkResult:
        """Test memory usage under sustained load."""
        print(f"\n💾 Running Memory Stability Benchmark")
        print(f"   Duration: {duration_seconds}s at {rate} ops/sec")
        
        # Create a MessageBus with backpressure handling
        from llmgine.bus.resilience import ResilientMessageBus
        wrapped_bus = MessageBus()  # Regular bus for this test
        
        processed = 0
        dropped = 0
        
        async def handler(event: BenchmarkEvent) -> None:
            nonlocal processed
            processed += 1
            # Simulate memory allocation
            data = "x" * random.randint(100, 1000)
            await asyncio.sleep(0.001)
        
        wrapped_bus.register_event_handler(BenchmarkEvent, handler)
        
        # Start the message bus
        await wrapped_bus.start()
        
        memory_samples: List[float] = []
        latencies: List[float] = []
        
        async def monitor_memory():
            while True:
                memory_samples.append(self.get_memory_mb())
                await asyncio.sleep(0.5)
        
        monitor_task = asyncio.create_task(monitor_memory())
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        operations = 0
        
        while time.time() < end_time:
            # Publish at target rate
            batch_start = time.time()
            batch_size = rate // 10  # 100ms batches
            
            for _ in range(batch_size):
                try:
                    publish_start = time.time()
                    await wrapped_bus.publish(BenchmarkEvent(
                        payload={"data": "x" * random.randint(50, 200)}
                    ))
                    latencies.append((time.time() - publish_start) * 1000)
                    operations += 1
                except Exception:
                    dropped += 1
            
            # Sleep to maintain rate
            elapsed = time.time() - batch_start
            if elapsed < 0.1:
                await asyncio.sleep(0.1 - elapsed)
        
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Wait for processing to complete
        await asyncio.sleep(1)
        
        # Calculate results
        actual_duration = time.time() - start_time
        p50, p95, p99 = self.calculate_percentiles(latencies)
        
        result = BenchmarkResult(
            test_name="Memory Stability",
            duration_seconds=actual_duration,
            total_operations=operations,
            throughput_ops_per_sec=operations / actual_duration,
            latencies_ms=latencies[:1000],
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            memory_start_mb=memory_samples[0] if memory_samples else 0,
            memory_peak_mb=max(memory_samples) if memory_samples else 0,
            memory_end_mb=memory_samples[-1] if memory_samples else 0,
            cpu_percent_avg=0.0,  # Not measured in this test
            errors=dropped,
            notes=f"Dropped {dropped} events due to backpressure"
        )
        
        # Stop the bus
        await wrapped_bus.stop()
        
        self.results.append(result)
        return result
    
    async def benchmark_chaos_testing(self, duration_seconds: int = 20, failure_rate: float = 0.1) -> BenchmarkResult:
        """Test resilience with random handler failures."""
        print(f"\n🔥 Running Chaos Testing Benchmark")
        print(f"   Duration: {duration_seconds}s with {failure_rate*100}% failure rate")
        
        bus = ResilientMessageBus(
            max_retries=3,
            retry_delay=0.01,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=1.0
        )
        
        processed = 0
        failed = 0
        retried = 0
        circuit_opened = 0
        
        async def chaos_handler(event: BenchmarkEvent) -> None:
            nonlocal processed, failed
            if random.random() < failure_rate:
                failed += 1
                raise Exception("Chaos monkey strikes!")
            processed += 1
            await asyncio.sleep(0.001)
        
        bus.register_event_handler(BenchmarkEvent, chaos_handler)
        
        # Start the message bus
        await bus.start()
        
        # Monitor circuit breaker state
        async def monitor_circuit_breaker():
            nonlocal circuit_opened
            while True:
                for handler_id, breaker in bus._circuit_breakers.items():
                    if breaker.state == breaker.State.OPEN:
                        circuit_opened += 1
                await asyncio.sleep(0.1)
        
        monitor_task = asyncio.create_task(monitor_circuit_breaker())
        
        memory_start = self.get_memory_mb()
        latencies: List[float] = []
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        operations = 0
        
        while time.time() < end_time:
            publish_start = time.time()
            try:
                await bus.publish(BenchmarkEvent(
                    payload={"chaos": True, "index": operations}
                ))
                latencies.append((time.time() - publish_start) * 1000)
                operations += 1
            except Exception:
                pass  # Circuit breaker might be open
            
            await asyncio.sleep(0.002)  # ~500 ops/sec
        
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Get final stats
        memory_end = self.get_memory_mb()
        dlq_size = bus._dead_letter_queue.qsize()
        
        # Calculate retries from metrics
        metrics = get_metrics_collector()
        if "events_failed_total" in metrics._counters:
            total_failures = metrics._counters["events_failed_total"].value
            retried = int(total_failures - dlq_size)  # Approximate retries
        
        actual_duration = time.time() - start_time
        p50, p95, p99 = self.calculate_percentiles(latencies)
        
        result = BenchmarkResult(
            test_name="Chaos Testing",
            duration_seconds=actual_duration,
            total_operations=operations,
            throughput_ops_per_sec=operations / actual_duration,
            latencies_ms=latencies[:1000],
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            memory_start_mb=memory_start,
            memory_peak_mb=memory_start,  # Not tracked in this test
            memory_end_mb=memory_end,
            cpu_percent_avg=0.0,  # Not measured
            errors=failed,
            notes=f"DLQ size: {dlq_size}, Circuit opened: {circuit_opened} times"
        )
        
        # Stop the bus
        await bus.stop()
        
        self.results.append(result)
        return result
    
    def print_results(self):
        """Print formatted benchmark results."""
        print("\n" + "="*80)
        print("📊 BENCHMARK RESULTS SUMMARY")
        print("="*80)
        
        for result in self.results:
            print(f"\n### {result.test_name}")
            print(f"Duration: {result.duration_seconds:.2f}s")
            print(f"Total Operations: {result.total_operations:,}")
            print(f"Throughput: {result.throughput_ops_per_sec:,.0f} ops/sec")
            print(f"Latency (ms): p50={result.latency_p50_ms:.2f}, p95={result.latency_p95_ms:.2f}, p99={result.latency_p99_ms:.2f}")
            print(f"Memory: Start={result.memory_start_mb:.1f}MB, Peak={result.memory_peak_mb:.1f}MB, End={result.memory_end_mb:.1f}MB")
            if result.cpu_percent_avg > 0:
                print(f"CPU Average: {result.cpu_percent_avg:.1f}%")
            if result.errors > 0:
                print(f"Errors: {result.errors}")
            if result.notes:
                print(f"Notes: {result.notes}")
        
        print("\n" + "="*80)
        print("🎯 PERFORMANCE TARGETS")
        print("="*80)
        
        # Check against targets
        sustained_result = next((r for r in self.results if r.test_name == "Sustained Throughput"), None)
        if sustained_result:
            target_met = sustained_result.throughput_ops_per_sec >= 10000
            status = "✅ PASS" if target_met else "❌ FAIL"
            print(f"Throughput Target (10k ops/sec): {status} - Achieved {sustained_result.throughput_ops_per_sec:,.0f} ops/sec")
            
            latency_met = sustained_result.latency_p99_ms < 10
            status = "✅ PASS" if latency_met else "❌ FAIL"
            print(f"Latency Target (p99 < 10ms): {status} - Achieved {sustained_result.latency_p99_ms:.2f}ms")
        
        print("\n" + "="*80)
        print("💡 OPTIMIZATION RECOMMENDATIONS")
        print("="*80)
        
        recommendations = []
        
        # Analyze results and provide recommendations
        for result in self.results:
            if result.throughput_ops_per_sec < 10000:
                recommendations.append(f"- {result.test_name}: Consider optimizing handler performance or increasing concurrency")
            if result.latency_p99_ms > 10:
                recommendations.append(f"- {result.test_name}: High p99 latency detected, investigate blocking operations")
            if result.memory_peak_mb - result.memory_start_mb > 100:
                recommendations.append(f"- {result.test_name}: Significant memory growth detected, check for memory leaks")
            if result.cpu_percent_avg > 80:
                recommendations.append(f"- {result.test_name}: High CPU usage, consider optimizing hot paths")
        
        if not recommendations:
            recommendations.append("- All performance targets met! Consider testing with higher loads.")
        
        for rec in recommendations:
            print(rec)
        
        print("\n" + "="*80)


async def main():
    """Run all benchmarks."""
    print("🏁 Starting LLMgine Message Bus Performance Benchmarks")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    runner = BenchmarkRunner()
    
    # Reset metrics before starting
    reset_metrics_collector()
    
    # Run benchmarks
    try:
        # 1. Sustained throughput test
        result = await runner.benchmark_sustained_throughput(
            target_ops=10000,  # 10k events
            target_rate=10000  # 10k/sec
        )
        print(f"   ✓ Completed: {result.throughput_ops_per_sec:,.0f} ops/sec")
        
        # 2. Latency under varying load
        result = await runner.benchmark_latency_under_load(
            ops_per_batch=1000,
            num_batches=10
        )
        print(f"   ✓ Completed: p99 latency {result.latency_p99_ms:.2f}ms")
        
        # 3. Memory stability test
        result = await runner.benchmark_memory_stability(
            duration_seconds=10,
            rate=5000
        )
        print(f"   ✓ Completed: Memory growth {result.memory_peak_mb - result.memory_start_mb:.1f}MB")
        
        # 4. Chaos testing
        result = await runner.benchmark_chaos_testing(
            duration_seconds=10,
            failure_rate=0.2
        )
        print(f"   ✓ Completed: Handled {result.errors} failures")
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Print results
    runner.print_results()
    
    print(f"\n🏁 Benchmarks completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    # Set in-memory database for benchmarking
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    asyncio.run(main())