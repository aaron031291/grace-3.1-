"""
LLM Interaction Tracker

Core system that records every LLM interaction for learning purposes.
Acts as the "black box recorder" for all LLM calls, capturing:

- Every prompt sent to an LLM
- Every response received
- The reasoning chain the LLM used
- Whether the outcome was successful
- What patterns emerge from the interaction

This data feeds into the Pattern Learner and Dependency Reducer
to progressively reduce reliance on external LLMs.

Architecture:
    User Request -> Kimi (LLM) -> Tracker records interaction
                                -> Reasoning path extracted
                                -> Patterns identified
                                -> Learning memory updated
                                -> Dependency metrics updated

Classes:
- `LLMInteractionTracker`

Key Methods:
- `record_interaction()`
- `update_interaction_outcome()`
- `record_coding_task()`
- `update_coding_task()`
- `get_interaction_stats()`
- `get_recent_interactions()`
- `get_reasoning_paths()`
- `get_coding_task_stats()`
- `get_llm_interaction_tracker()`
"""

import logging
import hashlib
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from models.llm_tracking_models import (
    LLMInteraction,
    ReasoningPath,
    ExtractedPattern,
    CodingTaskRecord,
    LLMDependencyMetric,
    InteractionType,
    InteractionOutcome,
    TaskDelegationType,
)

logger = logging.getLogger(__name__)


