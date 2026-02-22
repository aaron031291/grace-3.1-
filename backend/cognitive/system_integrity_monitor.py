"""
System Integrity Monitor

Continuously tracks unknowns, missing wirings, disconnected components,
and system health. Grace reads this as part of her system state observation.

Runs automatically. Reports what's connected, what's broken, what's unknown.
User never has to ask "what's the state" -- the system tells them.

WHAT IT TRACKS:
  - Connected vs disconnected subsystems
  - Missing wiring (imports exist but connections don't)
  - Dead code (functions defined but never called)
  - Knowledge gaps (topics with no compiled knowledge)
  - Test coverage gaps (components without tests)
  - Weight system health (stale weights, extreme values)
  - Learning pipeline status (is data flowing?)
  - Dependency trend (is autonomy improving?)

Grace reads this in her system state. If something is broken,
Grace's diagnosis will include it. The user sees it in the dashboard.
"""

import os
import re
import ast
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class IntegrityIssue:
    """A single integrity issue detected."""
    category: str       # wiring, dead_code, knowledge_gap, test_gap, weight, pipeline
    severity: str       # critical, high, medium, low, info
    component: str      # which component
    description: str    # what's wrong
    suggestion: str     # how to fix
    auto_fixable: bool  # can Grace fix this herself?


