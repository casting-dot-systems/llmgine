import asyncio
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import HTML, PromptSession
from llmgine.ui.cli.config import CLIConfig
from rich import print

console = Console()


async def main():
    while True:
        print(
            Panel(
                "hello",
                title="[bold yellow]Prompt[/bold yellow]",
                subtitle="[yellow]Type your message... (y/n)[/yellow]",
                title_align="left",
                width=CLIConfig().max_width,
                style="yellow",
                padding=CLIConfig().padding,
            )
        )
        user_input = await PromptSession().prompt_async(
            HTML("  ❯ "),
        )
        print(user_input)


asyncio.run(main())
