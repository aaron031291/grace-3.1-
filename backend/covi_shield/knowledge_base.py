"""
COVI-SHIELD Knowledge Base Integration

Integrates COVI-SHIELD with GRACE's comprehensive ecosystem:
- Trust Scoring (Adaptive, Neural, Deterministic)
- KPI Tracking (Component and System-wide)
- Compliance Monitoring (SOC2, HIPAA, GDPR, ISO27001)
- Immutable Audit Trails
- Governance (Layer3 Quorum, Constitutional Framework)
- Cascading Failure Prediction (Oracle Intelligence)
- Diagnostic Machine (Sensors, Healing)
- Pattern Mining (Transformation Library)
- TimeSense (Performance Estimation)
- Zero Trust Security (Threat Detection)
- Hallucination Guard (AI Validation)
- Memory Mesh (Distributed Learning)
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

try:
    from .models import (
        VerificationResult,
        VerificationCertificate,
        RepairSuggestion,
        AnalysisReport,
        RiskLevel,
        CertificateStatus
    )
except ImportError:
    # Minimal fallback for testing
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# TRUST SCORE INTEGRATION
# ============================================================================

class COVIShieldTrustIntegration:
    """
    Integrates COVI-SHIELD with GRACE's trust scoring systems.

    Uses:
    - AdaptiveTrustScorer for context-aware trust
    - NeuralTrustScorer for learned patterns
    - DeterministicTrustProver for mathematical proofs
    """

    def __init__(self):
        self._adaptive_scorer = None
        self._neural_scorer = None
        self._deterministic_prover = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of trust components."""
        if self._initialized:
            return

        try:
            from cognitive.enhanced_trust_scorer import AdaptiveTrustScorer
            self._adaptive_scorer = AdaptiveTrustScorer()
            logger.info("[COVI-SHIELD Trust] AdaptiveTrustScorer initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Trust] AdaptiveTrustScorer not available: {e}")

        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer
            self._neural_scorer = NeuralTrustScorer()
            logger.info("[COVI-SHIELD Trust] NeuralTrustScorer initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Trust] NeuralTrustScorer not available: {e}")

        try:
            from cognitive.deterministic_trust_proofs import DeterministicTrustProver
            self._deterministic_prover = DeterministicTrustProver()
            logger.info("[COVI-SHIELD Trust] DeterministicTrustProver initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Trust] DeterministicTrustProver not available: {e}")

        self._initialized = True

    def calculate_verification_trust(
        self,
        verification_result: VerificationResult,
        context_type: str = "OPERATIONAL"
    ) -> Dict[str, Any]:
        """
        Calculate trust score for a verification result.

        Args:
            verification_result: The verification result to score
            context_type: SAFETY_CRITICAL, OPERATIONAL, THEORETICAL, GENERAL

        Returns:
            Dict with trust score, confidence interval, and breakdown
        """
        self._lazy_init()

        trust_data = {
            "trust_score": 0.5,
            "confidence_interval": (0.4, 0.6),
            "uncertainty": 0.3,
            "factors": {},
            "neural_prediction": None,
            "proof_verified": False
        }

        # Factor 1: Issue severity
        severity_scores = {
            RiskLevel.INFO: 1.0,
            RiskLevel.LOW: 0.9,
            RiskLevel.MEDIUM: 0.7,
            RiskLevel.HIGH: 0.4,
            RiskLevel.CRITICAL: 0.1
        }
        severity_trust = severity_scores.get(verification_result.risk_level, 0.5)
        trust_data["factors"]["severity"] = severity_trust

        # Factor 2: Fix rate
        if verification_result.issues_found > 0:
            fix_rate = verification_result.issues_fixed / verification_result.issues_found
        else:
            fix_rate = 1.0
        trust_data["factors"]["fix_rate"] = fix_rate

        # Factor 3: Proof success rate
        proofs = verification_result.proofs or []
        if proofs:
            verified_proofs = sum(1 for p in proofs if p.get("verified", False))
            proof_rate = verified_proofs / len(proofs)
        else:
            proof_rate = 0.5
        trust_data["factors"]["proof_rate"] = proof_rate

        # Calculate composite trust score
        base_trust = (severity_trust * 0.4 + fix_rate * 0.3 + proof_rate * 0.3)

        # Use adaptive scorer if available
        if self._adaptive_scorer:
            try:
                adaptive_result = self._adaptive_scorer.calculate_trust_score(
                    source="covi_shield_verification",
                    validated_count=verification_result.issues_fixed,
                    invalidated_count=verification_result.issues_found - verification_result.issues_fixed,
                    context_type=context_type
                )
                trust_data["trust_score"] = adaptive_result.trust_score
                trust_data["confidence_interval"] = adaptive_result.confidence_interval
                trust_data["uncertainty"] = adaptive_result.uncertainty
            except Exception as e:
                logger.warning(f"[COVI-SHIELD Trust] Adaptive scoring failed: {e}")
                trust_data["trust_score"] = base_trust
        else:
            trust_data["trust_score"] = base_trust

        # Neural trust prediction if available
        if self._neural_scorer:
            try:
                neural_result = self._neural_scorer.predict_trust({
                    "issues_found": verification_result.issues_found,
                    "issues_fixed": verification_result.issues_fixed,
                    "risk_level": verification_result.risk_level.value
                })
                trust_data["neural_prediction"] = neural_result
            except Exception as e:
                logger.debug(f"[COVI-SHIELD Trust] Neural prediction skipped: {e}")

        # Verify determinism if prover available
        if self._deterministic_prover:
            try:
                proof = self._deterministic_prover.prove_trust_score_determinism(
                    lambda: trust_data["trust_score"]
                )
                trust_data["proof_verified"] = proof.is_valid
            except Exception as e:
                logger.debug(f"[COVI-SHIELD Trust] Determinism proof skipped: {e}")

        return trust_data


# ============================================================================
# KPI TRACKING INTEGRATION
# ============================================================================

