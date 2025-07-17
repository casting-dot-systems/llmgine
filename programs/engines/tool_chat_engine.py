import json
import asyncio
from typing import Any
from pydantic import Field, PrivateAttr

from llmgine.bus.bus import MessageBus
from llmgine.llm.context.memory import SimpleChatHistory
from llmgine.llm.models.openai_models import Gpt41Mini
from llmgine.llm.providers.providers import Providers
from llmgine.llm.providers.response import LLMResponse
from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools import ToolCall
from llmgine.llm.models.openai_models import OpenAIResponse
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.ui.cli.cli import EngineCLI
from llmgine.ui.cli.components import EngineResultComponent
from llmgine.llm import SessionID, AsyncOrSyncToolFunction
from llmgine.llm.engine.engine import Engine


class ToolChatEngineCommand(Command):
    """Command for the Tool Chat Engine."""

    prompt: str = Field(default_factory=str)


class ToolChatEngineStatusEvent(Event):
    """Event emitted when the status of the engine changes."""

    status: str = Field(default_factory=str)


class ToolChatEngineToolResultEVent(Event):
    """Event emitted when a tool is executed."""

    tool_name: str = Field(default_factory=str)
    result: Any = Field(default=None)


class ToolChatEngine(Engine):
    _message_bus: MessageBus = PrivateAttr()
    _session_id: SessionID = PrivateAttr()
    _context_manager: SimpleChatHistory = PrivateAttr()
    _llm_manager: Gpt41Mini = PrivateAttr()
    _tool_manager: ToolManager = PrivateAttr()


    def __init__(
        self,
        session_id: SessionID,
    ):
        """Initialize the LLM engine.

        Args:
            session_id: The session identifier
            api_key: OpenAI API key (defaults to environment variable)
            model: The model to use
            system_prompt: Optional system prompt to set
            message_bus: Optional MessageBus instance (from bootstrap)
        """
        super().__init__()
        # Use the provided message bus or create a new one
        self._message_bus: MessageBus = MessageBus()
        self._session_id: SessionID = SessionID(session_id)

        # Create tightly coupled components - pass the simple engine
        self._context_manager = SimpleChatHistory(
            engine_id=self.engine_id, session_id=self._session_id
        )
        self._llm_manager = Gpt41Mini(Providers.OPENAI)
        self._tool_manager = ToolManager(
            engine_id=self.engine_id, session_id=self._session_id, llm_model_name="openai"
        )

    async def handle_command(self, command: ToolChatEngineCommand) -> CommandResult:
        """Handle a prompt command following OpenAI tool usage pattern.

        Args:
            command: The prompt command to handle

        Returns:
            CommandResult: The result of the command execution
        """
        try:
            # 1. Add user message to history
            self._context_manager.store_string(command.prompt, "user")

            # Loop for potential tool execution cycles
            while True:
                # 2. Get current context (including latest user message or tool results)
                current_context = await self._context_manager.retrieve()

                # 3. Get available tools
                tools = await self._tool_manager.get_tools()

                # 4. Call LLM
                # print(
                #     f"\nCalling LLM with context:\n{json.dumps(current_context, indent=2)}\n"
                # )  # Debug print
                await self._message_bus.publish(
                    ToolChatEngineStatusEvent(
                        status="calling LLM", session_id=self._session_id
                    )
                )
                response: LLMResponse = await self._llm_manager.generate(
                    messages=current_context, tools=tools
                )
                assert isinstance(response, OpenAIResponse), (
                    "response is not an OpenAIResponse"
                )

                # print(f"\nLLM Raw Response:\n{response.raw}\n")  # Debug print

                # 5. Extract the first choice's message object
                # Important: Access the underlying OpenAI object structure
                response_message: ChatCompletionMessage = response.raw.choices[0].message
                assert isinstance(response_message, ChatCompletionMessage), (
                    "response_message is not a ChatCompletionMessage"
                )

                # 6. Add the *entire* assistant message object to history.
                # This is crucial for context if it contains tool_calls.
                await self._context_manager.store_assistant_message(response_message)

                # 7. Check for tool calls
                if not response_message.tool_calls:
                    # No tool calls, break the loop and return the content
                    final_content = response_message.content or ""

                    # Notify status complete
                    await self._message_bus.publish(
                        ToolChatEngineStatusEvent(
                            status="finished", session_id=self._session_id
                        )
                    )
                    return CommandResult(
                        success=True, result=final_content, session_id=self._session_id
                    )

                # 8. Process tool calls
                for tool_call in response_message.tool_calls:
                    tool_call_obj = ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments,
                    )
                    try:
                        # Execute the tool
                        await self._message_bus.publish(
                            ToolChatEngineStatusEvent(
                                status="executing tool", session_id=self._session_id
                            )
                        )

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
                            ToolChatEngineToolResultEVent(
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
                # After processing all tool calls, loop back to call the LLM again
                # with the updated context (including tool results).

        except Exception as e:
            # Log the exception before returning
            # logger.exception(f"Error in handle_prompt_command for session {self.session_id}") # Requires logger setup
            print(f"ERROR in handle_prompt_command: {e}")  # Simple print for now
            import traceback

            traceback.print_exc()  # Print stack trace

            return CommandResult(success=False, error=str(e), session_id=self._session_id)

    async def register_tool(self, function: AsyncOrSyncToolFunction):
        """Register a function as a tool.

        Args:
            function: The function to register as a tool
        """
        await self._tool_manager.register_tool(function)
        print(f"Tool registered: {function.__name__}")

    async def clear_context(self):
        """Clear the conversation context."""
        self._context_manager.clear()

    def set_system_prompt(self, prompt: str):
        """Set the system prompt.

        Args:
            prompt: The system prompt to set
        """
        self._context_manager.set_system_prompt(prompt)


async def main():
    import os

    print(f"Current working directory: {os.getcwd()}")

    from tools.test_tools import get_weather
    from llmgine.ui.cli.components import ToolComponent
    from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()

    cli = EngineCLI(SessionID("test"))
    engine = ToolChatEngine(session_id=SessionID("test"))
    await engine.register_tool(get_weather)
    cli.register_engine(engine)
    cli.register_engine_command(ToolChatEngineCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(ToolChatEngineStatusEvent)
    cli.register_component_event(ToolChatEngineToolResultEVent, ToolComponent)
    await cli.main()


if __name__ == "__main__":
    asyncio.run(main())
