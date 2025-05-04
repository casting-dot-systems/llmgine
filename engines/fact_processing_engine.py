"""
This engine's job is to receive facts and decides whether to
create, update, or delete a fact.

To create or update a fact, construct the content as follows:
<CREATE_FACT><fact>

To delete a fact, construct the content as follows:
<DELETE_FACT><fact>
"""

from dataclasses import dataclass
from typing import Optional
import uuid
import json

from llmgine.llm.engine.engine import Engine
from llmgine.llm.models.model import Model
from llmgine.messages.commands import Command, CommandResult
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools import ToolCall
from llmgine.ui.cli.components import YesNoPromptCommand


SYSTEM_PROMPT = f'You are a fact processing engine. Everything you receive is a fact.'\
f'You will decide whether to create, update, or delete a fact.\n'\
f'Your task:' \
f'1. If there are similar facts, call the send_to_judge tool.'\
f'2. If there are no similar facts, call the create_fact tool.'\
f'3. If requested for deletion and there are similar facts, call get_deletion_confirmation tool before delete_facts tool.\n'\
f'Example 1:'\
f'Example Input: "New fact: I love cheese. Existing facts: I enjoy eating cheese."'\
f'Example Action: "Tool call: send_to_judge"\n'\
f'Example 2:'\
f'Example Input: "New fact: I love cheese. Existing facts: None"'\
f'Example Action: "Tool call: create_fact"\n'\
f'Example 3:'\
f'Example Input: "Delete fact: I love cheese. Existing facts: I enjoy eating cheese."'\
f'Example Action: "Tool call: get_deletion_confirmation"'\
f'Example Tool Result: "Yes"'\
f'Example Action: "Tool call: delete_facts"\n'\
f'Example 4:'\
f'Example Input: "Delete fact: I love cheese. Existing facts: None"'\
f'Example Action: "Cannot delete fact because there are no similar facts"'\
f'Example 5:'\
f'Example Input: "Delete fact: I love cheese. Existing facts: I enjoy eating cheese."'\
f'Example Action: "Tool call: get_deletion_confirmation"'\
f'Example Tool Result: "No."'\
f'Example Action: "Deletion cancelled"'\

CREATE_FACT_TOKEN = "<CREATE_FACT>"
DELETE_FACT_TOKEN = "<DELETE_FACT>"

# ----------------------------------FAKE TOOLS-----------------------------------
def create_fact(fact: str) -> str:
    """This function creates a fact in the database.
    
    Args:
        fact: The fact to create

    Returns:
        A message indicating that the fact was created
    """

    return f"Created fact: {fact}"

def update_fact(fact: str) -> str:
    """This function updates a fact in the database.
    
    Args:
        fact: The fact to update

    Returns:
        A message indicating that the fact was updated
    """

    return f"Updated fact: {fact}"


def delete_facts(facts: list[str]) -> str:
    """This function deletes a fact from the database.
    
    Args:
        facts: The facts to delete

    Returns:
        A message indicating that the facts were deleted
    """

    return f"Deleted facts: {facts}"

def get_similar_facts(fact: str) -> str:
    """This function gets similar facts from the database.

    Args:
        fact: The fact to get

    Returns:
        A message indicating that the fact was retrieved
    """
    if "cheese" in fact:
        return "I enjoy eating cheese."
    if "beef" in fact:
        return "I enjoy eating beef."
    return ""


def send_to_judge(new_fact: str, old_facts: list[str]) -> str:
    """This function sends a fact to the judge.
    
    Args:
        new_fact: The new fact to send
        old_facts: The old facts to compare to

    Returns:
        A message indicating that the fact was sent to the judge
    """

    return f"Sent fact to judge, the judge will decide whether to create, update, or delete the fact."

def get_deletion_confirmation(target_fact: str, similar_facts: list[str]) -> str:
    """This function gets a deletion confirmation from the user.
    
    Args:
        target_fact: The fact to delete
        similar_facts: The similar facts to compare to

    Returns:
        A subset of similar_facts that the user wants to delete. 
    """


    if "cheese" in target_fact:
        return "No"
    return "Yes"

# -------------------------------------------------------------------------------

@dataclass
class FactProcessingEngineCommand(Command):
    prompt: str = ""


@dataclass
class FactProcessingEngineStatusEvent(Event):
    status: str = ""


@dataclass
class FactProcessingEngineToolResultEvent(Event):
    tool_name: str = ""
    result: str = ""

