"""
Task Playbook Engine

Every task is unique. Grace needs to know:
  - What subtasks make up this task?
  - What ORDER do they need to happen in?
  - What DEPENDENCIES exist between subtasks?
  - What does 100% look like for each subtask?

First time: Kimi breaks it down (reads the task, produces ordered subtasks).
On completion: The breakdown becomes a PLAYBOOK saved in the Knowledge Compiler.
Next similar task: Grace uses the playbook directly, skips Kimi.

FLOW:
  1. User requests: "Add authentication to the API"
  2. Grace checks: Do I have a playbook for this type?
  3. NO playbook → Ask Kimi to break it down
  4. Kimi produces:
     Step 1: Read existing auth code (no deps)
     Step 2: Design auth flow (depends on 1)
     Step 3: Implement auth middleware (depends on 2)
     Step 4: Add login/logout endpoints (depends on 3)
     Step 5: Write tests (depends on 3, 4)
     Step 6: Run tests (depends on 5)
     Step 7: Update docs (depends on 3, 4)
  5. Grace executes in dependency order, verifies each step
  6. On 100% → Save as playbook: "api_authentication"
  7. Next time "Add auth to X" → Load playbook, adapt, execute

PLAYBOOKS are stored as CompiledProcedures with:
  - Ordered steps with dependencies
  - Completion criteria per step
  - Estimated time per step (from TimeSense)
  - Success/failure history
"""

import logging
import uuid
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Float, Integer, Text, JSON, Boolean
from database.base import BaseModel

logger = logging.getLogger(__name__)


class TaskPlaybook(BaseModel):
    """
    A reusable playbook for completing a type of task.

    Built from successful task completions.
    Used to skip Kimi for known task types.
    """
    __tablename__ = "task_playbooks"

    playbook_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(512), nullable=False)
    task_pattern = Column(String(256), nullable=False, index=True)
    description = Column(Text, nullable=True)

    steps = Column(JSON, nullable=False)
    # Each step: {
    #   "step_id": "S1",
    #   "order": 1,
    #   "action": "Read existing code",
    #   "details": "Examine current implementation",
    #   "depends_on": [],
    #   "completion_criteria": ["files_read", "understanding_documented"],
    #   "estimated_minutes": 10,
    #   "category": "analysis"
    # }

    total_steps = Column(Integer, default=0)
    estimated_total_minutes = Column(Integer, nullable=True)

    times_used = Column(Integer, default=0)
    times_succeeded = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    source = Column(String(64), default="kimi")  # kimi, manual, learned
    confidence = Column(Float, default=0.5)


@dataclass
class TaskBreakdown:
    """A breakdown of a task into ordered subtasks."""
    task_description: str
    steps: List[Dict[str, Any]]
    total_steps: int
    estimated_minutes: int
    playbook_id: Optional[str] = None
    from_playbook: bool = False
    from_kimi: bool = False


