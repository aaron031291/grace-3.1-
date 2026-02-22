"""
LLM Pattern Learner

Extracts reusable patterns from tracked LLM interactions to progressively
reduce dependency on external LLMs. This is the core "learning from Kimi"
system.

How it works:
1. Analyzes all recorded LLM interactions (from LLMInteractionTracker)
2. Identifies recurring reasoning patterns across similar tasks
3. Extracts deterministic action sequences from successful interactions
4. Builds a pattern library that Grace can use instead of calling the LLM
5. Validates patterns by comparing autonomous results to LLM results
6. Gradually expands the set of tasks Grace handles independently

Key Concepts:
- Pattern Signature: The abstract shape of a reasoning chain (action types)
- Pattern Confidence: How often this pattern leads to success
- Pattern Utility: How frequently this pattern is needed
- Replaceability Score: Whether Grace can handle this without an LLM

Classes:
- `LLMPatternLearner`

Key Methods:
- `extract_patterns()`
- `can_handle_autonomously()`
- `apply_pattern()`
- `get_pattern_stats()`
- `get_learning_progress()`
- `get_llm_pattern_learner()`
"""

import logging
import hashlib
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from models.llm_tracking_models import (
    LLMInteraction,
    ReasoningPath,
    ExtractedPattern,
    CodingTaskRecord,
    InteractionType,
    InteractionOutcome,
)

logger = logging.getLogger(__name__)


