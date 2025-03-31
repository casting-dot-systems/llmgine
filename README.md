# LLMgine: An Event-Driven LLM Application Framework

[![Build status](https://img.shields.io/github/actions/workflow/status/nathan-luo/llmgine/main.yml?branch=main)](https://github.com/nathan-luo/llmgine/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/nathan-luo/llmgine)](https://img.shields.io/github/license/nathan-luo/llmgine)

LLMgine is a Python framework for building complex, event-driven applications powered by Large Language Models (LLMs). It provides a structured way to manage LLM interactions, tool usage, context, and observability.

## Key Features

- **Event-Driven Architecture**: Decouple components using a central `MessageBus`.
- **Command/Event Pattern**: Clearly separate actions (Commands) from notifications (Events).
- **Integrated Observability**: Automatic JSONL logging of all bus events (commands, results, LLM interactions, metrics, traces), with optional console output for metrics and traces, built into the `MessageBus`.
- **Context Management**: Flexible context handling (currently in-memory).
- **LLM Provider Abstraction**: Interface with different LLM providers (e.g., OpenAI).
- **Tool Management**: Define and manage tools/functions for LLMs to use.
- **Async First**: Built on `asyncio` for high performance.

## Core Concepts

### MessageBus

The `MessageBus` is the central nervous system of an LLMgine application. It handles:

1.  **Command Execution**: Receiving `Command` objects, finding the registered handler, executing it, and publishing resulting events (`CommandResultEvent`, `CommandErrorEvent`).
2.  **Event Publishing**: Broadcasting `Event` objects to any registered handlers.
3.  **Integrated Observability**: Automatically logging *all* events passing through it (application events and internal observability events like `MetricEvent`, `TraceEvent`) to a JSONL file. It also handles command execution tracing and optional console logging for metrics/traces based on its configuration.

```python
from llmgine.bus import MessageBus
from llmgine.messages.commands import YourCommand
from llmgine.messages.events import YourEvent

# Initialize the bus with observability configuration
# Log file will be created in 'logs/app_events.jsonl'
# Console output for metrics and traces is enabled by default
message_bus = MessageBus(
    log_dir="logs",
    log_filename="app_events.jsonl",
    enable_console_metrics=True,
    enable_console_traces=True
)

# Start the bus's background processing
await message_bus.start()

# Register handlers (example)
# message_bus.register_command_handler(YourCommand, handle_your_command)
# message_bus.register_event_handler(YourEvent, handle_your_event)

# Execute commands
# result = await message_bus.execute(YourCommand(...))

# Publish events (also happens automatically for command results)
# await message_bus.publish(YourEvent(...))

# --- Observability Events ---
# You can also publish standard observability events directly
from llmgine.observability import Metric, MetricEvent, TraceEvent, SpanContext

# Publish a metric
await message_bus.publish(MetricEvent(metrics=[Metric(name="files_processed", value=10)]))

# Publish a custom trace span (though command traces are automatic)
# trace_id = "custom_trace_1"
# span_id = "custom_span_1"
# span_context = SpanContext(trace_id=trace_id, span_id=span_id)
# await message_bus.publish(TraceEvent(name="Custom Operation Start", span_context=span_context, start_time=datetime.now().isoformat()))
# # ... perform operation ...
# await message_bus.publish(TraceEvent(name="Custom Operation End", span_context=span_context, end_time=datetime.now().isoformat(), status="OK"))

# Stop the bus
# await message_bus.stop()
```

### Commands

Commands represent requests to perform an action. They should be named imperatively (e.g., `ProcessDocumentCommand`). Each command type should have exactly one handler registered with the `MessageBus`.

### Events

Events represent something that has happened in the system. They should be named in the past tense (e.g., `DocumentProcessedEvent`). Multiple handlers can be registered for a single event type. The `MessageBus` automatically logs all events.

### LLMEngine

The `LLMEngine` orchestrates interactions with the LLM, managing context, tools, and communication with the LLM provider. It listens for commands like `PromptCommand` and publishes events like `LLMResponseEvent` and `ToolCallEvent`.

### Observability

Observability (logging, metrics, tracing) is integrated directly into the `MessageBus`.

-   **Logging**: All events published via `message_bus.publish()` are automatically serialized to a JSONL file configured during `MessageBus` initialization. Standard Python logging is used for internal bus/component messages.
-   **Metrics**: Publish `MetricEvent` objects to the `MessageBus`. Console output is configurable.
-   **Tracing**: Command execution spans (`TraceEvent`) are automatically generated and published by the `MessageBus`. You can publish custom `TraceEvent`s as well. Console output is configurable.

## Getting Started

*(Add setup and basic usage instructions here)*

## Project Structure Ideas

```
my_llm_app/
├── main.py                 # Application entry point
├── config.py               # Configuration loading
├── bootstrap.py            # ApplicationBootstrap implementation
├── commands/
│   ├── __init__.py
│   └── process_data.py     # Example: ProcessDataCommand
├── events/
│   ├── __init__.py
│   └── data_processed.py   # Example: DataProcessedEvent
├── handlers/
│   ├── __init__.py
│   └── process_data_handler.py # Example: Handler for ProcessDataCommand
├── services/               # Business logic components
│   └── data_processor.py
├── logs/                   # Default log directory
└── requirements.txt
```

## Contributing

*(Add contribution guidelines here)*

## License

*(Add license information here)*