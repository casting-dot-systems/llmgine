# LLMgine

LLMgine is a framework for building LLM-powered applications. It provides a modular architecture for integrating language models, tools, and custom logic into applications.

## Architecture

LLMgine follows an event-driven architecture with the following components:

- **Engine**: The central component that orchestrates all other components
- **LLM Router**: Routes requests to appropriate LLM providers
- **Tools**: Reusable functions that can be called by the system
- **Context**: Manages variables, memory, and chat history
- **Message Bus**: Communication backbone with event bus and command bus
- **Observability**: Logging and metrics for monitoring the system
- **User Interface**: Handles user input and output

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llmgine.git
cd llmgine

# Install the package
pip install -e .
```

## Usage

### Basic Usage

```python
from llmgine import Engine, LLMRouter, ToolManager, ContextManager, MessageBus
from llmgine.core.llm import DummyLLMProvider
from llmgine.core.tools import CalculatorTool

# Create an engine
engine = Engine()

# Register an LLM provider
engine.llm_router.register_provider(DummyLLMProvider(), is_default=True)

# Register a tool
engine.tool_manager.register_tool(CalculatorTool())

# Generate text with the LLM
response = engine.llm_router.generate_text("Hello, world!")
print(response)  # Output: Echo: Hello, world!

# Execute a tool
result = engine.tool_manager.execute_tool("calculator", {
    "operation": "add",
    "args": [1, 2, 3]
})
print(result)  # Output: {'result': 6}

# Store and retrieve variables
engine.context_manager.set_variable("greeting", "Hello, LLMgine!")
greeting = engine.context_manager.get_variable("greeting")
print(greeting)  # Output: Hello, LLMgine!
```

### Running the CLI

The package includes a simple command-line interface that demonstrates the framework's capabilities:

```bash
python -m llmgine
```

Available commands in the CLI:

- `calc <operation> <arg1> <arg2> ...`: Perform a calculation (add, subtract, multiply, divide)
- `llm <prompt>`: Send a prompt to the LLM
- `var <name>=<value>`: Set a variable
- `get <name>`: Get a variable value
- `help`: Show help message
- `exit`: Exit the application

### Creating a Custom LLM Provider

You can implement your own LLM provider by extending the `LLMProvider` abstract base class:

```python
from llmgine.core.llm import LLMProvider
from typing import Dict, Any, List

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        # Initialize OpenAI client
        
    def generate_text(self, prompt: str, parameters: Dict[str, Any]) -> str:
        # Call OpenAI API
        # Return the generated text
        
    def get_name(self) -> str:
        return "openai"
        
    def get_supported_models(self) -> List[str]:
        return ["gpt-3.5-turbo", "gpt-4"]
```

### Creating a Custom Tool

You can implement your own tools by extending the `Tool` abstract base class:

```python
from llmgine.core.tools import Tool
from typing import Dict, Any

class WeatherTool(Tool):
    def __init__(self, api_key):
        self.api_key = api_key
        # Initialize weather API client
        
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        location = input_data.get("location")
        # Call weather API
        # Return the weather information
        
    def get_name(self) -> str:
        return "weather"
        
    def get_description(self) -> str:
        return "Gets weather information for a location"
        
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
        
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "conditions": {"type": "string"}
            },
            "required": ["temperature", "conditions"]
        }
```

### Event-Driven Programming

LLMgine uses an event-driven architecture. You can subscribe to events and register command handlers:

```python
# Subscribe to an event
engine.message_bus.subscribe_to_event("llm.response", lambda event_data: print(f"LLM response: {event_data}"))

# Register a command handler
engine.message_bus.register_command_handler("tool.execute", lambda command_data: engine.tool_manager.execute_tool(
    command_data["tool_name"],
    command_data["input_data"]
))

# Publish an event
engine.message_bus.publish_event("custom.event", {"key": "value"})

# Execute a command
result = engine.message_bus.execute_command("tool.execute", {
    "tool_name": "calculator",
    "input_data": {"operation": "add", "args": [1, 2, 3]}
})
```

## Configuration

LLMgine can be configured using a JSON file:

```json
{
    "version": "0.1.0",
    "enable_event_logging": true,
    "log_file": "llmgine.log",
    "database_path": "llmgine.db"
}
```

Pass the configuration file path when running the CLI:

```bash
python -m llmgine --config=config.json
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 