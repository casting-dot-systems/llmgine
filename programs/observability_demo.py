"""Demonstration of the handler-based observability system using MessageBus."""

import asyncio
import sys
import os
import uuid # Added for trace IDs
from datetime import datetime # Added for trace timestamps
from typing import Any, List, Type, Optional, Dict # Added Optional and Dict
from dataclasses import dataclass, field

from llmgine.bus.bus import MessageBus, current_span_context
from llmgine.messages.commands import Command, CommandResult

# Adjust path to import from the llmgine source directory
# This assumes the script is run from the root of the 'llmgine' project directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
# Import events directly
from llmgine.observability import (
    LogEvent, LogLevel, ObservabilityBaseEvent as ObservabilityBaseEvent, # Renamed BaseEvent
    MetricEvent, Metric, 
    TraceEvent, SpanContext 
)
# Need the application Event base class
from llmgine.messages.events import Event

# --- Define Simple App Event for Testing ---
@dataclass(kw_only=True)
class DemoAppEvent(Event):
    """A simple application-specific event for the demo."""
    payload: Dict[str, Any]

# --- Define Simple Nested Command for Testing ---
@dataclass(kw_only=True)
class NestedCommandOuter(Command):
    """A simple nested command for the demo."""
    payload: Dict[str, Any]

@dataclass(kw_only=True)
class NestedCommandInner(Command):
    """A simple nested command for the demo."""
    payload: Dict[str, Any]

async def nested_command_handler_outer(command: NestedCommandOuter) -> str:
    """A simple nested command handler for the demo."""
    result = await MessageBus().execute(NestedCommandInner(payload={"data": "nested command inner data"}))
    result = CommandResult(original_command=command, success=True, result=result.result + "help")
    await MessageBus().publish(result)
    return result

async def nested_command_handler_inner(command: NestedCommandInner) -> str:
    """A simple nested command handler for the demo."""
    result = CommandResult(original_command=command, success=True, result="cheers")
    await MessageBus().publish(result)
    return result

# --- 2. Define Configuration --- 
@dataclass
class DemoConfig(ApplicationConfig):
    """Configuration specific to this demo."""
    name: str = "ObservabilityDemo"
    description: str = "Demonstrates handler-based observability via MessageBus."

    # Configure observability handlers via ApplicationConfig fields
    enable_console_handler: bool = True
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs/observability_handler_demo" # Specify log directory
    file_handler_log_filename: str = "handler_demo_events.jsonl" # Specify log filename

    # Standard Python logging level (adjust if needed)
    log_level: LogLevel = LogLevel.DEBUG


class DemoApplicationBootstrap(ApplicationBootstrap):
    # --- Register Command Handlers --- 
    def _register_command_handlers(self):
        MessageBus().register_command_handler(NestedCommandOuter, nested_command_handler_outer)
        MessageBus().register_command_handler(NestedCommandInner, nested_command_handler_inner)


