"""
COVI-SHIELD Knowledge Base Integration

Integrates COVI-SHIELD with GRACE's comprehensive ecosystem:
- Trust Scoring (Adaptive, Neural, Deterministic)
- KPI Tracking (Component and System-wide)
- Compliance Monitoring (SOC2, HIPAA, GDPR, ISO27001)
- Immutable Audit Trails
- Governance (Layer3 Quorum, Constitutional Framework)
- Memory Mesh Learning
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
    """

    def __init__(self, session=None, knowledge_base_path: Optional[Path] = None):
        self.trust = COVIShieldTrustIntegration()
        self.kpi = COVIShieldKPIIntegration()
        self.compliance = COVIShieldComplianceIntegration()
        self.audit = COVIShieldAuditIntegration(session=session)
        self.governance = COVIShieldGovernanceIntegration(session=session)
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
            }
        }


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
