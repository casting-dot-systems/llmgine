"""Common middleware implementations for the message bus.

This module provides reusable middleware for logging, timing, validation, etc.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from llmgine.bus.interfaces import AsyncCommandHandler, AsyncEventHandler, HandlerMiddleware
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


logger = logging.getLogger(__name__)


class LoggingMiddleware(HandlerMiddleware):
    """Middleware that logs command and event processing."""
    
    def __init__(self, log_level: int = logging.INFO):
        """Initialize with specified log level."""
        self.log_level = log_level
    
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Log command execution."""
        command_type = type(command).__name__
        logger.log(
            self.log_level,
            f"Executing command {command_type} (id={command.command_id}, "
            f"session={command.session_id})"
        )
        
        start_time = time.time()
        try:
            result = await next_middleware(command, handler)
            duration = time.time() - start_time
            
            logger.log(
                self.log_level,
                f"Command {command_type} completed in {duration:.3f}s "
                f"(success={result.success})"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                f"Command {command_type} failed after {duration:.3f}s: {e}"
            )
            raise
    
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Log event processing."""
        event_type = type(event).__name__
        handler_name = getattr(handler, "__qualname__", repr(handler))
        
        logger.log(
            self.log_level,
            f"Processing event {event_type} with handler {handler_name} "
            f"(session={event.session_id})"
        )
        
        start_time = time.time()
        try:
            await next_middleware(event, handler)
            duration = time.time() - start_time
            
            logger.log(
                self.log_level,
                f"Event {event_type} processed by {handler_name} in {duration:.3f}s"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                f"Event {event_type} handler {handler_name} failed after "
                f"{duration:.3f}s: {e}"
            )
            raise


class TimingMiddleware(HandlerMiddleware):
    """Middleware that tracks execution timing statistics."""
    
    def __init__(self):
        """Initialize timing statistics."""
        self.command_timings: Dict[str, list[float]] = {}
        self.event_timings: Dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
    
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Track command execution time."""
        start_time = time.time()
        try:
            return await next_middleware(command, handler)
        finally:
            duration = time.time() - start_time
            command_type = type(command).__name__
            
            async with self._lock:
                if command_type not in self.command_timings:
                    self.command_timings[command_type] = []
                self.command_timings[command_type].append(duration)
    
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Track event processing time."""
        start_time = time.time()
        try:
            await next_middleware(event, handler)
        finally:
            duration = time.time() - start_time
            event_type = type(event).__name__
            
            async with self._lock:
                if event_type not in self.event_timings:
                    self.event_timings[event_type] = []
                self.event_timings[event_type].append(duration)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get timing statistics."""
        async with self._lock:
            stats = {}
            
            # Command statistics
            for cmd_type, timings in self.command_timings.items():
                if timings:
                    stats[f"command_{cmd_type}"] = {
                        "count": len(timings),
                        "avg_ms": sum(timings) / len(timings) * 1000,
                        "min_ms": min(timings) * 1000,
                        "max_ms": max(timings) * 1000,
                    }
            
            # Event statistics
            for evt_type, timings in self.event_timings.items():
                if timings:
                    stats[f"event_{evt_type}"] = {
                        "count": len(timings),
                        "avg_ms": sum(timings) / len(timings) * 1000,
                        "min_ms": min(timings) * 1000,
                        "max_ms": max(timings) * 1000,
                    }
            
            return stats


class RetryMiddleware(HandlerMiddleware):
    """Middleware that retries failed commands."""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        exponential_backoff: bool = True,
    ):
        """Initialize retry configuration."""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
    
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Retry failed commands with backoff."""
        last_error: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await next_middleware(command, handler)
                
                # If command succeeded, return result
                if result.success:
                    return result
                
                # Command returned failure, check if we should retry
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Command {type(command).__name__} failed (attempt {attempt + 1}/"
                        f"{self.max_retries + 1}), retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    # No more retries
                    return result
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Command {type(command).__name__} raised exception "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}, "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
        
        # Should not reach here, but return failure if we do
        return CommandResult(
            success=False,
            command_id=command.command_id,
            error=f"Max retries exceeded: {last_error}",
        )
    
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Pass through events without retry (events should be idempotent)."""
        await next_middleware(event, handler)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay with optional exponential backoff."""
        if self.exponential_backoff:
            return self.retry_delay * (2 ** attempt)
        return self.retry_delay


class ValidationMiddleware(HandlerMiddleware):
    """Middleware that validates commands before execution."""
    
    def __init__(self, validate_session_id: bool = True):
        """Initialize validation options."""
        self.validate_session_id = validate_session_id
    
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Validate command before processing."""
        # Validate session ID if required
        if self.validate_session_id and not command.session_id:
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error="Command missing session_id",
            )
        
        # Validate command has required fields
        if not command.command_id:
            return CommandResult(
                success=False,
                command_id="unknown",
                error="Command missing command_id",
            )
        
        # Additional validation can be added here
        # For example, check command-specific required fields
        
        return await next_middleware(command, handler)
    
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Validate event before processing."""
        # Basic validation
        if self.validate_session_id and not event.session_id:
            logger.warning(
                f"Event {type(event).__name__} missing session_id, skipping handler"
            )
            return
        
        await next_middleware(event, handler)


class RateLimitMiddleware(HandlerMiddleware):
    """Middleware that implements rate limiting for commands."""
    
    def __init__(self, max_per_second: float = 10.0):
        """Initialize rate limit configuration."""
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.last_execution: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def process_command(
        self,
        command: Command,
        handler: AsyncCommandHandler,
        next_middleware: Callable[[Command, AsyncCommandHandler], Awaitable[CommandResult]],
    ) -> CommandResult:
        """Apply rate limiting to commands."""
        command_type = type(command).__name__
        
        async with self._lock:
            now = time.time()
            last_time = self.last_execution.get(command_type, 0)
            time_since_last = now - last_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                logger.warning(
                    f"Rate limit for {command_type}: waiting {wait_time:.3f}s"
                )
                await asyncio.sleep(wait_time)
                now = time.time()
            
            self.last_execution[command_type] = now
        
        return await next_middleware(command, handler)
    
    async def process_event(
        self,
        event: Event,
        handler: AsyncEventHandler,
        next_middleware: Callable[[Event, AsyncEventHandler], Awaitable[None]],
    ) -> None:
        """Pass through events without rate limiting."""
        await next_middleware(event, handler)