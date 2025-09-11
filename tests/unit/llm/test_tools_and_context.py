"""Unit tests covering the new SimpleChatHistory and ToolManager behavior."""

import asyncio
import json
from enum import Enum
from typing import Literal

import pytest

from llmgine.llm.context.memory import SimpleChatHistory, Role
from llmgine.llm.tools.toolCall import ToolCall
from llmgine.llm.tools.tool_manager import ToolManager


@pytest.mark.asyncio
async def test_simple_chat_history_flow():
    chat = SimpleChatHistory(engine_id="e", session_id="s", max_messages=10)
    chat.set_system_prompt("You are a helpful assistant.")
    chat.add_user_message("What's the weather in Paris?")

    # Simulate a tool call by the assistant
    tool_call = ToolCall(
        id="call-1", name="get_weather", arguments='{"city":"Paris"}'
    )
    chat.add_assistant_message(content="", tool_calls=[tool_call])

    # And its tool result
    chat.add_tool_message(tool_call_id="call-1", content='{"temp_c":18}')

    msgs = chat.get_messages()
    # Expect: system, user, assistant(with tool_calls), tool
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user" and "Paris" in msgs[1]["content"]
    assert msgs[2]["role"] == "assistant" and "tool_calls" in msgs[2]
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "get_weather"
    assert msgs[3]["role"] == "tool" and msgs[3]["tool_call_id"] == "call-1"


class Color(Enum):
    RED = "red"
    BLUE = "blue"


async def add(x: int, y: float, flag: bool, color: Color = Color.RED) -> str:
    """Adds numbers, echoes bool and enum selection."""
    return f"{x + y}:{flag}:{color.value}"


async def sleepy(delay: float) -> str:
    """Sleeps for given seconds (used to test timeout)."""
    await asyncio.sleep(delay)
    return "done"


@pytest.mark.asyncio
async def test_tool_manager_validation_and_timeout():
    mgr = ToolManager(default_timeout_s=0.05)  # fast timeout for tests
    mgr.register_tool(add)
    mgr.register_tool(sleepy)

    # Coercion & enum handling
    tc_add = ToolCall(
        id="1",
        name="add",
        arguments=json.dumps({"x": "5", "y": "2.5", "flag": "true", "color": "blue"}),
    )
    res = await mgr.execute_tool_call(tc_add)
    assert isinstance(res, str)
    assert "7.5" in res and "True" in res and "blue" in res

    # Schema should include enum for 'color'
    schemas = mgr.tool_schemas
    add_schema = next(s for s in schemas if s["function"]["name"] == "add")
    color_prop = add_schema["function"]["parameters"]["properties"]["color"]
    assert "enum" in color_prop and set(color_prop["enum"]) == {"red", "blue"}

    # Timeout path
    tc_sleep = ToolCall(id="2", name="sleepy", arguments=json.dumps({"delay": 0.2}))
    res2 = await mgr.execute_tool_call(tc_sleep)
    assert isinstance(res2, str) and "timed out" in res2.lower()