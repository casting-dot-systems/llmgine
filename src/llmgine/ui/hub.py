import asyncio
import json
from typing import Set

from starlette.websockets import WebSocket


class UIHub:
    """Simple broadcast hub for UI websockets."""
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)


hub = UIHub()
