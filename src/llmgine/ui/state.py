import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from llmgine.bus import BackpressureStrategy, MessageBus, ResilientMessageBus
from llmgine.bus.filters import (
    DebugFilter,
    EventTypeFilter,
    MetadataFilter,
    PatternFilter,
    RateLimitFilter,
    SessionFilter,
)
from llmgine.bus.interfaces import HandlerPriority
from llmgine.bus.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RetryMiddleware,
    TimingMiddleware,
    ValidationMiddleware,
)
from llmgine.llm import SessionID
from llmgine.messages.approvals import ApprovalCommand, ApprovalResult
from llmgine.messages.commands import CommandResult
from llmgine.observability.manager import ObservabilityManager

from .handlers_catalog import (
    EchoCommand,
    FailingCommand,
    GenerateEventsCommand,
    LogEvent,
    ScheduledPingEvent,
    SleepCommand,
    echo_command_handler,
    failing_command_handler,
    generate_events_command_handler,
    sleep_command_handler,
    slow_log_event_handler,
)
from .loadgen import LoadTask, start_firehose
from .observability_ui import UIEventBufferHandler

logger = logging.getLogger(__name__)


@dataclass
class UIConfig:
    bus_kind: str = "resilient"  # "basic" or "resilient"
    queue_size: int = 10000
    backpressure: str = BackpressureStrategy.DROP_OLDEST.value
    batch_size: int = 10
    batch_timeout: float = 0.01


