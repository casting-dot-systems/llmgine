import os
from typing import Optional, List
from dotenv import load_dotenv
from rich.console import Console
from loguru import logger
from pydantic import BaseModel

from src.framework.core.engine import ToolEngine
from src.interfaces.cli import ToolCLI
from src.framework.clients import ClientOpenAI
from tools.core.terminal import TerminalOperations
from src.framework.utils import CLIStatusCallback
from tools.pwsh import execute_command
from src.interfaces.cli.observer import CLIObserver
from tools.notion import (
    query_projects_database,
    get_project_tasks,
    get_project_documents,
    read_document,
)

# Configure logging
logger.remove()
logger.add("outputs/logs/function_chat.log", rotation="10 MB", level="INFO")
logger.info("Starting Function Chat")

# Constants
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_SYSTEM_PROMPT_PATH = "prompts/core/agents/function_maker.md"


class FunctionChatConfig(BaseModel):
    """Configuration model for FunctionChat"""

    mode: str
    model_name: str = DEFAULT_MODEL
    system_prompt_path: str = DEFAULT_SYSTEM_PROMPT_PATH
    api_key: Optional[str] = None


class FunctionChat:
    def __init__(self, config: FunctionChatConfig):
        """Initialize FunctionChat with configuration"""
        self.config = config
        self.console = Console()
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key provided and OPENAI_API_KEY not found in environment"
            )

        self.client = ClientOpenAI.create_openai(self.api_key)
        self.terminal = TerminalOperations("./botenv")

        # Initialize CLI interface
        self.cli = self._setup_cli()
        # Initialize engine
        self.engine = self._setup_engine()
        self.engine.subscribe(CLIObserver(self.cli))

    def _setup_cli(self) -> ToolCLI:
        """Set up the CLI interface"""
        menu_text = """
🤖 Function Chat Interface

Available commands:
- exit/quit: Exit the program
- clear: Clear chat history
- help: Show this menu

Type your message to begin...
"""
        return ToolCLI(menu_text=menu_text)

    def _setup_engine(self) -> ToolEngine:
        """Set up the tool engine"""
        # Load system prompt
        try:
            with open(self.config.system_prompt_path, "r", encoding="utf-8") as file:
                system_prompt = file.read()
        except FileNotFoundError:
            logger.warning(
                f"System prompt file not found at {self.config.system_prompt_path}"
            )
            system_prompt = "You are a helpful assistant that uses available tools."

        return ToolEngine(
            client=self.client,
            model_name=self.config.model_name,
            tools=[
                self.terminal.list_directory,
                self.terminal.read_file,
                self.terminal.write_file,
                self.terminal.delete_file,
                self.terminal.create_directory,
                execute_command,
                query_projects_database,
                get_project_tasks,
                get_project_documents,
                read_document,
            ],
            mode=self.config.mode,
            system_prompt=system_prompt,
            confirm=True,
        )

    def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands, return True if handled"""
        if user_input.lower() in ["exit", "quit"]:
            self.cli.print_info("Goodbye! 👋")
            return True
        elif user_input.lower() == "clear":
            self.engine.store.clear()
            self.cli.clear_messages()
            self.cli.print_info("Chat history cleared! 🧹")
            return True
        elif user_input.lower() == "help":
            self.cli.redraw()
            return True
        return False

    def _process_messages(self, count: int, messages: List[dict]):
        """Process and display messages"""
        for i in range(count, len(messages)):
            msg = messages[i]
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    self.cli.add_message(msg.get("content"), "You", "blue")
                elif msg.get("role") == "assistant":
                    self.cli.add_message(msg.get("content"), "Assistant", "green")
                elif msg.get("role") == "tool":
                    self.cli.add_message(
                        msg.get("content")[:500], msg.get("name", "Tool"), "yellow"
                    )

    def run(self):
        """Run the chat interface"""
        try:
            count = 1
            while True:
                try:
                    # Get user input
                    user_input = self.cli.get_input()

                    # Handle special commands
                    if self._handle_special_commands(user_input):
                        if user_input.lower() in ["exit", "quit"]:
                            break
                        continue

                    # Process regular input
                    self.cli.add_message(user_input, "You", "blue")
                    count += 1
                    self.cli.redraw()

                    # Execute the request
                    self.engine.execute(user_input)
                    self.engine.subject.notify(
                        {"type": "status_update", "message": "done"}
                    )
                    # Process new messages
                    messages = self.engine.store.retrieve()
                    self._process_messages(count, messages)
                    count = len(messages)

                    self.cli.redraw()

                except KeyboardInterrupt:
                    if (
                        self.cli.get_input("Do you want to exit? (y/n): ").lower()
                        == "y"
                    ):
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error in chat loop: {str(e)}")
                    self.cli.print_error(f"Error: {str(e)}")
                    self.cli.print_info(
                        "You can continue chatting or type 'exit' to quit."
                    )

        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            self.cli.print_error(f"Fatal error: {str(e)}")
        finally:
            logger.info("Shutting down Function Chat")


def main(mode: str = "normal", model_name: str = DEFAULT_MODEL):
    """Main entry point for the function chat"""
    try:
        load_dotenv()

        config = FunctionChatConfig(mode=mode, model_name=model_name)

        chat = FunctionChat(config)
        chat.run()

    except Exception as e:
        Console().print(f"[red]Error starting Function Chat: {str(e)}[/red]")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    sys.exit(main(mode=mode))
