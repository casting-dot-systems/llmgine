import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.messages.scheduled_events import (
    ScheduledEvent,
    register_scheduled_event_class,
)

# ----------------------------
# Built-in demo/test messages
# ----------------------------

@dataclass
class EchoCommand(Command):
    text: str = ""

@dataclass
class FailingCommand(Command):
    message: str = "boom"
    raise_exception: bool = True

@dataclass
class SleepCommand(Command):
    seconds: float = 0.25

@dataclass
class GenerateEventsCommand(Command):
    count: int = 100
    delay_ms: int = 0
    payload: str = "ping"


@dataclass
class LogEvent(Event):
    message: str = ""
    level: str = "info"


@register_scheduled_event_class
@dataclass
class ScheduledPingEvent(ScheduledEvent):
    message: str = "scheduled ping"


# ----------------------------
# Handler factories
# ----------------------------

def echo_command_handler(publish: Callable[[Event], Any]) -> Callable[[Command], Any]:
    async def handle(cmd: EchoCommand) -> CommandResult:
        await publish(LogEvent(message=f"echo: {cmd.text}", session_id=cmd.session_id))
        return CommandResult(success=True, command_id=cmd.command_id, result={"upper": cmd.text.upper()})
    return handle

def failing_command_handler(publish: Callable[[Event], Any]) -> Callable[[Command], Any]:
    async def handle(cmd: FailingCommand) -> CommandResult:
        if cmd.raise_exception:
            raise RuntimeError(cmd.message)
        return CommandResult(success=False, command_id=cmd.command_id, error=cmd.message)
    return handle

def sleep_command_handler(publish: Callable[[Event], Any]) -> Callable[[Command], Any]:
    async def handle(cmd: SleepCommand) -> CommandResult:
        await asyncio.sleep(max(0.0, float(cmd.seconds)))
        await publish(LogEvent(message=f"slept {cmd.seconds}s", session_id=cmd.session_id))
        return CommandResult(success=True, command_id=cmd.command_id)
    return handle

def generate_events_command_handler(publish: Callable[[Event], Any]) -> Callable[[Command], Any]:
    async def handle(cmd: GenerateEventsCommand) -> CommandResult:
        delay = max(0, int(cmd.delay_ms)) / 1000.0
        for i in range(int(cmd.count)):
            await publish(LogEvent(message=f"{cmd.payload}-{i}", session_id=cmd.session_id))
            if delay:
                await asyncio.sleep(delay)
        return CommandResult(success=True, command_id=cmd.command_id, result={"count": cmd.count})
    return handle


def slow_log_event_handler(delay_ms: int = 20) -> Callable[[Event], Any]:
    async def handle(evt: LogEvent) -> None:
        await asyncio.sleep(max(0, delay_ms) / 1000.0)
        # no-op; observing is handled by Observability
        return None
    return handle