class COVIShieldKPIIntegration:
    """
    Integrates COVI-SHIELD with GRACE's KPI tracking system.

    Tracks:
    - Analyses performed
    - Issues detected
    - Issues fixed
    - Certificates issued
    - Learning cycles
    """

    COMPONENT_NAME = "covi_shield"

    def __init__(self):
        self._tracker = None
        self._registered = False

    def _lazy_init(self):
        """Lazy initialization of KPI tracker."""
        if self._registered:
            return

        try:
            from ml_intelligence.kpi_tracker import KPITracker, KPI

            self._tracker = KPITracker()

            # Register COVI-SHIELD component with KPIs
            self._tracker.register_component(
                component_name=self.COMPONENT_NAME,
                kpis={
                    "analyses_performed": KPI(
                        name="analyses_performed",
                        value=0,
                        weight=0.1,
                        threshold=0
                    ),
                    "issues_detected": KPI(
                        name="issues_detected",
                        value=0,
                        weight=0.2,
                        threshold=0
                    ),
                    "issues_fixed": KPI(
                        name="issues_fixed",
                        value=0,
                        weight=0.3,
                        threshold=0
                    ),
                    "fix_success_rate": KPI(
                        name="fix_success_rate",
                        value=1.0,
                        weight=0.3,
                        threshold=0.8
                    ),
                    "certificates_issued": KPI(
                        name="certificates_issued",
                        value=0,
                        weight=0.1,
                        threshold=0
                    )
                }
            )

            self._registered = True
            logger.info("[COVI-SHIELD KPI] Registered with KPI tracker")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD KPI] KPI tracker not available: {e}")

    def record_analysis(
        self,
        report: AnalysisReport
    ):
        """Record analysis KPIs."""
        self._lazy_init()

        if not self._tracker:
            return

        try:
            self._tracker.increment_kpi(
                self.COMPONENT_NAME,
                "analyses_performed",
                1
            )

            self._tracker.increment_kpi(
                self.COMPONENT_NAME,
                "issues_detected",
                report.total_issues
            )

            self._tracker.increment_kpi(
                self.COMPONENT_NAME,
                "issues_fixed",
                report.total_fixed
            )

            if report.certificate:
                self._tracker.increment_kpi(
                    self.COMPONENT_NAME,
                    "certificates_issued",
                    1
                )

            # Update fix success rate
            if report.total_issues > 0:
                rate = report.total_fixed / report.total_issues
                # Update as running average
                current_rate = self._tracker.get_component_kpis(
                    self.COMPONENT_NAME
                ).get("fix_success_rate", {}).get("value", 1.0)
                new_rate = (current_rate + rate) / 2
                self._tracker.set_kpi(
                    self.COMPONENT_NAME,
                    "fix_success_rate",
                    new_rate
                )

            logger.debug(f"[COVI-SHIELD KPI] Recorded analysis KPIs")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD KPI] Failed to record KPIs: {e}")

    def get_trust_score(self) -> float:
        """Get COVI-SHIELD's trust score from KPIs."""
        self._lazy_init()

        if not self._tracker:
            return 0.8  # Default

        try:
            return self._tracker.get_component_trust_score(self.COMPONENT_NAME)
        except Exception:
            return 0.8

    def get_health_signal(self) -> Dict[str, Any]:
        """Get COVI-SHIELD health signal."""
        self._lazy_init()

        if not self._tracker:
            return {"status": "unknown"}

        try:
            return self._tracker.get_health_signal(self.COMPONENT_NAME)
        except Exception:
            return {"status": "unknown"}


# ============================================================================
# COMPLIANCE INTEGRATION
# ============================================================================

