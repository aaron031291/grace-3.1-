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


# ── Architecture Compass ──────────────────────────────────────────────

@router.get("/compass/explain/{component}")
async def compass_explain(component: str):
    """Grace asks: What does this component do?"""
    from cognitive.architecture_compass import get_compass
    compass = get_compass()
    return {"component": component, "explanation": compass.explain(component)}


@router.get("/compass/find")
async def compass_find(capability: str):
    """Grace asks: What can handle this task?"""
    from cognitive.architecture_compass import get_compass
    compass = get_compass()
    results = compass.find_for(capability)
    return {"capability": capability, "components": results}


@router.get("/compass/path")
async def compass_path(from_comp: str, to_comp: str):
    """Grace asks: How does data flow from A to B?"""
    from cognitive.architecture_compass import get_compass
    compass = get_compass()
    path = compass.how_connected(from_comp, to_comp)
    return {"from": from_comp, "to": to_comp, "path": path}


@router.get("/compass/diagnose")
async def compass_diagnose():
    """Grace self-diagnoses her architecture."""
    from cognitive.architecture_compass import get_compass
    compass = get_compass()
    return compass.diagnose()


@router.get("/compass/map")
async def compass_full_map():
    """Complete architecture map with all components."""
    from cognitive.architecture_compass import get_compass
    compass = get_compass()
    return compass.get_full_map()


# ── User Intent Override ──────────────────────────────────────────────

@router.post("/override/analyse")
async def analyse_override(command: str, context: str = ""):
    """Analyse a user command for governance impacts and offer alternatives."""
    from cognitive.user_intent_override import get_override_system
    system = get_override_system()
    analysis = system.analyse(command, context)
    return {
        "original_intent": analysis.original_intent,
        "parsed_action": analysis.parsed_action,
        "governance_impacts": [
            {"rule": i.rule_name, "severity": i.severity,
             "description": i.description, "skipped_check": i.skipped_check}
            for i in analysis.governance_impacts
        ],
        "blast_radius": analysis.blast_radius,
        "risk_level": analysis.risk_level,
        "alternatives": [
            {"description": a.description, "compliance_level": a.compliance_level,
             "trade_offs": a.trade_offs, "recommended": a.recommended}
            for a in analysis.alternatives
        ],
        "override_token": analysis.override_token,
        "explanation": analysis.explanation,
        "can_proceed": analysis.can_proceed,
    }


@router.post("/override/execute")
async def execute_override(token: str):
    """Execute with user override — explicit permission confirmed."""
    from cognitive.user_intent_override import get_override_system
    system = get_override_system()
    return system.execute_override(token)


@router.get("/override/active")
async def active_overrides():
    """List all active override tokens."""
    from cognitive.user_intent_override import get_override_system
    system = get_override_system()
    return {"overrides": system.get_active_overrides()}


# ── Live Integration Protocol ─────────────────────────────────────────

@router.post("/lip/integrate")
async def lip_integrate(file_path: str):
    """Integrate a single component into Grace's world."""
    from cognitive.live_integration import integrate_component
    return integrate_component(file_path)


@router.post("/lip/integrate-directory")
async def lip_integrate_directory(dir_path: str):
    """Integrate all Python files in a directory."""
    from cognitive.live_integration import integrate_directory
    return integrate_directory(dir_path)


@router.get("/lip/ledger")
async def lip_ledger():
    """Get the full citizenship ledger."""
    from cognitive.live_integration import get_citizenship_ledger
    return get_citizenship_ledger()


@router.post("/lip/promote")
async def lip_promote(file_path: str, level: str):
    """Manually promote a component's citizenship level."""
    from cognitive.live_integration import promote_component
    return promote_component(file_path, level)


# ── Circuit Breaker & Named Loops ─────────────────────────────────────

@router.get("/loops")
async def get_named_loops():
    """Get all named system loops with status and metrics."""
    from cognitive.circuit_breaker import get_loop_status
    return {"loops": get_loop_status()}


@router.get("/loops/by-category")
async def get_loops_by_category():
    """Get loops grouped by category (homeostasis, learning, healing, trust, knowledge)."""
    from cognitive.circuit_breaker import get_loops_by_category
    return get_loops_by_category()


@router.get("/loops/{loop_name}")
async def get_loop_detail(loop_name: str):
    """Get detail for a specific named loop."""
    from cognitive.circuit_breaker import get_loop_status
    status = get_loop_status()
    if loop_name not in status:
        raise HTTPException(status_code=404, detail=f"Loop not found: {loop_name}")
    return status[loop_name]


# ── Composite Loops ───────────────────────────────────────────────────

@router.get("/composites")
async def list_composites():
    """List all composite loop definitions."""
    from cognitive.loop_orchestrator import get_loop_orchestrator
    return {"composites": get_loop_orchestrator().get_available_composites()}


