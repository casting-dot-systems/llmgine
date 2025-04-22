from abc import ABC, abstractmethod
import asyncio
from typing import Optional
from prompt_toolkit import HTML, PromptSession
from rich.panel import Panel
from rich.console import Console
from rich.box import ROUNDED
from rich import print

MAX_WIDTH = 100
PADDING = (1, 2)


class CLIComponent(ABC):
    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def serialize(self):
        pass


class CLIPrompt(ABC):
    @abstractmethod
    def prompt(self, *args, **kwargs):
        pass


class UserComponent(CLIComponent):
    def __init__(self, text: str, subtitle: Optional[str] = None):
        self.text = text
        self.subtitle = subtitle

    def render(self):
        print(
            Panel(
                self.text,
                title="[bold blue]User[/bold blue]",
                subtitle_align="right",
                subtitle=f"[blue]{self.subtitle}[/blue]",
                style="blue",
                width=MAX_WIDTH,
                padding=PADDING,
                title_align="left",
            )
        )

    @property
    def serialize(self):
        return {"role": "user", "content": self.text}


class AssistantComponent(CLIComponent):
    def __init__(self, text: str, name: str):
        self.text = text
        self.name = name

    def render(self):
        print(
            Panel(
                self.text,
                title=f"[bold green]{self.name}[/bold green]",
                style="green",
                width=MAX_WIDTH,
                padding=PADDING,
                title_align="left",
            )
        )

    @property
    def serialize(self):
        return {"role": "assistant", "content": self.text}


class ToolComponent(CLIComponent):
    def __init__(self, tool_name: str, tool_result: str):
        self.tool_name = tool_name
        self.tool_result = tool_result

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


class YesNoPrompt(CLIPrompt):
    def __init__(self, prompt: Event):
        self.session = PromptSession()
        self.prompt = Event.prompt

    async def prompt(self):
        print(
            Panel(
                self.question,
                title="[bold yellow]Yes/No Prompt[/bold yellow]",
                subtitle="[yellow]Type your message...[/yellow]",
                title_align="left",
                width=MAX_WIDTH,
                style="yellow",
                padding=PADDING,
            )
        )
        user_input = await self.session.prompt_async(
            HTML("  ❯ "),
            multiline=True,
            prompt_continuation=HTML("  ❯ "),
            vi_mode=True,
        )
        if user_input.lower() in ("yes", "y"):
            return True
        elif user_input.lower() in ("no", "n"):
            return False
        else:
            Console().print(
                "[bold red]Invalid input[/bold red]. Please enter 'yes' or 'no'."
            )
            return await self.prompt()


async def main():
    class EngineCLI(CLI):
        def component_router(self, event: CustomEvent1):
            component = componentlookup[type(CustomEvent1)]
            component = component(event)
            component.render()
            self.components.append(component)

        async def prompt_router(self, event: PromptCommand):
            prompt = promptlookup[type(event)]
            prompt = prompt(event)
            result = await prompt.prompt()
            self.clear_screen()
            self.render()
            component = prompt.component()
            component.render()
            self.components.append(component)

        def register_component_event(self, event: Event, component: Type[CLIComponent]):
            self.component_lookup[type(event)] = component

    CLI.register_component_event(CustomEvent1, ComponentRouter)
    register_engine_output
    register_

    UserComponent("Hello, world!", "29:10").render()
    AssistantComponent("Hey there!", "Assistant").render()
    ToolComponent("get_weather", "Tool result").render()
    prompt = YesNoPrompt("Do you want to continue?")
    result = await prompt.prompt()
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
