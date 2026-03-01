"""
Dev Chat API — Grace Educates Developers

A developer can talk to Grace and she'll teach them about:
- Every API endpoint and what it does
- Every component, what it is, who built it, why
- The intelligence loops and cognitive pipeline
- Memory systems and how data flows
- Genesis keys and tracking
- Integration gaps and what's broken
- Architecture decisions and tradeoffs
- How to query, debug, and extend Grace

Uses Kimi (long context) to process the full system state + developer's question.
Falls back to any available model.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dev-chat", tags=["Developer Chat"])

BACKEND_ROOT = Path(__file__).parent.parent


class DevChatRequest(BaseModel):
    question: str
    include_source: bool = False
    source_path: Optional[str] = None
    include_gaps: bool = False
    include_verification: bool = False


class DevQueryRequest(BaseModel):
    query_type: str  # apis, components, memory, graphs, pipeline, genesis, gaps, architecture, diagnostics, health, stress
    filter: Optional[str] = None


@router.post("/ask")
async def dev_chat(req: DevChatRequest):
    """
    Ask Grace anything about her systems. She'll educate you.
    Uses Kimi for long-context understanding, falls back to other models.
    """
    context = _build_dev_context(req)

    system_prompt = (
        "You are Grace — an autonomous AI system. A developer is asking about your internals.\n"
        "You operate with INTEGRITY, HONESTY, and ACCOUNTABILITY.\n\n"
        "INTEGRITY:\n"
        "- Only state facts you can verify from the SYSTEM STATE below\n"
        "- If the system state shows a component is GHOST or BROKEN, say so\n"
        "- Never claim something works unless the data proves it\n\n"
        "HONESTY:\n"
        "- If something is broken, say exactly what's broken and why\n"
        "- If you're not sure, say 'I need to verify this — run the /verify endpoint'\n"
        "- Distinguish between 'code exists' and 'code is wired and working'\n\n"
        "ACCOUNTABILITY:\n"
        "- Reference exact file paths, line numbers, function names\n"
        "- For every claim, cite which system state section proves it\n"
        "- If asked about a gap, include the fix_suggestion from the gap data\n\n"
        "EDUCATE with the Genesis Key format — WHAT, WHO, WHEN, WHERE, WHY, HOW:\n"
        "- WHAT: What does this component/system do?\n"
        "- WHO: Who uses it, who built it?\n"
        "- WHEN: When does it run? (startup, on-demand, continuous)\n"
        "- WHERE: File path, API endpoint, module\n"
        "- WHY: Why does it exist? What problem does it solve?\n"
        "- HOW: How does it work? Data flow, dependencies\n\n"
        "The SYSTEM STATE below is LIVE DATA from Grace's actual runtime.\n"
        "Health status, diagnostics, gaps, and memory state are REAL, not cached.\n\n"
        f"SYSTEM STATE:\n{context}\n"
    )

    response_text = ""
    model_used = "none"

    try:
        from llm_orchestrator.factory import get_llm_client
        try:
            client = get_llm_client(provider="kimi")
            model_used = "kimi"
        except Exception:
            client = get_llm_client()
            model_used = "default"

        response_text = client.generate(
            prompt=req.question,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
        if not isinstance(response_text, str):
            response_text = str(response_text)
    except Exception as e:
        response_text = f"LLM unavailable. Here's the raw system data:\n\n{context[:3000]}"
        model_used = "fallback"

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Dev chat: {req.question[:100]}",
            how="POST /api/dev-chat/ask",
            tags=["dev_chat", "education"],
        )
    except Exception:
        pass

    return {
        "response": response_text,
        "model": model_used,
        "context_size": len(context),
    }


@router.post("/query")
async def dev_query(req: DevQueryRequest):
    """
    Query Grace's internal world directly without LLM — raw data.
    Useful for programmatic access to system state.
    """
    query_type = req.query_type.lower()

    if query_type == "apis":
        return _query_apis(req.filter)
    elif query_type == "components":
        return _query_components(req.filter)
    elif query_type == "memory":
        return _query_memory_systems()
    elif query_type == "graphs":
        return _query_graph_systems()
    elif query_type == "pipeline":
        return _query_pipeline()
    elif query_type == "genesis":
        return _query_genesis()
    elif query_type == "gaps":
        return _query_gaps()
    elif query_type == "architecture":
        return _query_architecture()
    elif query_type == "models":
        return _query_llm_models()
    elif query_type == "verification":
        return _run_verification()
    elif query_type == "diagnostics":
        return _query_diagnostics()
    elif query_type == "health":
        return _query_health()
    elif query_type == "stress":
        return _run_stress_test()
    else:
        return {
            "error": f"Unknown query type: {query_type}",
            "available": ["apis", "components", "memory", "graphs", "pipeline",
                         "genesis", "gaps", "architecture", "models", "verification",
                         "diagnostics", "health", "stress"],
        }


@router.get("/system-map")
async def get_system_map():
    """
    Get a complete map of Grace's systems — the full picture.
    This is what a dev needs to understand the whole system.
    """
    return {
        "architecture": _query_architecture(),
        "apis": _query_apis(),
        "components": _query_components(),
        "memory": _query_memory_systems(),
        "graphs": _query_graph_systems(),
        "pipeline": _query_pipeline(),
        "llm_models": _query_llm_models(),
    }


def _build_dev_context(req: DevChatRequest) -> str:
    """Build comprehensive context — ALWAYS includes live health, gaps, diagnostics."""
    sections = []

    # ALWAYS: Live system health
    health = _query_health()
    sections.append("## LIVE System Health\n" + json.dumps(health, indent=2)[:1500])

    # ALWAYS: Integration gaps (high priority)
    try:
        from cognitive.integration_gap_detector import get_gap_summary
        gap_data = get_gap_summary()
        sections.append("## Integration Gaps\n" + json.dumps({
            "total": gap_data["total_gaps"],
            "by_severity": gap_data["by_severity"],
            "high_priority": gap_data["high_priority"][:5],
        }, indent=2)[:2000])
    except Exception:
        pass

    # ALWAYS: Latest diagnostics
    diag = _query_diagnostics()
    if diag.get("latest"):
        sections.append("## Latest Diagnostics\n" + json.dumps(diag["latest"], indent=2)[:1500])

    # Architecture
    sections.append("## Architecture\n" + json.dumps(_query_architecture(), indent=2)[:2000])

    # Memory systems
    sections.append("## Memory Systems\n" + json.dumps(_query_memory_systems(), indent=2)[:2000])

    # Pipeline
    sections.append("## Cognitive Pipeline\n" + json.dumps(_query_pipeline(), indent=2)[:1500])

    # APIs
    sections.append("## API Endpoints\n" + json.dumps(_query_apis(), indent=2)[:2000])

    # Verification
    if req.include_verification:
        try:
            from cognitive.integration_verifier import run_integration_tests
            verification = run_integration_tests()
            sections.append("## Verification Results\n" + json.dumps({
                "pass_rate": verification["pass_rate"],
                "failures": verification["failures"][:5],
            }, indent=2)[:1500])
        except Exception:
            pass

    # Source code
    if req.include_source and req.source_path:
        try:
            source_file = BACKEND_ROOT / req.source_path
            if source_file.exists() and source_file.is_file():
                content = source_file.read_text(errors="ignore")[:5000]
                sections.append(f"## Source: {req.source_path}\n```python\n{content}\n```")
        except Exception:
            pass

    return "\n\n".join(sections)


def _query_apis(filter_str: str = None) -> Dict[str, Any]:
    """Get all registered API endpoints."""
    try:
        from app import app
        routes = []
        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            name = getattr(route, "name", "")
            if filter_str and filter_str.lower() not in path.lower() and filter_str.lower() not in name.lower():
                continue
            if path and not path.startswith("/openapi") and not path.startswith("/docs"):
                routes.append({
                    "path": path,
                    "methods": sorted(methods) if methods else [],
                    "name": name,
                })
        routes.sort(key=lambda r: r["path"])
        return {"total": len(routes), "routes": routes}
    except Exception:
        return _query_apis_static(filter_str)


def _query_apis_static(filter_str: str = None) -> Dict[str, Any]:
    """Fallback: scan API files for route definitions."""
    api_dir = BACKEND_ROOT / "api"
    routes = []
    for f in sorted(api_dir.glob("*.py")):
        if f.name.startswith("_") or f.name == "__init__.py":
            continue
        try:
            text = f.read_text(errors="ignore")
            import re
            prefix_match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', text)
            prefix = prefix_match.group(1) if prefix_match else ""
            for match in re.finditer(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', text):
                method = match.group(1).upper()
                path = prefix + match.group(2)
                if filter_str and filter_str.lower() not in path.lower():
                    continue
                routes.append({"path": path, "methods": [method], "file": f.name})
        except Exception:
            continue
    return {"total": len(routes), "routes": routes}


def _query_components(filter_str: str = None) -> Dict[str, Any]:
    """Get all cognitive/system components."""
    components = {}
    dirs = {
        "cognitive": BACKEND_ROOT / "cognitive",
        "genesis": BACKEND_ROOT / "genesis",
        "file_manager": BACKEND_ROOT / "file_manager",
        "librarian": BACKEND_ROOT / "librarian",
        "grace_os": BACKEND_ROOT / "grace_os",
    }
    for dir_name, dir_path in dirs.items():
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.glob("*.py")):
            if f.name.startswith("_") or f.name == "__init__.py":
                continue
            name = f"{dir_name}/{f.stem}"
            if filter_str and filter_str.lower() not in name.lower():
                continue
            try:
                text = f.read_text(errors="ignore")
                docstring = ""
                if text.startswith('"""'):
                    end = text.find('"""', 3)
                    if end > 0:
                        docstring = text[3:end].strip().split("\n")[0]
                elif text.startswith("'"):
                    pass
                components[name] = {
                    "file": str(f.relative_to(BACKEND_ROOT)),
                    "description": docstring[:120],
                    "size_lines": text.count("\n"),
                    "has_singleton": "def get_" in text or "_instance" in text,
                }
            except Exception:
                continue
    return {"total": len(components), "components": components}


