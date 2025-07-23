"""Resilient message bus implementation with error recovery and retry logic.

Extends the base MessageBus to provide production-grade resilience features.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
from typing import cast

from llmgine.bus.bus import MessageBus, AsyncCommandHandler
from llmgine.bus.backpressure import BoundedEventQueue, BackpressureStrategy
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event, CommandResultEvent
from llmgine.messages.scheduled_events import ScheduledEvent
from llmgine.llm import SessionID

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 0.1
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class HandlerErrorInfo:
    """Track error information for a specific handler."""
    handler_type: Type[Command]
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    total_executions: int = 0


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue."""
    command: Command
    error: str
    attempts: int
    first_attempt: datetime
    last_attempt: datetime
    metadata: Dict[str, Any]


class CircuitState(Enum):
    """States for the circuit breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes in half-open before closing
    window_size: float = 60.0          # Time window for failure counting


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, 
                 name: str,
                 config: Optional[CircuitBreakerConfig] = None) -> None:
        """Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker (usually handler name)
            config: Configuration for circuit breaker behavior
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        self.recent_failures: List[datetime] = []
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self) -> None:
        """Handle successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(f"Circuit breaker '{self.name}' success in HALF_OPEN: {self.success_count}/{self.config.success_threshold}")
                
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                # Reset failure tracking on success
                self.failure_count = 0
                self.recent_failures = []
    
    async def _on_failure(self) -> None:
        """Handle failed execution."""
        async with self._lock:
            now = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open returns to open
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                # Track failures within time window
                self.recent_failures.append(now)
                self._clean_old_failures(now)
                self.failure_count = len(self.recent_failures)
                self.last_failure_time = now
                
                logger.debug(f"Circuit breaker '{self.name}' failure count: {self.failure_count}/{self.config.failure_threshold}")
                
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
    
    def _clean_old_failures(self, now: datetime) -> None:
        """Remove failures outside the time window."""
        cutoff = now - timedelta(seconds=self.config.window_size)
        self.recent_failures = [f for f in self.recent_failures if f > cutoff]
    
    async def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open state."""
        if self.last_state_change:
            elapsed = (datetime.now() - self.last_state_change).total_seconds()
            return elapsed >= self.config.recovery_timeout
        return False
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.recent_failures = []
        self.last_state_change = datetime.now()
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
        logger.warning(f"Circuit breaker '{self.name}' transitioned to OPEN")
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.last_state_change = datetime.now()
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat()
        }


