"""
Grace Brain - READ-ONLY Intelligence Layer

Kimi is another brain. She does NOT execute anything.
She READS Grace's cognitive systems, ANALYZES problems,
and produces INSTRUCTIONS that Grace then verifies and executes.

Architecture:
    ┌──────────────────────────────────────────────────────┐
    │                    KIMI (READ-ONLY)                   │
    │                                                       │
    │  Reads:                     Produces:                │
    │  - Self-Mirroring          - Diagnosis               │
    │  - Self-Modeling           - Instructions             │
    │  - Time Sense / OODA       - Fix Recommendations     │
    │  - Self-Healing state      - Learning Priorities      │
    │  - Learning Progress       - Pattern Observations     │
    │  - Diagnostic Machine      - Architecture Suggestions │
    │  - Knowledge Base                                     │
    │                                                       │
    └───────────────────────┬──────────────────────────────┘
                            │ Instructions (read-only output)
                            ▼
    ┌──────────────────────────────────────────────────────┐
    │                 GRACE (VERIFIES & EXECUTES)           │
    │                                                       │
    │  1. Receives Grace's instructions                     │
    │  2. Runs through OODA loop                           │
    │  3. Verifies via governance/trust                    │
    │  4. Executes via execution bridge                    │
    │  5. Reports results back                             │
    │                                                       │
    └──────────────────────────────────────────────────────┘
                            │
                            ▼
              Tracker records everything for learning

Kimi connects to these Grace subsystems (READ-ONLY):
  - MirrorSelfModelingSystem: What Grace has been doing, behavioral patterns
  - OODA Loop: Current phase, decision history
  - Self-Healing: Current health, detected issues, healing history
  - Learning Systems: Progress, efficiency, knowledge gaps
  - Diagnostic Machine: Sensor data, interpretations, judgements
  - Knowledge Base: What Grace knows
  - Memory Mesh: Episodic, procedural, conceptual memory
"""

import logging
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from cognitive.llm_interaction_tracker import get_llm_interaction_tracker

logger = logging.getLogger(__name__)


class InstructionType(str, Enum):
    """Types of instructions Kimi can produce."""
    FIX = "fix"
    REFACTOR = "refactor"
    CREATE = "create"
    DELETE = "delete"
    CONFIGURE = "configure"
    HEAL = "heal"
    LEARN = "learn"
    INGEST = "ingest"
    DEPLOY = "deploy"
    TEST = "test"
    INVESTIGATE = "investigate"
    OBSERVE = "observe"


