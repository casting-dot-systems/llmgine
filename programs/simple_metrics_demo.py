#!/usr/bin/env python3
"""
Simple Message Bus Metrics Demo

A quick demonstration of how metrics are collected and accessed in the message bus.
"""

import asyncio
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich import print as rprint

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

console = Console()


# Simple command and event
@dataclass
class GreetCommand(Command):
    name: str = ""


@dataclass 
class GreetingEvent(Event):
    greeting: str = ""


async def greet_handler(cmd: GreetCommand) -> CommandResult:
    """Handle greet command."""
    greeting = f"Hello, {cmd.name}!"
    return CommandResult(
        success=True,
        command_id=cmd.command_id,
        result={"greeting": greeting}
    )


async def log_greeting(event: GreetingEvent) -> None:
    """Log greeting event."""
    console.print(f"[dim]Event received: {event.greeting}[/dim]")


async def slow_handler(event: GreetingEvent) -> None:
    """Simulate a slow event handler."""
    await asyncio.sleep(0.1)  # 100ms delay
    

async def failing_handler(event: GreetingEvent) -> None:
    """Handler that always fails."""
    raise Exception("This handler always fails!")


def print_metrics(metrics: dict):
    """Pretty print metrics."""
    console.print("\n[bold cyan]Message Bus Metrics[/bold cyan]")
    
    # Counters
    console.print("\n[yellow]Counters:[/yellow]")
    for name, data in metrics["counters"].items():
        if data["value"] > 0:
            console.print(f"  {name}: {int(data['value'])}")
    
    # Histograms
    console.print("\n[yellow]Histograms:[/yellow]")
    for name, data in metrics["histograms"].items():
        if data["count"] > 0:
            p50 = data["percentiles"]["p50"]
            p95 = data["percentiles"]["p95"]
            console.print(f"  {name}:")
            console.print(f"    count: {data['count']}")
            console.print(f"    p50: {p50*1000:.1f}ms" if p50 else "    p50: N/A")
            console.print(f"    p95: {p95*1000:.1f}ms" if p95 else "    p95: N/A")
    
    # Gauges
    console.print("\n[yellow]Gauges:[/yellow]")
    for name, data in metrics["gauges"].items():
        value = int(data["value"])
        if value > 0 or name in ["queue_size", "registered_handlers"]:
            console.print(f"  {name}: {value}")


async def main():
    """Run simple metrics demo."""
    console.print("[bold blue]Simple Message Bus Metrics Demo[/bold blue]\n")
    
    # Create and start bus
    bus = MessageBus()
    await bus.start()
    
    # Register handlers
    bus.register_command_handler(GreetCommand, greet_handler)
    bus.register_event_handler(GreetingEvent, log_greeting)
    bus.register_event_handler(GreetingEvent, slow_handler)
    bus.register_event_handler(GreetingEvent, failing_handler)
    
    console.print("[green]✓[/green] Bus started with handlers registered\n")
    
    # Show initial metrics
    metrics = await bus.get_metrics()
    console.print("Initial state:")
    print_metrics(metrics)
    
    # Execute some commands
    console.print("\n[bold]Executing commands...[/bold]")
    
    for name in ["Alice", "Bob", "Charlie"]:
        cmd = GreetCommand(name=name)
        result = await bus.execute(cmd)
        
        if result.success:
            console.print(f"[green]✓[/green] Greeted {name}")
            
            # Publish event
            event = GreetingEvent(
                greeting=result.result["greeting"],
                session_id=cmd.session_id
            )
            await bus.publish(event)
    
    # Wait for events to process
    await asyncio.sleep(0.2)
    
    # Show metrics after processing
    console.print("\n[bold]After processing:[/bold]")
    metrics = await bus.get_metrics()
    print_metrics(metrics)
    
    # Demonstrate metric details
    console.print("\n[bold]Metric Details:[/bold]")
    
    # Command success rate
    cmd_sent = metrics["counters"]["commands_sent_total"]["value"]
    cmd_success = metrics["counters"]["commands_processed_total"]["value"]
    cmd_failed = metrics["counters"]["commands_failed_total"]["value"]
    
    if cmd_sent > 0:
        success_rate = (cmd_success / cmd_sent) * 100
        console.print(f"\nCommand success rate: {success_rate:.1f}%")
        console.print(f"  Total: {int(cmd_sent)}, Success: {int(cmd_success)}, Failed: {int(cmd_failed)}")
    
    # Event processing
    events_pub = metrics["counters"]["events_published_total"]["value"]
    events_proc = metrics["counters"]["events_processed_total"]["value"]
    events_fail = metrics["counters"]["events_failed_total"]["value"]
    
    console.print(f"\nEvent processing:")
    console.print(f"  Published: {int(events_pub)}")
    console.print(f"  Processed: {int(events_proc)} (multiple handlers per event)")
    console.print(f"  Failed: {int(events_fail)}")
    
    # Performance metrics
    cmd_hist = metrics["histograms"]["command_processing_duration_seconds"]
    event_hist = metrics["histograms"]["event_processing_duration_seconds"]
    
    if cmd_hist["count"] > 0:
        console.print(f"\nCommand performance:")
        console.print(f"  Median latency: {cmd_hist['percentiles']['p50']*1000:.1f}ms")
        console.print(f"  95th percentile: {cmd_hist['percentiles']['p95']*1000:.1f}ms")
    
    if event_hist["count"] > 0:
        console.print(f"\nEvent handler performance:")
        console.print(f"  Median latency: {event_hist['percentiles']['p50']*1000:.1f}ms")
        console.print(f"  95th percentile: {event_hist['percentiles']['p95']*1000:.1f}ms")
        console.print(f"  (includes slow 100ms handler)")
    
    # Clean up
    await bus.stop()
    console.print("\n[green]✓[/green] Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())