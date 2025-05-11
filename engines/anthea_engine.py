from dataclasses import dataclass
from typing import Optional
import uuid
from llmgine.llm.engine.engine import Engine
from llmgine.llm.models.model import Model
from llmgine.messages.commands import Command, CommandResult
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event


@dataclass
class AntheaEngineCommand(Command):
    prompt: str = ""
    
@dataclass
class AntheaEngineStatusEvent(Event):
    status: str = ""
    
@dataclass
class AntheaPromptCommand(Command):
    prompt: str = ""

@dataclass
class AntheaEngine:
    model: Model
    system_prompt: Optional[str] = """You are an assistant to a fact - checker . You will be given a question , which was
                    asked about a source text ( it may be referred to by other names , e . g . , a
                    dataset ) . You will also be given an excerpt from a response to the question . If
                    it contains "[...]" , this means that you are NOT seeing all sentences in the
                    response . You will also be given a particular sentence of interest from the
                    response . Your task is to determine whether this particular sentence contains at
                    least one specific and verifiable proposition , and if so , to return a complete
                    sentence that only contains verifiable information """
    session_id: Optional[str] = None
    bus:  MessageBus = MessageBus()
    
    async def handle_command(self, command: AntheaEngineCommand) -> CommandResult:
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
        
    async def execute(self, prompt: str) -> str:
        if self.system_prompt:
            context = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            context = [{"role": "user", "content": prompt}]
        await self.bus.publish(
            AntheaEngineStatusEvent(status="Calling LLM", session_id=self.session_id)
        )
        response = await self.model.generate(context)
        await self.bus.publish(
            AntheaEngineStatusEvent(status="finished", session_id=self.session_id)
        )
        return response.content       

async def useAntheaEngine(
    prompt: str, model, system_prompt: Optional[str] = None  
):
    session_id = str(uuid.uuid4())
    engine = AntheaEngine(model, system_prompt, session_id)
    return await engine.execute(prompt)
    
async def main(case: int):
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap
    from llmgine.llm.models.openai_models import Gpt41Mini
    from llmgine.llm.providers.providers import Providers

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    if case == 1:
        engine = AntheaEngine(
            Gpt41Mini(Providers.OPENAI), session_id="test"
        )
        cli = EngineCLI("test")
        cli.register_engine(engine)
        cli.register_engine_command(AntheaEngineCommand, engine.handle_command)
        cli.register_engine_result_component(EngineResultComponent)
        cli.register_loading_event(AntheaEngineStatusEvent)
        await cli.main()
    elif case == 2:
        result = await useAntheaEngine(
            "Hello, world!", Gpt41Mini(Providers.OPENAI), "respond in spoilt child"
        )
        print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(1))




