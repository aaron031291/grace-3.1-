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

    # ── Loops 14-36: Full Autonomous Coverage ─────────────────────────

    # Safety Loops
    "api_request_validation": NamedLoop(
        name="API Request Validation Loop",
        category="safety",
        components=["trust_engine", "immune_system", "governance_wrapper", "event_bus"],
        status="healthy",
        description="Request authentication → rate limiting → payload validation → security scan → route to handler. Rollback: reject with error code. Fallback: most restrictive security policy.",
        max_depth=5,
    ),
    "security_compliance_enforcement": NamedLoop(
        name="Security Compliance Enforcement Loop",
        category="safety",
        components=["governance_wrapper", "trust_engine", "immune_system"],
        status="healthy",
        description="Policy compliance assessment → security posture evaluation → violation detection → corrective action → execution. Rollback: last compliant config. Fallback: maximum security lockdown.",
        max_depth=2,
    ),
    "live_integration_safety": NamedLoop(
        name="Live Integration Safety Loop",
        category="safety",
        components=["live_integration", "architecture_compass", "immune_system", "trust_engine"],
        status="healthy",
        description="Integration impact assessment → safety validation via compass → staged integration with monitoring → success validation. Rollback: revert to pre-integration state. Fallback: offline testing first.",
        max_depth=2,
    ),
    "sandbox_experiment_lifecycle": NamedLoop(
        name="Sandbox Experiment Lifecycle Loop",
        category="safety",
        components=["sandbox_engine", "immune_system", "trust_engine"],
        status="healthy",
        description="Sandbox creation → resource isolation → experiment execution → result validation → safety assessment. Rollback: immediate sandbox destruction. Fallback: offline experiment queue.",
        max_depth=3,
    ),
    "autonomous_trigger_validation": NamedLoop(
        name="Autonomous Trigger Validation Loop",
        category="safety",
        components=["central_orchestrator", "trust_engine", "governance_wrapper", "immune_system", "event_bus"],
        status="healthy",
        description="Trigger legitimacy → authority validation → safety constraints → impact assessment → authorization. Rollback: cancel pending actions. Fallback: require human authorization.",
        max_depth=2,
    ),
    "emergency_response_coordination": NamedLoop(
        name="Emergency Response Coordination Loop",
        category="safety",
        components=["immune_system", "central_orchestrator", "event_bus"],
        status="healthy",
        description="Emergency severity assessment → response protocol → resource mobilization → coordinated response → status monitoring. Rollback: system shutdown with data preservation. Fallback: complete isolation.",
        max_depth=1,
    ),

    # Verification Loops
    "api_response_verification": NamedLoop(
        name="API Response Verification Loop",
        category="verification",
        components=["consensus_engine", "trust_engine", "unified_memory"],
        status="healthy",
        description="Response content validation → consensus accuracy check → trust scoring → sanitization → delivery confirmation. Rollback: cached safe response. Fallback: generic safe response.",
        max_depth=3,
    ),
    "code_deployment_verification": NamedLoop(
        name="Code Deployment Verification Loop",
        category="verification",
        components=["immune_system", "consensus_engine", "trust_engine", "circuit_breaker"],
        status="healthy",
        description="Pre-deployment health check → staged deployment → performance validation → consensus on success → full rollout or rollback. Rollback: revert to previous stable version. Fallback: maintenance mode.",
        max_depth=3,
    ),
    "llm_hallucination_detection": NamedLoop(
        name="LLM Hallucination Detection Loop",
        category="verification",
        components=["consensus_engine", "unified_memory", "trust_engine", "pipeline"],
        status="healthy",
        description="Multi-model consensus → fact verification against memory → confidence scoring → hallucination probability → response filtering. Rollback: conservative fact-based response. Fallback: acknowledge uncertainty.",
        max_depth=5,
    ),
    "report_generation_verification": NamedLoop(
        name="Report Generation Verification Loop",
        category="verification",
        components=["reporting_engine", "consensus_engine", "unified_memory", "trust_engine"],
        status="healthy",
        description="Data source validation → report generation → fact verification → consensus validation → accuracy scoring. Rollback: template-based report. Fallback: report with uncertainty markers.",
        max_depth=4,
    ),

    # Data Loops
    "data_ingestion_validation": NamedLoop(
        name="Data Ingestion Validation Loop",
        category="data",
        components=["librarian_autonomous", "immune_system", "trust_engine", "unified_memory", "consensus_engine"],
        status="healthy",
        description="Source verification → format validation → content scanning → consensus quality check → memory integration. Rollback: remove ingested data. Fallback: manual review queue.",
        max_depth=4,
    ),
    "librarian_file_integrity": NamedLoop(
        name="Librarian File Integrity Loop",
        category="data",
        components=["librarian_autonomous", "immune_system", "unified_memory", "trust_engine", "event_bus"],
        status="healthy",
        description="File operation validation → integrity check (checksums) → permission verification → execution with monitoring → post-op validation. Rollback: restore from backup. Fallback: read-only mode.",
        max_depth=4,
    ),
    "memory_consistency_maintenance": NamedLoop(
        name="Memory Consistency Maintenance Loop",
        category="data",
        components=["unified_memory", "flash_cache", "immune_system"],
        status="healthy",
        description="Memory integrity verification → cross-reference validation → inconsistency detection → conflict resolution → synchronization. Rollback: restore from consistent backup. Fallback: read-only mode.",
        max_depth=4,
    ),
    "version_control_integrity": NamedLoop(
        name="Version Control Integrity Loop",
        category="data",
        components=["consensus_engine", "trust_engine"],
        status="healthy",
        description="Change validation → version integrity verification → conflict detection → consensus on changes → version commit. Rollback: last known good version. Fallback: read-only until resolved.",
        max_depth=3,
    ),
    "cross_system_synchronization": NamedLoop(
        name="Cross-System Synchronization Loop",
        category="data",
        components=["event_bus", "unified_memory", "central_orchestrator"],
        status="healthy",
        description="Sync requirement assessment → data consistency verification → conflict identification → resolution strategy → sync execution. Rollback: last consistent state. Fallback: eventual consistency.",
        max_depth=3,
    ),

    # Coding Loops
    "code_generation_safety": NamedLoop(
        name="Code Generation Safety Loop",
        category="coding",
        components=["pipeline", "immune_system", "consensus_engine", "trust_engine", "sandbox_engine"],
        status="healthy",
        description="Requirements analysis → code generation with constraints → static analysis → sandbox testing → consensus validation. Rollback: revert to last good code. Fallback: pre-approved templates.",
        max_depth=6,
    ),

    # Learning Loops
    "user_intent_adaptation": NamedLoop(
        name="User Intent Adaptation Loop",
        category="learning",
        components=["user_intent_override", "unified_memory", "pipeline"],
        status="healthy",
        description="Intent extraction → historical pattern analysis → preference learning → response personalisation → feedback collection. Rollback: previous user model. Fallback: generic responses.",
        max_depth=4,
    ),
    "feedback_loop_optimization": NamedLoop(
        name="Feedback Loop Optimization Loop",
        category="learning",
        components=["intelligence_layer", "unified_memory", "trust_engine"],
        status="healthy",
        description="Feedback quality assessment → learning effectiveness → optimization opportunity → parameter adjustment → performance validation. Rollback: previous learning config. Fallback: conservative learning rates.",
        max_depth=4,
    ),

    # Homeostasis Loops
    "system_health_monitoring": NamedLoop(
        name="System Health Monitoring Loop",
        category="homeostasis",
        components=["immune_system", "central_orchestrator", "event_bus", "reporting_engine"],
        status="healthy",
        description="Resource utilisation → performance metrics → anomaly detection → health scoring → alert generation. Rollback: reduce load, disable non-critical features. Fallback: safe mode with core functions.",
        max_depth=3,
    ),
    "cognitive_load_balancing": NamedLoop(
        name="Cognitive Load Balancing Loop",
        category="homeostasis",
        components=["central_orchestrator", "pipeline", "consensus_engine"],
        status="healthy",
        description="Cognitive load assessment → task priority evaluation → resource reallocation → load distribution → performance monitoring. Rollback: previous resource allocation. Fallback: essential functions only.",
        max_depth=3,
    ),
    "performance_optimization_feedback": NamedLoop(
        name="Performance Optimization Feedback Loop",
        category="homeostasis",
        components=["intelligence_layer", "central_orchestrator", "event_bus"],
        status="healthy",
        description="Bottleneck identification → optimization strategy → configuration adjustment → impact measurement → validation. Rollback: previous configuration. Fallback: conservative settings with guaranteed stability.",
        max_depth=4,
    ),

    # Trust Loops
    "external_api_reliability": NamedLoop(
        name="External API Reliability Loop",
        category="trust",
        components=["flash_cache", "trust_engine", "circuit_breaker", "event_bus"],
        status="healthy",
        description="API endpoint trust assessment → request with timeout → response validation → reliability scoring → circuit breaker update. Rollback: switch to backup/cached data. Fallback: cached responses.",
        max_depth=5,
    ),

    # Knowledge Loops
    "knowledge_graph_maintenance": NamedLoop(
        name="Knowledge Graph Maintenance Loop",
        category="knowledge",
        components=["unified_memory", "flash_cache", "consensus_engine", "magma_bridge"],
        status="healthy",
        description="Graph consistency validation → relationship verification → redundancy detection → optimization → consensus on changes. Rollback: last consistent checkpoint. Fallback: simplified graph.",
        max_depth=4,
    ),

    # ── 4 Missing Loops from Kimi+Opus Consensus Audit ────────────────

    "resource_exhaustion": NamedLoop(
        name="Resource Exhaustion Loop",
        category="homeostasis",
        components=["central_orchestrator", "immune_system", "event_bus"],
        status="healthy",
        description="Trigger: RAM > 85%. Action: spin down idle processes, flush caches, notify. Rollback: restore previous load. Fallback: safe mode.",
        max_depth=2,
    ),
    "model_drift_detection": NamedLoop(
        name="Model Drift Detection Loop",
        category="trust",
        components=["intelligence_layer", "trust_engine", "consensus_engine", "event_bus"],
        status="healthy",
        description="Trigger: LLM quality drops >15% vs baseline. Action: auto-switch primary model, flag in UI. Rollback: revert model. Fallback: use consensus.",
        max_depth=3,
    ),
    "user_feedback": NamedLoop(
        name="User Feedback Loop",
        category="learning",
        components=["unified_memory", "intelligence_layer", "trust_engine", "event_bus"],
        status="healthy",
        description="Trigger: 3+ thumbs-down on one topic. Action: flag knowledge gap, trigger learning cycle. Rollback: N/A. Fallback: route to human.",
        max_depth=4,
    ),
    "blueprint_build": NamedLoop(
        name="Blueprint Build Loop",
        category="coding",
        components=["consensus_engine", "pipeline", "grace_compiler", "trust_engine", "live_integration"],
        status="healthy",
        description="Kimi+Opus design blueprint → Qwen builds code → compiler verifies → retry/escalate → deploy. Up to 20 retries + 3 revisions. Rollback: discard code. Fallback: escalate to human.",
        max_depth=5,
    ),
    "qwen_coding_net": NamedLoop(
        name="Qwen Coding Net Loop",
        category="coding",
        components=["qwen_coding_net", "ghost_memory", "consensus_engine", "grace_compiler",
                     "trust_engine", "architecture_compass", "time_sense", "unified_memory"],
        status="healthy",
        description="Unified coding: consensus designs → ghost memory tracks → Qwen codes → compiler tests → playbook learns. Token-managed with circuit breaker. Resets ghost memory on task completion.",
        max_depth=50,
    ),
    "ethics_governance": NamedLoop(
        name="Ethics & Governance Loop",
        category="safety",
        components=["governance_wrapper", "trust_engine", "consensus_engine", "event_bus"],
        status="healthy",
        description="Trigger: governance rule violated. Action: halt response, queue for human review, log incident. Rollback: block action. Fallback: most restrictive policy.",
        max_depth=1,
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

    # Feed ML trainer with every loop entry
    try:
        from cognitive.ml_trainer import get_ml_trainer
        get_ml_trainer().observe(loop_name, {
            "depth": depth, "max_depth": max_depth,
            "executions": _metrics[loop_name]["executions"],
            "breaks": _metrics[loop_name]["breaks"],
        }, "success" if depth <= max_depth else "failure")
    except Exception:
        pass

    if depth > max_depth:
        with _depth_lock:
            _call_depths[loop_name] -= 1
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
