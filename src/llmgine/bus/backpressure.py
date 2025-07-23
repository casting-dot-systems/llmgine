"""Backpressure handling for message bus to prevent queue overflow.

Provides bounded queues and overflow strategies for managing high event rates.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar

from llmgine.messages.events import Event
from llmgine.bus.metrics import get_metrics_collector

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BackpressureStrategy(Enum):
    """Strategies for handling queue overflow."""
    DROP_OLDEST = "drop_oldest"  # Remove oldest items to make room
    REJECT_NEW = "reject_new"    # Reject new items when full
    ADAPTIVE_RATE_LIMIT = "adaptive_rate_limit"  # Slow down producers


@dataclass
class QueueMetrics:
    """Metrics for monitoring queue performance."""
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    total_rejected: int = 0
    high_water_mark_hits: int = 0
    last_high_water_mark: Optional[datetime] = None
    current_size: int = 0
    max_size_reached: int = 0


class BoundedEventQueue(Generic[T]):
    """Bounded queue with backpressure handling for events.
    
    Provides configurable strategies for handling queue overflow and
    monitoring of queue health metrics.
    """

    def __init__(self,
                 maxsize: int = 10000,
                 high_water_mark: float = 0.8,
                 low_water_mark: float = 0.5,
                 strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST,
                 on_high_water: Optional[Callable[[], None]] = None,
                 on_low_water: Optional[Callable[[], None]] = None) -> None:
        """Initialize bounded queue.
        
        Args:
            maxsize: Maximum queue size
            high_water_mark: Percentage (0-1) that triggers backpressure
            low_water_mark: Percentage (0-1) that releases backpressure
            strategy: Strategy for handling overflow
            on_high_water: Callback when high water mark is reached
            on_low_water: Callback when low water mark is reached
        """
        if not 0 < low_water_mark < high_water_mark <= 1:
            raise ValueError("Must have 0 < low_water_mark < high_water_mark <= 1")
            
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._high_water_mark = int(maxsize * high_water_mark)
        self._low_water_mark = int(maxsize * low_water_mark)
        self._strategy = strategy
        self._on_high_water = on_high_water
        self._on_low_water = on_low_water
        
        # State tracking
        self._backpressure_active = False
        self._rate_limit_delay = 0.0  # For adaptive rate limiting
        self._metrics = QueueMetrics()
        
        # Lock for coordinating overflow handling
        self._overflow_lock = asyncio.Lock()
        
        logger.info(f"BoundedEventQueue initialized: maxsize={maxsize}, "
                   f"high_water={self._high_water_mark}, low_water={self._low_water_mark}, "
                   f"strategy={strategy.value}")

    async def put(self, item: T) -> bool:
        """Put an item in the queue with backpressure handling.
        
        Args:
            item: Item to enqueue
            
        Returns:
            True if item was enqueued, False if rejected
        """
        # Apply rate limiting if using adaptive strategy
        if self._strategy == BackpressureStrategy.ADAPTIVE_RATE_LIMIT and self._rate_limit_delay > 0:
            await asyncio.sleep(self._rate_limit_delay)
        
        # Handle overflow based on strategy
        if self._queue.full():
            return await self._handle_overflow(item)
        
        try:
            self._queue.put_nowait(item)
            self._metrics.total_enqueued += 1
            
            # Update metrics and check high water mark after adding
            current_size = self.qsize()
            self._metrics.current_size = current_size
            self._metrics.max_size_reached = max(self._metrics.max_size_reached, current_size)
            
            # Check high water mark after adding item
            if current_size >= self._high_water_mark and not self._backpressure_active:
                self._activate_backpressure()
                
            return True
        except asyncio.QueueFull:
            # Race condition - queue became full
            return await self._handle_overflow(item)

    async def get(self) -> T:
        """Get an item from the queue.
        
        Returns:
            Next item from queue
        """
        item = await self._queue.get()
        self._metrics.total_dequeued += 1
        
        current_size = self.qsize()
        self._metrics.current_size = current_size
        
        # Check low water mark
        if current_size <= self._low_water_mark and self._backpressure_active:
            self._deactivate_backpressure()
            
        return item

    def get_nowait(self) -> T:
        """Get an item without waiting.
        
        Returns:
            Next item from queue
            
        Raises:
            asyncio.QueueEmpty: If queue is empty
        """
        item = self._queue.get_nowait()
        self._metrics.total_dequeued += 1
        
        current_size = self.qsize()
        self._metrics.current_size = current_size
        
        # Check low water mark
        if current_size <= self._low_water_mark and self._backpressure_active:
            self._deactivate_backpressure()
            
        return item

    async def _handle_overflow(self, new_item: T) -> bool:
        """Handle queue overflow based on configured strategy.
        
        Args:
            new_item: Item trying to be added
            
        Returns:
            True if item was added, False if rejected
        """
        async with self._overflow_lock:
            # Double-check queue is still full
            if not self._queue.full():
                try:
                    self._queue.put_nowait(new_item)
                    self._metrics.total_enqueued += 1
                    return True
                except asyncio.QueueFull:
                    pass
            
            if self._strategy == BackpressureStrategy.DROP_OLDEST:
                try:
                    # Remove oldest item
                    dropped = self._queue.get_nowait()
                    self._metrics.total_dropped += 1
                    logger.warning(f"Dropped oldest item due to overflow: {type(dropped).__name__}")
                    
                    # Add new item
                    self._queue.put_nowait(new_item)
                    self._metrics.total_enqueued += 1
                    return True
                except asyncio.QueueEmpty:
                    # Race condition - queue was emptied
                    self._queue.put_nowait(new_item)
                    self._metrics.total_enqueued += 1
                    return True
                    
            elif self._strategy == BackpressureStrategy.REJECT_NEW:
                self._metrics.total_rejected += 1
                logger.warning(f"Rejected new item due to overflow: {type(new_item).__name__}")
                return False
                
            elif self._strategy == BackpressureStrategy.ADAPTIVE_RATE_LIMIT:
                # Increase rate limit delay
                self._rate_limit_delay = min(self._rate_limit_delay + 0.001, 0.1)
                self._metrics.total_rejected += 1
                logger.warning(f"Rejected item and increased rate limit to {self._rate_limit_delay:.3f}s")
                return False
                
        return False

    def _activate_backpressure(self) -> None:
        """Activate backpressure mechanisms."""
        self._backpressure_active = True
        self._metrics.high_water_mark_hits += 1
        self._metrics.last_high_water_mark = datetime.now()
        
        logger.warning(f"Backpressure activated: queue size {self.qsize()}/{self._maxsize}")
        
        # Update metrics
        metrics = get_metrics_collector()
        metrics.set_gauge("backpressure_active", 1)
        
        if self._on_high_water:
            try:
                self._on_high_water()
            except Exception as e:
                logger.error(f"Error in high water callback: {e}")

    def _deactivate_backpressure(self) -> None:
        """Deactivate backpressure mechanisms."""
        self._backpressure_active = False
        
        # Update metrics
        metrics = get_metrics_collector()
        metrics.set_gauge("backpressure_active", 0)
        
        # Reset adaptive rate limit
        if self._strategy == BackpressureStrategy.ADAPTIVE_RATE_LIMIT:
            self._rate_limit_delay = max(self._rate_limit_delay - 0.01, 0.0)
        
        logger.info(f"Backpressure deactivated: queue size {self.qsize()}/{self._maxsize}")
        
        if self._on_low_water:
            try:
                self._on_low_water()
            except Exception as e:
                logger.error(f"Error in low water callback: {e}")

    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()

    @property
    def is_backpressure_active(self) -> bool:
        """Check if backpressure is currently active."""
        return self._backpressure_active

    @property
    def metrics(self) -> QueueMetrics:
        """Get queue metrics."""
        self._metrics.current_size = self.qsize()
        return self._metrics

    def task_done(self) -> None:
        """Mark a task as done (for compatibility with asyncio.Queue)."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait for all tasks to be processed."""
        await self._queue.join()