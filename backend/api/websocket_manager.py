"""
Central WebSocket Manager - Real-time Event Bridge

Provides a single persistent WebSocket connection for the frontend.
Bridges internal subsystem events to the frontend in real-time.

Events pushed to frontend:
- system.health: Periodic health updates
- diagnostic.scan: Diagnostic scan results  
- ingestion.complete: New document ingested
- learning.update: Learning progress
- message_bus.event: Any message bus event
- agent.status: Agent task updates

Classes:
- `ConnectionManager`

Key Methods:
- `disconnect()`
- `get_stats()`
- `get_ws_manager()`
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Set
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Manager"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        self._event_queue: asyncio.Queue = None
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WS-MANAGER] Client connected. Total: {len(self.active_connections)}")

        await websocket.send_json({
            "type": "system.connected",
            "data": {
                "message": "Connected to Grace real-time event stream",
                "timestamp": datetime.now().isoformat(),
                "active_clients": len(self.active_connections),
            },
        })

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        for topic_subs in self.subscriptions.values():
            topic_subs.discard(websocket)

        logger.info(f"[WS-MANAGER] Client disconnected. Total: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, topics: List[str]):
        """Subscribe a connection to specific event topics."""
        for topic in topics:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(websocket)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcast event to all connected clients."""
        if not self.active_connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_topic(self, topic: str, data: Dict[str, Any]):
        """Send event to subscribers of a specific topic."""
        subscribers = self.subscriptions.get(topic, set())
        if not subscribers:
            return

        message = json.dumps({
            "type": topic,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

        disconnected = []
        for connection in subscribers:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "subscriptions": {
                topic: len(subs) for topic, subs in self.subscriptions.items()
            },
        }


manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """Get the global WebSocket manager."""
    return manager


@router.websocket("/ws/events")
async def websocket_event_stream(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time events.
    
    Client can send:
        {"action": "subscribe", "topics": ["diagnostic.scan", "ingestion.complete"]}
        {"action": "unsubscribe", "topics": ["diagnostic.scan"]}
        {"action": "ping"}
    
    Server pushes:
        {"type": "event_type", "data": {...}, "timestamp": "..."}
    """
    await manager.connect(websocket)

    health_task = asyncio.create_task(_periodic_health_push(websocket))

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action", "")

                if action == "subscribe":
                    topics = message.get("topics", [])
                    await manager.subscribe(websocket, topics)
                    await websocket.send_json({
                        "type": "system.subscribed",
                        "data": {"topics": topics},
                    })

                elif action == "unsubscribe":
                    topics = message.get("topics", [])
                    for topic in topics:
                        subs = manager.subscriptions.get(topic, set())
                        subs.discard(websocket)

                elif action == "ping":
                    await websocket.send_json({
                        "type": "system.pong",
                        "data": {"timestamp": datetime.now().isoformat()},
                    })

                elif action == "get_stats":
                    await websocket.send_json({
                        "type": "system.stats",
                        "data": manager.get_stats(),
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "system.error",
                    "data": {"message": "Invalid JSON"},
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        health_task.cancel()
    except Exception as e:
        logger.error(f"[WS-MANAGER] Error: {e}")
        manager.disconnect(websocket)
        health_task.cancel()


async def _periodic_health_push(websocket: WebSocket):
    """Push health updates every 30 seconds."""
    try:
        while True:
            await asyncio.sleep(30)
            try:
                from startup import get_subsystems
                subs = get_subsystems()
                status = subs.get_status()

                await websocket.send_json({
                    "type": "system.health",
                    "data": status,
                })
            except Exception:
                pass
    except asyncio.CancelledError:
        pass
