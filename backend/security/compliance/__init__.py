"""
GRACE Compliance and Audit System for High-Stakes Environments.

This module provides comprehensive compliance management for:
- SOC 2 Type II
- HIPAA
- GDPR
- ISO 27001
- FedRAMP
- PCI-DSS
- Custom frameworks

All compliance activities are audited through the immutable audit system.
"""

from security.compliance.frameworks import (
    ComplianceFramework,
    FrameworkType,
    Control,
    ControlStatus,
    ControlEvidence,
    SOC2Controls,
    HIPAAControls,
    GDPRControls,
    ISO27001Controls,
    FedRAMPControls,
    PCIDSSControls,
    ComplianceFrameworkRegistry,
    get_framework_registry,
)

from security.compliance.evidence import (
    EvidenceCollector,
    EvidencePackage,
    EvidenceRetentionPolicy,
    ChainOfCustody,
    TamperEvidentStorage,
    get_evidence_collector,
)

from security.compliance.reporting import (
    ComplianceReporter,
    ComplianceDashboard,
    GapAnalysis,
    RemediationTracker,
    ControlEffectivenessScore,
    get_compliance_reporter,
)

from security.compliance.data_governance import (
    DataClassification,
    DataClassificationLevel,
    DataLineageTracker,
    DataRetentionPolicy,
    RightToErasure,
    DataAccessGovernance,
    get_data_governance,
)

from security.compliance.privacy import (
    PIIDetector,
    PIIType,
    ConsentManager,
    DSARHandler,
    PrivacyImpactAssessment,
    CrossBorderTransferControl,
    get_privacy_controller,
)

from security.compliance.continuous_monitoring import (
    ComplianceMonitor,
    ViolationDetector,
    ComplianceDriftDetector,
    ComplianceSelfHealer,
    AlertManager,
    get_compliance_monitor,
)

__all__ = [
    # Frameworks
    "ComplianceFramework",
    "FrameworkType",
    "Control",
    "ControlStatus",
    "ControlEvidence",
    "SOC2Controls",
    "HIPAAControls",
    "GDPRControls",
    "ISO27001Controls",
    "FedRAMPControls",
    "PCIDSSControls",
    "ComplianceFrameworkRegistry",
    "get_framework_registry",
    # Evidence
    "EvidenceCollector",
    "EvidencePackage",
    "EvidenceRetentionPolicy",
    "ChainOfCustody",
    "TamperEvidentStorage",
    "get_evidence_collector",
    # Reporting
    "ComplianceReporter",
    "ComplianceDashboard",
    "GapAnalysis",
    "RemediationTracker",
    "ControlEffectivenessScore",
    "get_compliance_reporter",
    # Data Governance
    "DataClassification",
    "DataClassificationLevel",
    "DataLineageTracker",
    "DataRetentionPolicy",
    "RightToErasure",
    "DataAccessGovernance",
    "get_data_governance",
    # Privacy
    "PIIDetector",
    "PIIType",
    "ConsentManager",
    "DSARHandler",
    "PrivacyImpactAssessment",
    "CrossBorderTransferControl",
    "get_privacy_controller",
    # Continuous Monitoring
    "ComplianceMonitor",
    "ViolationDetector",
    "ComplianceDriftDetector",
    "ComplianceSelfHealer",
    "AlertManager",
    "get_compliance_monitor",
]
