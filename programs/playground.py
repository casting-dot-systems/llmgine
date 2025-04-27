import asyncio
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.panel import Panel
from rich.text import Text

console = Console()


async def main():
    async def loading_panel(message: str) -> Panel:
        spinner = Spinner("dots", text=message)
        return Panel(
            Align.center(spinner, vertical="middle"),
            title="Loading",
            border_style="blue",
            padding=(2, 4),
        )

    # This simulates something loading
    with Live(
        Align.center(Text("Starting...")), refresh_per_second=10, console=console
    ) as live:
        await asyncio.sleep(1)
        live.update(await loading_panel("Connecting to server..."))
        await asyncio.sleep(2)
        live.update(await loading_panel("Fetching data..."))
        await asyncio.sleep(2)
        live.update(await loading_panel("Processing results..."))
        await asyncio.sleep(2)
        live.update(
            Panel(
                Align.center(Text("✅ Done!", style="bold green")), border_style="green"
            )
        )


asyncio.run(main())
