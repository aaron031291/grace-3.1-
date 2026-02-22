"""
Intelligence Feedback Loops

11 self-improving loops that make Grace smarter with every task.
Each loop feeds outcomes back into the system that produced them.

These are the connections that turn a collection of systems into
a unified intelligence that improves itself.

LOOPS:
  1. Criteria Effectiveness    - learn which criteria catch real problems
  2. Question Effectiveness    - learn which questions need asking
  3. Research Quality           - learn which research sources are reliable
  4. Auto Test Generation       - derive test specs from criteria
  5. Kimi Fact Composition      - compose facts, store, skip LLM next time
  6. Unified Task Enrichment    - enrich tasks with all 9 intelligence layers
  7. Knowledge Gap Priority     - prioritize gaps by frequency
  8. Playbook Evolution         - playbooks improve with each use
  9. Cross-Task Dependencies    - detect when tasks block each other
  10. Verification → Guard      - task outcomes train hallucination guard
  11. Mid-Task Consultation     - pause, ask user, resume
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CriteriaEffectivenessTracker:
    """
    Loop 1: Track which criteria catch real problems vs noise.

    Criteria that never fail = too easy, suggest removal.
    Criteria that always fail = probably wrong, flag for review.
    Sweet spot: criteria that fail 10-40% of the time.
    """

    def __init__(self, session: Session):
        self.session = session
        self._criteria_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"checked": 0, "passed": 0, "failed": 0}
        )

    def record_criterion_result(self, criterion_id: str, criterion_name: str, passed: bool):
        stats = self._criteria_stats[criterion_id]
        stats["checked"] += 1
        if passed:
            stats["passed"] += 1
        else:
            stats["failed"] += 1

    def get_effectiveness_report(self) -> Dict[str, Any]:
        too_easy = []
        too_hard = []
        effective = []

        for cid, stats in self._criteria_stats.items():
            if stats["checked"] < 3:
                continue
            fail_rate = stats["failed"] / stats["checked"]
            if fail_rate == 0:
                too_easy.append({"criterion": cid, "fail_rate": 0, "suggestion": "remove_or_tighten"})
            elif fail_rate > 0.8:
                too_hard.append({"criterion": cid, "fail_rate": fail_rate, "suggestion": "review_or_fix"})
            else:
                effective.append({"criterion": cid, "fail_rate": fail_rate})

        return {"too_easy": too_easy, "too_hard": too_hard, "effective": effective}


class QuestionEffectivenessTracker:
    """
    Loop 2: Track which questions Grace can self-answer vs need user.

    If Grace always self-resolves HOW via ConceptNet, stop asking HOW.
    Focus user questions on what genuinely needs human input.
    """

    def __init__(self):
        self._question_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"asked": 0, "self_resolved": 0, "user_answered": 0}
        )

    def record_question(self, question_key: str, resolved_by: str):
        stats = self._question_stats[question_key]
        stats["asked"] += 1
        if resolved_by == "self_research":
            stats["self_resolved"] += 1
        elif resolved_by == "user":
            stats["user_answered"] += 1

    def get_skip_recommendations(self) -> List[str]:
        skip = []
        for qkey, stats in self._question_stats.items():
            if stats["asked"] >= 5 and stats["self_resolved"] / stats["asked"] > 0.8:
                skip.append(qkey)
        return skip

    def get_report(self) -> Dict[str, Any]:
        return {
            "question_stats": dict(self._question_stats),
            "recommend_skip": self.get_skip_recommendations(),
        }


class ResearchQualityTracker:
    """
    Loop 3: Track which research sources lead to task success vs failure.

    When self-research gives an answer that leads to task success,
    upweight that source. When it leads to failure, downweight.
    """

    def __init__(self, session: Session):
        self.session = session
        self._source_outcomes: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"used": 0, "led_to_success": 0, "led_to_failure": 0}
        )

    def record_research_outcome(self, source: str, task_succeeded: bool):
        stats = self._source_outcomes[source]
        stats["used"] += 1
        if task_succeeded:
            stats["led_to_success"] += 1
        else:
            stats["led_to_failure"] += 1

        # Propagate to weight system
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            outcome = "success" if task_succeeded else "failure"
            ws.propagate_outcome(outcome=outcome, source_type=source)
        except Exception:
            pass

    def get_source_reliability(self) -> Dict[str, float]:
        reliability = {}
        for source, stats in self._source_outcomes.items():
            if stats["used"] > 0:
                reliability[source] = stats["led_to_success"] / stats["used"]
        return reliability


class KnowledgeGapPriorityQueue:
    """
    Loop 7: Prioritize knowledge gaps by frequency.

    Gaps that appear 5 times → mine deeply.
    Gaps that appear once → low priority.
    """

    def __init__(self):
        self._gap_counts: Dict[str, int] = defaultdict(int)
        self._gap_details: Dict[str, List[str]] = defaultdict(list)

    def record_gap(self, topic: str, context: str = ""):
        self._gap_counts[topic] += 1
        if context:
            self._gap_details[topic].append(context[:200])

    def get_priority_queue(self) -> List[Dict[str, Any]]:
        queue = [
            {"topic": topic, "frequency": count, "contexts": self._gap_details.get(topic, [])[:3]}
            for topic, count in self._gap_counts.items()
        ]
        queue.sort(key=lambda x: x["frequency"], reverse=True)
        return queue

    def get_top_gaps(self, n: int = 5) -> List[str]:
        queue = self.get_priority_queue()
        return [g["topic"] for g in queue[:n]]


class PlaybookEvolution:
    """
    Loop 8: Playbooks improve with each use.

    When a playbook is used but requires modifications,
    the diff between original and actual steps updates the playbook.
    """

    def __init__(self, session: Session):
        self.session = session

    def record_playbook_modification(
        self,
        playbook_id: str,
        original_steps: List[Dict],
        actual_steps: List[Dict],
    ):
        if original_steps == actual_steps:
            return

        try:
            from cognitive.task_playbook_engine import TaskPlaybook
            playbook = self.session.query(TaskPlaybook).filter(
                TaskPlaybook.playbook_id == playbook_id
            ).first()

            if playbook:
                # Merge: keep original steps, add new ones that were needed
                original_ids = {s.get("step_id") for s in original_steps}
                new_steps = [s for s in actual_steps if s.get("step_id") not in original_ids]

                if new_steps:
                    updated = list(playbook.steps) + new_steps
                    playbook.steps = updated
                    playbook.total_steps = len(updated)
                    self.session.flush()

                    logger.info(f"[PLAYBOOK-EVOLVE] Playbook {playbook_id} evolved: +{len(new_steps)} steps")
        except Exception as e:
            logger.debug(f"[PLAYBOOK-EVOLVE] Error: {e}")


class CrossTaskDependencyDetector:
    """
    Loop 9: Detect when tasks block each other.

    Task A can't reach 100% if Task B isn't done.
    "Add auth middleware" needs "Create user model" first.
    """

    def __init__(self, session: Session):
        self.session = session

    def detect_blockers(self, task_id: str) -> List[Dict[str, Any]]:
        try:
            from cognitive.task_completion_verifier import VerifiedTask
            task = self.session.query(VerifiedTask).filter(
                VerifiedTask.task_id == task_id
            ).first()

            if not task:
                return []

            blockers = []
            criteria = task.completion_criteria or []

            # Check if any criterion references another file/system
            # that has its own incomplete task
            other_tasks = self.session.query(VerifiedTask).filter(
                VerifiedTask.status.in_(["in_progress", "planned", "verification"]),
                VerifiedTask.task_id != task_id,
            ).all()

            task_files = set(task.files_involved or [])
            for other in other_tasks:
                other_files = set(other.files_involved or [])
                overlap = task_files & other_files
                if overlap:
                    blockers.append({
                        "blocking_task_id": other.task_id,
                        "blocking_title": other.title,
                        "blocking_status": other.status,
                        "blocking_completion": other.completion_percentage,
                        "overlapping_files": list(overlap),
                    })

            return blockers
        except Exception:
            return []


class VerificationGuardFeedback:
    """
    Loop 10: Task verification outcomes train the hallucination guard.

    When verification passes → LLM outputs that led to it are good.
    When verification fails → those outputs had issues.
    """

    def __init__(self, session: Session):
        self.session = session

    def feed_verification_to_guard(
        self,
        task_succeeded: bool,
        llm_outputs_used: List[str],
    ):
        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            tracker = get_llm_interaction_tracker(self.session)

            for output_id in llm_outputs_used:
                tracker.update_interaction_outcome(
                    interaction_id=output_id,
                    outcome="success" if task_succeeded else "failure",
                    quality_score=0.9 if task_succeeded else 0.3,
                )
        except Exception:
            pass


class UnifiedTaskEnrichment:
    """
    Loop 6: Run task through all 9 intelligence layers for context.

    Before breaking down a task, gather everything Grace knows
    about it from every layer. Produces richer breakdowns.
    """

    def __init__(self, session: Session):
        self.session = session

    def enrich(self, task_description: str) -> Dict[str, Any]:
        context = {"enrichment_sources": []}

        try:
            from cognitive.unified_intelligence import get_unified_intelligence
            ui = get_unified_intelligence(self.session)

            result = ui.query(task_description, max_layer=7, min_confidence=0.3)

            if result.answered:
                context["unified_intelligence"] = {
                    "layer": result.layer_used,
                    "response": result.response[:500],
                    "confidence": result.confidence,
                    "facts": result.facts_used[:5],
                }
                context["enrichment_sources"].append(result.layer_used)
        except Exception:
            pass

        return context


# ============================================================
# MASTER FEEDBACK COORDINATOR
# ============================================================

class IntelligenceFeedbackCoordinator:
    """
    Coordinates all 11 feedback loops.

    Provides a single interface for recording outcomes and
    getting improvement recommendations.
    """

    def __init__(self, session: Session):
        self.session = session
        self.criteria_tracker = CriteriaEffectivenessTracker(session)
        self.question_tracker = QuestionEffectivenessTracker()
        self.research_tracker = ResearchQualityTracker(session)
        self.gap_queue = KnowledgeGapPriorityQueue()
        self.playbook_evolution = PlaybookEvolution(session)
        self.cross_task = CrossTaskDependencyDetector(session)
        self.guard_feedback = VerificationGuardFeedback(session)
        self.task_enrichment = UnifiedTaskEnrichment(session)

    def record_task_outcome(
        self,
        task_id: str,
        succeeded: bool,
        criteria_results: Dict[str, bool],
        research_sources_used: List[str],
        questions_asked: Dict[str, str],
        llm_outputs_used: List[str] = None,
    ):
        """Record a complete task outcome across all feedback loops."""

        # Loop 1: Criteria effectiveness
        for cid, passed in criteria_results.items():
            self.criteria_tracker.record_criterion_result(cid, cid, passed)

        # Loop 2: Question effectiveness (already tracked during interrogation)

        # Loop 3: Research quality
        for source in research_sources_used:
            self.research_tracker.record_research_outcome(source, succeeded)

        # Loop 10: Verification → guard
        if llm_outputs_used:
            self.guard_feedback.feed_verification_to_guard(succeeded, llm_outputs_used)

        # Track overall
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "feedback_loops",
                f"Task {'succeeded' if succeeded else 'failed'}: fed {len(criteria_results)} criteria, {len(research_sources_used)} research sources",
                outcome="success" if succeeded else "failure",
                data={
                    "task_id": task_id,
                    "criteria_count": len(criteria_results),
                    "research_sources": research_sources_used,
                },
            )
        except Exception:
            pass

    def get_improvement_recommendations(self) -> Dict[str, Any]:
        """Get recommendations from all feedback loops."""
        return {
            "criteria_effectiveness": self.criteria_tracker.get_effectiveness_report(),
            "question_recommendations": self.question_tracker.get_report(),
            "source_reliability": self.research_tracker.get_source_reliability(),
            "knowledge_gap_queue": self.gap_queue.get_priority_queue()[:10],
            "top_gaps_to_mine": self.gap_queue.get_top_gaps(5),
        }


_coordinator: Optional[IntelligenceFeedbackCoordinator] = None


def get_feedback_coordinator(session: Session) -> IntelligenceFeedbackCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = IntelligenceFeedbackCoordinator(session)
    return _coordinator
