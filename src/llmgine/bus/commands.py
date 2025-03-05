from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import uuid
from datetime import datetime


@dataclass
class Command:
    """Base class for all commands in the system"""

    command_type: str
    data: Any
    command_id: str = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.command_id is None:
            self.command_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# LLM commands
class LLMCommand(Command):
    """Base class for LLM-related commands"""

    def __init__(self, command_type: str, data: Any):
        super().__init__(f"llm.{command_type}", data)


class GenerateTextCommand(LLMCommand):
    """Command to generate text using an LLM"""

    def __init__(
        self, prompt: str, model: str = None, parameters: Dict[str, Any] = None
    ):
        super().__init__(
            "generate_text",
            {"prompt": prompt, "model": model, "parameters": parameters or {}},
        )


class CompletionCommand(LLMCommand):
    """Command to get a completion from an LLM"""

    def __init__(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        model: str = None,
    ):
        super().__init__(
            "completion",
            {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "model": model,
            },
        )


# Tool commands
class ToolCommand(Command):
    """Base class for tool-related commands"""

    def __init__(self, command_type: str, data: Any):
        super().__init__(f"tool.{command_type}", data)


class ExecuteToolCommand(ToolCommand):
    """Command to execute a specific tool"""

    def __init__(self, tool_name: str, input_data: Any):
        super().__init__("execute", {"tool_name": tool_name, "input_data": input_data})


class ListToolsCommand(ToolCommand):
    """Command to list available tools"""

    def __init__(self, filter_criteria: Optional[Dict[str, Any]] = None):
        super().__init__("list", {"filter_criteria": filter_criteria or {}})


# State management commands
class StateCommand(Command):
    """Base class for state-related commands"""

    def __init__(self, command_type: str, data: Any):
        super().__init__(f"state.{command_type}", data)


class UpdateVariableCommand(StateCommand):
    """Command to update a variable in state"""

    def __init__(self, variable_name: str, value: Any):
        super().__init__(
            "update_variable", {"variable_name": variable_name, "value": value}
        )


class GetVariableCommand(StateCommand):
    """Command to get a variable from state"""

    def __init__(self, variable_name: str):
        super().__init__("get_variable", {"variable_name": variable_name})


# UI commands
class UICommand(Command):
    """Base class for UI-related commands"""

    def __init__(self, command_type: str, data: Any):
        super().__init__(f"ui.{command_type}", data)


class DisplayCommand(UICommand):
    """Command to display content in the UI"""

    def __init__(self, content: Any, display_type: str = "text"):
        super().__init__("display", {"content": content, "display_type": display_type})


class PromptUserCommand(UICommand):
    """Command to prompt the user for input"""

    def __init__(self, prompt_text: str, options: Optional[List[str]] = None):
        super().__init__("prompt", {"prompt_text": prompt_text, "options": options})
