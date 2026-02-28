"""
Circuit Breaker — Prevents dangerous recursive loops from causing stack overflows.

Opus forensic audit identified 3 dangerous recursive loops:
  1. Genesis Provenance Cascade (8-module deep cycle)
  2. Core Pipeline Loop (6-module cycle)
  3. Kimi Enhancement Loop (pipeline ↔ kimi_enhanced)

This module provides:
  - Per-loop call depth tracking
  - Configurable max depth per loop
  - Automatic circuit breaking when depth exceeded
  - Named loop registry for Grace's self-awareness
  - Loop execution metrics for the reporting engine

Also registers all 12 named system loops (healthy + dangerous) so
Grace can reference them by name in her internal dialogue.
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NamedLoop:
    name: str
    category: str  # homeostasis, learning, healing, trust, knowledge
    components: List[str]
    status: str  # healthy, dangerous, broken
    description: str
    max_depth: int = 5
    current_depth: int = 0
    total_executions: int = 0
    total_breaks: int = 0


# All named system loops from Opus audit
NAMED_LOOPS: Dict[str, NamedLoop] = {
    # Homeostasis Loops
    "healing_homeostasis": NamedLoop(
        name="Autonomous Healing Loop",
        category="homeostasis",
        components=["immune_system", "healing_coordinator", "autonomous_healing_system"],
        status="healthy",
        description="Self-healing detect→fix→verify cycle. Immune system detects anomalies, coordinator orchestrates healing, results feed back to immune for learning.",
    ),
    "trust_homeostasis": NamedLoop(
        name="Trust Homeostasis Loop",
        category="homeostasis",
        components=["genesis_key_service", "governance", "trust_engine"],
        status="healthy",
        description="Trust scores self-regulate. Genesis keys track actions, governance evaluates compliance, trust scores adjust, which influences future genesis key confidence.",
    ),
    "resource_balance": NamedLoop(
        name="Resource Balance Loop",
        category="homeostasis",
        components=["central_orchestrator", "immune_system", "event_bus"],
        status="healthy",
        description="System resources stay balanced. Orchestrator monitors load, immune system throttles if needed, event bus propagates state changes.",
    ),

    # Learning Loops
    "autonomous_learning": NamedLoop(
        name="Autonomous Learning Loop",
        category="learning",
        components=["autonomous_triggers", "llm_orchestrator", "cognitive_layer1", "feedback_loop"],
        status="healthy",
        description="Grace learns from her own actions. Triggers fire LLM calls, results feed cognitive layer, outcomes stored as learning examples, which improve future triggers.",
    ),
    "memory_mesh_learning": NamedLoop(
        name="Memory Mesh Learning Loop",
        category="learning",
        components=["unified_memory", "flash_cache", "magma_bridge", "knowledge_cycle"],
        status="healthy",
        description="Knowledge expands iteratively. Memory queries find gaps, knowledge cycle discovers new data, flash cache indexes references, unified memory integrates.",
    ),
    "consensus_refinement": NamedLoop(
        name="Consensus Refinement Loop",
        category="learning",
        components=["consensus_engine", "trust_engine", "pipeline"],
        status="healthy",
        description="Multi-model consensus improves over time. Consensus results are trust-scored, scores inform future model weighting, better weighting improves consensus.",
        max_depth=3,
    ),

    # Healing Loops
    "cognitive_healing": NamedLoop(
        name="Cognitive Healing Loop",
        category="healing",
        components=["immune_system", "healing_coordinator", "consensus_engine"],
        status="healthy",
        description="Complex healing uses multi-model diagnosis. Immune detects, coordinator tries fix, if stuck escalates to consensus roundtable for multi-model diagnosis.",
    ),
    "pipeline_self_repair": NamedLoop(
        name="Pipeline Self-Repair Loop",
        category="healing",
        components=["pipeline", "trust_engine", "immune_system"],
        status="healthy",
        description="Pipeline failures trigger self-repair. Failed stages lower trust, low trust triggers immune scan, immune heals the pipeline component.",
    ),

    # Trust Loops
    "genesis_trust": NamedLoop(
        name="Genesis Trust Loop",
        category="trust",
        components=["genesis_key_service", "trust_engine", "governance_wrapper"],
        status="healthy",
        description="Every action builds or erodes trust. Genesis keys track outputs, trust engine scores them, governance wrapper enforces trust thresholds.",
    ),

    # Knowledge Loops
    "knowledge_integration": NamedLoop(
        name="Knowledge Integration Loop",
        category="knowledge",
        components=["librarian_autonomous", "flash_cache", "unified_memory", "knowledge_cycle"],
        status="healthy",
        description="New files trigger knowledge expansion. Librarian organises, flash cache indexes, unified memory stores, knowledge cycle discovers related topics.",
    ),
    "cognitive_consensus": NamedLoop(
        name="Cognitive Consensus Loop",
        category="knowledge",
        components=["pipeline", "consensus_engine", "unified_memory"],
        status="healthy",
        description="Pipeline ambiguity escalates to consensus, consensus results stored in memory, memory informs future pipeline decisions.",
        max_depth=3,
    ),
    "live_integration": NamedLoop(
        name="Live Integration Loop",
        category="knowledge",
        components=["live_integration", "architecture_compass", "trust_engine", "event_bus"],
        status="healthy",
        description="New components auto-integrate. LIP scans, compass maps, trust scores, event bus notifies all systems of the new citizen.",
    ),

    # The 13th Loop — from HEAL-001 incident
    "autonomous_healing": NamedLoop(
        name="Autonomous Healing Loop (13th Loop)",
        category="healing",
        components=["immune_system", "consensus_engine", "trust_engine", "unified_memory",
                     "event_bus", "intelligence_layer", "circuit_breaker"],
        status="healthy",
        description="Complete autonomous healing: Detect→Triage→Diagnose→Select Strategy→Validate→Snapshot→Execute→Verify Quality→Commit/Rollback→Learn. Born from HEAL-001: wholesale rewrite caused 50.6% content loss. Now enforces surgical patches, size gates, quality gates, and automatic rollback.",
        max_depth=3,
    ),
}

# Thread-local call depth tracking
_call_depths: Dict[str, int] = defaultdict(int)
_depth_lock = threading.Lock()
_metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: {"executions": 0, "breaks": 0})


def enter_loop(loop_name: str) -> bool:
    """
    Enter a named loop. Returns True if OK to proceed, False if circuit broken.
    Must be paired with exit_loop() in a try/finally.
    """
    loop = NAMED_LOOPS.get(loop_name)
    max_depth = loop.max_depth if loop else 5

    with _depth_lock:
        _call_depths[loop_name] += 1
        depth = _call_depths[loop_name]
        _metrics[loop_name]["executions"] += 1

    if depth > max_depth:
        with _depth_lock:
            _metrics[loop_name]["breaks"] += 1
        logger.warning(f"[CIRCUIT BREAKER] Loop '{loop_name}' broken at depth {depth} (max {max_depth})")

        try:
            from cognitive.event_bus import publish_async
            publish_async("circuit_breaker.triggered", {
                "loop": loop_name, "depth": depth, "max": max_depth,
            }, source="circuit_breaker")
        except Exception:
            pass

        return False

    return True


def exit_loop(loop_name: str):
    """Exit a named loop — decrement depth counter."""
    with _depth_lock:
        _call_depths[loop_name] = max(0, _call_depths[loop_name] - 1)


def get_loop_status() -> Dict[str, Any]:
    """Get status of all named loops."""
    result = {}
    with _depth_lock:
        for name, loop in NAMED_LOOPS.items():
            metrics = _metrics.get(name, {"executions": 0, "breaks": 0})
            result[name] = {
                "display_name": loop.name,
                "category": loop.category,
                "status": loop.status,
                "description": loop.description,
                "components": loop.components,
                "max_depth": loop.max_depth,
                "current_depth": _call_depths.get(name, 0),
                "total_executions": metrics["executions"],
                "total_breaks": metrics["breaks"],
            }
    return result


def get_loops_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """Get loops grouped by category."""
    by_cat: Dict[str, list] = {}
    status = get_loop_status()
    for name, info in status.items():
        cat = info["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append({"id": name, **info})
    return by_cat


def protected_call(loop_name: str, fn: Callable, *args, **kwargs) -> Any:
    """Execute a function within a circuit-protected loop."""
    if not enter_loop(loop_name):
        return None
    try:
        return fn(*args, **kwargs)
    finally:
        exit_loop(loop_name)
