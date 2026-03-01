"""
Brain API — Domain-based monolith endpoints.

Instead of 678 flat routes, Grace exposes ~8 domain "brains".
Each brain is ONE POST endpoint with action-based routing.

  POST /brain/chat      { action: "send", payload: { message: "hello" } }
  POST /brain/files     { action: "browse", payload: { path: "/" } }
  POST /brain/govern    { action: "approvals", payload: { limit: 10 } }

Benefits:
  - 1 endpoint per domain = fewer auth checks, CORS, rate-limit rules
  - Internal imports are wiring — brain knows its own turf
  - Swap out a subsystem, no client breakage
  - Probe agent checks 8 brains instead of 678 routes
  - Genesis key tracks at the brain+action level

Each brain is kept small (5-15 actions max).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, Dict
from datetime import datetime
import logging
import json
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brain", tags=["Brain API"])


class BrainRequest(BaseModel):
    action: str
    payload: Optional[Dict[str, Any]] = {}


class BrainResponse(BaseModel):
    brain: str
    action: str
    ok: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0
    genesis_key_id: Optional[str] = None


def _brain_call(brain: str, action: str, payload: dict, handler_map: dict) -> BrainResponse:
    """Route an action to its handler, track via Genesis, return clean response."""
    start = time.time()

    handler = handler_map.get(action)
    if not handler:
        available = ", ".join(sorted(handler_map.keys()))
        return BrainResponse(
            brain=brain, action=action, ok=False,
            error=f"Unknown action '{action}'. Available: {available}",
        )

    try:
        data = handler(payload)
        latency = round((time.time() - start) * 1000, 1)

        gk_id = None
        try:
            from api._genesis_tracker import track
            gk_id = track(
                key_type="api_request",
                what=f"brain/{brain}/{action}",
                who=f"brain_api.{brain}",
                how=action,
                input_data={"action": action, "payload_keys": list(payload.keys()) if payload else []},
                output_data={"ok": True, "latency_ms": latency},
                tags=["brain", brain, action],
            )
        except Exception:
            pass

        return BrainResponse(
            brain=brain, action=action, ok=True,
            data=data, latency_ms=latency, genesis_key_id=gk_id,
        )
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        logger.error(f"brain/{brain}/{action} failed: {e}")

        try:
            from api._genesis_tracker import track
            track(
                key_type="error", what=f"brain/{brain}/{action} failed: {e}",
                who=f"brain_api.{brain}", is_error=True,
                error_type=type(e).__name__, error_message=str(e)[:200],
                tags=["brain", brain, action, "error"],
            )
        except Exception:
            pass

        return BrainResponse(
            brain=brain, action=action, ok=False,
            error=str(e)[:300], latency_ms=latency,
        )


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: CHAT — conversations, prompts, world model
# ═══════════════════════════════════════════════════════════════════

def _chat_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"

    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}: {r.text[:200]}"}

    return {
        "list":    lambda p: _j(req.get(f"{B}/chats", params={"limit": p.get("limit", 50)}, timeout=10)),
        "create":  lambda p: _j(req.post(f"{B}/chats", json=p, timeout=10)),
        "get":     lambda p: _j(req.get(f"{B}/chats/{p['chat_id']}", timeout=10)),
        "delete":  lambda p: _j(req.delete(f"{B}/chats/{p['chat_id']}", timeout=10)),
        "send":    lambda p: _j(req.post(f"{B}/chats/{p['chat_id']}/prompt", json={"content": p["message"]}, timeout=120)),
        "history": lambda p: _j(req.get(f"{B}/chats/{p['chat_id']}/messages", timeout=10)),
        "consensus": lambda p: _j(req.post(f"{B}/api/consensus/fast", json={"prompt": p["message"], "models": p.get("models")}, timeout=60)),
        "world_model": lambda p: _j(req.get(f"{B}/api/world-model/state", timeout=10)),
    }

@router.post("/chat", response_model=BrainResponse)
async def brain_chat(req: BrainRequest):
    return _brain_call("chat", req.action, req.payload or {}, _chat_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: FILES — folders, documents, uploads, librarian
# ═══════════════════════════════════════════════════════════════════

def _files_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "tree":     lambda p: _j(req.get(f"{B}/api/librarian-fs/tree", params=p, timeout=10)),
        "browse":   lambda p: _j(req.get(f"{B}/api/librarian-fs/browse", params={"path": p.get("path", "")}, timeout=10)),
        "read":     lambda p: _j(req.get(f"{B}/api/librarian-fs/file/content", params={"path": p["path"]}, timeout=10)),
        "write":    lambda p: _j(req.put(f"{B}/api/librarian-fs/file/content", json=p, timeout=10)),
        "create":   lambda p: _j(req.post(f"{B}/api/librarian-fs/file/create", json=p, timeout=10)),
        "delete":   lambda p: _j(req.delete(f"{B}/api/librarian-fs/file", params={"path": p["path"]}, timeout=10)),
        "search":   lambda p: _j(req.post(f"{B}/retrieve/search", params={"query": p["query"]}, timeout=15)),
        "docs_all": lambda p: _j(req.get(f"{B}/api/docs/all", timeout=10)),
        "stats":    lambda p: _j(req.get(f"{B}/api/librarian-fs/stats", timeout=10)),
    }

@router.post("/files", response_model=BrainResponse)
async def brain_files(req: BrainRequest):
    return _brain_call("files", req.action, req.payload or {}, _files_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: GOVERN — governance, approvals, rules, persona, genesis
# ═══════════════════════════════════════════════════════════════════

def _govern_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "dashboard":  lambda p: _j(req.get(f"{B}/api/governance-hub/dashboard", timeout=10)),
        "approvals":  lambda p: _j(req.get(f"{B}/api/governance-hub/approvals", timeout=10)),
        "approve":    lambda p: _j(req.post(f"{B}/api/governance-hub/approvals/{p['id']}", json=p, timeout=10)),
        "scores":     lambda p: _j(req.get(f"{B}/api/governance-hub/scores", timeout=10)),
        "rules":      lambda p: _j(req.get(f"{B}/api/governance-rules/documents", timeout=10)),
        "persona":    lambda p: _j(req.get(f"{B}/api/governance-rules/persona", timeout=10)),
        "genesis_stats": lambda p: _j(req.get(f"{B}/genesis/stats", timeout=10)),
        "heal":       lambda p: _j(req.post(f"{B}/api/governance-hub/healing/trigger", timeout=30)),
        "learn":      lambda p: _j(req.post(f"{B}/api/governance-hub/learning/trigger", timeout=30)),
    }

@router.post("/govern", response_model=BrainResponse)
async def brain_govern(req: BrainRequest):
    return _brain_call("govern", req.action, req.payload or {}, _govern_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: AI — consensus, models, coding agent, oracle
# ═══════════════════════════════════════════════════════════════════

def _ai_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "models":     lambda p: _j(req.get(f"{B}/api/consensus/models", timeout=15)),
        "consensus":  lambda p: _j(req.post(f"{B}/api/consensus/run", json=p, timeout=120)),
        "quick":      lambda p: _j(req.post(f"{B}/api/consensus/quick", json=p, timeout=60)),
        "fast":       lambda p: _j(req.post(f"{B}/api/consensus/fast", json=p, timeout=60)),
        "generate":   lambda p: _j(req.post(f"{B}/api/coding-agent/generate", json=p, timeout=60)),
        "oracle":     lambda p: _j(req.get(f"{B}/api/oracle/dashboard", timeout=10)),
        "training":   lambda p: _j(req.get(f"{B}/api/oracle/training-data", timeout=10)),
        "console":    lambda p: _j(req.post(f"{B}/api/console/ask", json=p, timeout=60)),
    }

@router.post("/ai", response_model=BrainResponse)
async def brain_ai(req: BrainRequest):
    return _brain_call("ai", req.action, req.payload or {}, _ai_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: SYSTEM — health, diagnostics, runtime, triggers, probe
# ═══════════════════════════════════════════════════════════════════

def _system_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "health":       lambda p: _j(req.get(f"{B}/api/system-health/dashboard", timeout=10)),
        "runtime":      lambda p: _j(req.get(f"{B}/api/runtime/status", timeout=5)),
        "connectivity": lambda p: _j(req.get(f"{B}/api/runtime/connectivity", timeout=10)),
        "hot_reload":   lambda p: _j(req.post(f"{B}/api/runtime/hot-reload", timeout=15)),
        "pause":        lambda p: _j(req.post(f"{B}/api/runtime/pause", timeout=5)),
        "resume":       lambda p: _j(req.post(f"{B}/api/runtime/resume", timeout=5)),
        "triggers":     lambda p: _j(req.get(f"{B}/api/triggers/scan", timeout=15)),
        "scan_heal":    lambda p: _j(req.post(f"{B}/api/triggers/scan-and-heal", timeout=30)),
        "probe":        lambda p: _j(req.post(f"{B}/api/probe/sweep", timeout=60)),
        "probe_models": lambda p: _j(req.post(f"{B}/api/probe/sweep-models", timeout=60)),
        "fix_all":      lambda p: _j(req.post(f"{B}/api/consensus-fix/fix-all", timeout=120)),
        "health_map":   lambda p: _j(req.get(f"{B}/api/component-health/map", params=p, timeout=10)),
        "problems":     lambda p: _j(req.get(f"{B}/api/component-health/problems", timeout=10)),
        "baselines":    lambda p: _j(req.get(f"{B}/api/component-health/learned-baselines", timeout=15)),
        "orphans":      lambda p: _j(req.get(f"{B}/api/component-health/orphans", timeout=10)),
        "diagnostics":  lambda p: _j(req.get(f"{B}/api/audit/diagnostics/status", timeout=10)),
        "bi":           lambda p: _j(req.get(f"{B}/api/bi/dashboard", timeout=10)),
    }

@router.post("/system", response_model=BrainResponse)
async def brain_system(req: BrainRequest):
    return _brain_call("system", req.action, req.payload or {}, _system_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: DATA — whitelist sources, knowledge mining, ingestion
# ═══════════════════════════════════════════════════════════════════

def _data_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "api_sources":  lambda p: _j(req.get(f"{B}/api/whitelist-hub/api-sources", timeout=10)),
        "web_sources":  lambda p: _j(req.get(f"{B}/api/whitelist-hub/web-sources", timeout=10)),
        "add_api":      lambda p: _j(req.post(f"{B}/api/whitelist-hub/api-sources", json=p, timeout=10)),
        "add_web":      lambda p: _j(req.post(f"{B}/api/whitelist-hub/web-sources", json=p, timeout=10)),
        "stats":        lambda p: _j(req.get(f"{B}/api/whitelist-hub/stats", timeout=10)),
        "flash_cache":  lambda p: _j(req.get(f"{B}/api/flash-cache/stats", timeout=10)),
    }

@router.post("/data", response_model=BrainResponse)
async def brain_data(req: BrainRequest):
    return _brain_call("data", req.action, req.payload or {}, _data_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: TASKS — scheduling, time sense, planner
# ═══════════════════════════════════════════════════════════════════

def _tasks_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "live":      lambda p: _j(req.get(f"{B}/api/tasks-hub/live", timeout=10)),
        "history":   lambda p: _j(req.get(f"{B}/api/tasks-hub/history", params={"limit": p.get("limit", 40)}, timeout=10)),
        "submit":    lambda p: _j(req.post(f"{B}/api/tasks-hub/submit", json=p, timeout=15)),
        "scheduled": lambda p: _j(req.get(f"{B}/api/tasks-hub/scheduled", timeout=10)),
        "schedule":  lambda p: _j(req.post(f"{B}/api/tasks-hub/schedule", json=p, timeout=10)),
        "time_sense": lambda p: _j(req.get(f"{B}/api/tasks-hub/time-sense", timeout=10)),
        "planner":   lambda p: _j(req.get(f"{B}/api/planner/sessions", timeout=10)),
    }

@router.post("/tasks", response_model=BrainResponse)
async def brain_tasks(req: BrainRequest):
    return _brain_call("tasks", req.action, req.payload or {}, _tasks_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN: CODE — codebase, projects, version control
# ═══════════════════════════════════════════════════════════════════

def _code_handlers() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    def _j(r): return r.json() if r.ok else {"error": f"{r.status_code}"}

    return {
        "projects":  lambda p: _j(req.get(f"{B}/api/codebase-hub/projects", timeout=10)),
        "tree":      lambda p: _j(req.get(f"{B}/api/codebase-hub/tree/{p['folder']}", timeout=10)),
        "read":      lambda p: _j(req.get(f"{B}/api/codebase-hub/file", params={"path": p["path"]}, timeout=10)),
        "write":     lambda p: _j(req.put(f"{B}/api/codebase-hub/file", json=p, timeout=10)),
        "generate":  lambda p: _j(req.post(f"{B}/api/coding-agent/generate", json=p, timeout=60)),
        "apply":     lambda p: _j(req.post(f"{B}/api/coding-agent/apply", json=p, timeout=30)),
    }

@router.post("/code", response_model=BrainResponse)
async def brain_code(req: BrainRequest):
    return _brain_call("code", req.action, req.payload or {}, _code_handlers())


# ═══════════════════════════════════════════════════════════════════
#  BRAIN DIRECTORY — list all brains and their actions
# ═══════════════════════════════════════════════════════════════════

BRAIN_DIRECTORY = {
    "chat":   {"actions": list(_chat_handlers().keys()), "description": "Conversations, prompts, consensus chat, world model"},
    "files":  {"actions": list(_files_handlers().keys()), "description": "Folders, documents, uploads, search, librarian"},
    "govern": {"actions": list(_govern_handlers().keys()), "description": "Governance, approvals, rules, persona, genesis, healing"},
    "ai":     {"actions": list(_ai_handlers().keys()), "description": "Consensus, models, coding agent, oracle, console"},
    "system": {"actions": list(_system_handlers().keys()), "description": "Health, diagnostics, runtime, triggers, probe, component health"},
    "data":   {"actions": list(_data_handlers().keys()), "description": "Whitelist sources, knowledge mining, flash cache"},
    "tasks":  {"actions": list(_tasks_handlers().keys()), "description": "Task scheduling, time sense, planner"},
    "code":   {"actions": list(_code_handlers().keys()), "description": "Codebase, projects, version control, code generation"},
}

@router.get("/directory")
async def brain_directory():
    """List all brains and their available actions."""
    total_actions = sum(len(b["actions"]) for b in BRAIN_DIRECTORY.values())
    return {
        "brains": BRAIN_DIRECTORY,
        "total_brains": len(BRAIN_DIRECTORY),
        "total_actions": total_actions,
        "usage": "POST /brain/{name} with { action: '...', payload: {...} }",
    }
