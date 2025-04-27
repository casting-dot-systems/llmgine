#!/usr/bin/env python3
"""
Rich-based event log visualizer for LLMgine.
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import rich.box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.tree import Tree

# Default logs directory
DEFAULT_LOGS_DIR = Path(os.path.expanduser("~/dev/llmgine/logs"))

# Event type color mapping
EVENT_COLORS = {
    "SessionStartEvent": "green",
    "SessionEndEvent": "red",
    "ToolCompiledEvent": "blue",
    "ToolCalledEvent": "yellow",
    "ToolReturnedEvent": "cyan",
    "LLMRequestEvent": "magenta",
    "LLMResponseEvent": "bright_magenta",
    # Add more event types and colors as needed
    "default": "white"
}

class EventLogViewer:
    """Rich-based event log visualizer for LLMgine."""

    def __init__(self, log_file: Path, console: Optional[Console] = None):
        """Initialize the event log viewer.
        
        Args:
            log_file: Path to the event log file
            console: Rich console instance (optional)
        """
        self.log_file = log_file
        self.console = console or Console()
        self.events: List[Dict] = []
        self.sessions: Set[str] = set()
        self.event_types: Set[str] = set()
        self.filtered_events: List[Dict] = []
        self.current_filters = {
            "session_id": None,
            "event_type": None,
            "event_id": None,
            "after_time": None,
            "before_time": None,
        }
        
        # Load events
        self.load_events()
        
    def load_events(self) -> None:
        """Load events from the log file."""
        self.events = []
        
        # Read all content to handle multi-line JSON properly
        with open(self.log_file, "r") as f:
            content = f.read()
            
        # Split by closing brace followed by an opening brace (with possible whitespace)
        # This is to handle both single-line and multi-line JSON objects
        json_objects = []
        current_obj = ""
        for line in content.split("\n"):
            current_obj += line
            if line.strip() == "}":
                json_objects.append(current_obj)
                current_obj = ""
        
        # Parse each JSON object
        for json_str in json_objects:
            if not json_str.strip():
                continue
                
            try:
                event = json.loads(json_str)
                # Skip entries that don't have event_type
                if "event_type" not in event:
                    continue
                    
                self.events.append(event)
                if "session_id" in event:
                    self.sessions.add(event["session_id"])
                if "event_type" in event:
                    self.event_types.add(event["event_type"])
            except json.JSONDecodeError:
                # Try to fix common issues with the JSON
                try:
                    # Try adding missing closing braces
                    fixed_str = json_str
                    while fixed_str.count("{") > fixed_str.count("}"):
                        fixed_str += "}"
                    event = json.loads(fixed_str)
                    
                    # Skip entries that don't have event_type
                    if "event_type" not in event:
                        continue
                        
                    self.events.append(event)
                    if "session_id" in event:
                        self.sessions.add(event["session_id"])
                    if "event_type" in event:
                        self.event_types.add(event["event_type"])
                except json.JSONDecodeError:
                    # Just skip problematic objects silently
                    continue
        
        # Initial filtering (no filters)
        self.apply_filters()
        
    def apply_filters(self) -> None:
        """Apply current filters to the events."""
        self.filtered_events = self.events.copy()
        
        # Apply session filter
        if self.current_filters["session_id"]:
            self.filtered_events = [
                e for e in self.filtered_events 
                if e.get("session_id") == self.current_filters["session_id"]
            ]
            
        # Apply event type filter
        if self.current_filters["event_type"]:
            self.filtered_events = [
                e for e in self.filtered_events 
                if e.get("event_type") == self.current_filters["event_type"]
            ]
            
        # Apply event ID filter
        if self.current_filters["event_id"]:
            self.filtered_events = [
                e for e in self.filtered_events 
                if e.get("event_id") == self.current_filters["event_id"]
            ]
            
        # Apply time filters
        if self.current_filters["after_time"]:
            self.filtered_events = [
                e for e in self.filtered_events 
                if e.get("timestamp", "") >= self.current_filters["after_time"]
            ]
            
        if self.current_filters["before_time"]:
            self.filtered_events = [
                e for e in self.filtered_events 
                if e.get("timestamp", "") <= self.current_filters["before_time"]
            ]
    
    def set_filter(self, filter_name: str, value: Optional[str]) -> None:
        """Set a filter value and apply filters.
        
        Args:
            filter_name: Name of the filter to set
            value: Value to set for the filter (None to clear)
        """
        if filter_name in self.current_filters:
            self.current_filters[filter_name] = value
            self.apply_filters()
    
    def print_help(self) -> None:
        """Print help information."""
        self.console.print(Panel(
            "LLMgine Event Log Viewer Commands\n\n"
            "help, h       - Show this help\n"
            "view, v       - View events (with optional page number)\n"
            "filter, f     - Filter events\n"
            "sessions, s   - List available sessions\n"
            "types, t      - List event types\n"
            "detail, d     - Show event details\n"
            "timeline, l   - Show session timeline\n"
            "stats, st     - Show statistics\n"
            "clear, c      - Clear all filters\n"
            "quit, q       - Quit the viewer",
            title="Help",
            border_style="blue"
        ))
        
    def get_sessions_table(self) -> Table:
        """Create a table of unique sessions."""
        table = Table(title="Sessions", box=rich.box.ROUNDED)
        table.add_column("Session ID", style="cyan")
        table.add_column("First Event", style="green")
        table.add_column("Last Event", style="yellow")
        table.add_column("Event Count", style="magenta")
        
        session_data = {}
        for event in self.events:
            sid = event.get("session_id")
            if not sid:
                continue
                
            if sid not in session_data:
                session_data[sid] = {
                    "first": event.get("timestamp", ""),
                    "last": event.get("timestamp", ""),
                    "count": 1
                }
            else:
                session_data[sid]["last"] = event.get("timestamp", "")
                session_data[sid]["count"] += 1
        
        for sid, data in session_data.items():
            table.add_row(
                sid,
                data["first"],
                data["last"],
                str(data["count"])
            )
            
        return table
        
    def get_event_types_table(self) -> Table:
        """Create a table of event types and their counts."""
        table = Table(title="Event Types", box=rich.box.ROUNDED)
        table.add_column("Event Type", style="cyan")
        table.add_column("Count", style="magenta")
        
        type_counts = {}
        for event in self.events:
            event_type = event.get("event_type", "Unknown")
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
            
        for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            table.add_row(
                Text(event_type, style=color),
                str(count)
            )
            
        return table
        
    def get_events_table(self, page: int = 0, page_size: int = 20) -> Table:
        """Create a table of events.
        
        Args:
            page: Page number (0-based)
            page_size: Number of events per page
            
        Returns:
            Rich Table object
        """
        total_events = len(self.filtered_events)
        total_pages = max(1, (total_events + page_size - 1) // page_size)
        
        # Ensure page is valid
        page = max(0, min(page, total_pages - 1))
        
        # Calculate slice indices
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, total_events)
        
        # Create table
        table = Table(
            title=f"Events (Page {page+1}/{total_pages}, {total_events} total)",
            box=rich.box.ROUNDED
        )
        table.add_column("Time", style="bright_black")
        table.add_column("Session", style="cyan")
        table.add_column("Event Type", style="green")
        table.add_column("Event ID", style="yellow", no_wrap=True)
        
        # Add events for current page
        display_events = self.filtered_events[start_idx:end_idx]
        
        for event in display_events:
            timestamp = event.get("timestamp", "")
            if timestamp:
                # Just display time portion if it's a full timestamp
                if "T" in timestamp:
                    timestamp = timestamp.split("T")[1][:8]
                    
            event_type = event.get("event_type", "Unknown")
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            
            table.add_row(
                timestamp,
                event.get("session_id", ""),
                Text(event_type, style=color),
                event.get("event_id", "")[:8]  # Truncate UUID
            )
            
        return table
    
    def display_event_detail(self, event_id: str) -> None:
        """Display detailed information about a specific event.
        
        Args:
            event_id: ID of the event to display
        """
        # Try to find the event by ID or prefix
        found_event = None
        for event in self.events:
            if event.get("event_id") == event_id:
                found_event = event
                break
        
        # If not found by exact match, try prefix match
        if not found_event:
            for event in self.events:
                if event.get("event_id", "").startswith(event_id):
                    found_event = event
                    break
        
        if found_event:
            json_str = json.dumps(found_event, indent=4)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            
            event_type = found_event.get("event_type", "Unknown")
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            
            self.console.print(Panel(
                syntax,
                title=f"[{color}]{event_type}[/{color}] ({found_event.get('event_id')})",
                border_style=color
            ))
        else:
            self.console.print(f"Event with ID {event_id} not found", style="bold red")
        
    def create_timeline_tree(self, session_id: Optional[str] = None) -> Tree:
        """Create a tree-based timeline visualization.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Rich Tree object
        """
        events_to_display = [
            e for e in self.filtered_events 
            if not session_id or e.get("session_id") == session_id
        ]
        
        # Sort by timestamp
        events_to_display.sort(key=lambda e: e.get("timestamp", ""))
        
        root = Tree("[bold]Timeline[/bold]")
        current_session = None
        session_branch = None
        
        for event in events_to_display:
            sid = event.get("session_id")
            event_type = event.get("event_type", "Unknown")
            timestamp = event.get("timestamp", "").split("T")[1][:12] if "T" in event.get("timestamp", "") else ""
            event_id = event.get("event_id", "")[:8]
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            
            # If this is a new session, create a new branch
            if sid != current_session:
                current_session = sid
                session_branch = root.add(f"[cyan]Session: {sid}[/cyan]")
                
            if session_branch:
                session_branch.add(f"[{color}]{timestamp} {event_type}[/{color}] ({event_id})")
            
        return root
    
    def print_stats(self) -> None:
        """Print statistics about the log file."""
        # Count events by type
        type_counts = {}
        for event in self.events:
            event_type = event.get("event_type", "Unknown")
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Count events by session
        session_counts = {}
        for event in self.events:
            session_id = event.get("session_id", "Unknown")
            session_counts[session_id] = session_counts.get(session_id, 0) + 1
        
        # Create stats panel
        self.console.print(Panel(
            f"Total Events: {len(self.events)}\n"
            f"Filtered Events: {len(self.filtered_events)}\n"
            f"Unique Sessions: {len(self.sessions)}\n"
            f"Event Types: {len(self.event_types)}\n\n"
            f"Current Filters:\n" + 
            "\n".join([f"  {k}: {v}" for k, v in self.current_filters.items() if v]),
            title="Log Statistics",
            border_style="green"
        ))
        
        # Print type counts
        type_table = Table(title="Event Types", box=rich.box.ROUNDED)
        type_table.add_column("Event Type", style="cyan")
        type_table.add_column("Count", style="magenta")
        type_table.add_column("Percentage", style="green")
        
        for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.events)) * 100 if self.events else 0
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            type_table.add_row(
                Text(event_type, style=color),
                str(count),
                f"{percentage:.1f}%"
            )
            
        self.console.print(type_table)
    
    def run_interactive(self) -> None:
        """Run simple interactive mode with command input."""
        # Show welcome message
        self.console.print(Panel(
            f"[bold]LLMgine Event Log Viewer[/bold]\n\n"
            f"Log file: {self.log_file}\n"
            f"Total events: {len(self.events)}\n"
            f"Unique sessions: {len(self.sessions)}\n\n"
            f"Type 'help' to see available commands.",
            title="Welcome",
            border_style="blue"
        ))
        
        # Track current page
        current_page = 0
        page_size = 20
        
        # Command loop
        while True:
            # Show prompt with filter info
            filter_text = ""
            for k, v in self.current_filters.items():
                if v:
                    filter_text += f"{k}={v} "
                    
            if filter_text:
                prompt = f"[bold cyan]llmgine-logs[{filter_text.strip()}]>[/bold cyan] "
            else:
                prompt = "[bold cyan]llmgine-logs>[/bold cyan] "
                
            # Get command
            cmd_input = self.console.input(prompt).strip()
            if not cmd_input:
                continue
                
            # Parse command and arguments
            parts = cmd_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            try:
                # Process command
                if cmd in ("quit", "q", "exit"):
                    break
                    
                elif cmd in ("help", "h", "?"):
                    self.print_help()
                
                elif cmd in ("view", "v", "events", "show"):
                    # Check for page number in args
                    if args and args.isdigit():
                        page = int(args) - 1  # Convert to 0-based
                        current_page = max(0, page)
                    
                    # Show events table
                    table = self.get_events_table(page=current_page, page_size=page_size)
                    self.console.print(table)
                    
                elif cmd in ("next", "n"):
                    # Go to next page
                    total_pages = max(1, (len(self.filtered_events) + page_size - 1) // page_size)
                    if current_page < total_pages - 1:
                        current_page += 1
                        table = self.get_events_table(page=current_page, page_size=page_size)
                        self.console.print(table)
                    else:
                        self.console.print("Already at last page", style="yellow")
                        
                elif cmd in ("prev", "p", "previous"):
                    # Go to previous page
                    if current_page > 0:
                        current_page -= 1
                        table = self.get_events_table(page=current_page, page_size=page_size)
                        self.console.print(table)
                    else:
                        self.console.print("Already at first page", style="yellow")
                
                elif cmd in ("filter", "f"):
                    if not args:
                        # Show available filters
                        self.console.print("Available filters:", style="bold yellow")
                        self.console.print("  session_id - Filter by session ID")
                        self.console.print("  event_type - Filter by event type")
                        self.console.print("  event_id - Filter by event ID")
                        self.console.print("  after_time - Filter events after timestamp")
                        self.console.print("  before_time - Filter events before timestamp")
                        self.console.print("\nUsage: filter <filter_name> <value>")
                        self.console.print("Example: filter session_id ABC123")
                    else:
                        # Parse filter command
                        filter_parts = args.split(maxsplit=1)
                        if len(filter_parts) == 2:
                            filter_name, filter_value = filter_parts
                            if filter_name in self.current_filters:
                                # Set filter
                                self.set_filter(filter_name, filter_value)
                                self.console.print(f"Filter set: {filter_name} = {filter_value}", style="green")
                                current_page = 0  # Reset to first page
                            else:
                                self.console.print(f"Unknown filter: {filter_name}", style="bold red")
                        else:
                            self.console.print("Invalid filter command. Use: filter <name> <value>", style="bold red")
                
                elif cmd in ("clear", "c"):
                    # Clear all filters
                    for k in self.current_filters:
                        self.current_filters[k] = None
                    self.apply_filters()
                    self.console.print("All filters cleared", style="green")
                    current_page = 0  # Reset to first page
                
                elif cmd in ("sessions", "s"):
                    # Show sessions table
                    self.console.print(self.get_sessions_table())
                
                elif cmd in ("types", "t"):
                    # Show event types table
                    self.console.print(self.get_event_types_table())
                
                elif cmd in ("detail", "d"):
                    # Show event details
                    if not args:
                        self.console.print("Usage: detail <event_id>", style="yellow")
                    else:
                        self.display_event_detail(args)
                
                elif cmd in ("timeline", "l"):
                    # Show timeline
                    if args:
                        # Filter by session ID
                        self.console.print(self.create_timeline_tree(session_id=args))
                    else:
                        # Show all events (or filtered events)
                        self.console.print(self.create_timeline_tree())
                
                elif cmd in ("stats", "st"):
                    # Show statistics
                    self.print_stats()
                
                else:
                    self.console.print(f"Unknown command: {cmd}. Type 'help' for available commands.", style="bold red")
            
            except Exception as e:
                self.console.print(f"Error: {str(e)}", style="bold red")
                import traceback
                self.console.print(traceback.format_exc(), style="dim red")


def main():
    """Main entry point for the event log viewer."""
    parser = argparse.ArgumentParser(description="LLMgine Event Log Viewer")
    parser.add_argument("log_file", nargs="?", type=str, help="Path to event log file")
    parser.add_argument("--list", "-l", action="store_true", help="List available log files")
    parser.add_argument("--session", "-s", type=str, help="Filter by session ID")
    parser.add_argument("--type", "-t", type=str, help="Filter by event type")
    parser.add_argument("--event", "-e", type=str, help="Show details for event ID")
    parser.add_argument("--timeline", action="store_true", help="Show timeline view")
    
    args = parser.parse_args()
    
    console = Console()
    
    # List available logs
    if args.list:
        logs_dir = DEFAULT_LOGS_DIR
        if not logs_dir.exists():
            console.print(f"Logs directory not found: {logs_dir}", style="bold red")
            return
        
        log_files = sorted(logs_dir.glob("*.jsonl"), reverse=True)
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
            modified = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row(log_file.name, size, modified)
            
        console.print(table)
        return
    
    # Determine log file path
    log_path = None
    if args.log_file:
        log_path = Path(args.log_file)
        if not log_path.exists() and not log_path.is_absolute():
            # Try relative to the default logs directory
            log_path = DEFAULT_LOGS_DIR / args.log_file
    else:
        # Use the most recent log file
        logs_dir = DEFAULT_LOGS_DIR
        if logs_dir.exists():
            log_files = sorted(logs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                log_path = log_files[0]
    
    if not log_path or not log_path.exists():
        console.print("Log file not found. Use --list to see available logs.", style="bold red")
        return
    
    viewer = EventLogViewer(log_path, console)
    
    # Apply command-line filters
    if args.session:
        viewer.set_filter("session_id", args.session)
    
    if args.type:
        viewer.set_filter("event_type", args.type)
    
    # Show detailed event
    if args.event:
        viewer.display_event_detail(args.event)
        return
    
    # Show timeline view
    if args.timeline:
        console.print(viewer.create_timeline_tree())
        return
    
    # Otherwise, run interactive mode
    viewer.run_interactive()

if __name__ == "__main__":
    main()