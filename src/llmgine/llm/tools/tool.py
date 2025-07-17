import asyncio
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from llmgine.llm import AsyncOrSyncToolFunction


class Parameter(BaseModel):
    """A parameter for a tool.

    Attributes:
        name: The name of the parameter
        description: A description of the parameter
        type: The type of the parameter
        required: Whether the parameter is required
    """

    name: str = Field(default_factory=str)
    description: str = Field(default_factory=str)
    type: str = Field(default_factory=str)
    required: bool = Field(default=False)

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
    name: str = Field(default_factory=str)
    description: str = Field(default_factory=str)
    parameters: List[Parameter] = Field(default_factory=list)
    function: Optional[AsyncOrSyncToolFunction] = None
    is_async: bool = Field(default=False)

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [param.to_dict() for param in self.parameters],
            "is_async": self.is_async,
        }