class LLMPatternLearner:
    """
    Learns patterns from LLM interactions to build autonomous capabilities.

    The pattern learner is Grace's way of "studying Kimi as a mentor."
    By observing how Kimi solves problems, Grace can learn to solve
    similar problems on her own.

    Learning Process:
    1. OBSERVE: Watch LLM interactions and reasoning paths
    2. ABSTRACT: Extract general patterns from specific interactions
    3. VALIDATE: Test patterns against new interactions
    4. APPLY: Use patterns to handle tasks autonomously
    5. REFINE: Update patterns based on outcomes
    """

    def __init__(
        self,
        session: Session,
        min_occurrences_for_pattern: int = 3,
        min_success_rate_for_pattern: float = 0.7,
        min_confidence_for_autonomous: float = 0.85,
    ):
        self.session = session
        self.min_occurrences = min_occurrences_for_pattern
        self.min_success_rate = min_success_rate_for_pattern
        self.min_confidence_autonomous = min_confidence_for_autonomous

        self._pattern_cache: Dict[str, ExtractedPattern] = {}
        self._applicability_cache: Dict[str, List[str]] = {}

        logger.info(
            f"[PATTERN-LEARNER] Initialized (min_occ={min_occurrences_for_pattern}, "
            f"min_success={min_success_rate_for_pattern}, "
            f"min_conf_auto={min_confidence_for_autonomous})"
        )

    def extract_patterns(
        self,
        time_window_hours: int = 168,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract patterns from recent LLM interactions.

        Scans reasoning paths and interactions to identify recurring
        patterns that can be codified for autonomous use.

        Returns:
            List of newly extracted or updated patterns
        """
        logger.info("[PATTERN-LEARNER] Extracting patterns from interactions...")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        paths = self.session.query(ReasoningPath).filter(
            ReasoningPath.created_at >= cutoff,
            ReasoningPath.times_seen >= self.min_occurrences,
        ).all()

        signature_groups = defaultdict(list)
        for path in paths:
            if path.pattern_signature:
                signature_groups[path.pattern_signature].append(path)

        new_patterns = []

        for signature, group_paths in signature_groups.items():
            if len(group_paths) < self.min_occurrences:
                continue

            total_seen = sum(p.times_seen for p in group_paths)
            total_succeeded = sum(p.times_succeeded for p in group_paths)
            total_failed = sum(p.times_failed for p in group_paths)
            total_attempts = total_succeeded + total_failed

            if total_attempts == 0:
                continue

            success_rate = total_succeeded / total_attempts

            if success_rate < self.min_success_rate:
                continue

            pattern = self._create_or_update_pattern(
                signature=signature,
                paths=group_paths,
                success_rate=success_rate,
                total_seen=total_seen,
            )

            if pattern:
                new_patterns.append(pattern)

        interaction_patterns = self._extract_interaction_level_patterns(cutoff)
        new_patterns.extend(interaction_patterns)

        logger.info(
            f"[PATTERN-LEARNER] Extracted {len(new_patterns)} patterns "
            f"from {len(paths)} reasoning paths"
        )

        return new_patterns

    def _create_or_update_pattern(
        self,
        signature: str,
        paths: List[ReasoningPath],
        success_rate: float,
        total_seen: int,
    ) -> Optional[Dict[str, Any]]:
        """Create or update an extracted pattern from reasoning paths."""
        pattern_id = f"PAT-{hashlib.sha256(signature.encode()).hexdigest()[:16]}"

        existing = self.session.query(ExtractedPattern).filter(
            ExtractedPattern.pattern_id == pattern_id
        ).first()

        representative_path = max(paths, key=lambda p: p.success_rate)

        domains = [p.domain for p in paths if p.domain]
        domain = Counter(domains).most_common(1)[0][0] if domains else "general"

        categories = [p.task_category for p in paths if p.task_category]
        category = Counter(categories).most_common(1)[0][0] if categories else "general"

        trigger_conditions = self._extract_trigger_conditions(paths)
        action_sequence = self._extract_action_sequence(representative_path)
        expected_outcomes = self._extract_expected_outcomes(paths)

        confidence = self._calculate_pattern_confidence(
            success_rate, total_seen, len(paths)
        )

        utility = self._calculate_pattern_utility(paths)

        can_replace = (
            confidence >= self.min_confidence_autonomous
            and success_rate >= 0.9
            and total_seen >= self.min_occurrences * 2
        )

        if existing:
            existing.times_observed = total_seen
            existing.success_rate = success_rate
            existing.confidence_score = confidence
            existing.utility_score = utility
            existing.can_replace_llm = can_replace
            existing.trigger_conditions = trigger_conditions
            existing.action_sequence = action_sequence
            existing.expected_outcomes = expected_outcomes
            existing.last_validated = datetime.now(timezone.utc)

            self.session.flush()

            return {
                "pattern_id": existing.pattern_id,
                "name": existing.pattern_name,
                "action": "updated",
                "confidence": confidence,
                "success_rate": success_rate,
                "can_replace_llm": can_replace,
            }
        else:
            pattern_name = self._generate_pattern_name(
                signature, domain, category
            )

            pattern = ExtractedPattern(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                pattern_type="reasoning_chain",
                domain=domain,
                task_category=category,
                trigger_conditions=trigger_conditions,
                action_sequence=action_sequence,
                expected_outcomes=expected_outcomes,
                confidence_score=confidence,
                utility_score=utility,
                times_observed=total_seen,
                success_rate=success_rate,
                supporting_interactions=[p.interaction_id for p in paths[:10]],
                example_prompts=self._get_example_prompts(paths),
                example_responses=self._get_example_responses(paths),
                can_replace_llm=can_replace,
            )

            self.session.add(pattern)
            self.session.flush()

            self._pattern_cache[pattern_id] = pattern

            return {
                "pattern_id": pattern_id,
                "name": pattern_name,
                "action": "created",
                "confidence": confidence,
                "success_rate": success_rate,
                "can_replace_llm": can_replace,
                "domain": domain,
                "category": category,
            }

    def _extract_interaction_level_patterns(
        self,
        cutoff: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Extract patterns from interaction-level data.

        Looks at the interaction type + outcome combinations to find
        patterns in what types of tasks succeed or fail.
        """
        interactions = self.session.query(LLMInteraction).filter(
            LLMInteraction.created_at >= cutoff,
        ).all()

        type_outcome_groups = defaultdict(list)
        for interaction in interactions:
            key = f"{interaction.interaction_type.value}:{interaction.model_used}"
            type_outcome_groups[key].append(interaction)

        patterns = []

        for key, group in type_outcome_groups.items():
            if len(group) < self.min_occurrences:
                continue

            successes = sum(
                1 for i in group if i.outcome == InteractionOutcome.SUCCESS
            )
            total = len(group)
            success_rate = successes / total if total > 0 else 0

            if success_rate >= self.min_success_rate:
                itype, model = key.split(":", 1)
                pattern_id = f"PAT-IL-{hashlib.sha256(key.encode()).hexdigest()[:12]}"

                existing = self.session.query(ExtractedPattern).filter(
                    ExtractedPattern.pattern_id == pattern_id
                ).first()

                if not existing:
                    pattern = ExtractedPattern(
                        pattern_id=pattern_id,
                        pattern_name=f"Model affinity: {model} for {itype}",
                        pattern_type="model_affinity",
                        domain="general",
                        task_category=itype,
                        trigger_conditions={
                            "interaction_type": itype,
                            "preferred_model": model,
                        },
                        action_sequence={
                            "route_to_model": model,
                            "task_type": itype,
                        },
                        expected_outcomes={
                            "success_rate": success_rate,
                            "avg_confidence": sum(i.confidence_score for i in group) / total,
                        },
                        confidence_score=min(0.95, success_rate),
                        utility_score=total / 100.0,
                        times_observed=total,
                        success_rate=success_rate,
                        can_replace_llm=False,
                    )
                    self.session.add(pattern)

                    patterns.append({
                        "pattern_id": pattern_id,
                        "name": pattern.pattern_name,
                        "action": "created",
                        "type": "model_affinity",
                        "confidence": min(0.95, success_rate),
                        "success_rate": success_rate,
                    })

        if patterns:
            self.session.flush()

        return patterns

    def _extract_trigger_conditions(
        self,
        paths: List[ReasoningPath],
    ) -> Dict[str, Any]:
        """Extract conditions that trigger this pattern."""
        all_entry = [p.entry_conditions for p in paths if p.entry_conditions]
        if not all_entry:
            return {}

        common_conditions = {}
        for key in all_entry[0]:
            values = [e.get(key) for e in all_entry if key in e]
            if len(values) >= len(all_entry) * 0.7:
                most_common = Counter(str(v) for v in values).most_common(1)
                if most_common:
                    common_conditions[key] = most_common[0][0]

        return common_conditions

    def _extract_action_sequence(self, path: ReasoningPath) -> Dict[str, Any]:
        """Extract the action sequence from a representative reasoning path."""
        if not path.steps:
            return {}

        return {
            "steps": [
                {
                    "action": step.get("action", ""),
                    "description": step.get("thought", "")[:200],
                }
                for step in path.steps
            ],
            "step_count": path.step_count,
            "pattern_signature": path.pattern_signature,
        }

    def _extract_expected_outcomes(
        self,
        paths: List[ReasoningPath],
    ) -> Dict[str, Any]:
        """Extract expected outcomes from a group of paths."""
        all_exit = [p.exit_conditions for p in paths if p.exit_conditions]
        if not all_exit:
            return {}

        avg_confidence = sum(
            float(e.get("confidence", 0)) for e in all_exit
        ) / len(all_exit) if all_exit else 0

        avg_steps = sum(
            int(e.get("step_count", 0)) for e in all_exit
        ) / len(all_exit) if all_exit else 0

        return {
            "expected_confidence": round(avg_confidence, 3),
            "expected_steps": round(avg_steps, 1),
            "success_probability": sum(
                1 for p in paths if p.outcome_success
            ) / len(paths) if paths else 0,
        }

    def _calculate_pattern_confidence(
        self,
        success_rate: float,
        total_seen: int,
        unique_paths: int,
    ) -> float:
        """
        Calculate confidence in a pattern.

        Higher confidence requires:
        - High success rate
        - Many observations
        - Multiple unique paths supporting it
        """
        rate_factor = success_rate * 0.5

        observation_factor = min(1.0, total_seen / 20) * 0.3

        diversity_factor = min(1.0, unique_paths / 5) * 0.2

        return min(1.0, rate_factor + observation_factor + diversity_factor)

    def _calculate_pattern_utility(self, paths: List[ReasoningPath]) -> float:
        """
        Calculate utility of a pattern (how useful/frequent it is).

        Higher utility means:
        - Frequently occurring pattern
        - Covers important task categories
        - High time savings potential
        """
        frequency = min(1.0, sum(p.times_seen for p in paths) / 50) * 0.4

        categories = set(p.task_category for p in paths if p.task_category)
        breadth = min(1.0, len(categories) / 5) * 0.3

        avg_duration = sum(p.total_duration_ms for p in paths) / len(paths) if paths else 0
        time_savings = min(1.0, avg_duration / 5000) * 0.3

        return min(1.0, frequency + breadth + time_savings)

    def _generate_pattern_name(
        self,
        signature: str,
        domain: str,
        category: str,
    ) -> str:
        """Generate a human-readable name for a pattern."""
        steps = signature.split("->")
        if len(steps) <= 3:
            step_desc = " then ".join(steps)
        else:
            step_desc = f"{steps[0]} then {steps[1]} ... then {steps[-1]}"

        return f"{domain.title()} {category}: {step_desc}"

    def _get_example_prompts(self, paths: List[ReasoningPath]) -> List[str]:
        """Get example prompts that triggered these paths."""
        prompts = []
        for path in paths[:5]:
            interaction = self.session.query(LLMInteraction).filter(
                LLMInteraction.interaction_id == path.interaction_id
            ).first()
            if interaction and interaction.prompt:
                prompts.append(interaction.prompt[:500])
        return prompts

    def _get_example_responses(self, paths: List[ReasoningPath]) -> List[str]:
        """Get example responses from these paths."""
        responses = []
        for path in paths[:5]:
            interaction = self.session.query(LLMInteraction).filter(
                LLMInteraction.interaction_id == path.interaction_id
            ).first()
            if interaction and interaction.response:
                responses.append(interaction.response[:500])
        return responses

    def can_handle_autonomously(
        self,
        request: str,
        task_type: str,
    ) -> bool:
        """
        Check if Grace can handle this request autonomously
        using learned patterns.

        This is the key method for reducing LLM dependency.
        """
        matching_patterns = self._find_matching_patterns(request, task_type)

        for pattern in matching_patterns:
            if (
                pattern.can_replace_llm
                and pattern.confidence_score >= self.min_confidence_autonomous
                and pattern.success_rate >= 0.9
            ):
                return True

        return False

    def apply_pattern(
        self,
        request: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Apply a learned pattern to handle a request autonomously.

        Returns:
            Result dict if a pattern was applied, None if no pattern found
        """
        matching_patterns = self._find_matching_patterns(request, task_type)

        for pattern in matching_patterns:
            if not pattern.can_replace_llm:
                continue

            if pattern.confidence_score < self.min_confidence_autonomous:
                continue

            pattern.times_applied += 1
            pattern.last_applied = datetime.now(timezone.utc)

            result = self._execute_pattern(pattern, request, context)

            if result.get("success"):
                pattern.times_succeeded += 1
                pattern.llm_calls_saved += 1
            else:
                pattern.times_failed += 1

            total = pattern.times_succeeded + pattern.times_failed
            if total > 0:
                pattern.success_rate = pattern.times_succeeded / total

            self.session.flush()

            logger.info(
                f"[PATTERN-LEARNER] Applied pattern {pattern.pattern_id}: "
                f"success={result.get('success')}"
            )

            return {
                "pattern_id": pattern.pattern_id,
                "pattern_name": pattern.pattern_name,
                "output": result.get("output", ""),
                "success": result.get("success", False),
                "patterns": [pattern.pattern_name],
                "confidence": pattern.confidence_score,
            }

        return None

    def _find_matching_patterns(
        self,
        request: str,
        task_type: str,
    ) -> List[ExtractedPattern]:
        """Find patterns that match a given request and task type."""
        patterns = self.session.query(ExtractedPattern).filter(
            ExtractedPattern.task_category == task_type,
            ExtractedPattern.confidence_score >= 0.5,
        ).order_by(
            desc(ExtractedPattern.confidence_score),
            desc(ExtractedPattern.times_observed),
        ).limit(10).all()

        if not patterns:
            patterns = self.session.query(ExtractedPattern).filter(
                ExtractedPattern.confidence_score >= 0.5,
            ).order_by(
                desc(ExtractedPattern.confidence_score),
            ).limit(5).all()

        return patterns

    def _execute_pattern(
        self,
        pattern: ExtractedPattern,
        request: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute a pattern's action sequence.

        This is where the pattern is actually applied to produce output
        without calling an LLM.
        """
        action_seq = pattern.action_sequence or {}
        steps = action_seq.get("steps", [])

        if not steps:
            return {
                "success": False,
                "output": "Pattern has no action steps",
                "error": "empty_pattern",
            }

        output_parts = []
        for step in steps:
            action = step.get("action", "")
            description = step.get("description", "")
            output_parts.append(f"Step [{action}]: {description}")

        return {
            "success": True,
            "output": "\n".join(output_parts),
            "steps_executed": len(steps),
            "pattern_used": pattern.pattern_name,
        }

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about extracted patterns."""
        all_patterns = self.session.query(ExtractedPattern).all()

        if not all_patterns:
            return {
                "total_patterns": 0,
                "message": "No patterns extracted yet"
            }

        replaceable = [p for p in all_patterns if p.can_replace_llm]
        total_saved = sum(p.llm_calls_saved for p in all_patterns)

        by_domain = defaultdict(int)
        by_type = defaultdict(int)
        for p in all_patterns:
            by_domain[p.domain or "unknown"] += 1
            by_type[p.pattern_type or "unknown"] += 1

        return {
            "total_patterns": len(all_patterns),
            "replaceable_patterns": len(replaceable),
            "non_replaceable_patterns": len(all_patterns) - len(replaceable),
            "total_llm_calls_saved": total_saved,
            "avg_confidence": round(
                sum(p.confidence_score for p in all_patterns) / len(all_patterns), 3
            ),
            "avg_success_rate": round(
                sum(p.success_rate for p in all_patterns) / len(all_patterns), 3
            ),
            "by_domain": dict(by_domain),
            "by_type": dict(by_type),
            "top_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "name": p.pattern_name,
                    "confidence": p.confidence_score,
                    "success_rate": p.success_rate,
                    "times_observed": p.times_observed,
                    "can_replace_llm": p.can_replace_llm,
                    "llm_calls_saved": p.llm_calls_saved,
                }
                for p in sorted(
                    all_patterns,
                    key=lambda x: x.confidence_score * x.utility_score,
                    reverse=True,
                )[:10]
            ],
        }

    def get_learning_progress(self) -> Dict[str, Any]:
        """
        Get a report on learning progress from LLM interactions.

        Shows how much Grace has learned and how close it is to
        handling various task types autonomously.
        """
        patterns = self.session.query(ExtractedPattern).all()
        interactions = self.session.query(LLMInteraction).count()
        reasoning_paths = self.session.query(ReasoningPath).count()

        if not patterns:
            return {
                "learning_stage": "initial",
                "interactions_recorded": interactions,
                "reasoning_paths_captured": reasoning_paths,
                "patterns_extracted": 0,
                "autonomy_readiness": 0.0,
                "message": "Still in observation phase. More interactions needed.",
            }

        replaceable = sum(1 for p in patterns if p.can_replace_llm)
        total = len(patterns)
        avg_confidence = sum(p.confidence_score for p in patterns) / total
        total_saved = sum(p.llm_calls_saved for p in patterns)

        task_categories = set(p.task_category for p in patterns if p.task_category)
        domains = set(p.domain for p in patterns if p.domain)

        autonomy_readiness = min(1.0, (
            (replaceable / total * 0.4) +
            (avg_confidence * 0.3) +
            (min(1.0, total / 50) * 0.2) +
            (min(1.0, len(task_categories) / 10) * 0.1)
        )) if total > 0 else 0.0

        if autonomy_readiness < 0.2:
            stage = "initial"
        elif autonomy_readiness < 0.4:
            stage = "learning"
        elif autonomy_readiness < 0.6:
            stage = "practicing"
        elif autonomy_readiness < 0.8:
            stage = "proficient"
        else:
            stage = "autonomous"

        return {
            "learning_stage": stage,
            "interactions_recorded": interactions,
            "reasoning_paths_captured": reasoning_paths,
            "patterns_extracted": total,
            "patterns_replaceable": replaceable,
            "autonomy_readiness": round(autonomy_readiness, 3),
            "avg_pattern_confidence": round(avg_confidence, 3),
            "total_llm_calls_saved": total_saved,
            "task_categories_covered": list(task_categories),
            "domains_covered": list(domains),
            "next_milestone": self._get_next_milestone(autonomy_readiness),
        }

    def _get_next_milestone(self, current_readiness: float) -> Dict[str, Any]:
        """Determine the next learning milestone."""
        milestones = [
            (0.2, "learning", "Extract 10+ patterns from LLM interactions"),
            (0.4, "practicing", "Achieve 80%+ success rate on 5+ patterns"),
            (0.6, "proficient", "Handle 3+ task categories autonomously"),
            (0.8, "autonomous", "Replace LLM for 50%+ of common tasks"),
            (1.0, "mastery", "Handle all tracked task types autonomously"),
        ]

        for threshold, name, description in milestones:
            if current_readiness < threshold:
                return {
                    "name": name,
                    "threshold": threshold,
                    "description": description,
                    "progress": round(current_readiness / threshold, 3),
                }

        return {
            "name": "mastery",
            "threshold": 1.0,
            "description": "Full autonomous capability achieved",
            "progress": 1.0,
        }


_learner_instance: Optional[LLMPatternLearner] = None


def get_llm_pattern_learner(session: Session) -> LLMPatternLearner:
    """Get or create the LLM pattern learner singleton."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = LLMPatternLearner(session)
    return _learner_instance