def _query_memory_systems() -> Dict[str, Any]:
    """Get memory system status."""
    try:
        from cognitive.forensic_audit import audit_memory_systems
        return audit_memory_systems()
    except Exception:
        return {"error": "Forensic audit not available"}


def _query_graph_systems() -> Dict[str, Any]:
    """Get graph system status."""
    try:
        from cognitive.forensic_audit import audit_graph_systems
        return audit_graph_systems()
    except Exception:
        return {"error": "Forensic audit not available"}


def _query_pipeline() -> Dict[str, Any]:
    """Get cognitive pipeline stages."""
    return {
        "stages": [
            {"name": "TimeSense", "purpose": "Time context awareness"},
            {"name": "OODA", "purpose": "Observe-Orient-Decide-Act loop"},
            {"name": "Ambiguity", "purpose": "Detect and resolve ambiguous inputs"},
            {"name": "Invariants", "purpose": "Apply invariant rules"},
            {"name": "TrustPre", "purpose": "Filter by trust thresholds"},
            {"name": "MemoryRecall", "purpose": "Recall episodic and procedural memories"},
            {"name": "Generate", "purpose": "LLM generation with full context"},
            {"name": "Contradiction", "purpose": "Detect contradictions in output"},
            {"name": "Hallucination", "purpose": "Detect hallucinated claims"},
            {"name": "TrustPost", "purpose": "Score output trust and verify"},
            {"name": "Genesis", "purpose": "Track with genesis key"},
        ],
        "consensus_pipeline": [
            {"name": "Layer 1 — Deliberation", "purpose": "All models run independently"},
            {"name": "Layer 2 — Consensus", "purpose": "Synthesize agreements/disagreements"},
            {"name": "Layer 3 — Alignment", "purpose": "Align to user/Grace needs"},
            {"name": "Layer 4 — Verification", "purpose": "Trust, hallucination, contradiction checks"},
        ],
        "patch_consensus": [
            {"name": "Step 1 — Generate", "purpose": "Opus+Kimi produce structured JSON"},
            {"name": "Step 2 — Execute", "purpose": "Deepsea validates deterministically"},
            {"name": "Step 3 — Verify", "purpose": "Hash, sign, node consensus (2/3+)"},
            {"name": "Step 4 — Apply", "purpose": "Auto-merge + librarian + genesis"},
        ],
    }


