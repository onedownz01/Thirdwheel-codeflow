"""WebSocket send helper with connection guardrails."""
from __future__ import annotations

from fastapi import WebSocket


class WSEmitter:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def emit(self, message: dict) -> None:
        try:
            await self.websocket.send_json(message)
        except Exception:
            return
