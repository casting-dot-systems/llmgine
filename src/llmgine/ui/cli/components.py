import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from prompt_toolkit import HTML, PromptSession
from rich import print
from rich.panel import Panel
from rich.prompt import Confirm
from pydantic import Field

from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
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
    def get_input(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def component(self) -> None:
        pass


class UserComponentEvent(Event):
    text: str = Field(default_factory=str)


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


class EngineResultCommandResult(CommandResult):
    result: str = Field(default_factory=str)
    success: bool = Field(default=True)


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


class AssistantResultEvent(Event):
    text: str = Field(default_factory=str)


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


class ToolResultEvent(Event):
    tool_name: str = Field(default_factory=str)
    result: str = Field(default_factory=str)


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


class UserGeneralInputCommand(Command):
    prompt: str = Field(default_factory=str)


class UserGeneralInput(CLIPrompt):
    """
    Command must have property prompt.
    """

    @classmethod
    def from_prompt(cls, prompt: str, cli: Optional["EngineCLI"] = None):
        return cls(UserGeneralInputCommand(prompt=prompt), cli=cli)

    def __init__(self, command: Command, cli: "EngineCLI"):
        self.session: PromptSession = PromptSession()
        self.prompt = command.prompt
        self.result = None
        self.cli = cli

    # TODO types
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


class YesNoPromptCommand(Event):
    prompt: str = Field(default_factory=str)


class YesNoPrompt(CLIPrompt):
    """
    Command must have property prompt.
    """

    def __init__(self, command: EngineResultCommandResult):
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
    def component(self) -> None:
        return None

    def attach_cli(self, cli: "EngineCLI") -> None:
        self.cli = None


class SelectPromptCommand(Command):
    prompt: str = Field(default_factory=str)
    option_number: int = Field(default=0)
    title: str = Field(default_factory=str)


class SelectPrompt(CLIPrompt):
    """
    Command must have property prompt and list.
    """

    def __init__(self, command: Command):
        self.title = command.title
        self.prompt = command.prompt

    async def get_input(self):
        print(
            Panel(
                self.prompt,
                title=f"[bold green]{self.title}[/bold green]",
                subtitle="[green]Input a number...[/green]",
                title_align="left",
                width=CLIConfig().max_width,
                style="green",
                padding=CLIConfig().padding,
            )
        )
        while True:
            user_input = IntPrompt.ask()
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

    EngineResultComponent(EngineResultCommandResult(result="Hello, world!")).render()


if __name__ == "__main__":
    asyncio.run(main())
