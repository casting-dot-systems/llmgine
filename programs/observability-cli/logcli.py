#!/usr/bin/env python3
"""
Unified CLI for LLMgine observability tools.
"""
import os
import sys
from pathlib import Path
from typing import List, Optional

import rich.box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def get_default_logs_dir() -> Path:
    """Get the default logs directory."""
    return Path(os.path.expanduser("~/dev/llmgine/logs"))


def list_log_files(console: Console) -> List[Path]:
    """List available log files.
    
    Args:
        console: Rich console instance
        
    Returns:
        List of log file paths
    """
    logs_dir = get_default_logs_dir()
    if not logs_dir.exists():
        console.print(f"Logs directory not found: {logs_dir}", style="bold red")
        return []
    
    log_files = sorted(logs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return log_files


def print_available_logs(console: Console) -> None:
    """Print a list of available log files.
    
    Args:
        console: Rich console instance
    """
    log_files = list_log_files(console)
    
    if not log_files:
        console.print("No log files found", style="bold yellow")
        return
    
    table = Table(title="Available Log Files")
    table.add_column("Filename", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Modified", style="yellow")
    
    for log_file in log_files:
        stats = log_file.stat()
        size = f"{stats.st_size / 1024:.1f} KB"
        modified = stats.st_mtime
        import datetime
        modified_str = datetime.datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(log_file.name, size, modified_str)
        
    console.print(table)


def print_help(console: Console) -> None:
    """Print help information.
    
    Args:
        console: Rich console instance
    """
    console.print(Panel(
        "LLMgine Observability Tools",
        style="bold white on blue"
    ))
    
    commands = [
        ["logcli list", "List available log files"],
        ["logcli view [LOG_FILE]", "Open interactive log viewer"],
        ["logcli stats [LOG_FILE]", "Show statistics for a log file"],
        ["logcli search [LOG_FILE] [OPTIONS]", "Search for events in a log file"],
        ["logcli trace [LOG_FILE] [OPTIONS]", "Visualize event traces"],
    ]
    
    table = Table(title="Available Commands", box=rich.box.ROUNDED)
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
        
    console.print(table)
    
    console.print("\nExamples:", style="bold yellow")
    console.print("  logcli list", style="bright_black")
    console.print("  logcli view events_20250420_170615.jsonl", style="bright_black")
    console.print("  logcli stats events_20250420_170615.jsonl --summary", style="bright_black")
    console.print("  logcli search events_20250420_170615.jsonl --session ABCDE", style="bright_black")
    console.print("  logcli trace events_20250420_170615.jsonl --session ABCDE", style="bright_black")


def main() -> None:
    """Main entry point."""
    console = Console()
    
    if len(sys.argv) < 2:
        print_help(console)
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        print_available_logs(console)
        
    elif command == "help":
        print_help(console)
        
    elif command == "view":
        import log_viewer
        
        # Prepare arguments for log_viewer
        view_args = sys.argv[2:] if len(sys.argv) > 2 else []
        sys.argv = [sys.argv[0]] + view_args
        log_viewer.main()
        
    elif command == "stats":
        import log_stats
        
        # Prepare arguments for log_stats
        stats_args = sys.argv[2:] if len(sys.argv) > 2 else []
        sys.argv = [sys.argv[0]] + stats_args
        log_stats.main()
        
    elif command == "search":
        import log_search
        
        # Prepare arguments for log_search
        search_args = sys.argv[2:] if len(sys.argv) > 2 else []
        sys.argv = [sys.argv[0]] + search_args
        log_search.main()
        
    elif command == "trace":
        import traceviz
        
        # Prepare arguments for traceviz
        trace_args = sys.argv[2:] if len(sys.argv) > 2 else []
        sys.argv = [sys.argv[0]] + trace_args
        traceviz.main()
        
    else:
        console.print(f"Unknown command: {command}", style="bold red")
        print_help(console)


if __name__ == "__main__":
    main()