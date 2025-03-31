"""Core LLM Engine for handling interactions with language models."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Protocol, Type, Union

from llmgine.bus import MessageBus
from llmgine.llm.context import InMemoryContextManager
from llmgine.llm.engine.messages import (
    ClearHistoryCommand, 
    LLMResponseEvent,
    PromptCommand, 
    SystemPromptCommand,
    ToolCallEvent,
    ToolResultEvent,
)
from llmgine.llm.providers import DefaultLLMManager, create_tool_call
from llmgine.llm.tools import default_tool_manager
from llmgine.messages.commands import CommandResult
from llmgine.messages.events import LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class LLMEngine:
    """Engine for handling interactions with language models.
    
    This class is the main coordinator of LLM interactions, managing:
    1. Context and history management
    2. LLM provider selection and communication
    3. Tool/function calling
    4. Event publishing
    """

    def __init__(
        self,
        message_bus: MessageBus,
    ):
        """Initialize the LLM engine.

        Args:
            message_bus: The message bus for command and event handling
        """
        self.message_bus = message_bus
        
        # Create tightly coupled components
        self.llm_manager = DefaultLLMManager()
        self.context_manager = InMemoryContextManager()
        self.tool_manager = default_tool_manager
        
        # Register command handlers
        self._register_command_handlers()
        
    def _register_command_handlers(self) -> None:
        """Register command handlers with the message bus."""
        self.message_bus.register_command_handler(
            PromptCommand, self._handle_prompt
        )
        self.message_bus.register_command_handler(
            SystemPromptCommand, self._handle_system_prompt
        )
        self.message_bus.register_command_handler(
            ClearHistoryCommand, self._handle_clear_history
        )

    async def _handle_system_prompt(self, command: SystemPromptCommand) -> CommandResult:
        """Handle a system prompt command.

        Args:
            command: The system prompt command

        Returns:
            The result of handling the command
        """
        system_prompt = command.system_prompt
        conversation_id = command.conversation_id

        try:
            # Get current context
            context = self.context_manager.get_context(conversation_id)

            # Remove any existing system prompts
            context = [msg for msg in context if msg.get("role") != "system"]

            # Add system prompt at the beginning
            system_message = {"role": "system", "content": system_prompt}
            self.context_manager.clear_context(conversation_id)
            self.context_manager.add_message(conversation_id, system_message)

            # Add back the rest of the messages
            for message in context:
                self.context_manager.add_message(conversation_id, message)

            logger.info(
                f"Added system prompt to conversation {conversation_id}"
            )

            return CommandResult(
                command_id=command.id,
                success=True, 
                result="System prompt set successfully"
            )

        except Exception as e:
            error_msg = f"Error setting system prompt: {e!s}"
            logger.exception(error_msg)
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _handle_clear_history(self, command: ClearHistoryCommand) -> CommandResult:
        """Handle a clear history command.

        Args:
            command: The clear history command

        Returns:
            The result of handling the command
        """
        conversation_id = command.conversation_id

        try:
            self.context_manager.clear_context(conversation_id)
            
            logger.info(
                f"Cleared conversation history for {conversation_id}"
            )

            return CommandResult(
                command_id=command.id,
                success=True, 
                result="Conversation history cleared"
            )

        except Exception as e:
            error_msg = f"Error clearing conversation history: {e!s}"
            logger.exception(error_msg)
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _handle_prompt(self, command: PromptCommand) -> CommandResult:
        """Handle a prompt command.

        Args:
            command: The prompt command

        Returns:
            The result of handling the command
        """
        prompt = command.prompt
        conversation_id = command.conversation_id

        # Add user message to context
        user_message = {"role": "user", "content": prompt}
        self.context_manager.add_message(conversation_id, user_message)

        # Get the conversation context
        context = self.context_manager.get_context(conversation_id)

        # Get tool descriptions if enabled
        tools = None
        if command.use_tools and self.tool_manager.tools:
            tools = self.tool_manager.get_tool_descriptions()

        try:
            # Generate response using the LLM manager
            llm_response = await self.llm_manager.generate(
                prompt=prompt,
                context=context,
                provider_id=command.provider_id,
                temperature=command.temperature,
                max_tokens=command.max_tokens,
                model=command.model,
                tools=tools,
                **command.extra_params
            )
            
            # Add assistant response to context
            assistant_message = {
                "role": "assistant",
            }
            
            # Add content if present (content is required by OpenAI except when tool_calls are present)
            if llm_response.content:
                assistant_message["content"] = llm_response.content
            elif not llm_response.tool_calls:
                assistant_message["content"] = ""
                
            # Add tool calls if present
            if llm_response.tool_calls:
                assistant_message["tool_calls"] = [
                    tc.to_dict() for tc in llm_response.tool_calls
                ]
                
            # Add the message to context
            self.context_manager.add_message(conversation_id, assistant_message)

            # Publish response event
            await self.message_bus.publish(
                LLMResponseEvent(prompt, llm_response, conversation_id)
            )

            # Handle tool calls if present
            if llm_response.has_tool_calls():
                await self._process_tool_calls(llm_response.tool_calls, conversation_id)

            return CommandResult(
                command_id=command.id,
                success=True, 
                result=llm_response
            )

        except Exception as e:
            error_msg = f"Error processing prompt: {e!s}"
            logger.exception(error_msg)
                
            return CommandResult(
                command_id=command.id,
                success=False, 
                error=error_msg
            )

    async def _process_tool_calls(
        self, tool_calls: List[ToolCall], conversation_id: str
    ) -> None:
        """Process tool calls from the LLM response.

        Args:
            tool_calls: The tool calls to process
            conversation_id: The conversation identifier
        """
        for tool_call in tool_calls:
            # Publish tool call event
            await self.message_bus.publish(
                ToolCallEvent(tool_call.function.name, tool_call.function.arguments, conversation_id)
            )

            try:
                # Execute tool and get result
                tool_result = await self.tool_manager.execute(
                    tool_call.function.name,
                    tool_call.function.arguments
                )

                # Add tool result to context
                tool_message = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": tool_result,
                }
                self.context_manager.add_message(conversation_id, tool_message)

                # Publish tool result event
                await self.message_bus.publish(
                    ToolResultEvent(tool_call.function.name, tool_result, conversation_id)
                )

            except Exception as e:
                error_msg = f"Error executing tool {tool_call.function.name}: {e!s}"
                logger.exception(error_msg)

                # Add error to context
                error_content = json.dumps({"error": error_msg})
                error_message = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": error_content,
                }
                self.context_manager.add_message(conversation_id, error_message)

                # Publish tool result event with error
                await self.message_bus.publish(
                    ToolResultEvent(
                        tool_call.function.name, None, error=error_msg, 
                        conversation_id=conversation_id
                    )
                )