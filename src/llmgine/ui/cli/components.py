from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import dataclasses
from operator import truediv
from typing import Optional, Type
from prompt_toolkit import HTML, PromptSession
import rich
from rich.panel import Panel
from rich.console import Console
from rich.box import ROUNDED
from rich import print
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from rich.spinner import Spinner
from rich.live import Live
from rich.prompt import Prompt
from rich.prompt import Confirm
from typing import TYPE_CHECKING

from llmgine.ui.cli.config import CLIConfig

if TYPE_CHECKING:
    from llmgine.ui.cli.cli import EngineCLI


class CLIComponent(ABC):
    @abstractmethod
    def render(self):
        pass

    # @abstractmethod
    # def serialize(self):
    #     pass


class CLIPrompt(ABC):
    @abstractmethod
    def get_input(self, *args, **kwargs):
        pass

    @abstractmethod
    def component(self):
        pass


@dataclass
class UserComponentEvent(Event):
    text: str = ""


class UserComponent(CLIComponent):
    """
    Event must have property text.
    """

    def __init__(self, event: Event):
        self.text = event.text

    @classmethod
    def from_text(cls, text: str):
        return cls(UserComponentEvent(text=text))

    def render(self):
        print(
            Panel(
                self.text,
                title="[bold blue]User[/bold blue]",
                subtitle_align="right",
                style="blue",
                width=CLIConfig().max_width,
                padding=CLIConfig().padding,
                title_align="left",
            )
        )

    @property
    def serialize(self):
        return {"role": "user", "content": self.text}


@dataclass
class EngineResultCommandResult(CommandResult):
    result: str = ""
    success: bool = True


class EngineResultComponent(CLIComponent):
    """
    Renders the output of the engine command. Takes in a CommandResult object.
    """

    def __init__(self, result: CommandResult):
        self.result = result.result

    def render(self):
        print(
            Panel(
                self.result,
                title="[bold green]Engine Result[/bold green]",
                style="green",
                width=CLIConfig().max_width,
                padding=CLIConfig().padding,
                title_align="left",
            )
        )


@dataclass
class AssistantResultEvent(Event):
    text: str = ""


class AssistantComponent(CLIComponent):
    """
    Event must have property text.
    """

    def __init__(self, event: Event):
        self.text = event.text

    def render(self):
        print(
            Panel(
                self.text,
                title="[bold green]Assistant[/bold green]",
                style="green",
                width=CLIConfig().max_width,
                padding=CLIConfig().padding,
                title_align="left",
            )
        )


@dataclass
class ToolResultEvent(Event):
    tool_name: str = ""
    result: str = ""


class ToolComponent(CLIComponent):
    """
    Event must have property tool_name and tool_result.
    """

    def __init__(self, event: Event):
        self.tool_name = event.tool_name
        self.tool_result = event.result

    def render(self):
        print(
            Panel(
                self.tool_result,
                title=f"[yellow][bold]:hammer_and_wrench: : {self.tool_name}[/bold][/yellow]",
                title_align="left",
                style="yellow",
                width=CLIConfig().max_width,
                padding=CLIConfig().padding,
            )
        )

    @property
    def serialize(self):
        return {"role": "tool", "content": self.tool_result}


class ToolComponentShort(CLIComponent):
    """
    Event must have property tool_name and tool_result.
    """

    def __init__(self, event: Event):
        self.tool_name = event.tool_name
        self.tool_result = event.result

    def render(self):
        print(
            Panel(
                f"[yellow][bold]:hammer_and_wrench:  Executed tool: {self.tool_name}[/bold][/yellow]",
                style="yellow",
                width=CLIConfig().max_width,
            )
        )


@dataclass
class UserGeneralInputCommand(Command):
    prompt: str = ""


class UserGeneralInput(CLIPrompt):
    """
    Command must have property prompt.
    """

    @classmethod
    def from_prompt(cls, prompt: str, cli: Optional["EngineCLI"] = None):
        return cls(UserGeneralInputCommand(prompt=prompt), cli=cli)

    def __init__(self, command: Command, cli: "EngineCLI"):
        self.session = PromptSession()
        self.prompt = command.prompt
        self.result = None
        self.cli = cli

    async def get_input(self):
        print(
            Panel(
                "",
                title="[bold blue]User[/bold blue]",
                subtitle="[blue]Type your message... [/blue]",
                title_align="left",
                width=CLIConfig().max_width,
                style="blue",
                padding=0,
            )
        )
        while True:
            user_input = await self.session.prompt_async(
                HTML("  ❯ "),
                multiline=True,
                prompt_continuation="  ❯ ",
                vi_mode=CLIConfig().vi_mode,
            )
            if self.cli is not None:
                if self.cli.process_cli_cmds(user_input):
                    return None
            self.result = user_input
            return user_input

    @property
    def component(self):
        if self.result is None:
            return None
        else:
            return UserComponent.from_text(self.result)


@dataclass
class YesNoPromptCommand(Event):
    prompt: str = ""


class YesNoPrompt(CLIPrompt):
    """
    Command must have property prompt.
    """

    def __init__(self, command: Command):
        self.prompt = command.prompt
        self.result = None

    async def get_input(self):
        print(
            Panel(
                self.prompt,
                title="[bold yellow]Prompt[/bold yellow]",
                subtitle="[yellow]Type your message... (y/n)[/yellow]",
                title_align="left",
                width=CLIConfig().max_width,
                style="yellow",
                padding=CLIConfig().padding,
            )
        )
        while True:
            user_input = Confirm.ask()
            return user_input

    @property
    def component(self):
        return None

    def attach_cli(self, cli: "EngineCLI"):
        self.cli = None


async def main():
    # UserComponent(UserComponentEvent(text="Hello, world!")).render()
    # AssistantComponent(AssistantResultEvent(text="Hey there!")).render()
    # ToolComponent(ToolResultEvent(tool_name="get_weather", result="Tool result")).render()
    # prompt = UserGeneralInput(
    #     UserGeneralInputCommand(prompt="Do you want to continue?"), cli=None
    # )
    # result = await prompt.get_input()
    # print(result)

    # EngineResultComponent(EngineResultCommandResult(result="Hello, world!")).render()
    ToolComponentShort(
        ToolResultEvent(tool_name="get_weather", result="Tool result")
    ).render()


if __name__ == "__main__":
    asyncio.run(main())
