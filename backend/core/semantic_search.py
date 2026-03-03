"""
Semantic Search — ask Grace anything about how she works in natural language.

"How does the librarian work?" → full component profile with code location,
connections, Genesis key history, memory, dependencies.

Replaces having to explain Grace to every new developer.
"""

import ast
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent

# Component registry — what Grace knows about herself
COMPONENTS = {
    "librarian": {"file": "core/librarian.py", "purpose": "Auto-categorize, tag, version, search all documents", "connects": ["workspace_bridge", "document_processor", "genesis_tracker"]},
    "brain_api": {"file": "api/brain_api_v2.py", "purpose": "Single entry point for all 200 brain actions across 8 domains", "connects": ["all services", "all cognitive modules"]},
    "consensus_engine": {"file": "cognitive/consensus_engine.py", "purpose": "4-model deliberation — Kimi, Opus, Qwen, DeepSeek must agree", "connects": ["llm_orchestrator", "trust_engine", "intelligence"]},
    "coding_pipeline": {"file": "core/coding_pipeline.py", "purpose": "8-layer pipeline: plan→decompose→propose→select→simulate→generate→verify→deploy", "connects": ["brain_api", "deterministic_bridge", "safety", "governance"]},
    "deterministic_bridge": {"file": "core/deterministic_bridge.py", "purpose": "Find bugs WITHOUT LLM — AST parse, import check, tests, DB health", "connects": ["coding_pipeline", "ouroboros_loop"]},
    "ouroboros_loop": {"file": "api/autonomous_loop_api.py", "purpose": "30s autonomous cycle: detect→decide→act→learn→verify", "connects": ["component_health", "triggers", "intelligence", "brain_api"]},
    "hebbian": {"file": "core/hebbian.py", "purpose": "Synaptic weights between brains — connections strengthen on success", "connects": ["brain_api.call_brain"]},
    "memory_injector": {"file": "core/memory_injector.py", "purpose": "Injects memory+trust+episodes+patterns into every LLM call", "connects": ["governance_wrapper", "all LLM clients"]},
    "genesis_tracker": {"file": "api/_genesis_tracker.py", "purpose": "Track every operation with what/who/when/where/why/how", "connects": ["genesis_storage", "event_bus", "qdrant"]},
    "safety": {"file": "core/safety.py", "purpose": "Rollback, security scan, budget breaker, provenance ledger", "connects": ["coding_pipeline", "brain_api"]},
    "intelligence": {"file": "core/intelligence.py", "purpose": "Genesis key mining, adaptive trust, episodic mining", "connects": ["ouroboros_loop", "brain_api"]},
    "workspace_bridge": {"file": "core/workspace_bridge.py", "purpose": "Sync files between folder UI and Dev tab — every write tracked", "connects": ["genesis_tracker", "librarian", "realtime_sync"]},
    "project_container": {"file": "core/project_container.py", "purpose": "Isolated project environments with 3-tier governance rules", "connects": ["environment", "governance_engine"]},
    "governance_engine": {"file": "core/governance_engine.py", "purpose": "Per-project rules, approval workflow, KPI scoring, compliance", "connects": ["coding_pipeline", "brain_api"]},
    "deep_learning": {"file": "core/deep_learning.py", "purpose": "3-head PyTorch MLP predicting success/risk/trust from Genesis keys", "connects": ["intelligence", "ouroboros_loop"]},
    "cognitive_mesh": {"file": "core/cognitive_mesh.py", "purpose": "Unified interface to OODA, ambiguity, procedural memory, bandits", "connects": ["coding_pipeline", "brain_api"]},
    "auto_router": {"file": "core/auto_router.py", "purpose": "Natural language → optimal brain+action routing", "connects": ["brain_api", "hebbian"]},
    "environment": {"file": "core/environment.py", "purpose": "Select which project all output routes to", "connects": ["workspace_bridge", "brain_api"]},
    "multi_user": {"file": "core/multi_user.py", "purpose": "Lightweight user IDs, activity tracking, team summaries", "connects": ["brain_api", "tracing"]},
    "resilience": {"file": "core/resilience.py", "purpose": "Circuit breakers, error boundaries, graceful degradation", "connects": ["brain_api"]},
}


def semantic_query(question: str) -> dict:
    """
    Ask Grace anything about how she works.
    Returns structured answer with code locations, connections, history.
    """
    q = question.lower()

    # Find matching components
    matches = []
    for cid, info in COMPONENTS.items():
        score = 0
        if cid.replace("_", " ") in q or cid in q:
            score += 5
        for word in q.split():
            if word in info["purpose"].lower():
                score += 1
            if word in " ".join(info["connects"]).lower():
                score += 0.5
        if score > 0:
            matches.append((cid, info, score))

    matches.sort(key=lambda x: -x[2])

    if not matches:
        # Fallback: search all Python files for the query terms
        file_matches = _search_code(q)
        return {
            "query": question,
            "component_matches": 0,
            "code_matches": file_matches,
            "suggestion": "No exact component match. Try: " + ", ".join(list(COMPONENTS.keys())[:10]),
        }

    # Build rich response for top match
    top = matches[0]
    cid, info, score = top

    result = {
        "query": question,
        "component_id": cid,
        "purpose": info["purpose"],
        "file": info["file"],
        "connects_to": info["connects"],
    }

    # Add file details
    filepath = ROOT / info["file"]
    if filepath.exists():
        content = filepath.read_text(errors="ignore")
        result["file_size"] = len(content)
        result["line_count"] = content.count("\n") + 1

        # Extract functions/classes
        try:
            tree = ast.parse(content)
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            result["functions"] = functions[:20]
            result["classes"] = classes[:10]
        except Exception:
            pass

    # Add other matches
    if len(matches) > 1:
        result["related"] = [
            {"id": m[0], "purpose": m[1]["purpose"], "relevance": round(m[2], 1)}
            for m in matches[1:5]
        ]

    return result


def _search_code(query: str) -> list:
    """Search code files for query terms."""
    results = []
    terms = [t for t in query.split() if len(t) > 2]

    for py_file in ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file) or "venv" in str(py_file):
            continue
        try:
            content = py_file.read_text(errors="ignore")[:5000]
            if any(t in content.lower() for t in terms):
                results.append({
                    "file": str(py_file.relative_to(ROOT)),
                    "match": "content",
                })
        except Exception:
            pass
        if len(results) >= 10:
            break

    return results


def get_component_registry() -> dict:
    """Get the full component registry."""
    return {"components": COMPONENTS, "total": len(COMPONENTS)}


def get_component_profile(component_id: str) -> dict:
    """Get detailed profile for one component."""
    if component_id not in COMPONENTS:
        return {"error": f"Unknown component: {component_id}"}
    return semantic_query(component_id)