class ResilientMessageBus(MessageBus):
    """Message bus with resilience features including retry logic and dead letter queue."""

    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 max_dead_letter_size: int = 1000,
                 event_queue_size: int = 10000,
                 backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 **kwargs: Any) -> None:
        """Initialize resilient message bus.
        
        Args:
            retry_config: Configuration for retry behavior
            max_dead_letter_size: Maximum size of dead letter queue
            event_queue_size: Maximum size of event queue
            backpressure_strategy: Strategy for handling event queue overflow
            circuit_breaker_config: Configuration for circuit breakers
            **kwargs: Additional arguments passed to parent MessageBus
        """
        super().__init__(**kwargs)
        
        self._retry_config = retry_config or RetryConfig()
        self._max_dead_letter_size = max_dead_letter_size
        self._event_queue_size = event_queue_size
        self._backpressure_strategy = backpressure_strategy
        self._circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        
        # Dead letter queue for commands that exceed retry limits
        self._dead_letter_queue: asyncio.Queue[DeadLetterEntry] = asyncio.Queue(maxsize=max_dead_letter_size)
        
        # Error tracking per handler
        self._handler_errors: Dict[SessionID, Dict[Type[Command], HandlerErrorInfo]] = {}
        
        # Commands currently being retried
        self._retrying_commands: Set[str] = set()
        
        # Circuit breakers per command type
        self._circuit_breakers: Dict[Type[Command], CircuitBreaker] = {}
        
        logger.info(f"ResilientMessageBus initialized with retry config: {self._retry_config}, "
                   f"event queue size: {event_queue_size}, backpressure: {backpressure_strategy.value}")

    async def start(self) -> None:
        """Start the message bus with bounded event queue."""
        if self._processing_task is None:
            if self._event_queue is None:
                # Create bounded queue with backpressure handling
                self._event_queue = BoundedEventQueue[Event](
                    maxsize=self._event_queue_size,
                    strategy=self._backpressure_strategy,
                    high_water_mark=0.8,
                    low_water_mark=0.5,
                    on_high_water=self._on_high_water_mark,
                    on_low_water=self._on_low_water_mark
                )
                logger.info("Bounded event queue created with backpressure handling")
            await self._load_scheduled_events()
            self._processing_task = asyncio.create_task(self._process_events())
            logger.info("ResilientMessageBus started")
        else:
            logger.warning("ResilientMessageBus already running")

    def _on_high_water_mark(self) -> None:
        """Handle high water mark reached in event queue."""
        logger.warning("Event queue high water mark reached - backpressure activated")
        # Could implement additional handling like alerting or metrics

    def _on_low_water_mark(self) -> None:
        """Handle low water mark reached in event queue."""
        logger.info("Event queue low water mark reached - backpressure deactivated")
        # Could implement additional handling

    async def execute(self, command: Command) -> CommandResult:
        """Execute a command with circuit breaker and retry logic.
        
        Args:
            command: The command to execute
            
        Returns:
            CommandResult indicating success or failure
        """
        command_type = type(command)
        session_id = command.session_id
        
        # Get or create circuit breaker for this command type
        if command_type not in self._circuit_breakers:
            self._circuit_breakers[command_type] = CircuitBreaker(
                name=command_type.__name__,
                config=self._circuit_breaker_config
            )
        
        circuit_breaker = self._circuit_breakers[command_type]
        
        # Check circuit breaker state first
        if circuit_breaker.state == CircuitState.OPEN:
            if not await circuit_breaker._should_attempt_reset():
                logger.warning(f"Circuit breaker for {command_type.__name__} is OPEN - rejecting command")
                return CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error=f"Circuit breaker is OPEN for {command_type.__name__}",
                    metadata={
                        "circuit_breaker_state": circuit_breaker.state.value,
                        "circuit_breaker_info": circuit_breaker.get_state_info()
                    }
                )
        
        # Initialize error tracking for this handler if needed
        if session_id not in self._handler_errors:
            self._handler_errors[session_id] = {}
        if command_type not in self._handler_errors[session_id]:
            self._handler_errors[session_id][command_type] = HandlerErrorInfo(handler_type=command_type)
        
        error_info = self._handler_errors[session_id][command_type]
        error_info.total_executions += 1
        
        # Track retry attempts
        attempts = 0
        first_attempt_time = datetime.now()
        last_error: Optional[Exception] = None
        
        while attempts <= self._retry_config.max_retries:
            try:
                # Mark command as being retried if not first attempt
                if attempts > 0:
                    self._retrying_commands.add(command.command_id)
                    logger.info(f"Retrying command {command_type.__name__} (attempt {attempts + 1}/{self._retry_config.max_retries + 1})")
                
                # Execute through circuit breaker
                async def execute_command() -> CommandResult:
                    return await super(ResilientMessageBus, self).execute(command)
                
                result = await circuit_breaker.call(execute_command)
                
                # If successful, reset error tracking
                if result.success:
                    error_info.consecutive_failures = 0
                    if command.command_id in self._retrying_commands:
                        self._retrying_commands.remove(command.command_id)
                    logger.debug(f"Command {command_type.__name__} succeeded after {attempts + 1} attempts")
                    return result
                else:
                    # Command handler returned failure (not exception)
                    raise Exception(f"Command failed: {result.error}")
                    
            except Exception as e:
                last_error = e
                attempts += 1
                
                # Update error tracking
                error_info.failure_count += 1
                error_info.consecutive_failures += 1
                error_info.last_failure = datetime.now()
                
                logger.warning(f"Command {command_type.__name__} failed (attempt {attempts}/{self._retry_config.max_retries + 1}): {e}")
                
                # If circuit breaker opened due to this failure, stop retrying
                if circuit_breaker.state == CircuitState.OPEN:
                    logger.warning(f"Circuit breaker opened for {command_type.__name__} - stopping retries")
                    break
                
                # If we haven't exceeded retries, wait before next attempt
                if attempts <= self._retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempts)
                    logger.debug(f"Waiting {delay:.2f}s before retry")
                    await asyncio.sleep(delay)
                
        # All retries exhausted - add to dead letter queue
        if command.command_id in self._retrying_commands:
            self._retrying_commands.remove(command.command_id)
            
        await self._add_to_dead_letter_queue(
            command=command,
            error=str(last_error),
            attempts=attempts,
            first_attempt=first_attempt_time,
            last_attempt=datetime.now()
        )
        
        # Return failed result
        return CommandResult(
            success=False,
            command_id=command.command_id,
            error=f"Command failed after {attempts} attempts: {last_error}",
            metadata={
                "attempts": attempts,
                "last_error": str(last_error),
                "dead_letter": True,
                "circuit_breaker_state": circuit_breaker.state.value
            }
        )

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self._retry_config.initial_delay * (self._retry_config.exponential_base ** (attempt - 1)),
            self._retry_config.max_delay
        )
        
        # Add jitter if enabled
        if self._retry_config.jitter:
            import random
            delay *= (0.5 + random.random())
            
        return delay

    async def _add_to_dead_letter_queue(self, 
                                       command: Command,
                                       error: str,
                                       attempts: int,
                                       first_attempt: datetime,
                                       last_attempt: datetime) -> None:
        """Add failed command to dead letter queue.
        
        Args:
            command: The failed command
            error: Error message
            attempts: Number of attempts made
            first_attempt: Time of first attempt
            last_attempt: Time of last attempt
        """
        entry = DeadLetterEntry(
            command=command,
            error=error,
            attempts=attempts,
            first_attempt=first_attempt,
            last_attempt=last_attempt,
            metadata={
                "command_type": type(command).__name__,
                "session_id": str(command.session_id)
            }
        )
        
        try:
            await self._dead_letter_queue.put(entry)
            logger.info(f"Added command {type(command).__name__} to dead letter queue")
            
            # Publish event about dead letter
            await self.publish(Event(
                session_id=command.session_id,
                metadata={
                    "event_type": "dead_letter_added",
                    "command_type": type(command).__name__,
                    "command_id": command.command_id,
                    "attempts": attempts,
                    "error": error
                }
            ))
        except asyncio.QueueFull:
            logger.error(f"Dead letter queue full! Cannot add command {type(command).__name__}")

    async def get_dead_letter_entries(self, limit: Optional[int] = None) -> List[DeadLetterEntry]:
        """Retrieve entries from dead letter queue.
        
        Args:
            limit: Maximum number of entries to retrieve
            
        Returns:
            List of dead letter entries
        """
        entries = []
        
        while not self._dead_letter_queue.empty() and (limit is None or len(entries) < limit):
            try:
                entry = self._dead_letter_queue.get_nowait()
                entries.append(entry)
            except asyncio.QueueEmpty:
                break
                
        # Put entries back in queue
        for entry in entries:
            try:
                await self._dead_letter_queue.put(entry)
            except asyncio.QueueFull:
                logger.warning("Could not return entry to dead letter queue")
                
        return entries

    async def retry_dead_letter_entry(self, command_id: str) -> Optional[CommandResult]:
        """Retry a command from the dead letter queue.
        
        Args:
            command_id: ID of command to retry
            
        Returns:
            CommandResult if command found and retried, None otherwise
        """
        # Find and remove entry from dead letter queue
        entries = []
        target_entry = None
        
        while not self._dead_letter_queue.empty():
            try:
                entry = self._dead_letter_queue.get_nowait()
                if entry.command.command_id == command_id:
                    target_entry = entry
                else:
                    entries.append(entry)
            except asyncio.QueueEmpty:
                break
        
        # Return other entries to queue
        for entry in entries:
            try:
                await self._dead_letter_queue.put(entry)
            except asyncio.QueueFull:
                logger.warning("Could not return entry to dead letter queue")
        
        # Retry the command if found
        if target_entry:
            logger.info(f"Retrying dead letter command {type(target_entry.command).__name__}")
            return await self.execute(target_entry.command)
        
        return None

    def get_handler_error_stats(self, session_id: Optional[SessionID] = None) -> Dict[str, Any]:
        """Get error statistics for handlers.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Dictionary of error statistics
        """
        stats = {}
        
        if session_id:
            if session_id in self._handler_errors:
                stats[str(session_id)] = {
                    cmd_type.__name__: {
                        "failure_count": info.failure_count,
                        "consecutive_failures": info.consecutive_failures,
                        "total_executions": info.total_executions,
                        "failure_rate": info.failure_count / info.total_executions if info.total_executions > 0 else 0,
                        "last_failure": info.last_failure.isoformat() if info.last_failure else None
                    }
                    for cmd_type, info in self._handler_errors[session_id].items()
                }
        else:
            for sid, handlers in self._handler_errors.items():
                stats[str(sid)] = {
                    cmd_type.__name__: {
                        "failure_count": info.failure_count,
                        "consecutive_failures": info.consecutive_failures,
                        "total_executions": info.total_executions,
                        "failure_rate": info.failure_count / info.total_executions if info.total_executions > 0 else 0,
                        "last_failure": info.last_failure.isoformat() if info.last_failure else None
                    }
                    for cmd_type, info in handlers.items()
                }
        
        return stats

    @property
    def dead_letter_queue_size(self) -> int:
        """Get current size of dead letter queue."""
        return self._dead_letter_queue.qsize()

    @property
    def is_retrying_commands(self) -> bool:
        """Check if any commands are currently being retried."""
        return len(self._retrying_commands) > 0

    async def publish(self, event: Event, await_processing: bool = True) -> None:
        """Publish an event with backpressure handling.
        
        Args:
            event: The event to publish
            await_processing: Whether to wait for event processing
        """
        logger.info(f"Publishing event {type(event).__name__} in session {event.session_id}")
        
        # Direct call to observability - no event publishing
        if self._observability:
            self._observability.observe_event(event)
        
        try:
            if self._event_queue is None:
                raise ValueError("Event queue is not initialized")
            
            # Use bounded queue's put method which handles backpressure
            if isinstance(self._event_queue, BoundedEventQueue):
                success = await self._event_queue.put(event)
                if success:
                    logger.debug(f"Queued event: {type(event).__name__}")
                else:
                    logger.warning(f"Failed to queue event due to backpressure: {type(event).__name__}")
            else:
                # Fallback to regular queue behavior
                await self._event_queue.put(event)
                logger.debug(f"Queued event: {type(event).__name__}")
                
        except Exception as e:
            logger.error(f"Error queuing event: {e}", exc_info=True)
        finally:
            if not isinstance(event, ScheduledEvent) and await_processing:
                await self.wait_for_events()

    async def wait_for_events(self) -> None:
        """Wait for all current events to be processed."""
        # Simply delegate to parent implementation
        await super().wait_for_events()

    async def reset(self) -> None:
        """Reset the resilient message bus to its initial state."""
        await super().reset()
        
        # Reset resilient-specific state
        self._dead_letter_queue = asyncio.Queue(maxsize=self._max_dead_letter_size)
        self._handler_errors = {}
        self._retrying_commands = set()
        self._circuit_breakers = {}
        
        logger.info("ResilientMessageBus reset")
    
    def get_queue_metrics(self) -> Optional[Dict[str, Any]]:
        """Get metrics from the bounded event queue.
        
        Returns:
            Queue metrics if using bounded queue, None otherwise
        """
        if isinstance(self._event_queue, BoundedEventQueue):
            metrics = self._event_queue.metrics
            return {
                "current_size": metrics.current_size,
                "total_enqueued": metrics.total_enqueued,
                "total_dequeued": metrics.total_dequeued,
                "total_dropped": metrics.total_dropped,
                "total_rejected": metrics.total_rejected,
                "high_water_mark_hits": metrics.high_water_mark_hits,
                "max_size_reached": metrics.max_size_reached,
                "backpressure_active": self._event_queue.is_backpressure_active
            }
        return None
    
    def get_circuit_breaker_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state information for all circuit breakers.
        
        Returns:
            Dictionary mapping command names to circuit breaker state info
        """
        states = {}
        for command_type, breaker in self._circuit_breakers.items():
            states[command_type.__name__] = breaker.get_state_info()
        return states