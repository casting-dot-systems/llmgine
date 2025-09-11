import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Pattern, Set, Tuple, Type

from llmgine.llm import SessionID
from llmgine.messages.events import Event


class EventFilter:
    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        return True


class SessionFilter(EventFilter):
    def __init__(
        self,
        include_sessions: Optional[Set[SessionID]] = None,
        exclude_sessions: Optional[Set[SessionID]] = None,
    ):
        self.include = include_sessions
        self.exclude = exclude_sessions

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        if self.exclude and session_id in self.exclude:
            return False
        if self.include is not None:
            return session_id in self.include
        return True


class EventTypeFilter(EventFilter):
    def __init__(
        self,
        include_types: Optional[Set[Type[Event]]] = None,
        exclude_types: Optional[Set[Type[Event]]] = None,
    ):
        self.include = include_types
        self.exclude = exclude_types

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        et = type(event)
        if self.exclude and et in self.exclude:
            return False
        if self.include is not None:
            return et in self.include
        return True


class PatternFilter(EventFilter):
    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        case_sensitive: bool = False,
    ):
        flags = 0 if case_sensitive else re.IGNORECASE
        self.include: Optional[List[Pattern[str]]] = (
            [re.compile(p, flags) for p in include_patterns] if include_patterns else None
        )
        self.exclude: Optional[List[Pattern[str]]] = (
            [re.compile(p, flags) for p in exclude_patterns] if exclude_patterns else None
        )

    def _matches(self, patterns: List[Pattern[str]], name: str) -> bool:
        return any(p.search(name) for p in patterns)

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        name = type(event).__name__
        if self.exclude and self._matches(self.exclude, name):
            return False
        if self.include is not None:
            return self._matches(self.include, name)
        return True


class MetadataFilter(EventFilter):
    def __init__(
        self,
        required_keys: Optional[Set[str]] = None,
        required_values: Optional[Dict[str, Any]] = None,
    ):
        self.required_keys = required_keys or set()
        self.required_values = required_values or {}

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        md = getattr(event, "metadata", {}) or {}
        if self.required_keys:
            if not all(k in md for k in self.required_keys):
                return False
        if self.required_values:
            for k, v in self.required_values.items():
                if md.get(k) != v:
                    return False
        return True


class CompositeFilter(EventFilter):
    def __init__(self, filters: List[EventFilter], require_all: bool = True):
        self.filters = filters
        self.require_all = require_all

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        results = [f.should_handle(event, session_id) for f in self.filters]
        return all(results) if self.require_all else any(results)


class RateLimitFilter(EventFilter):
    """Token-bucket rate limiter; defaults per-session; optionally per-type."""
    def __init__(self, max_per_second: float, per_session: bool = True, per_type: bool = False):
        self.rate = float(max_per_second)
        self.capacity = float(max_per_second)
        self.per_session = per_session
        self.per_type = per_type
        # key -> (tokens, last_refill)
        self._buckets: Dict[Tuple[Optional[str], Optional[str]], Tuple[float, float]] = {}

    def _key(self, event: Event, session_id: SessionID) -> Tuple[Optional[str], Optional[str]]:
        sid = str(session_id) if self.per_session else None
        et = type(event).__name__ if self.per_type else None
        return (sid, et)

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        now = time.monotonic()
        key = self._key(event, session_id)
        tokens, last = self._buckets.get(key, (self.capacity, now))
        # refill
        elapsed = max(0.0, now - last)
        tokens = min(self.capacity, tokens + elapsed * self.rate)
        if tokens >= 1.0:
            tokens -= 1.0
            self._buckets[key] = (tokens, now)
            return True
        else:
            self._buckets[key] = (tokens, now)
            return False


class DebugFilter(EventFilter):
    def __init__(self, logger_func: Optional[Callable[[str], None]] = None, enabled: bool = True):
        self._log = logger_func or (lambda msg: None)
        self.enabled = enabled

    def should_handle(self, event: Event, session_id: SessionID) -> bool:
        if self.enabled:
            self._log(f"[DEBUG FILTER] Event={type(event).__name__} session={session_id}")
        return True