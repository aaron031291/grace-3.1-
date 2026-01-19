"""
WebSocket API for Real-Time Updates
====================================
Provides real-time bidirectional communication for:
- Live chat streaming
- System status updates
- Learning progress notifications
- File ingestion status
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional, Any
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        # Active connections by channel
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "chat": set(),
            "status": set(),
            "learning": set(),
            "ingestion": set(),
            "monitoring": set(),
        }
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, channel: str = "status"):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = set()

        self.active_connections[channel].add(websocket)
        self.connection_info[websocket] = {
            "channel": channel,
            "connected_at": datetime.utcnow().isoformat(),
            "messages_received": 0,
            "messages_sent": 0
        }

        logger.info(f"[WS] New connection on channel '{channel}'. Total: {len(self.active_connections[channel])}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        info = self.connection_info.pop(websocket, {})
        channel = info.get("channel", "status")

        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

        logger.info(f"[WS] Disconnected from channel '{channel}'")

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
            if websocket in self.connection_info:
                self.connection_info[websocket]["messages_sent"] += 1
        except Exception as e:
            logger.error(f"[WS] Failed to send personal message: {e}")

    async def broadcast(self, channel: str, message: dict):
        """Broadcast a message to all connections on a channel."""
        if channel not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
                if connection in self.connection_info:
                    self.connection_info[connection]["messages_sent"] += 1
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_all(self, message: dict):
        """Broadcast to all channels."""
        for channel in self.active_connections:
            await self.broadcast(channel, message)

    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "channels": {
                channel: len(conns)
                for channel, conns in self.active_connections.items()
            },
            "total_connections": sum(len(c) for c in self.active_connections.values())
        }


# Global connection manager
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, channel: str = "status"):
    """
    Main WebSocket endpoint for real-time communication.

    Channels:
    - status: System status updates
    - chat: Chat message streaming
    - learning: Learning progress updates
    - ingestion: File ingestion status
    - monitoring: System monitoring data

    Message format (incoming):
    {
        "type": "subscribe" | "unsubscribe" | "message" | "ping",
        "channel": "channel_name",
        "data": {...}
    }

    Message format (outgoing):
    {
        "type": "update" | "error" | "pong" | "ack",
        "channel": "channel_name",
        "data": {...},
        "timestamp": "ISO timestamp"
    }
    """
    await manager.connect(websocket, channel)

    try:
        # Send welcome message
        await manager.send_personal(websocket, {
            "type": "connected",
            "channel": channel,
            "data": {"message": f"Connected to {channel} channel"},
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            # Receive message
            data = await websocket.receive_json()

            if websocket in manager.connection_info:
                manager.connection_info[websocket]["messages_received"] += 1

            msg_type = data.get("type", "message")

            if msg_type == "ping":
                # Respond to ping
                await manager.send_personal(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif msg_type == "subscribe":
                # Subscribe to additional channel
                new_channel = data.get("channel", channel)
                if new_channel in manager.active_connections:
                    manager.active_connections[new_channel].add(websocket)
                    await manager.send_personal(websocket, {
                        "type": "ack",
                        "data": {"subscribed": new_channel},
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif msg_type == "unsubscribe":
                # Unsubscribe from channel
                unsub_channel = data.get("channel")
                if unsub_channel and unsub_channel in manager.active_connections:
                    manager.active_connections[unsub_channel].discard(websocket)
                    await manager.send_personal(websocket, {
                        "type": "ack",
                        "data": {"unsubscribed": unsub_channel},
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif msg_type == "message":
                # Handle chat message (for chat channel)
                if channel == "chat":
                    await handle_chat_message(websocket, data.get("data", {}))
                else:
                    # Echo back for other channels
                    await manager.send_personal(websocket, {
                        "type": "ack",
                        "data": data.get("data"),
                        "timestamp": datetime.utcnow().isoformat()
                    })

            elif msg_type == "status":
                # Request current status
                await manager.send_personal(websocket, {
                    "type": "status",
                    "data": manager.get_stats(),
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        manager.disconnect(websocket)


async def handle_chat_message(websocket: WebSocket, data: dict):
    """Handle incoming chat messages and stream responses."""
    message = data.get("message", "")
    chat_id = data.get("chat_id")

    if not message:
        await manager.send_personal(websocket, {
            "type": "error",
            "data": {"error": "No message provided"},
            "timestamp": datetime.utcnow().isoformat()
        })
        return

    try:
        from ollama_client.client import get_ollama_client
        try:
            from settings import settings
            model_name = settings.OLLAMA_LLM_DEFAULT
        except ImportError:
            model_name = "mistral:7b"

        client = get_ollama_client()

        if not client.is_running():
            await manager.send_personal(websocket, {
                "type": "error",
                "data": {"error": "Ollama service not running"},
                "timestamp": datetime.utcnow().isoformat()
            })
            return

        # Stream response
        await manager.send_personal(websocket, {
            "type": "start",
            "data": {"message": "Generating response..."},
            "timestamp": datetime.utcnow().isoformat()
        })

        try:
            stream_response = client.client.chat(
                model=model_name,
                messages=[{"role": "user", "content": message}],
                stream=True,
                options={"temperature": 0.7}
            )

            full_response = ""
            for chunk in stream_response:
                if "message" in chunk and "content" in chunk["message"]:
                    token = chunk["message"]["content"]
                    full_response += token
                    await manager.send_personal(websocket, {
                        "type": "token",
                        "data": {"token": token},
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    await asyncio.sleep(0)

            await manager.send_personal(websocket, {
                "type": "complete",
                "data": {
                    "full_response": full_response,
                    "length": len(full_response)
                },
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as stream_error:
            # Fallback to non-streaming
            response = client.generate(prompt=message, model=model_name, stream=False)
            await manager.send_personal(websocket, {
                "type": "complete",
                "data": {"full_response": response, "length": len(response)},
                "timestamp": datetime.utcnow().isoformat()
            })

    except Exception as e:
        await manager.send_personal(websocket, {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        })


# =============================================================================
# Broadcast Helper Functions (for use by other modules)
# =============================================================================

async def broadcast_status_update(status: dict):
    """Broadcast a status update to all status channel subscribers."""
    await manager.broadcast("status", {
        "type": "status_update",
        "data": status,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_learning_progress(progress: dict):
    """Broadcast learning progress to learning channel subscribers."""
    await manager.broadcast("learning", {
        "type": "learning_progress",
        "data": progress,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_ingestion_status(status: dict):
    """Broadcast ingestion status to ingestion channel subscribers."""
    await manager.broadcast("ingestion", {
        "type": "ingestion_status",
        "data": status,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_monitoring_data(data: dict):
    """Broadcast monitoring data to monitoring channel subscribers."""
    await manager.broadcast("monitoring", {
        "type": "monitoring_data",
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


# =============================================================================
# REST endpoints for WebSocket management
# =============================================================================

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "status": "ok",
        **manager.get_stats()
    }


@router.post("/ws/broadcast/{channel}")
async def broadcast_to_channel(channel: str, message: dict):
    """Broadcast a message to a specific channel (admin endpoint)."""
    if channel not in manager.active_connections:
        return {"error": f"Unknown channel: {channel}"}

    await manager.broadcast(channel, {
        "type": "broadcast",
        "data": message,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "status": "sent",
        "channel": channel,
        "recipients": len(manager.active_connections[channel])
    }
