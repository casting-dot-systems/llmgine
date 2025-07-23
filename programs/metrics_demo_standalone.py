#!/usr/bin/env python3
"""
Standalone Message Bus Metrics Demo

This demo showcases metrics without requiring database configuration.
"""

import asyncio
import os
from dataclasses import dataclass

from rich.console import Console
from rich import print as rprint

# Set a dummy DATABASE_URL to avoid startup errors
os.environ["DATABASE_URL"] = "sqlite:///dummy.db"

from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

console = Console()


# Simple command and event
@dataclass
class CalculateCommand(Command):
    """Command to perform a calculation."""
    a: float = 0.0
    b: float = 0.0
    operation: str = "add"


@dataclass 
class CalculationEvent(Event):
    """Event emitted when calculation is done."""
    result: float = 0.0
    operation: str = ""


async def calculate_handler(cmd: CalculateCommand) -> CommandResult:
    """Handle calculation command."""
    # Simulate some processing time
    await asyncio.sleep(0.01)
    
    if cmd.operation == "add":
        result = cmd.a + cmd.b
    elif cmd.operation == "multiply":
        result = cmd.a * cmd.b
    else:
        return CommandResult(
            success=False,
            command_id=cmd.command_id,
            error=f"Unknown operation: {cmd.operation}"
        )
    
    return CommandResult(
        success=True,
        command_id=cmd.command_id,
        result={"result": result, "operation": cmd.operation}
    )


async def log_calculation(event: CalculationEvent) -> None:
    """Log calculation event."""
    console.print(f"[dim]Calculation result: {event.result} (operation: {event.operation})[/dim]")


def format_metrics_summary(metrics: dict) -> str:
    """Format metrics into a readable summary."""
    lines = []
    
    # Commands
    cmd_sent = metrics["counters"]["commands_sent_total"]["value"]
    cmd_success = metrics["counters"]["commands_processed_total"]["value"]
    cmd_failed = metrics["counters"]["commands_failed_total"]["value"]
    
    lines.append("[bold cyan]Command Metrics:[/bold cyan]")
    lines.append(f"  Total sent: {int(cmd_sent)}")
    lines.append(f"  Successful: {int(cmd_success)}")
    lines.append(f"  Failed: {int(cmd_failed)}")
    
    if cmd_sent > 0:
        success_rate = (cmd_success / cmd_sent) * 100
        lines.append(f"  Success rate: {success_rate:.1f}%")
    
    # Events
    events_pub = metrics["counters"]["events_published_total"]["value"]
    events_proc = metrics["counters"]["events_processed_total"]["value"]
    events_fail = metrics["counters"]["events_failed_total"]["value"]
    
    lines.append("\n[bold cyan]Event Metrics:[/bold cyan]")
    lines.append(f"  Published: {int(events_pub)}")
    lines.append(f"  Processed: {int(events_proc)}")
    lines.append(f"  Failed: {int(events_fail)}")
    
    # Performance
    cmd_hist = metrics["histograms"]["command_processing_duration_seconds"]
    if cmd_hist["count"] > 0:
        lines.append("\n[bold cyan]Command Performance:[/bold cyan]")
        lines.append(f"  Count: {cmd_hist['count']}")
        lines.append(f"  p50 latency: {cmd_hist['percentiles']['p50']*1000:.1f}ms")
        lines.append(f"  p95 latency: {cmd_hist['percentiles']['p95']*1000:.1f}ms")
        lines.append(f"  p99 latency: {cmd_hist['percentiles']['p99']*1000:.1f}ms")
    
    event_hist = metrics["histograms"]["event_processing_duration_seconds"]
    if event_hist["count"] > 0:
        lines.append("\n[bold cyan]Event Handler Performance:[/bold cyan]")
        lines.append(f"  Count: {event_hist['count']}")
        lines.append(f"  p50 latency: {event_hist['percentiles']['p50']*1000:.1f}ms")
        lines.append(f"  p95 latency: {event_hist['percentiles']['p95']*1000:.1f}ms")
    
    # System state
    lines.append("\n[bold cyan]System State:[/bold cyan]")
    lines.append(f"  Queue size: {int(metrics['gauges']['queue_size']['value'])}")
    lines.append(f"  Registered handlers: {int(metrics['gauges']['registered_handlers']['value'])}")
    
    return "\n".join(lines)


async def main():
    """Run the metrics demo."""
    console.print("[bold blue]Message Bus Metrics Demo (Standalone)[/bold blue]\n")
    
    # Create and start bus
    bus = MessageBus()
    await bus.start()
    
    # Register handlers
    bus.register_command_handler(CalculateCommand, calculate_handler)
    bus.register_event_handler(CalculationEvent, log_calculation)
    
    console.print("[green]✓[/green] Message bus started\n")
    
    # Perform some calculations
    calculations = [
        (10, 20, "add"),
        (5, 6, "multiply"),
        (100, 25, "add"),
        (7, 8, "divide"),  # This will fail
        (3, 4, "multiply"),
    ]
    
    console.print("[bold]Executing calculations...[/bold]\n")
    
    for a, b, op in calculations:
        cmd = CalculateCommand(a=a, b=b, operation=op)
        result = await bus.execute(cmd)
        
        if result.success:
            console.print(f"[green]✓[/green] {a} {op} {b} = {result.result['result']}")
            
            # Publish event
            event = CalculationEvent(
                result=result.result['result'],
                operation=op,
                session_id=cmd.session_id
            )
            await bus.publish(event)
        else:
            console.print(f"[red]✗[/red] {a} {op} {b} failed: {result.error}")
    
    # Wait for events to process
    await asyncio.sleep(0.1)
    
    # Get and display metrics
    console.print("\n[bold]Metrics Summary:[/bold]\n")
    metrics = await bus.get_metrics()
    console.print(format_metrics_summary(metrics))
    
    # Show raw metrics structure for one example
    console.print("\n[bold]Example Raw Metric:[/bold]")
    console.print("[dim]counters.commands_sent_total:[/dim]")
    rprint(metrics["counters"]["commands_sent_total"])
    
    # Demonstrate Prometheus export format
    console.print("\n[bold]Prometheus Export Example:[/bold]")
    console.print("```")
    console.print("# HELP commands_sent_total Total number of commands sent to the bus")
    console.print("# TYPE commands_sent_total counter")
    console.print(f"commands_sent_total {metrics['counters']['commands_sent_total']['value']}")
    console.print("```")
    
    await bus.stop()
    console.print("\n[green]✓[/green] Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())