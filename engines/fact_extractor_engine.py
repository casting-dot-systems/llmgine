import json
import uuid
import asyncio

from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from dataclasses import dataclass
from typing import Optional

    
@dataclass
class EngineStatusEvent(Event):
    status: str = ""
    session_id: Optional[str] = None

@dataclass
class FactExtractorEngineCommand(Command):
    prompt: str = ""

@dataclass
class Engine:
    model = Gpt41Mini(Providers.OPENAI)
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
    
    async def handle_command(self, command: FactExtractorEngineCommand) -> CommandResult:
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
        
    async def execute(self, prompt: str) -> str:
        self.bus = MessageBus()
        if self.system_prompt:
            context = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            context = [{"role": "user", "content": prompt}]
        await self.bus.publish(
            EngineStatusEvent(status="Calling LLM", session_id=self.session_id)
        )
        response = await self.model.generate(context)
        await self.bus.publish( 
            EngineStatusEvent(status="finished", session_id=self.session_id)
        )
        return response.content

    async def handle_fact_extraction(self, command: FactExtractorEngineCommand) -> CommandResult:
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
    
async def useEngine(
    prompt: str, model, system_prompt: Optional[str] = None 
):
    session_id = str(uuid.uuid4())
    engine = Engine(model, system_prompt, session_id)
    return await engine.execute(prompt)
    
async def main():
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap
    from llmgine.llm.models.openai_models import Gpt41Mini
    from llmgine.llm.providers.providers import Providers
    
    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    
    engine = Engine(
        Gpt41Mini(Providers.OPENAI),
        "You are a personal fact extractor.",
        "fact_extractor_session",
    )

    bus = MessageBus()
    cli = EngineCLI("fact_extractor_session")
    cli.register_engine(engine)
    cli.register_engine_command(FactExtractorEngineCommand, engine.handle_fact_extraction)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(EngineStatusEvent)
    await cli.main()
    
if __name__ == "__main__":
    asyncio.run(main())