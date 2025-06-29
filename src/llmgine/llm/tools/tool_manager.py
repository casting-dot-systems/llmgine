"""Tool management and execution for LLMs.

This module provides a way to register, describe, and execute tools
that can be called by language models.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from llmgine.bus.bus import MessageBus
from llmgine.llm.tools.tool import Tool
from llmgine.llm.tools.tool_events import (
    ToolCompiledEvent,
    ToolExecuteResultEvent,
    ToolRegisterEvent,
)
from llmgine.llm.tools.tool_parser import (
    ClaudeToolParser,
    DeepSeekToolParser,
    OpenAIToolParser,
    ToolParser,
)
from llmgine.llm.tools.tool_register import ToolRegister
from llmgine.llm.tools.types import AsyncOrSyncToolFunction, ToolCall


class ToolManager:
    """Manages tool registration and execution."""

    def __init__(
        self, engine_id: str, session_id: str, llm_model_name: Optional[str] = None
    ):
        """Initialize the tool manager."""
        self.tool_manager_id = str(uuid.uuid4())
        self.engine_id: str = engine_id  # TODO make type
        self.session_id: str = session_id  # TODO amke type
        self.message_bus: MessageBus = MessageBus()
        self.tools: Dict[str, Tool] = {}
        self.__tool_parser: ToolParser = self._get_parser(llm_model_name)
        self.__tool_register: ToolRegister = ToolRegister()

    async def register_tool(self, tool_function: AsyncOrSyncToolFunction) -> None:
        """Register a tool, tool manager will publish the tool
            registration event and hand it to the tool register.

        Args:
            tool: The tool to register
        """

        name: str
        tool: Tool
        name, tool = self.__tool_register.register_tool(tool_function)

        self.tools[name] = tool

        # Publish the tool registration event
        await self.message_bus.publish(
            ToolRegisterEvent(
                tool_manager_id=self.tool_manager_id,
                session_id=self.session_id,
                engine_id=self.engine_id,
                tool_info=tool.to_dict(),
            )
        )

    async def register_tools(self, platform_list: List[str]):
        """Register tools for a specific platform. Completely independent from register_tool.

        Args:
            platform_list: A list of platform names
        """

        # Register tools for each platform
        for name, tool in self.__tool_register.register_tools(platform_list).items():
            self.tools[name] = tool

            # Publish the tool registration event
            await self.message_bus.publish(
                ToolRegisterEvent(
                    tool_manager_id=self.tool_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    tool_info=tool.to_dict(),
                )
            )

    async def get_tools(self) -> List[Tool]:
        """Get all registered tools from the tool register.

        Returns:
            A list of tools in the registered model's format
        """
        # Collect all tools from the tool register
        tools = list(self.tools.values())

        # Publish the tool compilation event
        await self.message_bus.publish(
            ToolCompiledEvent(
                tool_manager_id=self.tool_manager_id,
                session_id=self.session_id,
                engine_id=self.engine_id,
                tool_compiled_list=[tool.to_dict() for tool in tools],
            )
        )

        return [self.__tool_parser.parse_tool(tool) for tool in tools]

    async def execute_tool_call(self, tool_call: ToolCall) -> Optional[dict[str, Any]]:
        """Execute a tool from a ToolCall object.

        Args:
            tool_call: The tool call to execute

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        tool_name = tool_call.name

        try:
            # Parse arguments
            arguments = json.loads(tool_call.arguments)
            return await self.__execute_tool(tool_name, arguments)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON arguments for tool {tool_name}: {e}"
            raise ValueError(error_msg) from e

    async def __execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with the given arguments.

        Args:
            tool_name: The name of the tool to execute
            arguments: The arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        if tool_name not in self.tools:
            error_msg = f"Tool not found: {tool_name}"
            raise ValueError(error_msg)

        tool = self.tools[tool_name]

        try:
            # Call the tool function with the provided arguments
            if tool.is_async:
                result = await tool.function(**arguments)
            else:
                result = tool.function(**arguments)

            # Publish the tool execution event
            await self.message_bus.publish(
                ToolExecuteResultEvent(
                    tool_manager_id=self.tool_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    execution_succeed=True,
                    tool_info=tool.to_dict(),
                    tool_args=arguments,
                    tool_result=str(result),
                )
            )
            return result
        except Exception as e:
            # Publish the tool execution event
            await self.message_bus.publish(
                ToolExecuteResultEvent(
                    tool_manager_id=self.tool_manager_id,
                    session_id=self.session_id,
                    engine_id=self.engine_id,
                    execution_succeed=False,
                    tool_info=tool.to_dict(),
                    tool_args=arguments,
                    tool_result=str(e),
                )
            )

            return f"ERROR: {e!s}"

    def _get_parser(self, llm_model_name: Optional[str] = None) -> ToolParser:
        """Get the appropriate tool parser based on the LLM model name."""
        if llm_model_name == "openai":
            tool_parser: ToolParser = OpenAIToolParser()
        elif llm_model_name == "claude":
            tool_parser = ClaudeToolParser()
        elif llm_model_name == "deepseek":
            tool_parser = DeepSeekToolParser()
        else:
            tool_parser = OpenAIToolParser()
        return tool_parser
