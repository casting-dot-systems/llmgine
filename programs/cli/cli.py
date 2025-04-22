from abc import ABC, abstractmethod
import os
import sys
import json
import asyncio
import threading
from rich.markdown import Markdown
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from rich.spinner import Spinner
from rich import box
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
from time import sleep
import logging
from prompt_toolkit import HTML, prompt
from prompt_toolkit.shortcuts import PromptSession
import aiofiles


logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from llmgine.bus.bus import MessageBus
from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from engines.tool_chat_engine import (
    ToolChatEngine,
    PromptResponseEvent,
    PromptCommand,
    DisplayStatusEvent,
)


async def get_weather():
    """
    A function to get the current weather in Melbourne, Australia.
    """

    return "It is 25 degrees and cloudy in Melbourne."


@dataclass
class CLIConfig(ApplicationConfig):
    """Configuration for the CLI application."""

    # Application-specific configuration
    name: str = "CLI chatbot"
    description: str = "llmgine power in the CLI"

    log_level = logging.ERROR

    enable_tracing: bool = False
    enable_console_handler: bool = False

    # OpenAI configuration
    model: str = "gpt-4o"


class CLIInterface:
    def __init__(
        self,
        chat_storing_path: str = "./programs/cli/chat_history.json",
    ):
        self.debug = False
        load_dotenv()
        self.console = Console()
        self.chat_history = []
        self.chat_storing_path = chat_storing_path
        self._status = None
        self.SYSTEM_PROMPT = """
        You are a friendly AI Personality. 
        """

        # Engine components
        self.bus = MessageBus()
        self.engine = ToolChatEngine(
            session_id="cli_session",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            system_prompt=self.SYSTEM_PROMPT,
            message_bus=self.bus,
        )
        self.prompt_session = PromptSession()

    async def initialize(self):
        await self.bus.start()
        await self.engine.register_tool(get_weather)

        # await self.bus.register_command_handler(
        #     "cli_session",
        #     PromptCommand,
        #     self.handle_confirm_action_command,
        # )

        self.bus.register_event_handler(
            PromptResponseEvent,
            self.handle_response_llm,
            "cli_session",
        )

        self.bus.register_event_handler(
            DisplayStatusEvent,
            self.handle_status_event,
            "cli_session",
        )
        self.bus.register_command_handler(
            PromptCommand,
            self.engine.handle_prompt_command,
            "cli_session",
        )

    async def terminate(self):
        await self.bus.stop()

    # ------ Events and commands handling ------
    async def handle_status_event(self, event: DisplayStatusEvent):
        await self.update_status(event.status)

    async def handle_response_llm(self, event: PromptResponseEvent):
        await self.register_response_llm(event)

    # def handle_confirm_action_command(self, command: PromptCommand):# -> CommandResponse:
    #     prompt = command.message
    #     confirmed = self.get_confirmation(prompt)
    #     # return CommandResponse(...)  # Placeholder for actual response

    # ------ Interface functions ------
    async def clear_console(self):
        if not self.debug:
            os.system("cls" if os.name == "nt" else "clear")

    async def prompt_user(self):
        self.console.print(
            Panel(
                "",
                title=f"[bold green]You[/bold green]",
                subtitle="Type your message...",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        user_input = await self.prompt_session.prompt_async(
            HTML("  ❯ "),
            multiline=True,
            prompt_continuation=HTML("  ❯ "),
            vi_mode=True,
        )

        # Check for exit commands
        if user_input.lower() in ("exit", "quit", "q"):
            self.console.print("\n[bold red]Goodbye![/bold red]")
            self.chat_history.append({"role": "system", "content": "Conversation ended"})
            await self.save_chat_to_json()
            user_input = None

        return user_input

    async def register_response_llm(self, event):
        if event:
            self.chat_history.append({"role": "bot", "content": event.response})
        else:
            print(
                "==================ERROR=========================="
            )  # TODO: implement how to handle errors from llm

    async def get_confirmation(self, prompt: str) -> bool:
        confirmation_panel = Panel(
            f"Do you want to proceed with:\n[bold yellow]{prompt}[/bold yellow]?",
            title="Please Confirm Command",
            style="confirmation",
        )

        self.console.print(confirmation_panel)
        while True:
            response = await self.prompt_session.prompt_async("Confirm (y/n): ")
            response = response.strip().lower()

            if response in ("yes", "no", "y", "n"):
                break
            self.console.print("[red]Please enter 'yes' or 'no'.[/red]")

        await self.clear_console()
        await self.display_chat_history()

        return response.strip().lower() in ("yes", "y")

    async def update_status(self, message: str):
        # if we don't yet have a live spinner, create & start one
        if self._status is None:
            self._status = self.console.status(message, spinner="dots")
            self._status.start()
        # if we already have one, and LLM says "FINISHED", stop it
        elif message == "FINISHED":
            self._status.stop()
            self._status = None
        # otherwise just update the text
        else:
            self._status.update(message)

    async def show_spinner(self):
        with self.console.status("[bold yellow]Waiting for message...", spinner="dots"):
            await asyncio.sleep(5)

    async def display_chat_history(self):
        await self.clear_console()
        for i in range(len(self.chat_history)):
            chat = self.chat_history[i]
            if chat["role"] == "user":
                self.console.print(Panel(chat["content"], title="You", style="user"))
            else:
                self.console.print(
                    Panel(
                        Markdown(chat["content"], justify="left"),
                        title="Darcy",
                        style="darcy",
                    )
                )

    # ------ logs ------
    async def save_chat_to_json(self):
        # Check if the chat history is empty
        if len(self.chat_history) == 0:
            return

        async with aiofiles.open(self.chat_storing_path, "w") as file:
            json_data = json.dumps(self.chat_history, indent=4)
            await file.write(json_data)

    async def run(self):
        self.console.print("[bold magenta]Welcome to the CLI![/bold magenta]\n")

        while True:
            # Display prompt
            user_input = await self.prompt_user()

            if user_input is None:
                break

            # Add user message to chat history
            self.chat_history.append({"role": "user", "content": user_input})

            command = PromptCommand(message=user_input, session_id="cli_session")

            # Process command
            await self.update_status("Processing your message...")
            result = await self.bus.execute(command)
            await self.bus.publish(
                PromptResponseEvent(response=result.result, session_id="cli_session")
            )
            await self.bus.ensure_events_processed()
            await self.update_status("FINISHED")
            await self.display_chat_history()
            # The display_chat_history will be called after the response is received
            # through the event handler


async def main():
    # Bootstrap the application once
    config = CLIConfig()
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()

    interface = CLIInterface()
    await interface.initialize()
    try:
        await interface.run()
    finally:
        await interface.terminate()


if __name__ == "__main__":
    asyncio.run(main())
