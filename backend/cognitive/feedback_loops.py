"""
Grace Feedback Loops (5 core loops, consolidated from 11)

Every task outcome flows through 5 self-improving loops:

1. QualityFeedback   - tracks criteria effectiveness + research quality + guard accuracy
2. KnowledgeGaps     - prioritizes gaps by frequency + tracks question effectiveness
3. PlaybookEvolution - playbooks improve with each use
4. WeightBackprop    - task outcomes adjust weights + cross-task dependency detection
5. TaskEnrichment    - enriches tasks with unified intelligence context
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QualityFeedback:
    """Loop 1: Merged criteria + research + verification guard feedback."""

    def __init__(self, session: Session):
        self.session = session
        self._criteria: Dict[str, Dict[str, int]] = defaultdict(lambda: {"checked": 0, "passed": 0, "failed": 0})
        self._sources: Dict[str, Dict[str, int]] = defaultdict(lambda: {"used": 0, "success": 0, "failure": 0})

    def record_criterion(self, criterion_id: str, passed: bool):
        s = self._criteria[criterion_id]
        s["checked"] += 1
        s["passed" if passed else "failed"] += 1

    def record_research_outcome(self, source: str, succeeded: bool):
        s = self._sources[source]
        s["used"] += 1
        s["success" if succeeded else "failure"] += 1
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            ws.propagate_outcome("success" if succeeded else "failure", source_type=source)
        except Exception:
            pass

    def record_guard_result(self, task_succeeded: bool, interaction_ids: List[str]):
        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            tracker = get_llm_interaction_tracker(self.session)
            for iid in interaction_ids:
                tracker.update_interaction_outcome(iid, "success" if task_succeeded else "failure", quality_score=0.9 if task_succeeded else 0.3)
        except Exception:
            pass

    def get_report(self) -> Dict[str, Any]:
        too_easy = [c for c, s in self._criteria.items() if s["checked"] >= 3 and s["failed"] == 0]
        too_hard = [c for c, s in self._criteria.items() if s["checked"] >= 3 and s["failed"] / s["checked"] > 0.8]
        source_reliability = {src: s["success"] / s["used"] if s["used"] > 0 else 0 for src, s in self._sources.items()}
        return {"too_easy_criteria": too_easy, "too_hard_criteria": too_hard, "source_reliability": source_reliability}


class KnowledgeGaps:
    """Loop 2: Merged gap priority + question effectiveness."""

    def __init__(self):
        self._gaps: Dict[str, int] = defaultdict(int)
        self._gap_contexts: Dict[str, List[str]] = defaultdict(list)
        self._questions: Dict[str, Dict[str, int]] = defaultdict(lambda: {"asked": 0, "self_resolved": 0, "user_answered": 0})

    def record_gap(self, topic: str, context: str = ""):
        self._gaps[topic] += 1
        if context:
            self._gap_contexts[topic].append(context[:200])

    def record_question(self, key: str, resolved_by: str):
        s = self._questions[key]
        s["asked"] += 1
        s[resolved_by if resolved_by in s else "user_answered"] += 1

    def get_priority_queue(self) -> List[Dict[str, Any]]:
        return sorted([{"topic": t, "frequency": c, "contexts": self._gap_contexts.get(t, [])[:3]} for t, c in self._gaps.items()], key=lambda x: x["frequency"], reverse=True)

    def get_skip_recommendations(self) -> List[str]:
        return [k for k, s in self._questions.items() if s["asked"] >= 5 and s["self_resolved"] / s["asked"] > 0.8]


class PlaybookEvolution:
    """Loop 3: Playbooks improve with each use."""

    def __init__(self, session: Session):
        self.session = session

    def record_modification(self, playbook_id: str, original_steps: List, actual_steps: List):
        if original_steps == actual_steps:
            return
        try:
            from cognitive.task_playbook_engine import TaskPlaybook
            pb = self.session.query(TaskPlaybook).filter(TaskPlaybook.playbook_id == playbook_id).first()
            if pb:
                orig_ids = {s.get("step_id") for s in original_steps}
                new_steps = [s for s in actual_steps if s.get("step_id") not in orig_ids]
                if new_steps:
                    pb.steps = list(pb.steps) + new_steps
                    pb.total_steps = len(pb.steps)
                    self.session.flush()
        except Exception:
            pass


class WeightBackprop:
    """Loop 4: Merged weight propagation + cross-task dependencies."""

    def __init__(self, session: Session):
        self.session = session

    def propagate(self, outcome: str, knowledge_ids: List[str] = None, pattern_ids: List[str] = None, source_type: str = None):
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            ws.propagate_outcome(outcome, knowledge_ids=knowledge_ids, pattern_ids=pattern_ids, source_type=source_type)
        except Exception:
            pass

    def detect_blockers(self, task_id: str) -> List[Dict[str, Any]]:
        try:
            from cognitive.task_completion_verifier import VerifiedTask
            task = self.session.query(VerifiedTask).filter(VerifiedTask.task_id == task_id).first()
            if not task:
                return []
            others = self.session.query(VerifiedTask).filter(VerifiedTask.status.in_(["in_progress", "planned"]), VerifiedTask.task_id != task_id).all()
            task_files = set(task.files_involved or [])
            return [{"blocking_task": o.task_id, "title": o.title, "overlap": list(task_files & set(o.files_involved or []))} for o in others if task_files & set(o.files_involved or [])]
        except Exception:
            return []


class TaskEnrichment:
    """Loop 5: Enriches tasks with unified intelligence context."""

    def __init__(self, session: Session):
        self.session = session

    def enrich(self, task_description: str) -> Dict[str, Any]:
        try:
            from cognitive.unified_intelligence import get_unified_intelligence
            ui = get_unified_intelligence(self.session)
            result = ui.query(task_description, max_layer=7, min_confidence=0.3)
            if result.answered:
                return {"layer": result.layer_used, "response": result.response[:500], "confidence": result.confidence}
        except Exception:
            pass
        return {}


class FeedbackCoordinator:
    """Single coordinator for all 5 loops."""

    def __init__(self, session: Session):
        self.session = session
        self.quality = QualityFeedback(session)
        self.gaps = KnowledgeGaps()
        self.playbooks = PlaybookEvolution(session)
        self.weights = WeightBackprop(session)
        self.enrichment = TaskEnrichment(session)

    def record_task_outcome(self, task_id: str, succeeded: bool, criteria_results: Dict[str, bool], research_sources: List[str], llm_outputs: List[str] = None):
        for cid, passed in criteria_results.items():
            self.quality.record_criterion(cid, passed)
        for source in research_sources:
            self.quality.record_research_outcome(source, succeeded)
        if llm_outputs:
            self.quality.record_guard_result(succeeded, llm_outputs)
        self.weights.propagate("success" if succeeded else "failure", source_type="task_execution")

        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event("feedback_loops", f"Task {'succeeded' if succeeded else 'failed'}", data={"task_id": task_id, "criteria": len(criteria_results)})
        except Exception:
            pass

    def get_recommendations(self) -> Dict[str, Any]:
        return {
            "quality": self.quality.get_report(),
            "knowledge_gaps": self.gaps.get_priority_queue()[:10],
            "skip_questions": self.gaps.get_skip_recommendations(),
        }


_coordinator: Optional[FeedbackCoordinator] = None

def get_feedback_coordinator(session: Session) -> FeedbackCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = FeedbackCoordinator(session)
    return _coordinator
