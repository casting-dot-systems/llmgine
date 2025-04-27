#!/usr/bin/env python3
"""
Trace visualization tool for LLMgine event logs.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import rich.box
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
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


class TraceVisualizer:
    """Trace visualization tool for LLMgine event logs."""
    
    def __init__(self, log_file: Path, console: Optional[Console] = None):
        """Initialize the trace visualizer.
        
        Args:
            log_file: Path to the event log file
            console: Rich console instance (optional)
        """
        self.log_file = log_file
        self.console = console or Console()
        self.events: List[Dict] = []
        self.sessions: Set[str] = set()
        
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
                except json.JSONDecodeError:
                    # Just skip problematic objects silently
                    continue
    
    def get_session_events(self, session_id: str) -> List[Dict]:
        """Get all events for a specific session.
        
        Args:
            session_id: The session ID to filter by
            
        Returns:
            List of events for the session
        """
        return [
            event for event in self.events
            if event.get("session_id") == session_id
        ]
    
    def create_session_timeline(self, session_id: str) -> Tree:
        """Create a timeline tree for a session.
        
        Args:
            session_id: The session ID to visualize
            
        Returns:
            Rich Tree object representing the session timeline
        """
        events = self.get_session_events(session_id)
        events.sort(key=lambda e: e.get("timestamp", ""))
        
        root = Tree(f"[bold cyan]Session: {session_id}[/bold cyan]")
        
        # Track tool calls to build a tree structure
        tool_calls = {}
        call_stack = []
        
        for event in events:
            event_type = event.get("event_type", "Unknown")
            event_id = event.get("event_id", "")[:8]
            timestamp = event.get("timestamp", "").split("T")[1][:12] if "T" in event.get("timestamp", "") else ""
            color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
            
            # Handle specific event types
            if event_type == "SessionStartEvent":
                node = root.add(f"[{color}]{timestamp} Session started[/{color}] ({event_id})")
                
            elif event_type == "SessionEndEvent":
                node = root.add(f"[{color}]{timestamp} Session ended[/{color}] ({event_id})")
                
            elif event_type == "ToolCompiledEvent":
                tools = event.get("tool_compiled_list", [])
                tool_list = ", ".join(str(t) for t in tools) if tools else "None"
                node = root.add(f"[{color}]{timestamp} Tools compiled[/{color}]: {tool_list} ({event_id})")
                
            elif event_type == "ToolCalledEvent":
                tool_name = event.get("tool_name", "Unknown")
                tool_id = event.get("tool_call_id", "")
                
                # Create node for tool call
                node = root.add(f"[{color}]{timestamp} Tool call: {tool_name}[/{color}] ({event_id})")
                
                # Track tool call
                tool_calls[tool_id] = node
                call_stack.append(tool_id)
                
                # Add tool input if available
                tool_input = event.get("tool_input")
                if tool_input:
                    if isinstance(tool_input, dict):
                        for k, v in tool_input.items():
                            node.add(f"[bright_black]Input[/bright_black]: {k} = {v}")
                    else:
                        node.add(f"[bright_black]Input[/bright_black]: {tool_input}")
                
            elif event_type == "ToolReturnedEvent":
                tool_id = event.get("tool_call_id", "")
                
                # If we have the corresponding call node, add return as a child
                if tool_id in tool_calls:
                    parent = tool_calls[tool_id]
                    node = parent.add(f"[{color}]{timestamp} Tool returned[/{color}] ({event_id})")
                    
                    # Remove from call stack
                    if tool_id in call_stack:
                        call_stack.remove(tool_id)
                    
                    # Add tool output if available
                    tool_output = event.get("tool_output")
                    if tool_output:
                        if isinstance(tool_output, dict):
                            output_str = json.dumps(tool_output, indent=2)
                            if len(output_str) > 100:
                                output_str = output_str[:100] + "..."
                            node.add(f"[bright_black]Output[/bright_black]: {output_str}")
                        else:
                            output_str = str(tool_output)
                            if len(output_str) > 100:
                                output_str = output_str[:100] + "..."
                            node.add(f"[bright_black]Output[/bright_black]: {output_str}")
                else:
                    # If no matching call node, add to root
                    node = root.add(f"[{color}]{timestamp} Tool returned[/{color}] ({event_id})")
                    
            elif event_type == "LLMRequestEvent":
                # Add request node
                node = root.add(f"[{color}]{timestamp} LLM request[/{color}] ({event_id})")
                
                # Add request details
                model = event.get("model", "Unknown")
                node.add(f"[bright_black]Model[/bright_black]: {model}")
                
            elif event_type == "LLMResponseEvent":
                # Add response node
                node = root.add(f"[{color}]{timestamp} LLM response[/{color}] ({event_id})")
                
                # Add response details
                model = event.get("model", "Unknown")
                tokens = event.get("usage", {}).get("total_tokens", 0)
                node.add(f"[bright_black]Model[/bright_black]: {model}, [bright_black]Tokens[/bright_black]: {tokens}")
                
            else:
                # Generic event handling
                node = root.add(f"[{color}]{timestamp} {event_type}[/{color}] ({event_id})")
            
        return root
    
    def create_call_graph(self, session_id: str) -> Tuple[Tree, Dict[str, Dict]]:
        """Create a call graph for a session.
        
        Args:
            session_id: The session ID to visualize
            
        Returns:
            Tuple of (Rich Tree object, stats dictionary)
        """
        events = self.get_session_events(session_id)
        events.sort(key=lambda e: e.get("timestamp", ""))
        
        root = Tree(f"[bold cyan]Call Graph: {session_id}[/bold cyan]")
        
        # Track nodes and stats
        nodes = {}
        stats = {
            "total_calls": 0,
            "tool_counts": {},
            "avg_duration": 0,
            "total_duration": 0,
            "max_duration": 0,
            "max_call": None
        }
        
        # First pass: create nodes for each tool call
        tool_calls = {}
        for event in events:
            if event.get("event_type") == "ToolCalledEvent":
                tool_id = event.get("tool_call_id", "")
                tool_name = event.get("tool_name", "Unknown")
                timestamp = event.get("timestamp", "")
                color = EVENT_COLORS.get("ToolCalledEvent", EVENT_COLORS["default"])
                
                # Create node for tool call
                node = root.add(f"[{color}]{tool_name}[/{color}]")
                
                # Track tool call
                tool_calls[tool_id] = {
                    "node": node,
                    "tool_name": tool_name,
                    "start_time": timestamp,
                    "end_time": None,
                    "duration": None
                }
                
                # Update stats
                stats["total_calls"] += 1
                stats["tool_counts"][tool_name] = stats["tool_counts"].get(tool_name, 0) + 1
        
        # Second pass: add tool returns and calculate durations
        for event in events:
            if event.get("event_type") == "ToolReturnedEvent":
                tool_id = event.get("tool_call_id", "")
                timestamp = event.get("timestamp", "")
                
                if tool_id in tool_calls:
                    # Update tool call info
                    tool_calls[tool_id]["end_time"] = timestamp
                    
                    # Calculate duration if possible
                    if tool_calls[tool_id]["start_time"] and timestamp:
                        try:
                            start = tool_calls[tool_id]["start_time"]
                            end = timestamp
                            
                            # Simple string comparison works for ISO format
                            format_time = lambda t: t.split("T")[1][:8] if "T" in t else t
                            duration_str = f"{format_time(start)} to {format_time(end)}"
                            
                            # Extract seconds (very simplistic)
                            start_seconds = float(start.split(":")[-1]) if ":" in start else 0
                            end_seconds = float(end.split(":")[-1]) if ":" in end else 0
                            duration = end_seconds - start_seconds
                            
                            tool_calls[tool_id]["duration"] = duration
                            tool_calls[tool_id]["duration_str"] = duration_str
                            
                            # Update stats
                            stats["total_duration"] += duration
                            
                            if duration > stats["max_duration"]:
                                stats["max_duration"] = duration
                                stats["max_call"] = tool_calls[tool_id]["tool_name"]
                                
                            # Update node label
                            node = tool_calls[tool_id]["node"]
                            tool_name = tool_calls[tool_id]["tool_name"]
                            color = EVENT_COLORS.get("ToolCalledEvent", EVENT_COLORS["default"])
                            node.label = f"[{color}]{tool_name}[/{color}] ({duration:.2f}s)"
                        except (ValueError, TypeError):
                            pass
        
        # Calculate average duration
        if stats["total_calls"] > 0:
            stats["avg_duration"] = stats["total_duration"] / stats["total_calls"]
            
        return root, stats
    
    def print_session_list(self) -> None:
        """Print a list of available sessions."""
        table = Table(title="Available Sessions", box=rich.box.ROUNDED)
        table.add_column("Session ID", style="cyan")
        table.add_column("Event Count", style="magenta")
        
        session_counts = {}
        for event in self.events:
            session_id = event.get("session_id")
            if session_id:
                session_counts[session_id] = session_counts.get(session_id, 0) + 1
                
        for session_id, count in sorted(session_counts.items(), key=lambda x: x[1], reverse=True):
            table.add_row(session_id, str(count))
            
        self.console.print(table)
    
    def print_session_trace(self, session_id: str) -> None:
        """Print a trace visualization for a session.
        
        Args:
            session_id: The session ID to visualize
        """
        # Check if session exists
        if session_id not in self.sessions:
            self.console.print(f"Session not found: {session_id}", style="bold red")
            self.print_session_list()
            return
            
        # Create and print timeline
        timeline = self.create_session_timeline(session_id)
        self.console.print(Panel(
            timeline,
            title=f"Session Timeline: {session_id}",
            border_style="blue"
        ))
        
        # Create and print call graph
        call_graph, stats = self.create_call_graph(session_id)
        
        # Print stats
        stats_text = Text()
        stats_text.append(f"Total tool calls: {stats['total_calls']}\n", style="bold")
        
        if stats["avg_duration"]:
            stats_text.append(f"Average duration: {stats['avg_duration']:.3f}s\n", style="green")
            stats_text.append(f"Maximum duration: {stats['max_duration']:.3f}s", style="yellow")
            if stats["max_call"]:
                stats_text.append(f" ({stats['max_call']})\n", style="yellow")
                
        # Add tool count breakdown
        stats_text.append("\nTool usage:\n", style="bold")
        for tool, count in sorted(stats["tool_counts"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats["total_calls"]) * 100 if stats["total_calls"] else 0
            stats_text.append(f"  {tool}: {count} ({percentage:.1f}%)\n", style="cyan")
        
        self.console.print(Panel(
            Padding(stats_text, (1, 2)),
            title="Call Statistics",
            border_style="green"
        ))
        
        # Print call graph
        self.console.print(Panel(
            call_graph,
            title=f"Call Graph: {session_id}",
            border_style="yellow"
        ))
    
    def print_event_detail(self, event_id: str) -> None:
        """Print detailed information about a specific event.
        
        Args:
            event_id: ID of the event to display
        """
        for event in self.events:
            if event.get("event_id") == event_id or event.get("event_id", "").startswith(event_id):
                json_str = json.dumps(event, indent=4)
                syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
                
                event_type = event.get("event_type", "Unknown")
                color = EVENT_COLORS.get(event_type, EVENT_COLORS["default"])
                
                self.console.print(Panel(
                    syntax,
                    title=f"[{color}]{event_type}[/{color}] ({event.get('event_id')})",
                    border_style=color
                ))
                return
                
        self.console.print(f"Event with ID {event_id} not found", style="bold red")


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLMgine Trace Visualizer")
    parser.add_argument("log_file", nargs="?", type=str, help="Path to event log file")
    parser.add_argument("--list", "-l", action="store_true", help="List available sessions")
    parser.add_argument("--session", "-s", type=str, help="Session ID to visualize")
    parser.add_argument("--event", "-e", type=str, help="Show details for event ID")
    
    args = parser.parse_args()
    
    console = Console()
    
    # Determine log file path
    log_path = None
    if args.log_file:
        log_path = Path(args.log_file)
    else:
        # Use the most recent log file
        logs_dir = DEFAULT_LOGS_DIR
        if logs_dir.exists():
            log_files = sorted(logs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                log_path = log_files[0]
    
    if not log_path or not log_path.exists():
        console.print("Log file not found. Please specify a valid log file path.", style="bold red")
        return
    
    visualizer = TraceVisualizer(log_path, console)
    
    if args.list:
        visualizer.print_session_list()
    elif args.event:
        visualizer.print_event_detail(args.event)
    elif args.session:
        visualizer.print_session_trace(args.session)
    else:
        # Show usage
        console.print("Please specify an action:", style="bold blue")
        console.print("  --list (-l) to list sessions", style="yellow")
        console.print("  --session (-s) SESSION_ID to visualize a session", style="yellow")
        console.print("  --event (-e) EVENT_ID to show event details", style="yellow")


if __name__ == "__main__":
    main()