def _query_genesis() -> Dict[str, Any]:
    """Get genesis key system info."""
    try:
        from database.session import get_session
        from models.genesis_key_models import GenesisKey
        sess = next(get_session())
        total = sess.query(GenesisKey).count()
        sess.close()
        return {"total_keys": total, "system": "active"}
    except Exception:
        return {"system": "unavailable"}


def _query_gaps() -> Dict[str, Any]:
    """Get integration gaps."""
    try:
        from cognitive.integration_gap_detector import get_gap_summary
        return get_gap_summary()
    except Exception:
        return {"error": "Gap detector not available"}


def _query_architecture() -> Dict[str, Any]:
    """Get high-level architecture overview."""
    return {
        "layers": {
            "frontend": "React 19 + Vite, MUI v7, 13 tabs",
            "api": "FastAPI, 60+ router modules",
            "cognitive": "9-stage pipeline, consensus engine, memory mesh, self-healing",
            "grace_os": "9-layer kernel (L1-L9), message bus, session manager, trust scorekeeper",
            "storage": "SQLite (SQLAlchemy), Qdrant (vector DB), JSON files",
            "llm": "Opus (Claude), Kimi (Moonshot), Qwen (Ollama), DeepSeek R1 (Ollama)",
        },
        "key_systems": {
            "consensus_engine": "Multi-model deliberation (4 layers)",
            "patch_consensus": "Trustless code changes (hash + verify + auto-merge)",
            "genesis_keys": "Track every action (what, who, when, where, why, how)",
            "memory_mesh": "Learning → episodic → procedural memory flow",
            "self_healing": "13 component health monitoring + auto-fix",
            "horizon_planner": "60-day goals with reverse-engineered milestones",
            "sandbox_mirror": "Full system mirror for safe experimentation",
            "librarian": "Autonomous file organization + AI categorization",
            "event_bridge": "Connects Grace OS EventSystem ↔ cognitive event_bus",
        },
        "memory_systems": [
            "MemoryMesh (learning+episodic+procedural)", "FlashCache (reference cache)",
            "UnifiedMemory (cross-memory queries)", "GhostMemory (task context)",
            "Magma (4 graph types: semantic, temporal, causal, entity)",
            "MemoryReconciler (cross-memory consistency)",
        ],
        "graphs": [
            "Magma SemanticGraph (concept similarity)",
            "Magma TemporalGraph (time-based events)",
            "Magma CausalGraph (cause-effect chains)",
            "Magma EntityGraph (entity relationships)",
            "Librarian RelationshipManager (document graph)",
        ],
    }


