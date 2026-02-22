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
def _check_hia(text):
    try:
        from security.honesty_integrity_accountability import get_hia_framework
        return get_hia_framework().verify_llm_output(text)
    except Exception:
        return None


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
            "connected_at": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat()
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
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "subscribe":
                # Subscribe to additional channel
                new_channel = data.get("channel", channel)
                if new_channel in manager.active_connections:
                    manager.active_connections[new_channel].add(websocket)
                    await manager.send_personal(websocket, {
                        "type": "ack",
                        "data": {"subscribed": new_channel},
                        "timestamp": datetime.now().isoformat()
                    })

            elif msg_type == "unsubscribe":
                # Unsubscribe from channel
                unsub_channel = data.get("channel")
                if unsub_channel and unsub_channel in manager.active_connections:
                    manager.active_connections[unsub_channel].discard(websocket)
                    await manager.send_personal(websocket, {
                        "type": "ack",
                        "data": {"unsubscribed": unsub_channel},
                        "timestamp": datetime.now().isoformat()
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
                        "timestamp": datetime.now().isoformat()
                    })

            elif msg_type == "status":
                # Request current status
                await manager.send_personal(websocket, {
                    "type": "status",
                    "data": manager.get_stats(),
                    "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        })
        return

    try:
        from llm_orchestrator.factory import get_llm_client
        from settings import settings
        
        model_name = settings.LLM_MODEL if settings else "gpt-4o"
        client = get_llm_client()

        if not client.is_running():
            provider_name = settings.LLM_PROVIDER.upper() if settings else "LLM"
            await manager.send_personal(websocket, {
                "type": "error",
                "data": {"error": f"{provider_name} service not responding"},
                "timestamp": datetime.now().isoformat()
            })
            return

        # Stream response
        await manager.send_personal(websocket, {
            "type": "start",
            "data": {"message": "Generating response...", "model": model_name},
            "timestamp": datetime.now().isoformat()
        })

        try:
            full_response = ""
            stream_gen = client.chat(
                messages=[{"role": "user", "content": message}],
                model=model_name,
                stream=True,
                temperature=0.7
            )

            if hasattr(stream_gen, "iter_lines"):
                for line in stream_gen.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith("data: "):
                            data_str = line_text[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                                    token = chunk_json["choices"][0].get("delta", {}).get("content", "")
                                    if token:
                                        full_response += token
                                        await manager.send_personal(websocket, {
                                            "type": "token",
                                            "data": {"token": token},
                                            "timestamp": datetime.now().isoformat()
                                        })
                            except Exception:
                                continue
            else:
                for chunk in stream_gen:
                    if isinstance(chunk, dict) and "message" in chunk:
                        token = chunk["message"].get("content", "")
                        if token:
                            full_response += token
                            await manager.send_personal(websocket, {
                                "type": "token",
                                "data": {"token": token},
                                "timestamp": datetime.now().isoformat()
                            })
                    elif isinstance(chunk, str):
                        full_response += chunk
                        await manager.send_personal(websocket, {
                            "type": "token",
                            "data": {"token": chunk},
                            "timestamp": datetime.now().isoformat()
                        })
                    await asyncio.sleep(0)

            await manager.send_personal(websocket, {
                "type": "complete",
                "data": {
                    "full_response": full_response,
                    "length": len(full_response),
                    "model": model_name
                },
                "timestamp": datetime.now().isoformat()
            })

        except Exception as stream_error:
            # Fallback to non-streaming
            print(f"[WS] Streaming failed, using fallback: {stream_error}")
            response = client.generate(prompt=message, model_id=model_name, stream=False)
            response_text = response if isinstance(response, str) else str(response)
            await manager.send_personal(websocket, {
                "type": "complete",
                "data": {"full_response": response_text, "length": len(response_text)},
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        await manager.send_personal(websocket, {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        })


# =============================================================================
# Broadcast Helper Functions (for use by other modules)
# =============================================================================

async def broadcast_status_update(status: dict):
    """Broadcast a status update to all status channel subscribers."""
    await manager.broadcast("status", {
        "type": "status_update",
        "data": status,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_learning_progress(progress: dict):
    """Broadcast learning progress to learning channel subscribers."""
    await manager.broadcast("learning", {
        "type": "learning_progress",
        "data": progress,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_ingestion_status(status: dict):
    """Broadcast ingestion status to ingestion channel subscribers."""
    await manager.broadcast("ingestion", {
        "type": "ingestion_status",
        "data": status,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_monitoring_data(data: dict):
    """Broadcast monitoring data to monitoring channel subscribers."""
    await manager.broadcast("monitoring", {
        "type": "monitoring_data",
        "data": data,
        "timestamp": datetime.now().isoformat()
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
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "sent",
        "channel": channel,
        "recipients": len(manager.active_connections[channel])
    }
