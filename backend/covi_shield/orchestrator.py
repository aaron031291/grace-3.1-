"""
COVI-SHIELD Orchestrator

Coordinates all COVI-SHIELD modules for comprehensive verification, repair, and learning.

Provides:
- Workflow management (quick_check, full_verification, repair_only)
- Module coordination
- Resource management
- Fault tolerance
"""

import logging
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import (
    VerificationResult,
    VerificationCertificate,
    RepairSuggestion,
    AnalysisReport,
    ShieldStatus,
    RiskLevel,
    AnalysisPhase,
    CertificateStatus
)
from .static_analyzer import StaticAnalyzer
from .formal_verifier import FormalVerifier
from .dynamic_analyzer import DynamicAnalyzer
from .repair_engine import RepairEngine
from .learning_module import LearningModule
from .certificate_authority import CertificateAuthority, CertificateType
from .knowledge_base import get_covi_shield_knowledge_base

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class VerificationLevel(str, Enum):
    """Level of verification depth."""
    QUICK = "quick"        # Static analysis only
    STANDARD = "standard"  # Static + formal
    FULL = "full"          # Static + formal + dynamic
    REPAIR = "repair"      # Full + auto-repair


class WorkflowType(str, Enum):
    """Type of verification workflow."""
    QUICK_CHECK = "quick_check"         # Fast static check
    FULL_VERIFICATION = "full_verification"  # Complete verification
    REPAIR_ONLY = "repair_only"         # Just repair existing code
    LEARNING_UPDATE = "learning_update"  # Update knowledge base


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class COVIShieldOrchestrator:
    """
    COVI-SHIELD Orchestrator.

    Coordinates all verification modules:
    - Static Analysis Engine
    - Formal Verification Engine
    - Dynamic Analysis Engine
    - Repair Engine
    - Learning Module
    - Certificate Authority

    Triggered on every Genesis Key creation for comprehensive protection.
    """

    def __init__(
        self,
        knowledge_base_path: Optional[Path] = None,
        secret_key: Optional[str] = None,
        auto_repair: bool = True,
        learning_enabled: bool = True
    ):
        # Initialize modules
        self.static_analyzer = StaticAnalyzer()
        self.formal_verifier = FormalVerifier(secret_key=secret_key)
        self.dynamic_analyzer = DynamicAnalyzer()
        self.repair_engine = RepairEngine()
        self.learning_module = LearningModule(
            knowledge_base_path=knowledge_base_path,
            memory_mesh_enabled=learning_enabled
        )
        self.certificate_authority = CertificateAuthority(secret_key=secret_key)

        # Configuration
        self.auto_repair = auto_repair
        self.learning_enabled = learning_enabled

        # GRACE integrations
        self.knowledge_base = get_covi_shield_knowledge_base(
            knowledge_base_path=knowledge_base_path
        )

        # Advanced GRACE systems (lazy loaded)
        self._oracle = None
        self._transformation_library = None
        self._healing_system = None
        self._ooda_engine = None
        self._magma_memory = None
        self._mirror_system = None
        self._timesense = None

        # Status tracking
        self.start_time = datetime.utcnow()
        self.total_analyses = 0
        self.total_bugs_detected = 0
        self.total_bugs_fixed = 0

        logger.info("[COVI-SHIELD] Orchestrator initialized - All modules active with GRACE integration")

    def analyze(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None,
        verification_level: VerificationLevel = VerificationLevel.STANDARD,
        genesis_key_id: Optional[str] = None,
        properties_to_verify: Optional[List[str]] = None,
        auto_repair: Optional[bool] = None
    ) -> AnalysisReport:
        """
        Perform comprehensive analysis on code.

        This is the main entry point - triggered on every Genesis Key.

        Args:
            code: Source code to analyze
            language: Programming language
            file_path: Optional file path for context
            verification_level: Depth of verification
            genesis_key_id: Associated Genesis Key
            properties_to_verify: Specific properties to verify
            auto_repair: Override auto-repair setting

        Returns:
            AnalysisReport with all results
        """
        start_time = time.time()
        self.total_analyses += 1

        should_repair = auto_repair if auto_repair is not None else self.auto_repair

        report = AnalysisReport(
            genesis_key_id=genesis_key_id,
            title=f"COVI-SHIELD Analysis: {file_path or 'code'}",
            phase=AnalysisPhase.PRE_FLIGHT
        )

        # Phase 1: Static Analysis (always)
        logger.info(f"[COVI-SHIELD] Phase 1: Static Analysis (level={verification_level.value})")
        report.static_analysis = self.static_analyzer.analyze(
            code=code,
            language=language,
            file_path=file_path,
            genesis_key_id=genesis_key_id
        )
        self.total_bugs_detected += report.static_analysis.issues_found

        # Phase 2: Formal Verification (standard and above)
        if verification_level in (VerificationLevel.STANDARD, VerificationLevel.FULL, VerificationLevel.REPAIR):
            logger.info("[COVI-SHIELD] Phase 2: Formal Verification")
            report.formal_verification = self.formal_verifier.verify(
                code=code,
                properties_to_verify=properties_to_verify,
                language=language,
                genesis_key_id=genesis_key_id
            )
            self.total_bugs_detected += report.formal_verification.issues_found

        # Phase 3: Dynamic Analysis (full and repair only)
        if verification_level in (VerificationLevel.FULL, VerificationLevel.REPAIR):
            logger.info("[COVI-SHIELD] Phase 3: Dynamic Analysis")
            report.dynamic_analysis = self.dynamic_analyzer.analyze_execution(
                code=code,
                genesis_key_id=genesis_key_id
            )
            self.total_bugs_detected += report.dynamic_analysis.issues_found

        # Collect all issues
        all_issues = []
        if report.static_analysis:
            all_issues.extend(report.static_analysis.issues)
        if report.formal_verification:
            all_issues.extend(report.formal_verification.issues)
        if report.dynamic_analysis:
            all_issues.extend(report.dynamic_analysis.issues)

        report.total_issues = len(all_issues)

        # Phase 4: Auto-Repair (if enabled and there are issues)
        repaired_code = code
        if should_repair and all_issues:
            logger.info("[COVI-SHIELD] Phase 4: Auto-Repair")
            repaired_code, suggestions = self.repair_engine.repair_all(
                code=code,
                issues=all_issues,
                genesis_key_id=genesis_key_id
            )
            report.repairs_suggested = suggestions
            report.repairs_applied = [s for s in suggestions if s.validation_passed]
            report.total_fixed = len(report.repairs_applied)
            self.total_bugs_fixed += report.total_fixed

        # Phase 5: Issue Certificate
        logger.info("[COVI-SHIELD] Phase 5: Certificate Generation")

        # Combine verification results
        combined_result = self._combine_results(report)

        report.certificate = self.certificate_authority.issue_certificate(
            verification_result=combined_result,
            certificate_type=CertificateType.VERIFICATION,
            properties_verified=properties_to_verify or []
        )

        # Phase 6: Learning (record outcome)
        if self.learning_enabled:
            logger.info("[COVI-SHIELD] Phase 6: Learning Update")
            self.learning_module.record_verification_outcome(
                verification_result=combined_result,
                code=code,
                genesis_key_id=genesis_key_id
            )

            # Record repair outcomes
            for suggestion in report.repairs_applied:
                self.learning_module.record_repair_outcome(
                    suggestion=suggestion,
                    applied=True,
                    verification_passed=suggestion.validation_passed,
                    genesis_key_id=genesis_key_id
                )

        # Calculate overall risk
        report.overall_risk = self._calculate_overall_risk(report)

        # Generate summary
        report.summary = self._generate_summary(report)
        report.analysis_duration_ms = (time.time() - start_time) * 1000

        # Phase 7: GRACE Knowledge Base Integration
        if self.learning_enabled:
            logger.info("[COVI-SHIELD] Phase 7: GRACE Knowledge Base Integration")
            try:
                integration_results = self.knowledge_base.process_analysis_complete(report)
                report.metrics["grace_integration"] = integration_results
            except Exception as e:
                logger.warning(f"[COVI-SHIELD] GRACE integration failed: {e}")

        logger.info(
            f"[COVI-SHIELD] Analysis complete: {report.total_issues} issues found, "
            f"{report.total_fixed} fixed, risk={report.overall_risk.value}, "
            f"certificate={report.certificate.certificate_id if report.certificate else 'none'}, "
            f"time={report.analysis_duration_ms:.2f}ms"
        )

        return report

    def quick_check(
        self,
        code: str,
        language: str = "python",
        genesis_key_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Perform quick static analysis check.

        Args:
            code: Code to check
            language: Programming language
            genesis_key_id: Associated Genesis Key

        Returns:
            VerificationResult from static analysis
        """
        return self.static_analyzer.analyze(
            code=code,
            language=language,
            genesis_key_id=genesis_key_id
        )

    def full_verify(
        self,
        code: str,
        language: str = "python",
        genesis_key_id: Optional[str] = None
    ) -> AnalysisReport:
        """
        Perform full verification without auto-repair.

        Args:
            code: Code to verify
            language: Programming language
            genesis_key_id: Associated Genesis Key

        Returns:
            AnalysisReport with full verification
        """
        return self.analyze(
            code=code,
            language=language,
            verification_level=VerificationLevel.FULL,
            genesis_key_id=genesis_key_id,
            auto_repair=False
        )

    def repair_and_verify(
        self,
        code: str,
        language: str = "python",
        genesis_key_id: Optional[str] = None
    ) -> Tuple[str, AnalysisReport]:
        """
        Repair code and verify the result.

        Args:
            code: Code to repair
            language: Programming language
            genesis_key_id: Associated Genesis Key

        Returns:
            Tuple of (repaired_code, AnalysisReport)
        """
        report = self.analyze(
            code=code,
            language=language,
            verification_level=VerificationLevel.REPAIR,
            genesis_key_id=genesis_key_id,
            auto_repair=True
        )

        # Get repaired code
        repaired_code = code
        if report.repairs_applied:
            # Take the last applied repair
            repaired_code = report.repairs_applied[-1].repaired_code

        return repaired_code, report

    def verify_certificate(
        self,
        certificate_id: str
    ) -> Tuple[bool, str]:
        """
        Verify a certificate's validity.

        Args:
            certificate_id: Certificate ID to verify

        Returns:
            Tuple of (is_valid, reason)
        """
        certificate = self.certificate_authority.get_certificate(certificate_id)
        if not certificate:
            return False, "Certificate not found"

        return self.certificate_authority.verify_certificate(certificate)

    def run_learning_cycle(self) -> Dict[str, Any]:
        """Run a learning cycle to improve detection and repair."""
        return self.learning_module.run_learning_cycle()

    def _combine_results(self, report: AnalysisReport) -> VerificationResult:
        """Combine all verification results into one."""
        all_issues = []
        all_proofs = []

        if report.static_analysis:
            all_issues.extend(report.static_analysis.issues)
            all_proofs.extend(report.static_analysis.proofs)

        if report.formal_verification:
            all_issues.extend(report.formal_verification.issues)
            all_proofs.extend(report.formal_verification.proofs)

        if report.dynamic_analysis:
            all_issues.extend(report.dynamic_analysis.issues)
            all_proofs.extend(report.dynamic_analysis.proofs)

        return VerificationResult(
            genesis_key_id=report.genesis_key_id,
            phase=report.phase,
            success=len(all_issues) == 0 or report.total_fixed == len(all_issues),
            risk_level=report.overall_risk,
            issues_found=len(all_issues),
            issues_fixed=report.total_fixed,
            issues=all_issues,
            proofs=all_proofs,
            metrics={
                "static_issues": report.static_analysis.issues_found if report.static_analysis else 0,
                "formal_issues": report.formal_verification.issues_found if report.formal_verification else 0,
                "dynamic_issues": report.dynamic_analysis.issues_found if report.dynamic_analysis else 0,
                "repairs_applied": report.total_fixed
            },
            analysis_time_ms=report.analysis_duration_ms
        )

    def _calculate_overall_risk(self, report: AnalysisReport) -> RiskLevel:
        """Calculate overall risk from all analyses."""
        risks = []

        if report.static_analysis:
            risks.append(report.static_analysis.risk_level)
        if report.formal_verification:
            risks.append(report.formal_verification.risk_level)
        if report.dynamic_analysis:
            risks.append(report.dynamic_analysis.risk_level)

        if not risks:
            return RiskLevel.INFO

        # Reduce risk if issues were fixed
        if report.total_fixed > 0:
            unfixed = report.total_issues - report.total_fixed
            if unfixed == 0:
                return RiskLevel.INFO

        # Return highest risk
        if RiskLevel.CRITICAL in risks:
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in risks:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risks:
            return RiskLevel.MEDIUM
        elif RiskLevel.LOW in risks:
            return RiskLevel.LOW
        return RiskLevel.INFO

    def _generate_summary(self, report: AnalysisReport) -> str:
        """Generate human-readable summary."""
        parts = [f"COVI-SHIELD Analysis Complete"]

        if report.total_issues == 0:
            parts.append("No issues detected. Code verified successfully.")
        else:
            parts.append(f"Found {report.total_issues} issue(s).")

            if report.total_fixed > 0:
                parts.append(f"Auto-repaired {report.total_fixed} issue(s).")

            unfixed = report.total_issues - report.total_fixed
            if unfixed > 0:
                parts.append(f"{unfixed} issue(s) require manual attention.")

        parts.append(f"Risk Level: {report.overall_risk.value.upper()}")

        if report.certificate:
            parts.append(f"Certificate: {report.certificate.certificate_id}")

        return " ".join(parts)

    def get_status(self) -> ShieldStatus:
        """Get COVI-SHIELD system status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        detection_rate = (
            self.total_bugs_detected / self.total_analyses
            if self.total_analyses > 0 else 0
        )

        correction_rate = (
            self.total_bugs_fixed / self.total_bugs_detected
            if self.total_bugs_detected > 0 else 0
        )

        return ShieldStatus(
            operational=True,
            modules_active={
                "static_analyzer": True,
                "formal_verifier": True,
                "dynamic_analyzer": True,
                "repair_engine": True,
                "learning_module": self.learning_enabled,
                "certificate_authority": True
            },
            total_analyses=self.total_analyses,
            total_bugs_detected=self.total_bugs_detected,
            total_bugs_fixed=self.total_bugs_fixed,
            total_certificates_issued=self.certificate_authority.stats["certificates_issued"],
            detection_rate=detection_rate,
            correction_rate=correction_rate,
            learning_improvement=self.learning_module.stats.get("patterns_promoted", 0) / 100,
            uptime_seconds=uptime,
            last_analysis=datetime.utcnow()
        )

    def get_module_stats(self) -> Dict[str, Any]:
        """Get statistics from all modules."""
        return {
            "orchestrator": {
                "total_analyses": self.total_analyses,
                "total_bugs_detected": self.total_bugs_detected,
                "total_bugs_fixed": self.total_bugs_fixed,
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            },
            "static_analyzer": self.static_analyzer.get_stats(),
            "formal_verifier": self.formal_verifier.get_stats(),
            "dynamic_analyzer": self.dynamic_analyzer.get_stats(),
            "repair_engine": self.repair_engine.get_stats(),
            "learning_module": self.learning_module.get_stats(),
            "certificate_authority": self.certificate_authority.get_stats()
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_covi_shield: Optional[COVIShieldOrchestrator] = None


def get_covi_shield(
    knowledge_base_path: Optional[Path] = None,
    secret_key: Optional[str] = None,
    auto_repair: bool = True,
    learning_enabled: bool = True
) -> COVIShieldOrchestrator:
    """Get or create global COVI-SHIELD instance."""
    global _covi_shield

    if _covi_shield is None:
        _covi_shield = COVIShieldOrchestrator(
            knowledge_base_path=knowledge_base_path,
            secret_key=secret_key,
            auto_repair=auto_repair,
            learning_enabled=learning_enabled
        )

    return _covi_shield