class InstructionPriority(str, Enum):
    """Priority of an instruction."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class GraceDiagnosis:
    """
    Grace's diagnosis of the system state.

    This is what Kimi produces after reading all of Grace's
    cognitive systems. It's an analysis, not an execution.
    """
    diagnosis_id: str
    timestamp: datetime

    system_health: Dict[str, Any]
    behavioral_patterns: List[Dict[str, Any]]
    detected_problems: List[Dict[str, Any]]
    learning_gaps: List[Dict[str, Any]]
    improvement_opportunities: List[Dict[str, Any]]

    overall_assessment: str
    confidence: float


@dataclass
class KimiInstruction:
    """
    A single instruction Kimi produces for Grace to execute.

    Kimi does NOT execute this. She passes it to Grace.
    Grace verifies it and decides whether/how to execute.
    """
    instruction_id: str
    instruction_type: InstructionType
    priority: InstructionPriority

    what: str
    why: str
    how: List[Dict[str, Any]]
    expected_outcome: str

    target_files: List[str] = field(default_factory=list)
    target_systems: List[str] = field(default_factory=list)

    preconditions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    rollback_plan: Optional[str] = None

    confidence: float = 0.0
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)

    source_diagnosis_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GraceInstructionSet:
    """
    A set of instructions Kimi produces from a single analysis session.

    This is the complete output of Grace's brain for a given request.
    Grace receives this, verifies each instruction, and executes.
    """
    session_id: str
    diagnosis: GraceDiagnosis
    instructions: List[KimiInstruction]
    summary: str
    total_confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GraceBrain:
    """
    Grace's read-only intelligence layer.

    Grace reads Grace's cognitive systems, analyzes the state,
    identifies problems, and produces instructions for Grace
    to verify and execute.

    Kimi NEVER executes. Kimi OBSERVES, ANALYZES, INSTRUCTS.
    """

    def __init__(self, session: Session, llm_client=None):
        self.session = session
        self.tracker = get_llm_interaction_tracker(session)
        self.llm_client = llm_client

        self._mirror_system = None
        self._diagnostic_engine = None
        self._learning_tracker = None
        self._pattern_learner = None
        self._tool_registry = None
        self._request_queue: List[Dict[str, Any]] = []
        self._max_concurrent = 3
        self._active_requests = 0

        self._session_history: List[GraceInstructionSet] = []

        # Load tool registry for instruction awareness
        try:
            from cognitive.kimi_tool_executor import TOOL_REGISTRY
            self._tool_registry = TOOL_REGISTRY
        except Exception:
            pass

        # Try to get LLM client if not provided
        if not self.llm_client:
            try:
                from ollama_client.client import get_ollama_client
                client = get_ollama_client()
                if client.is_running():
                    self.llm_client = client
            except Exception:
                pass

        logger.info(
            f"[GRACE-BRAIN] Read-only intelligence layer initialized "
            f"(LLM: {'connected' if self.llm_client else 'none - template composition only'})"
        )

    def connect_mirror(self, mirror_system):
        """Connect to Grace's self-mirroring system (READ-ONLY)."""
        self._mirror_system = mirror_system
        logger.info("[GRACE-BRAIN] Connected to MirrorSelfModelingSystem (read-only)")

    def connect_diagnostics(self, diagnostic_engine):
        """Connect to Grace's diagnostic machine (READ-ONLY)."""
        self._diagnostic_engine = diagnostic_engine
        logger.info("[GRACE-BRAIN] Connected to DiagnosticEngine (read-only)")

    def connect_learning(self, learning_tracker):
        """Connect to Grace's learning efficiency tracker (READ-ONLY)."""
        self._learning_tracker = learning_tracker
        logger.info("[GRACE-BRAIN] Connected to LearningEfficiencyTracker (read-only)")

    def connect_pattern_learner(self, pattern_learner):
        """Connect to LLM pattern learner (READ-ONLY)."""
        self._pattern_learner = pattern_learner
        logger.info("[GRACE-BRAIN] Connected to LLMPatternLearner (read-only)")

    # ==================================================================
    # READ: Observe Grace's cognitive systems
    # ==================================================================

    def read_system_state(self) -> Dict[str, Any]:
        """
        Read the current state of all Grace's cognitive systems.

        This is Grace's OBSERVE phase -- gathering data from all
        of Grace's internal systems without modifying anything.
        """
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mirror": self._read_mirror(),
            "diagnostics": self._read_diagnostics(),
            "learning": self._read_learning(),
            "patterns": self._read_patterns(),
            "interaction_stats": self._read_interaction_stats(),
            "active_tasks": self._read_active_tasks(),
            "system_integrity": self._read_system_integrity(),
            "handshake": self._read_handshake_status(),
            "unified_intelligence": self._read_unified_intelligence(),
            "weight_system": self._read_weight_system(),
            "security": self._read_security(),
        }

        logger.info("[GRACE-BRAIN] System state read complete")
        return state

    def _read_mirror(self) -> Dict[str, Any]:
        """Read from self-mirroring system."""
        if not self._mirror_system:
            return {"connected": False, "message": "Mirror system not connected"}

        try:
            self_model = self._mirror_system.build_self_model()
            return {
                "connected": True,
                "operations_observed": self_model.get("operations_observed", 0),
                "behavioral_patterns": self_model.get("behavioral_patterns", {}),
                "learning_progress": self_model.get("learning_progress", {}),
                "improvement_suggestions": self_model.get("improvement_suggestions", []),
                "self_awareness_score": self_model.get("self_awareness_score", 0),
            }
        except Exception as e:
            logger.warning(f"[GRACE-BRAIN] Error reading mirror: {e}")
            return {"connected": True, "error": str(e)}

    def _read_diagnostics(self) -> Dict[str, Any]:
        """Read from diagnostic machine."""
        if not self._diagnostic_engine:
            return {"connected": False, "message": "Diagnostic engine not connected"}

        try:
            return {
                "connected": True,
                "engine_state": getattr(self._diagnostic_engine, 'state', 'unknown'),
                "recent_cycles": getattr(self._diagnostic_engine, 'cycle_count', 0),
            }
        except Exception as e:
            logger.warning(f"[GRACE-BRAIN] Error reading diagnostics: {e}")
            return {"connected": True, "error": str(e)}

    def _read_learning(self) -> Dict[str, Any]:
        """Read from learning systems."""
        if not self._learning_tracker:
            return {"connected": False, "message": "Learning tracker not connected"}

        try:
            metrics = self._learning_tracker.export_metrics()
            return {
                "connected": True,
                "total_insights": metrics.get("summary", {}).get("total_insights", 0),
                "total_domains": metrics.get("summary", {}).get("total_domains", 0),
                "efficiency": metrics.get("efficiency", {}),
                "domain_efficiency": metrics.get("domain_efficiency", {}),
            }
        except Exception as e:
            logger.warning(f"[GRACE-BRAIN] Error reading learning: {e}")
            return {"connected": True, "error": str(e)}

    def _read_patterns(self) -> Dict[str, Any]:
        """Read from LLM pattern learner."""
        if not self._pattern_learner:
            return {"connected": False, "message": "Pattern learner not connected"}

        try:
            progress = self._pattern_learner.get_learning_progress()
            stats = self._pattern_learner.get_pattern_stats()
            return {
                "connected": True,
                "learning_stage": progress.get("learning_stage", "initial"),
                "autonomy_readiness": progress.get("autonomy_readiness", 0),
                "patterns_extracted": stats.get("total_patterns", 0),
                "replaceable_patterns": stats.get("replaceable_patterns", 0),
            }
        except Exception as e:
            logger.warning(f"[GRACE-BRAIN] Error reading patterns: {e}")
            return {"connected": True, "error": str(e)}

    def _read_active_tasks(self) -> Dict[str, Any]:
        """Read active task status from Task Completion Verifier."""
        try:
            from cognitive.task_completion_verifier import get_task_completion_verifier
            verifier = get_task_completion_verifier(self.session)
            tasks = verifier.get_all_tasks(limit=20)
            schedule = verifier.get_schedule()

            active = [t for t in tasks if t["status"] in ("in_progress", "verification", "planned")]
            stuck = [t for t in tasks if t["status"] == "failed_verification"]
            complete = [t for t in tasks if t["status"] == "complete"]

            return {
                "connected": True,
                "active_tasks": len(active),
                "stuck_tasks": len(stuck),
                "completed_tasks": len(complete),
                "behind_schedule": schedule.get("behind_schedule", 0),
                "at_risk": schedule.get("at_risk", 0),
                "tasks": active[:5],
                "stuck": stuck[:3],
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_handshake_status(self) -> Dict[str, Any]:
        """Read component handshake status -- who's alive, dead, degraded."""
        try:
            from genesis.component_registry import ComponentEntry
            components = self.session.query(ComponentEntry).filter(
                ComponentEntry.is_active == True
            ).all()

            alive = [c for c in components if c.status == "active"]
            dead = [c for c in components if c.status == "dead"]
            degraded = [c for c in components if c.status == "degraded"]

            return {
                "connected": True,
                "total_components": len(components),
                "alive": len(alive),
                "dead": len(dead),
                "degraded": len(degraded),
                "dead_components": [c.name for c in dead],
                "degraded_components": [c.name for c in degraded],
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_system_integrity(self) -> Dict[str, Any]:
        """Read system integrity status -- what's connected, broken, unknown."""
        try:
            from cognitive.system_integrity_monitor import get_system_integrity_monitor
            monitor = get_system_integrity_monitor(self.session)
            report = monitor.get_quick_status()
            return {
                "connected": True,
                "health_score": report.get("health_score", 0),
                "total_issues": report.get("total_issues", 0),
                "critical_issues": report.get("critical", 0),
                "connected_systems": report.get("connected_systems", 0),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_unified_intelligence(self) -> Dict[str, Any]:
        """Read unified intelligence chain performance."""
        try:
            from cognitive.unified_intelligence import get_unified_intelligence
            ui = get_unified_intelligence(self.session)
            stats = ui.get_stats()
            return {
                "connected": True,
                "total_queries": stats.get("total_queries", 0),
                "hit_rate": stats.get("hit_rate", 0),
                "layer_hits": stats.get("layer_hits", {}),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_weight_system(self) -> Dict[str, Any]:
        """Read weight system health."""
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            stats = ws.get_stats()
            return {
                "connected": True,
                "total_updates": stats.get("total_weight_updates", 0),
                "kpis": stats.get("current_kpis", {}),
                "recent_updates": len(stats.get("recent_updates", [])),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_security(self) -> Dict[str, Any]:
        """Read security configuration status."""
        try:
            from security.config import get_security_config
            config = get_security_config()
            return {
                "connected": True,
                "encryption_enabled": config.ENCRYPTION_ENABLED,
                "api_key_required": config.REQUIRE_API_KEY,
                "rate_limiting": config.RATE_LIMIT_ENABLED,
                "production_mode": config.PRODUCTION_MODE,
                "csrf_ready": True,
                "cors_origins": len(config.CORS_ALLOWED_ORIGINS),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _read_interaction_stats(self) -> Dict[str, Any]:
        """Read recent LLM interaction stats."""
        try:
            return self.tracker.get_interaction_stats(time_window_hours=24)
        except Exception as e:
            return {"error": str(e)}

    # ==================================================================
    # ANALYZE: Diagnose problems from observed state
    # ==================================================================

    def diagnose(self, user_request: Optional[str] = None) -> GraceDiagnosis:
        """
        Analyze Grace's current state and produce a diagnosis.

        Grace reads all systems, identifies problems, gaps,
        and opportunities. This is pure analysis -- no execution.
        """
        diagnosis_id = f"DIAG-{uuid.uuid4().hex[:12]}"
        state = self.read_system_state()

        detected_problems = self._identify_problems(state)
        learning_gaps = self._identify_learning_gaps(state)
        improvement_opps = self._identify_improvements(state)
        behavioral = self._analyze_behavioral_patterns(state)

        health = self._assess_overall_health(state)

        assessment = self._generate_assessment(
            state, detected_problems, learning_gaps, improvement_opps
        )

        confidence = self._calculate_diagnosis_confidence(state)

        diagnosis = GraceDiagnosis(
            diagnosis_id=diagnosis_id,
            timestamp=datetime.now(timezone.utc),
            system_health=health,
            behavioral_patterns=behavioral,
            detected_problems=detected_problems,
            learning_gaps=learning_gaps,
            improvement_opportunities=improvement_opps,
            overall_assessment=assessment,
            confidence=confidence,
        )

        # Track with Genesis Key for full provenance
        genesis_key_id = None
        try:
            from genesis.genesis_key_service import GenesisKeyService
            gk_service = GenesisKeyService(self.session)
            gk = gk_service.create_key(
                entity_type="kimi_diagnosis",
                entity_id=diagnosis_id,
                origin_source="grace_brain",
                origin_type="diagnosis",
                context_data={"problems": len(detected_problems), "gaps": len(learning_gaps)},
            )
            genesis_key_id = gk.key_id if gk else None
        except Exception:
            pass

        self.tracker.record_interaction(
            prompt=user_request or "System diagnosis requested",
            response=assessment,
            model_used="grace_brain",
            interaction_type="reasoning",
            outcome="success",
            confidence_score=confidence,
            reasoning_chain=[
                {"action": "read_state", "thought": "Reading all cognitive systems"},
                {"action": "identify_problems", "thought": f"Found {len(detected_problems)} problems"},
                {"action": "identify_gaps", "thought": f"Found {len(learning_gaps)} learning gaps"},
                {"action": "assess", "thought": assessment[:200]},
            ],
            genesis_key_id=genesis_key_id,
            metadata={"diagnosis_id": diagnosis_id},
        )

        logger.info(
            f"[GRACE-BRAIN] Diagnosis {diagnosis_id}: "
            f"{len(detected_problems)} problems, "
            f"{len(learning_gaps)} gaps, "
            f"confidence={confidence:.2f}"
        )

        return diagnosis

    def _identify_problems(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify problems from system state."""
        problems = []

        mirror = state.get("mirror", {})
        if mirror.get("connected"):
            patterns = mirror.get("behavioral_patterns", {})
            for pattern in patterns.get("patterns", []):
                if pattern.get("pattern_type") == "repeated_failure":
                    problems.append({
                        "source": "mirror",
                        "type": "repeated_failure",
                        "severity": pattern.get("severity", "medium"),
                        "topic": pattern.get("topic", "unknown"),
                        "occurrences": pattern.get("occurrences", 0),
                        "description": pattern.get("recommendation", ""),
                    })

        learning = state.get("learning", {})
        if learning.get("connected"):
            efficiency = learning.get("efficiency", {})
            if efficiency.get("hours_per_insight", 0) > 10:
                problems.append({
                    "source": "learning",
                    "type": "slow_learning",
                    "severity": "medium",
                    "description": (
                        f"Learning is slow: {efficiency.get('hours_per_insight', 0):.1f} "
                        "hours per insight. Consider more targeted study."
                    ),
                })

        stats = state.get("interaction_stats", {})
        outcomes = stats.get("outcomes", {})
        if outcomes.get("success_rate", 1) < 0.5 and outcomes.get("failure", 0) > 5:
            problems.append({
                "source": "interactions",
                "type": "high_failure_rate",
                "severity": "high",
                "description": (
                    f"High failure rate: {outcomes.get('success_rate', 0):.1%}. "
                    f"{outcomes.get('failure', 0)} failures in last 24h."
                ),
            })

        return problems

    def _identify_learning_gaps(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify learning gaps from state."""
        gaps = []

        patterns = state.get("patterns", {})
        if patterns.get("connected"):
            if patterns.get("autonomy_readiness", 0) < 0.3:
                gaps.append({
                    "area": "pattern_extraction",
                    "description": "Low autonomy readiness. More patterns needed from LLM interactions.",
                    "priority": "high",
                    "suggestion": "Run more diverse tasks through Kimi to build pattern library.",
                })

            if patterns.get("patterns_extracted", 0) < 5:
                gaps.append({
                    "area": "pattern_volume",
                    "description": "Too few patterns extracted. Need more interaction data.",
                    "priority": "high",
                    "suggestion": "Record more LLM interactions with reasoning chains.",
                })

        mirror = state.get("mirror", {})
        if mirror.get("connected"):
            progress = mirror.get("learning_progress", {})
            if progress.get("success_rate", 1) < 0.6:
                gaps.append({
                    "area": "practice",
                    "description": "Low practice success rate. Need more practice exercises.",
                    "priority": "medium",
                    "suggestion": "Focus practice on areas with lowest success rates.",
                })

        return gaps

    def _identify_improvements(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify improvement opportunities."""
        improvements = []

        mirror = state.get("mirror", {})
        if mirror.get("connected"):
            for suggestion in mirror.get("improvement_suggestions", []):
                improvements.append({
                    "source": "mirror",
                    "category": suggestion.get("category", "general"),
                    "topic": suggestion.get("topic", "unknown"),
                    "action": suggestion.get("action", "study"),
                    "reason": suggestion.get("reason", ""),
                    "priority": suggestion.get("priority", "medium"),
                })

        return improvements

    def _analyze_behavioral_patterns(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze behavioral patterns from mirror data."""
        mirror = state.get("mirror", {})
        if not mirror.get("connected"):
            return []

        patterns = mirror.get("behavioral_patterns", {})
        return patterns.get("patterns", [])[:20]

    def _assess_overall_health(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall system health."""
        scores = {}

        mirror = state.get("mirror", {})
        if mirror.get("connected"):
            scores["self_awareness"] = mirror.get("self_awareness_score", 0)

        patterns = state.get("patterns", {})
        if patterns.get("connected"):
            scores["autonomy_readiness"] = patterns.get("autonomy_readiness", 0)

        learning = state.get("learning", {})
        if learning.get("connected"):
            scores["learning_active"] = 1.0 if learning.get("total_insights", 0) > 0 else 0.0

        stats = state.get("interaction_stats", {})
        outcomes = stats.get("outcomes", {})
        scores["interaction_success"] = outcomes.get("success_rate", 0)

        if scores:
            overall = sum(scores.values()) / len(scores)
        else:
            overall = 0.0

        return {
            "overall_score": round(overall, 3),
            "component_scores": scores,
            "status": (
                "healthy" if overall >= 0.7
                else "degraded" if overall >= 0.4
                else "unhealthy"
            ),
        }

    def _generate_assessment(
        self,
        state: Dict[str, Any],
        problems: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        improvements: List[Dict[str, Any]],
    ) -> str:
        """Generate a human-readable assessment."""
        parts = []

        health = self._assess_overall_health(state)
        parts.append(f"System health: {health['status']} (score: {health['overall_score']:.2f})")

        if problems:
            critical = [p for p in problems if p.get("severity") == "high"]
            parts.append(
                f"Detected {len(problems)} problems "
                f"({len(critical)} high severity)"
            )

        if gaps:
            parts.append(f"Identified {len(gaps)} learning gaps")

        if improvements:
            parts.append(f"Found {len(improvements)} improvement opportunities")

        patterns = state.get("patterns", {})
        if patterns.get("connected"):
            parts.append(
                f"Autonomy readiness: {patterns.get('autonomy_readiness', 0):.1%}, "
                f"Stage: {patterns.get('learning_stage', 'initial')}"
            )

        return ". ".join(parts) + "."

    def _calculate_diagnosis_confidence(self, state: Dict[str, Any]) -> float:
        """Calculate confidence in the diagnosis."""
        connected = sum(
            1 for key in ["mirror", "diagnostics", "learning", "patterns"]
            if state.get(key, {}).get("connected", False)
        )
        connectivity_score = connected / 4

        has_data = 0
        if state.get("interaction_stats", {}).get("total", 0) > 0:
            has_data += 1
        if state.get("patterns", {}).get("patterns_extracted", 0) > 0:
            has_data += 1
        if state.get("mirror", {}).get("operations_observed", 0) > 0:
            has_data += 1
        data_score = has_data / 3

        return min(1.0, connectivity_score * 0.6 + data_score * 0.4)

    # ==================================================================
    # INSTRUCT: Produce instructions for Grace to execute
    # ==================================================================

    def produce_instructions(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GraceInstructionSet:
        """
        Analyze a user request and produce instructions for Grace.

        Kimi:
        1. Reads system state (OBSERVE)
        2. Diagnoses problems (ANALYZE)
        3. Produces instruction set (INSTRUCT)

        Grace then:
        4. Verifies each instruction (VERIFY)
        5. Executes via her systems (EXECUTE)
        """
        session_id = f"KIMI-{uuid.uuid4().hex[:12]}"

        diagnosis = self.diagnose(user_request)

        instructions = self._generate_instructions(
            user_request, diagnosis, context
        )

        total_confidence = (
            sum(i.confidence for i in instructions) / len(instructions)
            if instructions else 0
        )

        summary = (
            f"Kimi analyzed request: '{user_request[:100]}'. "
            f"Produced {len(instructions)} instructions. "
            f"System {diagnosis.system_health.get('status', 'unknown')}. "
            f"Confidence: {total_confidence:.2f}."
        )

        instruction_set = GraceInstructionSet(
            session_id=session_id,
            diagnosis=diagnosis,
            instructions=instructions,
            summary=summary,
            total_confidence=total_confidence,
        )

        self._session_history.append(instruction_set)

        self.tracker.record_interaction(
            prompt=user_request,
            response=summary,
            model_used="grace_brain",
            interaction_type="planning",
            delegation_type="grace_direct",
            outcome="success",
            confidence_score=total_confidence,
            reasoning_chain=[
                {"action": "observe", "thought": "Reading system state"},
                {"action": "diagnose", "thought": diagnosis.overall_assessment[:200]},
                {"action": "instruct", "thought": f"Produced {len(instructions)} instructions"},
            ],
            session_id=session_id,
            metadata={
                "diagnosis_id": diagnosis.diagnosis_id,
                "instruction_count": len(instructions),
                "problems_found": len(diagnosis.detected_problems),
            },
        )

        logger.info(
            f"[GRACE-BRAIN] Session {session_id}: "
            f"{len(instructions)} instructions produced, "
            f"confidence={total_confidence:.2f}"
        )

        return instruction_set

    def _generate_instructions(
        self,
        user_request: str,
        diagnosis: GraceDiagnosis,
        context: Optional[Dict[str, Any]],
    ) -> List[KimiInstruction]:
        """
        Generate specific instructions from diagnosis.

        Each instruction tells Grace WHAT to do, WHY, and HOW,
        but Kimi does NOT do it herself.
        """
        instructions = []

        request_lower = user_request.lower()
        task_type = self._classify_request(request_lower)

        if task_type == "coding":
            instructions.append(GraceInstruction(
                instruction_id=f"INS-{uuid.uuid4().hex[:8]}",
                instruction_type=InstructionType.CREATE if "create" in request_lower or "add" in request_lower
                    else InstructionType.FIX if "fix" in request_lower or "bug" in request_lower
                    else InstructionType.REFACTOR,
                priority=InstructionPriority.MEDIUM,
                what=f"Coding task: {user_request}",
                why="User requested coding work. Delegate to coding agent.",
                how=[
                    {"step": 1, "action": "delegate_to_coding_agent", "detail": user_request},
                    {"step": 2, "action": "run_tests", "detail": "Verify changes pass tests"},
                    {"step": 3, "action": "report_results", "detail": "Report outcome"},
                ],
                expected_outcome="Code changes implemented and tested",
                target_systems=["coding_agent", "execution_bridge"],
                confidence=0.8,
                reasoning_chain=[{"action": "classify", "thought": "This is a coding task"}],
                source_diagnosis_id=diagnosis.diagnosis_id,
            ))

        elif task_type == "healing":
            for problem in diagnosis.detected_problems:
                instructions.append(GraceInstruction(
                    instruction_id=f"INS-{uuid.uuid4().hex[:8]}",
                    instruction_type=InstructionType.HEAL,
                    priority=InstructionPriority.HIGH if problem.get("severity") == "high"
                        else InstructionPriority.MEDIUM,
                    what=f"Heal: {problem.get('description', 'Unknown problem')}",
                    why=f"Detected {problem.get('type', 'issue')} from {problem.get('source', 'unknown')}",
                    how=[
                        {"step": 1, "action": "run_diagnostic", "detail": "Full diagnostic cycle"},
                        {"step": 2, "action": "apply_healing", "detail": problem.get("type", "")},
                        {"step": 3, "action": "verify_healed", "detail": "Confirm issue resolved"},
                    ],
                    expected_outcome=f"Problem '{problem.get('type')}' resolved",
                    target_systems=["diagnostic_machine", "self_healing"],
                    risks=["Healing may cause brief service interruption"],
                    confidence=0.7,
                    source_diagnosis_id=diagnosis.diagnosis_id,
                ))

        elif task_type == "learning":
            for gap in diagnosis.learning_gaps:
                instructions.append(GraceInstruction(
                    instruction_id=f"INS-{uuid.uuid4().hex[:8]}",
                    instruction_type=InstructionType.LEARN,
                    priority=InstructionPriority.MEDIUM,
                    what=f"Learn: {gap.get('description', 'Unknown gap')}",
                    why=f"Learning gap in {gap.get('area', 'unknown')}",
                    how=[
                        {"step": 1, "action": "trigger_study", "detail": gap.get("suggestion", "")},
                        {"step": 2, "action": "extract_patterns", "detail": "Extract patterns from new data"},
                        {"step": 3, "action": "validate_learning", "detail": "Test that gap is closed"},
                    ],
                    expected_outcome=f"Learning gap in {gap.get('area')} addressed",
                    target_systems=["learning_system", "pattern_learner"],
                    confidence=0.6,
                    source_diagnosis_id=diagnosis.diagnosis_id,
                ))

        elif task_type == "investigation":
            instructions.append(GraceInstruction(
                instruction_id=f"INS-{uuid.uuid4().hex[:8]}",
                instruction_type=InstructionType.INVESTIGATE,
                priority=InstructionPriority.MEDIUM,
                what=f"Investigate: {user_request}",
                why="User asked for analysis/investigation",
                how=[
                    {"step": 1, "action": "query_knowledge_base", "detail": user_request},
                    {"step": 2, "action": "search_codebase", "detail": "Search for relevant code"},
                    {"step": 3, "action": "analyze_results", "detail": "Compile findings"},
                ],
                expected_outcome="Investigation results compiled",
                target_systems=["knowledge_base", "retrieval"],
                confidence=0.7,
                source_diagnosis_id=diagnosis.diagnosis_id,
            ))

        else:
            instructions.append(GraceInstruction(
                instruction_id=f"INS-{uuid.uuid4().hex[:8]}",
                instruction_type=InstructionType.OBSERVE,
                priority=InstructionPriority.MEDIUM,
                what=user_request,
                why="General request from user",
                how=[
                    {"step": 1, "action": "analyze_request", "detail": user_request},
                    {"step": 2, "action": "gather_context", "detail": "Collect relevant information"},
                    {"step": 3, "action": "execute_or_respond", "detail": "Take appropriate action"},
                ],
                expected_outcome="Request fulfilled",
                target_systems=["grace_core"],
                confidence=0.5,
                source_diagnosis_id=diagnosis.diagnosis_id,
            ))

        return instructions

    def _classify_request(self, request_lower: str) -> str:
        """Classify a user request into a category."""
        coding_words = ["write", "code", "implement", "create function", "fix bug",
                       "refactor", "add feature", "create class", "build"]
        healing_words = ["heal", "fix error", "repair", "recover", "health",
                        "diagnose", "broken", "not working", "crash"]
        learning_words = ["learn", "study", "practice", "train", "improve",
                         "knowledge", "pattern", "understand"]
        investigation_words = ["investigate", "analyze", "explain", "why",
                              "how does", "find out", "search", "query"]

        if any(w in request_lower for w in coding_words):
            return "coding"
        elif any(w in request_lower for w in healing_words):
            return "healing"
        elif any(w in request_lower for w in learning_words):
            return "learning"
        elif any(w in request_lower for w in investigation_words):
            return "investigation"
        return "general"

    # ==================================================================
    # STATUS
    # ==================================================================

    def compose_response(
        self,
        query: str,
        facts: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compose a coherent response from individual facts.

        This is the key capability that bridges the gap between
        'Grace has the facts' and 'Grace can answer the question.'

        Uses Kimi (LLM) to compose ONCE. Result is stored in
        distilled knowledge so next time it's served without LLM.

        Args:
            query: The user's question
            facts: Individual facts from compiled store / libraries / RAG
            context: Additional context

        Returns:
            Composed natural language response
        """
        if not facts:
            return ""

        # Build fact summary for composition
        fact_lines = []
        for f in facts[:10]:
            if isinstance(f, dict):
                subj = f.get("subject", f.get("entity_a", ""))
                pred = f.get("predicate", f.get("relation", ""))
                obj = f.get("object", f.get("object_value", f.get("entity_b", "")))
                if subj and obj:
                    fact_lines.append(f"- {subj} {pred} {obj}")
                elif f.get("text"):
                    fact_lines.append(f"- {f['text'][:200]}")
                elif f.get("response"):
                    fact_lines.append(f"- {f['response'][:200]}")

        if not fact_lines:
            return ". ".join(str(f) for f in facts[:5])

        facts_text = "\n".join(fact_lines)

        # Try local composition first (template-based, no LLM)
        if len(facts) <= 3:
            composed = ". ".join(line.lstrip("- ") for line in fact_lines)
            return composed

        # For complex composition, use LLM if available
        composition_prompt = f"Based on these facts, write a clear concise answer to: {query}\n\nFacts:\n{facts_text}\n\nAnswer:"

        composed = None

        if self.llm_client:
            try:
                # Use LLM for intelligent composition
                if hasattr(self.llm_client, 'chat'):
                    llm_response = self.llm_client.chat(
                        model=getattr(self.llm_client, 'default_model', 'mistral:7b'),
                        messages=[
                            {"role": "system", "content": "Compose a clear, concise answer from the given facts. Only use the facts provided."},
                            {"role": "user", "content": composition_prompt},
                        ],
                        stream=False,
                        temperature=0,  # Deterministic
                    )
                    if llm_response:
                        composed = llm_response
                elif hasattr(self.llm_client, 'generate'):
                    result = self.llm_client.generate(
                        prompt=composition_prompt,
                        task_type="reasoning",
                        system_prompt="Compose a clear answer from facts. Only use facts provided. Be concise.",
                    )
                    if result.get("success"):
                        composed = result.get("content", "")
            except Exception as e:
                logger.debug(f"[GRACE-COMPOSE] LLM composition failed: {e}")

        if not composed:
            # Template composition fallback (no LLM)
            composed = f"Based on available knowledge: {'. '.join(line.lstrip('- ') for line in fact_lines)}"

        self.tracker.record_interaction(
            prompt=composition_prompt,
            response=composed[:2000],
            model_used="grace_composer" if not self.llm_client else f"kimi_composer:llm",
            interaction_type="reasoning",
            outcome="success",
            confidence_score=0.8 if self.llm_client else 0.6,
            metadata={"composition": True, "fact_count": len(facts), "used_llm": bool(self.llm_client)},
        )

        # Store in distilled knowledge for next time
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            miner = get_llm_knowledge_miner(self.session)
            miner.store_interaction(
                query=query,
                response=composed,
                model_used="grace_composer",
                confidence=0.7,
            )
            self.session.commit()
        except Exception:
            pass

        return composed

    def consult(
        self,
        question: str,
        requester: str = "grace",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Any Grace subsystem can consult Grace Brain for reasoning.

        This is the bidirectional channel: Grace → Kimi.
        Diagnostic engine, self-healing, task verifier, etc.
        can all call this to get Grace's analysis.

        Rate-limited to prevent overwhelming the LLM.
        """
        if self._active_requests >= self._max_concurrent:
            return {
                "answered": False,
                "reason": "Kimi is busy (max concurrent requests reached)",
                "queued": True,
            }

        self._active_requests += 1

        try:
            # Read system state for context
            state = self.read_system_state()

            # Produce focused analysis
            diagnosis = self.diagnose(question)

            # If the question is about facts, try to compose from known facts
            try:
                from cognitive.knowledge_compiler import get_knowledge_compiler
                compiler = get_knowledge_compiler(self.session)

                import re
                terms = re.findall(r'\b[A-Z][a-z]+\b', question)[:3]
                all_facts = []
                for term in terms:
                    all_facts.extend(compiler.query_facts(subject=term, limit=3))

                if all_facts:
                    composed = self.compose_response(question, all_facts)
                    if composed:
                        return {
                            "answered": True,
                            "response": composed,
                            "source": "kimi_composed_from_facts",
                            "facts_used": len(all_facts),
                            "diagnosis": diagnosis.overall_assessment,
                        }
            except Exception:
                pass

            return {
                "answered": True,
                "response": diagnosis.overall_assessment,
                "source": "kimi_diagnosis",
                "problems": len(diagnosis.detected_problems),
                "suggestions": len(diagnosis.improvement_opportunities),
                "requester": requester,
            }

        finally:
            self._active_requests -= 1

    def audit_system(self) -> Dict[str, Any]:
        """
        Full system audit. Kimi scans for non-integrated components,
        missing connections, and knowledge retrieval gaps.

        This is what Kimi runs to keep the system aligned as it grows.
        """
        import os, re

        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self.read_system_state(),
            "disconnected": [],
            "knowledge_gaps": [],
            "integration_issues": [],
            "recommendations": [],
        }

        # Check each state source
        for key, value in audit["state"].items():
            if key == "timestamp":
                continue
            if isinstance(value, dict):
                if not value.get("connected", True):
                    audit["disconnected"].append({
                        "system": key,
                        "error": value.get("error", "not connected"),
                    })

        # Check knowledge store health
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)
            stats = compiler.get_stats()

            if stats.get("total_facts", 0) == 0:
                audit["knowledge_gaps"].append("Knowledge store has NO compiled facts")
            if stats.get("total_procedures", 0) == 0:
                audit["knowledge_gaps"].append("No compiled procedures")

        except Exception:
            audit["knowledge_gaps"].append("Cannot access knowledge compiler")

        # Check RAG readiness
        try:
            from models.database_models import Document, DocumentChunk
            docs = self.session.query(Document).count()
            chunks = self.session.query(DocumentChunk).count()
            if docs == 0:
                audit["integration_issues"].append("0 documents ingested - RAG has nothing to search")
            if chunks == 0:
                audit["integration_issues"].append("0 chunks in DB - no embeddings for vector search")
        except Exception:
            pass

        # Check security
        security = audit["state"].get("security", {})
        if not security.get("encryption_enabled"):
            audit["recommendations"].append("Enable data encryption (ENCRYPTION_ENABLED=true)")
        if not security.get("production_mode"):
            audit["recommendations"].append("Enable production mode for full security (PRODUCTION_MODE=true)")

        # Check learning pipeline
        learning = audit["state"].get("patterns", {})
        if learning.get("connected") and learning.get("autonomy_readiness", 0) < 0.1:
            audit["recommendations"].append("Autonomy readiness is very low - need more interaction data")

        # Check integrity
        integrity = audit["state"].get("system_integrity", {})
        if integrity.get("connected"):
            if integrity.get("total_issues", 0) > 5:
                audit["recommendations"].append(f"System has {integrity['total_issues']} integrity issues")

        # Score
        total_sources = 11
        connected = total_sources - len(audit["disconnected"])
        gaps = len(audit["knowledge_gaps"]) + len(audit["integration_issues"])
        health = max(0, (connected / total_sources * 70) - (gaps * 5) + 30)

        audit["health_score"] = round(min(100, health), 1)
        audit["connected_count"] = connected
        audit["total_sources"] = total_sources
        audit["summary"] = (
            f"Health: {audit['health_score']}%, "
            f"{connected}/{total_sources} connected, "
            f"{len(audit['disconnected'])} disconnected, "
            f"{len(audit['knowledge_gaps'])} knowledge gaps, "
            f"{len(audit['recommendations'])} recommendations"
        )

        # Track the audit
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "kimi_audit",
                audit["summary"],
                data={"health": audit["health_score"], "issues": gaps},
            )
        except Exception:
            pass

        return audit

    def get_status(self) -> Dict[str, Any]:
        """Get Kimi brain status."""
        return {
            "role": "read-only intelligence",
            "connected_systems": {
                "mirror": self._mirror_system is not None,
                "diagnostics": self._diagnostic_engine is not None,
                "learning": self._learning_tracker is not None,
                "patterns": self._pattern_learner is not None,
            },
            "sessions_completed": len(self._session_history),
            "recent_sessions": [
                {
                    "session_id": s.session_id,
                    "instructions": len(s.instructions),
                    "confidence": s.total_confidence,
                    "summary": s.summary[:200],
                    "created_at": s.created_at.isoformat(),
                }
                for s in self._session_history[-5:]
            ],
        }


_brain_instance: Optional[KimiBrain] = None


def get_kimi_brain(session: Session, llm_client=None) -> KimiBrain:
    """Get or create the Kimi brain singleton."""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = GraceBrain(session, llm_client=llm_client)
    return _brain_instance
