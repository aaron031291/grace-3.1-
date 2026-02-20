"""
Adaptive CI/CD Pipeline System
==============================
Intelligent, self-improving CI/CD with:
- Trust scores for pipeline reliability
- KPI tracking and performance metrics
- LLM orchestration for intelligent decisions
- Sandbox testing before production
- Governance integration for human oversight

GRACE can autonomously trigger pipelines based on her needs,
test in sandbox, and request human approval via governance.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import statistics

logger = logging.getLogger(__name__)


class PipelineTrustLevel(str, Enum):
    """Trust levels for pipelines."""
    UNTRUSTED = "untrusted"      # New or failing pipeline
    LOW = "low"                   # < 50% success rate
    MEDIUM = "medium"             # 50-80% success rate
    HIGH = "high"                 # 80-95% success rate
    VERIFIED = "verified"         # > 95% success rate, human approved


class AdaptiveTriggerReason(str, Enum):
    """Reasons for adaptive pipeline triggers."""
    CODE_CHANGE = "code_change"
    SCHEDULED = "scheduled"
    ANOMALY_DETECTED = "anomaly_detected"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_CONCERN = "security_concern"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    SELF_IMPROVEMENT = "self_improvement"
    DEPENDENCY_UPDATE = "dependency_update"
    HUMAN_REQUEST = "human_request"
    AUTONOMOUS_DECISION = "autonomous_decision"


class GovernanceAction(str, Enum):
    """Actions requiring governance approval."""
    PRODUCTION_DEPLOY = "production_deploy"
    SECURITY_CHANGE = "security_change"
    TRUST_ELEVATION = "trust_elevation"
    AUTONOMOUS_MODIFICATION = "autonomous_modification"
    ROLLBACK = "rollback"
    NEW_PIPELINE = "new_pipeline"


@dataclass
class PipelineTrustScore:
    """Trust score for a pipeline."""
    pipeline_id: str
    trust_level: PipelineTrustLevel
    score: float  # 0.0 - 1.0
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_duration: float = 0
    reliability_trend: str = "stable"  # improving, stable, degrading
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    human_verified: bool = False
    verification_date: Optional[str] = None
    genesis_key: Optional[str] = None


@dataclass
class PipelineKPIs:
    """KPI metrics for a pipeline."""
    pipeline_id: str
    timestamp: str

    # Performance KPIs
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    p95_duration_seconds: float = 0.0
    throughput_per_hour: float = 0.0

    # Quality KPIs
    test_pass_rate: float = 0.0
    code_coverage: float = 0.0
    security_score: float = 0.0
    lint_score: float = 0.0

    # Efficiency KPIs
    resource_utilization: float = 0.0
    queue_wait_time: float = 0.0
    retry_rate: float = 0.0

    # Trend indicators
    performance_trend: str = "stable"
    quality_trend: str = "stable"

    # Composite scores
    overall_health: float = 0.0
    confidence: float = 0.0


@dataclass
class AdaptiveTrigger:
    """An adaptive pipeline trigger decision."""
    id: str
    pipeline_id: str
    reason: AdaptiveTriggerReason
    confidence: float
    trust_score: float
    requires_approval: bool
    governance_action: Optional[GovernanceAction]
    llm_recommendation: Optional[str]
    sandbox_required: bool
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernanceRequest:
    """Request for human oversight."""
    id: str
    action: GovernanceAction
    pipeline_id: str
    trigger_id: str
    reason: str
    risk_level: str  # low, medium, high, critical
    llm_analysis: str
    recommended_action: str
    requires_response: bool
    deadline: Optional[str]
    status: str = "pending"  # pending, approved, rejected, expired
    reviewer: Optional[str] = None
    response_time: Optional[str] = None
    genesis_key: Optional[str] = None


class AdaptiveCICD:
    """
    Adaptive CI/CD system with trust, KPIs, and governance.

    GRACE can:
    1. Monitor pipeline health and trust scores
    2. Make intelligent decisions using LLM orchestration
    3. Test changes in sandbox before production
    4. Request human approval via governance
    5. Learn and improve from outcomes
    """

    def __init__(self):
        # Trust scores
        self.trust_scores: Dict[str, PipelineTrustScore] = {}

        # KPI history
        self.kpi_history: Dict[str, List[PipelineKPIs]] = {}

        # Adaptive triggers
        self.triggers: Dict[str, AdaptiveTrigger] = {}

        # Governance requests
        self.governance_requests: Dict[str, GovernanceRequest] = {}

        # Run history for calculations
        self.run_history: Dict[str, List[Dict[str, Any]]] = {}

        # LLM recommendations cache
        self.llm_cache: Dict[str, Dict[str, Any]] = {}

        # Sandbox runs
        self.sandbox_runs: Dict[str, Dict[str, Any]] = {}

        logger.info("[Adaptive CICD] Initialized adaptive CI/CD system")

    # =========================================================================
    # Trust Score Management
    # =========================================================================

    def calculate_trust_score(self, pipeline_id: str) -> PipelineTrustScore:
        """
        Calculate trust score for a pipeline based on history.
        """
        history = self.run_history.get(pipeline_id, [])

        if not history:
            return PipelineTrustScore(
                pipeline_id=pipeline_id,
                trust_level=PipelineTrustLevel.UNTRUSTED,
                score=0.0,
                genesis_key=self._generate_genesis_key("trust", pipeline_id)
            )

        # Calculate metrics
        total = len(history)
        successful = sum(1 for r in history if r.get("status") == "success")
        failed = total - successful
        success_rate = successful / total if total > 0 else 0

        # Calculate average duration
        durations = [r.get("duration", 0) for r in history if r.get("duration")]
        avg_duration = statistics.mean(durations) if durations else 0

        # Determine trust level
        if success_rate >= 0.95 and total >= 20:
            trust_level = PipelineTrustLevel.VERIFIED
        elif success_rate >= 0.80:
            trust_level = PipelineTrustLevel.HIGH
        elif success_rate >= 0.50:
            trust_level = PipelineTrustLevel.MEDIUM
        elif success_rate > 0:
            trust_level = PipelineTrustLevel.LOW
        else:
            trust_level = PipelineTrustLevel.UNTRUSTED

        # Calculate trend (last 10 vs previous 10)
        if len(history) >= 20:
            recent = history[-10:]
            previous = history[-20:-10]
            recent_rate = sum(1 for r in recent if r.get("status") == "success") / 10
            previous_rate = sum(1 for r in previous if r.get("status") == "success") / 10

            if recent_rate > previous_rate + 0.1:
                trend = "improving"
            elif recent_rate < previous_rate - 0.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Find last success/failure
        last_success = None
        last_failure = None
        for r in reversed(history):
            if r.get("status") == "success" and not last_success:
                last_success = r.get("timestamp")
            elif r.get("status") == "failed" and not last_failure:
                last_failure = r.get("timestamp")
            if last_success and last_failure:
                break

        trust_score = PipelineTrustScore(
            pipeline_id=pipeline_id,
            trust_level=trust_level,
            score=success_rate,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration=avg_duration,
            reliability_trend=trend,
            last_success=last_success,
            last_failure=last_failure,
            human_verified=self.trust_scores.get(pipeline_id, PipelineTrustScore(
                pipeline_id=pipeline_id,
                trust_level=PipelineTrustLevel.UNTRUSTED,
                score=0.0
            )).human_verified,
            genesis_key=self._generate_genesis_key("trust", pipeline_id)
        )

        self.trust_scores[pipeline_id] = trust_score
        return trust_score

    def record_run_result(
        self,
        pipeline_id: str,
        status: str,
        duration: float,
        metadata: Dict[str, Any] = None
    ):
        """Record a pipeline run result for trust calculation."""
        if pipeline_id not in self.run_history:
            self.run_history[pipeline_id] = []

        self.run_history[pipeline_id].append({
            "status": status,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })

        # Keep last 100 runs
        self.run_history[pipeline_id] = self.run_history[pipeline_id][-100:]

        # Recalculate trust
        self.calculate_trust_score(pipeline_id)

    # =========================================================================
    # KPI Tracking
    # =========================================================================

    def calculate_kpis(self, pipeline_id: str) -> PipelineKPIs:
        """Calculate KPI metrics for a pipeline."""
        history = self.run_history.get(pipeline_id, [])

        if not history:
            return PipelineKPIs(
                pipeline_id=pipeline_id,
                timestamp=datetime.now().isoformat()
            )

        # Performance KPIs
        total = len(history)
        successful = sum(1 for r in history if r.get("status") == "success")
        success_rate = successful / total if total > 0 else 0

        durations = [r.get("duration", 0) for r in history if r.get("duration")]
        avg_duration = statistics.mean(durations) if durations else 0
        p95_duration = (
            sorted(durations)[int(len(durations) * 0.95)]
            if len(durations) > 1 else avg_duration
        )

        # Calculate throughput (runs per hour in last 24h)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_runs = [
            r for r in history
            if datetime.fromisoformat(r.get("timestamp", "2000-01-01")) > recent_cutoff
        ]
        throughput = len(recent_runs) / 24 if recent_runs else 0

        # Quality metrics from metadata
        test_scores = [
            r.get("metadata", {}).get("test_pass_rate", 0)
            for r in history if r.get("metadata", {}).get("test_pass_rate")
        ]
        test_pass_rate = statistics.mean(test_scores) if test_scores else 0

        coverage_scores = [
            r.get("metadata", {}).get("coverage", 0)
            for r in history if r.get("metadata", {}).get("coverage")
        ]
        code_coverage = statistics.mean(coverage_scores) if coverage_scores else 0

        # Retry rate
        retries = sum(1 for r in history if r.get("metadata", {}).get("is_retry", False))
        retry_rate = retries / total if total > 0 else 0

        # Calculate trends
        if len(history) >= 20:
            recent = history[-10:]
            previous = history[-20:-10]

            recent_success = sum(1 for r in recent if r.get("status") == "success") / 10
            previous_success = sum(1 for r in previous if r.get("status") == "success") / 10

            if recent_success > previous_success + 0.05:
                perf_trend = "improving"
            elif recent_success < previous_success - 0.05:
                perf_trend = "degrading"
            else:
                perf_trend = "stable"
        else:
            perf_trend = "stable"

        # Overall health score (weighted average)
        health = (
            success_rate * 0.4 +
            (1 - retry_rate) * 0.2 +
            test_pass_rate * 0.2 +
            (code_coverage / 100 if code_coverage else 0.5) * 0.2
        )

        # Confidence based on sample size
        confidence = min(1.0, total / 50)

        kpis = PipelineKPIs(
            pipeline_id=pipeline_id,
            timestamp=datetime.now().isoformat(),
            success_rate=success_rate,
            avg_duration_seconds=avg_duration,
            p95_duration_seconds=p95_duration,
            throughput_per_hour=throughput,
            test_pass_rate=test_pass_rate,
            code_coverage=code_coverage,
            retry_rate=retry_rate,
            performance_trend=perf_trend,
            overall_health=health,
            confidence=confidence
        )

        # Store in history
        if pipeline_id not in self.kpi_history:
            self.kpi_history[pipeline_id] = []
        self.kpi_history[pipeline_id].append(kpis)
        self.kpi_history[pipeline_id] = self.kpi_history[pipeline_id][-100:]

        return kpis

    # =========================================================================
    # LLM Orchestration Integration
    # =========================================================================

    async def get_llm_recommendation(
        self,
        pipeline_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get LLM recommendation for pipeline decision.

        Integrates with LLM orchestration for intelligent analysis.
        """
        try:
            from api.llm_orchestration import get_orchestrator

            orchestrator = get_orchestrator()

            # Build context for LLM
            trust = self.trust_scores.get(pipeline_id)
            kpis = self.calculate_kpis(pipeline_id)

            prompt = f"""Analyze this CI/CD pipeline situation and provide a recommendation:

Pipeline: {pipeline_id}
Trust Level: {trust.trust_level.value if trust else 'unknown'}
Trust Score: {trust.score if trust else 0:.2%}
Success Rate: {kpis.success_rate:.2%}
Overall Health: {kpis.overall_health:.2%}
Performance Trend: {kpis.performance_trend}

Context:
{json.dumps(context, indent=2)}

Recent History:
- Total Runs: {trust.total_runs if trust else 0}
- Last Success: {trust.last_success if trust else 'Never'}
- Last Failure: {trust.last_failure if trust else 'Never'}
- Trend: {trust.reliability_trend if trust else 'Unknown'}

Provide:
1. Risk assessment (low/medium/high/critical)
2. Recommended action (proceed/sandbox/defer/reject)
3. Confidence level (0-100%)
4. Reasoning (brief)
5. Whether human approval is needed (yes/no)

Format as JSON."""

            # Get LLM response
            response = await orchestrator.generate(
                prompt=prompt,
                context={"pipeline_analysis": True},
                temperature=0.3
            )

            # Parse response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    recommendation = json.loads(json_match.group())
                else:
                    recommendation = {
                        "risk": "medium",
                        "action": "proceed",
                        "confidence": 50,
                        "reasoning": response[:500],
                        "needs_approval": True
                    }
            except json.JSONDecodeError:
                recommendation = {
                    "risk": "medium",
                    "action": "proceed",
                    "confidence": 50,
                    "reasoning": response[:500],
                    "needs_approval": True
                }

            # Cache result
            cache_key = f"{pipeline_id}:{hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()[:8]}"
            self.llm_cache[cache_key] = {
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt[:500]
            }

            logger.info(f"[Adaptive] LLM recommendation for {pipeline_id}: {recommendation.get('action')}")

            return recommendation

        except Exception as e:
            logger.error(f"[Adaptive] LLM recommendation failed: {e}")
            # Fallback to rule-based
            return self._rule_based_recommendation(pipeline_id, context)

    def _rule_based_recommendation(
        self,
        pipeline_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback rule-based recommendation."""
        trust = self.trust_scores.get(pipeline_id)
        kpis = self.calculate_kpis(pipeline_id)

        if not trust or trust.trust_level == PipelineTrustLevel.UNTRUSTED:
            return {
                "risk": "high",
                "action": "sandbox",
                "confidence": 70,
                "reasoning": "Pipeline has no trust history - sandbox testing required",
                "needs_approval": True
            }

        if trust.trust_level == PipelineTrustLevel.LOW:
            return {
                "risk": "high",
                "action": "sandbox",
                "confidence": 60,
                "reasoning": f"Low trust score ({trust.score:.0%}) - sandbox recommended",
                "needs_approval": True
            }

        if trust.reliability_trend == "degrading":
            return {
                "risk": "medium",
                "action": "sandbox",
                "confidence": 65,
                "reasoning": "Performance degrading - sandbox verification recommended",
                "needs_approval": True
            }

        if trust.trust_level in [PipelineTrustLevel.HIGH, PipelineTrustLevel.VERIFIED]:
            return {
                "risk": "low",
                "action": "proceed",
                "confidence": 85,
                "reasoning": f"High trust ({trust.score:.0%}) and stable performance",
                "needs_approval": False
            }

        return {
            "risk": "medium",
            "action": "proceed",
            "confidence": 70,
            "reasoning": "Medium trust - proceed with monitoring",
            "needs_approval": False
        }

    # =========================================================================
    # Adaptive Triggering
    # =========================================================================

    async def should_trigger_pipeline(
        self,
        pipeline_id: str,
        reason: AdaptiveTriggerReason,
        context: Dict[str, Any] = None
    ) -> AdaptiveTrigger:
        """
        Determine if a pipeline should be triggered and how.

        Returns an AdaptiveTrigger with decision details.
        """
        context = context or {}
        trust = self.trust_scores.get(pipeline_id) or self.calculate_trust_score(pipeline_id)

        # Get LLM recommendation
        llm_rec = await self.get_llm_recommendation(pipeline_id, {
            "reason": reason.value,
            **context
        })

        # Determine if governance approval needed
        requires_approval = False
        governance_action = None
        sandbox_required = False

        # High-risk actions always need approval
        if reason in [AdaptiveTriggerReason.SECURITY_CONCERN, AdaptiveTriggerReason.AUTONOMOUS_DECISION]:
            requires_approval = True
            governance_action = GovernanceAction.SECURITY_CHANGE

        # Low trust requires sandbox
        if trust.trust_level in [PipelineTrustLevel.UNTRUSTED, PipelineTrustLevel.LOW]:
            sandbox_required = True
            requires_approval = True
            governance_action = GovernanceAction.NEW_PIPELINE

        # LLM recommends approval
        if llm_rec.get("needs_approval", False):
            requires_approval = True

        # LLM recommends sandbox
        if llm_rec.get("action") == "sandbox":
            sandbox_required = True

        trigger = AdaptiveTrigger(
            id=self._generate_trigger_id(pipeline_id),
            pipeline_id=pipeline_id,
            reason=reason,
            confidence=llm_rec.get("confidence", 50) / 100,
            trust_score=trust.score,
            requires_approval=requires_approval,
            governance_action=governance_action,
            llm_recommendation=json.dumps(llm_rec),
            sandbox_required=sandbox_required,
            timestamp=datetime.now().isoformat(),
            metadata={
                "context": context,
                "trust_level": trust.trust_level.value,
                "risk": llm_rec.get("risk", "medium")
            }
        )

        self.triggers[trigger.id] = trigger

        logger.info(
            f"[Adaptive] Trigger decision for {pipeline_id}: "
            f"sandbox={sandbox_required}, approval={requires_approval}, "
            f"confidence={trigger.confidence:.0%}"
        )

        return trigger

    async def trigger_autonomous_pipeline(
        self,
        pipeline_id: str,
        reason: AdaptiveTriggerReason,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Autonomously trigger a pipeline with full adaptive logic.

        1. Evaluate if trigger is appropriate
        2. Run in sandbox if needed
        3. Request governance approval if required
        4. Execute and track results
        """
        # Get trigger decision
        trigger = await self.should_trigger_pipeline(pipeline_id, reason, context)

        result = {
            "trigger_id": trigger.id,
            "pipeline_id": pipeline_id,
            "status": "pending",
            "sandbox_run": None,
            "governance_request": None,
            "production_run": None
        }

        # Step 1: Sandbox if required
        if trigger.sandbox_required:
            sandbox_result = await self.run_in_sandbox(pipeline_id, trigger.id, context)
            result["sandbox_run"] = sandbox_result

            if sandbox_result.get("status") == "failed":
                result["status"] = "sandbox_failed"
                logger.warning(f"[Adaptive] Sandbox failed for {pipeline_id}")
                return result

        # Step 2: Request governance approval if required
        if trigger.requires_approval:
            gov_request = await self.request_governance_approval(trigger)
            result["governance_request"] = {
                "id": gov_request.id,
                "status": gov_request.status,
                "action": gov_request.action.value
            }

            if gov_request.status != "approved":
                result["status"] = "awaiting_approval"
                return result

        # Step 3: Execute production run
        from genesis.cicd import get_cicd

        cicd = get_cicd()
        run = await cicd.trigger_pipeline(
            pipeline_id=pipeline_id,
            trigger=reason.value,
            branch=context.get("branch", "main"),
            triggered_by="grace_adaptive"
        )

        result["production_run"] = {
            "run_id": run.id,
            "genesis_key": run.genesis_key,
            "status": run.status.value
        }
        result["status"] = "triggered"

        logger.info(f"[Adaptive] Triggered pipeline {pipeline_id} (run: {run.id})")

        return result

    # =========================================================================
    # Sandbox Testing
    # =========================================================================

    async def run_in_sandbox(
        self,
        pipeline_id: str,
        trigger_id: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a pipeline in sandbox mode for testing.

        Isolates execution and validates before production.
        """
        sandbox_id = f"sandbox-{trigger_id[:8]}"

        logger.info(f"[Adaptive] Starting sandbox run for {pipeline_id}")

        try:
            from genesis.cicd import get_cicd

            cicd = get_cicd()

            # Check if pipeline exists
            pipeline = cicd.get_pipeline(pipeline_id)
            if not pipeline:
                return {
                    "sandbox_id": sandbox_id,
                    "status": "failed",
                    "error": f"Pipeline '{pipeline_id}' not found"
                }

            # Create sandbox run with limited scope
            run = await cicd.trigger_pipeline(
                pipeline_id=pipeline_id,
                trigger="sandbox",
                branch=context.get("branch", "main") if context else "main",
                triggered_by="sandbox_test",
                variables={"SANDBOX_MODE": "true", "DRY_RUN": "true"}
            )

            # Wait for completion (with timeout)
            timeout = 300  # 5 minutes
            start = datetime.now()

            while (datetime.now() - start).seconds < timeout:
                current_run = cicd.get_run(run.id)
                if current_run.status.value in ["success", "failed", "cancelled"]:
                    break
                await asyncio.sleep(5)

            final_run = cicd.get_run(run.id)

            sandbox_result = {
                "sandbox_id": sandbox_id,
                "run_id": run.id,
                "status": final_run.status.value,
                "duration": final_run.duration_seconds,
                "stages_passed": sum(
                    1 for s in final_run.stage_results
                    if s.status.value == "success"
                ),
                "stages_total": len(final_run.stage_results),
                "timestamp": datetime.now().isoformat()
            }

            self.sandbox_runs[sandbox_id] = sandbox_result

            logger.info(f"[Adaptive] Sandbox {sandbox_id} completed: {final_run.status.value}")

            return sandbox_result

        except Exception as e:
            logger.error(f"[Adaptive] Sandbox failed: {e}")
            return {
                "sandbox_id": sandbox_id,
                "status": "failed",
                "error": str(e)
            }

    # =========================================================================
    # Governance Integration
    # =========================================================================

    async def request_governance_approval(
        self,
        trigger: AdaptiveTrigger
    ) -> GovernanceRequest:
        """
        Request human oversight via governance system.

        Integrates with Three-Pillar Governance framework.
        """
        # Get LLM analysis for governance
        llm_rec = json.loads(trigger.llm_recommendation) if trigger.llm_recommendation else {}

        # Determine risk level
        risk_level = llm_rec.get("risk", "medium")

        # Calculate deadline based on risk
        if risk_level == "critical":
            deadline = (datetime.now() + timedelta(hours=1)).isoformat()
        elif risk_level == "high":
            deadline = (datetime.now() + timedelta(hours=4)).isoformat()
        else:
            deadline = (datetime.now() + timedelta(hours=24)).isoformat()

        request = GovernanceRequest(
            id=f"gov-{trigger.id[:8]}",
            action=trigger.governance_action or GovernanceAction.AUTONOMOUS_MODIFICATION,
            pipeline_id=trigger.pipeline_id,
            trigger_id=trigger.id,
            reason=f"Adaptive trigger: {trigger.reason.value}",
            risk_level=risk_level,
            llm_analysis=llm_rec.get("reasoning", "No analysis available"),
            recommended_action=llm_rec.get("action", "proceed"),
            requires_response=True,
            deadline=deadline,
            genesis_key=self._generate_genesis_key("governance", trigger.pipeline_id)
        )

        self.governance_requests[request.id] = request

        # Try to integrate with actual governance system
        try:
            from api.governance_api import submit_governance_request

            await submit_governance_request({
                "type": request.action.value,
                "resource": f"pipeline:{trigger.pipeline_id}",
                "risk_level": risk_level,
                "description": request.reason,
                "analysis": request.llm_analysis,
                "deadline": deadline,
                "metadata": {
                    "trigger_id": trigger.id,
                    "trust_score": trigger.trust_score,
                    "confidence": trigger.confidence
                }
            })

        except Exception as e:
            logger.warning(f"[Adaptive] Could not submit to governance system: {e}")

        logger.info(
            f"[Adaptive] Governance request {request.id} created for {trigger.pipeline_id} "
            f"(risk: {risk_level}, deadline: {deadline})"
        )

        return request

    def approve_governance_request(
        self,
        request_id: str,
        reviewer: str,
        approved: bool
    ) -> GovernanceRequest:
        """Process governance approval response."""
        request = self.governance_requests.get(request_id)

        if not request:
            raise ValueError(f"Governance request '{request_id}' not found")

        request.status = "approved" if approved else "rejected"
        request.reviewer = reviewer
        request.response_time = datetime.now().isoformat()

        logger.info(
            f"[Adaptive] Governance request {request_id} {request.status} by {reviewer}"
        )

        return request

    # =========================================================================
    # Self-Improvement
    # =========================================================================

    async def analyze_and_improve(self) -> Dict[str, Any]:
        """
        GRACE analyzes pipeline performance and suggests improvements.

        This is called periodically for self-improvement.
        """
        improvements = []

        for pipeline_id, trust in self.trust_scores.items():
            kpis = self.calculate_kpis(pipeline_id)

            # Check for degrading pipelines
            if trust.reliability_trend == "degrading":
                improvements.append({
                    "pipeline_id": pipeline_id,
                    "issue": "degrading_performance",
                    "recommendation": "Investigate recent failures",
                    "priority": "high"
                })

            # Check for slow pipelines
            if kpis.avg_duration_seconds > 600:  # > 10 minutes
                improvements.append({
                    "pipeline_id": pipeline_id,
                    "issue": "slow_execution",
                    "recommendation": "Optimize pipeline stages",
                    "priority": "medium",
                    "avg_duration": kpis.avg_duration_seconds
                })

            # Check for high retry rate
            if kpis.retry_rate > 0.2:  # > 20% retries
                improvements.append({
                    "pipeline_id": pipeline_id,
                    "issue": "high_retry_rate",
                    "recommendation": "Investigate flaky tests or unstable stages",
                    "priority": "high",
                    "retry_rate": kpis.retry_rate
                })

        return {
            "timestamp": datetime.now().isoformat(),
            "pipelines_analyzed": len(self.trust_scores),
            "improvements_found": len(improvements),
            "improvements": improvements
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_genesis_key(self, action: str, resource: str) -> str:
        """Generate Genesis Key for adaptive operations."""
        timestamp = datetime.now().isoformat()
        key_data = f"adaptive:{action}:{resource}:{timestamp}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:12]
        return f"gk-adapt-{key_hash}"

    def _generate_trigger_id(self, pipeline_id: str) -> str:
        """Generate unique trigger ID."""
        timestamp = datetime.now().isoformat()
        key_data = f"trigger:{pipeline_id}:{timestamp}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:12]

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return {
            "timestamp": datetime.now().isoformat(),
            "trust_scores": {
                pid: asdict(ts) for pid, ts in self.trust_scores.items()
            },
            "kpis": {
                pid: asdict(self.calculate_kpis(pid))
                for pid in self.trust_scores.keys()
            },
            "pending_governance": [
                asdict(gr) for gr in self.governance_requests.values()
                if gr.status == "pending"
            ],
            "recent_triggers": list(self.triggers.values())[-10:],
            "sandbox_runs": list(self.sandbox_runs.values())[-10:]
        }


# =============================================================================
# Global Instance
# =============================================================================

_adaptive_cicd: Optional[AdaptiveCICD] = None


def get_adaptive_cicd() -> AdaptiveCICD:
    """Get the global adaptive CI/CD instance."""
    global _adaptive_cicd
    if _adaptive_cicd is None:
        _adaptive_cicd = AdaptiveCICD()
    return _adaptive_cicd