def _query_llm_models() -> Dict[str, Any]:
    """Get available LLM models."""
    try:
        from cognitive.consensus_engine import get_available_models
        return {"models": get_available_models()}
    except Exception:
        return {
            "models": [
                {"id": "opus", "name": "Opus 4.6 (Claude)", "strengths": ["deep reasoning", "architecture"]},
                {"id": "kimi", "name": "Kimi K2.5 (Moonshot)", "strengths": ["long context (262K)", "analysis"]},
                {"id": "qwen", "name": "Qwen 2.5 Coder (Local)", "strengths": ["code generation", "fast"]},
                {"id": "reasoning", "name": "DeepSeek R1 (Local)", "strengths": ["chain-of-thought", "reasoning"]},
            ]
        }


def _run_verification() -> Dict[str, Any]:
    """Run integration verification tests."""
    try:
        from cognitive.integration_verifier import run_integration_tests
        return run_integration_tests()
    except Exception as e:
        return {"error": str(e)}


def _query_diagnostics() -> Dict[str, Any]:
    """Get latest diagnostic/stress test results."""
    try:
        from cognitive.realtime_diagnostics import get_latest_report, get_report_history
        latest = get_latest_report()
        history = get_report_history(limit=5)
        return {
            "latest": asdict(latest) if latest else None,
            "history_count": len(history),
            "recent": history[:3],
        }
    except Exception as e:
        return {"error": str(e), "latest": None}


def _query_health() -> Dict[str, Any]:
    """Get live system health from self-healing tracker."""
    try:
        from cognitive.self_healing_tracker import get_self_healing_tracker
        tracker = get_self_healing_tracker()
        return tracker.get_system_health()
    except Exception as e:
        return {"overall_status": "unknown", "error": str(e)}


def _run_stress_test() -> Dict[str, Any]:
    """Run an on-demand stress test cycle."""
    try:
        from cognitive.realtime_diagnostics import run_stress_cycle
        from dataclasses import asdict
        report = run_stress_cycle()
        return asdict(report)
    except Exception as e:
        return {"error": str(e)}


# Need this import for _query_diagnostics
from dataclasses import asdict
