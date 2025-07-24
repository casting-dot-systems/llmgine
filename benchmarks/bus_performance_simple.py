#!/usr/bin/env python3
"""
Simple performance benchmark for the LLMgine Message Bus (no database required).

Targets:
- Throughput: 10,000+ events/second sustained
- Latency: <10ms p99 for event publishing
- Memory: Bounded memory usage under load
"""

import asyncio
import time
import statistics
from typing import List
from dataclasses import dataclass, field

# We'll test the core bus directly without database dependencies
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event


@dataclass
class TestEvent(Event):
    """Simple test event."""
    data: str = ""


async def simple_throughput_test():
    """Test basic throughput without database."""
    print("\n🚀 Running Simple Throughput Test")
    print("   Target: 10,000 events in minimal time")
    
    bus = MessageBus()
    processed = 0
    
    async def handler(event: TestEvent) -> None:
        nonlocal processed
        processed += 1
    
    # Register handler
    bus.register_event_handler(TestEvent, handler)
    
    # Skip database initialization
    bus._initialized = True
    bus._running = True
    bus._stop_event.clear()
    
    # Start event processor without database
    asyncio.create_task(bus._process_events())
    
    # Measure throughput
    start_time = time.time()
    
    # Publish 10k events
    for i in range(10000):
        await bus.publish(TestEvent(data=f"event-{i}"))
    
    # Wait for processing
    while processed < 10000:
        await asyncio.sleep(0.01)
    
    duration = time.time() - start_time
    throughput = 10000 / duration
    
    print(f"   ✓ Processed 10,000 events in {duration:.2f}s")
    print(f"   ✓ Throughput: {throughput:,.0f} events/sec")
    
    # Stop the bus
    bus._running = False
    bus._stop_event.set()
    
    return throughput >= 10000  # Target met?


async def latency_test():
    """Test event publishing latency."""
    print("\n⏱️  Running Latency Test")
    print("   Measuring p50, p95, p99 latencies")
    
    bus = MessageBus()
    latencies: List[float] = []
    
    async def handler(event: TestEvent) -> None:
        pass  # Minimal handler
    
    bus.register_event_handler(TestEvent, handler)
    
    # Skip database
    bus._initialized = True
    bus._running = True
    bus._stop_event.clear()
    asyncio.create_task(bus._process_events())
    
    # Measure 1000 event publishing latencies
    for i in range(1000):
        start = time.time()
        await bus.publish(TestEvent(data=f"latency-{i}"))
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
    
    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.5)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
    
    print(f"   ✓ p50: {p50:.2f}ms")
    print(f"   ✓ p95: {p95:.2f}ms")
    print(f"   ✓ p99: {p99:.2f}ms")
    
    # Stop the bus
    bus._running = False
    bus._stop_event.set()
    
    return p99 < 10  # Target: p99 < 10ms


async def main():
    """Run simple benchmarks."""
    print("🏁 Starting Simple Message Bus Benchmarks")
    print("   (No database required)")
    
    # Run tests
    throughput_passed = await simple_throughput_test()
    latency_passed = await latency_test()
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    print(f"Throughput Target (10k/sec): {'✅ PASS' if throughput_passed else '❌ FAIL'}")
    print(f"Latency Target (p99 < 10ms): {'✅ PASS' if latency_passed else '❌ FAIL'}")
    print("="*60)
    
    if throughput_passed and latency_passed:
        print("\n✨ All performance targets met!")
    else:
        print("\n⚠️  Some targets not met. Consider optimization.")


if __name__ == "__main__":
    # Set in-memory database for benchmarking
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    asyncio.run(main())