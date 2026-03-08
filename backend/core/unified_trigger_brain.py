"""
Unified Trigger Brain — determinism, self-heal, diagnostics, self-learning,
self-governance, and coding agent looped together with async multi-trigger access.

Single registry of triggers; each trigger maps to brain/action(s).
Run one, some, or all triggers in parallel. Used by the autonomous loop and API.
"""

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thread pool for sync brain calls from async context
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)


@dataclass
class TriggerDef:
    """Single trigger definition: id, category, brain/action, optional payload builder."""
    id: str
    name: str
    category: str  # determinism | self_heal | diagnostics | self_learning | self_governance | coding_agent
    description: str
    brain: str
    action: str
    payload_fn: Optional[Callable[[], dict]] = None  # optional; default {}

    def payload(self) -> dict:
        return (self.payload_fn or (lambda: {}))()


def _call_brain_sync(brain: str, action: str, payload: dict) -> dict:
    """Synchronous brain call (run in thread from async)."""
    from api.brain_api_v2 import call_brain
    return call_brain(brain, action, payload or {})


async def _call_brain_async(brain: str, action: str, payload: dict) -> dict:
    """Run brain call in thread pool so we don't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _call_brain_sync,
        brain,
        action,
        payload or {},
    )


# ─── TRIGGER REGISTRY: single source of truth ─────────────────────────────
# Categories: determinism, self_heal, diagnostics, self_learning, self_governance, coding_agent

TRIGGER_REGISTRY: List[TriggerDef] = [
    TriggerDef(
        id="determinism",
        name="Determinism / verify built",
        category="determinism",
        description="Run deterministic build verification; ensures everything built has been built.",
        brain="system",
        action="verify_built",
        payload_fn=lambda: {"skip_verify_script": False},
    ),
    TriggerDef(
        id="self_heal",
        name="Self-heal",
        category="self_heal",
        description="Trigger governance healing (DB, Qdrant, LLM fallback, GC).",
        brain="govern",
        action="heal",
    ),
    TriggerDef(
        id="diagnostics",
        name="Diagnostics",
        category="diagnostics",
        description="Run system diagnostics status and health map.",
        brain="system",
        action="diagnostics",
    ),
    TriggerDef(
        id="self_learning",
        name="Self-learning",
        category="self_learning",
        description="Trigger governance learning (memory, patterns).",
        brain="govern",
        action="learn",
    ),
    TriggerDef(
        id="self_governance",
        name="Self-governance",
        category="self_governance",
        description="Governance dashboard and persona (self-governance state).",
        brain="govern",
        action="dashboard",
    ),
    TriggerDef(
        id="coding_agent_scan",
        name="Coding agent (deterministic scan)",
        category="coding_agent",
        description="Deterministic code scan (AST, imports, no LLM).",
        brain="ai",
        action="deterministic_scan",
    ),
    TriggerDef(
        id="trigger_scan",
        name="Runtime trigger scan",
        category="diagnostics",
        description="Scan resources, services, code, network for anomalies.",
        brain="system",
        action="triggers",
    ),
    TriggerDef(
        id="scan_heal",
        name="Scan then heal",
        category="self_heal",
        description="Scan triggers and run healing pipeline.",
        brain="system",
        action="scan_heal",
    ),
    TriggerDef(
        id="coding_agent_step",
        name="Coding agent (proactive step)",
        category="coding_agent",
        description="Proactive diagnose and knowledge-gap check so GRACE acts, not only reacts.",
        brain="ai",
        action="diagnose",
        payload_fn=lambda: {},
    ),
    # Agentic filing and categorization (Qwen + librarian)
    TriggerDef(
        id="file_saved",
        name="File saved",
        category="filing",
        description="After a file save: run agentic filing (place in correct subfolder, categorize).",
        brain="files",
        action="filing",
        payload_fn=lambda: {},  # Caller passes path via payload when invoking
    ),
    TriggerDef(
        id="document_created",
        name="Document created",
        category="filing",
        description="After a document is created: process through librarian (ingest, tag, categorize).",
        brain="data",
        action="librarian_process",
        payload_fn=lambda: {},
    ),
    TriggerDef(
        id="librarian_organise",
        name="Librarian organise",
        category="filing",
        description="Organise a file into the correct folder (Qwen-backed suggestion).",
        brain="data",
        action="librarian_organise_file",
        payload_fn=lambda: {},
    ),
]


def get_trigger_definitions(
    category: Optional[str] = None,
    trigger_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return trigger definitions, optionally filtered by category or ids."""
    out = []
    for t in TRIGGER_REGISTRY:
        if category and t.category != category:
            continue
        if trigger_ids and t.id not in trigger_ids:
            continue
        out.append({
            "id": t.id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "brain": t.brain,
            "action": t.action,
        })
    return out


