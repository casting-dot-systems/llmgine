from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
import dataclasses
from typing import Optional, Type
from jinja2 import pass_context
from prompt_toolkit import HTML, PromptSession
from rich.panel import Panel
from rich.console import Console
from rich.box import ROUNDED
from rich import print
from llmgine.bus.bus import MessageBus
from llmgine.messages.commands import Command
from llmgine.messages.events import Event

MAX_WIDTH = 100
PADDING = (1, 2)


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
class UserComponentTestEvent(Event):
    text: str = ""

class UserComponent(CLIComponent):
    """
    Event must have property text.
    """
    def __init__(self, event: Event):
        self.text = event.text

    def render(self):
        print(
            Panel(
                self.text,
                title="[bold blue]User[/bold blue]",
                subtitle_align="right",
                style="blue",
                width=MAX_WIDTH,
                padding=PADDING,
                title_align="left",
            )
        )

    @property
    def serialize(self):
        return {"role": "user", "content": self.text}

@dataclass
class AssistantResultTestEvent(Event):
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
                width=MAX_WIDTH,
                padding=PADDING,
                title_align="left",
            )
        )

@dataclass 
class ToolResultTestEvent(Event):
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
                title=f"[yellow][bold]Tool: [/bold]{self.tool_name}[/yellow]",
                title_align="left",
                style="yellow",
                width=MAX_WIDTH,
                padding=PADDING,
            )
        )

    @property
    def serialize(self):
        return {"role": "tool", "content": self.tool_result}

@dataclass
class GeneralInputTestEvent(Event):
    prompt: str = ""

class GeneralInput(CLIPrompt):
    """
    Command must have property prompt.
    """
    def __init__(self, command: Command):
        self.prompt = command.prompt

    def get_input(self):
        return self.prompt

    def component(self):
        return self.prompt


@dataclass
class YesNoPromptTestEvent(Event):
    prompt: str = ""

class YesNoPrompt(CLIPrompt):
    """
    Command must have property prompt. 
    """

    def __init__(self, command: Command):
        self.session = PromptSession()
        self.prompt = command.prompt
        self.result = None

    async def get_input(self):
        print(
            Panel(
                self.prompt,
                title="[bold yellow]Yes/No Prompt[/bold yellow]",
                subtitle="[yellow]Type your message...[/yellow]",
                title_align="left",
                width=MAX_WIDTH,
                style="yellow",
                padding=PADDING,
            )
        )
        while True:
            user_input = await self.session.prompt_async(
                HTML("  ❯ "),
            )
            if user_input.lower() in ("yes", "y"):
                self.result = True
                return True
            elif user_input.lower() in ("no", "n"):
                self.result = False
                return False
            else:
                Console().print(
                    "[bold red]Invalid input[/bold red]. Please enter 'yes' or 'no'."
                )
                continue

    @property
    def component(self):
        if self.result is None:
            raise ValueError("Result is not set")
        return None


    class EngineCLI:
        def __init__(self, update_status_event: Event):
            self.update_status_event = update_status_event
            self.components = []
            self.component_lookup = {}
            self.prompt_lookup = {}
            self.bus = MessageBus()

        async def component_router(self, event: Event):
            component = self.component_lookup[type(event)]
            component = component(event)
            component.render()
            self.components.append(component)

        async def prompt_router(self, command: Command):
            prompt = self.prompt_lookup[type(command)]
            prompt = prompt(command)
            result = await prompt.prompt()
            self.clear_screen()
            self.render()
            if prompt.component is not None:
                component = prompt.component
                component.render()
                self.components.append(component)

        async def update_status(self, event: Event):
            pass
        
        def register_component_event(self, event: Event, component: Type[CLIComponent]):
            self.component_lookup[type(event)] = component
            self.bus.register_event_handler(event, self.component_router)
        
        def register_prompt_command(self, command: Command, prompt: CLIPrompt):
            self.prompt_lookup[type(command)] = prompt
            self.bus.register_event_handler(command, self.prompt_router)

        def redraw(self):
            self.clear_screen()
            for component in self.components:
                component.render()

        def start(self):
            self.setup()
            self.bus.run()
        
        def stop(self):
            self.bus.stop()

async def main():
    UserComponent(UserComponentTestEvent(text="Hello, world!")).render()
    AssistantComponent(AssistantResultTestEvent(text="Hey there!")).render()
    ToolComponent(ToolResultTestEvent(tool_name="get_weather", result="Tool result")).render()
    prompt = YesNoPrompt(YesNoPromptTestEvent(prompt="Do you want to continue?"))
    result = await prompt.get_input()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())


class BotComponent(CLIComponent):
    def __init__(self):
        self.name = "bot"

    def render(self, input):
        return Panel(input, title=self.name, style="green")


class SystemComponent(CLIComponent):
    def __init__(self):
        self.name = "System"

    def render(self, input):
        return Panel(input, title=self.name, style="yellow")


class CLICommand(ABC):
    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def execute(self):
        pass
