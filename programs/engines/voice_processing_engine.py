"""
This engine's job is to receive facts and decides whether to
create, update, or delete a fact.

To create or update a fact, construct the content as follows:
<CREATE_FACT><fact>

To delete a fact, construct the content as follows:
<DELETE_FACT><fact>
"""

from typing import Optional
import uuid
import json
from pydantic import Field, PrivateAttr

from llmgine.llm.engine.engine import Engine
from llmgine.llm.providers.response import LLMResponse
from llmgine.messages.commands import CommandResult, Command
from llmgine.bus.bus import MessageBus
from llmgine.messages.events import Event
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.tools import ToolCall
from llmgine.ui.cli.voice_processing_engine_cli import (
    SpecificPrompt,
    SpecificComponent,
    SpecificPromptCommand,
    SpecificComponentEvent,
)
from llmgine.llm import SessionID, AsyncOrSyncToolFunction
from programs.stt import process_audio, merge_speakers, merge_speakers_engine
from llmgine.llm.models.openai_models import OpenAIResponse
from openai.types.chat.chat_completion_message import ChatCompletionMessage

SYSTEM_PROMPT = (
    f"You are a voice processing engine. You are provided with the number of speakers inside the conversation, "
    f"and a snippet of what each speaker said in the conversation. "
    f"The number of speakers present in the snippet will be greater than the actual number of speakers in the conversation. "
    f"Your task is to decide which speakers in the snippet should be merged into a single speaker, based on the context, speaking style, "
    f"and the content of what they said. Make sure the number of speakers after merge is the same as the actual number of speakers in the conversation. "
    f"If you think speaker_1 and speaker_2 are actually one person, speaker_3 and speaker_4 are one person: "
    f'example function call: merge_speakers("speaker_1,speaker_2") ; merge_speakers("speaker_3,speaker_4")'
)


class VoiceProcessingEngineCommand(Command):
    prompt: str = Field(default_factory=str)


class VoiceProcessingEngineStatusEvent(Event):
    status: str = Field(default_factory=str)


class VoiceProcessingEngineToolResultEvent(Event):
    tool_name: str = Field(default_factory=str)
    result: str = Field(default_factory=str)


# ------------------------------------ENGINE-------------------------------------------


