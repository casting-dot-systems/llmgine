"""Messages used by the LLM engine.

This module defines the commands and events used by the LLM engine.
"""

from typing import Any, Dict, List, Optional

from llmgine.llm.tools.types import ToolCall
from llmgine.messages.commands import Command
from llmgine.messages.events import Event, LLMResponse


class PromptCommand(Command):
    """Command to send a prompt to the LLM."""

    def __init__(
        self, 
        prompt: str, 
        use_tools: bool = True, 
        conversation_id: str = "default",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize the prompt command.
        
        Args:
            prompt: The prompt to send to the LLM
            use_tools: Whether to allow tool usage
            conversation_id: The conversation identifier
            temperature: Optional temperature parameter
            max_tokens: Optional maximum tokens for the response
            model: Optional model name/identifier
            provider_id: Optional provider to use
            **kwargs: Additional provider-specific parameters
        """
        super().__init__()
        self.prompt = prompt
        self.use_tools = use_tools
        self.conversation_id = conversation_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model
        self.provider_id = provider_id
        self.extra_params = kwargs


class SystemPromptCommand(Command):
    """Command to set the system prompt for a conversation."""

    def __init__(self, system_prompt: str, conversation_id: str = "default"):
        """Initialize the system prompt command.
        
        Args:
            system_prompt: The system prompt to set
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.conversation_id = conversation_id


class ClearHistoryCommand(Command):
    """Command to clear the conversation history."""

    def __init__(self, conversation_id: str = "default"):
        """Initialize the clear history command.
        
        Args:
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.conversation_id = conversation_id


class LLMResponseEvent(Event):
    """Event emitted when the LLM responds."""

    def __init__(
        self, 
        prompt: str, 
        response: LLMResponse, 
        conversation_id: str = "default"
    ):
        """Initialize the LLM response event.
        
        Args:
            prompt: The prompt that was sent
            response: The response from the LLM
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.prompt = prompt
        self.response = response
        self.conversation_id = conversation_id


class ToolCallEvent(Event):
    """Event emitted when a tool is called."""

    def __init__(self, tool_call: ToolCall, conversation_id: str = "default"):
        """Initialize the tool call event.
        
        Args:
            tool_call: The tool call
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.tool_call = tool_call
        self.conversation_id = conversation_id


class ToolResultEvent(Event):
    """Event emitted when a tool execution completes."""

    def __init__(
        self, 
        tool_call: ToolCall, 
        result: Any, 
        error: Optional[str] = None,
        conversation_id: str = "default"
    ):
        """Initialize the tool result event.
        
        Args:
            tool_call: The tool call
            result: The result of the tool execution
            error: Optional error message if the tool execution failed
            conversation_id: The conversation identifier
        """
        super().__init__()
        self.tool_call = tool_call
        self.result = result
        self.error = error
        self.conversation_id = conversation_id