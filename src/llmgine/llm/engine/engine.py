"""Core LLM Engine for handling interactions with language models."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from llmgine.bus.bus import MessageBus
from llmgine.llm import EngineID, SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from pydantic import BaseModel

class EngineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"

class Engine(BaseModel):
    """Placeholder for all engines"""

    def __init__(self, engine_id: Optional[EngineID] = None):
        self.engine_id: EngineID = engine_id or EngineID(str(uuid.uuid4()))
        self.status: EngineStatus = EngineStatus.RUNNING
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.bus = MessageBus()


class DummyEngineCommand(Command):
    prompt: str = ""


class DummyEngineStatusUpdate(Event):
    status: str = ""


class DummyEngineConfirmationInput(Command):
    prompt: str = ""


class DummyEngineToolResult(Event):
    tool_name: str = ""
    result: str = ""


class DummyEngine(Engine):
    """Dummy engine for testing"""

    def __init__(self, engine_id: Optional[EngineID] = None, session_id: Optional[SessionID] = None):
        super().__init__(engine_id)
        self.session_id: SessionID = session_id or SessionID(str(uuid.uuid4()))

    async def handle_command(self, command: Command):
        result = self.execute(command.prompt)
        await self.bus.publish(
            DummyEngineStatusUpdate(status="started", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        await self.bus.publish(
            DummyEngineStatusUpdate(status="thinking", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        await self.bus.publish(
            DummyEngineStatusUpdate(status="finished", session_id=self.session_id)
        )
        # breakpoint()
        confirmation = await self.bus.execute(
            DummyEngineConfirmationInput(
                prompt="Do you want to execute a tool?", session_id=self.session_id
            )
        )
        await self.bus.publish(
            DummyEngineStatusUpdate(status="executing tool", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        if confirmation.result:
            await self.bus.publish(
                DummyEngineToolResult(
                    tool_name="get_weather",
                    result="Tool result is here!",
                    session_id=self.session_id,
                )
            )
        await self.bus.publish(
            DummyEngineStatusUpdate(status="finished", session_id=self.session_id)
        )
        await self.bus.ensure_events_processed()
        return CommandResult(success=True, result=result)

    def execute(self, prompt: str):
        return "Hello, world!"


def main():
    engine = DummyEngine(EngineID("123"), SessionID("123"))
    result = engine.handle_command(DummyEngineCommand(prompt="Hello, world!"))
    print(result)


if __name__ == "__main__":
    main()
