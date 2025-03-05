"""
Main entry point for LLMgine when run directly
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

from .core.engine import Engine
from .core.llm import LLMRouter, DummyLLMProvider
from .core.tools import ToolManager, CalculatorTool
from .ui import ConsoleUI
from .observability import Observability, Logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="LLMgine - A framework for building LLM-powered applications"
    )
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", type=str, help="Path to log file")

    return parser.parse_args()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults"""
    default_config = {
        "version": "0.1.0",
        "enable_event_logging": False,
        "log_file": "llmgine.log",
        "database_path": "llmgine.db",
    }

    if not config_path:
        return default_config

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            # Merge with defaults
            default_config.update(config)
            return default_config
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return default_config


def setup_engine(config: Dict[str, Any]) -> Engine:
    """Set up the engine with all components"""
    # Create engine
    engine = Engine(config=config)

    # Register a dummy LLM provider
    engine.llm_router.register_provider(DummyLLMProvider(), is_default=True)

    # Register a calculator tool
    engine.tool_manager.register_tool(CalculatorTool())

    # Set up an input handler
    def handle_user_input(input_text, metadata):
        if input_text.startswith("calc "):
            # Parse calculation command
            try:
                parts = input_text[5:].strip().split()
                operation = parts[0]
                args = [float(arg) for arg in parts[1:]]

                result = engine.tool_manager.execute_tool(
                    "calculator", {"operation": operation, "args": args}
                )

                engine.message_bus.publish_event(
                    "ui.display",
                    {"content": f"Result: {result['result']}", "type": "text"},
                )
            except Exception as e:
                engine.message_bus.publish_event(
                    "ui.display", {"content": f"Error: {str(e)}", "type": "error"}
                )
        elif input_text.startswith("llm "):
            # Send to LLM
            prompt = input_text[4:].strip()
            response = engine.llm_router.generate_text(prompt)

            engine.message_bus.publish_event(
                "ui.display", {"content": response, "type": "text"}
            )
        elif input_text.startswith("var "):
            # Set variable
            try:
                parts = input_text[4:].strip().split("=", 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()

                engine.context_manager.set_variable(var_name, var_value)

                engine.message_bus.publish_event(
                    "ui.display",
                    {
                        "content": f"Variable '{var_name}' set to '{var_value}'",
                        "type": "text",
                    },
                )
            except Exception as e:
                engine.message_bus.publish_event(
                    "ui.display", {"content": f"Error: {str(e)}", "type": "error"}
                )
        elif input_text.startswith("get "):
            # Get variable
            var_name = input_text[4:].strip()
            var_value = engine.context_manager.get_variable(var_name)

            engine.message_bus.publish_event(
                "ui.display",
                {"content": f"Variable '{var_name}' = '{var_value}'", "type": "text"},
            )
        elif input_text == "help":
            # Show help
            help_text = """
Available commands:
- calc <operation> <arg1> <arg2> ... : Perform a calculation (add, subtract, multiply, divide)
- llm <prompt> : Send a prompt to the LLM
- var <name>=<value> : Set a variable
- get <name> : Get a variable value
- help : Show this help message
- exit : Exit the application
            """
            engine.message_bus.publish_event(
                "ui.display", {"content": help_text, "type": "text"}
            )
        else:
            # Echo back
            engine.message_bus.publish_event(
                "ui.display",
                {
                    "content": f"Unknown command: {input_text}. Type 'help' for available commands.",
                    "type": "text",
                },
            )

    # Subscribe to user input events
    engine.message_bus.subscribe_to_event(
        "ui.input",
        lambda event_data: handle_user_input(
            event_data.get("input_text", ""), event_data.get("metadata", {})
        ),
    )

    return engine


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Set up logging
    if args.debug:
        config["enable_event_logging"] = True

    if args.log_file:
        config["log_file"] = args.log_file

    # Set up observability
    observability = Observability(config=config)
    logger = observability.get_logger("main")

    logger.info("Starting LLMgine")

    try:
        # Set up engine
        engine = setup_engine(config)

        # Set up UI
        ui = ConsoleUI(engine.message_bus)

        # Start the engine
        engine_thread = None
        try:
            import threading

            engine_thread = threading.Thread(target=engine.start)
            engine_thread.daemon = True
            engine_thread.start()

            # Show welcome message
            ui.display("Welcome to LLMgine! Type 'help' for available commands.")

            # Start UI input loop
            ui.start_input_loop()
        finally:
            # Shut down the engine
            engine.shutdown()

            # Wait for engine thread to finish
            if engine_thread and engine_thread.is_alive():
                engine_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info("LLMgine shutdown complete")


if __name__ == "__main__":
    main()
