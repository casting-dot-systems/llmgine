"""This module defines the different events that can be
emitted by the ToolManager.
"""

from typing import Dict, Any, List
from pydantic import Field

from llmgine.messages.events import Event
#from llmgine.llm.tools.types import SessionID

class ToolManagerEvent(Event):
    
    # TODO idk about this
    tool_manager_id: str = Field(default_factory=str)
    engine_id: str = Field(default_factory=str)



class ToolRegisterEvent(ToolManagerEvent):
    tool_info: Dict[str, Any] = Field(default_factory=dict)



class ToolCompiledEvent(ToolManagerEvent):
    tool_compiled_list: List[Dict[str, Any]] = Field(default_factory=list)



class ToolExecuteResultEvent(ToolManagerEvent):
    execution_succeed: bool = False
    tool_info: Dict[str, Any] = Field(default_factory=dict)
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    tool_result: str = ""
