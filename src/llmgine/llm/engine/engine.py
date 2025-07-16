"""Core LLM Engine for handling interactions with language models."""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from llmgine.bus.bus import MessageBus
from llmgine.llm import EngineID, SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event

class EngineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"

class Engine(BaseModel):
    """Placeholder for all engines, all attributes should be serializable"""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='ignore')
    
    engine_id: EngineID = Field(default_factory=lambda: EngineID(str(uuid.uuid4())))
    status: EngineStatus = Field(default=EngineStatus.RUNNING)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def __init__(self, **data: Any):
        super().__init__(**data)


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
    session_id: SessionID = Field(default_factory=lambda: SessionID(str(uuid.uuid4())))

    def __init__(self, engine_id: Optional[EngineID] = None, session_id: Optional[SessionID] = None, **data: Any):
        if session_id is None:
            session_id = SessionID(str(uuid.uuid4()))
        super().__init__(engine_id=engine_id, session_id=session_id, **data)

    async def handle_command(self, command: Command):
        bus = MessageBus()
        
        result = self.execute(command.prompt)
        await bus.publish(
            DummyEngineStatusUpdate(status="started", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        await bus.publish(
            DummyEngineStatusUpdate(status="thinking", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        await bus.publish(
            DummyEngineStatusUpdate(status="finished", session_id=self.session_id)
        )
        # breakpoint()
        confirmation = await bus.execute(
            DummyEngineConfirmationInput(
                prompt="Do you want to execute a tool?", session_id=self.session_id
            )
        )
        await bus.publish(
            DummyEngineStatusUpdate(status="executing tool", session_id=self.session_id)
        )
        await asyncio.sleep(1)
        if confirmation.result:
            await bus.publish(
                DummyEngineToolResult(
                    tool_name="get_weather",
                    result="Tool result is here!",
                    session_id=self.session_id,
                )
            )
        await bus.publish(
            DummyEngineStatusUpdate(status="finished", session_id=self.session_id)
        )
        await bus.ensure_events_processed()
        return CommandResult(success=True, result=result)

    def execute(self, prompt: str):
        return "Hello, world!"


def main():
    engine = DummyEngine(EngineID("123"), SessionID("123"))
    result = engine.handle_command(DummyEngineCommand(prompt="Hello, world!"))
    print(result)


if __name__ == "__main__":
    main()
