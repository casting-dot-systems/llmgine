"""
Simple, provider-agnostic context manager for chat history.
Compatible with litellm/pydantic-ai style message lists but has no provider deps.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from llmgine.llm.tools.toolCall import ToolCall


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    role: Role
    content: str
    # Optional extras
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class SimpleChatHistory:
    """
    Minimal, robust chat history with trimming & snapshot/restore.
    - No external dependencies or provider coupling
    - Returns litellm-compatible messages
    """

    def __init__(
        self,
        engine_id: str = "",
        session_id: str = "",
        *,
        max_messages: int = 120,
        max_chars: int = 24_000,
        trim_strategy: str = "drop_oldest",  # 'drop_oldest' | 'drop_middle'
        token_estimator: Optional[Callable[[str], int]] = None,
    ):
        self.engine_id = engine_id
        self.session_id = session_id
        self._system_prompt: Optional[str] = None
        self._messages: List[ChatMessage] = []
        self._max_messages = max_messages
        self._max_chars = max_chars
        self._trim_strategy = trim_strategy
        self._token_estimator = token_estimator

    # ---------------------- public API ----------------------
    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt or ""

    def add_user_message(self, content: str) -> None:
        self._append(ChatMessage(role=Role.USER, content=str(content or "")))

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
    ) -> None:
        self._append(
            ChatMessage(
                role=Role.ASSISTANT,
                content=str(content or ""),
                tool_calls=tool_calls if tool_calls else None,
            )
        )

    def add_tool_message(self, tool_call_id: str, content: str) -> None:
        self._append(
            ChatMessage(
                role=Role.TOOL, content=str(content or ""), tool_call_id=tool_call_id
            )
        )

    def get_messages(self) -> List[Dict[str, Any]]:
        """Return litellm-style messages including the system prompt (if set)."""
        msgs: List[Dict[str, Any]] = []
        if self._system_prompt:
            msgs.append({"role": "system", "content": self._system_prompt})
        for m in self._messages:
            if m.role == Role.ASSISTANT and m.tool_calls:
                msgs.append(
                    {
                        "role": "assistant",
                        "content": m.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": tc.arguments,
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            elif m.role == Role.TOOL:
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id or "",
                        "content": m.content,
                    }
                )
            else:
                msgs.append({"role": m.role.value, "content": m.content})
        return msgs

    def clear(self) -> None:
        """Clear history but keep system prompt."""
        self._messages.clear()

    def reset(self) -> None:
        """Clear everything including system prompt."""
        self._messages.clear()
        self._system_prompt = None

    # -------- back-compat shims used elsewhere in the repo --------
    async def store_assistant_message(self, message_object: Any) -> None:
        content = getattr(message_object, "content", "") or ""
        tool_calls = []
        if hasattr(message_object, "tool_calls") and message_object.tool_calls:
            for tc in message_object.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )
        self.add_assistant_message(content, tool_calls or None)

    async def store_tool_result(self, tool_call_id: str, result: str) -> None:
        self.add_tool_message(tool_call_id, str(result))

    async def retrieve(self) -> List[Dict[str, Any]]:
        return self.get_messages()

    # ---------------------- internals ----------------------
    def _append(self, msg: ChatMessage) -> None:
        self._messages.append(msg)
        self._enforce_limits()

    def _enforce_limits(self) -> None:
        # fast path: message count
        while len(self._messages) > self._max_messages:
            self._trim_once()

        # char budget (approx)
        def _length() -> int:
            total = len(self._system_prompt or "")
            for m in self._messages:
                total += len(m.content or "")
            return total

        while _length() > self._max_chars and self._messages:
            self._trim_once()

    def _trim_once(self) -> None:
        if self._trim_strategy == "drop_middle" and len(self._messages) > 2:
            mid = len(self._messages) // 2
            del self._messages[mid]
        else:
            # default: drop_oldest
            del self._messages[0]

    # Optional: token estimate if caller supplies estimator
    def estimated_tokens(self) -> Optional[int]:
        if not self._token_estimator:
            return None
        text = (self._system_prompt or "") + "\n".join(m.content for m in self._messages)
        return int(self._token_estimator(text))


# Back-compat alias, some code referred to "SimpleMemory"
SimpleMemory = SimpleChatHistory