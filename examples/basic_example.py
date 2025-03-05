"""
Basic example of using the LLMgine framework
"""

import sys
import os

# Add the src directory to the path so we can import llmgine
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from llmgine import Engine
from llmgine.core.llm import DummyLLMProvider
from llmgine.core.tools import CalculatorTool


def main():
    # Create an engine
    engine = Engine()

    # Register a dummy LLM provider
    engine.llm_router.register_provider(DummyLLMProvider(), is_default=True)

    # Register a calculator tool
    engine.tool_manager.register_tool(CalculatorTool())

    print("LLMgine Basic Example")
    print("---------------------")

    # Generate text with the LLM
    prompt = "Hello, world!"
    print(f"\nGenerating text with prompt: '{prompt}'")
    response = engine.llm_router.generate_text(prompt)
    print(f"Response: {response}")

    # Execute a tool
    print("\nExecuting calculator tool:")
    input_data = {"operation": "add", "args": [1, 2, 3, 4, 5]}
    print(f"Input: {input_data}")
    result = engine.tool_manager.execute_tool("calculator", input_data)
    print(f"Result: {result}")

    # Store and retrieve variables
    print("\nStoring and retrieving variables:")
    engine.context_manager.set_variable("greeting", "Hello, LLMgine!")
    engine.context_manager.set_variable("answer", 42)

    greeting = engine.context_manager.get_variable("greeting")
    answer = engine.context_manager.get_variable("answer")

    print(f"greeting = {greeting}")
    print(f"answer = {answer}")

    # Add chat messages
    print("\nAdding chat messages:")
    engine.context_manager.add_chat_message("user", "What is the meaning of life?")
    engine.context_manager.add_chat_message("assistant", "The meaning of life is 42.")

    chat_history = engine.context_manager.get_chat_history()
    print("Chat history:")
    for message in chat_history:
        print(f"[{message['role']}]: {message['content']}")

    # Subscribe to events
    print("\nSubscribing to events:")

    def event_handler(event_data):
        print(f"Event received: {event_data}")

    engine.message_bus.subscribe_to_event("custom.event", event_handler)

    print("Publishing a custom event...")
    engine.message_bus.publish_event("custom.event", {"message": "Hello from event!"})

    print("\nExample complete!")


if __name__ == "__main__":
    main()
