from dataclasses import dataclass
from typing import Type, Dict, Any, Self, cast

class Singleton:
    """
    A base class that ensures only one instance of a class exists.
    """

    _instances: Dict[Type['Singleton'], 'Singleton'] = {}

    def __new__(cls: Type[Self], *args: Any, **kwargs: Any) -> Self:
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cast(Self, cls._instances[cls])


@dataclass
class CLIConfig(Singleton):
    """
    A singleton configuration class for CLI components.

    This class will always return the same instance when instantiated.
    """

    # Add your configuration fields here
    max_width: int = 9999

    padding: tuple[int, int] = (1, 2)

    vi_mode: bool = True
