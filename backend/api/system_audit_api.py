"""
System Audit API — Full architecture analysis via Kimi + Opus consensus.

Generates a comprehensive system map and asks both models to:
1. Identify holes in the architecture
2. Find disconnected/underutilized components
3. Assess their own integration and how they can help Grace
4. Provide consensus on system quality and next steps
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["System Audit"])


def _build_system_map() -> str:
    """Build a comprehensive textual map of Grace's architecture."""
    sections = []

    # 1. Source code structure
    backend = Path(__file__).parent.parent
    sections.append("## SOURCE CODE STRUCTURE")
    for subdir in ["api", "cognitive", "llm_orchestrator", "genesis", "security", "search", "ingestion"]:
        d = backend / subdir
        if d.exists():
            files = sorted(f.name for f in d.iterdir() if f.is_file() and f.suffix == ".py")
            sections.append(f"\n### {subdir}/ ({len(files)} files)")
            for f in files:
                sections.append(f"  - {f}")

    # 2. API endpoints
    sections.append("\n## API ENDPOINTS")
    try:
        from api.manifest_api import _collect_endpoints
        endpoints = _collect_endpoints()
        sections.append(f"Total endpoints: {len(endpoints)}")
        by_prefix = {}
        for ep in endpoints:
            prefix = ep.get("path", "").split("/")[2] if len(ep.get("path", "").split("/")) > 2 else "root"
            by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
        for prefix, count in sorted(by_prefix.items(), key=lambda x: -x[1]):
            sections.append(f"  /{prefix}: {count} endpoints")
    except Exception:
        sections.append("  (manifest unavailable)")

    # 3. Cognitive systems
    sections.append("\n## COGNITIVE SYSTEMS")
    cognitive_modules = [
        ("pipeline.py", "9-stage cognitive pipeline (TimeSense→OODA→Ambiguity→Invariants→Generate→Contradiction→Hallucination→Trust→Genesis)"),
        ("trust_engine.py", "Component-level trust scoring (0-100), chunk-based confidence"),
        ("immune_system.py", "AVN — autonomous health monitoring, adaptive scanning, healing playbook"),
        ("consensus_engine.py", "Multi-model roundtable (4 layers: deliberate→consensus→align→verify)"),
        ("flash_cache.py", "Reference-based caching — store URI+keywords, stream on demand"),
        ("magma_bridge.py", "Graph memory — semantic, temporal, causal, entity relations"),
        ("knowledge_cycle.py", "Iterative knowledge expansion (Seed→Discover→Score→Enrich→Reingest)"),
        ("librarian_autonomous.py", "Autonomous file organisation with Kimi reasoning"),
        ("hunter_assimilator.py", "Autonomous code integration (HUNTER keyword trigger)"),
        ("idle_learner.py", "Background learning during idle time (26-topic curriculum)"),
        ("healing_coordinator.py", "Orchestrates detect→diagnose→fix→verify→learn chain"),
        ("file_generator.py", "Autonomous file creation (PDF, code, docs) from prompts"),
        ("self_healing.py", "Service restart, reconnection, fallback logic"),
    ]
    for name, desc in cognitive_modules:
        exists = (backend / "cognitive" / name).exists()
        status = "✓" if exists else "✗"
        sections.append(f"  {status} {name}: {desc}")

    # 4. LLM Providers
    sections.append("\n## LLM PROVIDERS")
    from settings import settings
    sections.append(f"  Default provider: {settings.LLM_PROVIDER}")
    sections.append(f"  Kimi API key configured: {'Yes' if settings.KIMI_API_KEY else 'No'}")
    sections.append(f"  Opus API key configured: {'Yes' if settings.OPUS_API_KEY else 'No'}")
    sections.append(f"  Ollama URL: {settings.OLLAMA_URL}")
    sections.append(f"  Ollama code model: {settings.OLLAMA_MODEL_CODE or '(not set)'}")
    sections.append(f"  Ollama reasoning model: {settings.OLLAMA_MODEL_REASON or '(not set)'}")

    # 5. Database
    sections.append("\n## DATABASE")
    try:
        from sqlalchemy import text
        from database.session import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            try:
                tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).fetchall()
                sections.append(f"  Tables: {len(tables)}")
                for t in tables:
                    count = db.execute(text(f"SELECT COUNT(*) FROM [{t[0]}]")).scalar()
                    sections.append(f"    - {t[0]}: {count} rows")
            finally:
                db.close()
    except Exception as e:
        sections.append(f"  Database error: {e}")

    # 6. Integration map
    sections.append("\n## INTEGRATION MAP — What connects to what")
    integrations = [
        ("Pipeline", "→ Trust Engine, Magma, Genesis, FlashCache, FeedbackLoop"),
        ("Consensus Engine", "→ All LLM providers (parallel), Trust Engine, Genesis, FeedbackLoop"),
        ("Immune System", "→ TimeSense, Trust Engine, Magma, Genesis Realtime, Consensus (escalation)"),
        ("Librarian", "→ Docs Library, FlashCache, Genesis, Kimi, Consensus (new folders)"),
        ("Knowledge Cycle", "→ Oracle, RAG, Magma, FlashCache, Trust Engine"),
        ("FlashCache", "→ SQLite, In-memory LRU, Keyword Index"),
        ("Whitelist Hub", "→ FlashCache (auto-register), Oracle, Magma, Trust Engine, Genesis"),
        ("SerpAPI", "→ FlashCache (auto-cache results)"),
        ("World Model", "→ All APIs, Database, Chat stats, Source code"),
        ("HUNTER", "→ Pipeline, Trust, Librarian, Immune, Genesis"),
        ("Idle Learner", "→ TimeSense, Magma, Genesis"),
        ("Chunked Upload", "→ Docs Library, Librarian, Magma, Genesis"),
    ]
    for system, connections in integrations:
        sections.append(f"  {system} {connections}")

    # 7. Known gaps
    sections.append("\n## KNOWN GAPS (from internal audit)")
    gaps = [
        "Mirror Self-Model: module exists but constructor requires DB session — pipeline can't instantiate",
        "Idle Learner: not connected to Librarian for auto-research output organization",
        "HUNTER: doesn't use consensus engine for ambiguous code analysis",
        "Pipeline: ambiguity stage doesn't escalate to consensus for blocking unknowns",
        "Governance wrapper: tracks LLM calls but doesn't feed stats to BI dashboard",
    ]
    for g in gaps:
        sections.append(f"  ⚠ {g}")

    return "\n".join(sections)


