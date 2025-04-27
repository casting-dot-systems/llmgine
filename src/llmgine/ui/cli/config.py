from dataclasses import dataclass


class Singleton:
    """
    A base class that ensures only one instance of a class exists.
    """

    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]


@dataclass
class CLIConfig(Singleton):
    """
    A singleton configuration class for CLI components.

    This class will always return the same instance when instantiated.
    """

    # Add your configuration fields here
    max_width: int = 9999
    padding: tuple = (1, 2)
    vi_mode: bool = True