def get_categories() -> List[str]:
    """Unique categories in registry."""
    return sorted({t.category for t in TRIGGER_REGISTRY})


async def run_triggers_async(
    trigger_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run triggers in parallel (async). If neither trigger_ids nor category given, run all.
    Returns combined result with per-trigger outcomes and summary.
    """
    triggers = TRIGGER_REGISTRY
    if trigger_ids:
        triggers = [t for t in triggers if t.id in trigger_ids]
    if category:
        triggers = [t for t in triggers if t.category == category]
    if not triggers:
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "trigger_ids": trigger_ids or [],
            "category": category,
            "results": [],
            "summary": {"run": 0, "ok": 0, "failed": 0},
        }

    async def run_one(t: TriggerDef) -> Dict[str, Any]:
        try:
            r = await _call_brain_async(t.brain, t.action, t.payload())
            return {
                "trigger_id": t.id,
                "category": t.category,
                "brain": t.brain,
                "action": t.action,
                "ok": r.get("ok", False),
                "data": r.get("data"),
                "error": r.get("error"),
            }
        except Exception as e:
            logger.exception("Trigger %s failed", t.id)
            return {
                "trigger_id": t.id,
                "category": t.category,
                "brain": t.brain,
                "action": t.action,
                "ok": False,
                "error": str(e)[:300],
            }

    results = await asyncio.gather(*[run_one(t) for t in triggers])
    results_list = list(results)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_ids": [t.id for t in triggers],
        "category": category,
        "results": results_list,
        "summary": {
            "run": len(results_list),
            "ok": sum(1 for r in results_list if r.get("ok")),
            "failed": sum(1 for r in results_list if not r.get("ok")),
        },
    }


def _run_one_trigger_sync(t: TriggerDef) -> Dict[str, Any]:
    """Run a single trigger (for parallel execution)."""
    from api.brain_api_v2 import call_brain
    try:
        r = call_brain(t.brain, t.action, t.payload())
        return {
            "trigger_id": t.id,
            "category": t.category,
            "brain": t.brain,
            "action": t.action,
            "ok": r.get("ok", False),
            "data": r.get("data"),
            "error": r.get("error"),
        }
    except Exception as e:
        logger.exception("Trigger %s failed", t.id)
        return {
            "trigger_id": t.id,
            "category": t.category,
            "brain": t.brain,
            "action": t.action,
            "ok": False,
            "error": str(e)[:300],
        }


def run_triggers_sync(
    trigger_ids: Optional[List[str]] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous multi-trigger run in parallel (thread pool)."""
    from core.async_parallel import run_parallel
    triggers = TRIGGER_REGISTRY
    if trigger_ids:
        triggers = [t for t in triggers if t.id in trigger_ids]
    if category:
        triggers = [t for t in triggers if t.category == category]
    if not triggers:
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "trigger_ids": trigger_ids or [],
            "category": category,
            "results": [],
            "summary": {"run": 0, "ok": 0, "failed": 0},
        }
    thunks = [lambda _t=t: _run_one_trigger_sync(_t) for t in triggers]
    results_list = run_parallel(thunks, return_exceptions=False)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_ids": [t.id for t in triggers],
        "category": category,
        "results": results_list,
        "summary": {
            "run": len(results_list),
            "ok": sum(1 for r in results_list if r.get("ok")),
            "failed": sum(1 for r in results_list if not r.get("ok")),
        },
    }
