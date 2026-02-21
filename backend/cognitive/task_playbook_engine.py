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

        # SELF-RESEARCH: Before asking the user, try to answer unknowns ourselves
        # Web search + library connectors + compiled knowledge
        unknowns_before = len(needs_asking)
        if needs_asking:
            self._self_research_unknowns(task_description, ledger, needs_asking)
            # Re-check what's still unknown after research
            needs_asking = [q for q in needs_asking if ledger.get(q["key"]).level.value == "unknown"]

        # Check: are there STILL blocking unknowns after self-research?
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

        # DERIVE SPECIFIC COMPLETION CRITERIA from interrogation answers
        # This is what defines 100% for THIS specific task
        resolved_answers = {}
        for key in ["what", "where", "why", "how", "who", "when"]:
            entry = ledger.get(key)
            if entry and entry.level in (AmbiguityLevel.KNOWN, AmbiguityLevel.INFERRED):
                resolved_answers[key] = entry.value

        specific_criteria = self.derive_completion_criteria(
            task_description, resolved_answers, breakdown.steps
        )

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
            "completion_criteria": specific_criteria,
            "what_100_percent_means": {
                "total_criteria": len(specific_criteria),
                "by_category": {},
                "criteria": [
                    {"name": c["name"], "category": c.get("category", "general"), "auto": c.get("auto", False)}
                    for c in specific_criteria
                ],
            },
        }

    def _self_research_unknowns(
        self,
        task_description: str,
        ledger,
        unknowns: List[Dict[str, Any]],
    ):
        """
        Try to answer unknown questions using web search, library connectors,
        and compiled knowledge BEFORE asking the user.

        Grace should exhaust her own resources before bothering the user.
        """
        # Extract key terms for research
        import re
        words = re.findall(r'\b[A-Za-z]{4,}\b', task_description)
        key_terms = [w for w in words if w.lower() not in {
            'this', 'that', 'with', 'from', 'have', 'need', 'want',
            'make', 'should', 'could', 'would', 'please', 'just',
        }][:5]

        if not key_terms:
            return

        search_query = " ".join(key_terms)

        # 1. Check compiled knowledge store
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            for term in key_terms[:3]:
                facts = compiler.query_facts(subject=term, limit=3)
                if facts:
                    for unknown in list(unknowns):
                        if unknown["key"] == "what" and any("is" in f.get("predicate", "") for f in facts):
                            ledger.promote_to_known(
                                "what",
                                f"From knowledge: {facts[0]['subject']} {facts[0]['predicate']} {facts[0]['object']}"
                            )
                        elif unknown["key"] == "how" and any(f.get("predicate", "") in ("uses", "requires", "based_on") for f in facts):
                            parts = [f"{ff['subject']} {ff['predicate']} {ff['object']}" for ff in facts[:2]]
                            ledger.promote_to_known(
                                "how",
                                f"From knowledge: {', '.join(parts)}"
                            )
        except Exception:
            pass

        # 2. Check library connectors (ConceptNet for common sense)
        try:
            from cognitive.library_connectors import get_library_connectors
            lib = get_library_connectors()

            for term in key_terms[:2]:
                cn_facts = lib.query_conceptnet(term, limit=5)
                if cn_facts:
                    for unknown in list(unknowns):
                        if unknown["key"] == "what":
                            is_a = [f for f in cn_facts if f["predicate"] == "IsA"]
                            if is_a:
                                ledger.promote_to_known(
                                    "what",
                                    f"From ConceptNet: {is_a[0]['subject']} is a {is_a[0]['object']}"
                                )
                        elif unknown["key"] == "how":
                            used_for = [f for f in cn_facts if f["predicate"] in ("UsedFor", "HasPrerequisite")]
                            if used_for:
                                uf = used_for[0]
                                uf_text = uf.get('surface_text') or f"{uf['subject']} {uf['predicate']} {uf['object']}"
                                ledger.add_inferred(
                                    "how",
                                    f"From ConceptNet: {uf_text}",
                                    confidence=0.7,
                                )
        except Exception:
            pass

        # 3. Memory Mesh - episodic + procedural recall
        try:
            from cognitive.procedural_memory import ProceduralRepository
            proc_repo = ProceduralRepository(self.session)
            procs = proc_repo.find_procedures(task_description, limit=3)
            if procs:
                for unknown in list(unknowns):
                    if unknown["key"] == "how" and ledger.get("how").level.value == "unknown":
                        best = procs[0]
                        ledger.promote_to_known(
                            "how",
                            f"From procedural memory: {best.get('name', '')} - {best.get('goal', '')}"
                        )
                        break
        except Exception:
            pass

        try:
            from cognitive.episodic_memory import EpisodicBuffer
            buffer = EpisodicBuffer(self.session)
            episodes = buffer.recall_similar(task_description, limit=3)
            if episodes:
                for unknown in list(unknowns):
                    if unknown["key"] == "what" and ledger.get("what").level.value == "unknown":
                        best = episodes[0]
                        ledger.add_inferred(
                            "what",
                            f"From past experience: {best.get('problem', '')}",
                            confidence=0.65,
                            notes="Similar task found in episodic memory",
                        )
                    elif unknown["key"] == "why" and ledger.get("why").level.value == "unknown":
                        best = episodes[0]
                        outcome = best.get("outcome", {})
                        if isinstance(outcome, dict):
                            ledger.add_inferred(
                                "why",
                                f"From past experience: previous outcome was {outcome.get('success', 'unknown')}",
                                confidence=0.6,
                            )
        except Exception:
            pass

        # 4. Oracle ML - predict what this task needs based on features
        try:
            from startup import get_subsystems
            subs = get_subsystems()
            if subs.systems_integration:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_running():
                        prediction = loop.run_until_complete(
                            subs.systems_integration.oracle_predict(
                                "task_success",
                                {"task_description": task_description, "task_terms": key_terms}
                            )
                        )
                        if prediction.get("success") and prediction.get("factors"):
                            for unknown in list(unknowns):
                                if unknown["key"] == "how" and ledger.get("how").level.value in ("unknown", "assumed"):
                                    factors = prediction["factors"]
                                    if factors:
                                        ledger.add_inferred(
                                            "how",
                                            f"Oracle suggests: {', '.join(str(f) for f in factors[:3])}",
                                            confidence=0.55,
                                            notes="Predicted from Oracle ML task analysis",
                                        )
                except RuntimeError:
                    pass
        except Exception:
            pass

        # 5. Reverse lookup - check what QUESTIONS this task type usually needs
        # This is the reverse KNN idea: given a task, what knowledge gaps exist?
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            # Check if we have any compiled rules about this type of task
            rules = compiler.query_rules(context=task_description, limit=5)
            if rules:
                for unknown in list(unknowns):
                    if unknown["key"] == "how" and ledger.get("how").level.value == "unknown":
                        rule = rules[0]
                        ledger.add_inferred(
                            "how",
                            f"From decision rule: {rule.get('action', '')}",
                            confidence=0.65,
                            notes=rule.get("explanation", ""),
                        )

            # Check entity relationships for context
            for term in key_terms[:2]:
                entities = compiler.query_entities(entity=term, limit=5)
                if entities:
                    for unknown in list(unknowns):
                        if unknown["key"] == "what" and ledger.get("what").level.value == "unknown":
                            rel = entities[0]
                            ledger.add_inferred(
                                "what",
                                f"From entity graph: {rel['entity_a']} {rel['relation']} {rel['entity_b']}",
                                confidence=0.6,
                            )
        except Exception:
            pass

        # 6. KNOWLEDGE GAP DETECTION: Unanswered questions reveal missing knowledge
        # Record what we COULDN'T answer - this is new knowledge to acquire
        still_unknown = [u for u in unknowns if ledger.get(u["key"]).level.value == "unknown"]
        if still_unknown:
            try:
                from cognitive.learning_hook import track_learning_event
                track_learning_event(
                    "knowledge_gap_detected",
                    f"Task '{task_description[:100]}' has {len(still_unknown)} unanswered questions",
                    outcome="failure",
                    data={
                        "task": task_description[:200],
                        "gaps": [u["key"] for u in still_unknown],
                        "gap_questions": [u["question"] for u in still_unknown],
                        "terms_searched": key_terms,
                        "needs_acquisition": True,
                    },
                )

                # Auto-trigger library mining for the topic to fill the gap
                try:
                    from cognitive.library_connectors import get_library_connectors
                    lib = get_library_connectors()
                    for term in key_terms[:2]:
                        lib.mine_and_compile(term, session=self.session, sources=["wikidata", "conceptnet"])
                except Exception:
                    pass
            except Exception:
                pass

        # 7. Web search for context (if SerpAPI available)
        try:
            from search.serpapi_service import SerpAPIService
            from settings import settings

            if hasattr(settings, 'SERPAPI_KEY') and settings.SERPAPI_KEY:
                search_service = SerpAPIService(api_key=settings.SERPAPI_KEY)
                results = search_service.search(
                    f"{search_query} best practices how to",
                    num_results=3,
                )

                if results:
                    snippets = [r.get("snippet", "") for r in results if r.get("snippet")]

                    for unknown in list(unknowns):
                        if unknown["key"] == "why" and snippets:
                            ledger.add_inferred(
                                "why",
                                f"From web: {snippets[0][:200]}",
                                confidence=0.5,
                                notes="Inferred from web search results",
                            )
                        elif unknown["key"] == "how" and len(snippets) > 1:
                            ledger.add_inferred(
                                "how",
                                f"From web: {snippets[1][:200]}",
                                confidence=0.5,
                                notes="Inferred from web search results",
                            )

                    # Track the research
                    from cognitive.learning_hook import track_learning_event
                    track_learning_event(
                        "task_self_research",
                        f"Self-researched '{search_query}': {len(results)} web results, {len(snippets)} useful",
                        data={"query": search_query, "results": len(results)},
                    )
        except Exception:
            pass

    def derive_completion_criteria(
        self,
        task_description: str,
        interrogation_answers: Dict[str, Any],
        steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Derive SPECIFIC, MEASURABLE completion criteria from the task.

        Uses interrogation answers (WHAT/WHERE/HOW) to generate
        criteria unique to THIS task, not generic templates.

        Args:
            task_description: The full task description
            interrogation_answers: Resolved WHAT/WHERE/HOW/WHY/WHO/WHEN
            steps: The task breakdown steps

        Returns:
            List of specific, measurable completion criteria
        """
        criteria = []
        what = interrogation_answers.get("what", {})
        where = interrogation_answers.get("where", {})
        how = interrogation_answers.get("how", {})

        what_val = what.get("value", what) if isinstance(what, dict) else str(what)
        where_val = where.get("value", where) if isinstance(where, dict) else str(where)
        how_val = how.get("value", how) if isinstance(how, dict) else str(how)

        desc_lower = task_description.lower()

        # ---- CRITERIA FROM WHAT (the deliverable) ----
        if what_val:
            criteria.append({
                "id": "deliverable_exists",
                "name": f"Deliverable exists: {str(what_val)[:100]}",
                "auto": False,
                "category": "deliverable",
                "source": "what",
            })

        # ---- CRITERIA FROM WHERE (location) ----
        if where_val:
            # Extract file paths
            import re
            files = re.findall(r'[\w/]+\.(?:py|js|ts|jsx|tsx)', str(where_val))
            for f in files[:5]:
                criteria.append({
                    "id": f"file_modified_{f.replace('/', '_').replace('.', '_')}",
                    "name": f"File modified/created: {f}",
                    "auto": True,
                    "category": "location",
                    "source": "where",
                    "check_file": f,
                })

        # ---- CRITERIA FROM HOW (approach) ----
        if how_val:
            criteria.append({
                "id": "approach_implemented",
                "name": f"Approach implemented: {str(how_val)[:100]}",
                "auto": False,
                "category": "implementation",
                "source": "how",
            })

        # ---- CRITERIA FROM STEPS (each step must complete) ----
        for step in steps:
            step_criteria = step.get("completion_criteria", [])
            for sc in step_criteria:
                criteria.append({
                    "id": f"step_{step['step_id']}_{sc}" if isinstance(sc, str) else f"step_{step['step_id']}",
                    "name": f"[{step['step_id']}] {step['action']}: {sc}" if isinstance(sc, str) else f"[{step['step_id']}] {step['action']}",
                    "auto": False,
                    "category": "step_completion",
                    "source": "breakdown",
                    "step_id": step["step_id"],
                })

        # ---- CRITERIA FROM TASK TYPE PATTERNS ----
        # API endpoints
        if any(w in desc_lower for w in ["endpoint", "api", "route", "post", "get"]):
            endpoint_match = re.search(r'(?:POST|GET|PUT|DELETE)\s+/\w+', task_description, re.IGNORECASE)
            if endpoint_match:
                ep = endpoint_match.group()
                criteria.append({"id": "endpoint_registered", "name": f"Endpoint registered: {ep}", "auto": True, "category": "api"})
                criteria.append({"id": "endpoint_returns_success", "name": f"Endpoint returns 200 on valid request", "auto": True, "category": "api"})
                criteria.append({"id": "endpoint_returns_error", "name": f"Endpoint returns 400/401/404 on invalid request", "auto": True, "category": "api"})
            else:
                criteria.append({"id": "endpoint_registered", "name": "API endpoint registered in router", "auto": True, "category": "api"})

        # Authentication/security tasks
        if any(w in desc_lower for w in ["auth", "login", "password", "jwt", "token", "security"]):
            criteria.append({"id": "no_plaintext_secrets", "name": "No hardcoded secrets or plaintext passwords", "auto": True, "category": "security"})
            criteria.append({"id": "auth_failure_handled", "name": "Authentication failure returns proper error", "auto": False, "category": "security"})

        # Database tasks
        if any(w in desc_lower for w in ["database", "model", "table", "migration", "schema"]):
            criteria.append({"id": "migration_exists", "name": "Database migration exists", "auto": True, "category": "database"})
            criteria.append({"id": "model_has_constraints", "name": "Model has proper constraints (not null, indexes)", "auto": False, "category": "database"})

        # Testing tasks
        if any(w in desc_lower for w in ["test", "spec", "coverage"]):
            criteria.append({"id": "tests_cover_happy_path", "name": "Tests cover success case", "auto": False, "category": "testing"})
            criteria.append({"id": "tests_cover_error_path", "name": "Tests cover error/edge cases", "auto": False, "category": "testing"})

        # ---- UNIVERSAL CRITERIA (always apply) ----
        criteria.append({"id": "syntax_valid", "name": "All changed files parse without syntax errors", "auto": True, "category": "quality"})
        criteria.append({"id": "tests_pass", "name": "All tests pass (0 failures, 0 warnings)", "auto": True, "category": "quality"})
        criteria.append({"id": "no_regressions", "name": "No regressions in existing tests", "auto": True, "category": "quality"})

        # ---- CRITERIA FROM COMPILED KNOWLEDGE ----
        # Check if we have known requirements for this domain
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            import re as _re
            key_terms = _re.findall(r'\b[A-Z][a-z]+\b', task_description)[:3]
            for term in key_terms:
                rules = compiler.query_rules(context=term, limit=2)
                for rule in rules:
                    criteria.append({
                        "id": f"rule_{rule.get('rule_name', 'unknown')[:30]}",
                        "name": f"Compiled rule: {rule.get('action', '')[:100]}",
                        "auto": False,
                        "category": "compiled_knowledge",
                        "source": "knowledge_compiler",
                    })
        except Exception:
            pass

        # ---- CRITERIA FROM PLAYBOOK HISTORY ----
        # What criteria did similar past tasks use?
        try:
            playbook = self._find_matching_playbook(task_description)
            if playbook and playbook.steps:
                for step in playbook.steps[:5]:
                    for sc in step.get("completion_criteria", [])[:2]:
                        crit_name = f"[Playbook] {sc}" if isinstance(sc, str) else f"[Playbook] {step.get('action', '')}"
                        criteria.append({
                            "id": f"playbook_{step.get('step_id', 'x')}_{len(criteria)}",
                            "name": crit_name[:150],
                            "auto": False,
                            "category": "playbook_learned",
                            "source": f"playbook:{playbook.playbook_id}",
                        })
        except Exception:
            pass

        # Deduplicate by name
        seen = set()
        unique = []
        for c in criteria:
            if c["name"] not in seen:
                seen.add(c["name"])
                unique.append(c)

        return unique

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
