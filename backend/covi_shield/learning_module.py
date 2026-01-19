"""
COVI-SHIELD Learning Module

Learns from verification outcomes to improve future performance.

Capabilities:
- Pattern mining from successful verifications
- Repair strategy optimization
- Cross-project transfer learning
- Knowledge base updates
"""

import hashlib
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from .models import (
    BugPattern,
    BugCategory,
    RiskLevel,
    VerificationResult,
    RepairSuggestion
)

logger = logging.getLogger(__name__)


# ============================================================================
# LEARNING DATA STRUCTURES
# ============================================================================

@dataclass
class LearningExample:
    """A learning example from verification/repair outcome."""
    example_id: str
    example_type: str  # verification, repair, pattern
    genesis_key_id: Optional[str] = None
    code_before: str = ""
    code_after: str = ""
    issue_pattern: Optional[str] = None
    repair_strategy: Optional[str] = None
    success: bool = False
    confidence: float = 0.0
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "example_id": self.example_id,
            "example_type": self.example_type,
            "genesis_key_id": self.genesis_key_id,
            "code_before": self.code_before[:500],
            "code_after": self.code_after[:500],
            "issue_pattern": self.issue_pattern,
            "repair_strategy": self.repair_strategy,
            "success": self.success,
            "confidence": self.confidence,
            "features": self.features,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PatternCandidate:
    """A candidate pattern discovered from learning."""
    candidate_id: str
    pattern_type: str
    description: str
    frequency: int = 0
    confidence: float = 0.0
    example_ids: List[str] = field(default_factory=list)
    code_snippets: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "example_count": len(self.example_ids),
            "created_at": self.created_at.isoformat()
        }


# ============================================================================
# LEARNING MODULE
# ============================================================================