class COVIShieldComplianceIntegration:
    """
    Integrates COVI-SHIELD with GRACE's compliance monitoring.

    Maps verification certificates to compliance controls:
    - SOC 2: CC6.1 (Access Control), CC8.1 (Change Management)
    - HIPAA: 164.312 (Technical Safeguards)
    - GDPR: Art25 (Data Protection by Design)
    - ISO 27001: A.12.6.1 (Technical Vulnerability Management)
    """

    # Mapping of verification outcomes to compliance controls
    COMPLIANCE_MAPPINGS = {
        "static_analysis": [
            ("SOC2", "CC8.1", "code_review"),
            ("ISO27001", "A.12.6.1", "vulnerability_management")
        ],
        "formal_verification": [
            ("SOC2", "CC6.1", "access_verification"),
            ("HIPAA", "164.312(d)", "verification")
        ],
        "security_scan": [
            ("SOC2", "CC7.1", "vulnerability_detection"),
            ("ISO27001", "A.12.6.1", "vulnerability_management"),
            ("GDPR", "Art32", "security_measures")
        ],
        "auto_repair": [
            ("SOC2", "CC8.1", "change_management"),
            ("ISO27001", "A.14.2.2", "change_control")
        ],
        "certificate": [
            ("SOC2", "CC6.2", "certification"),
            ("GDPR", "Art25", "data_protection_by_design")
        ]
    }

    def __init__(self):
        self._compliance_monitor = None
        self._framework_mapping = None

    def _lazy_init(self):
        """Lazy initialization of compliance components."""
        if self._compliance_monitor is not None:
            return

        try:
            from security.compliance.continuous_monitoring import ComplianceMonitor
            from security.compliance.frameworks import FrameworkMapping

            self._compliance_monitor = ComplianceMonitor()
            self._framework_mapping = FrameworkMapping()

            logger.info("[COVI-SHIELD Compliance] Compliance integration initialized")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Compliance] Compliance system not available: {e}")

    def record_compliance_evidence(
        self,
        report: AnalysisReport,
        verification_type: str
    ):
        """
        Record compliance evidence from verification.

        Args:
            report: Analysis report
            verification_type: Type of verification performed
        """
        self._lazy_init()

        if not self._framework_mapping:
            return

        try:
            # Get applicable compliance mappings
            mappings = self.COMPLIANCE_MAPPINGS.get(verification_type, [])

            for framework, control_id, evidence_type in mappings:
                # Record assessment
                self._framework_mapping.record_assessment(
                    framework=framework,
                    control_id=control_id,
                    status="pass" if report.overall_risk != RiskLevel.CRITICAL else "fail",
                    evidence={
                        "covi_shield_report_id": report.report_id,
                        "genesis_key_id": report.genesis_key_id,
                        "verification_type": verification_type,
                        "issues_found": report.total_issues,
                        "issues_fixed": report.total_fixed,
                        "risk_level": report.overall_risk.value,
                        "certificate_id": report.certificate.certificate_id if report.certificate else None,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    notes=f"COVI-SHIELD {verification_type} verification"
                )

            logger.debug(
                f"[COVI-SHIELD Compliance] Recorded evidence for {len(mappings)} controls"
            )

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Compliance] Failed to record evidence: {e}")

    def get_compliance_status(self) -> Dict[str, Any]:
        """Get compliance status for COVI-SHIELD related controls."""
        self._lazy_init()

        if not self._framework_mapping:
            return {"status": "unavailable"}

        try:
            # Get summaries for each framework
            summaries = {}
            for framework in ["SOC2", "HIPAA", "GDPR", "ISO27001"]:
                summaries[framework] = self._framework_mapping.get_compliance_summary(framework)

            return {
                "status": "available",
                "frameworks": summaries
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================================================
# AUDIT TRAIL INTEGRATION
# ============================================================================

class COVIShieldAuditIntegration:
    """
    Integrates COVI-SHIELD with GRACE's immutable audit trail.

    Records all COVI-SHIELD operations in tamper-evident audit log:
    - Verification events
    - Repair events
    - Certificate events
    - Learning events
    """

    def __init__(self, session=None):
        self._audit_storage = None
        self._session = session

    def _lazy_init(self):
        """Lazy initialization of audit storage."""
        if self._audit_storage is not None:
            return

        try:
            from genesis.immutable_audit_storage import ImmutableAuditStorage

            self._audit_storage = ImmutableAuditStorage(session=self._session)
            logger.info("[COVI-SHIELD Audit] Immutable audit storage initialized")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Audit] Audit storage not available: {e}")

    def record_verification(
        self,
        report: AnalysisReport,
        actor: str = "covi_shield"
    ):
        """Record verification event in audit trail."""
        self._lazy_init()

        if not self._audit_storage:
            return

        try:
            from genesis.immutable_audit_storage import ImmutableAuditType

            self._audit_storage.record(
                event_type=ImmutableAuditType.AI_DECISION,
                actor=actor,
                action="covi_shield_verification",
                resource_type="code",
                resource_id=report.genesis_key_id or report.report_id,
                details={
                    "report_id": report.report_id,
                    "phase": report.phase.value,
                    "total_issues": report.total_issues,
                    "total_fixed": report.total_fixed,
                    "overall_risk": report.overall_risk.value,
                    "has_static_analysis": report.static_analysis is not None,
                    "has_formal_verification": report.formal_verification is not None,
                    "has_dynamic_analysis": report.dynamic_analysis is not None
                },
                outcome="success" if report.overall_risk != RiskLevel.CRITICAL else "warning",
                genesis_key_id=report.genesis_key_id
            )

            logger.debug(f"[COVI-SHIELD Audit] Recorded verification event")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Audit] Failed to record verification: {e}")

    def record_repair(
        self,
        suggestion: RepairSuggestion,
        applied: bool,
        actor: str = "covi_shield"
    ):
        """Record repair event in audit trail."""
        self._lazy_init()

        if not self._audit_storage:
            return

        try:
            from genesis.immutable_audit_storage import ImmutableAuditType

            self._audit_storage.record(
                event_type=ImmutableAuditType.CODE_CHANGE,
                actor=actor,
                action="covi_shield_repair",
                resource_type="code",
                resource_id=suggestion.genesis_key_id or suggestion.suggestion_id,
                details={
                    "suggestion_id": suggestion.suggestion_id,
                    "issue_id": suggestion.issue_id,
                    "strategy": suggestion.strategy.value,
                    "confidence": suggestion.confidence,
                    "applied": applied,
                    "validation_passed": suggestion.validation_passed
                },
                outcome="success" if applied and suggestion.validation_passed else "pending",
                genesis_key_id=suggestion.genesis_key_id
            )

            logger.debug(f"[COVI-SHIELD Audit] Recorded repair event")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Audit] Failed to record repair: {e}")

    def record_certificate(
        self,
        certificate: VerificationCertificate,
        action: str,  # "issued", "verified", "revoked"
        actor: str = "covi_shield"
    ):
        """Record certificate event in audit trail."""
        self._lazy_init()

        if not self._audit_storage:
            return

        try:
            from genesis.immutable_audit_storage import ImmutableAuditType

            self._audit_storage.record(
                event_type=ImmutableAuditType.GENESIS_KEY_CREATED,
                actor=actor,
                action=f"covi_shield_certificate_{action}",
                resource_type="certificate",
                resource_id=certificate.certificate_id,
                details={
                    "certificate_id": certificate.certificate_id,
                    "status": certificate.status.value,
                    "properties_verified": certificate.properties_verified,
                    "proof_type": certificate.proof_type.value,
                    "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None
                },
                outcome="success",
                genesis_key_id=certificate.genesis_key_id
            )

            logger.debug(f"[COVI-SHIELD Audit] Recorded certificate event: {action}")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Audit] Failed to record certificate: {e}")

    def get_audit_trail(
        self,
        genesis_key_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get COVI-SHIELD audit trail."""
        self._lazy_init()

        if not self._audit_storage:
            return []

        try:
            if genesis_key_id:
                return self._audit_storage.get_genesis_audit_trail(genesis_key_id)
            else:
                return self._audit_storage.get_audit_trail(
                    action_filter="covi_shield",
                    limit=limit
                )

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Audit] Failed to get audit trail: {e}")
            return []


# ============================================================================
# GOVERNANCE INTEGRATION
# ============================================================================

class COVIShieldGovernanceIntegration:
    """
    Integrates COVI-SHIELD with GRACE's governance systems.

    Uses:
    - Layer3 Quorum for trust verification
    - Constitutional Framework for ethics checks
    - Genesis Key contradiction detection
    """

    def __init__(self, session=None):
        self._quorum_engine = None
        self._session = session

    def _lazy_init(self):
        """Lazy initialization of governance components."""
        if self._quorum_engine is not None:
            return

        try:
            from governance.layer3_quorum_verification import QuorumEngine

            self._quorum_engine = QuorumEngine(session=self._session)
            logger.info("[COVI-SHIELD Governance] Quorum engine initialized")

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Governance] Quorum engine not available: {e}")

    def assess_verification_trust(
        self,
        report: AnalysisReport
    ) -> Dict[str, Any]:
        """
        Assess trust of verification using quorum system.

        Args:
            report: Analysis report to assess

        Returns:
            Trust assessment from governance
        """
        self._lazy_init()

        if not self._quorum_engine:
            return {"trust": 0.8, "source": "default"}

        try:
            # Build trust assessment request
            assessment = self._quorum_engine.assess_trust(
                data={
                    "type": "covi_shield_verification",
                    "report_id": report.report_id,
                    "risk_level": report.overall_risk.value,
                    "issues_found": report.total_issues,
                    "issues_fixed": report.total_fixed
                },
                source="INTERNAL_DATA",  # COVI-SHIELD is internal
                genesis_key_id=report.genesis_key_id
            )

            return {
                "trust": assessment.trust_score,
                "source": assessment.source,
                "verified": assessment.is_trusted,
                "requires_quorum": assessment.requires_quorum
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Governance] Trust assessment failed: {e}")
            return {"trust": 0.8, "source": "default"}

    def check_constitutional_compliance(
        self,
        repair_suggestion: RepairSuggestion
    ) -> Tuple[bool, str]:
        """
        Check if repair complies with constitutional principles.

        Args:
            repair_suggestion: Repair to check

        Returns:
            Tuple of (is_compliant, reason)
        """
        self._lazy_init()

        if not self._quorum_engine:
            return True, "Governance not available - default allow"

        try:
            # Check constitutional framework
            result = self._quorum_engine.check_constitutional_compliance(
                action={
                    "type": "code_modification",
                    "suggestion_id": repair_suggestion.suggestion_id,
                    "strategy": repair_suggestion.strategy.value,
                    "confidence": repair_suggestion.confidence
                }
            )

            return result.is_compliant, result.reasoning

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Governance] Constitutional check failed: {e}")
            return True, "Check failed - default allow"

    def record_component_outcome(
        self,
        success: bool,
        details: Dict[str, Any]
    ):
        """Record COVI-SHIELD outcome for quorum KPI tracking."""
        self._lazy_init()

        if not self._quorum_engine:
            return

        try:
            self._quorum_engine.record_component_outcome(
                component_id="covi_shield",
                success=success,
                details=details
            )

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Governance] Failed to record outcome: {e}")


# ============================================================================
# CASCADING FAILURE PREDICTOR INTEGRATION
# ============================================================================

class COVIShieldFailurePredictorIntegration:
    """
    Integrates COVI-SHIELD with Oracle's Cascading Failure Predictor.

    Predicts potential failures BEFORE they occur, enabling:
    - Proactive bug prevention
    - Risk assessment before code changes
    - Dependency impact analysis
    """

    def __init__(self):
        self._predictor = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of failure predictor."""
        if self._initialized:
            return

        try:
            from oracle_intelligence.cascading_failure_predictor import CascadingFailurePredictor
            self._predictor = CascadingFailurePredictor()
            logger.info("[COVI-SHIELD Oracle] Cascading Failure Predictor initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Oracle] Failure predictor not available: {e}")

        self._initialized = True

    def predict_code_failures(
        self,
        code: str,
        file_path: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Predict potential failures from code changes.

        Args:
            code: Code to analyze
            file_path: Path of the code file
            dependencies: Known dependencies

        Returns:
            Prediction results with failure risks
        """
        self._lazy_init()

        if not self._predictor:
            return {
                "prediction_available": False,
                "risk_score": 0.5,
                "cascading_risks": []
            }

        try:
            prediction = self._predictor.predict(
                change={
                    "type": "code_change",
                    "content": code[:5000],  # Limit size
                    "file_path": file_path,
                    "dependencies": dependencies or []
                }
            )

            return {
                "prediction_available": True,
                "risk_score": prediction.risk_score,
                "cascading_risks": prediction.cascading_effects,
                "affected_components": prediction.affected_components,
                "recommendation": prediction.recommendation
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Oracle] Prediction failed: {e}")
            return {
                "prediction_available": False,
                "risk_score": 0.5,
                "cascading_risks": [],
                "error": str(e)
            }

    def assess_repair_risk(
        self,
        original_code: str,
        repaired_code: str,
        issue_id: str
    ) -> Dict[str, Any]:
        """
        Assess risk of applying a repair.

        Args:
            original_code: Original code
            repaired_code: Proposed repair
            issue_id: Issue being fixed

        Returns:
            Risk assessment for the repair
        """
        self._lazy_init()

        if not self._predictor:
            return {"safe_to_apply": True, "reason": "Predictor not available"}

        try:
            assessment = self._predictor.assess_change_risk(
                before=original_code,
                after=repaired_code,
                change_type="covi_shield_repair"
            )

            return {
                "safe_to_apply": assessment.risk_score < 0.7,
                "risk_score": assessment.risk_score,
                "potential_issues": assessment.potential_issues,
                "reason": assessment.reasoning
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Oracle] Risk assessment failed: {e}")
            return {"safe_to_apply": True, "reason": "Assessment failed - default allow"}


# ============================================================================
# DIAGNOSTIC MACHINE INTEGRATION
# ============================================================================

class COVIShieldDiagnosticIntegration:
    """
    Integrates COVI-SHIELD with GRACE's Diagnostic Machine.

    Provides:
    - Real-time sensor data for verification
    - System health context
    - Historical diagnostic patterns
    - Automatic bug fixing coordination
    """

    def __init__(self):
        self._diagnostic_engine = None
        self._bug_fixer = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of diagnostic components."""
        if self._initialized:
            return

        try:
            from diagnostic_machine.diagnostic_engine import DiagnosticEngine
            self._diagnostic_engine = DiagnosticEngine()
            logger.info("[COVI-SHIELD Diagnostic] Diagnostic Engine initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Diagnostic] Engine not available: {e}")

        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            self._bug_fixer = AutomaticBugFixer()
            logger.info("[COVI-SHIELD Diagnostic] Bug Fixer initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Diagnostic] Bug Fixer not available: {e}")

        self._initialized = True

    def get_system_context(self) -> Dict[str, Any]:
        """
        Get current system diagnostic context.

        Returns:
            System health and diagnostic data
        """
        self._lazy_init()

        if not self._diagnostic_engine:
            return {"context_available": False}

        try:
            diagnostics = self._diagnostic_engine.get_current_diagnostics()

            return {
                "context_available": True,
                "system_health": diagnostics.overall_health,
                "active_issues": diagnostics.active_issues,
                "sensor_readings": diagnostics.sensor_summary,
                "recent_trends": diagnostics.trend_summary
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Diagnostic] Context fetch failed: {e}")
            return {"context_available": False, "error": str(e)}

    def correlate_with_diagnostics(
        self,
        verification_result: VerificationResult
    ) -> Dict[str, Any]:
        """
        Correlate verification results with diagnostic data.

        Args:
            verification_result: COVI-SHIELD verification result

        Returns:
            Correlated diagnostic insights
        """
        self._lazy_init()

        if not self._diagnostic_engine:
            return {"correlation_available": False}

        try:
            correlation = self._diagnostic_engine.correlate_issue(
                issue_type="code_verification",
                severity=verification_result.risk_level.value,
                details={
                    "issues_found": verification_result.issues_found,
                    "phase": verification_result.phase.value
                }
            )

            return {
                "correlation_available": True,
                "related_diagnostics": correlation.related_issues,
                "root_cause_hints": correlation.root_cause_candidates,
                "historical_pattern": correlation.historical_matches
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Diagnostic] Correlation failed: {e}")
            return {"correlation_available": False}

    def get_fix_suggestions(
        self,
        issue: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get fix suggestions from the automatic bug fixer.

        Args:
            issue: Issue details

        Returns:
            List of fix suggestions
        """
        self._lazy_init()

        if not self._bug_fixer:
            return []

        try:
            suggestions = self._bug_fixer.suggest_fixes(
                issue_type=issue.get("pattern_id", "unknown"),
                issue_details=issue
            )

            return [
                {
                    "fix_id": s.fix_id,
                    "description": s.description,
                    "confidence": s.confidence,
                    "code_change": s.code_change
                }
                for s in suggestions
            ]

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Diagnostic] Fix suggestion failed: {e}")
            return []


# ============================================================================
# PATTERN MINER INTEGRATION
# ============================================================================

class COVIShieldPatternMinerIntegration:
    """
    Integrates COVI-SHIELD with GRACE's Transformation Library Pattern Miner.

    Provides:
    - Vulnerability pattern detection
    - AST-based pattern matching
    - Historical pattern database
    - Code transformation templates
    """

    def __init__(self):
        self._pattern_miner = None
        self._ast_matcher = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of pattern mining components."""
        if self._initialized:
            return

        try:
            from cognitive.transformation_library.pattern_miner import PatternMiner
            self._pattern_miner = PatternMiner()
            logger.info("[COVI-SHIELD Patterns] Pattern Miner initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Patterns] Pattern Miner not available: {e}")

        try:
            from cognitive.transformation_library.ast_matcher import ASTMatcher
            self._ast_matcher = ASTMatcher()
            logger.info("[COVI-SHIELD Patterns] AST Matcher initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Patterns] AST Matcher not available: {e}")

        self._initialized = True

    def mine_vulnerability_patterns(
        self,
        code: str,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Mine code for vulnerability patterns.

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            List of detected vulnerability patterns
        """
        self._lazy_init()

        if not self._pattern_miner:
            return []

        try:
            patterns = self._pattern_miner.mine_patterns(
                code=code,
                pattern_types=["security", "bug", "smell"],
                language=language
            )

            return [
                {
                    "pattern_id": p.pattern_id,
                    "name": p.name,
                    "severity": p.severity,
                    "locations": p.locations,
                    "confidence": p.confidence,
                    "fix_template": p.fix_template
                }
                for p in patterns
            ]

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Patterns] Pattern mining failed: {e}")
            return []

    def match_ast_patterns(
        self,
        code: str,
        pattern_queries: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Match AST patterns in code.

        Args:
            code: Source code
            pattern_queries: AST pattern queries to match

        Returns:
            List of pattern matches
        """
        self._lazy_init()

        if not self._ast_matcher:
            return []

        try:
            matches = self._ast_matcher.match_patterns(
                code=code,
                patterns=pattern_queries
            )

            return [
                {
                    "pattern": m.pattern,
                    "location": m.location,
                    "matched_code": m.matched_code,
                    "bindings": m.bindings
                }
                for m in matches
            ]

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Patterns] AST matching failed: {e}")
            return []

    def get_transformation_template(
        self,
        pattern_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get code transformation template for a pattern.

        Args:
            pattern_id: Pattern to get template for

        Returns:
            Transformation template if available
        """
        self._lazy_init()

        if not self._pattern_miner:
            return None

        try:
            template = self._pattern_miner.get_transformation(pattern_id)

            if template:
                return {
                    "pattern_id": pattern_id,
                    "before_template": template.before,
                    "after_template": template.after,
                    "constraints": template.constraints,
                    "confidence": template.confidence
                }
            return None

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Patterns] Template fetch failed: {e}")
            return None


# ============================================================================
# TIMESENSE INTEGRATION
# ============================================================================

class COVIShieldTimeSenseIntegration:
    """
    Integrates COVI-SHIELD with GRACE's TimeSense Engine.

    Provides:
    - Repair time estimation
    - Performance impact prediction
    - Verification time budgeting
    - Historical timing data
    """

    def __init__(self):
        self._timesense_engine = None
        self._predictor = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of TimeSense components."""
        if self._initialized:
            return

        try:
            from timesense.engine import TimeSenseEngine
            self._timesense_engine = TimeSenseEngine()
            logger.info("[COVI-SHIELD TimeSense] TimeSense Engine initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD TimeSense] Engine not available: {e}")

        try:
            from timesense.predictor import RuntimePredictor
            self._predictor = RuntimePredictor()
            logger.info("[COVI-SHIELD TimeSense] Runtime Predictor initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD TimeSense] Predictor not available: {e}")

        self._initialized = True

    def estimate_repair_time(
        self,
        repair_suggestion: RepairSuggestion
    ) -> Dict[str, Any]:
        """
        Estimate time to apply a repair.

        Args:
            repair_suggestion: Repair to estimate

        Returns:
            Time estimation with confidence
        """
        self._lazy_init()

        if not self._timesense_engine:
            return {"estimated_ms": 100, "confidence": 0.5}

        try:
            estimate = self._timesense_engine.estimate_operation(
                operation_type="code_repair",
                complexity_hints={
                    "strategy": repair_suggestion.strategy.value,
                    "code_size": len(repair_suggestion.repaired_code or ""),
                    "confidence": repair_suggestion.confidence
                }
            )

            return {
                "estimated_ms": estimate.estimated_time_ms,
                "confidence": estimate.confidence,
                "breakdown": estimate.breakdown
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD TimeSense] Estimation failed: {e}")
            return {"estimated_ms": 100, "confidence": 0.5}

    def predict_verification_impact(
        self,
        code: str,
        verification_level: str
    ) -> Dict[str, Any]:
        """
        Predict time impact of verification.

        Args:
            code: Code to verify
            verification_level: QUICK, STANDARD, FULL, REPAIR

        Returns:
            Time prediction for verification
        """
        self._lazy_init()

        if not self._predictor:
            return {"predicted_ms": 1000, "confidence": 0.5}

        try:
            prediction = self._predictor.predict_runtime(
                operation="covi_shield_verification",
                inputs={
                    "code_length": len(code),
                    "verification_level": verification_level
                }
            )

            return {
                "predicted_ms": prediction.predicted_time_ms,
                "confidence": prediction.confidence,
                "range": (prediction.min_time_ms, prediction.max_time_ms)
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD TimeSense] Prediction failed: {e}")
            return {"predicted_ms": 1000, "confidence": 0.5}


# ============================================================================
# ZERO TRUST INTEGRATION
# ============================================================================

class COVIShieldZeroTrustIntegration:
    """
    Integrates COVI-SHIELD with GRACE's Zero Trust Security.

    Provides:
    - Threat detection in code
    - Security policy enforcement
    - Identity verification for repairs
    - Network security validation
    """

    def __init__(self):
        self._threat_detector = None
        self._policy_engine = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of Zero Trust components."""
        if self._initialized:
            return

        try:
            from security.zero_trust.threat_detection import ThreatDetector
            self._threat_detector = ThreatDetector()
            logger.info("[COVI-SHIELD ZeroTrust] Threat Detector initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD ZeroTrust] Threat Detector not available: {e}")

        try:
            from security.zero_trust.policy_engine import PolicyEngine
            self._policy_engine = PolicyEngine()
            logger.info("[COVI-SHIELD ZeroTrust] Policy Engine initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD ZeroTrust] Policy Engine not available: {e}")

        self._initialized = True

    def detect_code_threats(
        self,
        code: str,
        file_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect security threats in code.

        Args:
            code: Source code to analyze
            file_path: Optional file path for context

        Returns:
            List of detected threats
        """
        self._lazy_init()

        if not self._threat_detector:
            return []

        try:
            threats = self._threat_detector.detect_threats(
                content=code,
                content_type="source_code",
                context={"file_path": file_path}
            )

            return [
                {
                    "threat_id": t.threat_id,
                    "type": t.threat_type,
                    "severity": t.severity,
                    "description": t.description,
                    "location": t.location,
                    "mitigation": t.mitigation
                }
                for t in threats
            ]

        except Exception as e:
            logger.warning(f"[COVI-SHIELD ZeroTrust] Threat detection failed: {e}")
            return []

    def validate_repair_policy(
        self,
        repair_suggestion: RepairSuggestion,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validate repair against security policies.

        Args:
            repair_suggestion: Proposed repair
            context: Repair context

        Returns:
            Tuple of (is_allowed, reason)
        """
        self._lazy_init()

        if not self._policy_engine:
            return True, "Policy engine not available"

        try:
            result = self._policy_engine.evaluate_action(
                action="code_modification",
                resource="source_code",
                context={
                    "repair_strategy": repair_suggestion.strategy.value,
                    "confidence": repair_suggestion.confidence,
                    **context
                }
            )

            return result.allowed, result.reason

        except Exception as e:
            logger.warning(f"[COVI-SHIELD ZeroTrust] Policy validation failed: {e}")
            return True, "Validation failed - default allow"


# ============================================================================
# HALLUCINATION GUARD INTEGRATION
# ============================================================================

class COVIShieldHallucinationGuardIntegration:
    """
    Integrates COVI-SHIELD with LLM Orchestrator's Hallucination Guard.

    Validates AI-generated repairs to ensure:
    - Code correctness
    - No fabricated dependencies
    - Semantic preservation
    - Logical consistency
    """

    def __init__(self):
        self._guard = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of hallucination guard."""
        if self._initialized:
            return

        try:
            from llm_orchestrator.hallucination_guard import HallucinationGuard
            self._guard = HallucinationGuard()
            logger.info("[COVI-SHIELD AIGuard] Hallucination Guard initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD AIGuard] Guard not available: {e}")

        self._initialized = True

    def validate_ai_repair(
        self,
        original_code: str,
        repaired_code: str,
        repair_rationale: str
    ) -> Dict[str, Any]:
        """
        Validate AI-generated repair for hallucinations.

        Args:
            original_code: Original source code
            repaired_code: AI-generated repair
            repair_rationale: Explanation for the repair

        Returns:
            Validation results
        """
        self._lazy_init()

        if not self._guard:
            return {"validated": True, "confidence": 0.5, "reason": "Guard not available"}

        try:
            validation = self._guard.validate_code_generation(
                original=original_code,
                generated=repaired_code,
                rationale=repair_rationale,
                validation_type="code_repair"
            )

            return {
                "validated": validation.is_valid,
                "confidence": validation.confidence,
                "issues": validation.issues,
                "fabrications_detected": validation.fabrications,
                "semantic_preserved": validation.semantic_check_passed,
                "reason": validation.summary
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD AIGuard] Validation failed: {e}")
            return {"validated": True, "confidence": 0.5, "reason": f"Validation error: {e}"}

    def check_dependency_hallucination(
        self,
        code: str,
        claimed_dependencies: List[str]
    ) -> Dict[str, Any]:
        """
        Check if claimed dependencies are real.

        Args:
            code: Code using the dependencies
            claimed_dependencies: List of claimed imports/deps

        Returns:
            Dependency validation results
        """
        self._lazy_init()

        if not self._guard:
            return {"all_valid": True, "invalid": []}

        try:
            result = self._guard.validate_dependencies(
                code=code,
                dependencies=claimed_dependencies
            )

            return {
                "all_valid": result.all_valid,
                "valid_dependencies": result.valid,
                "invalid_dependencies": result.invalid,
                "uncertain_dependencies": result.uncertain
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD AIGuard] Dependency check failed: {e}")
            return {"all_valid": True, "invalid": []}


# ============================================================================
# MEMORY MESH INTEGRATION
# ============================================================================

class COVIShieldMemoryMeshIntegration:
    """
    Integrates COVI-SHIELD with GRACE's Memory Mesh.

    Provides:
    - Distributed pattern learning
    - Cross-instance knowledge sharing
    - Historical verification memory
    - Federated learning coordination
    """

    def __init__(self):
        self._memory_mesh = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of Memory Mesh."""
        if self._initialized:
            return

        try:
            from cognitive.memory_mesh.mesh_coordinator import MemoryMeshCoordinator
            self._memory_mesh = MemoryMeshCoordinator()
            logger.info("[COVI-SHIELD Memory] Memory Mesh initialized")
        except Exception as e:
            logger.warning(f"[COVI-SHIELD Memory] Memory Mesh not available: {e}")

        self._initialized = True

    def store_verification_pattern(
        self,
        pattern_id: str,
        pattern_data: Dict[str, Any],
        effectiveness: float
    ):
        """
        Store a verification pattern in the mesh.

        Args:
            pattern_id: Unique pattern identifier
            pattern_data: Pattern details
            effectiveness: How effective this pattern is (0-1)
        """
        self._lazy_init()

        if not self._memory_mesh:
            return

        try:
            self._memory_mesh.store(
                key=f"covi_shield:pattern:{pattern_id}",
                data={
                    **pattern_data,
                    "effectiveness": effectiveness,
                    "source": "covi_shield",
                    "timestamp": datetime.utcnow().isoformat()
                },
                ttl_hours=24 * 30  # 30 days
            )

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Memory] Pattern storage failed: {e}")

    def retrieve_similar_patterns(
        self,
        code_hash: str,
        issue_type: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar patterns from the mesh.

        Args:
            code_hash: Hash of current code
            issue_type: Type of issue
            limit: Max patterns to return

        Returns:
            List of similar patterns
        """
        self._lazy_init()

        if not self._memory_mesh:
            return []

        try:
            patterns = self._memory_mesh.search(
                query={
                    "type": "covi_shield:pattern",
                    "issue_type": issue_type
                },
                limit=limit
            )

            return [
                {
                    "pattern_id": p.key.split(":")[-1],
                    "data": p.data,
                    "similarity": p.similarity,
                    "effectiveness": p.data.get("effectiveness", 0.5)
                }
                for p in patterns
            ]

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Memory] Pattern retrieval failed: {e}")
            return []

    def share_learning(
        self,
        learning_data: Dict[str, Any]
    ):
        """
        Share learning data with the mesh for federated learning.

        Args:
            learning_data: Data to share
        """
        self._lazy_init()

        if not self._memory_mesh:
            return

        try:
            self._memory_mesh.contribute_learning(
                source="covi_shield",
                data=learning_data
            )

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Memory] Learning share failed: {e}")

    def get_collective_insights(self) -> Dict[str, Any]:
        """
        Get collective insights from the mesh.

        Returns:
            Aggregated insights from all instances
        """
        self._lazy_init()

        if not self._memory_mesh:
            return {"available": False}

        try:
            insights = self._memory_mesh.get_collective_insights(
                topic="covi_shield"
            )

            return {
                "available": True,
                "total_patterns": insights.total_patterns,
                "top_effective_patterns": insights.top_patterns,
                "common_issues": insights.common_issues,
                "fix_success_rate": insights.aggregate_success_rate
            }

        except Exception as e:
            logger.warning(f"[COVI-SHIELD Memory] Insights fetch failed: {e}")
            return {"available": False}


# ============================================================================
# UNIFIED KNOWLEDGE BASE
# ============================================================================

class COVIShieldKnowledgeBase:
    """
    Unified knowledge base integrating all GRACE systems.

    Provides single interface for:
    - Trust scoring
    - KPI tracking
    - Compliance monitoring
    - Audit trails
    - Governance
    - Failure prediction
    - Diagnostics
    - Pattern mining
    - TimeSense
    - Zero Trust
    - AI validation
    - Memory Mesh
    """

    def __init__(self, session=None, knowledge_base_path: Optional[Path] = None):
        # Core integrations
        self.trust = COVIShieldTrustIntegration()
        self.kpi = COVIShieldKPIIntegration()
        self.compliance = COVIShieldComplianceIntegration()
        self.audit = COVIShieldAuditIntegration(session=session)
        self.governance = COVIShieldGovernanceIntegration(session=session)

        # Advanced integrations
        self.failure_predictor = COVIShieldFailurePredictorIntegration()
        self.diagnostic = COVIShieldDiagnosticIntegration()
        self.pattern_miner = COVIShieldPatternMinerIntegration()
        self.timesense = COVIShieldTimeSenseIntegration()
        self.zero_trust = COVIShieldZeroTrustIntegration()
        self.ai_guard = COVIShieldHallucinationGuardIntegration()
        self.memory_mesh = COVIShieldMemoryMeshIntegration()

        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")

        logger.info("[COVI-SHIELD Knowledge Base] Initialized with all GRACE integrations")

    def process_analysis_complete(
        self,
        report: AnalysisReport
    ) -> Dict[str, Any]:
        """
        Process a completed analysis through all integrations.

        Args:
            report: Completed analysis report

        Returns:
            Integration results
        """
        results = {
            "trust_score": None,
            "kpi_recorded": False,
            "compliance_recorded": False,
            "audit_recorded": False,
            "governance_assessment": None
        }

        # 1. Calculate trust score
        trust_data = self.trust.calculate_verification_trust(report.static_analysis)
        results["trust_score"] = trust_data

        # 2. Record KPIs
        try:
            self.kpi.record_analysis(report)
            results["kpi_recorded"] = True
        except Exception as e:
            logger.warning(f"KPI recording failed: {e}")

        # 3. Record compliance evidence
        try:
            if report.static_analysis:
                self.compliance.record_compliance_evidence(report, "static_analysis")
            if report.formal_verification:
                self.compliance.record_compliance_evidence(report, "formal_verification")
            if report.certificate:
                self.compliance.record_compliance_evidence(report, "certificate")
            results["compliance_recorded"] = True
        except Exception as e:
            logger.warning(f"Compliance recording failed: {e}")

        # 4. Record in audit trail
        try:
            self.audit.record_verification(report)
            if report.certificate:
                self.audit.record_certificate(report.certificate, "issued")
            results["audit_recorded"] = True
        except Exception as e:
            logger.warning(f"Audit recording failed: {e}")

        # 5. Governance assessment
        try:
            results["governance_assessment"] = self.governance.assess_verification_trust(report)
            self.governance.record_component_outcome(
                success=report.overall_risk != RiskLevel.CRITICAL,
                details={"report_id": report.report_id}
            )
        except Exception as e:
            logger.warning(f"Governance assessment failed: {e}")

        return results

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all integrations."""
        return {
            "trust": {
                "available": self.trust._initialized
            },
            "kpi": {
                "available": self.kpi._registered,
                "trust_score": self.kpi.get_trust_score(),
                "health": self.kpi.get_health_signal()
            },
            "compliance": self.compliance.get_compliance_status(),
            "governance": {
                "available": self.governance._quorum_engine is not None
            },
            "failure_predictor": {
                "available": self.failure_predictor._initialized
            },
            "diagnostic": {
                "available": self.diagnostic._initialized,
                "context": self.diagnostic.get_system_context()
            },
            "pattern_miner": {
                "available": self.pattern_miner._initialized
            },
            "timesense": {
                "available": self.timesense._initialized
            },
            "zero_trust": {
                "available": self.zero_trust._initialized
            },
            "ai_guard": {
                "available": self.ai_guard._initialized
            },
            "memory_mesh": {
                "available": self.memory_mesh._initialized,
                "insights": self.memory_mesh.get_collective_insights()
            }
        }

    def predict_failures_before_analysis(
        self,
        code: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict potential failures before running full analysis.

        Args:
            code: Code to analyze
            file_path: File path for context

        Returns:
            Failure predictions
        """
        return self.failure_predictor.predict_code_failures(code, file_path)

    def validate_repair_with_all_systems(
        self,
        original_code: str,
        repair_suggestion: RepairSuggestion,
        rationale: str = ""
    ) -> Dict[str, Any]:
        """
        Validate a repair using all available systems.

        Args:
            original_code: Original code
            repair_suggestion: Proposed repair
            rationale: Repair rationale

        Returns:
            Comprehensive validation results
        """
        results = {
            "oracle_risk": None,
            "policy_allowed": True,
            "ai_validated": True,
            "time_estimate": None,
            "overall_safe": True
        }

        # 1. Oracle risk assessment
        if repair_suggestion.repaired_code:
            results["oracle_risk"] = self.failure_predictor.assess_repair_risk(
                original_code,
                repair_suggestion.repaired_code,
                repair_suggestion.issue_id
            )
            if results["oracle_risk"].get("risk_score", 0) > 0.7:
                results["overall_safe"] = False

        # 2. Zero Trust policy check
        allowed, reason = self.zero_trust.validate_repair_policy(
            repair_suggestion,
            {"file_type": "python"}
        )
        results["policy_allowed"] = allowed
        results["policy_reason"] = reason
        if not allowed:
            results["overall_safe"] = False

        # 3. AI hallucination check
        if repair_suggestion.repaired_code:
            results["ai_validation"] = self.ai_guard.validate_ai_repair(
                original_code,
                repair_suggestion.repaired_code,
                rationale
            )
            if not results["ai_validation"].get("validated", True):
                results["overall_safe"] = False

        # 4. Time estimation
        results["time_estimate"] = self.timesense.estimate_repair_time(repair_suggestion)

        return results

    def enhance_analysis_with_patterns(
        self,
        code: str,
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Enhance analysis with pattern mining.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Additional patterns found
        """
        patterns = []

        # Mine vulnerability patterns
        mined = self.pattern_miner.mine_vulnerability_patterns(code, language)
        patterns.extend(mined)

        # Check for threats
        threats = self.zero_trust.detect_code_threats(code)
        for threat in threats:
            patterns.append({
                "pattern_id": f"THREAT-{threat.get('threat_id', 'unknown')}",
                "name": threat.get("type", "Security Threat"),
                "severity": threat.get("severity", "high"),
                "description": threat.get("description", ""),
                "source": "zero_trust"
            })

        return patterns

    def store_learning_in_mesh(
        self,
        report: AnalysisReport
    ):
        """
        Store analysis learnings in Memory Mesh.

        Args:
            report: Completed analysis report
        """
        # Store patterns found
        if report.static_analysis:
            for issue in report.static_analysis.issues:
                self.memory_mesh.store_verification_pattern(
                    pattern_id=issue.get("pattern_id", "unknown"),
                    pattern_data=issue,
                    effectiveness=1.0 if issue.get("fixed", False) else 0.5
                )

        # Share learning
        self.memory_mesh.share_learning({
            "report_id": report.report_id,
            "issues_found": report.total_issues,
            "issues_fixed": report.total_fixed,
            "risk_level": report.overall_risk.value,
            "timestamp": datetime.utcnow().isoformat()
        })


# Global instance
_knowledge_base: Optional[COVIShieldKnowledgeBase] = None


def get_covi_shield_knowledge_base(
    session=None,
    knowledge_base_path: Optional[Path] = None
) -> COVIShieldKnowledgeBase:
    """Get or create global knowledge base instance."""
    global _knowledge_base

    if _knowledge_base is None:
        _knowledge_base = COVIShieldKnowledgeBase(
            session=session,
            knowledge_base_path=knowledge_base_path
        )

    return _knowledge_base
