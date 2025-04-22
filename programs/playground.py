#!/usr/bin/env python3
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout import Layout, HSplit, VSplit
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings


def create_width_constrained_prompt(width=30, prompt_text=">>> "):
    """Creates a prompt with constrained width using PromptSession."""

    # Create key bindings
    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("c-q")
    def _(event):
        """Press Ctrl-C or Ctrl-Q to exit."""
        event.app.exit()

    # Create a prompt session with styling
    session = PromptSession(message=prompt_text, multiline=False)

    # Create visual markers to show width constraint
    top_marker = "┌" + "─" * width + "┐"
    bottom_marker = "└" + "─" * width + "┘"

    # Create custom layout with width indicators
    layout = Layout(
        HSplit([
            Window(
                height=1,
                content=FormattedTextControl(
                    HTML(f"<ansiyellow>{top_marker}</ansiyellow>")
                ),
            ),
            # Main window that constrains width
            Window(
                content=FormattedTextControl(HTML("<b>Enter text (width limited):</b>")),
                height=1,
            ),
            # This is where our prompt will go - we prepare the UI for it
            # Real width constraint will be handled by the PromptSession
            Window(
                content=FormattedTextControl(""),
                width=Dimension(preferred=width),
                height=1,
            ),
            Window(
                height=1,
                content=FormattedTextControl(
                    HTML(f"<ansiyellow>{bottom_marker}</ansiyellow>")
                ),
            ),
            Window(height=1, content=FormattedTextControl("Press Ctrl-C to exit")),
        ])
    )

    # Create application to set up terminal state
    app = Application(
        layout=layout, key_bindings=kb, full_screen=False, mouse_support=True
    )

    # Run the application to display the UI frame
    app.run()

    # After the frame is displayed, run the prompt session
    # This effectively gives us a prompt inside our created window
    user_input = session.prompt()

    return user_input


if __name__ == "__main__":
    result = create_width_constrained_prompt(width=30)
    print(f"You entered: {result}")
