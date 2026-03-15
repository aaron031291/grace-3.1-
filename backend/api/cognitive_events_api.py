import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from cognitive.event_bus import subscribe, unsubscribe, get_recent_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cognitive-events", tags=["Cognitive Events API"])

@router.get("/recent")
async def get_recent():
    """Fetch the most recent cognitive and autonomous healing events."""
    events = get_recent_events(limit=100)
    return {"ok": True, "events": events}

@router.websocket("/ws")
async def cognitive_events_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time cognitive and healing events.
    Streams events such as healing.started, healing.completed, and system anomalies.
    """
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    
    # Capture the active event loop to safely dispatch from background threads
    loop = asyncio.get_running_loop()

    def _safe_put(item):
        """Put item in queue, silently dropping if full."""
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass  # Drop event rather than crash the event loop

    def _event_handler(event):
        try:
            out = {
                "topic": getattr(event, "topic", "unknown"),
                "data": getattr(event, "data", {}),
                "source": getattr(event, "source", "system"),
                "timestamp": getattr(event, "timestamp", None)
            }
            loop.call_soon_threadsafe(_safe_put, out)
        except Exception as e:
            logger.error(f"[COGNITIVE-WS] Error handling event: {e}")

    # Subscribe to ALL system and cognitive events
    subscribe("*", _event_handler)
    logger.info("[COGNITIVE-WS] Client connected and subscribed to event_bus.")

    try:
        while True:
            # Wait for event from the queue and push to frontend
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("[COGNITIVE-WS] Client disconnected.")
    except Exception as e:
        logger.error(f"[COGNITIVE-WS] Unexpected WebSocket error: {e}")
    finally:
        unsubscribe("*", _event_handler)
        logger.info("[COGNITIVE-WS] Handler unsubscribed")