class FactProcessingEngine(Engine):
    def __init__(
        self,
        model: Model,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.session_id = session_id
        self.message_bus = MessageBus()
        self.engine_id = str(uuid.uuid4())

        # Create tightly coupled components - pass the simple engine
        self.context_manager = SimpleChatHistory(
            engine_id=self.engine_id, session_id=self.session_id
        )
        self.llm_manager = Gpt41Mini(Providers.OPENAI)
        self.tool_manager = ToolManager(
            engine_id=self.engine_id, session_id=self.session_id, llm_model_name="openai"
        )

    async def handle_command(self, command: FactProcessingEngineCommand) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        try:
            result = await self.execute(command.prompt)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def __parse_prompt(self, prompt: str) -> str:
        """This function parses the prompt into a content string.
        Content string is formatted as follows:
            if user wants to create a fact:
                New fact: <fact>. Existing facts: <existing_facts>.
            if user wants to delete a fact:
                Delete fact: <fact>. Existing facts: <existing_facts>.
        
        Args:
            prompt: The prompt to parse
        """
        content = ""
        if prompt.startswith(CREATE_FACT_TOKEN):
            prompt = prompt.replace(CREATE_FACT_TOKEN, "")
            content += f'New fact: {prompt}. '
        elif prompt.startswith(DELETE_FACT_TOKEN):
            prompt = prompt.replace(DELETE_FACT_TOKEN, "")
            content += f'Delete fact: {prompt}. '
        else:
            raise ValueError("Invalid prompt: you must use <CREATE_FACT> or <DELETE_FACT> only to create or delete a fact")
        existing_facts = get_similar_facts(prompt)
        if existing_facts == "":
            existing_facts = "None"
        content += f'Existing facts: {existing_facts}'
        return content


    async def execute(self, prompt: str) -> str:
        """This function executes the engine.
        
        Args:
            prompt: The prompt to execute
        """
        try:
            content = self.__parse_prompt(prompt)
        except ValueError as e:
            return str(e)

        self.context_manager.store_string(content, "user")

        while True:
            current_context = await self.context_manager.retrieve()
            tools = await self.tool_manager.get_tools()
            await self.message_bus.publish(
                FactProcessingEngineStatusEvent(
                    status="calling LLM", session_id=self.session_id
                )
            )
            response = await self.llm_manager.generate(
                messages=current_context, tools=tools
            )
            response_message = response.raw.choices[0].message
            await self.context_manager.store_assistant_message(response_message)
            if not response_message.tool_calls:
                # No tool calls, break the loop and return the content
                final_content = response_message.content or ""
                # Notify status complete
                await self.message_bus.publish(
                    FactProcessingEngineStatusEvent(
                        status="finished", session_id=self.session_id
                    )
                )
                return final_content

            # 8. Process tool calls
            for tool_call in response_message.tool_calls:
                tool_call_obj = ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                )
                try:
                    # Execute the tool
                    await self.message_bus.publish(
                        FactProcessingEngineStatusEvent(
                            status="executing tool", session_id=self.session_id
                        )
                    )                
                    
                    result = None
                    if tool_call.function.name == "send_to_judge":
                        args = json.loads(tool_call.function.arguments)
                        new_fact = args["new_fact"]
                        old_facts = args["old_facts"]

                        result = await self.message_bus.execute(
                            YesNoPromptCommand(
                                prompt=f'Do you want to delete the fact: "{new_fact}"? Similar facts: "{old_facts}"',
                                session_id=self.session_id,
                            )
                        )
                    else:
                        result = await self.tool_manager.execute_tool_call(tool_call_obj)

                    # Convert result to string if needed for history
                    if isinstance(result, dict):
                        result_str = json.dumps(result)
                    else:
                        result_str = str(result)
                    # Store tool execution result in history
                    self.context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=result_str,
                    )
                    # Publish tool execution event
                    await self.message_bus.publish(
                        FactProcessingEngineToolResultEvent(
                            tool_name=tool_call_obj.name,
                            result=result_str,
                            session_id=self.session_id,
                        )
                    )

                except Exception as e:
                    error_msg = f"Error executing tool {tool_call_obj.name}: {str(e)}"
                    print(error_msg)  # Debug print
                    # Store error result in history
                    self.context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=error_msg,
                    )
            # After processing all tool calls, loop back to call the LLM again
            # with the updated context (including tool results).

    
    async def register_tool(self, function):
        """Register a function as a tool.

        Args:
            function: The function to register as a tool
        """
        await self.tool_manager.register_tool(function)
        print(f"Tool registered: {function.__name__}")


async def use_fact_processing_engine(
    prompt: str, model: Model, system_prompt: Optional[str] = None
):
    session_id = str(uuid.uuid4())
    engine = FactProcessingEngine(model, system_prompt, session_id)
    return await engine.execute(prompt)


async def main(case: int):
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent, ToolComponent, YesNoPromptCommand, YesNoPrompt
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap
    from llmgine.llm.models.openai_models import Gpt41Mini
    from llmgine.llm.providers.providers import Providers

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    if case == 1:
        engine = FactProcessingEngine(
            model=Gpt41Mini(Providers.OPENAI),
            system_prompt=SYSTEM_PROMPT,
            session_id="test",
        )
        cli = EngineCLI("test")
        cli.register_engine(engine)
        cli.register_engine_command(FactProcessingEngineCommand, engine.handle_command)
        cli.register_engine_result_component(EngineResultComponent)
        cli.register_loading_event(FactProcessingEngineStatusEvent)
        cli.register_component_event(FactProcessingEngineToolResultEvent, ToolComponent)
        cli.register_prompt_command(YesNoPromptCommand, YesNoPrompt)

        # Register tools
        await engine.register_tool(create_fact)
        await engine.register_tool(update_fact)
        await engine.register_tool(delete_facts)
        # await engine.register_tool(get_similar_facts)
        await engine.register_tool(send_to_judge)
        await engine.register_tool(get_deletion_confirmation)
        await cli.main()
    elif case == 2:
        result = await use_fact_processing_engine(
            prompt="I love cheese",
            model=Gpt41Mini(Providers.OPENAI),
            system_prompt=SYSTEM_PROMPT,
        )
        print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(1))


