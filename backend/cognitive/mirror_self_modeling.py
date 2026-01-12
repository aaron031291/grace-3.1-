"""
Mirror Self-Modeling System

The Mirror Agent continuously observes Grace's operations through Genesis Keys
and builds a self-model of system behavior, patterns, and improvement opportunities.

This creates true self-awareness by:
1. Observing ALL operations via Genesis Keys
2. Building behavioral models and patterns
3. Identifying inefficiencies and improvement opportunities
4. Feeding insights back to learning system
5. Enabling recursive self-improvement

The mirror creates a "reflection" of Grace that Grace can examine to understand
herself and improve continuously.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.learning_memory import LearningExample
from cognitive.memory_mesh_learner import get_memory_mesh_learner

logger = logging.getLogger(__name__)


# ======================================================================
# Behavioral Pattern Types
# ======================================================================

class PatternType:
    """Types of behavioral patterns the mirror can detect."""
    REPEATED_FAILURE = "repeated_failure"           # Same operation failing repeatedly
    SUCCESS_SEQUENCE = "success_sequence"           # Sequence that consistently succeeds
    LEARNING_PLATEAU = "learning_plateau"           # No improvement in learning
    EFFICIENCY_DROP = "efficiency_drop"             # Tasks taking longer over time
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"       # Unexpected behavior patterns
    IMPROVEMENT_OPPORTUNITY = "improvement_opportunity"  # Areas for optimization


# ======================================================================
# Mirror Self-Modeling System
# ======================================================================

class MirrorSelfModelingSystem:
    """
    Mirror Agent - Observes and models Grace's behavior.

    Creates a self-model by analyzing Genesis Keys to understand:
    - What Grace does (operation patterns)
    - How Grace learns (learning patterns)
    - Where Grace struggles (failure patterns)
    - How Grace improves (improvement patterns)

    The mirror provides continuous self-awareness and improvement suggestions.
    """

    def __init__(
        self,
        session: Session,
        observation_window_hours: int = 24,
        min_pattern_occurrences: int = 3
    ):
        self.session = session
        self.observation_window_hours = observation_window_hours
        self.min_pattern_occurrences = min_pattern_occurrences

        # Self-model state
        self.behavioral_patterns = []
        self.operation_history = defaultdict(list)
        self.learning_progress = {}
        self.improvement_suggestions = []

        # Memory mesh integration
        self.memory_learner = get_memory_mesh_learner(session)

        logger.info(
            f"[MIRROR] Self-modeling system initialized "
            f"(window={observation_window_hours}h, min_patterns={min_pattern_occurrences})"
        )

    # ======================================================================
    # Observation - Watch ALL Genesis Keys
    # ======================================================================

    def observe_recent_operations(self) -> Dict[str, Any]:
        """
        Observe recent operations by analyzing Genesis Keys.

        This is the mirror "looking at" what Grace has been doing.
        """
        logger.info("[MIRROR] Observing recent operations...")

        cutoff_time = datetime.utcnow() - timedelta(hours=self.observation_window_hours)

        # Query all Genesis Keys in observation window
        genesis_keys = self.session.query(GenesisKey).filter(
            GenesisKey.created_at >= cutoff_time
        ).order_by(GenesisKey.created_at.desc()).all()

        # Categorize operations
        operations_by_type = defaultdict(list)
        for gk in genesis_keys:
            operations_by_type[gk.key_type.value].append(gk)

        # Build observation summary
        observation = {
            "timestamp": datetime.utcnow().isoformat(),
            "observation_window_hours": self.observation_window_hours,
            "total_operations": len(genesis_keys),
            "operations_by_type": {
                key_type: len(gks)
                for key_type, gks in operations_by_type.items()
            },
            "recent_genesis_keys": genesis_keys[:50]  # Sample of recent keys
        }

        logger.info(
            f"[MIRROR] Observed {len(genesis_keys)} operations across "
            f"{len(operations_by_type)} operation types"
        )

        return observation

    # ======================================================================
    # Pattern Detection - Find Behavioral Patterns
    # ======================================================================

    def detect_behavioral_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect behavioral patterns from Genesis Keys.

        The mirror identifies patterns in Grace's behavior:
        - What keeps failing?
        - What keeps succeeding?
        - What's becoming less efficient?
        - What's improving?
        """
        logger.info("[MIRROR] Detecting behavioral patterns...")

        patterns = []

        # 1. Detect repeated failures
        failure_patterns = self._detect_repeated_failures()
        patterns.extend(failure_patterns)

        # 2. Detect success sequences
        success_patterns = self._detect_success_sequences()
        patterns.extend(success_patterns)

        # 3. Detect learning plateaus
        plateau_patterns = self._detect_learning_plateaus()
        patterns.extend(plateau_patterns)

        # 4. Detect efficiency drops
        efficiency_patterns = self._detect_efficiency_drops()
        patterns.extend(efficiency_patterns)

        # 5. Detect improvement opportunities
        improvement_patterns = self._detect_improvement_opportunities()
        patterns.extend(improvement_patterns)

        self.behavioral_patterns = patterns

        logger.info(f"[MIRROR] Detected {len(patterns)} behavioral patterns")

        return patterns

    def _detect_repeated_failures(self) -> List[Dict[str, Any]]:
        """Detect operations that keep failing."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.observation_window_hours)

        # Find Genesis Keys with ERROR type
        failures = self.session.query(GenesisKey).filter(
            and_(
                GenesisKey.created_at >= cutoff_time,
                GenesisKey.key_type == GenesisKeyType.ERROR
            )
        ).all()

        # Group by operation/topic
        failure_groups = defaultdict(list)
        for failure in failures:
            # Extract topic or operation identifier
            topic = None
            if failure.context_data:
                topic = failure.context_data.get("topic")
            if not topic:
                topic = failure.what_description[:50]  # Use description as topic

            failure_groups[topic].append(failure)

        # Identify repeated failures (3+ times)
        patterns = []
        for topic, failures_list in failure_groups.items():
            if len(failures_list) >= self.min_pattern_occurrences:
                patterns.append({
                    "pattern_type": PatternType.REPEATED_FAILURE,
                    "severity": "high" if len(failures_list) > 5 else "medium",
                    "topic": topic,
                    "occurrences": len(failures_list),
                    "evidence": [f.key_id for f in failures_list[:5]],
                    "first_seen": failures_list[-1].created_at.isoformat(),
                    "last_seen": failures_list[0].created_at.isoformat(),
                    "recommendation": (
                        f"This operation has failed {len(failures_list)} times. "
                        "Consider: (1) Reviewing approach, (2) Additional study, "
                        "(3) Breaking into smaller steps"
                    )
                })

        return patterns

    def _detect_success_sequences(self) -> List[Dict[str, Any]]:
        """Detect sequences of operations that consistently succeed."""
        # For now, return empty list since PRACTICE_OUTCOME type doesn't exist yet
        # This can be implemented when the learning system creates these types
        return []

    def _detect_learning_plateaus(self) -> List[Dict[str, Any]]:
        """Detect topics where learning has plateaued (no improvement)."""
        # Use memory mesh to identify topics with stagnant progress
        suggestions = self.memory_learner.get_learning_suggestions()

        patterns = []
        for gap in suggestions.get("knowledge_gaps", []):
            # Knowledge gap = high theory but low practice = learning plateau
            patterns.append({
                "pattern_type": PatternType.LEARNING_PLATEAU,
                "severity": "medium",
                "topic": gap["topic"],
                "occurrences": gap["example_count"],
                "evidence": [],
                "recommendation": (
                    f"Learning plateau detected. High theoretical knowledge "
                    f"(data_confidence={gap['avg_data_confidence']:.2f}) but low "
                    f"practical skill (operational_confidence={gap['avg_operational_confidence']:.2f}). "
                    "Needs more practice exercises."
                )
            })

        return patterns

    def _detect_efficiency_drops(self) -> List[Dict[str, Any]]:
        """Detect operations that are taking longer over time."""
        # This would analyze execution times from Genesis Keys
        # For now, return empty list (can be enhanced with actual timing data)
        return []

    def _detect_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """Detect areas where Grace could improve."""
        patterns = []

        # Use memory mesh to identify high-value topics worth improving
        suggestions = self.memory_learner.get_learning_suggestions()

        for high_value in suggestions.get("high_value_topics", []):
            if high_value["total_value"] > 50:  # Significant value
                patterns.append({
                    "pattern_type": PatternType.IMPROVEMENT_OPPORTUNITY,
                    "severity": "low",
                    "topic": high_value["topic"],
                    "occurrences": high_value["example_count"],
                    "evidence": [],
                    "recommendation": (
                        f"High-value improvement opportunity. This topic has "
                        f"{high_value['example_count']} examples with total value "
                        f"{high_value['total_value']}. Investing time here would "
                        "yield significant returns."
                    )
                })

        return patterns

    # ======================================================================
    # Self-Model Building
    # ======================================================================

    def build_self_model(self) -> Dict[str, Any]:
        """
        Build a comprehensive self-model of Grace's behavior.

        This is the mirror creating a "reflection" that Grace can examine.
        """
        logger.info("[MIRROR] Building self-model...")

        # Observe recent operations
        observation = self.observe_recent_operations()

        # Detect behavioral patterns
        patterns = self.detect_behavioral_patterns()

        # Analyze learning progress
        learning_analysis = self._analyze_learning_progress()

        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(patterns, learning_analysis)

        self.improvement_suggestions = suggestions

        self_model = {
            "timestamp": datetime.utcnow().isoformat(),
            "observation_window_hours": self.observation_window_hours,
            "operations_observed": observation["total_operations"],
            "operations_by_type": observation["operations_by_type"],
            "behavioral_patterns": {
                "total_detected": len(patterns),
                "by_type": self._count_patterns_by_type(patterns),
                "patterns": patterns
            },
            "learning_progress": learning_analysis,
            "improvement_suggestions": suggestions,
            "self_awareness_score": self._calculate_self_awareness_score(patterns, learning_analysis)
        }

        logger.info(
            f"[MIRROR] Self-model built: {len(patterns)} patterns, "
            f"{len(suggestions)} improvement suggestions"
        )

        return self_model

    def _analyze_learning_progress(self) -> Dict[str, Any]:
        """Analyze Grace's learning progress over time."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.observation_window_hours)

        # Query learning examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.created_at >= cutoff_time
        ).all()

        if not examples:
            return {
                "total_examples": 0,
                "avg_confidence": 0.0,
                "success_rate": 0.0,
                "topics_studied": 0
            }

        # Calculate metrics
        total = len(examples)
        # Use outcome_quality to determine success (> 0.7 = success) or example_type
        successes = sum(1 for e in examples if (
            e.outcome_quality > 0.7 or 
            e.example_type in ["success", "practice_outcome"] or
            (isinstance(e.actual_output, dict) and e.actual_output.get("success", False))
        ))
        # Use trust_score as confidence (since confidence_score doesn't exist)
        avg_confidence = sum(e.trust_score for e in examples) / total if total > 0 else 0.0
        # Use example_type as topic (since topic doesn't exist)
        topics = len(set(e.example_type for e in examples))

        return {
            "total_examples": total,
            "avg_confidence": round(avg_confidence, 3),
            "success_rate": round(successes / total, 3) if total > 0 else 0.0,
            "topics_studied": topics,
            "recent_topics": list(set(e.example_type for e in examples[-10:]))
        }

    def _generate_improvement_suggestions(
        self,
        patterns: List[Dict[str, Any]],
        learning_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable improvement suggestions from patterns."""
        suggestions = []

        # From repeated failures
        failure_patterns = [p for p in patterns if p["pattern_type"] == PatternType.REPEATED_FAILURE]
        for pattern in failure_patterns:
            suggestions.append({
                "priority": "high",
                "category": "failure_resolution",
                "topic": pattern["topic"],
                "action": "restudy_and_practice",
                "reason": pattern["recommendation"],
                "evidence_count": pattern["occurrences"]
            })

        # From learning plateaus
        plateau_patterns = [p for p in patterns if p["pattern_type"] == PatternType.LEARNING_PLATEAU]
        for pattern in plateau_patterns:
            suggestions.append({
                "priority": "medium",
                "category": "skill_development",
                "topic": pattern["topic"],
                "action": "intensive_practice",
                "reason": pattern["recommendation"],
                "evidence_count": pattern["occurrences"]
            })

        # From improvement opportunities
        opportunity_patterns = [p for p in patterns if p["pattern_type"] == PatternType.IMPROVEMENT_OPPORTUNITY]
        for pattern in opportunity_patterns:
            suggestions.append({
                "priority": "low",
                "category": "optimization",
                "topic": pattern["topic"],
                "action": "deepen_knowledge",
                "reason": pattern["recommendation"],
                "evidence_count": pattern["occurrences"]
            })

        # From success sequences (what to teach/reinforce)
        success_patterns = [p for p in patterns if p["pattern_type"] == PatternType.SUCCESS_SEQUENCE]
        for pattern in success_patterns:
            suggestions.append({
                "priority": "low",
                "category": "mastery_reinforcement",
                "topic": pattern["topic"],
                "action": "teach_or_advance",
                "reason": pattern["recommendation"],
                "evidence_count": pattern["occurrences"]
            })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order[s["priority"]])

        return suggestions

    def _count_patterns_by_type(self, patterns: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count patterns by type."""
        counter = Counter(p["pattern_type"] for p in patterns)
        return dict(counter)

    def _calculate_self_awareness_score(
        self,
        patterns: List[Dict[str, Any]],
        learning_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate a self-awareness score (0.0-1.0).

        Higher score means Grace has better understanding of herself.
        """
        score = 0.0

        # More patterns detected = better self-awareness
        pattern_score = min(1.0, len(patterns) / 20)  # Cap at 20 patterns
        score += pattern_score * 0.3

        # More learning examples = more self-knowledge
        example_score = min(1.0, learning_analysis.get("total_examples", 0) / 100)
        score += example_score * 0.2

        # Higher success rate = better self-understanding
        success_score = learning_analysis.get("success_rate", 0.0)
        score += success_score * 0.3

        # More topics = broader self-knowledge
        topic_score = min(1.0, learning_analysis.get("topics_studied", 0) / 20)
        score += topic_score * 0.2

        return round(score, 3)

    # ======================================================================
    # Feedback Loop - Feed Insights to Learning System
    # ======================================================================

    def trigger_improvement_actions(
        self,
        learning_orchestrator=None
    ) -> Dict[str, Any]:
        """
        Trigger improvement actions based on self-model insights.

        This closes the loop: Mirror observes → Identifies issues → Triggers learning
        """
        logger.info("[MIRROR] Triggering improvement actions...")

        actions_triggered = []

        # Get top 3 priority suggestions
        top_suggestions = [
            s for s in self.improvement_suggestions
            if s["priority"] == "high"
        ][:3]

        for suggestion in top_suggestions:
            if suggestion["action"] == "restudy_and_practice":
                # Trigger study task for failed topic
                if learning_orchestrator:
                    task_id = learning_orchestrator.submit_study_task(
                        topic=suggestion["topic"],
                        learning_objectives=[
                            f"Restudy after {suggestion['evidence_count']} failures",
                            "Understand root cause of failures",
                            "Practice until success"
                        ],
                        priority=1
                    )
                    actions_triggered.append({
                        "action": "study_triggered",
                        "topic": suggestion["topic"],
                        "task_id": task_id
                    })

            elif suggestion["action"] == "intensive_practice":
                # Trigger practice task for plateau
                if learning_orchestrator:
                    task_id = learning_orchestrator.submit_practice_task(
                        topic=suggestion["topic"],
                        practice_type="intensive",
                        difficulty="medium",
                        priority=2
                    )
                    actions_triggered.append({
                        "action": "practice_triggered",
                        "topic": suggestion["topic"],
                        "task_id": task_id
                    })

        logger.info(f"[MIRROR] Triggered {len(actions_triggered)} improvement actions")

        return {
            "actions_triggered": len(actions_triggered),
            "details": actions_triggered
        }

    # ======================================================================
    # Status & Reporting
    # ======================================================================

    def get_mirror_status(self) -> Dict[str, Any]:
        """Get current mirror status."""
        return {
            "patterns_detected": len(self.behavioral_patterns),
            "improvement_suggestions": len(self.improvement_suggestions),
            "observation_window_hours": self.observation_window_hours,
            "high_priority_suggestions": len([
                s for s in self.improvement_suggestions
                if s.get("priority") == "high"
            ])
        }

    def analyze_recent_operations(self, limit: int = 100) -> Dict[str, Any]:
        """
        Analyze recent operations and return improvement opportunities.

        This is the method called by ContinuousLearningOrchestrator to get
        improvement opportunities that can be proposed as experiments.

        Args:
            limit: Maximum number of operations to analyze

        Returns:
            Dictionary with improvement_opportunities list
        """
        logger.info(f"[MIRROR] Analyzing recent operations (limit={limit})...")

        # Build self-model which includes patterns and suggestions
        self_model = self.build_self_model()

        # Convert suggestions to improvement opportunities for sandbox experiments
        improvement_opportunities = []

        for suggestion in self.improvement_suggestions:
            # Map suggestion categories to experiment-friendly format
            category_map = {
                "failure_resolution": "error",
                "skill_development": "learning",
                "optimization": "performance",
                "mastery_reinforcement": "learning"
            }

            opportunity = {
                "name": f"Improve {suggestion.get('topic', 'unknown')}",
                "description": suggestion.get("reason", ""),
                "category": category_map.get(suggestion.get("category", ""), "improvement"),
                "motivation": f"Mirror detected {suggestion.get('evidence_count', 0)} occurrences requiring attention",
                "confidence": 0.6 if suggestion["priority"] == "high" else 0.4,
                "priority": suggestion["priority"],
                "action": suggestion.get("action", "study")
            }
            improvement_opportunities.append(opportunity)

        # Also check for proactive improvements even without failures
        if len(improvement_opportunities) == 0:
            # Generate seed opportunities based on system capabilities
            seed_opportunities = self._generate_seed_opportunities()
            improvement_opportunities.extend(seed_opportunities)

        logger.info(f"[MIRROR] Found {len(improvement_opportunities)} improvement opportunities")

        return {
            "operations_analyzed": self_model.get("operations_observed", 0),
            "patterns_detected": len(self.behavioral_patterns),
            "improvement_opportunities": improvement_opportunities,
            "self_awareness_score": self_model.get("self_awareness_score", 0.0)
        }

    def _generate_seed_opportunities(self) -> List[Dict[str, Any]]:
        """
        Generate seed improvement opportunities when no patterns are detected.

        This ensures the system has experiments to run even when starting fresh.
        """
        seed_opportunities = [
            {
                "name": "Optimize Retrieval Quality",
                "description": "Improve semantic search and document retrieval accuracy",
                "category": "retrieval",
                "motivation": "Core capability that benefits all operations",
                "confidence": 0.5,
                "priority": "medium",
                "action": "algorithm_improvement"
            },
            {
                "name": "Enhance Chunking Strategy",
                "description": "Improve document chunking for better context preservation",
                "category": "chunking",
                "motivation": "Better chunks lead to better retrieval and responses",
                "confidence": 0.5,
                "priority": "medium",
                "action": "algorithm_improvement"
            },
            {
                "name": "Improve Learning Retention",
                "description": "Enhance how knowledge is consolidated and retained over time",
                "category": "learning",
                "motivation": "Continuous learning requires effective retention",
                "confidence": 0.5,
                "priority": "medium",
                "action": "learning_enhancement"
            }
        ]

        logger.info(f"[MIRROR] Generated {len(seed_opportunities)} seed opportunities for cold start")
        return seed_opportunities


# ======================================================================
# Global Instance
# ======================================================================

_mirror_system: Optional[MirrorSelfModelingSystem] = None


def get_mirror_system(
    session: Session,
    observation_window_hours: int = 24,
    min_pattern_occurrences: int = 3
) -> MirrorSelfModelingSystem:
    """Get or create global mirror self-modeling system."""
    global _mirror_system

    if _mirror_system is None:
        _mirror_system = MirrorSelfModelingSystem(
            session=session,
            observation_window_hours=observation_window_hours,
            min_pattern_occurrences=min_pattern_occurrences
        )

    return _mirror_system
