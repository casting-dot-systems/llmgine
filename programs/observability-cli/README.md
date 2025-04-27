# LLMgine Observability CLI

A set of rich, polished command-line tools for visualizing and analyzing LLMgine event logs.

## Features

- **Interactive Log Viewer**: Navigate and filter log events with a rich terminal UI
- **Log Statistics**: Generate and visualize statistics from log files
- **Log Search**: Find events using various search criteria
- **Trace Visualization**: Visualize event timelines and tool call graphs
- **Unified CLI**: Single entry point for all observability tools

## Installation

The tools are included as part of the LLMgine project. No additional installation is required beyond the standard LLMgine dependencies.

Make sure you have the `rich` library installed:

```
pip install rich
```

## Usage

### Unified CLI

The `logcli.py` script provides a unified interface to all the tools:

```
python -m programs.observability-cli.logcli [command] [options]
```

Available commands:

- `list`: List available log files
- `view [LOG_FILE]`: Open interactive log viewer
- `stats [LOG_FILE]`: Show statistics for a log file
- `search [LOG_FILE] [OPTIONS]`: Search for events in a log file
- `trace [LOG_FILE] [OPTIONS]`: Visualize event traces

For example:

```
python -m programs.observability-cli.logcli list
python -m programs.observability-cli.logcli view logs/events_20250420_170615.jsonl
python -m programs.observability-cli.logcli stats logs/events_20250420_170615.jsonl --summary
```

### Interactive Log Viewer

```
python -m programs.observability-cli.log_viewer [LOG_FILE]
```

Options:
- `--list` or `-l`: List available log files
- `--session` or `-s`: Filter by session ID
- `--type` or `-t`: Filter by event type
- `--event` or `-e`: Show details for event ID
- `--timeline`: Show timeline view

In the interactive mode, you'll see a command prompt where you can enter commands:

```
llmgine-logs> help
```

Available commands:
- `help`, `h`: Show help information
- `view [PAGE]`, `v`: View events (optionally specify page number)
- `next`, `n`: Go to next page
- `prev`, `p`: Go to previous page
- `filter <NAME> <VALUE>`, `f`: Filter events (e.g., `filter session_id UBWJK`)
- `clear`, `c`: Clear all filters
- `sessions`, `s`: List available sessions
- `types`, `t`: List event types
- `detail <EVENT_ID>`, `d`: Show event details
- `timeline [SESSION_ID]`, `l`: Show event timeline
- `stats`, `st`: Show log statistics
- `quit`, `q`: Exit the viewer

The prompt shows active filters:

```
llmgine-logs[session_id=UBWJK]> 
```

### Log Statistics

```
python -m programs.observability-cli.log_stats [LOG_FILE]
```

Options:
- `--summary` or `-s`: Print summary only
- `--events` or `-e`: Print event type distribution
- `--sessions` or `-S`: Print session statistics
- `--time` or `-t`: Print time series analysis
- `--sequences` or `-q`: Print common event sequences

### Log Search

```
python -m programs.observability-cli.log_search [LOG_FILE] [OPTIONS]
```

Options:
- `--id` or `-i`: Search by event ID pattern
- `--session` or `-s`: Search by session ID
- `--type` or `-t`: Search by event type
- `--start-time`: Search from this time (ISO format)
- `--end-time`: Search until this time (ISO format)
- `--pattern` or `-p`: Search by content pattern (regex)
- `--field` or `-f`: Specific field to search in
- `--format`: Output format (table, json, compact)
- `--context` or `-c`: Show context around matching events
- `--context-lines`: Number of context lines (default: 5)

### Trace Visualization

```
python -m programs.observability-cli.traceviz [LOG_FILE] [OPTIONS]
```

Options:
- `--list` or `-l`: List available sessions
- `--session` or `-s`: Session ID to visualize
- `--event` or `-e`: Show details for event ID

## Examples

1. View an interactive visualization of a log file:

```
python -m programs.observability-cli.log_viewer logs/events_20250420_170615.jsonl
```

2. Generate statistics for a log file:

```
python -m programs.observability-cli.log_stats logs/events_20250420_170615.jsonl
```

3. Search for specific events:

```
python -m programs.observability-cli.log_search logs/events_20250420_170615.jsonl --type ToolCalledEvent --format json
```

4. Visualize traces for a specific session:

```
python -m programs.observability-cli.traceviz logs/events_20250420_170615.jsonl --session UBWJK
```

5. Using the unified CLI:

```
python -m programs.observability-cli.logcli trace logs/events_20250420_170615.jsonl --session UBWJK
```

## Implementation Notes

### Key Features

- **Robust JSON Parsing**: Handles multi-line JSON objects in log files, with fallback repair mechanisms
- **Pagination**: View large log files with next/previous page navigation
- **Flexible Filtering**: Filter events by session ID, event type, event ID, and timestamp
- **Rich Visualizations**: Colorized event types, syntax highlighting, and tree-based timeline views
- **Command Completion**: Tab completion for commands and common values (in interactive mode)
- **Statistics**: Event type distribution, session statistics, and time series analysis

### Design Decisions

- **Command Line Interface**: Uses a simple text-based command prompt for maximum reliability
- **Modular Architecture**: Separate tools for viewing, searching, and analyzing logs
- **Unified Entry Point**: Single CLI that dispatches to appropriate tools
- **Robust Error Handling**: Graceful handling of malformed log entries and user input

### Technical Implementation

- Built with the Rich library for attractive terminal output
- Event-driven approach to match LLMgine's architecture
- Clear separation between data processing and presentation
- Compatible with all LLMgine log formats and event types