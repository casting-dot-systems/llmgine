"""Tests for message bus event filters."""


from llmgine.bus.filters import (
    CompositeFilter,
    DebugFilter,
    EventTypeFilter,
    MetadataFilter,
    PatternFilter,
    RateLimitFilter,
    SessionFilter,
)
from llmgine.llm import SessionID
from llmgine.messages.events import Event


# Test fixtures
class TestEvent(Event):
    """Test event for unit tests."""

    value: str = "test"


class AnotherTestEvent(Event):
    """Another test event."""

    value: str = "another"


class SystemStartedEvent(Event):
    """System event for pattern testing."""

    pass


class SystemStoppedEvent(Event):
    """System event for pattern testing."""

    pass


class TestFilters:
    """Test suite for event filter implementations."""

    def test_session_filter_include(self):
        """Test session filter with include list."""
        included = {SessionID("session1"), SessionID("session2")}
        filter_obj = SessionFilter(include_sessions=included)

        event = TestEvent()

        # Should handle included sessions
        assert filter_obj.should_handle(event, SessionID("session1"))
        assert filter_obj.should_handle(event, SessionID("session2"))

        # Should not handle other sessions
        assert not filter_obj.should_handle(event, SessionID("session3"))
        assert not filter_obj.should_handle(event, SessionID("BUS"))

    def test_session_filter_exclude(self):
        """Test session filter with exclude list."""
        excluded = {SessionID("bad1"), SessionID("bad2")}
        filter_obj = SessionFilter(exclude_sessions=excluded)

        event = TestEvent()

        # Should not handle excluded sessions
        assert not filter_obj.should_handle(event, SessionID("bad1"))
        assert not filter_obj.should_handle(event, SessionID("bad2"))

        # Should handle other sessions
        assert filter_obj.should_handle(event, SessionID("good"))
        assert filter_obj.should_handle(event, SessionID("BUS"))

    def test_event_type_filter_include(self):
        """Test event type filter with include list."""
        filter_obj = EventTypeFilter(include_types={TestEvent})

        # Should handle included type
        assert filter_obj.should_handle(TestEvent(), SessionID("any"))

        # Should not handle other types
        assert not filter_obj.should_handle(AnotherTestEvent(), SessionID("any"))

    def test_event_type_filter_exclude(self):
        """Test event type filter with exclude list."""
        filter_obj = EventTypeFilter(exclude_types={TestEvent})

        # Should not handle excluded type
        assert not filter_obj.should_handle(TestEvent(), SessionID("any"))

        # Should handle other types
        assert filter_obj.should_handle(AnotherTestEvent(), SessionID("any"))

    def test_pattern_filter_include(self):
        """Test pattern filter with include patterns."""
        filter_obj = PatternFilter(include_patterns=[r"System.*Event"])

        # Should handle matching patterns
        assert filter_obj.should_handle(SystemStartedEvent(), SessionID("any"))
        assert filter_obj.should_handle(SystemStoppedEvent(), SessionID("any"))

        # Should not handle non-matching
        assert not filter_obj.should_handle(TestEvent(), SessionID("any"))

    def test_pattern_filter_exclude(self):
        """Test pattern filter with exclude patterns."""
        filter_obj = PatternFilter(exclude_patterns=[r".*Test.*"])

        # Should not handle matching patterns
        assert not filter_obj.should_handle(TestEvent(), SessionID("any"))
        assert not filter_obj.should_handle(AnotherTestEvent(), SessionID("any"))

        # Should handle non-matching
        assert filter_obj.should_handle(SystemStartedEvent(), SessionID("any"))

    def test_pattern_filter_case_sensitivity(self):
        """Test pattern filter case sensitivity."""
        # Case insensitive (default)
        filter_insensitive = PatternFilter(include_patterns=[r"system"])
        assert filter_insensitive.should_handle(SystemStartedEvent(), SessionID("any"))

        # Case sensitive
        filter_sensitive = PatternFilter(
            include_patterns=[r"system"], case_sensitive=True
        )
        assert not filter_sensitive.should_handle(SystemStartedEvent(), SessionID("any"))

        filter_sensitive2 = PatternFilter(
            include_patterns=[r"System"], case_sensitive=True
        )
        assert filter_sensitive2.should_handle(SystemStartedEvent(), SessionID("any"))

    def test_metadata_filter_required_keys(self):
        """Test metadata filter with required keys."""
        filter_obj = MetadataFilter(required_keys={"user_id", "request_id"})

        # Event with all required keys
        event1 = TestEvent()
        event1.metadata = {"user_id": "123", "request_id": "abc", "extra": "ok"}
        assert filter_obj.should_handle(event1, SessionID("any"))

        # Event missing a key
        event2 = TestEvent()
        event2.metadata = {"user_id": "123"}
        assert not filter_obj.should_handle(event2, SessionID("any"))

        # Event with no metadata
        event3 = TestEvent()
        assert not filter_obj.should_handle(event3, SessionID("any"))

    def test_metadata_filter_required_values(self):
        """Test metadata filter with required values."""
        filter_obj = MetadataFilter(
            required_values={"environment": "production", "version": "2.0"}
        )

        # Event with matching values
        event1 = TestEvent()
        event1.metadata = {"environment": "production", "version": "2.0"}
        assert filter_obj.should_handle(event1, SessionID("any"))

        # Event with wrong value
        event2 = TestEvent()
        event2.metadata = {"environment": "development", "version": "2.0"}
        assert not filter_obj.should_handle(event2, SessionID("any"))

    def test_composite_filter_and_logic(self):
        """Test composite filter with AND logic."""
        filter_obj = CompositeFilter(
            filters=[
                SessionFilter(include_sessions={SessionID("session1")}),
                EventTypeFilter(include_types={TestEvent}),
            ],
            require_all=True,  # AND
        )

        # Both conditions met
        assert filter_obj.should_handle(TestEvent(), SessionID("session1"))

        # Only one condition met
        assert not filter_obj.should_handle(TestEvent(), SessionID("session2"))
        assert not filter_obj.should_handle(AnotherTestEvent(), SessionID("session1"))

    def test_composite_filter_or_logic(self):
        """Test composite filter with OR logic."""
        filter_obj = CompositeFilter(
            filters=[
                SessionFilter(include_sessions={SessionID("session1")}),
                EventTypeFilter(include_types={TestEvent}),
            ],
            require_all=False,  # OR
        )

        # Both conditions met
        assert filter_obj.should_handle(TestEvent(), SessionID("session1"))

        # Only one condition met (still passes)
        assert filter_obj.should_handle(TestEvent(), SessionID("session2"))
        assert filter_obj.should_handle(AnotherTestEvent(), SessionID("session1"))

        # Neither condition met
        assert not filter_obj.should_handle(AnotherTestEvent(), SessionID("session2"))

    def test_rate_limit_filter(self):
        """Test rate limit filter functionality."""
        import time

        # 2 events per second
        filter_obj = RateLimitFilter(max_per_second=2.0)

        event = TestEvent()
        session = SessionID("test")

        # First event should pass
        assert filter_obj.should_handle(event, session)

        # Second event should pass
        assert filter_obj.should_handle(event, session)

        # Third event too quickly should fail
        assert not filter_obj.should_handle(event, session)

        # Wait for rate limit window
        time.sleep(0.6)

        # Should pass again
        assert filter_obj.should_handle(event, session)

    def test_rate_limit_filter_per_type(self):
        """Test rate limit filter per event type."""
        filter_obj = RateLimitFilter(max_per_second=1.0, per_session=False, per_type=True)

        session = SessionID("test")

        # Different event types should have separate limits
        assert filter_obj.should_handle(TestEvent(), session)
        assert filter_obj.should_handle(AnotherTestEvent(), session)

        # Same type too quickly should fail
        assert not filter_obj.should_handle(TestEvent(), session)

    def test_debug_filter(self):
        """Test debug filter functionality."""
        logged_messages = []

        def logger(msg: str) -> None:
            logged_messages.append(msg)

        filter_obj = DebugFilter(logger_func=logger)

        event = TestEvent()
        session = SessionID("test-session")

        # Should always return True
        assert filter_obj.should_handle(event, session)

        # Should have logged
        assert len(logged_messages) == 1
        assert "TestEvent" in logged_messages[0]
        assert "test-session" in logged_messages[0]

        # Test with disabled
        filter_obj.enabled = False
        assert filter_obj.should_handle(event, session)
        assert len(logged_messages) == 1  # No new logs
