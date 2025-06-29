from dataclasses import dataclass
from typing import Optional
import uuid
import re
import json
import os
from llmgine.llm.engine.engine import Engine
from llmgine.llm.models.model import Model
from llmgine.messages.commands import Command, CommandResult
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event
import ast

PROMPT_PATHS = {
    "selection_prompt": "prompts/selection_new.md",
    "disambiguation_prompt": "prompts/disambiguation_prompt.md",
    "decomposition_prompt": "prompts/decomposition_prompt.md",
    "factextraction_prompt": "prompts/factextraction_prompt.md"
}

def load_prompts() -> dict[str, str]:
    """Load all prompts from their respective files."""
    return {
        name: open(path, 'r', encoding='utf-8').read()
        for name, path in PROMPT_PATHS.items()
    }

@dataclass
class FactExtractorEngineCommand(Command):
    prompt: str = ""

@dataclass
class FactExtractorEngineStatusEvent(Event):
    status: str = ""

@dataclass
class FactExtractorPromptCommand(Command):
    prompt: str = ""

@dataclass
class FactExtractorEngine:
    model: Model
    system_prompt: Optional[dict[str, str]] = None
    session_id: Optional[str] = None
    bus: MessageBus = MessageBus()
    
    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = load_prompts()
    
    async def handle_command(self, command: FactExtractorEngineCommand) -> CommandResult:
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))
        
    async def execute(self, prompt: str) -> str:
        await self.bus.publish(
            FactExtractorEngineStatusEvent(status="Starting fact extraction...", session_id=self.session_id)
        )
        sentence_data = sentence_context(prompt)
        
        results = []
        for data in sentence_data:
            context_text = " ".join(data["context"])
            sentence_prompt = f"Context: {context_text}\nSentence: {data['sentence']}"
            
            await self.bus.publish(
                FactExtractorEngineStatusEvent(status=f"Analyzing sentence {data['sentence_index'] + 1} of {len(sentence_data)}...", session_id=self.session_id)
            )
            fact_extraction_context = [
                {"role": "system", "content": self.system_prompt["factextraction_prompt"]},
                {"role": "user", "content": sentence_prompt},
            ]
            fact_extraction_response = await self.model.generate(fact_extraction_context, temperature=0.0)
            try:
                fact_extraction_response = ast.literal_eval(fact_extraction_response.content)
            except Exception as e:
                print(f"Error: {e}")
                print(f"Fact extraction response: {fact_extraction_response.content}")
                continue
            results.extend(fact_extraction_response)

            # disambiguation_context = [
            #     {"role": "system", "content": self.system_prompt["disambiguation_prompt"]},
            #     {"role": "user", "content": sentence_prompt},
            # ]
            # disambiguation_response = await self.model.generate(disambiguation_context)
            
            # await self.bus.publish(
            #     FactExtractorEngineStatusEvent(status=f"Extracting facts from sentence {data['sentence_index'] + 1}...", session_id=self.session_id)
            # )
            # decomposition_context = [
            #     {"role": "system", "content": self.system_prompt["decomposition_prompt"]},
            #     {"role": "user", "content": f"Original text: {sentence_prompt}\nDisambiguation: {disambiguation_response.content}"},
            # ]
            # decomposition_response = await self.model.generate(decomposition_context)
            # # output = f"Original text: {sentence_prompt}\n\nDisambiguation: {disambiguation_response.content}\n\nDecomposed: {decomposition_response.content}\n\n=========================\n\n"
            # # results.append(output)
        
            # selection_context = [
            #     {"role": "system", "content": self.system_prompt["selection_prompt"]},
            #     {"role": "user", "content": f"Sentences: {decomposition_response.content}"},
            # ]
            # selection_response = await self.model.generate(selection_context)
            # output = f"Original text: {data['sentence']}\n\nDisambiguation: {disambiguation_response.content}\n\nDecomposed: {decomposition_response.content}\n\nSelection: {selection_response.content}\n\n=========================\n\n"
            # results.append(output)
            
            # if selection_response.content.strip():
            #     results.append({
            #         "original": data["sentence"],
            #         "facts": selection_response.content
            #     })
        
        # if not results:
        #     print("finished")
        #     await self.bus.publish(
        #         FactExtractorEngineStatusEvent(status="finished", session_id=self.session_id)
        #     )
        #     return "No verifiable facts found in the text."
    
        # formatted_results = ["Extracted Facts:"]
        # for result in results:
        #     formatted_results.append(f"\nFrom: {result['original']}")
        #     formatted_results.append(f"Facts: {result['facts']}")
        #     formatted_results.append("-" * 40)

        await self.bus.publish(
            FactExtractorEngineStatusEvent(status="finished", session_id=self.session_id)
        )
        return "\n".join(results)
        # return "\n".join(formatted_results)

async def useFactExtractorEngine(
    prompt: str, model, system_prompt: Optional[dict[str, str]] = None
):
    session_id = str(uuid.uuid4())
    if system_prompt is None:
        system_prompt = load_prompts()
    engine = FactExtractorEngine(
        model=model,
        system_prompt=system_prompt,
        session_id=session_id
    )
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
    engine = FactExtractorEngine(
        Gpt41Mini(Providers.OPENAI), session_id="test"
    )
    cli = EngineCLI("test")
    cli.register_engine(engine)
    cli.register_engine_command(FactExtractorEngineCommand)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(FactExtractorEngineStatusEvent)
    await cli.main()

def sentence_context(texts: str, output_file: str = "sentence_contexts.json") -> list[dict]:
    """
    Split text into sentences and create a JSON file with each sentence and its preceding context.
    
    Args:
        texts (str): Either the text content directly or path to the input text file
        output_file (str): Path to save the JSON file (default: sentence_contexts.json)
    
    Returns:
        list[dict]: List of dictionaries containing sentences and their contexts
    """
    try:
        if os.path.isfile(texts):
            with open(texts, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = texts
        
        sentences = [s.strip() for s in text.replace('\n', ' ').split('. ') if s.strip()]
        
        i = 1
        sentence_data = []
        for i, sentence in enumerate(sentences):
            context = sentences[:i]  
            sentence_data.append({
                "sentence": sentence,
                "context": context,
                "sentence_index": i
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sentence_data, f, indent=2, ensure_ascii=False)
        
        return sentence_data
    except FileNotFoundError:
        print(f"Error: Could not find file {texts}")
        return []
    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return []

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())




