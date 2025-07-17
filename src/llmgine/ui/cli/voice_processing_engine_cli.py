from typing import Optional
from pydantic import Field
from prompt_toolkit import PromptSession
from rich.panel import Panel
from rich import print
from prompt_toolkit import HTML, PromptSession

from llmgine.llm import SessionID
from llmgine.messages.commands import Command
from llmgine.ui.cli.cli import EngineCLI
from llmgine.ui.cli.components import CLIPrompt, CLIComponent
from llmgine.ui.cli.config import CLIConfig
from llmgine.messages.events import Event

class SpecificComponentEvent(Event):
    text: str = Field(default_factory=str)
    field: str = Field(default_factory=str)

class SpecificComponent(CLIComponent):
    """
    Event must have property text.
    """

    def __init__(self, event: SpecificComponentEvent):
        self.text : str = event.text
        self.field : str = event.field

    @classmethod
    def from_text(cls, text: str, field: str):
        return cls(SpecificComponentEvent(text=text, field=field))

    def render(self):
        print(
            Panel(
                self.text,
                title="[bold yellow]" + self.field + "[/bold yellow]",
                subtitle_align="right",
                style="yellow",
                width=CLIConfig().max_width,
                padding=CLIConfig().padding,
                title_align="left",
            )
        )

    @property
    def serialize(self):
        return {"role": "user", "content": self.field + ": " + self.text}

class SpecificPromptCommand(Command):
    prompt: str = Field(default_factory=str)
    field: str = Field(default_factory=str)

# Custom user prompt
class SpecificPrompt(CLIPrompt):
    """
    Command must have property prompt.
    """

    @classmethod
    def from_prompt(cls, prompt: str, cli: Optional["EngineCLI"] = None, field: str = ""):
        return cls(SpecificPromptCommand(prompt=prompt, field=field), cli=cli)

    def __init__(self, command: SpecificPromptCommand, cli: "EngineCLI"):
        self.session = PromptSession()
        self.prompt : str = command.prompt
        self.result : Optional[str] = None
        self.cli = cli
        self.field : str= command.field

    async def get_input(self):
        print(
            Panel(
                "",
                title="[bold yellow]" + self.field + "[/bold yellow]",
                subtitle="[yellow]Please enter the " + self.field + "[/yellow]",
                title_align="left",
                width=CLIConfig().max_width,
                style="yellow",
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
            return SpecificComponent.from_text(self.result, self.field)

# ----------------------------------CUSTOM ENGINE CLI-----------------------------------

class VoiceProcessingEngineCLI(EngineCLI):
    def __init__(self, session_id: SessionID):
        super().__init__(session_id)

    async def main(self):
        self.validate_setup()
        while True:
            audio_file = await self.main_input("Audio file")
            if audio_file is None:
                continue

            number_of_speakers = await self.main_input("Number of speakers")
            if number_of_speakers is None:
                continue

            result = await self.bus.execute(
                self.engine_command(prompt=audio_file + "&" + number_of_speakers, session_id=self.session_id)
            )
            if result.success:
                self.components.append(self.engine_result_component(result))
                self.redraw()
            else:
                print(result.error)

    async def main_input(self, field: Optional[str] = None) -> Optional[str]:
        if field is None:
            prompt = SpecificPrompt.from_prompt("Do you want to continue?", self)
        else:
            prompt = SpecificPrompt.from_prompt("Do you want to continue?", self, field)

        result = await prompt.get_input()
        self.clear_screen()
        self.redraw()
        if prompt.component is not None:
            component = prompt.component
            component.render()
            self.components.append(component)
        return result