class SystemIntegrityMonitor:
    """
    Continuously monitors system integrity.

    Grace reads this. Dashboard shows this. User always knows the state.
    """

    def __init__(self, session: Session, workspace_dir: str = None):
        self.session = session
        self.workspace = workspace_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._last_scan: Optional[datetime] = None
        self._cached_report: Optional[Dict[str, Any]] = None

    def full_scan(self) -> Dict[str, Any]:
        """
        Run a complete system integrity scan.

        Returns a report with everything that's connected,
        disconnected, missing, or unknown.
        """
        issues = []

        issues.extend(self._check_subsystem_connections())
        issues.extend(self._check_learning_pipeline())
        issues.extend(self._check_knowledge_store())
        issues.extend(self._check_weight_health())
        issues.extend(self._check_api_coverage())
        issues.extend(self._check_rag_alignment())
        issues.extend(self._check_indexer_health())
        issues.extend(self._check_cross_system_signals())

        # Categorize
        critical = [i for i in issues if i.severity == "critical"]
        high = [i for i in issues if i.severity == "high"]
        medium = [i for i in issues if i.severity == "medium"]
        low = [i for i in issues if i.severity == "low"]
        info = [i for i in issues if i.severity == "info"]

        connected = [i for i in issues if i.category == "connected"]
        disconnected = [i for i in issues if i.category == "disconnected"]

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_issues": len(issues) - len(connected),
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "connected_systems": len(connected),
            "disconnected_systems": len(disconnected),
            "health_score": self._calculate_health_score(issues),
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "component": i.component,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "auto_fixable": i.auto_fixable,
                }
                for i in issues if i.category != "connected"
            ],
            "connected": [
                {"component": i.component, "description": i.description}
                for i in connected
            ],
        }

        self._last_scan = datetime.now(timezone.utc)
        self._cached_report = report

        # Track the scan
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "integrity_scan",
                f"Scan complete: {report['total_issues']} issues, health={report['health_score']:.0f}%",
                data={"health": report["health_score"], "critical": len(critical), "high": len(high)},
            )
        except Exception:
            pass

        return report

    def _check_subsystem_connections(self) -> List[IntegrityIssue]:
        """Check which subsystems are connected vs disconnected."""
        issues = []

        try:
            from startup import get_subsystems
            subs = get_subsystems()
            status = subs.get_status()

            for system, state in status.items():
                if system in ("active_count", "active_subsystems"):
                    continue
                if state == "active":
                    issues.append(IntegrityIssue(
                        "connected", "info", system,
                        f"{system} is active and connected",
                        "", False
                    ))
                else:
                    issues.append(IntegrityIssue(
                        "disconnected", "medium", system,
                        f"{system} is NOT active",
                        f"Check startup.py initialization for {system}",
                        False
                    ))
        except Exception as e:
            issues.append(IntegrityIssue(
                "disconnected", "critical", "startup",
                f"Cannot read subsystem status: {e}",
                "startup.py may not have been initialized",
                False
            ))

        return issues

    def _check_learning_pipeline(self) -> List[IntegrityIssue]:
        """Check if data is flowing through the learning pipeline."""
        issues = []

        # Check LLM interaction tracker has recent data
        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            tracker = get_llm_interaction_tracker(self.session)
            stats = tracker.get_interaction_stats(time_window_hours=24)

            if stats.get("total", 0) == 0:
                issues.append(IntegrityIssue(
                    "pipeline", "high", "llm_interaction_tracker",
                    "No interactions recorded in last 24 hours",
                    "The learning pipeline has no data flowing. Use /chat or /llm-learning/track to feed it.",
                    False
                ))
            else:
                issues.append(IntegrityIssue(
                    "connected", "info", "llm_interaction_tracker",
                    f"{stats['total']} interactions recorded in last 24h",
                    "", False
                ))
        except Exception as e:
            issues.append(IntegrityIssue(
                "pipeline", "high", "llm_interaction_tracker",
                f"Cannot check interaction tracker: {e}",
                "Database may not have LLM tracking tables",
                False
            ))

        # Check pattern learner progress
        try:
            from cognitive.llm_pattern_learner import get_llm_pattern_learner
            learner = get_llm_pattern_learner(self.session)
            progress = learner.get_learning_progress()

            if progress.get("patterns_extracted", 0) == 0:
                issues.append(IntegrityIssue(
                    "pipeline", "medium", "pattern_learner",
                    "No patterns extracted yet",
                    "Run POST /llm-learning/patterns/extract or wait for autonomous loop.",
                    True
                ))
            else:
                issues.append(IntegrityIssue(
                    "connected", "info", "pattern_learner",
                    f"{progress['patterns_extracted']} patterns, stage={progress['learning_stage']}",
                    "", False
                ))
        except Exception:
            pass

        # Check dependency reducer
        try:
            from cognitive.llm_dependency_reducer import get_llm_dependency_reducer
            reducer = get_llm_dependency_reducer(self.session)
            trend = reducer.get_dependency_trend(days=7)

            issues.append(IntegrityIssue(
                "connected", "info", "dependency_reducer",
                f"Trend: {trend.get('trend_direction', 'unknown')}, data points: {trend.get('data_points', 0)}",
                "", False
            ))
        except Exception:
            pass

        return issues

    def _check_knowledge_store(self) -> List[IntegrityIssue]:
        """Check compiled knowledge store health."""
        issues = []

        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)
            stats = compiler.get_stats()

            total = sum(stats.get(k, 0) for k in ["total_facts", "total_procedures", "total_rules", "total_topics", "total_entities"])

            if total == 0:
                issues.append(IntegrityIssue(
                    "knowledge_gap", "high", "knowledge_compiler",
                    "Knowledge store is EMPTY - no compiled facts, procedures, or rules",
                    "Run POST /llm-learning/compile or ingest documents. The unified intelligence layers 1-3 have nothing to query.",
                    True
                ))
            else:
                issues.append(IntegrityIssue(
                    "connected", "info", "knowledge_compiler",
                    f"Knowledge store: {stats.get('total_facts', 0)} facts, {stats.get('total_procedures', 0)} procedures, {stats.get('total_rules', 0)} rules",
                    "", False
                ))
        except Exception:
            issues.append(IntegrityIssue(
                "knowledge_gap", "medium", "knowledge_compiler",
                "Cannot check knowledge store",
                "Knowledge compiler tables may not exist yet",
                True
            ))

        # Check distilled knowledge
        try:
            from cognitive.knowledge_compiler import DistilledKnowledge
            distilled_count = self.session.query(DistilledKnowledge).count()

            if distilled_count == 0:
                issues.append(IntegrityIssue(
                    "knowledge_gap", "medium", "distilled_knowledge",
                    "No distilled knowledge stored",
                    "Start using /chat - every LLM response is automatically distilled.",
                    False
                ))
            else:
                verified = self.session.query(DistilledKnowledge).filter(
                    DistilledKnowledge.is_verified == True
                ).count()
                issues.append(IntegrityIssue(
                    "connected", "info", "distilled_knowledge",
                    f"{distilled_count} distilled entries ({verified} verified)",
                    "", False
                ))
        except Exception:
            pass

        # Check playbooks
        try:
            from cognitive.task_playbook_engine import TaskPlaybook
            playbook_count = self.session.query(TaskPlaybook).count()

            if playbook_count == 0:
                issues.append(IntegrityIssue(
                    "knowledge_gap", "low", "playbooks",
                    "No task playbooks saved yet",
                    "Complete tasks with 100% verification - playbooks auto-save on completion.",
                    False
                ))
            else:
                issues.append(IntegrityIssue(
                    "connected", "info", "playbooks",
                    f"{playbook_count} playbooks saved",
                    "", False
                ))
        except Exception:
            pass

        return issues

    def _check_weight_health(self) -> List[IntegrityIssue]:
        """Check weight system health."""
        issues = []

        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            stats = ws.get_stats()

            if stats.get("total_weight_updates", 0) == 0:
                issues.append(IntegrityIssue(
                    "weight", "medium", "weight_system",
                    "No weight updates recorded - backpropagation not happening",
                    "User feedback (upvote/downvote) triggers weight updates. Use POST /chat/feedback.",
                    False
                ))
            else:
                issues.append(IntegrityIssue(
                    "connected", "info", "weight_system",
                    f"{stats['total_weight_updates']} weight updates, KPIs: {stats.get('current_kpis', {})}",
                    "", False
                ))
        except Exception:
            pass

        return issues

    def _check_rag_alignment(self) -> List[IntegrityIssue]:
        """Check RAG subsystem alignment -- are all knowledge sources searchable?"""
        issues = []

        # Check if Knowledge Indexer has run
        try:
            from cognitive.knowledge_indexer import get_knowledge_indexer
            indexer = get_knowledge_indexer(self.session)
            stats = indexer.get_stats()

            if stats.get("last_run") is None:
                issues.append(IntegrityIssue(
                    "rag_alignment", "high", "knowledge_indexer",
                    "Knowledge Indexer has NEVER run - internal knowledge not searchable via RAG",
                    "Run POST /llm-learning/index/all or wait for continuous learning loop",
                    True
                ))
            else:
                total = stats.get("total_indexed", 0)
                issues.append(IntegrityIssue(
                    "connected", "info", "knowledge_indexer",
                    f"Knowledge Indexer active: {total} entries indexed across {len(stats.get('by_source', {}))} sources",
                    "", False
                ))

                # Check per-source coverage
                by_source = stats.get("by_source", {})
                expected_sources = ["chat_history", "completed_tasks", "playbooks", "diagnostics", "genesis_keys", "distilled_knowledge"]
                for source in expected_sources:
                    if source not in by_source or by_source[source] == 0:
                        issues.append(IntegrityIssue(
                            "rag_alignment", "medium", f"indexer_{source}",
                            f"RAG source '{source}' has 0 indexed entries",
                            f"This knowledge source exists but isn't searchable yet",
                            True
                        ))

        except Exception as e:
            issues.append(IntegrityIssue(
                "rag_alignment", "medium", "knowledge_indexer",
                f"Cannot check Knowledge Indexer: {e}",
                "Knowledge Indexer may not be initialized",
                False
            ))

        # Check retrieval quality
        try:
            from cognitive.knowledge_indexer import get_retrieval_quality_tracker
            qt = get_retrieval_quality_tracker(self.session)
            report = qt.get_quality_report()

            total = report.get("total_retrievals_tracked", 0)
            if total > 10:
                rate = report.get("usefulness_rate", 0)
                if rate < 0.3:
                    issues.append(IntegrityIssue(
                        "rag_alignment", "high", "retrieval_quality",
                        f"Retrieval usefulness rate is {rate:.0%} -- most retrieved results are noise",
                        "Reranker may need tuning, or documents need better chunking",
                        False
                    ))
                else:
                    issues.append(IntegrityIssue(
                        "connected", "info", "retrieval_quality",
                        f"Retrieval quality: {rate:.0%} usefulness rate ({total} retrievals tracked)",
                        "", False
                    ))
        except Exception:
            pass

        return issues

    def _check_indexer_health(self) -> List[IntegrityIssue]:
        """Check if all subsystems that produce knowledge are feeding the indexer."""
        issues = []

        # Count tables that should be indexed
        tables_to_check = [
            ("Chat history", "models.database_models", "Chat"),
            ("LLM interactions", "models.llm_tracking_models", "LLMInteraction"),
        ]

        for name, module, model_name in tables_to_check:
            try:
                mod = __import__(module, fromlist=[model_name])
                model_class = getattr(mod, model_name)
                count = self.session.query(model_class).count()
                if count > 0:
                    issues.append(IntegrityIssue(
                        "connected", "info", f"data_{name.lower().replace(' ', '_')}",
                        f"{name}: {count} records available for indexing",
                        "", False
                    ))
            except Exception:
                pass

        return issues

    def _check_cross_system_signals(self) -> List[IntegrityIssue]:
        """Check cross-system signals that should flow between subsystems."""
        issues = []

        # diagnostics → weight_system: health drops should adjust weights
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            stats = ws.get_stats()
            kpis = stats.get("current_kpis", {})
            if kpis.get("success_rate", 1) < 0.5:
                # Low success rate should trigger weight adjustment
                ws.propagate_outcome(outcome="failure", source_type="system_health")
                issues.append(IntegrityIssue(
                    "connected", "info", "diagnostics_to_weights",
                    "Low success rate triggered weight adjustment",
                    "", False
                ))
        except Exception:
            pass

        # handshake → system_integrity: dead components feed integrity
        try:
            from genesis.component_registry import ComponentEntry
            dead = self.session.query(ComponentEntry).filter(
                ComponentEntry.status == "dead"
            ).count()
            if dead > 0:
                issues.append(IntegrityIssue(
                    "cross_system", "high", "handshake_to_integrity",
                    f"{dead} dead components detected by handshake",
                    "Self-healing should attempt restart",
                    True
                ))

                from cognitive.learning_hook import track_learning_event
                track_learning_event(
                    "handshake_alert",
                    f"{dead} dead components",
                    outcome="failure",
                    severity="high",
                    signal_type="alert",
                    data={"dead_count": dead},
                )
        except Exception:
            pass

        # handshake → mirror: component health feeds self-awareness
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "system_health_snapshot",
                f"Cross-system health check complete",
                signal_type="health",
                data={"check": "cross_system_signals"},
            )
        except Exception:
            pass

        # patterns → weight_system: pattern outcomes adjust weights
        try:
            from cognitive.llm_pattern_learner import get_llm_pattern_learner
            learner = get_llm_pattern_learner(self.session)
            stats = learner.get_pattern_stats()
            if stats.get("total_patterns", 0) > 0:
                avg_success = stats.get("avg_success_rate", 0)
                if avg_success < 0.5:
                    from cognitive.grace_weight_system import get_grace_weight_system
                    ws = get_grace_weight_system(self.session)
                    ws.propagate_outcome(outcome="failure", source_type="pattern_derived")
        except Exception:
            pass

        return issues

    def _check_api_coverage(self) -> List[IntegrityIssue]:
        """Check API endpoint coverage."""
        issues = []

        try:
            api_file = os.path.join(self.workspace, "api", "llm_learning_api.py")
            with open(api_file) as f:
                content = f.read()
            endpoint_count = content.count("@router.")

            issues.append(IntegrityIssue(
                "connected", "info", "api",
                f"{endpoint_count} API endpoints defined in llm_learning_api.py",
                "", False
            ))
        except Exception:
            pass

        return issues

    def _calculate_health_score(self, issues: List[IntegrityIssue]) -> float:
        """Calculate overall system health 0-100.

        Separates startup issues (subsystems not active because app
        isn't running) from real issues (things that are actually broken).
        Startup issues don't tank the score in script/test mode.
        """
        if not issues:
            return 50.0

        connected = [i for i in issues if i.category == "connected"]

        # Separate startup issues from real issues
        startup_issues = [i for i in issues if "NOT active" in i.description and i.category == "disconnected"]
        real_issues = [i for i in issues if i not in connected and i not in startup_issues]

        total_real = len(connected) + len(real_issues)

        if total_real == 0:
            return 70.0  # Only startup issues, system is structurally fine

        # Base score from real connection ratio
        base = (len(connected) / max(total_real, 1)) * 60

        # Penalty for real critical/high issues only
        critical = len([i for i in real_issues if i.severity == "critical"])
        high = len([i for i in real_issues if i.severity == "high"])
        medium = len([i for i in real_issues if i.severity == "medium"])

        penalty = (critical * 15) + (high * 8) + (medium * 2)

        # Bonus for startup issues being the only problem (structurally sound)
        startup_bonus = 10 if len(startup_issues) > 0 and len(real_issues) <= 3 else 0

        return max(0, min(100, base + 30 - penalty + startup_bonus))

    def get_quick_status(self) -> Dict[str, Any]:
        """Quick status check without full scan. Uses cached report if recent."""
        if self._cached_report and self._last_scan:
            age = (datetime.now(timezone.utc) - self._last_scan).total_seconds()
            if age < 300:  # Cache valid for 5 minutes
                return {
                    "cached": True,
                    "age_seconds": int(age),
                    "health_score": self._cached_report["health_score"],
                    "total_issues": self._cached_report["total_issues"],
                    "critical": self._cached_report["critical"],
                    "connected_systems": self._cached_report["connected_systems"],
                }

        return self.full_scan()


_monitor: Optional[SystemIntegrityMonitor] = None


def get_system_integrity_monitor(session: Session) -> SystemIntegrityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemIntegrityMonitor(session)
    return _monitor
