import asyncio
from collections import deque
from typing import Any, Deque, Dict

from llmgine.messages.events import Event
from llmgine.observability.manager import ObservabilityHandler

from .hub import hub


def event_to_ui_dict(event: Event) -> Dict[str, Any]:
    # Try .to_dict() if available
    try:
        return {
            **(event.to_dict() if hasattr(event, "to_dict") else {}),
            "event_type": type(event).__name__,
        }
    except Exception:
        # Fallback to __dict__
        base = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
        base["event_type"] = type(event).__name__
        return base


class UIEventBufferHandler(ObservabilityHandler):
    """Observability handler that keeps a ring buffer and streams to the UI."""
    def __init__(self, max_events: int = 1000) -> None:
        self._buffer: Deque[Dict[str, Any]] = deque(maxlen=max_events)

    def handle(self, event: Event) -> None:
        data = event_to_ui_dict(event)
        self._buffer.append(data)
        # Stream asynchronously to connected UIs
        try:
            asyncio.get_running_loop().create_task(hub.broadcast({"type": "event", "data": data}))
        except RuntimeError:
            # No running loop; ignore streaming, buffer still updated
            pass

    def snapshot(self) -> list[Dict[str, Any]]:
        return list(self._buffer)
