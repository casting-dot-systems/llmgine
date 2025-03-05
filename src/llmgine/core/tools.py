from typing import Dict, Any, List, Optional, Callable, Union
from abc import ABC, abstractmethod
import uuid
from ..bus.events import ToolExecutionEvent, ToolResultEvent


class Tool(ABC):
    """Abstract base class for tools"""

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute the tool with the given input data"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the tool"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get the description of the tool"""
        pass

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the input data"""
        pass

    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the output data"""
        pass


class ToolManager:
    """Manages tools and their execution"""

    def __init__(self, message_bus=None):
        self.tools: Dict[str, Tool] = {}
        self.message_bus = message_bus

    def register_tool(self, tool: Tool):
        """Register a tool"""
        tool_name = tool.get_name()
        self.tools[tool_name] = tool

    def execute_tool(self, tool_name: str, input_data: Any) -> Any:
        """Execute a tool with the given input data"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered")

        tool = self.tools[tool_name]
        execution_id = str(uuid.uuid4())

        # Emit tool execution event if message bus is available
        if self.message_bus:
            self.message_bus.publish_event(
                "tool.execution",
                ToolExecutionEvent(
                    tool_name=tool_name,
                    input_data=input_data,
                    execution_id=execution_id,
                ),
            )

        try:
            result = tool.execute(input_data)

            # Emit tool result event if message bus is available
            if self.message_bus:
                self.message_bus.publish_event(
                    "tool.result",
                    ToolResultEvent(
                        execution_id=execution_id, tool_name=tool_name, result=result
                    ),
                )

            return result
        except Exception as e:
            # Emit tool error event if message bus is available
            error_message = str(e)
            if self.message_bus:
                self.message_bus.publish_event(
                    "tool.result",
                    ToolResultEvent(
                        execution_id=execution_id,
                        tool_name=tool_name,
                        result=None,
                        error=error_message,
                    ),
                )

            raise

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their metadata"""
        return [
            {
                "name": tool.get_name(),
                "description": tool.get_description(),
                "input_schema": tool.get_input_schema(),
                "output_schema": tool.get_output_schema(),
            }
            for tool in self.tools.values()
        ]

    def get_tool(self, tool_name: str) -> Tool:
        """Get a specific tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered")

        return self.tools[tool_name]


# Example tool implementation
class CalculatorTool(Tool):
    """A simple calculator tool"""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a simple calculation"""
        operation = input_data.get("operation")
        args = input_data.get("args", [])

        if operation == "add":
            result = sum(args)
        elif operation == "multiply":
            result = 1
            for arg in args:
                result *= arg
        elif operation == "subtract":
            if len(args) < 2:
                raise ValueError("Subtract operation requires at least 2 arguments")
            result = args[0]
            for arg in args[1:]:
                result -= arg
        elif operation == "divide":
            if len(args) < 2:
                raise ValueError("Divide operation requires at least 2 arguments")
            result = args[0]
            for arg in args[1:]:
                if arg == 0:
                    raise ValueError("Division by zero")
                result /= arg
        else:
            raise ValueError(f"Unknown operation: {operation}")

        return {"result": result}

    def get_name(self) -> str:
        return "calculator"

    def get_description(self) -> str:
        return "A simple calculator for basic arithmetic operations"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
                "args": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["operation", "args"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"result": {"type": "number"}},
            "required": ["result"],
        }
