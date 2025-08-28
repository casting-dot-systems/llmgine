import asyncio
import json
from contextlib import AsyncExitStack
from typing import List, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from llmgine.llm import ModelFormattedDictTool, SessionID
from llmgine.llm.tools.mcp.mcp_servers import MCP_SERVERS
from llmgine.llm.tools.mcp.mcp_tool_adapter import ToolAdapter

load_dotenv()


class MCPToolManager:
    def __init__(
        self,
        engine_id: str,
        session_id: SessionID,
        llm_model_name: str = "gpt-4o-mini",
    ):
        # Initialize the MCP tool manager
        self.engine_id: str = engine_id
        self.session_id: SessionID = session_id

        # Initialize the tool adapter based on the LLM model
        self.llm_model_name: str = llm_model_name
        self.tool_adapter: ToolAdapter = ToolAdapter(llm_model_name)

        # Initialize the MCP session
        self.session: Optional[ClientSession] = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect_to_mcp_server(self, servers: list[MCP_SERVERS]):
        """
        Connect to an MCP server running a script at the given path.

        Args:
            server_script_path: The path to the MCP server script. Must end with .py
        """

        for server in servers:
            server_script_path = server.value
            is_python = server_script_path.endswith(".py")

            if not is_python:
                raise ValueError("Server script must be a .py file")

            command = "python"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()

            # List available tools
            response = await self.session.list_tools()
            tools = response.tools

            # print out as json
            print(
                f"\nConnected to server with tools: {json.dumps([(tool.name, tool.title, tool.description, tool.inputSchema, tool.outputSchema, tool.annotations) for tool in tools], indent=4)}"
            )

    async def get_tools(self) -> List[ModelFormattedDictTool]:
        """
        Get the tools from the MCP server.
        """
        if self.session is None:
            raise ValueError("Not connected to an MCP server")
        response = await self.session.list_tools()

        return self.tool_adapter.convert_tools(response)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPToolManager(
        engine_id="test", session_id=SessionID("test"), llm_model_name="gpt-4o-mini"
    )
    try:
        await client.connect_to_mcp_server([MCP_SERVERS.NOTION])
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