@router.post("/composites/{composite_id}/run")
async def run_composite(composite_id: str):
    """Execute a composite loop (multiple loops cross-referencing)."""
    from cognitive.loop_orchestrator import get_loop_orchestrator
    orch = get_loop_orchestrator()
    result = orch.execute_composite(composite_id)
    return {
        "composite_id": result.composite_id,
        "verdict": result.verdict,
        "loops_executed": result.loops_executed,
        "loops_passed": result.loops_passed,
        "loops_failed": result.loops_failed,
        "total_duration_ms": result.total_duration_ms,
        "cross_references": result.cross_references,
        "results": [
            {"loop": r.loop_id, "success": r.success, "duration_ms": r.duration_ms,
             "output": r.output, "error": r.error}
            for r in result.results
        ],
    }


# ── Code Sandbox ──────────────────────────────────────────────────────

# ── Grace Compiler ────────────────────────────────────────────────────

# ── Blueprint Engine (Kimi+Opus design → Qwen builds) ────────────────

@router.post("/blueprint/create")
async def create_blueprint(task: str):
    """Full pipeline: describe what you want → Grace builds it."""
    from cognitive.blueprint_engine import create_from_prompt
    return create_from_prompt(task)


@router.get("/blueprint/list")
async def list_blueprints():
    """List all blueprints."""
    from cognitive.blueprint_engine import list_blueprints as _list
    return {"blueprints": _list()}


@router.post("/compiler/compile")
async def grace_compile(code: str, context: dict = None):
    """Compile code through Grace's native compiler (5-stage pipeline)."""
    from cognitive.grace_compiler import get_grace_compiler
    compiler = get_grace_compiler()
    result = compiler.compile(code, context or {})
    return result.to_dict()


# ── Domain Environments ──────────────────────────────────────────────

@router.post("/domain/create")
async def create_domain(name: str, description: str = ""):
    """Create a domain environment with auto-populated structure and learning."""
    from cognitive.librarian_autonomous import AutonomousLibrarian
    lib = AutonomousLibrarian()
    return lib.create_domain_environment(name, description)


@router.post("/domain/smart-ingest")
async def smart_ingest(file_path: str):
    """Smart document ingestion: read → understand → name → categorise → index."""
    from cognitive.librarian_autonomous import AutonomousLibrarian
    lib = AutonomousLibrarian()
    return lib.smart_ingest_document(file_path)


# ── Test Framework ────────────────────────────────────────────────────

# ── Autonomous Diagnostics ────────────────────────────────────────────

@router.get("/diagnostics/startup")
async def diagnostics_startup():
    """Run startup diagnostic — full system check with auto-fixing."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().on_startup()


@router.get("/diagnostics/hourly")
async def diagnostics_hourly():
    """Hourly health check with auto-fix."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().hourly_check()


@router.get("/diagnostics/daily")
async def diagnostics_daily():
    """Daily comprehensive report in plain English."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().daily_report()


@router.post("/diagnostics/error")
async def diagnostics_error(error_type: str, error_message: str, component: str = ""):
    """Report an error for autonomous diagnosis and fixing."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().on_error(error_type, error_message, component)


@router.post("/diagnostics/consensus-diagnose")
async def consensus_diagnose(error_type: str, error_detail: str):
    """Escalate a problem to Kimi+Opus for consensus diagnosis."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().consensus_diagnose(error_type, error_detail)


@router.get("/diagnostics/status")
async def diagnostics_status():
    """Current diagnostic system status."""
    from cognitive.autonomous_diagnostics import get_diagnostics
    return get_diagnostics().get_status()


@router.get("/test/smoke")
async def run_smoke_test():
    """Quick 30-second health check — is everything alive?"""
    from cognitive.test_framework import smoke_test
    return smoke_test()


@router.get("/test/full")
async def run_full_test():
    """Run full test suite with plain English results."""
    from cognitive.test_framework import full_test
    return full_test()


@router.get("/test/diagnostic")
async def run_diagnostic():
    """Deep diagnostic: what's broken, why, and how to fix it."""
    from cognitive.test_framework import diagnostic
    return diagnostic()


@router.post("/sandbox/run")
async def sandbox_run(code: str):
    """Execute code in sandboxed environment. Returns compile + runtime results."""
    from cognitive.code_sandbox import execute_sandboxed
    result = execute_sandboxed(code)
    return result.to_dict()


@router.post("/sandbox/verify")
async def sandbox_verify(code: str):
    """Full code quality check: compile + static + execute + score."""
    from cognitive.code_sandbox import verify_code_quality
    return verify_code_quality(code)


# ── Reverse kNN Oracle Discovery ─────────────────────────────────────

@router.get("/knowledge-gaps")
async def scan_knowledge_gaps():
    """Scan for knowledge gaps using reverse kNN."""
    from cognitive.reverse_knn import get_reverse_knn
    return get_reverse_knn().scan_knowledge_gaps()


@router.get("/knowledge-gaps/suggestions")
async def expansion_suggestions(limit: int = 10):
    """Get suggested topics to expand based on discovered gaps."""
    from cognitive.reverse_knn import get_reverse_knn
    topics = get_reverse_knn().suggest_expansion_topics(limit=limit)
    return {"suggestions": topics}


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
