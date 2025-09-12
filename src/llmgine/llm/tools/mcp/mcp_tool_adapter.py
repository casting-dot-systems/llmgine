from typing import Any, List

try:
    from mcp import ListToolsResult  # type: ignore
except Exception:  # pragma: no cover
    ListToolsResult = Any

from llmgine.llm import ModelFormattedDictTool


class ToolAdapter:
    """
    Converts MCP tool listings into function-call schemas usable by engines
    (default: OpenAI-style function tool schema).
    """

    def __init__(self, target_format: str = "openai"):
        self.target_format = (target_format or "openai").lower()

    def convert_tools(self, tools: Any) -> List[ModelFormattedDictTool]:
        items = getattr(tools, "tools", tools)
        result: List[ModelFormattedDictTool] = []
        for t in items:
            name = getattr(t, "name", "")
            description = getattr(t, "description", "") or getattr(t, "title", "") or ""
            input_schema = getattr(t, "inputSchema", {}) or {"type": "object", "properties": {}}
            if self.target_format == "openai":
                result.append(
                    ModelFormattedDictTool(
                        {
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": description,
                                "parameters": input_schema,
                            },
                        }
                    )
                )
            else:
                # default to openai format for unknown targets
                result.append(
                    ModelFormattedDictTool(
                        {
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": description,
                                "parameters": input_schema,
                            },
                        }
                    )
                )
        return result
