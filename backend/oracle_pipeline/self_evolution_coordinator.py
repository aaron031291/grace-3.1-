"""
Self-Evolution Coordinator

The capstone: connects self-healing, self-learning, self-building, and the
coding agent through Kimi/Deep Reasoning to the Oracle, KNN discovery, and
training data. This is what makes Grace self-evolving.

Self-Healing asks Kimi: "What's broken? What's the root cause?"
Self-Learning asks Kimi: "What's missing? What should I learn next?"
Self-Building asks Kimi: "What should I build? Is there a better design?"
Coding Agent asks Kimi:  "Is this code correct? What's the bug?"

Kimi reads the Oracle (all knowledge), the KNN discovery (what's related),
the training data (what Grace has learned), the source code (what exists),
and the memory systems (what Grace remembers) -- then provides grounded
answers that feed back into each pillar.

Kimi also refines and adds context to KNN search queries, making discovery
smarter over time. When KNN says "learn Rust because you know Python",
Kimi adds "specifically learn Rust's ownership model because it solves
the memory safety problems you've been hitting in Python."

Self-Healing + Self-Learning + Self-Building + Coding Agent
    + Kimi reasoning across Oracle + KNN + Training Data + Memory
    = Self-Evolution

The coordinator runs as a cycle:
  1. Each pillar reports its current situation (JSON)
  2. Kimi analyzes across all pillars + Oracle + KNN (reasoning)
  3. Kimi produces action plan with refined queries
  4. Actions route to appropriate pillar
  5. Results feed back into Oracle + training data
  6. KNN discovers more based on new knowledge
  7. Loop continues -> Grace evolves
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class PillarRole(str, Enum):
    """The four autonomous pillars + coding agent."""
    SELF_HEALING = "self_healing"
    SELF_LEARNING = "self_learning"
    SELF_BUILDING = "self_building"
    CODING_AGENT = "coding_agent"


class EvolutionActionType(str, Enum):
    """Types of evolution actions."""
    FIX_BUG = "fix_bug"
    LEARN_TOPIC = "learn_topic"
    BUILD_COMPONENT = "build_component"
    REFACTOR_CODE = "refactor_code"
    FILL_KNOWLEDGE_GAP = "fill_knowledge_gap"
    REFINE_SEARCH = "refine_search"
    IMPROVE_PROCESS = "improve_process"
    ADD_TEST = "add_test"
    UPDATE_TRAINING = "update_training"
    DEEPEN_DOMAIN = "deepen_domain"


@dataclass
class PillarSituation:
    """Current situation report from a pillar."""
    pillar: PillarRole
    status: str  # healthy, degraded, failing, learning, building
    active_issues: List[Dict[str, Any]]
    recent_successes: List[Dict[str, Any]]
    recent_failures: List[Dict[str, Any]]
    knowledge_gaps: List[str]
    current_tasks: List[str]
    metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON for Kimi."""
        return {
            "pillar": self.pillar.value,
            "status": self.status,
            "active_issues": self.active_issues,
            "recent_successes": self.recent_successes,
            "recent_failures": self.recent_failures,
            "knowledge_gaps": self.knowledge_gaps,
            "current_tasks": self.current_tasks,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EvolutionAction:
    """An action produced by the evolution coordinator."""
    action_id: str
    action_type: EvolutionActionType
    target_pillar: PillarRole
    description: str
    priority: int  # 1=critical, 5=low
    refined_queries: List[str]  # KNN-refined search queries
    reasoning: str  # Why this action was chosen
    confidence: float
    oracle_context: List[str]  # Relevant Oracle records
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvolutionCycleResult:
    """Result of one evolution cycle."""
    cycle_id: str
    cycle_number: int
    situations_analyzed: int
    actions_generated: int
    actions_by_pillar: Dict[str, int]
    refined_queries: int
    oracle_records_consulted: int
    knn_discoveries_triggered: int
    training_data_updated: int
    overall_health: float
    evolution_score: float  # How much Grace evolved in this cycle
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SelfEvolutionCoordinator:
    """
    Coordinates self-evolution across all pillars through Kimi and Oracle.

    The coordinator is the brain that connects:
    - Self-Healing: asks "what's broken?" -> Kimi diagnoses via Oracle
    - Self-Learning: asks "what's missing?" -> Kimi finds gaps via KNN
    - Self-Building: asks "what to build?" -> Kimi designs via source code
    - Coding Agent: asks "is this right?" -> Kimi verifies via Oracle

    Kimi refines KNN queries: instead of generic "learn Rust", Kimi adds
    context from Oracle to produce "learn Rust ownership model for memory
    safety, specifically borrow checker patterns for concurrent systems."

    The cycle:
    1. Pillars report situations
    2. Kimi reasons across Oracle + KNN + source + memory
    3. Actions route back to pillars with refined context
    4. Results feed Oracle + training data
    5. KNN discovers more based on new data
    6. Grace evolves
    """

    def __init__(self):
        # Connected systems
        self._deep_reasoning = None
        self._oracle = None
        self._knn_discovery = None
        self._proactive_discovery = None
        self._source_index = None

        # Pillar situations
        self._pillar_situations: Dict[PillarRole, PillarSituation] = {}

        # Evolution state
        self.actions: List[EvolutionAction] = []
        self.cycles: List[EvolutionCycleResult] = []
        self._cycle_count = 0
        self._evolution_score = 0.0

        # Metrics tracking
        self._pillar_metrics: Dict[PillarRole, Dict[str, float]] = {
            p: {"success_rate": 0.5, "issue_count": 0, "gap_count": 0}
            for p in PillarRole
        }

        logger.info("[SELF-EVOLUTION] Coordinator initialized")

    # =========================================================================
    # CONNECTIONS
    # =========================================================================

    def connect_deep_reasoning(self, reasoning) -> None:
        """Connect the Kimi/Deep Reasoning layer."""
        self._deep_reasoning = reasoning

    def connect_oracle(self, oracle) -> None:
        """Connect Oracle Vector Store."""
        self._oracle = oracle

    def connect_knn_discovery(self, knn) -> None:
        """Connect Reverse KNN Discovery."""
        self._knn_discovery = knn

    def connect_proactive_discovery(self, discovery) -> None:
        """Connect Proactive Discovery Engine."""
        self._proactive_discovery = discovery

    def connect_source_index(self, source_index) -> None:
        """Connect Source Code Index."""
        self._source_index = source_index

    def connect_from_loop(self, loop) -> None:
        """Connect from a PerpetualLearningLoop."""
        self.connect_oracle(loop.oracle)
        self.connect_knn_discovery(loop.knn)
        self.connect_proactive_discovery(loop.discovery)
        self.connect_source_index(loop.source_index)

    # =========================================================================
    # PILLAR SITUATION REPORTING
    # =========================================================================

    def report_situation(self, situation: PillarSituation) -> None:
        """A pillar reports its current situation."""
        self._pillar_situations[situation.pillar] = situation
        self._pillar_metrics[situation.pillar] = situation.metrics

    def report_healing_situation(
        self,
        active_issues: Optional[List[Dict[str, Any]]] = None,
        recent_fixes: Optional[List[Dict[str, Any]]] = None,
        recent_failures: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Self-healing reports its situation."""
        issues = active_issues or []
        status = "failing" if len(issues) > 3 else "degraded" if issues else "healthy"
        self.report_situation(PillarSituation(
            pillar=PillarRole.SELF_HEALING,
            status=status,
            active_issues=issues,
            recent_successes=recent_fixes or [],
            recent_failures=recent_failures or [],
            knowledge_gaps=[],
            current_tasks=[f"Fix: {i.get('description', 'unknown')}" for i in issues[:3]],
            metrics=metrics or {"success_rate": 0.5, "issue_count": len(issues)},
        ))

    def report_learning_situation(
        self,
        knowledge_gaps: Optional[List[str]] = None,
        recent_learnings: Optional[List[Dict[str, Any]]] = None,
        recent_failures: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Self-learning reports its situation."""
        gaps = knowledge_gaps or []
        self.report_situation(PillarSituation(
            pillar=PillarRole.SELF_LEARNING,
            status="learning" if gaps else "healthy",
            active_issues=[{"type": "knowledge_gap", "description": g} for g in gaps],
            recent_successes=recent_learnings or [],
            recent_failures=recent_failures or [],
            knowledge_gaps=gaps,
            current_tasks=[f"Learn: {g}" for g in gaps[:3]],
            metrics=metrics or {"success_rate": 0.5, "gap_count": len(gaps)},
        ))

    def report_building_situation(
        self,
        current_builds: Optional[List[str]] = None,
        recent_builds: Optional[List[Dict[str, Any]]] = None,
        build_failures: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Self-building reports its situation."""
        builds = current_builds or []
        self.report_situation(PillarSituation(
            pillar=PillarRole.SELF_BUILDING,
            status="building" if builds else "healthy",
            active_issues=[],
            recent_successes=recent_builds or [],
            recent_failures=build_failures or [],
            knowledge_gaps=[],
            current_tasks=builds[:3],
            metrics=metrics or {"success_rate": 0.5},
        ))

    def report_coding_agent_situation(
        self,
        current_bugs: Optional[List[Dict[str, Any]]] = None,
        code_questions: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Coding agent reports its situation."""
        bugs = current_bugs or []
        questions = code_questions or []
        self.report_situation(PillarSituation(
            pillar=PillarRole.CODING_AGENT,
            status="debugging" if bugs else "healthy",
            active_issues=bugs,
            recent_successes=[],
            recent_failures=[],
            knowledge_gaps=questions,
            current_tasks=[f"Debug: {b.get('description', '')}" for b in bugs[:3]],
            metrics=metrics or {"success_rate": 0.5, "bug_count": len(bugs)},
        ))

    # =========================================================================
    # EVOLUTION CYCLE
    # =========================================================================

    def run_evolution_cycle(self) -> EvolutionCycleResult:
        """
        Run one complete evolution cycle.

        1. Gather all pillar situations
        2. Consult Kimi for cross-pillar analysis
        3. Generate actions with refined KNN queries
        4. Route actions to pillars
        5. Update training data
        """
        start = datetime.now(timezone.utc)
        self._cycle_count += 1

        # Step 1: Build combined situation for Kimi
        combined_situation = self._build_combined_situation()

        # Step 2: Consult Kimi/reasoning
        kimi_analysis = self._consult_reasoning(combined_situation)

        # Step 3: Generate evolution actions
        actions = self._generate_actions(kimi_analysis, combined_situation)
        self.actions.extend(actions)

        # Step 4: Refine KNN queries through context
        refined_query_count = 0
        for action in actions:
            refined = self._refine_knn_queries(action)
            action.refined_queries = refined
            refined_query_count += len(refined)

        # Step 5: Count Oracle records consulted
        oracle_consulted = sum(
            len(a.oracle_context) for a in actions
        )

        # Step 6: Trigger KNN discoveries
        knn_triggered = self._trigger_knn_discoveries(actions)

        # Step 7: Update training data
        training_updated = self._update_training_data(actions)

        # Calculate evolution score
        self._evolution_score = self._calculate_evolution_score()

        # Build result
        actions_by_pillar = defaultdict(int)
        for a in actions:
            actions_by_pillar[a.target_pillar.value] += 1

        overall_health = self._calculate_overall_health()

        result = EvolutionCycleResult(
            cycle_id=f"evo-{uuid.uuid4().hex[:12]}",
            cycle_number=self._cycle_count,
            situations_analyzed=len(self._pillar_situations),
            actions_generated=len(actions),
            actions_by_pillar=dict(actions_by_pillar),
            refined_queries=refined_query_count,
            oracle_records_consulted=oracle_consulted,
            knn_discoveries_triggered=knn_triggered,
            training_data_updated=training_updated,
            overall_health=overall_health,
            evolution_score=self._evolution_score,
        )

        self.cycles.append(result)

        logger.info(
            f"[SELF-EVOLUTION] Cycle {self._cycle_count}: "
            f"{len(actions)} actions, "
            f"{refined_query_count} refined queries, "
            f"evolution={self._evolution_score:.2f}"
        )

        return result

    def _build_combined_situation(self) -> Dict[str, Any]:
        """Build combined JSON situation for Kimi."""
        situations = {}
        for pillar, sit in self._pillar_situations.items():
            situations[pillar.value] = sit.to_json()

        # Add Oracle context
        oracle_context = {}
        if self._oracle:
            oracle_context = {
                "total_records": len(self._oracle.records),
                "domains": self._oracle.get_all_domains(),
                "domain_stats": self._oracle.get_domain_stats(),
            }

        # Add source code context
        source_context = {}
        if self._source_index:
            stats = self._source_index.get_stats()
            source_context = {
                "modules": stats.get("total_modules", 0),
                "functions": stats.get("functions", 0),
                "classes": stats.get("classes", 0),
            }

        # Add discovery context
        discovery_context = {}
        if self._proactive_discovery:
            disc_stats = self._proactive_discovery.get_stats()
            discovery_context = {
                "queue_size": disc_stats.get("queue_size", 0),
                "active_domains": list(
                    getattr(self._proactive_discovery, '_domain_activity', {}).keys()
                ),
            }

        return {
            "pillars": situations,
            "oracle": oracle_context,
            "source_code": source_context,
            "discovery": discovery_context,
            "cycle_number": self._cycle_count,
            "evolution_score": self._evolution_score,
        }

    def _consult_reasoning(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Consult Kimi/Deep Reasoning for analysis."""
        if self._deep_reasoning:
            try:
                from .deep_reasoning_integration import ReasoningRequest, ReasoningTaskType
                result = self._deep_reasoning.reason(ReasoningRequest(
                    request_id=f"evo-{uuid.uuid4().hex[:12]}",
                    task_type=ReasoningTaskType.DEEP_ANALYSIS,
                    query="Analyze all pillar situations and recommend evolution actions.",
                    context=situation,
                ))
                return {
                    "conclusion": result.conclusion,
                    "recommendations": result.recommendations,
                    "confidence": result.confidence,
                    "reasoning_steps": len(result.reasoning_chain),
                }
            except Exception as e:
                logger.warning(f"[SELF-EVOLUTION] Reasoning failed: {e}")

        # Heuristic analysis
        return self._heuristic_analysis(situation)

    def _heuristic_analysis(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic analysis when Kimi is not available."""
        recommendations = []
        pillars = situation.get("pillars", {})

        for pillar_name, pillar_data in pillars.items():
            issues = pillar_data.get("active_issues", [])
            gaps = pillar_data.get("knowledge_gaps", [])
            failures = pillar_data.get("recent_failures", [])

            if issues:
                recommendations.append(
                    f"{pillar_name}: Fix {len(issues)} active issue(s)"
                )
            if gaps:
                recommendations.append(
                    f"{pillar_name}: Fill {len(gaps)} knowledge gap(s)"
                )
            if len(failures) > 2:
                recommendations.append(
                    f"{pillar_name}: Address recurring failures ({len(failures)})"
                )

        if not recommendations:
            recommendations.append("All pillars healthy. Continue learning.")

        return {
            "conclusion": f"Analyzed {len(pillars)} pillars.",
            "recommendations": recommendations,
            "confidence": 0.7,
            "reasoning_steps": 1,
        }

    def _generate_actions(
        self, analysis: Dict[str, Any], situation: Dict[str, Any]
    ) -> List[EvolutionAction]:
        """Generate evolution actions from analysis."""
        actions: List[EvolutionAction] = []
        pillars = situation.get("pillars", {})

        for pillar_name, pillar_data in pillars.items():
            try:
                pillar_role = PillarRole(pillar_name)
            except ValueError:
                continue

            # Generate actions for issues
            for issue in pillar_data.get("active_issues", [])[:3]:
                action_type = self._determine_action_type(pillar_role, issue)
                oracle_ctx = self._get_oracle_context(issue.get("description", ""))

                actions.append(EvolutionAction(
                    action_id=f"ea-{uuid.uuid4().hex[:12]}",
                    action_type=action_type,
                    target_pillar=pillar_role,
                    description=f"Address: {issue.get('description', 'unknown issue')}",
                    priority=2 if pillar_role == PillarRole.SELF_HEALING else 3,
                    refined_queries=[],
                    reasoning=f"Active issue in {pillar_name}",
                    confidence=analysis.get("confidence", 0.7),
                    oracle_context=oracle_ctx,
                ))

            # Generate actions for knowledge gaps
            for gap in pillar_data.get("knowledge_gaps", [])[:3]:
                oracle_ctx = self._get_oracle_context(gap)
                actions.append(EvolutionAction(
                    action_id=f"ea-{uuid.uuid4().hex[:12]}",
                    action_type=EvolutionActionType.FILL_KNOWLEDGE_GAP,
                    target_pillar=PillarRole.SELF_LEARNING,
                    description=f"Fill gap: {gap}",
                    priority=3,
                    refined_queries=[],
                    reasoning=f"Knowledge gap from {pillar_name}",
                    confidence=analysis.get("confidence", 0.7),
                    oracle_context=oracle_ctx,
                ))

        return actions

    def _determine_action_type(
        self, pillar: PillarRole, issue: Dict[str, Any]
    ) -> EvolutionActionType:
        """Determine action type based on pillar and issue."""
        issue_type = issue.get("type", "")

        if pillar == PillarRole.SELF_HEALING:
            return EvolutionActionType.FIX_BUG
        elif pillar == PillarRole.SELF_LEARNING:
            if "gap" in issue_type:
                return EvolutionActionType.FILL_KNOWLEDGE_GAP
            return EvolutionActionType.LEARN_TOPIC
        elif pillar == PillarRole.SELF_BUILDING:
            return EvolutionActionType.BUILD_COMPONENT
        elif pillar == PillarRole.CODING_AGENT:
            return EvolutionActionType.FIX_BUG

        return EvolutionActionType.IMPROVE_PROCESS

    def _get_oracle_context(self, query: str) -> List[str]:
        """Get relevant Oracle context for an action."""
        if not self._oracle or not query:
            return []
        results = self._oracle.search_by_content(query, limit=3)
        return [r.content[:150] for r in results if r.score > 0.1]

    # =========================================================================
    # KNN QUERY REFINEMENT (Kimi adds context to searches)
    # =========================================================================

    def _refine_knn_queries(self, action: EvolutionAction) -> List[str]:
        """
        Refine KNN discovery queries by adding Oracle context.

        Instead of generic "learn Rust", this produces:
        "learn Rust ownership model for memory safety,
         specifically borrow checker patterns for concurrent systems"
        """
        base_query = action.description
        refined: List[str] = []

        # Add Oracle context to make queries more specific
        if action.oracle_context:
            context_keywords = []
            for ctx in action.oracle_context[:2]:
                words = ctx.split()[:10]
                context_keywords.extend(w for w in words if len(w) > 4)

            if context_keywords:
                context_str = " ".join(context_keywords[:5])
                refined.append(f"{base_query} specifically {context_str}")

        # Add pillar-specific refinement
        if action.target_pillar == PillarRole.SELF_HEALING:
            refined.append(f"debugging techniques for: {base_query}")
            refined.append(f"root cause analysis: {base_query}")
        elif action.target_pillar == PillarRole.SELF_LEARNING:
            refined.append(f"tutorial: {base_query}")
            refined.append(f"best practices: {base_query}")
        elif action.target_pillar == PillarRole.SELF_BUILDING:
            refined.append(f"architecture patterns: {base_query}")
            refined.append(f"implementation guide: {base_query}")
        elif action.target_pillar == PillarRole.CODING_AGENT:
            refined.append(f"code fix: {base_query}")
            refined.append(f"debugging: {base_query}")

        if not refined:
            refined.append(base_query)

        return refined

    def _trigger_knn_discoveries(self, actions: List[EvolutionAction]) -> int:
        """Trigger KNN discoveries based on refined queries."""
        triggered = 0
        if not self._knn_discovery:
            return 0

        domains_to_discover = set()
        for action in actions:
            if action.action_type == EvolutionActionType.FILL_KNOWLEDGE_GAP:
                # Extract domain from action description
                desc_lower = action.description.lower()
                for domain in ["python", "rust", "javascript", "devops",
                               "ai_ml", "security", "business"]:
                    if domain in desc_lower:
                        domains_to_discover.add(domain)

        for domain in domains_to_discover:
            try:
                result = self._knn_discovery.discover_neighbors(domain)
                triggered += result.total_discovered
            except Exception as e:
                logger.warning(f"[SELF-EVOLUTION] KNN discovery error: {e}")

        return triggered

    def _update_training_data(self, actions: List[EvolutionAction]) -> int:
        """Update Oracle training data with evolution results."""
        updated = 0
        if not self._oracle:
            return 0

        for action in actions:
            if action.refined_queries:
                # Store the refined queries as training data
                content = (
                    f"Evolution action: {action.description}\n"
                    f"Refined queries: {'; '.join(action.refined_queries)}\n"
                    f"Reasoning: {action.reasoning}"
                )
                records = self._oracle.ingest(
                    content=content,
                    domain="self_evolution",
                    trust_score=0.9,
                    tags=["evolution", action.target_pillar.value, action.action_type.value],
                    metadata={
                        "action_id": action.action_id,
                        "cycle": self._cycle_count,
                    },
                )
                updated += len(records)

        return updated

    # =========================================================================
    # METRICS AND SCORING
    # =========================================================================

    def _calculate_evolution_score(self) -> float:
        """
        Calculate how much Grace has evolved.

        Based on:
        - Actions completed successfully
        - Knowledge gaps filled
        - Issues resolved
        - Training data growth
        """
        if not self.cycles:
            return 0.0

        total_actions = sum(c.actions_generated for c in self.cycles)
        total_refined = sum(c.refined_queries for c in self.cycles)
        total_training = sum(c.training_data_updated for c in self.cycles)
        total_knn = sum(c.knn_discoveries_triggered for c in self.cycles)

        # Score components
        action_score = min(total_actions / 50, 1.0) * 0.3
        query_score = min(total_refined / 100, 1.0) * 0.2
        training_score = min(total_training / 50, 1.0) * 0.3
        discovery_score = min(total_knn / 20, 1.0) * 0.2

        return min(action_score + query_score + training_score + discovery_score, 1.0)

    def _calculate_overall_health(self) -> float:
        """Calculate overall system health from pillar metrics."""
        if not self._pillar_metrics:
            return 0.5
        rates = [
            m.get("success_rate", 0.5) for m in self._pillar_metrics.values()
        ]
        return sum(rates) / len(rates)

    # =========================================================================
    # ACTION MANAGEMENT
    # =========================================================================

    def get_pending_actions(
        self, pillar: Optional[PillarRole] = None
    ) -> List[EvolutionAction]:
        """Get pending actions, optionally for a specific pillar."""
        actions = [a for a in self.actions if a.status == "pending"]
        if pillar:
            actions = [a for a in actions if a.target_pillar == pillar]
        return actions

    def complete_action(
        self, action_id: str, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark an action as completed."""
        for action in self.actions:
            if action.action_id == action_id:
                action.status = "completed"
                action.result = result or {}
                return True
        return False

    def fail_action(
        self, action_id: str, error: str
    ) -> bool:
        """Mark an action as failed."""
        for action in self.actions:
            if action.action_id == action_id:
                action.status = "failed"
                action.result = {"error": error}
                return True
        return False

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get evolution coordinator statistics."""
        completed = sum(1 for a in self.actions if a.status == "completed")
        failed = sum(1 for a in self.actions if a.status == "failed")
        pending = sum(1 for a in self.actions if a.status == "pending")

        return {
            "total_cycles": self._cycle_count,
            "evolution_score": self._evolution_score,
            "overall_health": self._calculate_overall_health(),
            "total_actions": len(self.actions),
            "actions_completed": completed,
            "actions_failed": failed,
            "actions_pending": pending,
            "pillar_situations": {
                p.value: s.status
                for p, s in self._pillar_situations.items()
            },
            "has_deep_reasoning": self._deep_reasoning is not None,
            "has_oracle": self._oracle is not None,
            "has_knn": self._knn_discovery is not None,
        }
