"""Tests for message bus middleware implementations."""

import asyncio
import pytest
from typing import List

from llmgine.bus.middleware import (
    LoggingMiddleware,
    TimingMiddleware,
    RetryMiddleware,
    ValidationMiddleware,
    RateLimitMiddleware,
)
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


# Test fixtures
class TestCommand(Command):
    """Test command for unit tests."""
    value: str = "test"


class TestEvent(Event):
    """Test event for unit tests."""
    value: str = "test"


class TestMiddleware:
    """Test suite for middleware implementations."""
    
    @pytest.mark.asyncio
    async def test_logging_middleware(self, caplog):
        """Test logging middleware functionality."""
        middleware = LoggingMiddleware()
        
        # Test command logging
        async def cmd_handler(cmd: Command) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        cmd = TestCommand()
        result = await middleware.process_command(cmd, cmd_handler, next_cmd)
        
        assert result.success
        assert "Executing command TestCommand" in caplog.text
        assert "completed in" in caplog.text
        
        # Test event logging
        events_processed = []
        
        async def evt_handler(evt: Event) -> None:
            events_processed.append(evt)
        
        async def next_evt(evt: Event, handler: Any) -> None:
            await handler(evt)
        
        evt = TestEvent()
        await middleware.process_event(evt, evt_handler, next_evt)
        
        assert len(events_processed) == 1
        assert "Processing event TestEvent" in caplog.text
    
    @pytest.mark.asyncio
    async def test_timing_middleware(self):
        """Test timing middleware functionality."""
        middleware = TimingMiddleware()
        
        # Test command timing
        async def slow_handler(cmd: Command) -> CommandResult:
            await asyncio.sleep(0.05)  # 50ms delay
            return CommandResult(success=True, command_id=cmd.command_id)
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        # Execute multiple commands
        for _ in range(3):
            cmd = TestCommand()
            await middleware.process_command(cmd, slow_handler, next_cmd)
        
        # Check stats
        stats = await middleware.get_stats()
        assert "command_TestCommand" in stats
        assert stats["command_TestCommand"]["count"] == 3
        assert stats["command_TestCommand"]["avg_ms"] >= 50
        assert stats["command_TestCommand"]["min_ms"] >= 50
        assert stats["command_TestCommand"]["max_ms"] >= 50
    
    @pytest.mark.asyncio
    async def test_retry_middleware_success(self):
        """Test retry middleware with eventual success."""
        middleware = RetryMiddleware(max_retries=3, retry_delay=0.01)
        
        # Handler that fails twice then succeeds
        attempt_count = 0
        
        async def flaky_handler(cmd: Command) -> CommandResult:
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise ValueError(f"Attempt {attempt_count} failed")
            
            return CommandResult(success=True, command_id=cmd.command_id)
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        cmd = TestCommand()
        result = await middleware.process_command(cmd, flaky_handler, next_cmd)
        
        assert result.success
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_middleware_max_retries(self):
        """Test retry middleware hitting max retries."""
        middleware = RetryMiddleware(max_retries=2, retry_delay=0.01)
        
        # Handler that always fails
        async def failing_handler(cmd: Command) -> CommandResult:
            raise ValueError("Always fails")
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        cmd = TestCommand()
        
        with pytest.raises(ValueError, match="Always fails"):
            await middleware.process_command(cmd, failing_handler, next_cmd)
    
    @pytest.mark.asyncio
    async def test_retry_middleware_exponential_backoff(self):
        """Test retry middleware with exponential backoff."""
        middleware = RetryMiddleware(
            max_retries=3,
            retry_delay=0.01,
            exponential_backoff=True
        )
        
        delays: List[float] = []
        last_time = asyncio.get_event_loop().time()
        
        async def timing_handler(cmd: Command) -> CommandResult:
            nonlocal last_time
            now = asyncio.get_event_loop().time()
            if last_time:
                delays.append(now - last_time)
            last_time = now
            raise ValueError("Force retry")
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        cmd = TestCommand()
        
        try:
            await middleware.process_command(cmd, timing_handler, next_cmd)
        except ValueError:
            pass  # Expected
        
        # Verify exponential delays (approximately)
        assert len(delays) >= 2
        assert delays[1] > delays[0] * 1.5  # Should roughly double
    
    @pytest.mark.asyncio
    async def test_validation_middleware(self):
        """Test validation middleware functionality."""
        middleware = ValidationMiddleware(validate_session_id=True)
        
        # Handler that returns success
        async def handler(cmd: Command) -> CommandResult:
            return CommandResult(success=True, command_id=cmd.command_id)
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        # Test with valid command
        cmd = TestCommand(session_id="test-session")
        result = await middleware.process_command(cmd, handler, next_cmd)
        assert result.success
        
        # Test with missing session_id
        cmd_no_session = TestCommand()
        cmd_no_session.session_id = ""  # Empty session
        result = await middleware.process_command(cmd_no_session, handler, next_cmd)
        assert not result.success
        assert "missing session_id" in result.error
    
    @pytest.mark.asyncio
    async def test_rate_limit_middleware(self):
        """Test rate limit middleware functionality."""
        # 5 per second limit
        middleware = RateLimitMiddleware(max_per_second=5.0)
        
        # Handler that tracks calls
        call_times: List[float] = []
        
        async def handler(cmd: Command) -> CommandResult:
            call_times.append(asyncio.get_event_loop().time())
            return CommandResult(success=True, command_id=cmd.command_id)
        
        async def next_cmd(cmd: Command, handler: Any) -> CommandResult:
            return await handler(cmd)
        
        # Execute commands rapidly
        start_time = asyncio.get_event_loop().time()
        for _ in range(6):
            cmd = TestCommand()
            await middleware.process_command(cmd, handler, next_cmd)
        
        # Check that rate limiting occurred
        total_time = asyncio.get_event_loop().time() - start_time
        assert total_time >= 1.0  # Should take at least 1 second for 6 calls at 5/sec
        
        # Verify spacing between calls
        for i in range(1, len(call_times)):
            interval = call_times[i] - call_times[i-1]
            assert interval >= 0.19  # Should be ~0.2s apart (1/5)