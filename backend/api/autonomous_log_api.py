"""
Autonomous Log Stream API -- WebSocket endpoint for the Live Tail panel.

Streams all event bus events as formatted log lines so the frontend
Tail Logs panel can display coding agent output, stabilisation results,
healing events, and Genesis Key tracking in real-time.

Also provides a REST endpoint for the agent work loop status and
manual stabilisation triggers.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from cognitive.event_bus import subscribe, unsubscribe, get_recent_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autonomous", tags=["Autonomous Log Stream"])


# ── Topic formatting for human-readable log lines ──

_TOPIC_ICONS = {
    "stabilisation.started": "🔧",
    "stabilisation.completed": "✅",
    "stabilisation.listener.registered": "👂",
    "coding_agent.dispatched": "🤖",
    "coding_agent.parallel_dispatch": "⚡",
    "coding_agent.parallel_complete": "📊",
    "coding_agent.kimi.completed": "🧠",
    "coding_agent.opus.completed": "🎭",
    "coding_agent.ollama.completed": "🦙",
    "coding_agent.group_session.started": "📋",
    "coding_agent.group_session.closed": "📝",
    "coding_agent.channel.message": "💬",
    "pipeline.deploy_gate": "🚀",
    "pipeline.code_generated": "💻",
    "coding_agent.hitl.accepted": "✅",
    "coding_agent.hitl.rejected": "❌",
    "coding_agent.hardening.task": "🔩",
    "healing.started": "🩹",
    "healing.completed": "💚",
    "healing.failed": "❌",
    "system.error": "🔴",
    "system.warning": "🟡",
    "system.ok": "🟢",
    "system.health_changed": "📈",
    "genesis.key_created": "🔑",
    "error.unhandled": "💥",
}

_SEVERITY_COLORS = {
    "critical": "\033[31m",  # Red
    "warning": "\033[33m",   # Yellow
    "info": "\033[36m",      # Cyan
    "success": "\033[32m",   # Green
}


def _format_event_as_log(topic: str, data: dict, source: str, timestamp: str = None) -> str:
    """Format a Spindle event as a human-readable log line for the Live Tail."""
    icon = _TOPIC_ICONS.get(topic, "📡")
    ts = timestamp or datetime.now(timezone.utc).strftime("%H:%M:%S")
    if isinstance(ts, str) and "T" in ts:
        try:
            ts = ts.split("T")[1][:8]
        except Exception:
            pass

    # Build the log line based on topic type
    if topic.startswith("coding_agent."):
        agent = data.get("agent", data.get("agents", ""))
        if isinstance(agent, list):
            agent = ", ".join(agent)
        status = data.get("status", data.get("statuses", ""))
        conf = data.get("confidence", data.get("best_confidence", ""))
        file = data.get("file", "")
        task_id = data.get("task_id", "")

        parts = [f"{icon} [{ts}] [AGENT] {topic}"]
        if agent:
            parts.append(f"agent={agent}")
        if status:
            parts.append(f"status={status}")
        if conf:
            parts.append(f"confidence={conf}")
        if file:
            parts.append(f"file={file}")
        if task_id:
            parts.append(f"task={task_id}")
        return " | ".join(parts)

    elif topic.startswith("stabilisation."):
        run_id = data.get("run_id", "")
        completed = data.get("completed", data.get("tasks_completed", ""))
        patches = data.get("patches", data.get("patches_generated", ""))
        duration = data.get("duration_s", "")

        parts = [f"{icon} [{ts}] [STABILISE] {topic}"]
        if run_id:
            parts.append(f"run={run_id}")
        if completed:
            parts.append(f"fixed={completed}")
        if patches:
            parts.append(f"patches={patches}")
        if duration:
            parts.append(f"duration={duration}s")
        return " | ".join(parts)

    elif topic.startswith("pipeline."):
        gate = data.get("gate", "")
        chunk = data.get("chunk", "")
        parts = [f"{icon} [{ts}] [PIPELINE] {topic}"]
        if gate:
            parts.append(f"gate={gate}")
        if chunk:
            parts.append(f"chunk={chunk[:60]}")
        return " | ".join(parts)

    elif topic.startswith("healing."):
        parts = [f"{icon} [{ts}] [HEALING] {topic}"]
        for key in ("component", "error", "status", "remaining_issues"):
            if key in data:
                parts.append(f"{key}={str(data[key])[:80]}")
        return " | ".join(parts)

    elif topic.startswith("genesis."):
        parts = [f"{icon} [{ts}] [GENESIS] {topic}"]
        for key in ("key_type", "what", "who"):
            if key in data:
                parts.append(f"{key}={str(data[key])[:60]}")
        return " | ".join(parts)

    elif topic.startswith("system.") or topic.startswith("error."):
        msg = data.get("message", data.get("error", ""))
        parts = [f"{icon} [{ts}] [{source.upper()}] {topic}"]
        if msg:
            parts.append(str(msg)[:120])
        return " | ".join(parts)

    else:
        # Generic format
        summary = json.dumps(data, default=str)[:150] if data else ""
        return f"{icon} [{ts}] [{source}] {topic} {summary}"


# ── WebSocket: Live Tail log stream ──

@router.websocket("/logs/stream")
async def autonomous_logs_stream(websocket: WebSocket):
    """
    WebSocket endpoint for the Live Tail panel.
    Streams ALL event bus events as formatted log lines.
    
    The frontend ProblemsPanel connects to this at:
      ws://localhost:8000/api/autonomous/logs/stream
    """
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    loop = asyncio.get_running_loop()

    def _safe_put(item):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass

    def _event_handler(event):
        try:
            topic = getattr(event, "topic", "unknown")
            data = getattr(event, "data", {})
            source = getattr(event, "source", "system")
            timestamp = getattr(event, "timestamp", None)

            log_line = _format_event_as_log(topic, data, source, timestamp)
            loop.call_soon_threadsafe(_safe_put, log_line)
        except Exception:
            pass

    # Subscribe to ALL events
    subscribe("*", _event_handler)
    logger.info("[TAIL-WS] Live Tail client connected")

    try:
        # Send recent events as initial backfill
        try:
            recent = get_recent_events(limit=50)
            for evt in reversed(recent):
                line = _format_event_as_log(
                    evt.get("topic", ""), {}, evt.get("source", "system"), evt.get("ts", "")
                )
                await websocket.send_text(line)
        except Exception:
            pass

        await websocket.send_text(f"🟢 [{datetime.now(timezone.utc).strftime('%H:%M:%S')}] [SYSTEM] Live Tail connected -- streaming all events")

        while True:
            data = await queue.get()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        logger.info("[TAIL-WS] Live Tail client disconnected")
    except Exception as e:
        logger.error(f"[TAIL-WS] Error: {e}")
    finally:
        unsubscribe("*", _event_handler)


# ── REST: Agent status & manual trigger ──

@router.get("/status")
async def agent_work_loop_status():
    """Get the current status of the coding agent work loop and pool."""
    result = {"ok": True}

    try:
        from cognitive.coding_agents import get_coding_agent_pool
        pool = get_coding_agent_pool()
        result["agent_pool"] = pool.get_status()
    except Exception as e:
        result["agent_pool"] = {"error": str(e)}

    try:
        from cognitive.agent_work_loop import _listener_active
        result["work_loop_active"] = _listener_active
    except Exception:
        result["work_loop_active"] = False

    return result


@router.post("/stabilise")
async def trigger_stabilisation():
    """Manually trigger a stabilisation run."""
    try:
        import threading
        from cognitive.agent_work_loop import run_stabilisation

        # Run in background thread
        result_holder = {"result": None, "error": None}

        def _run():
            try:
                result_holder["result"] = run_stabilisation(max_tasks=8)
            except Exception as e:
                result_holder["error"] = str(e)

        t = threading.Thread(target=_run, daemon=True, name="manual-stabilise")
        t.start()

        return {
            "ok": True,
            "message": "Stabilisation run started in background",
            "watch": "Check Live Tail for real-time progress",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/genesis-trail")
async def agent_genesis_trail():
    """Get Genesis Keys created by the coding agents (audit trail)."""
    try:
        from cognitive.coding_agents import get_coding_agent_pool
        pool = get_coding_agent_pool()
        summary = pool.ledger.get_summary()
        return {"ok": True, "genesis_trail": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}
