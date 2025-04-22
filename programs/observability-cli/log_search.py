#!/usr/bin/env python3
"""
Search utility for LLMgine event logs.
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Callable

import rich.box
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

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


class LogSearcher:
    """Search utility for LLMgine event logs."""
    
    def __init__(self, log_file: Path, console: Optional[Console] = None):
        """Initialize the log searcher.
        
        Args:
            log_file: Path to the event log file
            console: Rich console instance (optional)
        """
        self.log_file = log_file
        self.console = console or Console()
        self.events: List[Dict] = []
        
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
                except json.JSONDecodeError:
                    # Just skip problematic objects silently
                    continue
    
    def search_by_id(self, id_pattern: str) -> List[Dict]:
        """Search for events by ID pattern.
        
        Args:
            id_pattern: String pattern to match against event IDs
            
        Returns:
            List of matching events
        """
        results = []
        regex = re.compile(id_pattern, re.IGNORECASE)
        
        for event in self.events:
            event_id = event.get("event_id", "")
            if regex.search(event_id):
                results.append(event)
                
        return results
    
    def search_by_session(self, session_id: str) -> List[Dict]:
        """Search for events by session ID.
        
        Args:
            session_id: Session ID to match
            
        Returns:
            List of matching events
        """
        return [
            event for event in self.events
            if event.get("session_id") == session_id
        ]
    
    def search_by_type(self, event_type: str) -> List[Dict]:
        """Search for events by type.
        
        Args:
            event_type: Event type to match
            
        Returns:
            List of matching events
        """
        return [
            event for event in self.events
            if event.get("event_type") == event_type
        ]
    
    def search_by_time_range(self, start_time: str, end_time: Optional[str] = None) -> List[Dict]:
        """Search for events within a time range.
        
        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format (optional)
            
        Returns:
            List of matching events
        """
        results = []
        
        for event in self.events:
            timestamp = event.get("timestamp", "")
            
            if not timestamp:
                continue
                
            if timestamp >= start_time and (not end_time or timestamp <= end_time):
                results.append(event)
                
        return results
    
    def search_by_content(self, pattern: str, field: Optional[str] = None) -> List[Dict]:
        """Search for events with matching content.
        
        Args:
            pattern: Regex pattern to search for
            field: Specific field to search in (optional)
            
        Returns:
            List of matching events
        """
        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        for event in self.events:
            event_str = json.dumps(event)
            
            if field:
                # Search in specific field
                if field in event:
                    field_value = event[field]
                    if isinstance(field_value, (dict, list)):
                        field_str = json.dumps(field_value)
                    else:
                        field_str = str(field_value)
                        
                    if regex.search(field_str):
                        results.append(event)
            else:
                # Search in entire event
                if regex.search(event_str):
                    results.append(event)
                    
        return results
    
    def search_related_events(self, event: Dict, relation_type: str = "session") -> List[Dict]:
        """Find events related to the given event.
        
        Args:
            event: The reference event
            relation_type: Type of relation ('session', 'time', 'id')
            
        Returns:
            List of related events
        """
        if relation_type == "session":
            session_id = event.get("session_id")
            if session_id:
                return self.search_by_session(session_id)
                
        elif relation_type == "time":
            # Find events within 5 seconds
            timestamp = event.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    start_time = (dt - timedelta(seconds=5)).isoformat()
                    end_time = (dt + timedelta(seconds=5)).isoformat()
                    return self.search_by_time_range(start_time, end_time)
                except ValueError:
                    pass
                    
        return []
    
    def print_search_results(self, results: List[Dict], format_type: str = "table") -> None:
        """Print search results in the specified format.
        
        Args:
            results: List of events to display
            format_type: Display format ('table', 'json', 'compact')
        """
        if not results:
            self.console.print("No matching events found", style="yellow")
            return
            
        if format_type == "table":
            table = Table(box=rich.box.ROUNDED)
            table.add_column("Time", style="bright_black")
            table.add_column("Session", style="cyan")
            table.add_column("Event Type", style="green")
            table.add_column("Event ID", style="yellow", no_wrap=True)
            
            for event in results:
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
                
            self.console.print(table)
            
        elif format_type == "json":
            for event in results:
                json_str = json.dumps(event, indent=4)
                syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
                
                event_type = event.get("event_type", "Unknown")
                color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
                
                self.console.print(Panel(
                    syntax,
                    title=f"[{color}]{event_type}[/{color}] ({event.get('event_id', '')[:8]})",
                    border_style=color
                ))
                
        elif format_type == "compact":
            for event in results:
                event_type = event.get("event_type", "Unknown")
                color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
                
                timestamp = event.get("timestamp", "").split("T")[1][:8] if "T" in event.get("timestamp", "") else ""
                
                self.console.print(
                    f"[{color}]{event_type}[/{color}] "
                    f"[bright_black]{timestamp}[/bright_black] "
                    f"[cyan]{event.get('session_id', '')}[/cyan] "
                    f"[yellow]{event.get('event_id', '')[:8]}[/yellow]"
                )
    
    def print_event_context(self, event: Dict, context_lines: int = 5) -> None:
        """Print an event with its context.
        
        Args:
            event: The event to display
            context_lines: Number of events before and after to show
        """
        # Find the event's index
        try:
            index = self.events.index(event)
        except ValueError:
            # Event not found in the list
            self.print_search_results([event], "json")
            return
            
        # Get context
        start = max(0, index - context_lines)
        end = min(len(self.events), index + context_lines + 1)
        
        context = self.events[start:end]
        
        # Print with special highlighting for the target event
        for i, ctx_event in enumerate(context):
            event_type = ctx_event.get("event_type", "Unknown")
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            
            timestamp = ctx_event.get("timestamp", "").split("T")[1][:8] if "T" in ctx_event.get("timestamp", "") else ""
            
            # Highlight the target event
            if start + i == index:
                marker = "👉 "
                style = "bold"
            else:
                marker = "   "
                style = "dim" if start + i < index else ""
            
            self.console.print(
                f"{marker}[{style}][{color}]{event_type}[/{color}] "
                f"[bright_black]{timestamp}[/bright_black] "
                f"[cyan]{ctx_event.get('session_id', '')}[/cyan] "
                f"[yellow]{ctx_event.get('event_id', '')[:8]}[/yellow][/{style}]"
            )
            
        # Show the full event details
        self.console.print()
        json_str = json.dumps(event, indent=4)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        event_type = event.get("event_type", "Unknown")
        color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
        
        self.console.print(Panel(
            syntax,
            title=f"[{color}]{event_type}[/{color}] ({event.get('event_id', '')[:8]})",
            border_style=color
        ))


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLMgine Log Search")
    parser.add_argument("log_file", type=str, help="Path to event log file")
    parser.add_argument("--id", "-i", type=str, help="Search by event ID pattern")
    parser.add_argument("--session", "-s", type=str, help="Search by session ID")
    parser.add_argument("--type", "-t", type=str, help="Search by event type")
    parser.add_argument("--start-time", type=str, help="Search from this time (ISO format)")
    parser.add_argument("--end-time", type=str, help="Search until this time (ISO format)")
    parser.add_argument("--pattern", "-p", type=str, help="Search by content pattern (regex)")
    parser.add_argument("--field", "-f", type=str, help="Specific field to search in")
    parser.add_argument("--format", choices=["table", "json", "compact"], 
                        default="table", help="Output format")
    parser.add_argument("--context", "-c", action="store_true", 
                        help="Show context around matching events")
    parser.add_argument("--context-lines", type=int, default=5,
                        help="Number of context lines (default: 5)")
    
    args = parser.parse_args()
    
    console = Console()
    log_path = Path(args.log_file)
    
    if not log_path.exists():
        console.print(f"Log file not found: {log_path}", style="bold red")
        return
    
    searcher = LogSearcher(log_path, console)
    
    # Perform the search
    results = []
    
    if args.id:
        results = searcher.search_by_id(args.id)
    elif args.session:
        results = searcher.search_by_session(args.session)
    elif args.type:
        results = searcher.search_by_type(args.type)
    elif args.start_time:
        results = searcher.search_by_time_range(args.start_time, args.end_time)
    elif args.pattern:
        results = searcher.search_by_content(args.pattern, args.field)
    else:
        console.print("No search criteria specified", style="bold red")
        return
    
    # Display results
    if args.context and len(results) == 1:
        searcher.print_event_context(results[0], args.context_lines)
    else:
        console.print(f"Found {len(results)} matching events")
        searcher.print_search_results(results, args.format)


if __name__ == "__main__":
    main()