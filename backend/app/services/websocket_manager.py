from typing import Dict, List, Any
from fastapi import WebSocket
import logging
import json

logger = logging.getLogger("intellitest.ws")


class LiveProctorConnectionManager:
    """
    Manages WebSocket connections for real-time live proctoring console.
    Broadcasts candidate risk level changes, infractions, and camera pings.
    """
    def __init__(self):
        # assessment_id -> List[WebSocket]
        self.active_proctor_connections: Dict[str, List[WebSocket]] = {}

    async def connect_proctor(self, assessment_id: str, websocket: WebSocket):
        await websocket.accept()
        if assessment_id not in self.active_proctor_connections:
            self.active_proctor_connections[assessment_id] = []
        self.active_proctor_connections[assessment_id].append(websocket)
        logger.info(f"Proctor connected to live feed for assessment {assessment_id}")

    def disconnect_proctor(self, assessment_id: str, websocket: WebSocket):
        if assessment_id in self.active_proctor_connections:
            if websocket in self.active_proctor_connections[assessment_id]:
                self.active_proctor_connections[assessment_id].remove(websocket)
            if not self.active_proctor_connections[assessment_id]:
                del self.active_proctor_connections[assessment_id]

    async def broadcast_to_proctors(self, assessment_id: str, message: Dict[str, Any]):
        if assessment_id in self.active_proctor_connections:
            dead_connections = []
            for connection in self.active_proctor_connections[assessment_id]:
                try:
                    await connection.send_text(json.dumps(message, default=str))
                except Exception as e:
                    logger.warning(f"Error broadcasting to proctor ws: {e}")
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect_proctor(assessment_id, dead)


live_proctor_manager = LiveProctorConnectionManager()
