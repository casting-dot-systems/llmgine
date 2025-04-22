class CLI:
    def __init__(self):
        self.components = []
        self.bus = MessageBus()

    def clear_console(self):
        for component in self.components:
            component.render()

    def custom_setup(self):
        self.bus.register_command_handler(
            PromptCommand,
            self.handle_prompt,
        )

    def handle_component(self, Event):
        self.components.append(Component(Event.data))

    def handle_prompt(self, Command):
        prompt = CLIPrompt(Command.content)
        result = prompt.prompt_user(self)
        self.clear_console()
        self.append_component(CLIComponent(result))
        self.render()
        return result

    def render(self):
        for component in self.components:
            component.put()

    def append_component(self, component: CLIComponent):
        self.components.append(component)

    def prompt_user(self, prompt: CLIPrompt):
        a