class LLMInteractionTracker:
    """
    Records and analyzes every LLM interaction.

    This is the foundational tracking layer. Every time Kimi (or any LLM)
    processes a request, this tracker captures the full interaction for
    later analysis and pattern extraction.

    The tracker is deterministic in its recording -- since Grace is
    deterministic, tracking the LLM allows us to learn from its patterns
    and eventually replicate its logic without needing the LLM.
    """

    def __init__(self, session: Session):
        self.session = session
        self._interaction_buffer: List[LLMInteraction] = []
        self._flush_threshold = 10
        logger.info("[LLM-TRACKER] Interaction tracker initialized")

    def record_interaction(
        self,
        prompt: str,
        response: str,
        model_used: str,
        interaction_type: str = "reasoning",
        delegation_type: Optional[str] = None,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None,
        decision_path: Optional[List[str]] = None,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
        outcome: str = "pending",
        confidence_score: float = 0.0,
        duration_ms: float = 0.0,
        token_count_input: int = 0,
        token_count_output: int = 0,
        context_used: Optional[Dict[str, Any]] = None,
        files_referenced: Optional[List[str]] = None,
        commands_executed: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_interaction_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMInteraction:
        """
        Record a single LLM interaction.

        Args:
            prompt: The prompt sent to the LLM
            response: The LLM's response
            model_used: Which model was used (e.g., "kimi", "deepseek", "qwen2.5")
            interaction_type: Type of interaction (command_execution, coding_task, etc.)
            delegation_type: How the task was delegated
            reasoning_chain: Step-by-step reasoning the LLM performed
            decision_path: Key decision points
            alternatives_considered: What other approaches were considered
            outcome: success, failure, partial_success, etc.
            confidence_score: LLM's confidence in its response
            duration_ms: How long the interaction took
            token_count_input: Input tokens used
            token_count_output: Output tokens generated
            context_used: What context was provided to the LLM
            files_referenced: Files the LLM referenced
            commands_executed: Commands the LLM executed
            error_message: Error if any
            error_type: Classification of error
            session_id: Session grouping ID
            parent_interaction_id: Parent interaction for chains
            system_prompt: System prompt used
            genesis_key_id: Link to Genesis Key
            metadata: Additional metadata

        Returns:
            The recorded LLMInteraction
        """
        interaction_id = f"INT-{uuid.uuid4().hex[:16]}"

        try:
            itype = InteractionType(interaction_type)
        except ValueError:
            itype = InteractionType.REASONING

        try:
            ioutcome = InteractionOutcome(outcome)
        except ValueError:
            ioutcome = InteractionOutcome.PENDING

        dtype = None
        if delegation_type:
            try:
                dtype = TaskDelegationType(delegation_type)
            except ValueError:
                dtype = None

        interaction = LLMInteraction(
            interaction_id=interaction_id,
            session_id=session_id,
            interaction_type=itype,
            outcome=ioutcome,
            delegation_type=dtype,
            model_used=model_used,
            prompt=prompt,
            system_prompt=system_prompt,
            response=response,
            reasoning_chain=reasoning_chain,
            decision_path=decision_path,
            alternatives_considered=alternatives_considered,
            confidence_score=confidence_score,
            trust_score=self._calculate_initial_trust(confidence_score, outcome),
            duration_ms=duration_ms,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            error_message=error_message,
            error_type=error_type,
            context_used=context_used,
            files_referenced=files_referenced,
            commands_executed=commands_executed,
            genesis_key_id=genesis_key_id,
            parent_interaction_id=parent_interaction_id,
            metadata_extra=metadata,
        )

        self.session.add(interaction)
        self.session.flush()

        if reasoning_chain:
            self._extract_reasoning_path(interaction, reasoning_chain)

        logger.info(
            f"[LLM-TRACKER] Recorded interaction {interaction_id}: "
            f"type={interaction_type}, model={model_used}, outcome={outcome}"
        )

        return interaction

    def update_interaction_outcome(
        self,
        interaction_id: str,
        outcome: str,
        quality_score: Optional[float] = None,
        user_feedback: Optional[str] = None,
        user_feedback_text: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[LLMInteraction]:
        """
        Update the outcome of a previously recorded interaction.

        This is called after the interaction completes to record
        whether it actually succeeded.
        """
        interaction = self.session.query(LLMInteraction).filter(
            LLMInteraction.interaction_id == interaction_id
        ).first()

        if not interaction:
            logger.warning(f"[LLM-TRACKER] Interaction {interaction_id} not found for update")
            return None

        try:
            interaction.outcome = InteractionOutcome(outcome)
        except ValueError:
            pass

        if quality_score is not None:
            interaction.quality_score = quality_score

        if user_feedback:
            interaction.user_feedback = user_feedback

        if user_feedback_text:
            interaction.user_feedback_text = user_feedback_text

        if error_message:
            interaction.error_message = error_message

        interaction.trust_score = self._recalculate_trust(interaction)

        self.session.flush()

        self._update_reasoning_path_outcome(interaction)

        logger.info(
            f"[LLM-TRACKER] Updated interaction {interaction_id}: outcome={outcome}"
        )

        return interaction

    def record_coding_task(
        self,
        task_description: str,
        task_type: str,
        interaction_id: Optional[str] = None,
        delegated_by: str = "kimi",
        delegated_to: str = "coding_agent",
        files_targeted: Optional[List[str]] = None,
    ) -> CodingTaskRecord:
        """
        Record a coding task that was delegated.

        This specifically tracks tasks where Kimi decides "this is a coding
        task" and hands it off to the coding agent.
        """
        task_id = f"CT-{uuid.uuid4().hex[:16]}"

        record = CodingTaskRecord(
            task_id=task_id,
            interaction_id=interaction_id,
            task_description=task_description,
            task_type=task_type,
            delegated_by=delegated_by,
            delegated_to=delegated_to,
            files_targeted=files_targeted,
            outcome=InteractionOutcome.PENDING,
        )

        self.session.add(record)
        self.session.flush()

        logger.info(
            f"[LLM-TRACKER] Recorded coding task {task_id}: "
            f"{delegated_by} -> {delegated_to}, type={task_type}"
        )

        return record

    def update_coding_task(
        self,
        task_id: str,
        outcome: str,
        files_created: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None,
        diff_summary: Optional[str] = None,
        tests_run: bool = False,
        tests_passed: int = 0,
        tests_failed: int = 0,
        error_message: Optional[str] = None,
        duration_ms: float = 0.0,
        iterations: int = 1,
        quality_assessment: Optional[Dict[str, Any]] = None,
        reasoning_used: Optional[List[Dict[str, Any]]] = None,
        patterns_applied: Optional[List[str]] = None,
    ) -> Optional[CodingTaskRecord]:
        """Update a coding task record with its results."""
        record = self.session.query(CodingTaskRecord).filter(
            CodingTaskRecord.task_id == task_id
        ).first()

        if not record:
            logger.warning(f"[LLM-TRACKER] Coding task {task_id} not found")
            return None

        try:
            record.outcome = InteractionOutcome(outcome)
        except ValueError:
            pass

        if files_created:
            record.files_created = files_created
        if files_modified:
            record.files_modified = files_modified
        if diff_summary:
            record.diff_summary = diff_summary

        record.tests_run = tests_run
        record.tests_passed = tests_passed
        record.tests_failed = tests_failed
        record.error_message = error_message
        record.duration_ms = duration_ms
        record.iterations = iterations
        record.quality_assessment = quality_assessment
        record.reasoning_used = reasoning_used
        record.patterns_applied = patterns_applied

        self.session.flush()

        logger.info(
            f"[LLM-TRACKER] Updated coding task {task_id}: outcome={outcome}"
        )

        return record

    def _extract_reasoning_path(
        self,
        interaction: LLMInteraction,
        reasoning_chain: List[Dict[str, Any]],
    ):
        """
        Extract and store a reasoning path from an interaction.

        Reasoning paths are the step-by-step logic the LLM used.
        By storing these, we can identify patterns across many interactions.
        """
        path_id = f"RP-{uuid.uuid4().hex[:16]}"

        steps = []
        confidence_at_each_step = []

        for i, step in enumerate(reasoning_chain):
            step_data = {
                "step_number": i + 1,
                "action": step.get("action", "think"),
                "thought": step.get("thought", ""),
                "observation": step.get("observation", ""),
                "decision": step.get("decision", ""),
            }
            steps.append(step_data)

            conf = step.get("confidence", 0.5)
            confidence_at_each_step.append(conf)

        signature = self._compute_pattern_signature(steps)
        similarity = self._compute_similarity_hash(steps)

        domain = self._infer_domain(interaction.prompt, steps)
        task_category = interaction.interaction_type.value

        path = ReasoningPath(
            path_id=path_id,
            interaction_id=interaction.interaction_id,
            domain=domain,
            task_category=task_category,
            steps=steps,
            step_count=len(steps),
            entry_conditions=self._extract_entry_conditions(interaction),
            exit_conditions=self._extract_exit_conditions(interaction, steps),
            outcome_success=(interaction.outcome == InteractionOutcome.SUCCESS),
            confidence_at_each_step=confidence_at_each_step,
            total_duration_ms=interaction.duration_ms,
            pattern_signature=signature,
            similarity_hash=similarity,
            times_seen=1,
            times_succeeded=1 if interaction.outcome == InteractionOutcome.SUCCESS else 0,
            times_failed=1 if interaction.outcome == InteractionOutcome.FAILURE else 0,
            success_rate=1.0 if interaction.outcome == InteractionOutcome.SUCCESS else 0.0,
        )

        existing = self.session.query(ReasoningPath).filter(
            ReasoningPath.similarity_hash == similarity
        ).first()

        if existing:
            existing.times_seen += 1
            if interaction.outcome == InteractionOutcome.SUCCESS:
                existing.times_succeeded += 1
            elif interaction.outcome == InteractionOutcome.FAILURE:
                existing.times_failed += 1
            total = existing.times_succeeded + existing.times_failed
            if total > 0:
                existing.success_rate = existing.times_succeeded / total
        else:
            self.session.add(path)

        self.session.flush()

    def _update_reasoning_path_outcome(self, interaction: LLMInteraction):
        """Update reasoning path success/failure counts when outcome changes."""
        paths = self.session.query(ReasoningPath).filter(
            ReasoningPath.interaction_id == interaction.interaction_id
        ).all()

        for path in paths:
            path.outcome_success = (interaction.outcome == InteractionOutcome.SUCCESS)

    def _compute_pattern_signature(self, steps: List[Dict[str, Any]]) -> str:
        """
        Compute a signature that identifies the pattern of reasoning.

        This captures the sequence of action types (not content) so we
        can find similar reasoning patterns across different prompts.
        """
        action_sequence = [s.get("action", "unknown") for s in steps]
        signature = "->".join(action_sequence)
        return signature[:256]

    def _compute_similarity_hash(self, steps: List[Dict[str, Any]]) -> str:
        """
        Compute a hash for finding similar reasoning paths.

        Uses action sequence + key decisions to create a fingerprint.
        """
        parts = []
        for step in steps:
            parts.append(step.get("action", ""))
            decision = step.get("decision", "")
            if decision:
                parts.append(decision[:50])

        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _infer_domain(self, prompt: str, steps: List[Dict[str, Any]]) -> str:
        """Infer the domain of the interaction from prompt and steps."""
        prompt_lower = prompt.lower()

        domain_keywords = {
            "python": ["python", "pip", "pytest", "flask", "django", "fastapi"],
            "javascript": ["javascript", "node", "npm", "react", "vue", "angular"],
            "database": ["sql", "database", "query", "table", "migration", "postgres"],
            "devops": ["docker", "kubernetes", "deploy", "ci/cd", "pipeline"],
            "git": ["git", "commit", "branch", "merge", "pull request"],
            "api": ["api", "endpoint", "rest", "graphql", "http"],
            "testing": ["test", "spec", "assertion", "coverage", "mock"],
            "security": ["security", "auth", "token", "encrypt", "vulnerability"],
            "architecture": ["architecture", "design", "pattern", "structure"],
            "debugging": ["bug", "error", "fix", "debug", "trace", "stack"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return domain

        return "general"

    def _extract_entry_conditions(self, interaction: LLMInteraction) -> Dict[str, Any]:
        """Extract the conditions that were true when this reasoning started."""
        return {
            "interaction_type": interaction.interaction_type.value,
            "model": interaction.model_used,
            "has_context": bool(interaction.context_used),
            "has_files": bool(interaction.files_referenced),
            "prompt_length": len(interaction.prompt) if interaction.prompt else 0,
        }

    def _extract_exit_conditions(
        self,
        interaction: LLMInteraction,
        steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract the conditions at the end of reasoning."""
        return {
            "outcome": interaction.outcome.value,
            "step_count": len(steps),
            "confidence": interaction.confidence_score,
            "had_error": bool(interaction.error_message),
        }

    def _calculate_initial_trust(self, confidence: float, outcome: str) -> float:
        """Calculate initial trust score for an interaction."""
        base_trust = confidence * 0.6

        outcome_modifier = {
            "success": 0.3,
            "partial_success": 0.15,
            "failure": -0.1,
            "timeout": -0.05,
            "delegated": 0.1,
            "pending": 0.0,
        }

        modifier = outcome_modifier.get(outcome, 0.0)
        return max(0.0, min(1.0, base_trust + modifier + 0.1))

    def _recalculate_trust(self, interaction: LLMInteraction) -> float:
        """Recalculate trust score based on updated information."""
        base = interaction.confidence_score * 0.4

        outcome_scores = {
            InteractionOutcome.SUCCESS: 0.3,
            InteractionOutcome.PARTIAL_SUCCESS: 0.15,
            InteractionOutcome.FAILURE: -0.1,
            InteractionOutcome.TIMEOUT: -0.05,
            InteractionOutcome.DELEGATED: 0.1,
            InteractionOutcome.PENDING: 0.0,
        }

        outcome_bonus = outcome_scores.get(interaction.outcome, 0.0)

        quality_bonus = 0.0
        if interaction.quality_score is not None:
            quality_bonus = interaction.quality_score * 0.2

        feedback_bonus = 0.0
        if interaction.user_feedback == "positive":
            feedback_bonus = 0.15
        elif interaction.user_feedback == "negative":
            feedback_bonus = -0.15

        trust = base + outcome_bonus + quality_bonus + feedback_bonus + 0.1
        return max(0.0, min(1.0, trust))

    def get_interaction_stats(
        self,
        time_window_hours: int = 24,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about LLM interactions.

        Returns:
            Comprehensive stats including success rates, model usage,
            interaction types, and performance metrics.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        query = self.session.query(LLMInteraction).filter(
            LLMInteraction.created_at >= cutoff
        )
        if model:
            query = query.filter(LLMInteraction.model_used == model)

        interactions = query.all()

        if not interactions:
            return {
                "total": 0,
                "time_window_hours": time_window_hours,
                "message": "No interactions in this time window"
            }

        total = len(interactions)
        successes = sum(1 for i in interactions if i.outcome == InteractionOutcome.SUCCESS)
        failures = sum(1 for i in interactions if i.outcome == InteractionOutcome.FAILURE)
        partial = sum(1 for i in interactions if i.outcome == InteractionOutcome.PARTIAL_SUCCESS)

        type_counts = defaultdict(int)
        model_counts = defaultdict(int)
        delegation_counts = defaultdict(int)
        avg_duration_by_type = defaultdict(list)

        for interaction in interactions:
            type_counts[interaction.interaction_type.value] += 1
            model_counts[interaction.model_used] += 1
            if interaction.delegation_type:
                delegation_counts[interaction.delegation_type.value] += 1
            avg_duration_by_type[interaction.interaction_type.value].append(
                interaction.duration_ms
            )

        avg_durations = {
            k: sum(v) / len(v) for k, v in avg_duration_by_type.items()
        }

        avg_confidence = sum(i.confidence_score for i in interactions) / total
        avg_trust = sum(i.trust_score for i in interactions) / total
        total_tokens_in = sum(i.token_count_input for i in interactions)
        total_tokens_out = sum(i.token_count_output for i in interactions)

        return {
            "total": total,
            "time_window_hours": time_window_hours,
            "outcomes": {
                "success": successes,
                "failure": failures,
                "partial_success": partial,
                "success_rate": successes / total if total > 0 else 0,
            },
            "by_type": dict(type_counts),
            "by_model": dict(model_counts),
            "by_delegation": dict(delegation_counts),
            "performance": {
                "avg_confidence": round(avg_confidence, 3),
                "avg_trust": round(avg_trust, 3),
                "avg_duration_by_type_ms": avg_durations,
                "total_tokens_input": total_tokens_in,
                "total_tokens_output": total_tokens_out,
            },
        }

    def get_recent_interactions(
        self,
        limit: int = 50,
        interaction_type: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent interactions with optional filtering."""
        query = self.session.query(LLMInteraction).order_by(
            desc(LLMInteraction.created_at)
        )

        if interaction_type:
            try:
                itype = InteractionType(interaction_type)
                query = query.filter(LLMInteraction.interaction_type == itype)
            except ValueError:
                pass

        if outcome:
            try:
                ioutcome = InteractionOutcome(outcome)
                query = query.filter(LLMInteraction.outcome == ioutcome)
            except ValueError:
                pass

        interactions = query.limit(limit).all()

        return [
            {
                "interaction_id": i.interaction_id,
                "type": i.interaction_type.value,
                "outcome": i.outcome.value,
                "model": i.model_used,
                "confidence": i.confidence_score,
                "trust": i.trust_score,
                "duration_ms": i.duration_ms,
                "prompt_preview": (i.prompt[:200] + "...") if i.prompt and len(i.prompt) > 200 else i.prompt,
                "response_preview": (i.response[:200] + "...") if i.response and len(i.response) > 200 else i.response,
                "has_reasoning": bool(i.reasoning_chain),
                "error": i.error_message,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in interactions
        ]

    def get_reasoning_paths(
        self,
        domain: Optional[str] = None,
        min_success_rate: float = 0.0,
        min_times_seen: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recorded reasoning paths, optionally filtered."""
        query = self.session.query(ReasoningPath)

        if domain:
            query = query.filter(ReasoningPath.domain == domain)

        query = query.filter(
            ReasoningPath.success_rate >= min_success_rate,
            ReasoningPath.times_seen >= min_times_seen,
        )

        query = query.order_by(
            desc(ReasoningPath.success_rate),
            desc(ReasoningPath.times_seen),
        )

        paths = query.limit(limit).all()

        return [
            {
                "path_id": p.path_id,
                "domain": p.domain,
                "task_category": p.task_category,
                "step_count": p.step_count,
                "pattern_signature": p.pattern_signature,
                "times_seen": p.times_seen,
                "times_succeeded": p.times_succeeded,
                "times_failed": p.times_failed,
                "success_rate": p.success_rate,
                "steps": p.steps,
            }
            for p in paths
        ]

    def get_coding_task_stats(
        self,
        time_window_hours: int = 168,
    ) -> Dict[str, Any]:
        """Get statistics about coding tasks."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        tasks = self.session.query(CodingTaskRecord).filter(
            CodingTaskRecord.created_at >= cutoff
        ).all()

        if not tasks:
            return {"total": 0, "time_window_hours": time_window_hours}

        total = len(tasks)
        successes = sum(1 for t in tasks if t.outcome == InteractionOutcome.SUCCESS)
        failures = sum(1 for t in tasks if t.outcome == InteractionOutcome.FAILURE)

        type_counts = defaultdict(int)
        delegation_counts = defaultdict(int)

        for task in tasks:
            type_counts[task.task_type] += 1
            delegation_counts[f"{task.delegated_by}->{task.delegated_to}"] += 1

        total_tests_passed = sum(t.tests_passed for t in tasks)
        total_tests_failed = sum(t.tests_failed for t in tasks)
        avg_iterations = sum(t.iterations for t in tasks) / total
        avg_duration = sum(t.duration_ms for t in tasks) / total

        return {
            "total": total,
            "time_window_hours": time_window_hours,
            "outcomes": {
                "success": successes,
                "failure": failures,
                "success_rate": successes / total if total > 0 else 0,
            },
            "by_type": dict(type_counts),
            "by_delegation": dict(delegation_counts),
            "testing": {
                "total_tests_passed": total_tests_passed,
                "total_tests_failed": total_tests_failed,
                "test_pass_rate": (
                    total_tests_passed / (total_tests_passed + total_tests_failed)
                    if (total_tests_passed + total_tests_failed) > 0
                    else 0
                ),
            },
            "performance": {
                "avg_iterations": round(avg_iterations, 2),
                "avg_duration_ms": round(avg_duration, 2),
            },
        }


_tracker_instance: Optional[LLMInteractionTracker] = None


def get_llm_interaction_tracker(session: Session) -> LLMInteractionTracker:
    """Get or create the LLM interaction tracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = LLMInteractionTracker(session)
    return _tracker_instance
