"""In-memory implementation of the ContextManager interface."""

import asyncio
from typing import Any, Dict, List, Optional
import uuid

from llmgine.bus.bus import MessageBus
from llmgine.llm.context import ContextManager
from llmgine.llm.context.context_events import (
    ChatHistoryRetrievedEvent,
    ChatHistoryUpdatedEvent,
)

class SimpleChatHistory:
    def __init__(self, engine_id: str, session_id: str):
        self.engine_id = engine_id
        self.session_id = session_id
        self.context_manager_id = str(uuid.uuid4())
        self.bus = MessageBus()
        self.response_log: List[Any] = []  # Logs raw responses/inputs
        self.chat_history: List[Dict[str, Any]] = []  # Stores OpenAI formatted messages
        self.system_prompt: Optional[str] = None  # Changed from self.system

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt
        # Clear history if system prompt changes?
        # self.clear()

    async def store_assistant_message(self, message_object: Any):
        """Store the raw assistant message object (which might contain tool calls)."""
        self.response_log.append(message_object)
        # Convert the OpenAI message object to the dict format for history
        history_entry = {
            "role": message_object.role,
            "content": message_object.content,
        }
        if message_object.tool_calls:
            history_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message_object.tool_calls
            ]
        # Ensure content is not None if there are tool_calls, as per OpenAI spec
        if history_entry.get("tool_calls") and history_entry["content"] is None:
            history_entry["content"] = ""  # Or potentially remove the content key?

        self.chat_history.append(history_entry)
        await self.bus.publish(
            ChatHistoryUpdatedEvent(
                engine_id=self.engine_id,
                session_id=self.session_id,
                context_manager_id=self.context_manager_id,
                context=self.chat_history,
            )
        )

    def store_string(self, string: str, role: str):
        """Store a simple user or system message."""
        self.response_log.append([role, string])
        self.chat_history.append({"role": role, "content": string})

    def store_tool_call_result(self, tool_call_id: str, name: str, content: str):
        """Store the result of a specific tool call."""
        result_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        }
        self.response_log.append(result_message)  # Log the result message
        self.chat_history.append(result_message)

    async def retrieve(self) -> List[Dict[str, Any]]:
        """Retrieve the chat history in OpenAI format."""
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        result.extend(self.chat_history)
        await self.bus.publish(
            ChatHistoryRetrievedEvent(
                engine_id=self.engine_id,
                session_id=self.session_id,
                context_manager_id=self.context_manager_id,
                context=result,
            )
        )
        return result

    def clear(self):
        self.response_log = []
        self.chat_history = []
        self.system_prompt = ""


class SingleChatContextManager(ContextManager):
    def __init__(self, max_context_length: int = 100):
        """Initialize the single chat context manager.

        Args:
            max_context_length: Maximum number of messages to keep in context
        """
        self.context_raw = []

    def get_context(self) -> List[Dict[str, Any]]:
        """Get the conversation context for a specific conversation.

        Returns:
            List[Dict[str, Any]]: The conversation context/history
        """
        return self.context_raw

    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a message to the conversation context.

        Args:
            message: The message to add to the context
        """
        self.context_raw.append(message)


class InMemoryContextManager(ContextManager):
    """In-memory implementation of the context manager interface."""

    def __init__(self, max_context_length: int = 100):
        """Initialize the in-memory context manager.

        Args:
            max_context_length: Maximum number of messages to keep in context
        """
        self.contexts: Dict[str, List[Dict[str, Any]]] = {}
        self.max_context_length = max_context_length

    def get_context(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get the conversation context for a specific conversation.

        Args:
            conversation_id: The conversation identifier

        Returns:
            List[Dict[str, Any]]: The conversation context/history
        """
        return self.contexts.get(conversation_id, [])

    def add_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the conversation context.

        Args:
        conversation_id: The conversation identifier
            message: The message to add to the context
        """
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = []

        self.contexts[conversation_id].append(message)

        # Trim context if it exceeds max length
        if len(self.contexts[conversation_id]) > self.max_context_length:
            # Keep the first message (usually system prompt) and trim the oldest messages
            first_message = self.contexts[conversation_id][0]
            self.contexts[conversation_id] = [first_message] + self.contexts[
                conversation_id
            ][-(self.max_context_length - 1) :]

    def clear_context(self, conversation_id: str) -> None:
        """Clear the context for a specific conversation.

        Args:
            conversation_id: The conversation identifier
        """
        if conversation_id in self.contexts:
            self.contexts[conversation_id] = []
