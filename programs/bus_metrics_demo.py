#!/usr/bin/env python3
"""
Message Bus Metrics Demo

This demo showcases the comprehensive metrics collection capabilities of the
LLMgine message bus, including:
- Command and event processing metrics
- Error tracking and resilience metrics
- Real-time performance monitoring
- Prometheus-compatible export format
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from llmgine.bus.bus import MessageBus
from llmgine.bus.resilience import ResilientMessageBus, RetryConfig
from llmgine.bus.backpressure import BackpressureStrategy
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

console = Console()

# Define sample commands and events
@dataclass
class ProcessOrderCommand(Command):
    """Command to process an order."""
    order_id: str = ""
    amount: float = 0.0


@dataclass
class OrderProcessedEvent(Event):
    """Event emitted when order is processed."""
    order_id: str = ""
    amount: float = 0.0


@dataclass
class SendNotificationCommand(Command):
    """Command to send a notification."""
    user_id: str = ""
    message: str = ""


@dataclass
class NotificationSentEvent(Event):
    """Event emitted when notification is sent."""
    user_id: str = ""
    
    
# Command handlers with simulated processing times
async def handle_process_order(cmd: ProcessOrderCommand) -> CommandResult:
    """Process an order with simulated delay."""
    # Simulate processing time (20-100ms)
    await asyncio.sleep(random.uniform(0.02, 0.1))
    
    # 10% chance of failure
    if random.random() < 0.1:
        raise Exception(f"Failed to process order {cmd.order_id}")
    
    return CommandResult(
        success=True,
        command_id=cmd.command_id,
        result={"order_id": cmd.order_id, "status": "processed"}
    )


async def handle_send_notification(cmd: SendNotificationCommand) -> CommandResult:
    """Send a notification with simulated delay."""
    # Simulate fast processing (5-20ms)
    await asyncio.sleep(random.uniform(0.005, 0.02))
    
    # 5% chance of failure
    if random.random() < 0.05:
        raise Exception(f"Failed to send notification to {cmd.user_id}")
    
    return CommandResult(
        success=True,
        command_id=cmd.command_id,
        result={"user_id": cmd.user_id, "sent": True}
    )


# Event handlers
async def handle_order_processed(event: OrderProcessedEvent) -> None:
    """Handle order processed event."""
    # Simulate downstream processing (10-50ms)
    await asyncio.sleep(random.uniform(0.01, 0.05))
    
    # 2% chance of failure
    if random.random() < 0.02:
        raise Exception(f"Failed to handle order event {event.order_id}")


async def send_order_notification(event: OrderProcessedEvent) -> None:
    """Send notification for processed order."""
    # Simulate notification sending (5-15ms)
    await asyncio.sleep(random.uniform(0.005, 0.015))


async def handle_notification_sent(event: NotificationSentEvent) -> None:
    """Log notification sent event."""
    # Very fast handler (1-5ms)
    await asyncio.sleep(random.uniform(0.001, 0.005))


def create_metrics_table(metrics: dict) -> Table:
    """Create a rich table displaying metrics."""
    table = Table(title="Message Bus Metrics", expand=True)
    table.add_column("Metric", style="cyan", width=40)
    table.add_column("Value", style="green", width=20)
    table.add_column("Description", style="dim", width=50)
    
    # Add counters
    table.add_section()
    for name, data in metrics["counters"].items():
        table.add_row(
            f"[bold]{name}[/bold]",
            str(int(data["value"])),
            data["description"]
        )
    
    # Add histograms
    table.add_section()
    for name, data in metrics["histograms"].items():
        if data["count"] > 0:
            p50 = data["percentiles"]["p50"]
            p95 = data["percentiles"]["p95"]
            p99 = data["percentiles"]["p99"]
            
            table.add_row(
                f"[bold]{name}[/bold]",
                f"p50: {p50:.3f}s" if p50 else "N/A",
                data["description"]
            )
            table.add_row(
                f"  └─ percentiles",
                f"p95: {p95:.3f}s" if p95 else "N/A",
                ""
            )
            table.add_row(
                "",
                f"p99: {p99:.3f}s" if p99 else "N/A",
                ""
            )
    
    # Add gauges
    table.add_section()
    for name, data in metrics["gauges"].items():
        value = data["value"]
        if name == "circuit_breaker_state":
            states = ["CLOSED", "OPEN", "HALF-OPEN"]
            value_str = states[int(value)] if 0 <= value <= 2 else str(value)
        elif name == "backpressure_active":
            value_str = "YES" if value else "NO"
        else:
            value_str = str(int(value))
            
        table.add_row(
            f"[bold]{name}[/bold]",
            value_str,
            data["description"]
        )
    
    return table


def export_prometheus_format(metrics: dict) -> str:
    """Export metrics in Prometheus format."""
    lines = []
    
    # Export counters
    for name, data in metrics["counters"].items():
        lines.append(f'# HELP {name} {data["description"]}')
        lines.append(f'# TYPE {name} counter')
        lines.append(f'{name} {data["value"]}')
        lines.append("")
    
    # Export histograms
    for name, data in metrics["histograms"].items():
        if data["count"] > 0:
            lines.append(f'# HELP {name} {data["description"]}')
            lines.append(f'# TYPE {name} histogram')
            
            # Export buckets
            for bucket, count in data["buckets"].items():
                if bucket != float('inf'):
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
            
            lines.append(f'{name}_sum {data["sum"]:.6f}')
            lines.append(f'{name}_count {data["count"]}')
            lines.append("")
    
    # Export gauges
    for name, data in metrics["gauges"].items():
        lines.append(f'# HELP {name} {data["description"]}')
        lines.append(f'# TYPE {name} gauge')
        lines.append(f'{name} {data["value"]}')
        lines.append("")
    
    return "\n".join(lines)


async def generate_load(bus: MessageBus, duration: int = 30):
    """Generate simulated load on the message bus."""
    start_time = time.time()
    order_count = 0
    notification_count = 0
    
    while time.time() - start_time < duration:
        # Generate orders at ~20/sec
        if random.random() < 0.4:
            order_id = f"ORD-{order_count:04d}"
            amount = random.uniform(10.0, 500.0)
            
            cmd = ProcessOrderCommand(order_id=order_id, amount=amount)
            result = await bus.execute(cmd)
            
            if result.success:
                # Publish event
                event = OrderProcessedEvent(
                    order_id=order_id,
                    amount=amount,
                    session_id=cmd.session_id
                )
                await bus.publish(event)
            
            order_count += 1
        
        # Generate notifications at ~10/sec
        if random.random() < 0.2:
            user_id = f"USR-{random.randint(1, 100):03d}"
            message = f"Notification #{notification_count}"
            
            cmd = SendNotificationCommand(user_id=user_id, message=message)
            result = await bus.execute(cmd)
            
            if result.success:
                event = NotificationSentEvent(
                    user_id=user_id,
                    session_id=cmd.session_id
                )
                await bus.publish(event)
            
            notification_count += 1
        
        # Small delay to control rate
        await asyncio.sleep(0.02)


async def main():
    """Run the metrics demo."""
    console.print("[bold blue]LLMgine Message Bus Metrics Demo[/bold blue]\n")
    
    # Create resilient message bus with metrics
    bus = ResilientMessageBus(
        retry_config=RetryConfig(max_retries=3, initial_delay=0.1),
        event_queue_size=10000,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST
    )
    
    await bus.start()
    
    # Register command handlers
    bus.register_command_handler(ProcessOrderCommand, handle_process_order)
    bus.register_command_handler(SendNotificationCommand, handle_send_notification)
    
    # Register event handlers
    bus.register_event_handler(OrderProcessedEvent, handle_order_processed)
    bus.register_event_handler(OrderProcessedEvent, send_order_notification)
    bus.register_event_handler(NotificationSentEvent, handle_notification_sent)
    
    console.print("[green]✓[/green] Message bus started and handlers registered\n")
    
    # Create live display
    layout = Layout()
    
    with Live(layout, refresh_per_second=2, console=console) as live:
        # Generate load and update display
        load_task = asyncio.create_task(generate_load(bus, duration=30))
        
        console.print("[yellow]Generating load for 30 seconds...[/yellow]\n")
        
        while not load_task.done():
            # Get current metrics
            metrics = await bus.get_metrics()
            
            # Update display
            table = create_metrics_table(metrics)
            layout.update(Panel(table, title="Real-time Metrics", border_style="blue"))
            
            await asyncio.sleep(0.5)
        
        await load_task
    
    # Final metrics
    console.print("\n[bold green]Load generation complete![/bold green]\n")
    
    final_metrics = await bus.get_metrics()
    final_table = create_metrics_table(final_metrics)
    console.print(final_table)
    
    # Export in Prometheus format
    console.print("\n[bold]Prometheus Export Format:[/bold]")
    console.print(Panel(export_prometheus_format(final_metrics), expand=False))
    
    # Calculate throughput
    total_commands = (
        final_metrics["counters"]["commands_processed_total"]["value"] +
        final_metrics["counters"]["commands_failed_total"]["value"]
    )
    total_events = final_metrics["counters"]["events_published_total"]["value"]
    
    console.print(f"\n[bold]Performance Summary:[/bold]")
    console.print(f"Commands processed: {total_commands:.0f} ({total_commands/30:.1f}/sec)")
    console.print(f"Events published: {total_events:.0f} ({total_events/30:.1f}/sec)")
    
    # Command latency
    cmd_histogram = final_metrics["histograms"]["command_processing_duration_seconds"]
    if cmd_histogram["count"] > 0:
        console.print(f"\nCommand latency:")
        console.print(f"  p50: {cmd_histogram['percentiles']['p50']*1000:.1f}ms")
        console.print(f"  p95: {cmd_histogram['percentiles']['p95']*1000:.1f}ms")
        console.print(f"  p99: {cmd_histogram['percentiles']['p99']*1000:.1f}ms")
    
    # Event latency
    event_histogram = final_metrics["histograms"]["event_processing_duration_seconds"]
    if event_histogram["count"] > 0:
        console.print(f"\nEvent handler latency:")
        console.print(f"  p50: {event_histogram['percentiles']['p50']*1000:.1f}ms")
        console.print(f"  p95: {event_histogram['percentiles']['p95']*1000:.1f}ms")
        console.print(f"  p99: {event_histogram['percentiles']['p99']*1000:.1f}ms")
    
    await bus.stop()
    console.print("\n[green]✓[/green] Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())