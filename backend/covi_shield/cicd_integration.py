"""
COVI-SHIELD CI/CD Pipeline Integration

Integrates COVI-SHIELD verification into CI/CD pipelines to:
- Verify code before pipeline execution
- Gate deployments on verification status
- Learn from pipeline outcomes
- Prevent cascading failures in production

Philosophy: "Verify before deploy, don't deploy to verify."
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .models import (
    VerificationResult,
    VerificationCertificate,
    AnalysisReport,
    RiskLevel,
    CertificateStatus
)
from .orchestrator import COVIShieldOrchestrator, get_covi_shield, VerificationLevel

logger = logging.getLogger(__name__)


class PipelineGateDecision(str, Enum):
    """Decision for pipeline gate."""
    ALLOW = "allow"           # Continue pipeline
    WARN = "warn"             # Continue with warning
    BLOCK = "block"           # Block pipeline
    REQUIRE_APPROVAL = "require_approval"  # Human approval needed


@dataclass
class PipelineVerificationResult:
    """Result of COVI-SHIELD pipeline verification."""
    pipeline_id: str
    run_id: str
    decision: PipelineGateDecision
    risk_level: RiskLevel
    issues_found: int
    issues_fixed: int
    certificate_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "run_id": self.run_id,
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "issues_found": self.issues_found,
            "issues_fixed": self.issues_fixed,
            "certificate_id": self.certificate_id,
            "details": self.details,
            "recommendations": self.recommendations,
            "verified_at": self.verified_at
        }


class COVIShieldCICDIntegration:
    """
    Integrates COVI-SHIELD with CI/CD pipelines.

    Provides:
    - Pre-pipeline verification
    - Pipeline gate decisions
    - Code quality gates
    - Deployment verification
    - Post-pipeline learning
    """

    # Risk level to gate decision mapping
    RISK_GATE_MAPPING = {
        RiskLevel.INFO: PipelineGateDecision.ALLOW,
        RiskLevel.LOW: PipelineGateDecision.ALLOW,
        RiskLevel.MEDIUM: PipelineGateDecision.WARN,
        RiskLevel.HIGH: PipelineGateDecision.REQUIRE_APPROVAL,
        RiskLevel.CRITICAL: PipelineGateDecision.BLOCK
    }

    def __init__(
        self,
        orchestrator: Optional[COVIShieldOrchestrator] = None,
        strict_mode: bool = False,
        auto_fix: bool = True
    ):
        """
        Initialize CI/CD integration.

        Args:
            orchestrator: COVI-SHIELD orchestrator (creates if None)
            strict_mode: If True, MEDIUM risk also blocks
            auto_fix: If True, attempt auto-fixes before decision
        """
        self._orchestrator = orchestrator
        self.strict_mode = strict_mode
        self.auto_fix = auto_fix
        self.verification_history: Dict[str, PipelineVerificationResult] = {}
        self.stats = {
            "pipelines_verified": 0,
            "pipelines_allowed": 0,
            "pipelines_blocked": 0,
            "issues_found": 0,
            "issues_fixed": 0
        }

        logger.info(
            f"[COVI-SHIELD CICD] Initialized (strict={strict_mode}, auto_fix={auto_fix})"
        )

    @property
    def orchestrator(self) -> COVIShieldOrchestrator:
        """Lazy-load orchestrator."""
        if self._orchestrator is None:
            self._orchestrator = get_covi_shield(
                auto_repair=self.auto_fix,
                learning_enabled=True
            )
        return self._orchestrator

    def verify_before_pipeline(
        self,
        pipeline_id: str,
        run_id: str,
        code_changes: List[Dict[str, Any]],
        pipeline_type: str = "build",
        verification_level: VerificationLevel = VerificationLevel.STANDARD
    ) -> PipelineVerificationResult:
        """
        Verify code changes before pipeline execution.

        Args:
            pipeline_id: Pipeline identifier
            run_id: Pipeline run identifier
            code_changes: List of code changes to verify
            pipeline_type: Type of pipeline (build, test, deploy)
            verification_level: How thorough to verify

        Returns:
            PipelineVerificationResult with gate decision
        """
        logger.info(
            f"[COVI-SHIELD CICD] Verifying pipeline {pipeline_id} run {run_id} "
            f"({len(code_changes)} changes)"
        )

        self.stats["pipelines_verified"] += 1

        # Aggregate results across all changes
        total_issues = 0
        total_fixed = 0
        max_risk = RiskLevel.INFO
        all_issues: List[Dict[str, Any]] = []
        certificates: List[str] = []

        # Verify each code change
        for change in code_changes:
            code = change.get("content", "")
            file_path = change.get("file_path", "unknown")

            if not code:
                continue

            # Run verification
            report = self.orchestrator.analyze(
                code=code,
                file_path=file_path,
                verification_level=verification_level,
                auto_repair=self.auto_fix,
                genesis_key_id=f"cicd-{pipeline_id}-{run_id}"
            )

            total_issues += report.total_issues
            total_fixed += report.total_fixed

            # Track max risk
            risk_order = [RiskLevel.INFO, RiskLevel.LOW, RiskLevel.MEDIUM,
                         RiskLevel.HIGH, RiskLevel.CRITICAL]
            if risk_order.index(report.overall_risk) > risk_order.index(max_risk):
                max_risk = report.overall_risk

            # Collect issues
            if report.static_analysis:
                for issue in report.static_analysis.issues:
                    all_issues.append({
                        "file": file_path,
                        **issue
                    })

            if report.certificate:
                certificates.append(report.certificate.certificate_id)

        # Update stats
        self.stats["issues_found"] += total_issues
        self.stats["issues_fixed"] += total_fixed

        # Determine gate decision
        decision = self._determine_gate_decision(max_risk, pipeline_type)

        if decision == PipelineGateDecision.ALLOW:
            self.stats["pipelines_allowed"] += 1
        elif decision == PipelineGateDecision.BLOCK:
            self.stats["pipelines_blocked"] += 1

        # Build recommendations
        recommendations = self._build_recommendations(
            all_issues, max_risk, total_fixed, pipeline_type
        )

        # Create result
        result = PipelineVerificationResult(
            pipeline_id=pipeline_id,
            run_id=run_id,
            decision=decision,
            risk_level=max_risk,
            issues_found=total_issues,
            issues_fixed=total_fixed,
            certificate_id=certificates[0] if certificates else None,
            details={
                "files_verified": len(code_changes),
                "issues": all_issues[:20],  # Limit for readability
                "certificates": certificates,
                "verification_level": verification_level.value
            },
            recommendations=recommendations
        )

        # Store in history
        self.verification_history[f"{pipeline_id}:{run_id}"] = result

        logger.info(
            f"[COVI-SHIELD CICD] Pipeline {pipeline_id} verification complete: "
            f"decision={decision.value}, risk={max_risk.value}, "
            f"issues={total_issues}, fixed={total_fixed}"
        )

        return result

    def _determine_gate_decision(
        self,
        risk_level: RiskLevel,
        pipeline_type: str
    ) -> PipelineGateDecision:
        """
        Determine gate decision based on risk and pipeline type.

        Deploy pipelines are more strict than build pipelines.
        """
        base_decision = self.RISK_GATE_MAPPING.get(
            risk_level, PipelineGateDecision.BLOCK
        )

        # Stricter for deployments
        if pipeline_type == "deploy":
            if base_decision == PipelineGateDecision.WARN:
                return PipelineGateDecision.REQUIRE_APPROVAL
            elif risk_level == RiskLevel.MEDIUM and self.strict_mode:
                return PipelineGateDecision.REQUIRE_APPROVAL

        # Strict mode elevates MEDIUM to blocking
        if self.strict_mode and risk_level == RiskLevel.MEDIUM:
            return PipelineGateDecision.REQUIRE_APPROVAL

        return base_decision

    def _build_recommendations(
        self,
        issues: List[Dict[str, Any]],
        risk_level: RiskLevel,
        fixed_count: int,
        pipeline_type: str
    ) -> List[str]:
        """Build recommendations based on verification results."""
        recommendations = []

        if risk_level == RiskLevel.CRITICAL:
            recommendations.append(
                "CRITICAL: Security vulnerabilities detected. "
                "Do not proceed until resolved."
            )

        if risk_level == RiskLevel.HIGH:
            recommendations.append(
                "HIGH risk issues found. Review and fix before deployment."
            )

        # Group issues by category
        categories = {}
        for issue in issues:
            cat = issue.get("pattern_id", "unknown").split("-")[0]
            categories[cat] = categories.get(cat, 0) + 1

        if "SEC" in categories:
            recommendations.append(
                f"Found {categories['SEC']} security issues. "
                "Run security review before proceeding."
            )

        if fixed_count > 0:
            recommendations.append(
                f"Auto-fixed {fixed_count} issues. Verify fixes are correct."
            )

        if pipeline_type == "deploy" and risk_level != RiskLevel.INFO:
            recommendations.append(
                "Consider additional testing before production deployment."
            )

        return recommendations

    def verify_deployment_gate(
        self,
        pipeline_id: str,
        run_id: str,
        environment: str = "production"
    ) -> Tuple[bool, str]:
        """
        Final deployment gate verification.

        Args:
            pipeline_id: Pipeline identifier
            run_id: Pipeline run identifier
            environment: Target environment

        Returns:
            Tuple of (allowed, reason)
        """
        key = f"{pipeline_id}:{run_id}"
        result = self.verification_history.get(key)

        if not result:
            return False, "No verification result found. Run verify_before_pipeline first."

        # Production is strictest
        if environment == "production":
            if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return False, f"Blocked: {result.risk_level.value} risk for production"

            if result.risk_level == RiskLevel.MEDIUM and self.strict_mode:
                return False, "Blocked: Medium risk in strict mode"

            if result.decision == PipelineGateDecision.BLOCK:
                return False, "Pipeline verification blocked deployment"

        # Staging allows more risk
        elif environment == "staging":
            if result.risk_level == RiskLevel.CRITICAL:
                return False, "Critical risk blocks all deployments"

        # Check for valid certificate
        if not result.certificate_id:
            logger.warning(
                f"[COVI-SHIELD CICD] No certificate for deployment to {environment}"
            )

        return True, "Deployment approved by COVI-SHIELD"

    def learn_from_pipeline_outcome(
        self,
        pipeline_id: str,
        run_id: str,
        success: bool,
        failures: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Learn from pipeline execution outcome.

        Args:
            pipeline_id: Pipeline identifier
            run_id: Pipeline run identifier
            success: Whether pipeline succeeded
            failures: Any failures that occurred
        """
        key = f"{pipeline_id}:{run_id}"
        result = self.verification_history.get(key)

        if not result:
            return

        # Feed back to learning system
        try:
            learning_result = self.orchestrator.run_learning_cycle()
            logger.debug(
                f"[COVI-SHIELD CICD] Learning from pipeline outcome: "
                f"success={success}, cycle={learning_result.get('cycle_number')}"
            )
        except Exception as e:
            logger.warning(f"[COVI-SHIELD CICD] Learning feedback failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get CI/CD integration statistics."""
        return {
            **self.stats,
            "history_size": len(self.verification_history),
            "strict_mode": self.strict_mode,
            "auto_fix": self.auto_fix
        }

    def get_verification_history(
        self,
        pipeline_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get verification history."""
        results = []

        for key, result in self.verification_history.items():
            if pipeline_id and not key.startswith(f"{pipeline_id}:"):
                continue
            results.append(result.to_dict())

        # Sort by time descending
        results.sort(key=lambda x: x["verified_at"], reverse=True)
        return results[:limit]


# ============================================================================
# PIPELINE HOOKS
# ============================================================================

def create_covi_shield_pipeline_hook(
    strict_mode: bool = False,
    auto_fix: bool = True
) -> COVIShieldCICDIntegration:
    """
    Create a COVI-SHIELD hook for CI/CD pipelines.

    Usage in pipeline:
        hook = create_covi_shield_pipeline_hook()
        result = hook.verify_before_pipeline(
            pipeline_id="my-pipeline",
            run_id="run-123",
            code_changes=[{"file_path": "main.py", "content": "..."}]
        )
        if result.decision == PipelineGateDecision.BLOCK:
            raise PipelineBlockedError(result.recommendations)
    """
    return COVIShieldCICDIntegration(
        strict_mode=strict_mode,
        auto_fix=auto_fix
    )


# Global instance
_cicd_integration: Optional[COVIShieldCICDIntegration] = None


def get_covi_shield_cicd_integration(
    strict_mode: bool = False,
    auto_fix: bool = True
) -> COVIShieldCICDIntegration:
    """Get or create global CI/CD integration instance."""
    global _cicd_integration

    if _cicd_integration is None:
        _cicd_integration = COVIShieldCICDIntegration(
            strict_mode=strict_mode,
            auto_fix=auto_fix
        )

    return _cicd_integration


# ============================================================================
# DECORATOR FOR PIPELINE VERIFICATION
# ============================================================================

def covi_shield_verified(
    verification_level: VerificationLevel = VerificationLevel.STANDARD,
    strict: bool = False,
    block_on_high_risk: bool = True
):
    """
    Decorator to require COVI-SHIELD verification before pipeline function.

    Usage:
        @covi_shield_verified(verification_level=VerificationLevel.FULL)
        async def my_pipeline_stage(code_changes, **kwargs):
            # Your pipeline logic
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get integration
            integration = get_covi_shield_cicd_integration(strict_mode=strict)

            # Extract pipeline info from kwargs
            pipeline_id = kwargs.get("pipeline_id", "unknown")
            run_id = kwargs.get("run_id", "unknown")
            code_changes = kwargs.get("code_changes", [])

            # Verify
            result = integration.verify_before_pipeline(
                pipeline_id=pipeline_id,
                run_id=run_id,
                code_changes=code_changes,
                verification_level=verification_level
            )

            # Check decision
            if result.decision == PipelineGateDecision.BLOCK:
                raise RuntimeError(
                    f"COVI-SHIELD blocked pipeline: {result.recommendations}"
                )

            if block_on_high_risk and result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                raise RuntimeError(
                    f"COVI-SHIELD blocked due to {result.risk_level.value} risk"
                )

            # Add verification result to kwargs
            kwargs["covi_shield_result"] = result

            return await func(*args, **kwargs)

        return wrapper
    return decorator
