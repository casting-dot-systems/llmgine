# Engine Guide

An engine file is split into 3 (or 4) sections:

1. Engine commands
2. Engine class
3. CLI
4 (optional). Engine function

## Engine commands

### CustomEngineCommand

Each engine must have a command that takes in your prompt. 

```python
class CustomEngineCommand(Command):
    prompt: str = ""
    (and any other arguments you need)
```

This command will be used as the entry into your engine. 

### CustomEngineStatusEvent

Each engine must have a status event that is emitted when the engine is started.

```python
class CustomEngineStatusEvent(Event):
    status: str = ""
```

This event will be used to update the status of the engine. This is the loading bar you see in the CLI.

### PromptCommand

A prompt command is a command that gets a prompt from the user. Checkout the prompts class in the CLI for more information. 

```python
class PromptCommand(Command):
    prompt: str = ""
```

There are two defined prompt components, the simple yes or no or the full text prompt. They are in cli.components.py.

### Other Commands and Events

You can add other commands and events to your engine as needed. They will be registered to different components or prompts in the CLI. 

## Engine class

The engine class is where you define your engine. **The custom engine class must inherit from the Engine class in llm.engine.engine**

The entry into your engine is the handle_command function. Which takes in your CustomEngineCommand and returns a CommandResult. See the CommandResult class in the bus.commands module for more information. 

```python
async def handle_command(self, command: CustomEngineCommand) -> CommandResult:
    pass
```

The core logic of your engine should be in the execute function. 

```python
async def execute(self, prompt: str) -> str:
    pass
```

So your handle_command function will look like this:

```python
async def handle_command(self, command: CustomEngineCommand) -> CommandResult:
    try:
        result = await self.execute(command.prompt)
        return CommandResult(success=True, result=result)
    except Exception as e:
        return CommandResult(success=False, error=str(e))
```

Inside your execute function and your init is where all your custom logic will go.

## CLI

The CLI is defined in the cli.py file. It is a class that is responsible for handling the CLI. It is initialized with your engine and the model you want to use. 

The CLI class is callled 'EngineCLI' and is initialized with your engine's session id.

```python
cli = EngineCLI(session_id)
```

At the bare minimum, you need to register a couple of things for the cli to work.

```python
cli.register_engine(engine) # register the engine
cli.register_engine_command(CustomEngineCommand, engine.handle_command) # register the command to the engine input
cli.register_engine_result_component(EngineResultComponent) # register the result component to the engine output
cli.register_loading_event(CustomEngineStatusEvent) # register the loading event to the engine status
```

From there you can just do:

```python
await cli.main()
```

A full example of an engine looks like this:

```python
    from llmgine.ui.cli.cli import EngineCLI
    from llmgine.ui.cli.components import EngineResultComponent
    from llmgine.bootstrap import ApplicationConfig, ApplicationBootstrap
    from llmgine.llm.models.openai_models import Gpt41Mini
    from llmgine.llm.providers.providers import Providers

    config = ApplicationConfig(enable_console_handler=False)
    bootstrap = ApplicationBootstrap(config)
    await bootstrap.bootstrap()
    engine = SinglePassEngine(
        Gpt41Mini(Providers.OPENAI), "respond in pirate", "test"
    )
    cli = EngineCLI("test")
    cli.register_engine(engine)
    cli.register_engine_command(SinglePassEngineCommand, engine.handle_command)
    cli.register_engine_result_component(EngineResultComponent)
    cli.register_loading_event(SinglePassEngineStatusEvent)
    await cli.main()
```

You would write your cli inside of the engine file under main(), so then you can do if __name__ == "__main__": and run the engine directly.

See single_pass_engine.py for a full example.

###  Engine function

There's an additional step which is to make the engine usable through a single function.

```python
async def custom_engine(prompt: str) -> str:
    pass
```

This would be a function that takes in some value and the sets everything up, executes it and returns the result. 

To test this we put the condition case in the main() function, and we have a case for cli and also a case for the engine function. 

Check single_pass_engine.py for an example.