"""
Intelligent CI/CD Orchestrator
==============================
The BRAIN that connects all autonomous systems with the CI/CD pipeline.

This orchestrator provides:
1. CLOSED-LOOP FEEDBACK: Production metrics → Learning → Test selection → Deployment
2. INTELLIGENT TEST SELECTION: ML-based test prioritization
3. AUTONOMOUS PIPELINE TRIGGERING: Self-triggering based on system state
4. GENESIS KEY INTEGRATION: Full traceability across all CI/CD operations
5. WEBHOOK EVENT PROCESSING: Real-time event-driven automation
6. SELF-HEALING INTEGRATION: Auto-healing triggered by CI/CD failures

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                  INTELLIGENT CI/CD ORCHESTRATOR                      │
    ├─────────────────────────────────────────────────────────────────────┤
    │                                                                      │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
    │  │   Adaptive   │    │  Autonomous  │    │    Intelligent      │  │
    │  │    CI/CD     │ ←→ │   Triggers   │ ←→ │   Test Selector     │  │
    │  └──────────────┘    └──────────────┘    └──────────────────────┘  │
    │         ↑                   ↑                       ↑              │
    │         │                   │                       │              │
    │         ↓                   ↓                       ↓              │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
    │  │  Autonomous  │    │   Webhook    │    │   Learning Memory    │  │
    │  │   Healing    │ ←→ │  Processor   │ ←→ │     Integration      │  │
    │  └──────────────┘    └──────────────┘    └──────────────────────┘  │
    │         ↑                   ↑                       ↑              │
    │         └───────────────────┴───────────────────────┘              │
    │                             ↓                                       │
    │                    ┌──────────────┐                                 │
    │                    │ Genesis Keys │                                 │
    │                    │  (Tracking)  │                                 │
    │                    └──────────────┘                                 │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘

GRACE can autonomously:
- Monitor production health and trigger CI/CD based on anomalies
- Select optimal tests to run based on code changes and historical data
- Trigger healing actions when pipelines fail
- Learn from CI/CD outcomes to improve future decisions
- Create and track Genesis Keys for all operations
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class IntelligenceMode(str, Enum):
    """Intelligence level for CI/CD decisions."""
    RULE_BASED = "rule_based"           # Simple rule-based decisions
    ML_ASSISTED = "ml_assisted"         # ML helps with recommendations
    FULLY_AUTONOMOUS = "fully_autonomous"  # Full autonomous decision-making


class TriggerSource(str, Enum):
    """Sources that can trigger CI/CD actions."""
    GIT_PUSH = "git_push"
    GIT_PR = "git_pull_request"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    ANOMALY_DETECTED = "anomaly_detected"
    HEALTH_DEGRADATION = "health_degradation"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    USER_REQUEST = "user_request"
    AUTONOMOUS_DECISION = "autonomous_decision"
    HEALING_RESPONSE = "healing_response"


class TestSelectionStrategy(str, Enum):
    """Strategies for intelligent test selection."""
    ALL_TESTS = "all_tests"                    # Run all tests
    CHANGED_ONLY = "changed_only"              # Only test changed files
    IMPACT_ANALYSIS = "impact_analysis"        # Run tests affected by changes
    FAILURE_PREDICTION = "failure_prediction"  # Prioritize likely-to-fail tests
    RISK_BASED = "risk_based"                  # Prioritize high-risk areas
    BANDIT_SELECTION = "bandit_selection"      # Multi-armed bandit for selection


class PipelineDecision(str, Enum):
    """Decisions the orchestrator can make."""
    TRIGGER_FULL = "trigger_full"
    TRIGGER_PARTIAL = "trigger_partial"
    DEFER = "defer"
    SKIP = "skip"
    REQUEST_APPROVAL = "request_approval"
    SANDBOX_FIRST = "sandbox_first"


@dataclass
class TestMetrics:
    """Metrics for a test or test suite."""
    test_id: str
    pass_rate: float = 1.0
    avg_duration: float = 0.0
    failure_recency: float = 0.0  # How recently it failed (0=never, 1=just now)
    coverage_value: float = 0.0   # How much code it covers
    flakiness_score: float = 0.0  # How flaky the test is (0=stable, 1=very flaky)
    last_run: Optional[str] = None
    total_runs: int = 0
    priority_score: float = 0.5   # Computed priority score


@dataclass
class WebhookEvent:
    """A webhook event from GitHub/GitLab/etc."""
    id: str
    source: str                    # github, gitlab, jenkins, etc.
    event_type: str                # push, pull_request, workflow_run, etc.
    timestamp: str
    payload: Dict[str, Any]
    genesis_key: Optional[str] = None
    processed: bool = False
    actions_triggered: List[str] = field(default_factory=list)


@dataclass
class ClosedLoopMetric:
    """Metric for closed-loop feedback."""
    metric_name: str
    value: float
    timestamp: str
    source: str                    # production, staging, ci, etc.
    trend: str = "stable"          # improving, stable, degrading
    alert_threshold: Optional[float] = None


@dataclass
class IntelligentDecision:
    """An intelligent CI/CD decision with full context."""
    decision_id: str
    decision: PipelineDecision
    confidence: float
    reasoning: str
    intelligence_mode: IntelligenceMode
    trigger_source: TriggerSource
    test_strategy: TestSelectionStrategy
    tests_selected: List[str]
    pipeline_modifications: Dict[str, Any]
    genesis_key: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# INTELLIGENT TEST SELECTOR
# =============================================================================

class IntelligentTestSelector:
    """
    ML-based intelligent test selection.

    Uses:
    - Multi-armed bandit for test prioritization
    - Historical failure patterns
    - Code change impact analysis
    - Test coverage data
    """

    def __init__(self):
        self.test_metrics: Dict[str, TestMetrics] = {}
        self.bandit_arms: Dict[str, Dict[str, float]] = {}  # test_id -> {successes, failures}
        self.selection_history: List[Dict] = []

    def record_test_result(
        self,
        test_id: str,
        passed: bool,
        duration: float,
        coverage: float = 0.0
    ):
        """Record a test result for learning."""
        if test_id not in self.test_metrics:
            self.test_metrics[test_id] = TestMetrics(test_id=test_id)

        metrics = self.test_metrics[test_id]

        # Update pass rate (exponential moving average)
        alpha = 0.2
        metrics.pass_rate = alpha * (1.0 if passed else 0.0) + (1 - alpha) * metrics.pass_rate

        # Update duration
        metrics.avg_duration = alpha * duration + (1 - alpha) * metrics.avg_duration

        # Update failure recency
        if not passed:
            metrics.failure_recency = 1.0
        else:
            metrics.failure_recency *= 0.9  # Decay over time

        # Update coverage
        if coverage > 0:
            metrics.coverage_value = coverage

        metrics.last_run = datetime.now(timezone.utc).isoformat()
        metrics.total_runs += 1

        # Update bandit arms
        if test_id not in self.bandit_arms:
            self.bandit_arms[test_id] = {"successes": 0, "failures": 0}

        if passed:
            self.bandit_arms[test_id]["successes"] += 1
        else:
            self.bandit_arms[test_id]["failures"] += 1

        # Recompute priority
        self._compute_priority(test_id)

    def _compute_priority(self, test_id: str):
        """Compute test priority score."""
        metrics = self.test_metrics.get(test_id)
        if not metrics:
            return

        # Priority factors:
        # - Higher priority for tests that failed recently
        # - Higher priority for tests with good coverage
        # - Lower priority for flaky tests
        # - Lower priority for slow tests (within reason)

        priority = 0.0

        # Failure recency (weight: 0.35)
        priority += 0.35 * metrics.failure_recency

        # Coverage value (weight: 0.25)
        priority += 0.25 * metrics.coverage_value

        # Inverse flakiness (weight: 0.20)
        priority += 0.20 * (1.0 - metrics.flakiness_score)

        # Inverse duration penalty (weight: 0.10)
        duration_penalty = min(1.0, metrics.avg_duration / 60.0)  # Cap at 60s
        priority += 0.10 * (1.0 - duration_penalty)

        # Bandit exploration bonus (weight: 0.10) - UCB formula
        arms = self.bandit_arms.get(test_id, {"successes": 0, "failures": 0})
        total = arms["successes"] + arms["failures"]
        if total > 0:
            exploration_bonus = (2 * (total ** 0.5)) / total
            priority += 0.10 * min(1.0, exploration_bonus)
        else:
            priority += 0.10  # Unexplored tests get full exploration bonus

        metrics.priority_score = priority

    def select_tests(
        self,
        strategy: TestSelectionStrategy,
        changed_files: List[str] = None,
        max_tests: int = None,
        time_budget: float = None  # seconds
    ) -> List[str]:
        """
        Select tests to run based on strategy.

        Returns list of test IDs ordered by priority.
        """
        if not self.test_metrics:
            logger.warning("[TestSelector] No test metrics available, returning all tests")
            return []

        # Get all tests sorted by priority
        all_tests = sorted(
            self.test_metrics.values(),
            key=lambda t: t.priority_score,
            reverse=True
        )

        selected = []

        if strategy == TestSelectionStrategy.ALL_TESTS:
            selected = [t.test_id for t in all_tests]

        elif strategy == TestSelectionStrategy.CHANGED_ONLY:
            if changed_files:
                # Match tests to changed files
                selected = [
                    t.test_id for t in all_tests
                    if any(self._test_matches_file(t.test_id, f) for f in changed_files)
                ]

        elif strategy == TestSelectionStrategy.FAILURE_PREDICTION:
            # Select tests most likely to fail (high failure recency)
            selected = [t.test_id for t in all_tests if t.failure_recency > 0.3]
            # Add some random exploration
            remaining = [t for t in all_tests if t.test_id not in selected]
            selected.extend([t.test_id for t in remaining[:max(3, len(remaining) // 10)]])

        elif strategy == TestSelectionStrategy.RISK_BASED:
            # Select tests with good coverage of risky areas
            selected = [
                t.test_id for t in all_tests
                if t.coverage_value > 0.5 or t.failure_recency > 0.2
            ]

        elif strategy == TestSelectionStrategy.BANDIT_SELECTION:
            # Use Thompson sampling for test selection
            selected = self._bandit_select(all_tests, max_tests or len(all_tests))

        elif strategy == TestSelectionStrategy.IMPACT_ANALYSIS:
            # Analyze impact of changes (requires code analysis)
            if changed_files:
                selected = self._impact_based_selection(changed_files, all_tests)
            else:
                selected = [t.test_id for t in all_tests]

        # Apply max_tests limit
        if max_tests and len(selected) > max_tests:
            selected = selected[:max_tests]

        # Apply time budget
        if time_budget:
            selected = self._apply_time_budget(selected, time_budget)

        # Record selection
        self.selection_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy.value,
            "tests_selected": len(selected),
            "total_tests": len(all_tests)
        })

        logger.info(
            f"[TestSelector] Selected {len(selected)}/{len(all_tests)} tests "
            f"using {strategy.value} strategy"
        )

        return selected

    def _test_matches_file(self, test_id: str, file_path: str) -> bool:
        """Check if a test is related to a file."""
        # Simple heuristic: test file name matches source file
        test_name = test_id.lower().replace("test_", "").replace("_test", "")
        file_name = Path(file_path).stem.lower()
        return test_name in file_name or file_name in test_name

    def _bandit_select(
        self,
        tests: List[TestMetrics],
        n: int
    ) -> List[str]:
        """Select tests using Thompson sampling (multi-armed bandit)."""
        import random

        scores = []
        for test in tests:
            arms = self.bandit_arms.get(test.test_id, {"successes": 1, "failures": 1})
            # Thompson sampling: sample from Beta distribution
            # Here we use a simplified version
            alpha = arms["failures"] + 1  # We want to select tests that might fail
            beta = arms["successes"] + 1
            score = random.betavariate(alpha, beta)
            scores.append((test.test_id, score))

        # Sort by score and return top n
        scores.sort(key=lambda x: x[1], reverse=True)
        return [test_id for test_id, _ in scores[:n]]

    def _impact_based_selection(
        self,
        changed_files: List[str],
        all_tests: List[TestMetrics]
    ) -> List[str]:
        """Select tests based on code change impact."""
        # This would integrate with code analysis tools
        # For now, use a heuristic based on file paths
        selected = set()

        for file_path in changed_files:
            path = Path(file_path)

            # Direct test matches
            for test in all_tests:
                if self._test_matches_file(test.test_id, file_path):
                    selected.add(test.test_id)

            # Module-level matches
            module = path.parent.name
            for test in all_tests:
                if module.lower() in test.test_id.lower():
                    selected.add(test.test_id)

        # Always include high-priority tests
        for test in all_tests[:5]:
            selected.add(test.test_id)

        return list(selected)

    def _apply_time_budget(
        self,
        test_ids: List[str],
        budget: float
    ) -> List[str]:
        """Filter tests to fit within time budget."""
        result = []
        total_time = 0.0

        for test_id in test_ids:
            metrics = self.test_metrics.get(test_id)
            if metrics:
                if total_time + metrics.avg_duration <= budget:
                    result.append(test_id)
                    total_time += metrics.avg_duration

        return result


# =============================================================================
# WEBHOOK EVENT PROCESSOR
# =============================================================================

class WebhookEventProcessor:
    """
    Process webhook events from CI/CD providers.

    Converts external events into internal triggers and actions.
    """

    def __init__(self):
        self.event_queue: List[WebhookEvent] = []
        self.handlers: Dict[str, List[Callable]] = {}
        self.processed_count = 0

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Dict[str, Any]]
    ):
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def process_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """Process a single webhook event."""
        logger.info(
            f"[WebhookProcessor] Processing {event.event_type} from {event.source}"
        )

        results = {
            "event_id": event.id,
            "event_type": event.event_type,
            "handlers_invoked": 0,
            "actions_triggered": []
        }

        # Get handlers for this event type
        handlers = self.handlers.get(event.event_type, [])
        handlers.extend(self.handlers.get("*", []))  # Wildcard handlers

        for handler in handlers:
            try:
                result = await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
                if result:
                    results["actions_triggered"].extend(result.get("actions", []))
                results["handlers_invoked"] += 1
            except Exception as e:
                logger.error(f"[WebhookProcessor] Handler error: {e}")

        event.processed = True
        event.actions_triggered = results["actions_triggered"]
        self.processed_count += 1

        return results

    def parse_webhook_event(self, payload: Dict[str, Any], source: str = "webhook") -> WebhookEvent:
        """Parse a git host / CI webhook event (generic)."""
        event_type = payload.get("action", "unknown")

        # Determine event type from payload structure (GitHub-style shape; other hosts can be mapped similarly)
        if "pull_request" in payload:
            event_type = f"pull_request.{payload.get('action', 'unknown')}"
        elif "pusher" in payload:
            event_type = "push"
        elif "workflow_run" in payload:
            event_type = f"workflow_run.{payload.get('action', 'unknown')}"
        elif "check_run" in payload:
            event_type = f"check_run.{payload.get('action', 'unknown')}"

        return WebhookEvent(
            id=self._generate_event_id(payload),
            source=source,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
            genesis_key=self._generate_genesis_key("webhook", event_type)
        )

    def _generate_event_id(self, payload: Dict) -> str:
        """Generate unique event ID."""
        data = json.dumps(payload, sort_keys=True)[:1000]
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def _generate_genesis_key(self, category: str, action: str) -> str:
        """Generate Genesis Key for webhook event."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"webhook:{category}:{action}:{timestamp}"
        key_hash = hashlib.sha256(data.encode()).hexdigest()[:12]
        return f"GK-webhook-{key_hash}"