@dataclass
class UIState:
    config: UIConfig = field(default_factory=UIConfig)
    bus: Optional[MessageBus] = None
    observability: ObservabilityManager = field(default_factory=ObservabilityManager)
    ui_observer: UIEventBufferHandler = field(default_factory=lambda: UIEventBufferHandler(max_events=2000))
    metrics_task: Optional[asyncio.Task] = None
    load_tasks: Dict[str, LoadTask] = field(default_factory=dict)
    running: bool = False

    # Simple registry flagging
    mw_logging: bool = False
    mw_validation: bool = False
    mw_timing: bool = False
    mw_retry: bool = False
    mw_rate_limit: bool = False
    handlers_registered: bool = False

    def ensure_bus(self) -> MessageBus:
        if self.bus is None:
            # Choose initial bus type
            if self.config.bus_kind == "resilient":
                self.bus = ResilientMessageBus(
                    event_queue_size=int(self.config.queue_size),
                    backpressure_strategy=BackpressureStrategy(self.config.backpressure),
                )
            else:
                self.bus = MessageBus()
            # Hook observability
            self.observability.clear_handlers()
            self.observability.register_handler(self.ui_observer)
            self.bus.set_observability_manager(self.observability)
        return self.bus

    async def start_bus(self) -> None:
        bus = self.ensure_bus()
        if self.running:
            logger.info("MessageBus is already running")
            return

        await bus.start()

        # Register built-in handlers only if not already registered
        if not self.handlers_registered:
            try:
                bus.register_command_handler(EchoCommand, echo_command_handler(bus.publish))
                bus.register_command_handler(FailingCommand, failing_command_handler(bus.publish))
                bus.register_command_handler(SleepCommand, sleep_command_handler(bus.publish))
                bus.register_command_handler(GenerateEventsCommand, generate_events_command_handler(bus.publish))
                bus.register_event_handler(LogEvent, slow_log_event_handler(), priority=HandlerPriority.NORMAL)
                self.handlers_registered = True
                logger.info("UI command handlers registered successfully")
            except ValueError as e:
                logger.warning(f"Handler registration skipped: {e}")
                # Handlers already exist, which is fine
                self.handlers_registered = True

        self.running = True

    async def stop_bus(self) -> None:
        if self.bus:
            await self.bus.stop()
        self.running = False

    async def reset_bus(self) -> None:
        if self.bus:
            await self.bus.reset()
            self.bus = None
        self.running = False
        self.handlers_registered = False

    async def apply_batch_config(self, size: int, timeout: float) -> None:
        bus = self.ensure_bus()
        bus.set_batch_processing(size, timeout)
        self.config.batch_size = size
        self.config.batch_timeout = timeout

    # -------------- Middleware toggles --------------
    def toggle_logging_mw(self, enabled: bool) -> None:
        self.mw_logging = enabled
        bus = self.ensure_bus()
        if enabled:
            bus.add_command_middleware(LoggingMiddleware())
            bus.add_event_middleware(LoggingMiddleware())
        # Note: bus doesn't support removal; reset_bus to clear

    def toggle_validation_mw(self, enabled: bool) -> None:
        self.mw_validation = enabled
        bus = self.ensure_bus()
        if enabled:
            bus.add_command_middleware(ValidationMiddleware())

    def toggle_timing_mw(self, enabled: bool) -> None:
        self.mw_timing = enabled
        bus = self.ensure_bus()
        if enabled:
            tm = TimingMiddleware()
            bus.add_command_middleware(tm)
            bus.add_event_middleware(tm)

    def toggle_retry_mw(self, enabled: bool) -> None:
        self.mw_retry = enabled
        bus = self.ensure_bus()
        if enabled:
            bus.add_command_middleware(RetryMiddleware())

    def toggle_rate_limit_mw(self, enabled: bool, max_per_second: float = 10.0) -> None:
        self.mw_rate_limit = enabled
        bus = self.ensure_bus()
        if enabled:
            bus.add_command_middleware(RateLimitMiddleware(max_per_second=max_per_second))

    # -------------- Filters --------------
    def add_debug_filter(self) -> None:
        self.ensure_bus().add_event_filter(DebugFilter(enabled=True))

    def add_session_filter(self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None) -> None:
        inc = {SessionID(s) for s in (include or [])} if include else None
        exc = {SessionID(s) for s in (exclude or [])} if exclude else None
        self.ensure_bus().add_event_filter(SessionFilter(include_sessions=inc, exclude_sessions=exc))

    def add_event_type_filter(self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None) -> None:
        # We only know LogEvent here; UI uses it for demo
        type_map = {"LogEvent": LogEvent, "ScheduledPingEvent": ScheduledPingEvent}
        inc = {type_map[t] for t in (include or []) if t in type_map} if include else None
        exc = {type_map[t] for t in (exclude or []) if t in type_map} if exclude else None
        self.ensure_bus().add_event_filter(EventTypeFilter(include_types=inc, exclude_types=exc))

    def add_pattern_filter(self, include: Optional[list[str]] = None, exclude: Optional[list[str]] = None) -> None:
        self.ensure_bus().add_event_filter(PatternFilter(include_patterns=include, exclude_patterns=exclude))

    def add_metadata_filter(self, required: Optional[Dict[str, Any]] = None, keys: Optional[list[str]] = None) -> None:
        req_keys = set(keys or [])
        req_vals = dict(required or {})
        self.ensure_bus().add_event_filter(MetadataFilter(required_keys=req_keys, required_values=req_vals))

    def add_rate_limit_filter(self, max_per_sec: float = 100.0, per_session: bool = True, per_type: bool = False) -> None:
        self.ensure_bus().add_event_filter(RateLimitFilter(max_per_second=max_per_sec, per_session=per_session, per_type=per_type))

    # -------------- Commands & Events --------------
    async def exec_echo(self, text: str, session: Optional[str] = None) -> CommandResult:
        return await self.ensure_bus().execute(EchoCommand(text=text, session_id=SessionID(session or "BUS")))

    async def exec_fail(self, message: str = "boom", raise_exc: bool = True, session: Optional[str] = None) -> CommandResult:
        return await self.ensure_bus().execute(FailingCommand(message=message, raise_exception=raise_exc, session_id=SessionID(session or "BUS")))

    async def exec_sleep(self, seconds: float = 0.25, session: Optional[str] = None) -> CommandResult:
        return await self.ensure_bus().execute(SleepCommand(seconds=seconds, session_id=SessionID(session or "BUS")))

    async def exec_generate(self, count: int = 100, delay_ms: int = 0, payload: str = "ping", session: Optional[str] = None) -> CommandResult:
        return await self.ensure_bus().execute(GenerateEventsCommand(count=count, delay_ms=delay_ms, payload=payload, session_id=SessionID(session or "BUS")))

    async def publish_log(self, message: str, session: Optional[str] = None) -> None:
        await self.ensure_bus().publish(LogEvent(message=message, session_id=SessionID(session or "BUS")))

    async def schedule_ping(self, in_seconds: float = 3.0, message: str = "scheduled ping", session: Optional[str] = None) -> None:
        from datetime import datetime, timedelta
        evt = ScheduledPingEvent(
            message=message,
            scheduled_time=datetime.now() + timedelta(seconds=max(0.0, in_seconds)),
            session_id=SessionID(session or "BUS"),
        )
        await self.ensure_bus().publish(evt)

    # -------------- Approval demo --------------
    async def exec_approval_demo(self, approver: Optional[str] = None, ttl_seconds: float = 10.0, session: Optional[str] = None) -> ApprovalResult:
        # Creates an ApprovalCommand that "awaits" approval; UI can simulate approval by publishing a LogEvent
        cmd = ApprovalCommand(
            approver=approver,
            expires_at=None if ttl_seconds <= 0 else __import__("datetime").datetime.now() + __import__("datetime").timedelta(seconds=ttl_seconds),
            session_id=SessionID(session or "BUS"),
            on_approval_callback=LogEvent(message="APPROVED"),
            on_denial_callback=LogEvent(message="DENIED"),
            on_expiry_callback=LogEvent(message="EXPIRED"),
        )
        # No special handler registered by default; user can register their own or treat this as flow demo.
        return await self.ensure_bus().execute(cmd)

    # -------------- Load gen --------------
    def start_firehose(self, rps: float, duration: float, prefix: str, session: Optional[str]) -> str:
        bus = self.ensure_bus()
        task = start_firehose(bus.publish, rate_per_sec=rps, duration_s=duration, payload_prefix=prefix, session_id=SessionID(session or "BUS"))
        self.load_tasks[task.name] = task
        return task.name

    def stop_task(self, name: str) -> None:
        if name in self.load_tasks:
            self.load_tasks[name].task.cancel()
            del self.load_tasks[name]

    # -------------- Metrics --------------
    async def gather_metrics(self) -> Dict[str, Any]:
        bus = self.ensure_bus()
        metrics = await bus.get_metrics()
        stats = await bus.get_stats()
        out = {"metrics": metrics, "stats": stats, "bus_kind": self.config.bus_kind}
        if isinstance(bus, ResilientMessageBus):
            out["queue_metrics"] = bus.get_queue_metrics()
            out["circuit_breakers"] = bus.get_circuit_breaker_states()
            out["dead_letter_queue_size"] = bus.dead_letter_queue_size
        out["events_recent"] = self.ui_observer.snapshot()[-25:]
        return out


state = UIState()
