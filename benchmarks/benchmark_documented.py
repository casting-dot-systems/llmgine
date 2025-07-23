#!/usr/bin/env python3
"""
Performance benchmark following the documented MessageBus usage patterns.

This benchmark tests the message bus performance without requiring database setup.
"""

import asyncio
import time
import statistics
from dataclasses import dataclass
from typing import List

from llmgine.bus import MessageBus
from llmgine.messages import Event


@dataclass
class BenchmarkEvent(Event):
    """Event for benchmarking."""
    data: str = ""
    index: int = 0


async def benchmark_throughput():
    """Test sustained throughput."""
    print("\n🚀 Testing Throughput (10k events)")
    
    bus = MessageBus()
    processed = 0
    
    async def handler(event: BenchmarkEvent) -> None:
        nonlocal processed
        processed += 1
    
    # Register handler at bus scope
    bus.register_event_handler(BenchmarkEvent, handler)
    
    # Start the bus properly
    await bus.start()
    
    # Time the publishing of 10k events
    start_time = time.time()
    
    for i in range(10000):
        await bus.publish(BenchmarkEvent(data=f"test-{i}", index=i))
    
    # Wait for all events to be processed
    while processed < 10000:
        await asyncio.sleep(0.001)
    
    duration = time.time() - start_time
    throughput = 10000 / duration
    
    # Stop the bus properly
    await bus.stop()
    
    print(f"   Processed: {processed:,} events")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Throughput: {throughput:,.0f} events/sec")
    print(f"   Target (10k/sec): {'✅ PASS' if throughput >= 10000 else '❌ FAIL'}")
    
    return throughput


async def benchmark_latency():
    """Test event publishing latency."""
    print("\n⏱️  Testing Latency (1k events)")
    
    bus = MessageBus()
    latencies: List[float] = []
    
    async def handler(event: BenchmarkEvent) -> None:
        pass  # Minimal handler
    
    bus.register_event_handler(BenchmarkEvent, handler)
    await bus.start()
    
    # Measure latency for 1000 publishes
    for i in range(1000):
        start = time.time()
        await bus.publish(BenchmarkEvent(data=f"latency-{i}"))
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
    
    await bus.stop()
    
    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    p50 = sorted_latencies[int(n * 0.5)]
    p95 = sorted_latencies[int(n * 0.95)]
    p99 = sorted_latencies[int(n * 0.99)]
    
    print(f"   Samples: {len(latencies)}")
    print(f"   p50: {p50:.3f}ms")
    print(f"   p95: {p95:.3f}ms")
    print(f"   p99: {p99:.3f}ms")
    print(f"   Target (p99 < 10ms): {'✅ PASS' if p99 < 10 else '❌ FAIL'}")
    
    return p99


async def benchmark_session_cleanup():
    """Test session handler cleanup performance."""
    print("\n🧹 Testing Session Cleanup")
    
    bus = MessageBus()
    await bus.start()
    
    processed_counts = {}
    
    # Create 100 sessions with handlers
    start = time.time()
    
    for i in range(100):
        session_id = f"session-{i}"
        processed_counts[session_id] = 0
        
        async with bus.session(session_id) as session:
            # Create a closure to capture session_id
            def make_handler(sid):
                async def handler(event: BenchmarkEvent) -> None:
                    processed_counts[sid] += 1
                return handler
            
            # Register handler for this session
            session.register_event_handler(
                BenchmarkEvent, 
                make_handler(session_id)
            )
            
            # Publish one event per session (use bus.publish with session_id)
            await bus.publish(BenchmarkEvent(
                data=f"test-{i}",
                session_id=session.session_id
            ))
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    duration = time.time() - start
    
    # Verify each session processed exactly one event
    all_one = all(count == 1 for count in processed_counts.values())
    
    await bus.stop()
    
    print(f"   Sessions created: 100")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Cleanup verification: {'✅ PASS' if all_one else '❌ FAIL'}")
    
    return all_one


async def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("📊 LLMgine Message Bus Performance Benchmarks")
    print("=" * 60)
    
    try:
        # Run benchmarks
        throughput = await benchmark_throughput()
        p99_latency = await benchmark_latency()
        session_ok = await benchmark_session_cleanup()
        
        # Summary
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        all_passed = (
            throughput >= 10000 and 
            p99_latency < 10 and 
            session_ok
        )
        
        if all_passed:
            print("✅ All performance targets met!")
            print("\nThe message bus achieves:")
            print(f"- {throughput:,.0f} events/second throughput")
            print(f"- {p99_latency:.3f}ms p99 latency")
            print("- Proper session cleanup")
        else:
            print("⚠️  Some performance targets not met")
            if throughput < 10000:
                print(f"- Throughput: {throughput:,.0f}/sec (target: 10k/sec)")
            if p99_latency >= 10:
                print(f"- Latency p99: {p99_latency:.3f}ms (target: <10ms)")
            if not session_ok:
                print("- Session cleanup failed")
        
        # Save results
        with open("benchmarks/performance_results.txt", "w") as f:
            f.write("LLMgine Message Bus Performance Results\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Throughput: {throughput:,.0f} events/second\n")
            f.write(f"Latency p99: {p99_latency:.3f}ms\n")
            f.write(f"Session cleanup: {'PASS' if session_ok else 'FAIL'}\n")
            f.write(f"\nAll targets met: {'YES' if all_passed else 'NO'}\n")
            
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Set in-memory database for benchmarking
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    asyncio.run(main())