"""Core LLM Engine for handling interactions with language models."""

import asyncio
from dataclasses import dataclass

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


class Engine:
    """Placeholder for all engines"""

    pass


@dataclass
class DummyEngineCommand(Command):
    prompt: str = ""


@dataclass
class DummyEngineStatusUpdate(Event):
    status: str = ""


@dataclass
class DummyEngineConfirmationInput(Command):
    prompt: str = ""


@dataclass
class DummyEngineToolResult(Event):
    tool_name: str = ""
    result: str = ""


class DummyEngine(Engine):
    """Dummy engine for testing"""

    def __init__(self, session_id: SessionID):
        self.session_id: SessionID = session_id
        self.bus = MessageBus()

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
    engine = DummyEngine(SessionID("123"))
    result = engine.handle_command(DummyEngineCommand(prompt="Hello, world!"))
    print(result)


if __name__ == "__main__":
    main()
