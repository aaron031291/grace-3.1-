"""
COVI-SHIELD: Continuous Verification and Intelligent Self-Healing Integration for Error-Less Development

An autonomous verification, debugging, and correction system that prevents AI system failures through:
- Preemptive detection of potential failures
- Automatic correction of bugs and vulnerabilities
- Continuous verification of system properties
- Self-improvement from every analyzed project

Philosophy: "Don't debug failures; prevent them. Don't fix bugs; prove their absence."

Integration: Triggered on every Genesis Key creation for comprehensive system protection.
"""

from .orchestrator import (
    COVIShieldOrchestrator,
    get_covi_shield,
    VerificationLevel,
    WorkflowType
)
from .models import (
    VerificationResult,
    VerificationCertificate,
    BugPattern,
    RepairSuggestion,
    ShieldStatus,
    AnalysisReport,
    RiskLevel,
    CertificateStatus
)
from .static_analyzer import StaticAnalyzer
from .formal_verifier import FormalVerifier
from .dynamic_analyzer import DynamicAnalyzer
from .repair_engine import RepairEngine
from .learning_module import LearningModule
from .certificate_authority import CertificateAuthority
from .genesis_integration import COVIShieldGenesisIntegration
from .cicd_integration import (
    COVIShieldCICDIntegration,
    get_covi_shield_cicd_integration,
    create_covi_shield_pipeline_hook,
    covi_shield_verified,
    PipelineGateDecision,
    PipelineVerificationResult
)
from .knowledge_base import (
    COVIShieldKnowledgeBase,
    get_covi_shield_knowledge_base,
    COVIShieldTrustIntegration,
    COVIShieldKPIIntegration,
    COVIShieldComplianceIntegration,
    COVIShieldAuditIntegration,
    COVIShieldGovernanceIntegration,
    COVIShieldFailurePredictorIntegration,
    COVIShieldDiagnosticIntegration,
    COVIShieldPatternMinerIntegration,
    COVIShieldTimeSenseIntegration,
    COVIShieldZeroTrustIntegration,
    COVIShieldHallucinationGuardIntegration,
    COVIShieldMemoryMeshIntegration
)

__version__ = "1.0.0"
__all__ = [
    # Core
    "COVIShieldOrchestrator",
    "get_covi_shield",
    "VerificationLevel",
    "WorkflowType",
    # Models
    "VerificationResult",
    "VerificationCertificate",
    "BugPattern",
    "RepairSuggestion",
    "ShieldStatus",
    "AnalysisReport",
    "RiskLevel",
    "CertificateStatus",
    # Engines
    "StaticAnalyzer",
    "FormalVerifier",
    "DynamicAnalyzer",
    "RepairEngine",
    "LearningModule",
    "CertificateAuthority",
    # Genesis Integration
    "COVIShieldGenesisIntegration",
    # CI/CD Integration
    "COVIShieldCICDIntegration",
    "get_covi_shield_cicd_integration",
    "create_covi_shield_pipeline_hook",
    "covi_shield_verified",
    "PipelineGateDecision",
    "PipelineVerificationResult",
    # Knowledge Base
    "COVIShieldKnowledgeBase",
    "get_covi_shield_knowledge_base",
    "COVIShieldTrustIntegration",
    "COVIShieldKPIIntegration",
    "COVIShieldComplianceIntegration",
    "COVIShieldAuditIntegration",
    "COVIShieldGovernanceIntegration",
    "COVIShieldFailurePredictorIntegration",
    "COVIShieldDiagnosticIntegration",
    "COVIShieldPatternMinerIntegration",
    "COVIShieldTimeSenseIntegration",
    "COVIShieldZeroTrustIntegration",
    "COVIShieldHallucinationGuardIntegration",
    "COVIShieldMemoryMeshIntegration"
]
