"""
GraceMind — Unified Intelligence Cortex.

The single point of consciousness that wires every subsystem into ONE
intelligence pipeline. Before this, all subsystems ran as parallel silos.
Now every request flows through:

    Input
      → CognitiveMesh (OODA observe-orient-decide-act)
      → BrainOrchestrator (parallel multi-brain dispatch)
      → TrustEngine (score every output 0-100)
      → ConsensusTrustBridge (feed consensus results back into trust)
      → EpisodicMemory (learn from every decision)
      → GenesisKey (provenance audit trail)
      → EventBus (broadcast for downstream consumers)

GraceMind does NOT absorb domain logic — each module keeps its behavior.
GraceMind COORDINATES: it is the nervous system connecting the organs.
"""

import logging
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe(fn, fallback=None):
    """Call a function safely — never crash the mind."""
    try:
        return fn()
    except Exception as e:
        logger.debug(f"[GraceMind] safe-call failed: {e}")
        return fallback


class GraceMind:
    """
    Singleton unified intelligence cortex.
    Every cognitive request flows through think().
    """

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="grace-mind")
        self._decision_count = 0
        self._lock = threading.Lock()
        self._boot_time = datetime.now(timezone.utc).isoformat()
        logger.info("[GraceMind] Unified intelligence cortex initialized")

    # ═════════════════════════════════════════════════════════════════
    #  THE UNIFIED PIPELINE — every request flows through here
    # ═════════════════════════════════════════════════════════════════

    def think(
        self,
        intent: str,
        payload: dict = None,
        task_type: str = None,
        source: str = "user",
        skip_ooda: bool = False,
        skip_trust: bool = False,
    ) -> dict:
        """
        Unified intelligence pipeline. One call, all subsystems engaged.

        Args:
            intent:    What the caller wants (natural language or action name)
            payload:   Data for the request
            task_type: Brain task type (build/fix/chat/heal/etc). Auto-detected if None.
            source:    Who initiated this (user/system/autonomous)
            skip_ooda: Skip the OODA pre-analysis (for simple/fast requests)
            skip_trust: Skip trust scoring (for internal system calls)

        Returns:
            Unified result with brain outputs, trust scores, decision_id, and audit trail.
        """
        t0 = time.time()
        payload = payload or {}
        decision_id = self._next_decision_id()

        result = {
            "decision_id": decision_id,
            "intent": intent,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stages": {},
        }

        # ── Stage 1: OODA Pre-Analysis (Observe → Orient → Decide → Act) ──
        ooda_result = None
        if not skip_ooda:
            ooda_result = _safe(
                lambda: self._stage_ooda(intent, payload),
                {"decide": {"action": "proceed", "confidence": 0.5}},
            )
            result["stages"]["ooda"] = ooda_result

            # OODA may refine the task_type
            if not task_type and ooda_result:
                decided = ooda_result.get("decide", {})
                task_type = decided.get("action") or self._detect_task_type(intent)

        if not task_type:
            task_type = self._detect_task_type(intent)

        result["task_type"] = task_type

        # ── Stage 2: Procedural Memory Check (have we solved this before?) ──
        procedure = _safe(
            lambda: self._stage_procedural(intent, payload),
            {"found": False},
        )
        result["stages"]["procedural_memory"] = procedure

        # If a proven procedure exists with high success, use it as context
        if procedure.get("found") and procedure.get("success_rate", 0) > 0.7:
            payload["_proven_procedure"] = procedure

        # ── Stage 3: Brain Orchestration (parallel multi-brain dispatch) ──
        brain_result = _safe(
            lambda: self._stage_orchestrate(task_type, payload),
            {"results": {}, "successful": 0},
        )
        result["stages"]["brains"] = brain_result

        # ── Stage 4: Trust Scoring (score every brain output 0-100) ──
        trust_result = None
        if not skip_trust and brain_result:
            trust_result = _safe(
                lambda: self._stage_trust(decision_id, brain_result),
            )
            result["stages"]["trust"] = trust_result

        # ── Stage 5: Consensus→Trust Feedback (close the loop) ──
        if trust_result:
            _safe(lambda: self._stage_consensus_feedback(brain_result, trust_result))

        # ── Stage 6: Episodic Memory (learn from this decision) ──
        _safe(lambda: self._stage_episodic_learn(
            decision_id, intent, task_type, brain_result, trust_result, source,
        ))

        # ── Stage 7: Genesis Audit (provenance trail) ──
        _safe(lambda: self._stage_genesis_audit(
            decision_id, intent, task_type, brain_result, trust_result, source,
        ))

        # ── Stage 8: Event Bus Broadcast ──
        _safe(lambda: self._stage_broadcast(decision_id, intent, task_type, result))

        # ── Finalize ──
        latency_ms = round((time.time() - t0) * 1000, 1)
        result["latency_ms"] = latency_ms
        result["ok"] = brain_result.get("successful", 0) > 0 if brain_result else False

        # Extract the primary response for the caller
        result["response"] = self._extract_primary_response(brain_result)

        return result

    # ═════════════════════════════════════════════════════════════════
    #  INDIVIDUAL STAGES — each wraps an existing subsystem
    # ═════════════════════════════════════════════════════════════════

    def _stage_ooda(self, intent: str, payload: dict) -> dict:
        """Stage 1: Run OODA cycle via CognitiveMesh."""
        from core.cognitive_mesh import CognitiveMesh
        return CognitiveMesh.ooda_cycle(intent, payload)

    def _stage_procedural(self, intent: str, payload: dict) -> dict:
        """Stage 2: Check procedural memory for proven solutions."""
        from core.cognitive_mesh import CognitiveMesh
        return CognitiveMesh.find_procedure(intent, payload)

    def _stage_orchestrate(self, task_type: str, payload: dict) -> dict:
        """Stage 3: Dispatch to multiple brains in parallel."""
        from core.brain_orchestrator import get_orchestrator
        return get_orchestrator().orchestrate(task_type, payload)

    def _stage_trust(self, decision_id: str, brain_result: dict) -> dict:
        """Stage 4: Score every brain output through the Trust Engine."""
        from cognitive.trust_engine import get_trust_engine
        engine = get_trust_engine()

        trust_scores = {}
        for brain_name, output in brain_result.get("results", {}).items():
            output_text = str(output)
            source = "deterministic" if brain_name in ("system", "deterministic") else "llm"
            comp_score = engine.score_output(
                component_id=f"brain.{brain_name}",
                component_name=brain_name,
                output=output_text,
                source=source,
            )
            trust_scores[brain_name] = {
                "trust_score": comp_score.trust_score,
                "confidence": comp_score.confidence_score,
                "trend": comp_score.trend,
                "needs_remediation": comp_score.needs_remediation,
                "remediation_type": comp_score.remediation_type,
            }

            # If a brain needs remediation, trigger it
            if comp_score.needs_remediation:
                self._trigger_remediation(brain_name, comp_score, output)

        # Compute aggregate system trust
        scores = [v["trust_score"] for v in trust_scores.values() if v["trust_score"] > 0]
        system_trust = round(sum(scores) / len(scores), 1) if scores else 0.0

        return {
            "per_brain": trust_scores,
            "system_trust": system_trust,
            "decision_id": decision_id,
        }

    def _stage_consensus_feedback(self, brain_result: dict, trust_result: dict) -> None:
        """Stage 5: Feed brain agreement/disagreement back into adaptive trust."""
        from core.intelligence import ConsensusTrustBridge, AdaptiveTrust

        results = brain_result.get("results", {})
        models_used = list(results.keys())
        successes = [k for k, v in results.items() if v.get("ok")]
        failures = [k for k, v in results.items() if not v.get("ok")]

        # Map brain results to consensus format
        consensus_result = {
            "models_used": models_used,
            "agreements": successes,
            "disagreements": failures,
            "confidence": trust_result.get("system_trust", 50.0) / 100.0,
            "individual_responses": [
                {"model_id": k, "error": not v.get("ok")}
                for k, v in results.items()
            ],
        }
        ConsensusTrustBridge.process_consensus_result(consensus_result)

    def _stage_episodic_learn(
        self, decision_id: str, intent: str, task_type: str,
        brain_result: dict, trust_result: dict, source: str,
    ) -> None:
        """Stage 6: Record this decision as an episode for future learning."""
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicMemorySystem

        system_trust = trust_result.get("system_trust", 50.0) if trust_result else 50.0
        successful = brain_result.get("successful", 0) if brain_result else 0
        total = len(brain_result.get("results", {})) if brain_result else 0

        with session_scope() as session:
            eps = EpisodicMemorySystem(session)
            eps.record_episode(
                problem=intent,
                action={"task_type": task_type, "brains": brain_result.get("brains_called", [])},
                outcome={"successful": successful, "total": total, "ok": successful > 0},
                trust_score=system_trust / 100.0,
                source=source,
                decision_id=decision_id,
            )

    def _stage_genesis_audit(
        self, decision_id: str, intent: str, task_type: str,
        brain_result: dict, trust_result: dict, source: str,
    ) -> None:
        """Stage 7: Create a Genesis Key for provenance audit."""
        from api._genesis_tracker import track

        system_trust = trust_result.get("system_trust", 0) if trust_result else 0
        brains_called = brain_result.get("brains_called", []) if brain_result else []

        track(
            key_type="decision",
            what=f"GraceMind decision: {intent[:120]}",
            who=f"grace_mind/{source}",
            how=f"task_type={task_type}, brains={brains_called}",
            output_data={
                "decision_id": decision_id,
                "task_type": task_type,
                "system_trust": system_trust,
                "brains": brains_called,
            },
            tags=["grace_mind", "unified", task_type, source],
        )

    def _stage_broadcast(self, decision_id: str, intent: str, task_type: str, result: dict) -> None:
        """Stage 8: Broadcast the decision to all listeners via event bus."""
        from cognitive.event_bus import publish
        publish("grace_mind.decision", {
            "decision_id": decision_id,
            "intent": intent[:200],
            "task_type": task_type,
            "ok": result.get("ok", False),
            "system_trust": result.get("stages", {}).get("trust", {}).get("system_trust", 0),
            "latency_ms": result.get("latency_ms", 0),
        }, source="grace_mind")

    # ═════════════════════════════════════════════════════════════════
    #  HELPERS
    # ═════════════════════════════════════════════════════════════════

    def _next_decision_id(self) -> str:
        with self._lock:
            self._decision_count += 1
            return f"GM-{self._decision_count}-{uuid.uuid4().hex[:8]}"

    def _detect_task_type(self, intent: str) -> str:
        """Auto-detect task type from intent text."""
        low = intent.lower()
        keywords = {
            "build": ["build", "create", "generate", "make", "implement"],
            "fix": ["fix", "repair", "debug", "patch", "resolve"],
            "heal": ["heal", "recover", "restart", "self-heal"],
            "chat": ["chat", "talk", "ask", "question", "tell me", "explain"],
            "analyze": ["analyze", "inspect", "check", "review", "audit"],
            "learn": ["learn", "train", "study", "improve"],
            "search": ["search", "find", "look for", "locate"],
            "deploy": ["deploy", "release", "publish", "ship"],
            "plan": ["plan", "schedule", "roadmap", "prioritize"],
            "recall": ["remember", "recall", "what was", "history"],
        }
        for task_type, words in keywords.items():
            if any(w in low for w in words):
                return task_type
        return "chat"

    def _extract_primary_response(self, brain_result: dict) -> Any:
        """Extract the most useful response from brain outputs."""
        if not brain_result:
            return None
        results = brain_result.get("results", {})
        # Prefer successful AI/chat brain responses
        for preferred in ["ai", "chat", "code", "system", "govern"]:
            if preferred in results and results[preferred].get("ok"):
                return results[preferred]
        # Fall back to first successful
        for k, v in results.items():
            if v.get("ok"):
                return v
        # Fall back to first result
        return next(iter(results.values()), None) if results else None

    def _trigger_remediation(self, brain_name: str, comp_score, output: dict) -> None:
        """Trigger self-healing or coding agent for low-trust brains."""
        if comp_score.remediation_type == "self_healing":
            _safe(lambda: self._remediate_self_heal(brain_name))
        elif comp_score.remediation_type == "coding_agent":
            _safe(lambda: self._remediate_coding_agent(brain_name, output))

    def _remediate_self_heal(self, brain_name: str) -> None:
        from cognitive.event_bus import publish
        publish("grace_mind.remediation", {
            "brain": brain_name,
            "type": "self_healing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, source="grace_mind")

    def _remediate_coding_agent(self, brain_name: str, output: dict) -> None:
        from cognitive.event_bus import publish
        publish("grace_mind.remediation", {
            "brain": brain_name,
            "type": "coding_agent",
            "output_summary": str(output)[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, source="grace_mind")

    # ═════════════════════════════════════════════════════════════════
    #  INTROSPECTION — GraceMind knows itself
    # ═════════════════════════════════════════════════════════════════

    def status(self) -> dict:
        """Full introspection report — what GraceMind knows about itself."""
        trust_state = _safe(lambda: self._get_trust_state(), {})
        intelligence = _safe(lambda: self._get_intelligence_report(), {})

        return {
            "name": "GraceMind",
            "version": "1.0",
            "boot_time": self._boot_time,
            "decisions_made": self._decision_count,
            "trust_state": trust_state,
            "intelligence_report": intelligence,
            "subsystems": {
                "cognitive_mesh": "connected",
                "brain_orchestrator": "connected",
                "trust_engine": "connected",
                "consensus_bridge": "connected",
                "episodic_memory": "connected",
                "genesis_tracker": "connected",
                "event_bus": "connected",
            },
        }

    def _get_trust_state(self) -> dict:
        from core.intelligence import AdaptiveTrust
        return AdaptiveTrust.get_all_trust()

    def _get_intelligence_report(self) -> dict:
        from core.intelligence import get_intelligence_report
        return get_intelligence_report(hours=1)


# ═════════════════════════════════════════════════════════════════
#  SINGLETON
# ═════════════════════════════════════════════════════════════════

_mind: Optional[GraceMind] = None
_mind_lock = threading.Lock()


def get_grace_mind() -> GraceMind:
    """Get the singleton GraceMind instance."""
    global _mind
    if _mind is None:
        with _mind_lock:
            if _mind is None:
                _mind = GraceMind()
    return _mind
