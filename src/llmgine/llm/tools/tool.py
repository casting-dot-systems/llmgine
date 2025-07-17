from typing import Any, Dict, List
from pydantic import BaseModel

from llmgine.llm import AsyncOrSyncToolFunction


class Parameter(BaseModel):
    """A parameter for a tool.

    Attributes:
        name: The name of the parameter
        description: A description of the parameter
        type: The type of the parameter
        required: Whether the parameter is required
    """

    name: str
    description: str
    type: str
    required: bool = False

    def __init__(self, name: str, description: str, type: str, required: bool = False):
        self.name = name
        self.description = description or ""
        self.type = type
        self.required = required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "required": self.required,
        }


class Tool(BaseModel):
    """Contains all information about a tool.

    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        parameters: JSON schema for the tool parameters
        function: The function to call when the tool is invoked
        is_async: Whether the function is asynchronous
    """

    name: str
    description: str
    parameters: List[Parameter]
    function: AsyncOrSyncToolFunction
    is_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [param.to_dict() for param in self.parameters],
            "is_async": self.is_async,
        }
