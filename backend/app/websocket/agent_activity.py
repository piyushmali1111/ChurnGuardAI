import json
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import WebSocket, WebSocketDisconnect

class AgentActivityBroadcaster:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(
        self,
        agent: str,
        message: str,
        type_label: str = "info",
        chip: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        timestamp = datetime.now().strftime("%H:%M:%S")
        payload = json.dumps({
            "agent": agent,
            "message": message,
            "timestamp": timestamp,
            "type": type_label,
            "chip": chip,
            "run_id": run_id,
        })
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

broadcaster = AgentActivityBroadcaster()
