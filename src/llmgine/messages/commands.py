"""Commands used in the system.

This module defines commands that can be sent on the message bus.
Commands represent actions to be performed by the system.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid
from datetime import datetime


@dataclass
class Command:
    """Base class for all commands in the system.
    
    Commands represent actions to be performed by the system.
    Each command should be handled by exactly one handler.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SampleCommand(Command):
    """Sample command for testing."""
    
    value: str = ""
    

@dataclass
class CommandResult:
    """Result of a command execution."""
    
    success: bool
    original_command: Command = field(default_factory=Command)
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)