class LearningModule:
    """
    COVI-SHIELD Learning Module.

    Learns from verification and repair outcomes to:
    - Discover new bug patterns
    - Improve repair strategies
    - Update effectiveness scores
    - Transfer knowledge across projects
    """

    def __init__(
        self,
        knowledge_base_path: Optional[Path] = None,
        memory_mesh_enabled: bool = True
    ):
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.memory_mesh_enabled = memory_mesh_enabled

        # Learning storage
        self.examples: List[LearningExample] = []
        self.pattern_candidates: Dict[str, PatternCandidate] = {}
        self.pattern_effectiveness: Dict[str, float] = {}
        self.repair_effectiveness: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Statistics
        self.stats = {
            "examples_collected": 0,
            "patterns_discovered": 0,
            "patterns_promoted": 0,
            "effectiveness_updates": 0,
            "learning_cycles": 0
        }

        logger.info("[COVI-SHIELD] Learning Module initialized")

    def record_verification_outcome(
        self,
        verification_result: VerificationResult,
        code: str,
        genesis_key_id: Optional[str] = None
    ) -> LearningExample:
        """
        Record a verification outcome for learning.

        Args:
            verification_result: Result of verification
            code: Code that was verified
            genesis_key_id: Associated Genesis Key

        Returns:
            LearningExample created
        """
        example_id = f"LE-{hashlib.sha256(code.encode()).hexdigest()[:12]}"

        example = LearningExample(
            example_id=example_id,
            example_type="verification",
            genesis_key_id=genesis_key_id or verification_result.genesis_key_id,
            code_before=code,
            success=verification_result.success,
            confidence=1.0 if verification_result.success else 0.5,
            features={
                "issues_found": verification_result.issues_found,
                "risk_level": verification_result.risk_level.value,
                "phase": verification_result.phase.value,
                "metrics": verification_result.metrics
            }
        )

        self.examples.append(example)
        self.stats["examples_collected"] += 1

        # Update pattern effectiveness
        for issue in verification_result.issues:
            pattern_id = issue.get("pattern_id", "")
            if pattern_id:
                self._update_pattern_effectiveness(pattern_id, detected=True)

        # Try to discover new patterns
        self._mine_patterns(verification_result.issues, code)

        logger.info(
            f"[COVI-SHIELD] Recorded verification outcome: {example_id}, "
            f"success={example.success}"
        )

        return example

    def record_repair_outcome(
        self,
        suggestion: RepairSuggestion,
        applied: bool,
        verification_passed: bool,
        genesis_key_id: Optional[str] = None
    ) -> LearningExample:
        """
        Record a repair outcome for learning.

        Args:
            suggestion: Repair suggestion
            applied: Whether fix was applied
            verification_passed: Whether verification passed after fix
            genesis_key_id: Associated Genesis Key

        Returns:
            LearningExample created
        """
        example_id = f"LE-repair-{suggestion.suggestion_id}"

        example = LearningExample(
            example_id=example_id,
            example_type="repair",
            genesis_key_id=genesis_key_id or suggestion.genesis_key_id,
            code_before=suggestion.original_code,
            code_after=suggestion.repaired_code,
            issue_pattern=suggestion.issue_id,
            repair_strategy=suggestion.strategy.value,
            success=applied and verification_passed,
            confidence=suggestion.confidence,
            features={
                "validation_passed": suggestion.validation_passed,
                "applied": applied,
                "verification_passed": verification_passed
            }
        )

        self.examples.append(example)
        self.stats["examples_collected"] += 1

        # Update repair effectiveness
        self._update_repair_effectiveness(
            pattern_id=suggestion.issue_id,
            strategy=suggestion.strategy.value,
            success=example.success
        )

        logger.info(
            f"[COVI-SHIELD] Recorded repair outcome: {example_id}, "
            f"success={example.success}"
        )

        return example

    def _update_pattern_effectiveness(
        self,
        pattern_id: str,
        detected: bool,
        false_positive: bool = False
    ) -> None:
        """Update pattern detection effectiveness."""
        current = self.pattern_effectiveness.get(pattern_id, 0.5)

        if detected and not false_positive:
            # True positive - increase effectiveness
            new_value = min(1.0, current + 0.05)
        elif false_positive:
            # False positive - decrease effectiveness
            new_value = max(0.0, current - 0.1)
        else:
            # Not detected - slight decrease
            new_value = max(0.0, current - 0.01)

        self.pattern_effectiveness[pattern_id] = new_value
        self.stats["effectiveness_updates"] += 1

    def _update_repair_effectiveness(
        self,
        pattern_id: str,
        strategy: str,
        success: bool
    ) -> None:
        """Update repair strategy effectiveness for a pattern."""
        current = self.repair_effectiveness[pattern_id].get(strategy, 0.5)

        if success:
            new_value = min(1.0, current + 0.1)
        else:
            new_value = max(0.0, current - 0.1)

        self.repair_effectiveness[pattern_id][strategy] = new_value
        self.stats["effectiveness_updates"] += 1

    def _mine_patterns(
        self,
        issues: List[Dict[str, Any]],
        code: str
    ) -> None:
        """Mine for new patterns from issues."""
        # Group issues by similarity
        for issue in issues:
            code_snippet = issue.get("code_snippet", "")
            if not code_snippet:
                continue

            # Create pattern signature
            signature = self._compute_pattern_signature(issue)

            if signature in self.pattern_candidates:
                # Update existing candidate
                candidate = self.pattern_candidates[signature]
                candidate.frequency += 1
                candidate.code_snippets.append(code_snippet)
                candidate.confidence = min(1.0, candidate.confidence + 0.1)

                # Check if ready for promotion
                if candidate.frequency >= 5 and candidate.confidence >= 0.7:
                    self._promote_pattern(candidate)
            else:
                # Create new candidate
                candidate = PatternCandidate(
                    candidate_id=f"PC-{signature[:12]}",
                    pattern_type=issue.get("category", "unknown"),
                    description=issue.get("description", ""),
                    frequency=1,
                    confidence=0.3,
                    code_snippets=[code_snippet]
                )
                self.pattern_candidates[signature] = candidate
                self.stats["patterns_discovered"] += 1

    def _compute_pattern_signature(self, issue: Dict[str, Any]) -> str:
        """Compute a signature for pattern matching."""
        # Normalize and hash relevant features
        features = [
            issue.get("pattern_id", ""),
            issue.get("category", ""),
            issue.get("name", ""),
        ]
        feature_str = "|".join(str(f) for f in features)
        return hashlib.sha256(feature_str.encode()).hexdigest()

    def _promote_pattern(self, candidate: PatternCandidate) -> Optional[BugPattern]:
        """Promote a candidate to a full pattern."""
        # Only promote high-confidence candidates
        if candidate.confidence < 0.7 or candidate.frequency < 5:
            return None

        pattern = BugPattern(
            pattern_id=f"LEARNED-{candidate.candidate_id}",
            name=f"Learned: {candidate.pattern_type}",
            description=candidate.description,
            category=BugCategory.LOGIC,  # Default
            severity=RiskLevel.MEDIUM,
            detection_logic="learned_pattern",
            effectiveness=candidate.confidence
        )

        self.stats["patterns_promoted"] += 1
        logger.info(
            f"[COVI-SHIELD] Promoted pattern: {pattern.pattern_id}, "
            f"frequency={candidate.frequency}"
        )

        return pattern

    def get_best_repair_strategy(
        self,
        pattern_id: str
    ) -> Tuple[str, float]:
        """Get the best repair strategy for a pattern."""
        strategies = self.repair_effectiveness.get(pattern_id, {})

        if not strategies:
            return "template", 0.5

        best_strategy = max(strategies.items(), key=lambda x: x[1])
        return best_strategy

    def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a full learning cycle.

        - Analyze recent examples
        - Update pattern effectiveness
        - Discover new patterns
        - Prune low-effectiveness patterns

        Returns:
            Learning cycle results
        """
        start_time = time.time()
        self.stats["learning_cycles"] += 1

        results = {
            "cycle_number": self.stats["learning_cycles"],
            "examples_processed": len(self.examples),
            "patterns_updated": 0,
            "patterns_discovered": 0,
            "patterns_pruned": 0
        }

        # Analyze recent examples
        recent_examples = self.examples[-100:]  # Last 100

        for example in recent_examples:
            if example.example_type == "verification":
                # Update pattern effectiveness based on verification outcomes
                for pattern_id in example.features.get("patterns_detected", []):
                    self._update_pattern_effectiveness(pattern_id, detected=True)
                    results["patterns_updated"] += 1

            elif example.example_type == "repair":
                # Update repair effectiveness
                if example.issue_pattern and example.repair_strategy:
                    self._update_repair_effectiveness(
                        example.issue_pattern,
                        example.repair_strategy,
                        example.success
                    )
                    results["patterns_updated"] += 1

        # Prune low-effectiveness patterns
        pruned = []
        for pattern_id, effectiveness in list(self.pattern_effectiveness.items()):
            if effectiveness < 0.1:
                pruned.append(pattern_id)
                del self.pattern_effectiveness[pattern_id]

        results["patterns_pruned"] = len(pruned)

        # Integrate with Memory Mesh if enabled
        if self.memory_mesh_enabled:
            self._sync_with_memory_mesh()

        results["duration_ms"] = (time.time() - start_time) * 1000

        logger.info(
            f"[COVI-SHIELD] Learning cycle {results['cycle_number']}: "
            f"{results['examples_processed']} examples, "
            f"{results['patterns_updated']} patterns updated, "
            f"{results['patterns_pruned']} pruned"
        )

        return results

    def _sync_with_memory_mesh(self) -> None:
        """Sync learning outcomes with GRACE Memory Mesh."""
        try:
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            from database.session import SessionLocal

            session = SessionLocal()
            memory_mesh = MemoryMeshIntegration(
                session=session,
                knowledge_base_path=self.knowledge_base_path
            )

            # Ingest recent learning examples
            for example in self.examples[-10:]:
                memory_mesh.ingest_learning_experience(
                    experience_type="covi_shield_" + example.example_type,
                    context={
                        "issue_pattern": example.issue_pattern,
                        "repair_strategy": example.repair_strategy
                    },
                    action_taken={"code_before": example.code_before[:200]},
                    outcome={
                        "success": example.success,
                        "confidence": example.confidence
                    },
                    source="covi_shield",
                    genesis_key_id=example.genesis_key_id
                )

            session.close()
            logger.info("[COVI-SHIELD] Synced with Memory Mesh")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD] Memory Mesh sync failed: {e}")

    def export_knowledge(self) -> Dict[str, Any]:
        """Export learned knowledge."""
        return {
            "pattern_effectiveness": self.pattern_effectiveness,
            "repair_effectiveness": dict(self.repair_effectiveness),
            "pattern_candidates": {
                k: v.to_dict() for k, v in self.pattern_candidates.items()
            },
            "examples_count": len(self.examples),
            "stats": self.stats,
            "exported_at": datetime.utcnow().isoformat()
        }

    def import_knowledge(self, knowledge: Dict[str, Any]) -> None:
        """Import knowledge from export."""
        if "pattern_effectiveness" in knowledge:
            self.pattern_effectiveness.update(knowledge["pattern_effectiveness"])

        if "repair_effectiveness" in knowledge:
            for pattern_id, strategies in knowledge["repair_effectiveness"].items():
                self.repair_effectiveness[pattern_id].update(strategies)

        logger.info("[COVI-SHIELD] Imported knowledge")

    def get_stats(self) -> Dict[str, Any]:
        """Get learning module statistics."""
        return {
            **self.stats,
            "examples_stored": len(self.examples),
            "pattern_candidates": len(self.pattern_candidates),
            "patterns_tracked": len(self.pattern_effectiveness)
        }
