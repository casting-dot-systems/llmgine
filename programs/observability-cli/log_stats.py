#!/usr/bin/env python3
"""
Statistics generator for LLMgine event logs.
"""
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import rich.box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class LogStats:
    """Generate statistics from LLMgine event logs."""

    def __init__(self, log_file: Path, console: Optional[Console] = None):
        """Initialize the log stats generator.
        
        Args:
            log_file: Path to the event log file
            console: Rich console instance (optional)
        """
        self.log_file = log_file
        self.console = console or Console()
        self.events: List[Dict] = []
        self.sessions = set()
        self.event_types = Counter()
        self.session_stats: Dict[str, Dict] = {}
        
        # Load events
        self.load_events()
        self.calculate_stats()
        
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
    
    def calculate_stats(self) -> None:
        """Calculate statistics from the loaded events."""
        for event in self.events:
            event_type = event.get("event_type", "Unknown")
            session_id = event.get("session_id", "Unknown")
            timestamp = event.get("timestamp", "")
            
            # Count event types
            self.event_types[event_type] += 1
            
            # Track unique sessions
            self.sessions.add(session_id)
            
            # Calculate session-specific stats
            if session_id not in self.session_stats:
                self.session_stats[session_id] = {
                    "start_time": timestamp,
                    "end_time": timestamp,
                    "event_count": 1,
                    "event_types": Counter({event_type: 1}),
                    "duration": 0,
                }
            else:
                self.session_stats[session_id]["end_time"] = timestamp
                self.session_stats[session_id]["event_count"] += 1
                self.session_stats[session_id]["event_types"][event_type] += 1
        
        # Calculate session durations
        for sid, stats in self.session_stats.items():
            try:
                start = datetime.fromisoformat(stats["start_time"])
                end = datetime.fromisoformat(stats["end_time"])
                duration = (end - start).total_seconds()
                self.session_stats[sid]["duration"] = duration
            except (ValueError, TypeError):
                pass
    
    def print_summary(self) -> None:
        """Print a summary of the log statistics."""
        total_events = len(self.events)
        total_sessions = len(self.sessions)
        
        panel = Panel(
            f"[bold]Log Summary[/bold]\n\n"
            f"Total Events: {total_events}\n"
            f"Total Sessions: {total_sessions}\n"
            f"Event Types: {len(self.event_types)}\n"
            f"Log File: {self.log_file}",
            title="LLMgine Log Statistics",
            border_style="blue"
        )
        
        self.console.print(panel)
    
    def print_event_type_distribution(self) -> None:
        """Print the distribution of event types."""
        table = Table(title="Event Type Distribution", box=rich.box.ROUNDED)
        table.add_column("Event Type", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Percentage", style="green")
        
        for event_type, count in self.event_types.most_common():
            percentage = (count / len(self.events)) * 100
            table.add_row(
                event_type,
                str(count),
                f"{percentage:.1f}%"
            )
            
        self.console.print(table)
    
    def print_session_stats(self, limit: int = 10) -> None:
        """Print statistics for each session.
        
        Args:
            limit: Maximum number of sessions to display
        """
        table = Table(title="Session Statistics", box=rich.box.ROUNDED)
        table.add_column("Session ID", style="cyan")
        table.add_column("Duration", style="green")
        table.add_column("Events", style="magenta")
        table.add_column("Top Event Type", style="yellow")
        
        # Sort sessions by event count
        sorted_sessions = sorted(
            self.session_stats.items(),
            key=lambda x: x[1]["event_count"],
            reverse=True
        )
        
        for i, (sid, stats) in enumerate(sorted_sessions):
            if i >= limit:
                break
                
            # Format duration
            duration = stats["duration"]
            if duration > 60:
                duration_str = f"{duration / 60:.1f} min"
            else:
                duration_str = f"{duration:.1f} sec"
                
            # Get top event type
            top_event = stats["event_types"].most_common(1)
            top_event_str = f"{top_event[0][0]} ({top_event[0][1]})" if top_event else "N/A"
            
            table.add_row(
                sid,
                duration_str,
                str(stats["event_count"]),
                top_event_str
            )
            
        self.console.print(table)
    
    def print_time_series(self) -> None:
        """Print a time series analysis of events."""
        # Group events by hour
        hourly_counts = defaultdict(Counter)
        
        for event in self.events:
            timestamp = event.get("timestamp", "")
            event_type = event.get("event_type", "Unknown")
            
            try:
                dt = datetime.fromisoformat(timestamp)
                hour_key = dt.strftime("%Y-%m-%d %H:00")
                hourly_counts[hour_key][event_type] += 1
            except (ValueError, TypeError):
                pass
        
        table = Table(title="Hourly Event Distribution", box=rich.box.ROUNDED)
        table.add_column("Hour", style="cyan")
        table.add_column("Total Events", style="magenta")
        table.add_column("Top Event Types", style="green")
        
        for hour, counts in sorted(hourly_counts.items()):
            total = sum(counts.values())
            top_types = ", ".join(f"{t} ({c})" for t, c in counts.most_common(3))
            
            table.add_row(
                hour,
                str(total),
                top_types
            )
            
        self.console.print(table)
    
    def get_sequential_patterns(self, min_length: int = 2, min_occurrences: int = 2) -> List[Tuple[Tuple[str, ...], int]]:
        """Find common sequences of event types.
        
        Args:
            min_length: Minimum sequence length to consider
            min_occurrences: Minimum number of occurrences to report
            
        Returns:
            List of (sequence, count) tuples
        """
        sequences = defaultdict(int)
        
        # Group by session
        session_events = defaultdict(list)
        for event in self.events:
            session_id = event.get("session_id", "")
            event_type = event.get("event_type", "Unknown")
            session_events[session_id].append(event_type)
        
        # Find sequences in each session
        for session_id, events in session_events.items():
            for i in range(len(events) - min_length + 1):
                for seq_len in range(min_length, min(len(events) - i + 1, min_length + 3)):
                    seq = tuple(events[i:i+seq_len])
                    sequences[seq] += 1
        
        # Filter by minimum occurrences
        return [
            (seq, count) for seq, count in sequences.items() 
            if count >= min_occurrences
        ]
    
    def print_common_sequences(self) -> None:
        """Print common sequences of events."""
        sequences = self.get_sequential_patterns(min_length=2, min_occurrences=2)
        sequences.sort(key=lambda x: x[1], reverse=True)
        
        table = Table(title="Common Event Sequences", box=rich.box.ROUNDED)
        table.add_column("Sequence", style="cyan")
        table.add_column("Count", style="magenta")
        
        for seq, count in sequences[:10]:  # Show top 10
            seq_str = " → ".join(seq)
            table.add_row(seq_str, str(count))
            
        self.console.print(table)
    
    def print_all_stats(self) -> None:
        """Print all statistics."""
        self.print_summary()
        self.console.print()
        self.print_event_type_distribution()
        self.console.print()
        self.print_session_stats()
        self.console.print()
        self.print_time_series()
        self.console.print()
        self.print_common_sequences()


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLMgine Log Statistics")
    parser.add_argument("log_file", type=str, help="Path to event log file")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary only")
    parser.add_argument("--events", "-e", action="store_true", help="Print event type distribution")
    parser.add_argument("--sessions", "-S", action="store_true", help="Print session statistics")
    parser.add_argument("--time", "-t", action="store_true", help="Print time series analysis")
    parser.add_argument("--sequences", "-q", action="store_true", help="Print common event sequences")
    
    args = parser.parse_args()
    
    console = Console()
    log_path = Path(args.log_file)
    
    if not log_path.exists():
        console.print(f"Log file not found: {log_path}", style="bold red")
        return
    
    stats = LogStats(log_path, console)
    
    # If no specific stats requested, print all
    if not any([args.summary, args.events, args.sessions, args.time, args.sequences]):
        stats.print_all_stats()
        return
    
    if args.summary:
        stats.print_summary()
        console.print()
        
    if args.events:
        stats.print_event_type_distribution()
        console.print()
        
    if args.sessions:
        stats.print_session_stats()
        console.print()
        
    if args.time:
        stats.print_time_series()
        console.print()
        
    if args.sequences:
        stats.print_common_sequences()


if __name__ == "__main__":
    main()