# =============================================================================
# CLOSED-LOOP FEEDBACK SYSTEM
# =============================================================================

class ClosedLoopFeedback:
    """
    Closed-loop feedback system connecting:
    Production Metrics → Learning System → CI/CD Decisions

    This enables the system to:
    - Learn from production issues
    - Improve test selection based on real-world failures
    - Automatically trigger pipelines when issues are detected
    """

    def __init__(self):
        self.metrics: Dict[str, List[ClosedLoopMetric]] = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        self.feedback_actions: List[Dict] = []

    def record_metric(
        self,
        name: str,
        value: float,
        source: str = "production",
        alert_threshold: float = None
    ):
        """Record a metric from production or CI."""
        if name not in self.metrics:
            self.metrics[name] = []

        # Calculate trend
        recent = self.metrics[name][-10:] if self.metrics[name] else []
        if len(recent) >= 3:
            recent_avg = statistics.mean([m.value for m in recent])
            if value > recent_avg * 1.1:
                trend = "degrading"
            elif value < recent_avg * 0.9:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "stable"

        metric = ClosedLoopMetric(
            metric_name=name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            trend=trend,
            alert_threshold=alert_threshold
        )

        self.metrics[name].append(metric)

        # Keep last 100 data points
        self.metrics[name] = self.metrics[name][-100:]

        # Check for anomalies
        if self._is_anomaly(name, value):
            self._trigger_anomaly_response(name, metric)

        return metric

    def _is_anomaly(self, name: str, value: float) -> bool:
        """Detect if a value is anomalous using statistical analysis."""
        history = self.metrics.get(name, [])

        if len(history) < 10:
            return False

        values = [m.value for m in history[-30:]]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        if stdev == 0:
            return False

        z_score = abs(value - mean) / stdev
        return z_score > self.anomaly_threshold

    def _trigger_anomaly_response(self, name: str, metric: ClosedLoopMetric):
        """Trigger autonomous response to anomaly."""
        logger.warning(
            f"[ClosedLoop] Anomaly detected in {name}: {metric.value} "
            f"(trend: {metric.trend})"
        )

        action = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": name,
            "metric_value": metric.value,
            "action": "trigger_investigation",
            "recommendation": self._get_recommendation(name, metric)
        }

        self.feedback_actions.append(action)

    def _get_recommendation(
        self,
        name: str,
        metric: ClosedLoopMetric
    ) -> str:
        """Get recommendation based on metric type."""
        if "error" in name.lower():
            return "Trigger targeted tests for error-prone components"
        elif "latency" in name.lower():
            return "Run performance regression tests"
        elif "memory" in name.lower():
            return "Run memory leak detection tests"
        elif "coverage" in name.lower() and metric.trend == "degrading":
            return "Run full test suite to identify coverage gaps"
        else:
            return "Monitor and investigate if trend continues"

    def get_trigger_recommendation(self) -> Optional[TriggerSource]:
        """Get recommended trigger based on feedback loop analysis."""
        recent_actions = self.feedback_actions[-5:]

        if not recent_actions:
            return None

        # If multiple anomalies recently, recommend autonomous trigger
        if len(recent_actions) >= 2:
            return TriggerSource.ANOMALY_DETECTED

        # If trend is degrading, recommend health check
        for name, metrics in self.metrics.items():
            if metrics and metrics[-1].trend == "degrading":
                return TriggerSource.HEALTH_DEGRADATION

        return None


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class IntelligentCICDOrchestrator:
    """
    The central brain connecting all autonomous systems with CI/CD.

    Integrates:
    - Adaptive CI/CD (trust scoring, KPIs)
    - Autonomous triggers (Genesis Keys)
    - Intelligent test selection (ML-based)
    - Webhook processing (event-driven)
    - Closed-loop feedback (production → learning)
    - Self-healing (failure response)
    """

    def __init__(
        self,
        intelligence_mode: IntelligenceMode = IntelligenceMode.ML_ASSISTED
    ):
        self.intelligence_mode = intelligence_mode

        # Sub-systems
        self.test_selector = IntelligentTestSelector()
        self.webhook_processor = WebhookEventProcessor()
        self.feedback_loop = ClosedLoopFeedback()

        # State
        self.decisions: Dict[str, IntelligentDecision] = {}
        self.pipeline_runs: List[Dict] = []
        self.learning_memory: List[Dict] = []

        # Configuration
        self.auto_trigger_enabled = True
        self.sandbox_required_for_autonomous = True

        # Register default webhook handlers
        self._register_default_handlers()

        logger.info(
            f"[IntelligentCICD] Initialized with mode={intelligence_mode.value}"
        )

    def _register_default_handlers(self):
        """Register default webhook event handlers."""

        async def handle_push(event: WebhookEvent) -> Dict:
            """Handle push events."""
            payload = event.payload
            branch = payload.get("ref", "").replace("refs/heads/", "")

            if branch in ["main", "develop"]:
                return {
                    "actions": [
                        {
                            "type": "trigger_pipeline",
                            "pipeline": "ci",
                            "reason": f"Push to {branch}",
                            "priority": "high" if branch == "main" else "medium"
                        }
                    ]
                }
            return {"actions": []}

        async def handle_pr(event: WebhookEvent) -> Dict:
            """Handle pull request events."""
            payload = event.payload
            action = payload.get("action")

            if action in ["opened", "synchronize"]:
                return {
                    "actions": [
                        {
                            "type": "trigger_pipeline",
                            "pipeline": "pr-check",
                            "test_strategy": "impact_analysis",
                            "reason": f"PR {action}"
                        }
                    ]
                }
            return {"actions": []}

        async def handle_workflow_failure(event: WebhookEvent) -> Dict:
            """Handle workflow run failures."""
            payload = event.payload

            if payload.get("action") == "completed":
                conclusion = payload.get("workflow_run", {}).get("conclusion")

                if conclusion == "failure":
                    return {
                        "actions": [
                            {
                                "type": "trigger_healing",
                                "reason": "Workflow failed",
                                "healing_action": "investigate_failure"
                            },
                            {
                                "type": "update_feedback",
                                "metric": "ci_failure_rate",
                                "value": 1.0
                            }
                        ]
                    }
            return {"actions": []}

        self.webhook_processor.register_handler("push", handle_push)
        self.webhook_processor.register_handler("pull_request.opened", handle_pr)
        self.webhook_processor.register_handler("pull_request.synchronize", handle_pr)
        self.webhook_processor.register_handler("workflow_run.completed", handle_workflow_failure)

    # =========================================================================
    # INTELLIGENT DECISION MAKING
    # =========================================================================

    async def make_pipeline_decision(
        self,
        trigger_source: TriggerSource,
        context: Dict[str, Any]
    ) -> IntelligentDecision:
        """
        Make an intelligent decision about CI/CD pipeline execution.

        Uses all sub-systems to make the best decision:
        - Test selector for optimal test coverage
        - Feedback loop for production insights
        - Trust scores for safety
        """
        decision_id = self._generate_decision_id()
        genesis_key = self._generate_genesis_key("decision", trigger_source.value)

        # Gather intelligence
        test_strategy = await self._determine_test_strategy(trigger_source, context)
        selected_tests = self.test_selector.select_tests(
            strategy=test_strategy,
            changed_files=context.get("changed_files", []),
            max_tests=context.get("max_tests"),
            time_budget=context.get("time_budget")
        )

        # Check feedback loop for anomalies
        feedback_recommendation = self.feedback_loop.get_trigger_recommendation()

        # Make decision based on intelligence mode
        if self.intelligence_mode == IntelligenceMode.FULLY_AUTONOMOUS:
            decision, confidence, reasoning = await self._autonomous_decision(
                trigger_source, context, test_strategy, feedback_recommendation
            )
        elif self.intelligence_mode == IntelligenceMode.ML_ASSISTED:
            decision, confidence, reasoning = await self._ml_assisted_decision(
                trigger_source, context, test_strategy, feedback_recommendation
            )
        else:
            decision, confidence, reasoning = self._rule_based_decision(
                trigger_source, context
            )

        # Create decision record
        intelligent_decision = IntelligentDecision(
            decision_id=decision_id,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            intelligence_mode=self.intelligence_mode,
            trigger_source=trigger_source,
            test_strategy=test_strategy,
            tests_selected=selected_tests,
            pipeline_modifications={
                "test_subset": selected_tests if len(selected_tests) < 100 else "subset",
                "fast_path": len(selected_tests) < 20,
                "sandbox_required": self.sandbox_required_for_autonomous
            },
            genesis_key=genesis_key,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "feedback_recommendation": feedback_recommendation.value if feedback_recommendation else None,
                "context": context
            }
        )

        self.decisions[decision_id] = intelligent_decision

        logger.info(
            f"[IntelligentCICD] Decision: {decision.value} "
            f"(confidence={confidence:.2%}, tests={len(selected_tests)})"
        )

        return intelligent_decision

    async def _determine_test_strategy(
        self,
        trigger_source: TriggerSource,
        context: Dict[str, Any]
    ) -> TestSelectionStrategy:
        """Determine optimal test selection strategy."""

        # Use different strategies based on trigger source
        if trigger_source in [TriggerSource.ANOMALY_DETECTED, TriggerSource.HEALTH_DEGRADATION]:
            return TestSelectionStrategy.FAILURE_PREDICTION

        if trigger_source == TriggerSource.GIT_PR:
            return TestSelectionStrategy.IMPACT_ANALYSIS

        if trigger_source == TriggerSource.SCHEDULED:
            return TestSelectionStrategy.BANDIT_SELECTION

        if context.get("changed_files"):
            return TestSelectionStrategy.IMPACT_ANALYSIS

        if context.get("fast_feedback"):
            return TestSelectionStrategy.RISK_BASED

        return TestSelectionStrategy.ALL_TESTS

    async def _autonomous_decision(
        self,
        trigger_source: TriggerSource,
        context: Dict[str, Any],
        test_strategy: TestSelectionStrategy,
        feedback_recommendation: Optional[TriggerSource]
    ) -> Tuple[PipelineDecision, float, str]:
        """Make fully autonomous decision using LLM orchestration."""
        try:
            from llm_orchestrator.llm_orchestrator import get_llm_orchestrator

            orchestrator = get_llm_orchestrator()

            prompt = f"""CI/CD Pipeline Decision Required

Trigger: {trigger_source.value}
Test Strategy: {test_strategy.value}
Feedback Recommendation: {feedback_recommendation.value if feedback_recommendation else 'None'}
Context: {json.dumps(context, indent=2)[:500]}

Based on this information, decide:
1. Should we trigger the pipeline? (trigger_full, trigger_partial, defer, skip, sandbox_first)
2. What's your confidence level? (0-100%)
3. Brief reasoning (1-2 sentences)

Respond in JSON format:
{{"decision": "...", "confidence": 85, "reasoning": "..."}}"""

            response = await orchestrator.generate(prompt, temperature=0.3)

            # Parse response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                decision = PipelineDecision(result.get("decision", "trigger_full"))
                confidence = result.get("confidence", 70) / 100
                reasoning = result.get("reasoning", "LLM decision")
                return decision, confidence, reasoning

        except Exception as e:
            logger.error(f"[IntelligentCICD] LLM decision failed: {e}")

        # Fallback to rule-based
        return self._rule_based_decision(trigger_source, context)

    async def _ml_assisted_decision(
        self,
        trigger_source: TriggerSource,
        context: Dict[str, Any],
        test_strategy: TestSelectionStrategy,
        feedback_recommendation: Optional[TriggerSource]
    ) -> Tuple[PipelineDecision, float, str]:
        """Make ML-assisted decision combining rules and ML insights."""

        # Start with rule-based decision
        base_decision, base_confidence, base_reasoning = self._rule_based_decision(
            trigger_source, context
        )

        # Adjust based on feedback loop
        if feedback_recommendation:
            if feedback_recommendation == TriggerSource.ANOMALY_DETECTED:
                return (
                    PipelineDecision.TRIGGER_FULL,
                    min(0.95, base_confidence + 0.1),
                    f"{base_reasoning} + Anomaly detected in production"
                )
            elif feedback_recommendation == TriggerSource.HEALTH_DEGRADATION:
                return (
                    PipelineDecision.SANDBOX_FIRST,
                    base_confidence,
                    f"{base_reasoning} + Health degradation detected"
                )

        # Adjust based on test selection insights
        if test_strategy == TestSelectionStrategy.FAILURE_PREDICTION:
            base_confidence = min(0.90, base_confidence + 0.05)
            base_reasoning += " (prioritizing likely-to-fail tests)"

        return base_decision, base_confidence, base_reasoning

    def _rule_based_decision(
        self,
        trigger_source: TriggerSource,
        context: Dict[str, Any]
    ) -> Tuple[PipelineDecision, float, str]:
        """Make rule-based decision."""

        # High-priority triggers
        if trigger_source in [TriggerSource.GIT_PUSH, TriggerSource.GIT_PR]:
            return (
                PipelineDecision.TRIGGER_FULL,
                0.85,
                f"Standard CI trigger from {trigger_source.value}"
            )

        # Autonomous triggers need sandbox
        if trigger_source == TriggerSource.AUTONOMOUS_DECISION:
            return (
                PipelineDecision.SANDBOX_FIRST,
                0.70,
                "Autonomous trigger requires sandbox validation"
            )

        # Anomaly response
        if trigger_source in [TriggerSource.ANOMALY_DETECTED, TriggerSource.HEALTH_DEGRADATION]:
            return (
                PipelineDecision.TRIGGER_PARTIAL,
                0.75,
                f"Responding to {trigger_source.value}"
            )

        # Healing response
        if trigger_source == TriggerSource.HEALING_RESPONSE:
            return (
                PipelineDecision.SANDBOX_FIRST,
                0.65,
                "Healing action requires validation"
            )

        # Scheduled
        if trigger_source == TriggerSource.SCHEDULED:
            return (
                PipelineDecision.TRIGGER_FULL,
                0.80,
                "Scheduled pipeline run"
            )

        # Default
        return (
            PipelineDecision.REQUEST_APPROVAL,
            0.50,
            f"Unknown trigger source: {trigger_source.value}"
        )

    # =========================================================================
    # PIPELINE EXECUTION
    # =========================================================================

    async def execute_decision(
        self,
        decision: IntelligentDecision
    ) -> Dict[str, Any]:
        """Execute a pipeline decision."""
        result = {
            "decision_id": decision.decision_id,
            "genesis_key": decision.genesis_key,
            "status": "pending",
            "pipeline_run_id": None,
            "sandbox_run_id": None
        }

        try:
            # Import adaptive CI/CD for execution
            from genesis.adaptive_cicd import get_adaptive_cicd, AdaptiveTriggerReason

            adaptive = get_adaptive_cicd()

            if decision.decision == PipelineDecision.TRIGGER_FULL:
                # Full pipeline trigger
                trigger_result = await adaptive.trigger_autonomous_pipeline(
                    pipeline_id="grace-ci",
                    reason=AdaptiveTriggerReason.AUTONOMOUS_DECISION,
                    context={
                        "tests": decision.tests_selected,
                        "intelligent_decision": decision.decision_id
                    }
                )
                result["pipeline_run_id"] = trigger_result.get("trigger_id")
                result["status"] = "triggered"

            elif decision.decision == PipelineDecision.TRIGGER_PARTIAL:
                # Partial pipeline with selected tests
                trigger_result = await adaptive.trigger_autonomous_pipeline(
                    pipeline_id="grace-ci",
                    reason=AdaptiveTriggerReason.LEARNING_OPPORTUNITY,
                    context={
                        "tests": decision.tests_selected,
                        "partial": True
                    }
                )
                result["pipeline_run_id"] = trigger_result.get("trigger_id")
                result["status"] = "triggered_partial"

            elif decision.decision == PipelineDecision.SANDBOX_FIRST:
                # Run in sandbox first
                sandbox_result = await adaptive.run_in_sandbox(
                    pipeline_id="grace-ci",
                    trigger_id=decision.decision_id,
                    context={"tests": decision.tests_selected}
                )
                result["sandbox_run_id"] = sandbox_result.get("sandbox_id")
                result["status"] = "sandbox_running"

            elif decision.decision == PipelineDecision.DEFER:
                result["status"] = "deferred"

            elif decision.decision == PipelineDecision.SKIP:
                result["status"] = "skipped"

            elif decision.decision == PipelineDecision.REQUEST_APPROVAL:
                result["status"] = "awaiting_approval"

            # Record pipeline run
            self.pipeline_runs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "decision_id": decision.decision_id,
                "result": result
            })

        except Exception as e:
            logger.error(f"[IntelligentCICD] Execution failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    # =========================================================================
    # LEARNING & FEEDBACK
    # =========================================================================

    def record_pipeline_outcome(
        self,
        decision_id: str,
        success: bool,
        duration: float,
        test_results: Dict[str, bool] = None,
        coverage: float = None
    ):
        """Record pipeline outcome for learning."""
        decision = self.decisions.get(decision_id)

        if not decision:
            logger.warning(f"[IntelligentCICD] Decision {decision_id} not found")
            return

        # Update test metrics
        if test_results:
            for test_id, passed in test_results.items():
                self.test_selector.record_test_result(
                    test_id=test_id,
                    passed=passed,
                    duration=duration / len(test_results),
                    coverage=coverage or 0
                )

        # Record in feedback loop
        self.feedback_loop.record_metric(
            name="pipeline_success_rate",
            value=1.0 if success else 0.0,
            source="ci"
        )

        self.feedback_loop.record_metric(
            name="pipeline_duration",
            value=duration,
            source="ci"
        )

        # Store in learning memory
        self.learning_memory.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_id": decision_id,
            "decision": decision.decision.value,
            "test_strategy": decision.test_strategy.value,
            "tests_selected": len(decision.tests_selected),
            "success": success,
            "duration": duration,
            "outcome": "positive" if success else "negative"
        })

        logger.info(
            f"[IntelligentCICD] Recorded outcome for {decision_id}: "
            f"{'SUCCESS' if success else 'FAILURE'} in {duration:.1f}s"
        )

    # =========================================================================
    # INTEGRATION WITH AUTONOMOUS SYSTEMS
    # =========================================================================

    async def integrate_with_healing(
        self,
        failure_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate with autonomous healing system on failure."""
        try:
            from cognitive.autonomous_healing_system import (
                get_autonomous_healing,
                TrustLevel
            )

            healing = get_autonomous_healing(
                session=None,  # Will use default
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )

            # Trigger healing cycle
            cycle_result = healing.run_monitoring_cycle()

            # If healing recommends CI, trigger
            if cycle_result["health_status"] not in ["healthy", "degraded"]:
                decision = await self.make_pipeline_decision(
                    trigger_source=TriggerSource.HEALING_RESPONSE,
                    context={
                        "healing_context": failure_context,
                        "health_status": cycle_result["health_status"]
                    }
                )

                return {
                    "healing_triggered": True,
                    "healing_result": cycle_result,
                    "ci_decision": asdict(decision)
                }

            return {
                "healing_triggered": False,
                "healing_result": cycle_result
            }

        except Exception as e:
            logger.error(f"[IntelligentCICD] Healing integration failed: {e}")
            return {"healing_triggered": False, "error": str(e)}

    async def integrate_with_genesis_triggers(
        self,
        genesis_key_id: str
    ) -> Dict[str, Any]:
        """Integrate with Genesis Key trigger pipeline."""
        try:
            from genesis.autonomous_triggers import get_genesis_trigger_pipeline

            trigger_pipeline = get_genesis_trigger_pipeline()

            # The genesis trigger pipeline already handles autonomous actions
            # We just need to check if CI/CD should be triggered
            status = trigger_pipeline.get_status()

            if status["triggers_fired"] > 0:
                # Genesis triggers have fired, check if we need CI
                return {
                    "genesis_integrated": True,
                    "triggers_fired": status["triggers_fired"],
                    "recursive_loops": status["recursive_loops_active"]
                }

            return {
                "genesis_integrated": True,
                "triggers_fired": 0
            }

        except Exception as e:
            logger.error(f"[IntelligentCICD] Genesis integration failed: {e}")
            return {"genesis_integrated": False, "error": str(e)}

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _generate_decision_id(self) -> str:
        """Generate unique decision ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"decision:{timestamp}:{len(self.decisions)}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def _generate_genesis_key(self, category: str, action: str) -> str:
        """Generate Genesis Key for CI/CD operations."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"intelligent_cicd:{category}:{action}:{timestamp}"
        key_hash = hashlib.sha256(data.encode()).hexdigest()[:12]
        return f"GK-icicd-{key_hash}"

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "intelligence_mode": self.intelligence_mode.value,
            "decisions_made": len(self.decisions),
            "pipeline_runs": len(self.pipeline_runs),
            "test_metrics_tracked": len(self.test_selector.test_metrics),
            "webhooks_processed": self.webhook_processor.processed_count,
            "feedback_metrics": len(self.feedback_loop.metrics),
            "learning_examples": len(self.learning_memory),
            "auto_trigger_enabled": self.auto_trigger_enabled
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return {
            "status": self.get_status(),
            "recent_decisions": [
                asdict(d) for d in list(self.decisions.values())[-10:]
            ],
            "test_metrics": {
                t.test_id: asdict(t)
                for t in list(self.test_selector.test_metrics.values())[:20]
            },
            "feedback_summary": {
                name: {
                    "latest": metrics[-1].value if metrics else None,
                    "trend": metrics[-1].trend if metrics else "unknown",
                    "count": len(metrics)
                }
                for name, metrics in self.feedback_loop.metrics.items()
            },
            "recent_pipeline_runs": self.pipeline_runs[-10:]
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_intelligent_orchestrator: Optional[IntelligentCICDOrchestrator] = None


def get_intelligent_cicd_orchestrator(
    intelligence_mode: IntelligenceMode = IntelligenceMode.ML_ASSISTED
) -> IntelligentCICDOrchestrator:
    """Get or create global intelligent CI/CD orchestrator."""
    global _intelligent_orchestrator

    if _intelligent_orchestrator is None:
        _intelligent_orchestrator = IntelligentCICDOrchestrator(
            intelligence_mode=intelligence_mode
        )

    return _intelligent_orchestrator