class TaskPlaybookEngine:
    """
    Manages task breakdowns and playbooks.

    First time: asks Kimi to break down the task.
    After completion: saves as playbook.
    Next time: loads playbook, skips Kimi.
    """

    def __init__(self, session: Session, kimi_brain=None):
        self.session = session
        self.kimi_brain = kimi_brain

    def interrogate_task(
        self,
        task_description: str,
        answers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Interrogate a task with WHAT/WHERE/WHEN/WHO/HOW/WHY questions
        BEFORE breaking it down. Identifies what's known vs unknown.

        If unknowns are blocking, returns questions for the user to answer.
        If everything is known or answerable, proceeds to breakdown.

        Args:
            task_description: The raw task request
            answers: Previously answered questions (for follow-up calls)

        Returns:
            Either questions to ask the user, or a complete breakdown
        """
        from cognitive.ambiguity import AmbiguityLedger, AmbiguityLevel

        ledger = AmbiguityLedger()

        # The 6 essential questions for any task
        questions = {
            "what": {
                "question": "What exactly needs to be done? What is the deliverable?",
                "extract_from": ["implement", "create", "fix", "add", "build", "remove", "update", "refactor"],
            },
            "where": {
                "question": "Where in the system does this change happen? Which files/modules?",
                "extract_from": [".py", ".js", ".ts", "module", "file", "component", "api", "endpoint"],
            },
            "why": {
                "question": "Why is this needed? What problem does it solve?",
                "extract_from": ["because", "since", "broken", "missing", "need", "require", "improve"],
            },
            "how": {
                "question": "How should it be implemented? Any specific approach?",
                "extract_from": ["using", "with", "via", "through", "approach", "pattern", "algorithm"],
            },
            "who": {
                "question": "Who or what system is affected? Who requested this?",
                "extract_from": ["user", "admin", "system", "grace", "kimi", "api", "frontend"],
            },
            "when": {
                "question": "When does this need to be done? Any deadline or priority?",
                "extract_from": ["urgent", "asap", "priority", "deadline", "before", "after", "now"],
            },
        }

        desc_lower = task_description.lower()
        needs_asking = []

        # Analyze the task description to see what we already know
        for q_key, q_data in questions.items():
            # Check if the task description already answers this
            has_indicator = any(ind in desc_lower for ind in q_data["extract_from"])

            # Check if user provided an answer previously
            if answers and q_key in answers:
                ledger.add_known(q_key, answers[q_key], notes=f"User answered: {answers[q_key]}")
            elif has_indicator:
                # Extract what we can from the description
                ledger.add_inferred(
                    q_key,
                    f"Inferred from description: {task_description[:200]}",
                    confidence=0.6,
                    notes="Extracted from task description"
                )
            else:
                # We don't know this
                is_blocking = q_key in ("what", "where")  # WHAT and WHERE are blocking
                ledger.add_unknown(q_key, blocking=is_blocking, notes=q_data["question"])
                needs_asking.append({
                    "key": q_key,
                    "question": q_data["question"],
                    "blocking": is_blocking,
                })

        # Check: are there blocking unknowns?
        blocking = ledger.get_blocking_unknowns()

        if blocking and not answers:
            # Return questions to ask the user
            return {
                "status": "needs_clarification",
                "task": task_description,
                "ambiguity": ledger.to_dict(),
                "summary": ledger.summary(),
                "questions": needs_asking,
                "blocking_questions": [
                    {"key": b.key, "question": b.notes}
                    for b in blocking
                ],
                "can_proceed": False,
                "message": (
                    f"Task has {len(blocking)} blocking unknowns. "
                    "Please answer the blocking questions before proceeding."
                ),
            }

        # No blocking unknowns -- proceed to breakdown
        # Merge answers into context
        context = {"ambiguity": ledger.to_dict()}
        if answers:
            context["user_answers"] = answers

        breakdown = self.break_down_task(task_description, context)

        return {
            "status": "ready",
            "task": task_description,
            "ambiguity": ledger.to_dict(),
            "summary": ledger.summary(),
            "questions_answered": len(ledger.get_by_level(AmbiguityLevel.KNOWN)),
            "questions_inferred": len(ledger.get_by_level(AmbiguityLevel.INFERRED)),
            "can_proceed": True,
            "breakdown": {
                "steps": breakdown.steps,
                "total_steps": breakdown.total_steps,
                "estimated_minutes": breakdown.estimated_minutes,
                "from_playbook": breakdown.from_playbook,
                "from_kimi": breakdown.from_kimi,
            },
        }

    def break_down_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskBreakdown:
        """
        Break a task into ordered subtasks with dependencies.

        Checks playbooks first. Falls back to Kimi if no playbook.
        Falls back to heuristic if no Kimi.
        """
        # Step 1: Check if we have a playbook for this type
        playbook = self._find_matching_playbook(task_description)

        if playbook and playbook.confidence >= 0.7:
            logger.info(f"[PLAYBOOK] Using playbook '{playbook.name}' (used {playbook.times_used} times)")
            playbook.times_used += 1
            self.session.flush()

            return TaskBreakdown(
                task_description=task_description,
                steps=self._adapt_playbook_steps(playbook.steps, task_description),
                total_steps=playbook.total_steps,
                estimated_minutes=playbook.estimated_total_minutes or 60,
                playbook_id=playbook.playbook_id,
                from_playbook=True,
            )

        # Step 2: Ask Kimi to break it down
        if self.kimi_brain:
            kimi_breakdown = self._ask_kimi_breakdown(task_description, context)
            if kimi_breakdown:
                return kimi_breakdown

        # Step 3: Heuristic breakdown
        return self._heuristic_breakdown(task_description)

    def _find_matching_playbook(self, task_description: str) -> Optional[TaskPlaybook]:
        """Find a playbook that matches this task type."""
        # Extract task pattern keywords
        keywords = self._extract_task_pattern(task_description)

        # Search by pattern
        playbooks = self.session.query(TaskPlaybook).filter(
            TaskPlaybook.confidence >= 0.5
        ).order_by(TaskPlaybook.success_rate.desc()).all()

        best_match = None
        best_score = 0

        for pb in playbooks:
            # Score based on keyword overlap with pattern
            pattern_words = set(pb.task_pattern.lower().split())
            keyword_set = set(keywords.lower().split()) if isinstance(keywords, str) else set(keywords)
            overlap = len(pattern_words & keyword_set)
            if overlap > best_score:
                best_score = overlap
                best_match = pb

        if best_match and best_score >= 2:
            return best_match

        return None

    def _extract_task_pattern(self, task_description: str) -> str:
        """Extract a pattern identifier from a task description."""
        import re
        # Remove filler words, keep action + subject
        words = task_description.lower().split()
        stop_words = {'the', 'a', 'an', 'to', 'for', 'in', 'on', 'at', 'of', 'and', 'or', 'is', 'it', 'this', 'that', 'with'}
        meaningful = [w for w in words if w not in stop_words and len(w) > 2]
        return " ".join(meaningful[:6])

    def _ask_kimi_breakdown(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
    ) -> Optional[TaskBreakdown]:
        """Ask Kimi to break down the task into ordered subtasks."""
        try:
            instruction_set = self.kimi_brain.produce_instructions(
                user_request=f"Break down this task into ordered steps with dependencies: {task_description}",
                context=context,
            )

            steps = []
            for i, instruction in enumerate(instruction_set.instructions):
                step = {
                    "step_id": f"S{i+1}",
                    "order": i + 1,
                    "action": instruction.what,
                    "details": instruction.why,
                    "depends_on": [f"S{i}"] if i > 0 else [],
                    "completion_criteria": [
                        h.get("action", h.get("detail", ""))
                        for h in instruction.how
                    ],
                    "estimated_minutes": 15,
                    "category": instruction.instruction_type.value,
                    "kimi_confidence": instruction.confidence,
                }
                steps.append(step)

            if not steps:
                return None

            total_minutes = sum(s.get("estimated_minutes", 15) for s in steps)

            # Track this breakdown
            try:
                from cognitive.learning_hook import track_learning_event
                track_learning_event(
                    "kimi_task_breakdown",
                    f"Kimi broke down '{task_description[:100]}' into {len(steps)} steps",
                    data={"steps": len(steps), "estimated_minutes": total_minutes},
                )
            except Exception:
                pass

            return TaskBreakdown(
                task_description=task_description,
                steps=steps,
                total_steps=len(steps),
                estimated_minutes=total_minutes,
                from_kimi=True,
            )

        except Exception as e:
            logger.warning(f"[PLAYBOOK] Kimi breakdown failed: {e}")
            return None

    def _heuristic_breakdown(self, task_description: str) -> TaskBreakdown:
        """Heuristic task breakdown when no playbook or Kimi available."""
        desc_lower = task_description.lower()

        if any(w in desc_lower for w in ['fix', 'bug', 'error', 'broken']):
            steps = [
                {"step_id": "S1", "order": 1, "action": "Reproduce the issue", "depends_on": [], "completion_criteria": ["issue_reproduced"], "estimated_minutes": 10, "category": "investigation"},
                {"step_id": "S2", "order": 2, "action": "Identify root cause", "depends_on": ["S1"], "completion_criteria": ["root_cause_found"], "estimated_minutes": 15, "category": "analysis"},
                {"step_id": "S3", "order": 3, "action": "Implement fix", "depends_on": ["S2"], "completion_criteria": ["code_changed", "fix_applied"], "estimated_minutes": 20, "category": "coding"},
                {"step_id": "S4", "order": 4, "action": "Write test for the fix", "depends_on": ["S3"], "completion_criteria": ["test_written"], "estimated_minutes": 10, "category": "testing"},
                {"step_id": "S5", "order": 5, "action": "Run all tests", "depends_on": ["S4"], "completion_criteria": ["all_tests_pass"], "estimated_minutes": 5, "category": "testing"},
                {"step_id": "S6", "order": 6, "action": "Verify fix resolves original issue", "depends_on": ["S5"], "completion_criteria": ["issue_resolved"], "estimated_minutes": 5, "category": "verification"},
            ]
        elif any(w in desc_lower for w in ['add', 'create', 'implement', 'build', 'new']):
            steps = [
                {"step_id": "S1", "order": 1, "action": "Understand requirements", "depends_on": [], "completion_criteria": ["requirements_clear"], "estimated_minutes": 10, "category": "analysis"},
                {"step_id": "S2", "order": 2, "action": "Read existing related code", "depends_on": ["S1"], "completion_criteria": ["codebase_understood"], "estimated_minutes": 15, "category": "analysis"},
                {"step_id": "S3", "order": 3, "action": "Design the solution", "depends_on": ["S1", "S2"], "completion_criteria": ["design_documented"], "estimated_minutes": 10, "category": "planning"},
                {"step_id": "S4", "order": 4, "action": "Implement the code", "depends_on": ["S3"], "completion_criteria": ["code_written", "syntax_valid"], "estimated_minutes": 30, "category": "coding"},
                {"step_id": "S5", "order": 5, "action": "Wire into existing system", "depends_on": ["S4"], "completion_criteria": ["startup_wired", "api_registered"], "estimated_minutes": 10, "category": "integration"},
                {"step_id": "S6", "order": 6, "action": "Write tests", "depends_on": ["S4"], "completion_criteria": ["tests_written", "tests_verify_logic"], "estimated_minutes": 15, "category": "testing"},
                {"step_id": "S7", "order": 7, "action": "Run tests and verify", "depends_on": ["S5", "S6"], "completion_criteria": ["all_tests_pass", "no_warnings"], "estimated_minutes": 5, "category": "verification"},
                {"step_id": "S8", "order": 8, "action": "Track in learning system", "depends_on": ["S4"], "completion_criteria": ["learning_hook_added"], "estimated_minutes": 5, "category": "integration"},
            ]
        elif any(w in desc_lower for w in ['refactor', 'improve', 'optimize', 'clean']):
            steps = [
                {"step_id": "S1", "order": 1, "action": "Read current implementation", "depends_on": [], "completion_criteria": ["code_understood"], "estimated_minutes": 15, "category": "analysis"},
                {"step_id": "S2", "order": 2, "action": "Run existing tests (baseline)", "depends_on": ["S1"], "completion_criteria": ["baseline_recorded"], "estimated_minutes": 5, "category": "testing"},
                {"step_id": "S3", "order": 3, "action": "Apply refactoring", "depends_on": ["S1", "S2"], "completion_criteria": ["code_refactored"], "estimated_minutes": 25, "category": "coding"},
                {"step_id": "S4", "order": 4, "action": "Run tests (verify no regression)", "depends_on": ["S3"], "completion_criteria": ["all_tests_pass", "no_regression"], "estimated_minutes": 5, "category": "testing"},
                {"step_id": "S5", "order": 5, "action": "Verify improvement metrics", "depends_on": ["S4"], "completion_criteria": ["improvement_measured"], "estimated_minutes": 5, "category": "verification"},
            ]
        else:
            steps = [
                {"step_id": "S1", "order": 1, "action": "Analyze the request", "depends_on": [], "completion_criteria": ["request_understood"], "estimated_minutes": 10, "category": "analysis"},
                {"step_id": "S2", "order": 2, "action": "Plan approach", "depends_on": ["S1"], "completion_criteria": ["plan_defined"], "estimated_minutes": 10, "category": "planning"},
                {"step_id": "S3", "order": 3, "action": "Execute", "depends_on": ["S2"], "completion_criteria": ["execution_complete"], "estimated_minutes": 30, "category": "execution"},
                {"step_id": "S4", "order": 4, "action": "Verify result", "depends_on": ["S3"], "completion_criteria": ["result_verified"], "estimated_minutes": 10, "category": "verification"},
            ]

        total_minutes = sum(s.get("estimated_minutes", 15) for s in steps)

        return TaskBreakdown(
            task_description=task_description,
            steps=steps,
            total_steps=len(steps),
            estimated_minutes=total_minutes,
        )

    def _adapt_playbook_steps(
        self,
        steps: List[Dict[str, Any]],
        task_description: str,
    ) -> List[Dict[str, Any]]:
        """Adapt generic playbook steps to the specific task."""
        adapted = []
        for step in steps:
            adapted_step = dict(step)
            adapted_step["adapted_for"] = task_description[:100]
            adapted.append(adapted_step)
        return adapted

    def save_as_playbook(
        self,
        task_description: str,
        steps: List[Dict[str, Any]],
        task_type: str = "general",
        source: str = "completed_task",
    ) -> TaskPlaybook:
        """
        Save a successful task breakdown as a reusable playbook.

        Called after a task reaches 100% completion.
        """
        playbook_id = f"PB-{uuid.uuid4().hex[:12]}"
        pattern = self._extract_task_pattern(task_description)

        total_minutes = sum(s.get("estimated_minutes", 15) for s in steps)

        playbook = TaskPlaybook(
            playbook_id=playbook_id,
            name=f"{task_type.title()}: {task_description[:200]}",
            task_pattern=pattern,
            description=task_description,
            steps=steps,
            total_steps=len(steps),
            estimated_total_minutes=total_minutes,
            times_used=1,
            times_succeeded=1,
            success_rate=1.0,
            source=source,
            confidence=0.7,
        )

        self.session.add(playbook)
        self.session.flush()

        # Also compile as a procedure in the Knowledge Compiler
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            from cognitive.knowledge_compiler import CompiledProcedure
            proc = CompiledProcedure(
                name=f"playbook_{pattern.replace(' ', '_')[:100]}",
                goal=task_description[:500],
                domain=task_type,
                steps=[{"step": s["order"], "action": s["action"], "detail": s.get("details", "")} for s in steps],
                preconditions=[s.get("depends_on", []) for s in steps if s.get("depends_on")],
                expected_outcome="Task completed 100%",
                confidence=0.7,
            )
            self.session.add(proc)
            self.session.flush()
        except Exception as e:
            logger.debug(f"[PLAYBOOK] Procedure compilation failed: {e}")

        logger.info(f"[PLAYBOOK] Saved playbook '{playbook.name}' ({len(steps)} steps)")

        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "playbook_created",
                f"New playbook: {playbook.name}",
                data={"playbook_id": playbook_id, "steps": len(steps), "pattern": pattern},
            )
        except Exception:
            pass

        return playbook

    def update_playbook_outcome(self, playbook_id: str, success: bool):
        """Update a playbook's success rate after use."""
        playbook = self.session.query(TaskPlaybook).filter(
            TaskPlaybook.playbook_id == playbook_id
        ).first()

        if not playbook:
            return

        if success:
            playbook.times_succeeded += 1
        total = playbook.times_used
        if total > 0:
            playbook.success_rate = playbook.times_succeeded / total
            playbook.confidence = min(0.95, 0.5 + (playbook.success_rate * 0.3) + (min(total, 10) / 10 * 0.15))

        self.session.flush()

    def get_execution_order(self, steps: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Calculate the correct execution order based on dependencies.

        Returns steps grouped into waves -- each wave can run in parallel,
        but must complete before the next wave starts.

        Returns:
            List of waves, each wave is a list of steps that can run together.
        """
        completed = set()
        remaining = list(steps)
        waves = []

        while remaining:
            wave = []
            still_remaining = []

            for step in remaining:
                deps = set(step.get("depends_on", []))
                if deps.issubset(completed):
                    wave.append(step)
                else:
                    still_remaining.append(step)

            if not wave:
                # Circular dependency or missing dependency -- force remaining into last wave
                wave = still_remaining
                still_remaining = []

            waves.append(wave)
            completed.update(s["step_id"] for s in wave)
            remaining = still_remaining

        return waves

    def list_playbooks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all saved playbooks."""
        playbooks = self.session.query(TaskPlaybook).order_by(
            TaskPlaybook.success_rate.desc()
        ).limit(limit).all()

        return [
            {
                "playbook_id": pb.playbook_id,
                "name": pb.name,
                "pattern": pb.task_pattern,
                "steps": pb.total_steps,
                "estimated_minutes": pb.estimated_total_minutes,
                "times_used": pb.times_used,
                "success_rate": pb.success_rate,
                "confidence": pb.confidence,
                "source": pb.source,
            }
            for pb in playbooks
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get playbook statistics."""
        try:
            total = self.session.query(TaskPlaybook).count()
            high_conf = self.session.query(TaskPlaybook).filter(
                TaskPlaybook.confidence >= 0.7
            ).count()
            total_uses = sum(
                pb.times_used for pb in self.session.query(TaskPlaybook).all()
            )
            return {
                "total_playbooks": total,
                "high_confidence": high_conf,
                "total_uses": total_uses,
                "kimi_calls_saved": total_uses - total,  # Each reuse = 1 saved Kimi call
            }
        except Exception:
            return {"total_playbooks": 0}


_engine_instance: Optional[TaskPlaybookEngine] = None


def get_task_playbook_engine(session: Session, kimi_brain=None) -> TaskPlaybookEngine:
    """Get or create the task playbook engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TaskPlaybookEngine(session, kimi_brain)
    return _engine_instance
