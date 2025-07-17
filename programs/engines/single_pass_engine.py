import uuid
from typing import Optional
from pydantic import Field, PrivateAttr

from llmgine.bus.bus import MessageBus
from llmgine.llm import SessionID
from llmgine.llm.engine.engine import Engine
from llmgine.llm.models.model import Model
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.providers.response import LLMResponse
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event


class SinglePassEngineCommand(Command):
    prompt: str = Field(default_factory=str)


class SinglePassEngineStatusEvent(Event):
    status: str = Field(default_factory=str)


class SinglePassEngine(Engine):
    _model: Model = PrivateAttr()
    _system_prompt: Optional[str] = PrivateAttr()
    _session_id: SessionID = PrivateAttr()
    _bus: MessageBus = PrivateAttr()
    

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        session_id: Optional[SessionID] = None,
    ):
        super().__init__()
        self._llm_manager = Gpt41Mini(Providers.OPENAI)
        self._system_prompt = system_prompt
        self._session_id = session_id or SessionID(str(uuid.uuid4()))
        self._bus = MessageBus()

    async def handle_command(self, command: SinglePassEngineCommand) -> CommandResult:
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    async def execute(self, prompt: str) -> str:
        if self._system_prompt:
            context = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            context = [{"role": "user", "content": prompt}]
        await self._bus.publish(
            SinglePassEngineStatusEvent(status="Calling LLM", session_id=self._session_id)
        )

        response: LLMResponse = await self._llm_manager.generate(messages=context)
        await self._bus.publish(
            SinglePassEngineStatusEvent(status="finished", session_id=self._session_id)
        )

        return response.raw.choices[0].message.content


async def use_single_pass_engine(
    prompt: str, system_prompt: Optional[str] = None
):
    session_id = SessionID(str(uuid.uuid4()))
    engine = SinglePassEngine(system_prompt, session_id)
    return await engine.execute(prompt)


async def main(case: int):
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    if case == 1:
        engine = SinglePassEngine(
            "respond in pirate", SessionID("test")
        )
        cli = EngineCLI(SessionID("test"))
        cli.register_engine(engine)
        cli.register_engine_command(SinglePassEngineCommand, engine.handle_command)
        cli.register_engine_result_component(EngineResultComponent)
        cli.register_loading_event(SinglePassEngineStatusEvent)
        await cli.main()
    elif case == 2:
        result = await use_single_pass_engine(
            "Hello, world!", Gpt41Mini(Providers.OPENAI), "respond in pirate"
        )
        print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(1))
