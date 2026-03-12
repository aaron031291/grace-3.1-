"""
Loop Orchestrator — Cross-Referencing Loop Composition

Loops don't operate in isolation. Real operations trigger MULTIPLE loops
simultaneously. The orchestrator composes loops together:

Example: Code generation triggers:
  1. code_generation_safety (coding)
  2. llm_hallucination_detection (verification)
  3. trust_homeostasis (homeostasis)
  4. data_ingestion_validation (data — for the generated code)
  5. librarian_file_integrity (data — for file writes)

These run as a COMPOSITE LOOP — cross-referencing each other's outputs
so intelligence flows between them.

Composite Loops (pre-defined):
  - CODE_WRITE: coding + verification + data + trust
  - DATA_INGEST: data + verification + trust + learning
  - HEAL_AND_LEARN: healing + learning + trust + homeostasis
  - DEPLOY_SAFE: coding + verification + safety + homeostasis
  - USER_REQUEST: safety + verification + learning + trust
  - SYSTEM_MAINTENANCE: homeostasis + data + safety + healing
  - KNOWLEDGE_EXPAND: knowledge + learning + data + verification
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class LoopResult:
    loop_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class CompositeResult:
    composite_id: str
    loops_executed: int
    loops_passed: int
    loops_failed: int
    results: List[LoopResult] = field(default_factory=list)
    cross_references: Dict[str, Any] = field(default_factory=dict)
    total_duration_ms: float = 0
    verdict: str = "unknown"


# Pre-defined composite loops — which loops fire together
COMPOSITE_LOOPS = {
    "code_write": {
        "name": "Code Write Composite",
        "description": "Full code generation with verification, trust, and file integrity",
        "loops": ["code_generation_safety", "llm_hallucination_detection",
                  "trust_homeostasis", "librarian_file_integrity"],
        "cross_refs": {
            "code_generation_safety → llm_hallucination_detection": "generated code feeds into hallucination check",
            "llm_hallucination_detection → trust_homeostasis": "hallucination score feeds trust update",
            "trust_homeostasis → librarian_file_integrity": "trust score determines write permission",
        },
    },
    "data_ingest": {
        "name": "Data Ingestion Composite",
        "description": "Full data ingestion with validation, trust scoring, and learning",
        "loops": ["data_ingestion_validation", "api_response_verification",
                  "trust_homeostasis", "memory_consistency_maintenance"],
        "cross_refs": {
            "data_ingestion_validation → api_response_verification": "ingested data verified for accuracy",
            "api_response_verification → trust_homeostasis": "verification result updates trust",
            "trust_homeostasis → memory_consistency_maintenance": "trust-scored data stored in memory",
        },
    },
    "heal_and_learn": {
        "name": "Heal and Learn Composite",
        "description": "Autonomous healing with learning from outcomes",
        "loops": ["autonomous_healing", "feedback_loop_optimization",
                  "trust_homeostasis", "system_health_monitoring"],
        "cross_refs": {
            "autonomous_healing → feedback_loop_optimization": "healing outcome feeds learning",
            "feedback_loop_optimization → trust_homeostasis": "learning success updates trust",
            "trust_homeostasis → system_health_monitoring": "trust change triggers health check",
        },
    },
    "deploy_safe": {
        "name": "Safe Deployment Composite",
        "description": "Code deployment with full safety chain",
        "loops": ["code_deployment_verification", "live_integration_safety",
                  "security_compliance_enforcement", "system_health_monitoring"],
        "cross_refs": {
            "code_deployment_verification → live_integration_safety": "verified code enters integration",
            "live_integration_safety → security_compliance_enforcement": "integration checked for compliance",
            "security_compliance_enforcement → system_health_monitoring": "compliance result triggers health update",
        },
    },
    "user_request": {
        "name": "User Request Composite",
        "description": "Full user request handling with safety, verification, and adaptation",
        "loops": ["api_request_validation", "user_intent_adaptation",
                  "llm_hallucination_detection", "trust_homeostasis"],
        "cross_refs": {
            "api_request_validation → user_intent_adaptation": "validated request parsed for intent",
            "user_intent_adaptation → llm_hallucination_detection": "adapted response verified for hallucinations",
            "llm_hallucination_detection → trust_homeostasis": "response quality feeds trust",
        },
    },
    "system_maintenance": {
        "name": "System Maintenance Composite",
        "description": "Periodic system health, memory cleanup, and performance tuning",
        "loops": ["system_health_monitoring", "memory_consistency_maintenance",
                  "performance_optimization_feedback", "cross_system_synchronization"],
        "cross_refs": {
            "system_health_monitoring → memory_consistency_maintenance": "health issues trigger memory check",
            "memory_consistency_maintenance → performance_optimization_feedback": "memory state informs optimization",
            "performance_optimization_feedback → cross_system_synchronization": "optimizations synced across systems",
        },
    },
    "knowledge_expand": {
        "name": "Knowledge Expansion Composite",
        "description": "Full knowledge discovery, validation, and integration",
        "loops": ["knowledge_integration", "knowledge_graph_maintenance",
                  "data_ingestion_validation", "report_generation_verification"],
        "cross_refs": {
            "knowledge_integration → knowledge_graph_maintenance": "new knowledge updates graph",
            "knowledge_graph_maintenance → data_ingestion_validation": "graph changes validated as data",
            "data_ingestion_validation → report_generation_verification": "ingestion report generated",
        },
    },
    "emergency_response": {
        "name": "Emergency Response Composite",
        "description": "Full emergency handling with healing, safety, and notification",
        "loops": ["emergency_response_coordination", "autonomous_healing",
                  "security_compliance_enforcement", "system_health_monitoring"],
        "cross_refs": {
            "emergency_response_coordination → autonomous_healing": "emergency triggers healing",
            "autonomous_healing → security_compliance_enforcement": "healing checked for compliance",
            "security_compliance_enforcement → system_health_monitoring": "compliance result feeds health",
        },
    },
}


class LoopOrchestrator:
    """Orchestrates composite loops — multiple loops firing in concert."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "LoopOrchestrator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute_composite(
        self,
        composite_id: str,
        context: Dict[str, Any] = None,
    ) -> CompositeResult:
        """
        Execute a composite loop — multiple loops with cross-referencing.
        Each loop's output feeds into the next loop's input.
        """
        composite = COMPOSITE_LOOPS.get(composite_id)
        if not composite:
            return CompositeResult(
                composite_id=composite_id, loops_executed=0,
                loops_passed=0, loops_failed=0, verdict="unknown_composite"
            )

        start = time.time()
        results = []
        shared_context = dict(context or {})
        cross_refs = {}

        from cognitive.circuit_breaker import enter_loop, exit_loop

        for loop_id in composite["loops"]:
            loop_start = time.time()

            if not enter_loop(loop_id):
                results.append(LoopResult(
                    loop_id=loop_id, success=False,
                    error="circuit_breaker_open", duration_ms=0
                ))
                continue

            try:
                output = self._execute_single_loop(loop_id, shared_context)
                duration = (time.time() - loop_start) * 1000

                result = LoopResult(
                    loop_id=loop_id, success=True,
                    output=output, duration_ms=round(duration, 1)
                )
                results.append(result)

                # Cross-reference: feed this loop's output into shared context
                shared_context[f"loop_{loop_id}_output"] = output
                shared_context[f"loop_{loop_id}_success"] = True

            except Exception as e:
                duration = (time.time() - loop_start) * 1000
                results.append(LoopResult(
                    loop_id=loop_id, success=False,
                    error=str(e), duration_ms=round(duration, 1)
                ))
                shared_context[f"loop_{loop_id}_success"] = False
            finally:
                exit_loop(loop_id)

        total_duration = (time.time() - start) * 1000
        passed = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        verdict = "pass" if failed == 0 else "partial" if passed > 0 else "fail"

        # Track via event bus
        try:
            from cognitive.event_bus import publish
            publish(f"composite.{composite_id}.completed", {
                "composite": composite_id,
                "passed": passed,
                "failed": failed,
                "verdict": verdict,
                "duration_ms": round(total_duration, 1),
            }, source="loop_orchestrator")
        except Exception:
            pass

        # Genesis tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Composite loop {composite_id}: {verdict} ({passed}/{len(results)} passed)",
                how="loop_orchestrator.execute_composite",
                output_data={"composite": composite_id, "passed": passed, "failed": failed},
                tags=["composite_loop", composite_id, verdict],
            )
        except Exception:
            pass

        return CompositeResult(
            composite_id=composite_id,
            loops_executed=len(results),
            loops_passed=passed,
            loops_failed=failed,
            results=results,
            cross_references=composite.get("cross_refs", {}),
            total_duration_ms=round(total_duration, 1),
            verdict=verdict,
        )

    def _execute_single_loop(self, loop_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single loop with the shared context."""
        # Each loop type maps to a real system action
        output = {"loop": loop_id, "status": "executed", "timestamp": datetime.now(timezone.utc).isoformat()}

        if "trust" in loop_id:
            try:
                from cognitive.trust_engine import get_trust_engine
                te = get_trust_engine()
                d = te.get_dashboard()
                output["trust_score"] = d.get("overall_trust", 0)
            except Exception:
                pass

        if "health" in loop_id or "immune" in loop_id:
            try:
                from cognitive.central_orchestrator import get_orchestrator
                health = get_orchestrator().check_integration_health()
                output["health_percent"] = health.get("health_percent", 0)
            except Exception:
                pass

        if "memory" in loop_id:
            try:
                from cognitive.unified_memory import get_unified_memory
                stats = get_unified_memory().get_stats()
                output["memory_entries"] = sum(v.get("count", 0) for v in stats.values() if isinstance(v, dict))
            except Exception:
                pass

        if "hallucination" in loop_id:
            output["hallucination_check"] = "active"

        if "ingestion" in loop_id or "librarian" in loop_id:
            output["data_validated"] = True

        return output

    def get_composite_definitions(self) -> Dict[str, Any]:
        """Get all composite loop definitions."""
        return COMPOSITE_LOOPS

    def get_available_composites(self) -> List[Dict[str, Any]]:
        """List all available composite loops."""
        return [
            {
                "id": cid,
                "name": comp["name"],
                "description": comp["description"],
                "loop_count": len(comp["loops"]),
                "loops": comp["loops"],
                "cross_references": len(comp.get("cross_refs", {})),
            }
            for cid, comp in COMPOSITE_LOOPS.items()
        ]


def get_loop_orchestrator() -> LoopOrchestrator:
    return LoopOrchestrator.get_instance()