async def main():
    """Runs the simplified observability demo."""
    print("--- Starting Simplified Observability Demo (Handler-Based) --- ")

    # --- 3. Bootstrap Application --- 
    print("\n--- Initializing & Bootstrapping ---")
    config = DemoConfig()
    bootstrap = DemoApplicationBootstrap(config=config)
    await bootstrap.bootstrap()
    await asyncio.sleep(0.1) 
    message_bus = bootstrap.message_bus
    log_file_path = bootstrap.message_bus.log_file if hasattr(bootstrap.message_bus, 'log_file') else 'N/A' # Get log file path if FileHandler was enabled
    print(f"Handlers registered. File logging (if enabled) target: {log_file_path}")

    # --- 4. Demonstrate Observability Features ---
    print("\n--- Demonstrating Observability Features --- ")
    source_component = "SimplifiedDemoScript"

    # --- Example: Manual Span Creation ---
    manual_span_context = None
    manual_span_token = None
    try:
        print("\n* Manually starting a span 'DemoEventPublishing'")
        manual_span_context = await message_bus.start_span(
            name="DemoEventPublishing", 
            source="SimplifiedDemoScript",
            attributes={"demo_purpose": "Wrapping event publications"}
        )
        # Set context for manual span
        manual_span_token = current_span_context.set(manual_span_context) 
        
        # Events published within this block will be children of 'DemoEventPublishing' 
        # if their handlers use bus.execute or manually propagate context.

        # 1. Publish LogEvent
        print("\n* Publishing LogEvent...")
        log_event = LogEvent(level=LogLevel.WARNING, message="Test warning log event.", source=source_component)
        await message_bus.publish(log_event)
        # Expected: Handlers receive and process LogEvent.

        # 2. Publish MetricEvent using emit_metric
        print("\n* Publishing MetricEvent using emit_metric...")
        await message_bus.emit_metric(
            name="test_metric", 
            value=42, 
            tags={"environment": "demo"},
            source=source_component
        )
        # Expected: Handlers receive MetricEvent (published by emit_metric).

        # 3. Execute Nested Commands (Demonstrates Automatic Tracing)
        print("\n* Executing Nested Commands (Automatic Tracing)...")
        await MessageBus().execute(NestedCommandOuter(payload={"data": "nested command outer data"}))
        # Expected:
        # - Trace events for NestedCommandOuter and NestedCommandInner are generated by bus.execute.
        # - NestedCommandInner's span will have NestedCommandOuter's span_id as parent_span_id 
        #   due to automatic context propagation via contextvars.
        # - Both spans will share the same trace_id.
        # - If manual_span_context was set, NestedCommandOuter's trace will be a child of 'DemoEventPublishing'.

        # 4. Publish DemoAppEvent (Application Event)
        print("\n* Publishing DemoAppEvent...")
        app_event = DemoAppEvent(payload={"data": "some application data"}, metadata={"user": "test_user"})
        await message_bus.publish(app_event)
        # Expected: FileHandler logs it, specific handlers (if any) receive it.

        # 5. Publish Random Event
        print("\n* Publishing Random Event...")
        @dataclass
        class RandomEvent(Event):
            msg: str = "Random Event"
        random_event = RandomEvent()
        await message_bus.publish(random_event)
        # Expected: Handlers receive and process.

    except Exception as e:
        print(f"\nError during event publishing demo: {e}")
        # Optionally end the span with error status if an exception occurs
        if manual_span_context:
            print("* Manually ending span 'DemoEventPublishing' with EXCEPTION status.")
            await message_bus.end_span(
                manual_span_context, 
                name="DemoEventPublishing", 
                status="EXCEPTION", 
                error=e,
                source="SimplifiedDemoScript (Error)"
            )
            manual_span_context = None # Prevent ending again in finally
    finally:
        # Ensure the manual span is always ended and context is reset
        if manual_span_context:
            print("* Manually ending span 'DemoEventPublishing' with OK status.")
            await message_bus.end_span(
                manual_span_context, 
                name="DemoEventPublishing", 
                status="OK",
                source="SimplifiedDemoScript (Finally)"
            )
        if manual_span_token:
            current_span_context.reset(manual_span_token)
            print("* Reset context var after manual span.")


    # Allow time for handlers to process events
    print("\n--- Allowing time for events to process/log ---")
    await asyncio.sleep(0.5)

    # --- 5. Shutdown --- 
    print("\n--- Shutting Down Application ---")
    await bootstrap.shutdown()

    print("\n--- Simplified Observability Demo Finished --- ")
    print(f"Check console output above and log file: {log_file_path}")

if __name__ == "__main__":
    # Add basic error handling for path setup
    if src_path not in sys.path:
        print(f"Error: Could not find source directory at {src_path}", file=sys.stderr)
        print("Please run this script from the root 'llmgine' project directory.", file=sys.stderr)
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred during the demo: {e}", file=sys.stderr)
        # import traceback
        # traceback.print_exc()
        sys.exit(1) 