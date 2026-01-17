import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
class DiagnosticInsightType(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of diagnostic insights to feed into learning."""
    TEST_FAILURE_PATTERN = "test_failure_pattern"
    TEST_SUCCESS_PATTERN = "test_success_pattern"
    HEALING_SUCCESS = "healing_success"
    HEALING_FAILURE = "healing_failure"
    ANOMALY_DETECTED = "anomaly_detected"
    ANOMALY_RESOLVED = "anomaly_resolved"
    DRIFT_DETECTED = "drift_detected"
    INVARIANT_VIOLATION = "invariant_violation"
    FORENSIC_FINDING = "forensic_finding"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


@dataclass
class DiagnosticInsight:
    """An insight from diagnostics to store in learning memory."""
    insight_id: str
    insight_type: DiagnosticInsightType
    description: str
    context: Dict[str, Any]
    outcome: Dict[str, Any]
    confidence: float
    source_cycle_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    related_components: List[str] = field(default_factory=list)


@dataclass
class DiagnosticProcedure:
    """A learned diagnostic procedure to store in procedural memory."""
    procedure_id: str
    name: str
    description: str
    preconditions: Dict[str, Any]
    steps: List[Dict[str, Any]]
    expected_outcomes: Dict[str, Any]
    success_rate: float = 0.0
    times_applied: int = 0
    source_insights: List[str] = field(default_factory=list)


class LearningMemoryIntegration:
    """
    Integrates diagnostic insights with GRACE's Learning Memory.

    Converts diagnostic findings into learning examples that can be
    used to improve future diagnostics and system behavior.
    """

    def __init__(self, db_session=None):
        self.db_session = db_session
        self._insight_counter = 0

    def store_pattern_insight(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        cycle_id: str,
        confidence: float
    ) -> Optional[str]:
        """Store a detected pattern as a learning example."""
        self._insight_counter += 1
        insight_id = f"DIAG-INSIGHT-{self._insight_counter:06d}"

        try:
            # Try to use actual Learning Memory
            if self.db_session:
                try:
                    from cognitive.learning_memory import LearningExample
                    from database.session import get_session

                    example = LearningExample(
                        example_type="pattern",
                        input_context={
                            "pattern_type": pattern_type,
                            "source": "diagnostic_machine",
                            "cycle_id": cycle_id,
                        },
                        expected_output=pattern_data.get('expected', {}),
                        actual_output=pattern_data.get('actual', {}),
                        trust_score=confidence,
                        source_reliability=0.9,  # Diagnostic machine is reliable
                        outcome_quality=pattern_data.get('outcome_quality', 0.7),
                        source="diagnostic_machine",
                        genesis_key_id=pattern_data.get('genesis_key_id'),
                        example_metadata={
                            "insight_id": insight_id,
                            "pattern_data": pattern_data,
                        }
                    )

                    self.db_session.add(example)
                    self.db_session.commit()

                    logger.info(f"Stored pattern insight: {insight_id}")
                    return insight_id

                except Exception as e:
                    logger.debug(f"Could not store to Learning Memory DB: {e}")
                    # Fall through to file-based storage

            # File-based fallback
            return self._store_to_file(DiagnosticInsight(
                insight_id=insight_id,
                insight_type=DiagnosticInsightType.TEST_FAILURE_PATTERN if 'failure' in pattern_type.lower()
                    else DiagnosticInsightType.TEST_SUCCESS_PATTERN,
                description=pattern_data.get('description', f"Pattern: {pattern_type}"),
                context={"pattern_type": pattern_type, "cycle_id": cycle_id},
                outcome=pattern_data,
                confidence=confidence,
                source_cycle_id=cycle_id,
                related_components=pattern_data.get('affected_components', []),
            ))

        except Exception as e:
            logger.error(f"Failed to store pattern insight: {e}")
            return None

    def store_healing_insight(
        self,
        action_name: str,
        target_component: str,
        success: bool,
        details: Dict[str, Any],
        cycle_id: str
    ) -> Optional[str]:
        """Store a healing action result as a learning example."""
        self._insight_counter += 1
        insight_id = f"DIAG-INSIGHT-{self._insight_counter:06d}"

        insight_type = DiagnosticInsightType.HEALING_SUCCESS if success else DiagnosticInsightType.HEALING_FAILURE

        insight = DiagnosticInsight(
            insight_id=insight_id,
            insight_type=insight_type,
            description=f"Healing action '{action_name}' on {target_component} {'succeeded' if success else 'failed'}",
            context={
                "action_name": action_name,
                "target_component": target_component,
                "pre_conditions": details.get('pre_conditions', {}),
            },
            outcome={
                "success": success,
                "post_conditions": details.get('post_conditions', {}),
                "duration_ms": details.get('duration_ms', 0),
            },
            confidence=0.9 if success else 0.7,
            source_cycle_id=cycle_id,
            related_components=[target_component],
            tags=['healing', 'self-repair', action_name],
        )

        return self._store_to_file(insight)

    def store_anomaly_insight(
        self,
        anomaly_type: str,
        severity: float,
        description: str,
        resolution: Optional[Dict[str, Any]],
        cycle_id: str
    ) -> Optional[str]:
        """Store an anomaly detection as a learning example."""
        self._insight_counter += 1
        insight_id = f"DIAG-INSIGHT-{self._insight_counter:06d}"

        insight_type = DiagnosticInsightType.ANOMALY_RESOLVED if resolution else DiagnosticInsightType.ANOMALY_DETECTED

        insight = DiagnosticInsight(
            insight_id=insight_id,
            insight_type=insight_type,
            description=description,
            context={
                "anomaly_type": anomaly_type,
                "severity": severity,
            },
            outcome={
                "detected": True,
                "resolved": resolution is not None,
                "resolution": resolution or {},
            },
            confidence=severity,
            source_cycle_id=cycle_id,
            tags=['anomaly', anomaly_type],
        )

        return self._store_to_file(insight)

    def store_forensic_insight(
        self,
        finding_id: str,
        category: str,
        description: str,
        evidence: List[Dict],
        confidence: float,
        cycle_id: str
    ) -> Optional[str]:
        """Store a forensic finding as a learning example."""
        self._insight_counter += 1
        insight_id = f"DIAG-INSIGHT-{self._insight_counter:06d}"

        insight = DiagnosticInsight(
            insight_id=insight_id,
            insight_type=DiagnosticInsightType.FORENSIC_FINDING,
            description=description,
            context={
                "finding_id": finding_id,
                "category": category,
                "evidence_count": len(evidence),
            },
            outcome={
                "evidence": evidence,
                "root_cause_identified": category == "root_cause",
            },
            confidence=confidence,
            source_cycle_id=cycle_id,
            tags=['forensic', category],
        )

        return self._store_to_file(insight)

    def _store_to_file(self, insight: DiagnosticInsight) -> str:
        """Store insight to file-based learning memory."""
        try:
            learning_dir = Path(__file__).parent.parent / "learning_memory" / "diagnostic_insights"
            learning_dir.mkdir(parents=True, exist_ok=True)

            # Store as JSON
            file_path = learning_dir / f"{insight.insight_id}.json"
            with open(file_path, 'w') as f:
                json.dump({
                    "insight_id": insight.insight_id,
                    "insight_type": insight.insight_type.value,
                    "description": insight.description,
                    "context": insight.context,
                    "outcome": insight.outcome,
                    "confidence": insight.confidence,
                    "source_cycle_id": insight.source_cycle_id,
                    "timestamp": insight.timestamp.isoformat(),
                    "tags": insight.tags,
                    "related_components": insight.related_components,
                }, f, indent=2)

            logger.info(f"Stored insight to file: {insight.insight_id}")
            return insight.insight_id

        except Exception as e:
            logger.error(f"Failed to store insight to file: {e}")
            return insight.insight_id


class DecisionLogIntegration:
    """
    Integrates diagnostic decisions with GRACE's Decision Log.

    Ensures all diagnostic decisions are observable and auditable
    per Invariant 6: Observability Is Mandatory.
    """

    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs" / "diagnostic_decisions"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._decision_logger = None

        # Try to use actual DecisionLogger
        try:
            from cognitive.decision_log import DecisionLogger
            self._decision_logger = DecisionLogger(str(self.log_dir))
        except ImportError:
            logger.debug("DecisionLogger not available, using file-based logging")

    def log_diagnostic_decision(
        self,
        decision_id: str,
        decision_type: str,
        input_data: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        selected_action: Dict[str, Any],
        rationale: str,
        confidence: float
    ):
        """Log a diagnostic decision with full context."""
        decision_entry = {
            "event": "diagnostic_decision",
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "decision_type": decision_type,
            "input_summary": {
                "health_status": input_data.get('health_status', 'unknown'),
                "anomaly_count": input_data.get('anomaly_count', 0),
                "pattern_count": input_data.get('pattern_count', 0),
            },
            "alternatives_considered": len(alternatives),
            "alternatives": alternatives,
            "selected_action": selected_action,
            "rationale": rationale,
            "confidence": confidence,
        }

        self._write_decision(decision_entry)

    def log_healing_decision(
        self,
        decision_id: str,
        healing_action: str,
        target_component: str,
        justification: str,
        risk_assessment: Dict[str, Any],
        reversible: bool
    ):
        """Log a self-healing decision."""
        decision_entry = {
            "event": "healing_decision",
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "healing_action": healing_action,
            "target_component": target_component,
            "justification": justification,
            "risk_assessment": risk_assessment,
            "reversible": reversible,
            "invariant_4_compliant": reversible,  # INV-4: Ensure Reversibility
        }

        self._write_decision(decision_entry)

    def log_freeze_decision(
        self,
        decision_id: str,
        reason: str,
        affected_components: List[str],
        severity: float,
        human_override_available: bool
    ):
        """Log a system freeze decision."""
        decision_entry = {
            "event": "freeze_decision",
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "affected_components": affected_components,
            "severity": severity,
            "human_override_available": human_override_available,
            "invariant_2_compliant": human_override_available,  # INV-2: Preserve Human Override
        }

        self._write_decision(decision_entry)

    def _write_decision(self, entry: Dict[str, Any]):
        """Write decision to log file."""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"diagnostic_decisions_{today}.jsonl"

            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')

            logger.debug(f"Logged decision: {entry.get('decision_id')}")

        except Exception as e:
            logger.error(f"Failed to write decision log: {e}")


class MemoryMeshIntegration:
    """
    Integrates diagnostic patterns with GRACE's Memory Mesh.

    Stores diagnostic patterns in semantic memory for:
    - Pattern retrieval during future diagnostics
    - Cross-referencing with other system knowledge
    - Building diagnostic expertise over time
    """

    def __init__(self):
        self._memory_mesh = None

        # Try to use actual Memory Mesh
        try:
            from cognitive.memory_mesh_integration import MemoryMeshIntegrator
            self._memory_mesh = MemoryMeshIntegrator()
        except ImportError:
            logger.debug("MemoryMeshIntegrator not available, using local storage")

    def store_diagnostic_pattern(
        self,
        pattern_id: str,
        pattern_type: str,
        description: str,
        conditions: Dict[str, Any],
        actions: List[str],
        effectiveness: float
    ) -> Optional[str]:
        """Store a diagnostic pattern in memory mesh."""
        try:
            pattern_data = {
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
                "description": description,
                "conditions": conditions,
                "recommended_actions": actions,
                "effectiveness": effectiveness,
                "source": "diagnostic_machine",
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self._memory_mesh:
                # Use actual Memory Mesh
                return self._memory_mesh.store_pattern(pattern_data)

            # File-based fallback
            return self._store_pattern_to_file(pattern_data)

        except Exception as e:
            logger.error(f"Failed to store pattern in memory mesh: {e}")
            return None

    def retrieve_similar_patterns(
        self,
        current_conditions: Dict[str, Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve similar diagnostic patterns from memory mesh."""
        try:
            if self._memory_mesh:
                return self._memory_mesh.retrieve_similar(current_conditions, limit)

            # File-based fallback - simple keyword matching
            return self._retrieve_patterns_from_file(current_conditions, limit)

        except Exception as e:
            logger.error(f"Failed to retrieve patterns: {e}")
            return []

    def _store_pattern_to_file(self, pattern_data: Dict) -> str:
        """Store pattern to file."""
        try:
            pattern_dir = Path(__file__).parent.parent / "learning_memory" / "diagnostic_patterns"
            pattern_dir.mkdir(parents=True, exist_ok=True)

            pattern_id = pattern_data["pattern_id"]
            file_path = pattern_dir / f"{pattern_id}.json"

            with open(file_path, 'w') as f:
                json.dump(pattern_data, f, indent=2)

            return pattern_id

        except Exception as e:
            logger.error(f"Failed to store pattern to file: {e}")
            return pattern_data.get("pattern_id", "unknown")

    def _retrieve_patterns_from_file(
        self,
        conditions: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Retrieve patterns from file storage."""
        patterns = []
        try:
            pattern_dir = Path(__file__).parent.parent / "learning_memory" / "diagnostic_patterns"

            if not pattern_dir.exists():
                return []

            for file_path in pattern_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        pattern = json.load(f)
                        patterns.append(pattern)
                except Exception:
                    continue

            # Sort by effectiveness and return top N
            patterns.sort(key=lambda p: p.get('effectiveness', 0), reverse=True)
            return patterns[:limit]

        except Exception as e:
            logger.error(f"Failed to retrieve patterns from file: {e}")
            return []


class ProceduralMemoryIntegration:
    """
    Extracts and stores learned diagnostic procedures.

    Converts repeated diagnostic patterns into reusable procedures.
    """

    def __init__(self):
        self._procedure_counter = 0

    def extract_procedure_from_pattern(
        self,
        pattern_type: str,
        successful_actions: List[Dict[str, Any]],
        context: Dict[str, Any],
        success_rate: float
    ) -> Optional[DiagnosticProcedure]:
        """Extract a reusable procedure from a successful pattern."""
        if success_rate < 0.7:
            return None  # Only extract procedures with high success rate

        self._procedure_counter += 1
        procedure_id = f"DIAG-PROC-{self._procedure_counter:04d}"

        procedure = DiagnosticProcedure(
            procedure_id=procedure_id,
            name=f"Auto-learned: {pattern_type}",
            description=f"Automatically extracted procedure for handling {pattern_type}",
            preconditions=context,
            steps=[
                {
                    "step_number": i + 1,
                    "action": action.get('action_type', 'unknown'),
                    "parameters": action.get('parameters', {}),
                }
                for i, action in enumerate(successful_actions)
            ],
            expected_outcomes={
                "success_rate": success_rate,
                "typical_duration_ms": sum(a.get('duration_ms', 0) for a in successful_actions),
            },
            success_rate=success_rate,
            source_insights=[],
        )

        # Store procedure
        self._store_procedure(procedure)

        return procedure

    def _store_procedure(self, procedure: DiagnosticProcedure):
        """Store extracted procedure."""
        try:
            proc_dir = Path(__file__).parent.parent / "learning_memory" / "diagnostic_procedures"
            proc_dir.mkdir(parents=True, exist_ok=True)

            file_path = proc_dir / f"{procedure.procedure_id}.json"
            with open(file_path, 'w') as f:
                json.dump({
                    "procedure_id": procedure.procedure_id,
                    "name": procedure.name,
                    "description": procedure.description,
                    "preconditions": procedure.preconditions,
                    "steps": procedure.steps,
                    "expected_outcomes": procedure.expected_outcomes,
                    "success_rate": procedure.success_rate,
                    "times_applied": procedure.times_applied,
                    "timestamp": datetime.utcnow().isoformat(),
                }, f, indent=2)

            logger.info(f"Stored diagnostic procedure: {procedure.procedure_id}")

        except Exception as e:
            logger.error(f"Failed to store procedure: {e}")


class CognitiveIntegrationManager:
    """
    Main manager for all cognitive integrations.

    Provides a unified interface for the diagnostic machine to
    interact with GRACE's cognitive systems.
    """

    def __init__(self, db_session=None, log_dir: str = None):
        self.learning_memory = LearningMemoryIntegration(db_session)
        self.decision_log = DecisionLogIntegration(log_dir)
        self.memory_mesh = MemoryMeshIntegration()
        self.procedural_memory = ProceduralMemoryIntegration()

    def process_diagnostic_cycle(
        self,
        cycle_id: str,
        sensor_data: Dict[str, Any],
        interpreted_data: Dict[str, Any],
        judgement: Dict[str, Any],
        action_decision: Dict[str, Any]
    ):
        """Process a completed diagnostic cycle for learning."""
        try:
            # Store patterns as learning examples
            for pattern in interpreted_data.get('patterns', []):
                self.learning_memory.store_pattern_insight(
                    pattern_type=pattern.get('type', 'unknown'),
                    pattern_data=pattern,
                    cycle_id=cycle_id,
                    confidence=pattern.get('confidence', 0.5)
                )

            # Store forensic findings
            for finding in judgement.get('forensic_findings', []):
                self.learning_memory.store_forensic_insight(
                    finding_id=finding.get('finding_id', ''),
                    category=finding.get('category', 'unknown'),
                    description=finding.get('description', ''),
                    evidence=finding.get('evidence', []),
                    confidence=finding.get('confidence', 0.5),
                    cycle_id=cycle_id
                )

            # Log the diagnostic decision
            self.decision_log.log_diagnostic_decision(
                decision_id=action_decision.get('decision_id', cycle_id),
                decision_type=action_decision.get('action_type', 'unknown'),
                input_data={
                    'health_status': judgement.get('health', {}).get('status', 'unknown'),
                    'anomaly_count': len(interpreted_data.get('anomalies', [])),
                    'pattern_count': len(interpreted_data.get('patterns', [])),
                },
                alternatives=[],  # Could track alternatives if available
                selected_action={
                    'action': action_decision.get('action_type'),
                    'target': action_decision.get('target_components', []),
                },
                rationale=action_decision.get('reason', ''),
                confidence=action_decision.get('confidence', 0.5)
            )

            # Store successful patterns in memory mesh
            if judgement.get('health', {}).get('status') == 'healthy':
                for pattern in interpreted_data.get('patterns', []):
                    if pattern.get('type') == 'test_success_pattern':
                        self.memory_mesh.store_diagnostic_pattern(
                            pattern_id=f"PATTERN-{cycle_id}-{pattern.get('type')}",
                            pattern_type=pattern.get('type'),
                            description=pattern.get('description', ''),
                            conditions=sensor_data,
                            actions=[],
                            effectiveness=pattern.get('confidence', 0.5)
                        )

            logger.info(f"Processed diagnostic cycle {cycle_id} for learning")

        except Exception as e:
            logger.error(f"Failed to process cycle for learning: {e}")

    def retrieve_relevant_knowledge(
        self,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve relevant knowledge for current diagnostic context."""
        try:
            similar_patterns = self.memory_mesh.retrieve_similar_patterns(
                current_context, limit=5
            )

            return {
                "similar_patterns": similar_patterns,
                "suggested_actions": [
                    p.get('recommended_actions', [])
                    for p in similar_patterns
                ],
            }

        except Exception as e:
            logger.error(f"Failed to retrieve knowledge: {e}")
            return {"similar_patterns": [], "suggested_actions": []}


# Global instance
_cognitive_manager: Optional[CognitiveIntegrationManager] = None


def get_cognitive_manager() -> CognitiveIntegrationManager:
    """Get or create global cognitive integration manager."""
    global _cognitive_manager
    if _cognitive_manager is None:
        _cognitive_manager = CognitiveIntegrationManager()
    return _cognitive_manager
