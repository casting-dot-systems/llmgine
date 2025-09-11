"""
TODO:
- Test that the config is loaded correctly
- Test that the config is validated correctly
- Test that the config is used correctly
"""

import pytest
from dataclasses import dataclass
from llmgine.bootstrap import ApplicationConfig


@pytest.mark.asyncio
@dataclass
class Config(ApplicationConfig):
    name: str = "Test"
    description: str = "Test"
    log_level: LogLevel = LogLevel.DEBUG
    enable_console_handler: bool = True
    enable_file_handler: bool = True
    file_handler_log_dir: str = "logs"
    file_handler_log_filename: str = "test.log"


def test_bootstrap():
    TestConfig = ApplicationConfig(
        name="Test",
        description="Test",
        log_level=LogLevel.DEBUG,
        enable_console_handler=True,
        enable_file_handler=True,
        file_handler_log_dir="logs",
        file_handler_log_filename="test.log",
    )