@router.post("/full")
async def run_full_audit(use_consensus: bool = True):
    """
    Run a full system audit using Kimi + Opus (or just the available model).
    Returns individual analyses and consensus.
    """
    system_map = _build_system_map()

    audit_prompt = (
        "You are auditing an autonomous AI system called Grace. Below is a complete "
        "map of its architecture, components, integrations, and known gaps.\n\n"
        "Provide a thorough analysis covering:\n\n"
        "1. **Architecture Assessment** — How well-designed is the system? What patterns are strong?\n"
        "2. **Holes & Disconnections** — What components exist but aren't properly connected? "
        "What's missing entirely?\n"
        "3. **Integration Gaps** — Where should components be connected but aren't? "
        "Be specific about which modules should talk to which.\n"
        "4. **Your Integration** — As an AI model integrated into this system, how does your "
        "integration help Grace? What could you do better if given more access?\n"
        "5. **System Quality Score** — Rate the overall system 1-10 with reasoning.\n"
        "6. **Top 10 Improvements** — Prioritized list of what to fix/build next.\n"
        "7. **Your Honest Assessment** — What do you genuinely think about this system's "
        "potential, its approach to AI autonomy, and where it's heading?\n\n"
        f"=== GRACE SYSTEM MAP ===\n\n{system_map}"
    )

    if use_consensus:
        from cognitive.consensus_engine import run_consensus, _check_model_available
        models_to_use = []
        if _check_model_available("kimi"):
            models_to_use.append("kimi")
        if _check_model_available("opus"):
            models_to_use.append("opus")
        if not models_to_use:
            models_to_use = ["qwen"]

        try:
            result = run_consensus(
                prompt=audit_prompt,
                models=models_to_use,
                system_prompt=(
                    "You are a senior AI systems architect auditing Grace, an autonomous AI system. "
                    "Be thorough, honest, and constructive. Identify real problems, not surface issues. "
                    "Consider the system from the perspective of production readiness, scalability, "
                    "and genuine autonomous capability."
                ),
                source="user",
                user_context="System architect requesting full audit",
            )
            return {
                "audit_type": "consensus",
                "models_used": result.models_used,
                "individual_analyses": result.individual_responses,
                "consensus": result.consensus_text,
                "aligned_output": result.alignment_text,
                "final_audit": result.final_output,
                "confidence": result.confidence,
                "agreements": result.agreements,
                "disagreements": result.disagreements,
                "verification": result.verification,
                "total_latency_ms": result.total_latency_ms,
                "system_map_length": len(system_map),
            }
        except Exception as e:
            logger.error(f"Consensus audit failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Single model audit
        try:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            response = client.generate(
                prompt=audit_prompt,
                system_prompt="You are a senior AI systems architect.",
                temperature=0.3, max_tokens=8192,
            )
            return {"audit_type": "single", "model": "kimi", "audit": response}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/map")
async def get_system_map():
    """Get the raw system map without running the audit."""
    return {"system_map": _build_system_map()}


# ── Model Version Management ──────────────────────────────────────────

@router.get("/models/check")
async def check_model_versions():
    """Check all LLM providers for new model versions."""
    from cognitive.model_updater import check_all_models
    return check_all_models()


@router.post("/models/update")
async def update_model(provider: str, model_id: str):
    """Update the active model for a provider (kimi, opus, ollama)."""
    from cognitive.model_updater import update_model as _update
    result = _update(provider, model_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/models/history")
async def model_version_history():
    """Get the history of model version changes."""
    from cognitive.model_updater import get_version_history
    return get_version_history()


# ── Central Orchestrator ──────────────────────────────────────────────

@router.get("/orchestrator/dashboard")
async def orchestrator_dashboard():
    """Get the central orchestrator's dashboard — global state, integration health."""
    from cognitive.central_orchestrator import get_orchestrator
    orch = get_orchestrator()
    orch.initialize()
    return orch.get_dashboard()


@router.post("/orchestrator/sync")
async def orchestrator_sync():
    """Force a full state sync across all systems."""
    from cognitive.central_orchestrator import get_orchestrator
    orch = get_orchestrator()
    orch.initialize()
    return orch.sync_state()


@router.get("/orchestrator/health")
async def integration_health():
    """Check all integration points — find broken connections."""
    from cognitive.central_orchestrator import get_orchestrator
    orch = get_orchestrator()
    return orch.check_integration_health()


@router.post("/orchestrator/route")
async def route_task(task_type: str, data: dict = None):
    """Route a task to the appropriate cognitive module."""
    from cognitive.central_orchestrator import get_orchestrator
    orch = get_orchestrator()
    orch.initialize()
    return orch.route_task(task_type, data or {})


@router.get("/integration-matrix")
async def get_integration_matrix():
    """
    Return a matrix showing which systems connect to which.
    For each system, shows: connected (green), should-connect (yellow), not-needed (grey).
    """
    systems = [
        "Pipeline", "Consensus", "Immune", "Librarian", "FlashCache",
        "Trust Engine", "Magma", "Genesis", "Knowledge Cycle", "HUNTER",
        "Idle Learner", "Docs Library", "Whitelist", "Oracle", "SerpAPI",
    ]

    # connected[A][B] = True means A uses B
    connected = {
        "Pipeline": {"Trust Engine", "Magma", "Genesis", "FlashCache", "Librarian"},
        "Consensus": {"Trust Engine", "Genesis", "Pipeline"},
        "Immune": {"Trust Engine", "Magma", "Genesis", "Consensus"},
        "Librarian": {"FlashCache", "Genesis", "Docs Library", "Consensus"},
        "FlashCache": set(),
        "Trust Engine": set(),
        "Magma": set(),
        "Genesis": set(),
        "Knowledge Cycle": {"Oracle", "Magma", "Trust Engine", "FlashCache"},
        "HUNTER": {"Pipeline", "Trust Engine", "Librarian", "Immune", "Genesis"},
        "Idle Learner": {"Magma", "Genesis"},
        "Docs Library": {"Genesis", "Trust Engine"},
        "Whitelist": {"FlashCache", "Oracle", "Magma", "Trust Engine", "Genesis"},
        "Oracle": {"Genesis"},
        "SerpAPI": {"FlashCache"},
    }

    should_connect = {
        "Pipeline": {"Consensus"},
        "Immune": set(),
        "Librarian": {"Idle Learner", "Knowledge Cycle"},
        "Idle Learner": {"Librarian", "FlashCache"},
        "HUNTER": {"Consensus", "FlashCache"},
        "Knowledge Cycle": {"Consensus"},
        "Oracle": {"FlashCache", "Consensus"},
    }

    matrix = []
    for sys_name in systems:
        row = {"system": sys_name, "connections": {}}
        conn = connected.get(sys_name, set())
        should = should_connect.get(sys_name, set())
        for target in systems:
            if target == sys_name:
                row["connections"][target] = "self"
            elif target in conn:
                row["connections"][target] = "connected"
            elif target in should:
                row["connections"][target] = "should_connect"
            else:
                row["connections"][target] = "not_needed"
        matrix.append(row)

    return {"systems": systems, "matrix": matrix}
