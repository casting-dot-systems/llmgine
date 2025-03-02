from abc import ABC
from dataclasses import dataclass
from typing import Dict, Any
from uuid import uuid4


class Command(ABC):
    """Base class for all commands in the system.
    
    Commands represent intentions to change state in the system.
    Each command should be handled by exactly one handler.
    """
    command_id: str
    
    def __post_init__(self):
        if not hasattr(self, 'command_id'):
            self.command_id = str(uuid4())


@dataclass
class CreateResourceCommand(Command):
    """Command to create a new resource in the system."""
    resource_type: str
    resource_data: Dict[str, Any]


@dataclass
class UpdateResourceCommand(Command):
    """Command to update an existing resource in the system."""
    resource_id: str
    resource_type: str
    resource_data: Dict[str, Any]


@dataclass
class DeleteResourceCommand(Command):
    """Command to delete an existing resource in the system."""
    resource_id: str
    resource_type: str

