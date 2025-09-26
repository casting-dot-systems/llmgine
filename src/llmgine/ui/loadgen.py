import asyncio
from typing import Callable, Optional

from llmgine.llm import SessionID
from llmgine.messages.events import Event

from .handlers_catalog import LogEvent


class LoadTask:
    def __init__(self, task: asyncio.Task, name: str) -> None:
        self.task = task
        self.name = name


async def _firehose(publish: Callable[[Event, bool], None],
                    rate_per_sec: float,
                    duration_s: float,
                    payload_prefix: str,
                    session_id: Optional[SessionID]) -> None:
    if rate_per_sec <= 0 or duration_s <= 0:
        return
    period = 1.0 / rate_per_sec
    deadline = asyncio.get_event_loop().time() + duration_s
    i = 0
    while asyncio.get_event_loop().time() < deadline:
        evt = LogEvent(message=f"{payload_prefix}-{i}", session_id=session_id or SessionID("BUS"))
        await publish(evt, False)
        i += 1
        await asyncio.sleep(period)


def start_firehose(publish: Callable[[Event, bool], None],
                   rate_per_sec: float = 200.0,
                   duration_s: float = 10.0,
                   payload_prefix: str = "firehose",
                   session_id: Optional[SessionID] = None) -> LoadTask:
    loop = asyncio.get_event_loop()
    task = loop.create_task(_firehose(publish, rate_per_sec, duration_s, payload_prefix, session_id))
    return LoadTask(task, name=f"firehose@{rate_per_sec}rpsx{duration_s}s")
