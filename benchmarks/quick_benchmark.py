#!/usr/bin/env python3
"""Quick benchmark to verify performance targets."""

import asyncio
import time
from dataclasses import dataclass, field
from llmgine.messages.events import Event


@dataclass 
class PerfEvent(Event):
    """Performance test event."""
    index: int = 0
    

async def run_benchmark():
    """Run a quick performance test."""
    from llmgine.bus.bus import MessageBus
    
    print("Running quick performance benchmark...")
    
    # Create bus
    bus = MessageBus()
    processed = 0
    
    async def handler(event: PerfEvent):
        nonlocal processed
        processed += 1
    
    bus.register_event_handler(PerfEvent, handler)
    
    # Bypass database by setting initialized
    bus._initialized = True
    bus._running = True
    
    # Start event processor
    processor_task = asyncio.create_task(bus._process_events())
    
    # Time 10k events
    start = time.time()
    
    for i in range(10000):
        await bus.publish(PerfEvent(index=i))
    
    # Wait for processing
    timeout = 10  # seconds
    wait_start = time.time()
    while processed < 10000 and time.time() - wait_start < timeout:
        await asyncio.sleep(0.01)
    
    duration = time.time() - start
    
    # Stop processing
    bus._running = False
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    # Results
    throughput = processed / duration
    print(f"\nResults:")
    print(f"- Processed: {processed:,} events")
    print(f"- Duration: {duration:.2f}s")
    print(f"- Throughput: {throughput:,.0f} events/sec")
    print(f"- Target (10k/sec): {'✅ PASS' if throughput >= 10000 else '❌ FAIL'}")
    
    return throughput


if __name__ == "__main__":
    # Set in-memory database for benchmarking
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    throughput = asyncio.run(run_benchmark())
    
    # Create a benchmark result file
    with open("benchmarks/benchmark_results.txt", "w") as f:
        f.write(f"Message Bus Performance Benchmark Results\n")
        f.write(f"========================================\n\n")
        f.write(f"Throughput: {throughput:,.0f} events/second\n")
        f.write(f"Target: 10,000 events/second\n")
        f.write(f"Status: {'PASS' if throughput >= 10000 else 'FAIL'}\n\n")
        f.write(f"Note: This is a simplified benchmark without database dependencies.\n")
        f.write(f"Full benchmarks in bus_performance.py require DATABASE_URL to be set.\n")