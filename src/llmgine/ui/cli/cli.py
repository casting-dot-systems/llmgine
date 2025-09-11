import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type

from rich.live import Live
from rich.spinner import Spinner

from llmgine.bus.bus import MessageBus
from llmgine.bus.interfaces import AsyncCommandHandler
from llmgine.llm import SessionID
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.ui.cli.components import (
    CLIComponent,
    CLIPrompt,
    EngineResultComponent,
    UserComponent,
    UserGeneralInput,
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

    def __init__(self, session_id: SessionID):
        # Basic UI components
        self.components: list[UserComponent] = []
        self.component_lookup: dict[Any, Any] = {}
        self.prompt_lookup: dict[Any, Any] = {}
        self.cli_command_lookup: dict[Any, Any] = {}  # TODO what is this type?
        # Loading UI components
        self.spinner: Optional[Spinner] = None
        self.live: Optional[Live] = None
        self.hidden: bool = False
        # Bus
        self.bus: MessageBus = MessageBus()
        self.session_id: SessionID = session_id
        # Engine
        self.engine: Optional[Any] = None  # TODO rm any
        self.engine_command: Optional[Any] = None  # TODO rm any
        self.engine_result_component: Any = EngineResultComponent
        # CLI commands
        self.register_default_cli_commands()

    def register_engine(self, engine: Any):  # TODO nathan idk what this is
        self.engine = engine

    def register_engine_command(
        self, command: Type[Command], engine_function: AsyncCommandHandler
    ):
        self.engine_command = command
        self.bus.register_command_handler(command, engine_function, self.session_id)

    def register_engine_result_component(self, component: Type[CLIComponent]):
        self.engine_result_component = component

    async def main(self):
        self.validate_setup()
        while True:
            user_input = await self.main_input()  # TODO what type is this
            if user_input is None:
                continue

            assert self.engine_command

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
        prompt: UserGeneralInput = UserGeneralInput.from_prompt(
            "Do you want to continue?", self
        )
        result = await prompt.get_input()  # TODO what type is this
        self.clear_screen()
        self.redraw()
        if prompt.component is not None:
            component: UserComponent = prompt.component
            component.render()
            self.components.append(component)

        return result

    async def update_status(self, event: StatusEvent):
        if event.status == "finished":  # TODO event doesn't have status?
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

    async def prompt_router(self, command: Command) -> CommandResult:
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

    def register_component_event(
        self, event: Type[Event], component: Type[CLIComponent]
    ) -> None:
        self.component_lookup[event] = component
        self.bus.register_event_handler(event, self.component_router, self.session_id)

    def register_prompt_command(self, command: Type[Command], prompt: CLIPrompt) -> None:
        self.prompt_lookup[command] = prompt
        self.bus.register_command_handler(command, self.prompt_router, self.session_id)

    def register_loading_event(self, event: type[Event]) -> None:
        self.bus.register_event_handler(event, self.update_status, self.session_id)

    def redraw(self) -> None:
        self.clear_screen()
        for component in self.components:
            component.render()

    def clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    # CLI COMMANDS STRUCTURE

    def register_cli_command(self, command: str, func: Callable) -> None:
        self.cli_command_lookup[command] = func

    def process_cli_cmds(self, input: str):
        parts = input.split(" ")
        cmd = parts[0]
        if cmd in self.cli_command_lookup:
            self.cli_command_lookup[cmd]()
            return True
        else:
            return False

    # CLI COMMANDS

    def clear_screen_cmd(self):
        self.clear_screen()

    def exit_cmd(self):
        sys.exit(0)

    def register_default_cli_commands(self):
        self.register_cli_command("clear", self.clear_screen_cmd)
        self.register_cli_command("exit", self.exit_cmd)


# Note: Demo/main removed. Engines can register themselves with EngineCLI from their own entrypoints.
