"""Common event filter implementations for the message bus.

This module provides reusable filters for controlling event propagation.
"""

import re
from typing import List, Optional, Set, Type, Union

from llmgine.bus.interfaces import EventFilter
from llmgine.llm import SessionID
from llmgine.messages.events import Event


class SessionFilter(EventFilter):
    """Filter events based on session ID."""
    
    def __init__(
        self,
        include_sessions: Optional[Set[SessionID]] = None,
        exclude_sessions: Optional[Set[SessionID]] = None,
    ):
        """Initialize session filter.
        
        Args:
            include_sessions: Only process events from these sessions
            exclude_sessions: Skip events from these sessions
        """
        self.include_sessions = include_sessions
        self.exclude_sessions = exclude_sessions or set()
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event should be handled based on session."""
        # Check exclusions first
        if session_id in self.exclude_sessions:
            return False
        
        # Check inclusions
        if self.include_sessions is not None:
            return session_id in self.include_sessions
        
        return True


class EventTypeFilter(EventFilter):
    """Filter events based on event type."""
    
    def __init__(
        self,
        include_types: Optional[Set[Type[Event]]] = None,
        exclude_types: Optional[Set[Type[Event]]] = None,
    ):
        """Initialize event type filter.
        
        Args:
            include_types: Only process these event types
            exclude_types: Skip these event types
        """
        self.include_types = include_types
        self.exclude_types = exclude_types or set()
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event should be handled based on type."""
        event_type = type(event)
        
        # Check exclusions first
        if event_type in self.exclude_types:
            return False
        
        # Check inclusions
        if self.include_types is not None:
            return event_type in self.include_types
        
        return True


class PatternFilter(EventFilter):
    """Filter events based on event type name patterns."""
    
    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        case_sensitive: bool = False,
    ):
        """Initialize pattern filter.
        
        Args:
            include_patterns: Regex patterns for event types to include
            exclude_patterns: Regex patterns for event types to exclude
            case_sensitive: Whether pattern matching is case-sensitive
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        
        self.include_patterns = [
            re.compile(p, flags) for p in (include_patterns or [])
        ]
        self.exclude_patterns = [
            re.compile(p, flags) for p in (exclude_patterns or [])
        ]
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event should be handled based on name pattern."""
        event_name = type(event).__name__
        
        # Check exclusions first
        for pattern in self.exclude_patterns:
            if pattern.search(event_name):
                return False
        
        # Check inclusions
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.search(event_name):
                    return True
            return False  # Had include patterns but none matched
        
        return True


class MetadataFilter(EventFilter):
    """Filter events based on metadata content."""
    
    def __init__(
        self,
        required_keys: Optional[Set[str]] = None,
        required_values: Optional[dict] = None,
    ):
        """Initialize metadata filter.
        
        Args:
            required_keys: Event must have these metadata keys
            required_values: Event metadata must have these key-value pairs
        """
        self.required_keys = required_keys or set()
        self.required_values = required_values or {}
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event should be handled based on metadata."""
        if not hasattr(event, "metadata"):
            return not self.required_keys and not self.required_values
        
        metadata = event.metadata
        
        # Check required keys
        for key in self.required_keys:
            if key not in metadata:
                return False
        
        # Check required values
        for key, value in self.required_values.items():
            if metadata.get(key) != value:
                return False
        
        return True


class CompositeFilter(EventFilter):
    """Combine multiple filters with AND/OR logic."""
    
    def __init__(
        self,
        filters: List[EventFilter],
        require_all: bool = True,
    ):
        """Initialize composite filter.
        
        Args:
            filters: List of filters to combine
            require_all: If True, all filters must pass (AND).
                        If False, any filter can pass (OR).
        """
        self.filters = filters
        self.require_all = require_all
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event passes composite filter."""
        if not self.filters:
            return True
        
        if self.require_all:
            # AND logic - all must pass
            return all(f.should_handle(event, session_id) for f in self.filters)
        else:
            # OR logic - any can pass
            return any(f.should_handle(event, session_id) for f in self.filters)


class RateLimitFilter(EventFilter):
    """Filter events based on rate limits."""
    
    def __init__(
        self,
        max_per_second: float = 10.0,
        per_session: bool = True,
        per_type: bool = True,
    ):
        """Initialize rate limit filter.
        
        Args:
            max_per_second: Maximum events per second
            per_session: Apply limit per session
            per_type: Apply limit per event type
        """
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.per_session = per_session
        self.per_type = per_type
        self.last_seen: dict = {}
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Check if event passes rate limit."""
        import time
        
        # Build key for tracking
        key_parts = []
        if self.per_session:
            key_parts.append(str(session_id))
        if self.per_type:
            key_parts.append(type(event).__name__)
        
        key = "|".join(key_parts) if key_parts else "global"
        
        now = time.time()
        last_time = self.last_seen.get(key, 0)
        
        if now - last_time >= self.min_interval:
            self.last_seen[key] = now
            return True
        
        return False


class DebugFilter(EventFilter):
    """Filter that logs all events for debugging."""
    
    def __init__(self, logger_func: Optional[callable] = None, enabled: bool = True):
        """Initialize debug filter.
        
        Args:
            logger_func: Custom logging function (defaults to print)
            enabled: Whether filtering is enabled
        """
        self.logger_func = logger_func or print
        self.enabled = enabled
    
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        """Log event and always return True."""
        if self.enabled:
            self.logger_func(
                f"DebugFilter: {type(event).__name__} from session {session_id}"
            )
        return True