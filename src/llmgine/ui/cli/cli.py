import asyncio
import os
import sys
from llmgine.bus.bus import MessageBus
from llmgine.llm.engine.engine import (
    DummyEngineConfirmationInput,
    DummyEngineStatusUpdate,
    DummyEngineToolResult,
)
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from typing import Any, Callable, Type
from dataclasses import dataclass
from llmgine.ui.cli.components import (
    AssistantComponent,
    CLIComponent,
    CLIPrompt,
    EngineResultComponent,
    ToolComponent,
    UserGeneralInput,
    YesNoPrompt,
)


@dataclass
class StatusEvent(Event):
    status: str = ""


class EngineCLI:
    """
    An engine CLI is a CLI that is attached to an engine.
    It needs to register the engine command using register_engine_command.
    It needs to register the engine result component using register_engine_result_component.
    It needs to register the update status event using register_update_status_event.

    It needs to attach the relevant engine events using register_engine_events.
    It needs to register the default CLI commands using register_default_cli_commands.
    It needs to validate the setup using validate_setup.
    It needs to start the main loop using main.
    """

    def __init__(self, session_id: str):
        # Basic UI components
        self.components = []
        self.component_lookup = {}
        self.prompt_lookup = {}
        self.cli_command_lookup = {}
        # Loading UI components
        self.spinner = None
        self.live = None
        self.hidden = False
        # Bus
        self.bus = MessageBus()
        self.session_id = session_id
        # Engine
        self.engine = None
        self.engine_command = None
        self.engine_result_component = EngineResultComponent
        # CLI commands
        self.register_default_cli_commands()

    def register_engine(self, engine: Any):
        self.engine = engine

    def register_engine_command(self, command: Type[Command]):
        self.engine_command = command
        self.bus.register_command_handler(
            command, self.engine.handle_command, self.session_id
        )

    def register_engine_result_component(self, component: Type[CLIComponent]):
        self.engine_result_component = component

    async def main(self):
        self.validate_setup()
        while True:
            user_input = await self.main_input()
            if user_input is None:
                continue

            result = await self.bus.execute(
                self.engine_command(prompt=user_input, session_id=self.session_id)
            )
            if result.success:
                self.components.append(self.engine_result_component(result))
                self.redraw()
            else:
                print(result.error)

    def validate_setup(self):
        if self.engine is None:
            raise ValueError("Engine not attached")
        if self.engine_command is None:
            raise ValueError("Engine command not registered")
        if self.engine_result_component is None:
            raise ValueError("Engine result component not registered")

    async def main_input(self):
        prompt = UserGeneralInput.from_prompt("Do you want to continue?", self)
        result = await prompt.get_input()
        self.clear_screen()
        self.redraw()
        if prompt.component is not None:
            component = prompt.component
            component.render()
            self.components.append(component)
        return result

    async def update_status(self, event: Event):
        if event.status == "finished":
            await self.stop_loading()
        else:
            if not self.spinner:
                self.spinner = Spinner("point", text=f"[bold white]{event.status}")
                self.live = Live(self.spinner, refresh_per_second=10)
                self.live.start()
            else:
                if self.hidden:
                    self.live.start()
                    self.hidden = False
                self.spinner.update(text=f"[bold white]{event.status}")

    async def stop_loading(self):
        if self.live:
            self.live.stop()
            self.redraw()
        self.hidden = True

    async def component_router(self, event: Event):
        component = self.component_lookup[type(event)]
        component = component(event)
        component.render()
        self.components.append(component)

    async def prompt_router(self, command: Command):
        try:
            await self.stop_loading()
            prompt = self.prompt_lookup[type(command)]
            prompt = prompt(command)
            prompt.attach_cli(self)
            result = await prompt.get_input()
            self.clear_screen()
            self.redraw()
            if prompt.component is not None:
                component = prompt.component
                component.render()
                self.components.append(component)
            return CommandResult(success=True, result=result)
        except Exception as e:
            return CommandResult(success=False, error=str(e))

    def register_component_event(self, event: Type[Event], component: Type[CLIComponent]):
        self.component_lookup[event] = component
        self.bus.register_event_handler(event, self.component_router, self.session_id)

    def register_prompt_command(self, command: Type[Command], prompt: CLIPrompt):
        self.prompt_lookup[command] = prompt
        self.bus.register_command_handler(command, self.prompt_router, self.session_id)

    def register_loading_event(self, event: Event):
        self.bus.register_event_handler(event, self.update_status, self.session_id)

    def redraw(self):
        self.clear_screen()
        for component in self.components:
            component.render()

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    # CLI COMMANDS STRUCTURE

    def register_cli_command(self, command: str, func: Callable):
        self.cli_command_lookup[command] = func

    def process_cli_cmds(self, input: str):
        parts = input.split(" ")
        cmd = parts[0]
        if cmd in self.cli_command_lookup:
            self.cli_command_lookup[cmd](self)
            return True
        else:
            return False

    # CLI COMMANDS

    def clear_screen_cmd(self, temp: Any):
        self.clear_screen()

    def exit_cmd(self, temp: Any):
        sys.exit(0)

    def register_default_cli_commands(self):
        self.register_cli_command("clear", self.clear_screen_cmd)
        self.register_cli_command("exit", self.exit_cmd)


async def main():
    from llmgine.llm.engine.engine import DummyEngine, DummyEngineCommand

    engine = DummyEngine("123")
    chat = EngineCLI("123")
    await MessageBus().start()
    chat.register_engine(engine)
    chat.register_engine_command(DummyEngineCommand)
    chat.register_engine_result_component(EngineResultComponent)
    chat.register_loading_event(DummyEngineStatusUpdate)
    chat.register_prompt_command(DummyEngineConfirmationInput, YesNoPrompt)
    chat.register_component_event(DummyEngineToolResult, ToolComponent)
    chat.clear_screen()

    def a_command(cli: Any):
        cli.update_status(DummyEngineStatusUpdate(status="a command"))

    chat.register_cli_command("test", a_command)
    await chat.main()


if __name__ == "__main__":
    asyncio.run(main())
