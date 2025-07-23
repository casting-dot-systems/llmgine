"""Commands used in the system.

This module defines commands that can be sent on the message bus.
Commands represent actions to be performed by the system.
"""

import inspect
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from types import FrameType
from typing import Any, Dict, Optional

from llmgine.llm import SessionID


@dataclass
class Command:
    """Base class for all commands in the system.

    Commands represent actions to be performed by the system.
    Each command should be handled by exactly one handler.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: SessionID = field(default_factory=lambda: SessionID("BUS"))
    
    def __post_init__(self) -> None:
        pass



@dataclass
class CommandResult:
    """Result of a command execution."""

    success: bool
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: SessionID = field(default_factory=lambda: SessionID("BUS"))

    def __post_init__(self) -> None:
        # Add metadata about where this command was handled

        tmp: Optional[Any] = inspect.currentframe()
        assert tmp is not None
        frame: FrameType = tmp.f_back

        if frame:
            module = frame.f_globals.get("__name__", "unknown")
            function = frame.f_code.co_name
            line = frame.f_lineno
            self.metadata["finished_in"] = f"{module}.{function}:{line}"
        else:
            self.metadata["finished_in"] = "unknown"