class VoiceProcessingEngine(Engine):
    _llm_manager: Gpt41Mini = PrivateAttr()
    _system_prompt: Optional[str] = PrivateAttr()
    _session_id: SessionID = PrivateAttr()
    _message_bus: MessageBus = PrivateAttr()
    _context_manager: SimpleChatHistory = PrivateAttr()
    _tool_manager: ToolManager = PrivateAttr()

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        session_id: Optional[SessionID] = None,
    ):
        super().__init__()
        self._system_prompt: Optional[str] = system_prompt
        self._session_id: SessionID = session_id or SessionID(str(uuid.uuid4()))
        self._message_bus: MessageBus = MessageBus()
        self._engine_id: str = str(uuid.uuid4())

        # Create tightly coupled components - pass the simple engine
        self._context_manager = SimpleChatHistory(
            engine_id=self._engine_id, session_id=self._session_id
        )
        self._llm_manager = Gpt41Mini(Providers.OPENAI)
        self._tool_manager = ToolManager(
            engine_id=self._engine_id, session_id=self._session_id, llm_model_name="openai"
        )

    async def handle_command(
        self, command: Command
    ) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        assert isinstance(command, VoiceProcessingEngineCommand), "command is not a VoiceProcessingEngineCommand"
        try:
            # Process the audio file and get the snippet
            audio_file, number_of_speakers = command.prompt.split("&")
            snippet, audio_file_path = process_audio(audio_file, number_of_speakers)
            self.audio_file_path = audio_file_path

            if len(snippet) == int(number_of_speakers):
                return CommandResult(success=True, result="No merge is required.")

            # Prompt the LLM with the actual number of speakers and the snippet
            prompt = (
                "Actual Number of speakers: "
                + number_of_speakers
                + ".\nHere is the snippet of what each speaker said in the conversation: "
                + str(snippet)
            )
            result = await self.execute(prompt=prompt)

            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    async def execute(self, prompt: str) -> str:
        """This function executes the engine.

        Args:
            prompt: The prompt to execute
        """

        self._context_manager.store_string(prompt, "user")

        while True:
            # Retrieve the current context
            current_context = await self._context_manager.retrieve()
            # Get the tools
            tools = await self._tool_manager.get_tools()
            # Notify status
            await self._message_bus.publish(
                VoiceProcessingEngineStatusEvent(
                    status="calling LLM", session_id=self._session_id
                )
            )
            # Generate the response
            response: LLMResponse = await self._llm_manager.generate(
                messages=current_context, tools=tools, tool_choice="auto"
            )
            assert isinstance(response, OpenAIResponse), (
                "response is not an OpenAIResponse"
            )

            # Get the response message
            response_message: ChatCompletionMessage = response.raw.choices[0].message
            assert isinstance(response_message, ChatCompletionMessage), (
                "response_message is not a ChatCompletionMessage"
            )

            # Store the response message
            await self._context_manager.store_assistant_message(response_message)
            # If there are no tool calls, break the loop and return the content
            if not response_message.tool_calls:
                final_content = response_message.content or ""
                # Notify status complete
                await self._message_bus.publish(
                    VoiceProcessingEngineStatusEvent(
                        status="finished", session_id=self._session_id
                    )
                )
                return final_content

            # Else, process tool calls
            for tool_call in response_message.tool_calls:
                tool_call_obj = ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                )
                try:
                    # Execute the tool
                    await self._message_bus.publish(
                        VoiceProcessingEngineStatusEvent(
                            status="executing tool", session_id=self._session_id
                        )
                    )

                    # Insert audio file path here manually
                    if tool_call.function.name == "merge_speakers":
                        args = json.loads(tool_call.function.arguments)
                        args["audio_file"] = self.audio_file_path
                        tool_call_obj.arguments = json.dumps(args)
                        tool_call_obj.name = "merge_speakers_engine"

                    result = await self._tool_manager.execute_tool_call(tool_call_obj)

                    # Convert result to string if needed for history
                    if isinstance(result, dict):
                        result_str = json.dumps(result)
                    else:
                        result_str = str(result)
                    # Store tool execution result in history
                    self._context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=result_str,
                    )
                    # Publish tool execution event
                    await self._message_bus.publish(
                        VoiceProcessingEngineToolResultEvent(
                            tool_name=tool_call_obj.name,
                            result=result_str,
                            session_id=self._session_id,
                        )
                    )

                except Exception as e:
                    error_msg = f"Error executing tool {tool_call_obj.name}: {str(e)}"
                    print(error_msg)  # Debug print
                    # Store error result in history
                    self._context_manager.store_tool_call_result(
                        tool_call_id=tool_call_obj.id,
                        name=tool_call_obj.name,
                        content=error_msg,
                    )

    async def register_tool(self, function: AsyncOrSyncToolFunction):
        """Register a function as a tool.

        Args:
            function: The function to register as a tool
        """
        await self._tool_manager.register_tool(function)


async def main():
    from llmgine.ui.cli.voice_processing_engine_cli import VoiceProcessingEngineCLI
    from llmgine.ui.cli.components import EngineResultComponent, ToolComponent
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()

    # Initialize the engine
    engine = VoiceProcessingEngine(
        system_prompt=SYSTEM_PROMPT,
        session_id=SessionID("test")
    )

    # Register cli components
    cli = VoiceProcessingEngineCLI(SessionID("test"))
    cli.register_engine(engine)
    cli.register_engine_command(VoiceProcessingEngineCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(VoiceProcessingEngineStatusEvent)
    cli.register_component_event(VoiceProcessingEngineToolResultEvent, ToolComponent)
    cli.register_prompt_command(SpecificPromptCommand, SpecificPrompt)
    cli.register_component_event(SpecificComponentEvent, SpecificComponent)

    # Register tools
    await engine.register_tool(merge_speakers)
    await engine.register_tool(merge_speakers_engine)

    await cli.main()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
