"""
GRACE Compliance Frameworks

Defines compliance frameworks and control mappings for:
- SOC 2 Type II
- HIPAA Security Rules
- GDPR Requirements
- ISO 27001 Controls
- FedRAMP Controls
- PCI-DSS Requirements
- NIST Cybersecurity Framework

Enables automated compliance checking and evidence collection.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    SOC2 = "soc2"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    ISO27001 = "iso27001"
    FEDRAMP = "fedramp"
    PCI_DSS = "pci_dss"
    NIST_CSF = "nist_csf"
    CUSTOM = "custom"


class ControlCategory(str, Enum):
    """Categories of compliance controls."""
    ACCESS_CONTROL = "access_control"
    AUDIT_LOGGING = "audit_logging"
    DATA_PROTECTION = "data_protection"
    ENCRYPTION = "encryption"
    INCIDENT_RESPONSE = "incident_response"
    SECURITY_AWARENESS = "security_awareness"
    CHANGE_MANAGEMENT = "change_management"
    VULNERABILITY_MANAGEMENT = "vulnerability_management"
    NETWORK_SECURITY = "network_security"
    PHYSICAL_SECURITY = "physical_security"
    BUSINESS_CONTINUITY = "business_continuity"
    RISK_MANAGEMENT = "risk_management"
    PRIVACY = "privacy"
    GOVERNANCE = "governance"


class ControlStatus(str, Enum):
    """Status of a compliance control."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    NOT_ASSESSED = "not_assessed"
    IN_REMEDIATION = "in_remediation"


class ControlSeverity(str, Enum):
    """Severity if control is not met."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Control:
    """A compliance control."""
    control_id: str
    name: str
    description: str
    framework: ComplianceFramework
    category: ControlCategory
    requirements: List[str]
    evidence_types: List[str] = field(default_factory=list)
    severity: ControlSeverity = ControlSeverity.MEDIUM
    automated_check: bool = False
    check_function: Optional[str] = None  # Function name for automated check
    remediation_steps: List[str] = field(default_factory=list)
    related_controls: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "description": self.description,
            "framework": self.framework.value,
            "category": self.category.value,
            "requirements": self.requirements,
            "evidence_types": self.evidence_types,
            "severity": self.severity.value,
            "automated_check": self.automated_check,
        }


@dataclass
class ControlAssessment:
    """Assessment result for a control."""
    control_id: str
    status: ControlStatus
    assessed_at: datetime
    assessed_by: str
    evidence_ids: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    notes: str = ""
    next_review: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "status": self.status.value,
            "assessed_at": self.assessed_at.isoformat(),
            "assessed_by": self.assessed_by,
            "evidence_ids": self.evidence_ids,
            "findings": self.findings,
            "notes": self.notes,
        }


class FrameworkMapping:
    """
    Maps controls across compliance frameworks.
    
    Provides:
    - Control definitions per framework
    - Cross-framework control mapping
    - Automated check registration
    """
    
    def __init__(self):
        self._controls: Dict[str, Control] = {}
        self._assessments: Dict[str, ControlAssessment] = {}
        self._audit_event_mappings: Dict[str, List[str]] = {}
        
        self._initialize_soc2_controls()
        self._initialize_hipaa_controls()
        self._initialize_gdpr_controls()
        self._initialize_iso27001_controls()
        
        logger.info(f"[COMPLIANCE] Loaded {len(self._controls)} controls")
    
    def _initialize_soc2_controls(self):
        """Define SOC 2 controls."""
        controls = [
            Control(
                control_id="SOC2-CC6.1",
                name="Logical Access Security",
                description="Logical access security software, infrastructure, and architectures have been implemented",
                framework=ComplianceFramework.SOC2,
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Implement role-based access control",
                    "Enforce authentication for all users",
                    "Implement least privilege principle",
                ],
                evidence_types=["access_logs", "rbac_configuration", "user_reviews"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_rbac_enabled",
            ),
            Control(
                control_id="SOC2-CC6.2",
                name="User Registration and Authorization",
                description="Prior to issuing system credentials, the entity registers authorized users",
                framework=ComplianceFramework.SOC2,
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Formal user registration process",
                    "Authorization before access granted",
                    "Unique user identification",
                ],
                evidence_types=["user_creation_logs", "approval_records"],
                severity=ControlSeverity.HIGH,
            ),
            Control(
                control_id="SOC2-CC7.1",
                name="Detection and Monitoring",
                description="The entity implements detection activities to identify vulnerabilities and anomalies",
                framework=ComplianceFramework.SOC2,
                category=ControlCategory.AUDIT_LOGGING,
                requirements=[
                    "Implement security event logging",
                    "Monitor for unauthorized access",
                    "Detect anomalous behavior",
                ],
                evidence_types=["security_logs", "alert_records", "monitoring_dashboards"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_audit_logging",
            ),
            Control(
                control_id="SOC2-CC8.1",
                name="Change Management",
                description="The entity authorizes, designs, develops, configures, documents, tests, approves, and implements changes",
                framework=ComplianceFramework.SOC2,
                category=ControlCategory.CHANGE_MANAGEMENT,
                requirements=[
                    "Formal change approval process",
                    "Testing before production deployment",
                    "Rollback procedures documented",
                ],
                evidence_types=["change_records", "approval_tickets", "deployment_logs"],
                severity=ControlSeverity.HIGH,
                automated_check=True,
                check_function="check_change_management",
            ),
            Control(
                control_id="SOC2-A1.1",
                name="Data Availability",
                description="The entity maintains availability of information as committed",
                framework=ComplianceFramework.SOC2,
                category=ControlCategory.BUSINESS_CONTINUITY,
                requirements=[
                    "Backup procedures implemented",
                    "Disaster recovery plan",
                    "Availability monitoring",
                ],
                evidence_types=["backup_logs", "dr_test_records", "uptime_reports"],
                severity=ControlSeverity.HIGH,
            ),
        ]
        
        for control in controls:
            self._controls[control.control_id] = control
    
    def _initialize_hipaa_controls(self):
        """Define HIPAA security controls."""
        controls = [
            Control(
                control_id="HIPAA-164.312(a)(1)",
                name="Access Control",
                description="Implement technical policies to allow access only to authorized persons",
                framework=ComplianceFramework.HIPAA,
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Unique user identification",
                    "Emergency access procedure",
                    "Automatic logoff",
                    "Encryption and decryption",
                ],
                evidence_types=["access_policies", "user_lists", "encryption_configs"],
                severity=ControlSeverity.CRITICAL,
            ),
            Control(
                control_id="HIPAA-164.312(b)",
                name="Audit Controls",
                description="Implement mechanisms to record and examine activity in systems containing PHI",
                framework=ComplianceFramework.HIPAA,
                category=ControlCategory.AUDIT_LOGGING,
                requirements=[
                    "Record all access to PHI",
                    "Implement audit log review",
                    "Protect audit logs from modification",
                ],
                evidence_types=["audit_logs", "review_records", "log_protection"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_phi_audit_logging",
            ),
            Control(
                control_id="HIPAA-164.312(c)(1)",
                name="Integrity Controls",
                description="Implement policies to protect PHI from improper alteration or destruction",
                framework=ComplianceFramework.HIPAA,
                category=ControlCategory.DATA_PROTECTION,
                requirements=[
                    "Mechanism to authenticate PHI",
                    "Detect unauthorized changes",
                    "Maintain data integrity",
                ],
                evidence_types=["integrity_checks", "hash_logs", "validation_records"],
                severity=ControlSeverity.CRITICAL,
            ),
            Control(
                control_id="HIPAA-164.312(d)",
                name="Person or Entity Authentication",
                description="Implement procedures to verify persons seeking access to PHI",
                framework=ComplianceFramework.HIPAA,
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Strong authentication mechanisms",
                    "Multi-factor authentication for PHI access",
                    "Session management",
                ],
                evidence_types=["auth_logs", "mfa_configs", "session_policies"],
                severity=ControlSeverity.CRITICAL,
            ),
            Control(
                control_id="HIPAA-164.312(e)(1)",
                name="Transmission Security",
                description="Implement measures to guard against unauthorized access to PHI being transmitted",
                framework=ComplianceFramework.HIPAA,
                category=ControlCategory.ENCRYPTION,
                requirements=[
                    "Encryption in transit",
                    "Integrity controls for transmission",
                    "Secure communication channels",
                ],
                evidence_types=["tls_configs", "encryption_policies", "network_diagrams"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_encryption_in_transit",
            ),
        ]
        
        for control in controls:
            self._controls[control.control_id] = control
    
    def _initialize_gdpr_controls(self):
        """Define GDPR controls."""
        controls = [
            Control(
                control_id="GDPR-Art5",
                name="Data Processing Principles",
                description="Personal data must be processed lawfully, fairly, and transparently",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.PRIVACY,
                requirements=[
                    "Document lawful basis for processing",
                    "Implement purpose limitation",
                    "Data minimization",
                    "Accuracy maintenance",
                ],
                evidence_types=["processing_records", "purpose_documentation", "data_inventories"],
                severity=ControlSeverity.CRITICAL,
            ),
            Control(
                control_id="GDPR-Art15",
                name="Right of Access",
                description="Data subjects have the right to obtain confirmation and access to their data",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.PRIVACY,
                requirements=[
                    "Mechanism to fulfill access requests",
                    "Respond within 30 days",
                    "Provide data in portable format",
                ],
                evidence_types=["dsar_logs", "response_records", "data_exports"],
                severity=ControlSeverity.HIGH,
                automated_check=True,
                check_function="check_dsar_capability",
            ),
            Control(
                control_id="GDPR-Art17",
                name="Right to Erasure",
                description="Data subjects have the right to have their personal data erased",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.PRIVACY,
                requirements=[
                    "Mechanism to delete personal data",
                    "Delete from all systems including backups",
                    "Maintain deletion audit trail",
                ],
                evidence_types=["deletion_logs", "erasure_confirmations"],
                severity=ControlSeverity.HIGH,
                automated_check=True,
                check_function="check_erasure_capability",
            ),
            Control(
                control_id="GDPR-Art25",
                name="Data Protection by Design",
                description="Implement data protection measures into processing activities",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.PRIVACY,
                requirements=[
                    "Privacy by default",
                    "Data minimization by design",
                    "Security measures integrated",
                ],
                evidence_types=["design_reviews", "privacy_assessments", "architecture_docs"],
                severity=ControlSeverity.MEDIUM,
            ),
            Control(
                control_id="GDPR-Art32",
                name="Security of Processing",
                description="Implement appropriate technical and organizational security measures",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.DATA_PROTECTION,
                requirements=[
                    "Encryption of personal data",
                    "Ability to restore availability",
                    "Regular security testing",
                ],
                evidence_types=["security_configs", "penetration_tests", "encryption_proof"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_data_encryption",
            ),
            Control(
                control_id="GDPR-Art33",
                name="Data Breach Notification",
                description="Notify supervisory authority within 72 hours of breach awareness",
                framework=ComplianceFramework.GDPR,
                category=ControlCategory.INCIDENT_RESPONSE,
                requirements=[
                    "Breach detection capability",
                    "Notification procedures",
                    "Breach documentation",
                ],
                evidence_types=["breach_procedures", "notification_records", "incident_logs"],
                severity=ControlSeverity.CRITICAL,
            ),
        ]
        
        for control in controls:
            self._controls[control.control_id] = control
    
    def _initialize_iso27001_controls(self):
        """Define ISO 27001 controls."""
        controls = [
            Control(
                control_id="ISO27001-A.9.2.1",
                name="User Registration and De-registration",
                description="Formal user registration and de-registration process for access rights",
                framework=ComplianceFramework.ISO27001,
                category=ControlCategory.ACCESS_CONTROL,
                requirements=[
                    "Formal registration process",
                    "Unique user IDs",
                    "Timely de-registration",
                ],
                evidence_types=["user_lifecycle_logs", "registration_records"],
                severity=ControlSeverity.HIGH,
            ),
            Control(
                control_id="ISO27001-A.12.4.1",
                name="Event Logging",
                description="Event logs recording user activities and security events",
                framework=ComplianceFramework.ISO27001,
                category=ControlCategory.AUDIT_LOGGING,
                requirements=[
                    "Log user activities",
                    "Log security events",
                    "Log administrative activities",
                    "Protect logs from tampering",
                ],
                evidence_types=["event_logs", "log_protection_configs"],
                severity=ControlSeverity.CRITICAL,
                automated_check=True,
                check_function="check_event_logging",
            ),
            Control(
                control_id="ISO27001-A.10.1.1",
                name="Cryptographic Controls",
                description="Policy on the use of cryptographic controls for information protection",
                framework=ComplianceFramework.ISO27001,
                category=ControlCategory.ENCRYPTION,
                requirements=[
                    "Encryption policy defined",
                    "Key management procedures",
                    "Appropriate algorithms used",
                ],
                evidence_types=["crypto_policy", "key_management_docs", "algorithm_inventory"],
                severity=ControlSeverity.HIGH,
                automated_check=True,
                check_function="check_encryption_policy",
            ),
        ]
        
        for control in controls:
            self._controls[control.control_id] = control
    
    def get_controls(
        self,
        framework: Optional[ComplianceFramework] = None,
        category: Optional[ControlCategory] = None,
    ) -> List[Control]:
        """Get controls filtered by framework and/or category."""
        controls = list(self._controls.values())
        
        if framework:
            controls = [c for c in controls if c.framework == framework]
        
        if category:
            controls = [c for c in controls if c.category == category]
        
        return controls
    
    def get_control(self, control_id: str) -> Optional[Control]:
        """Get a specific control by ID."""
        return self._controls.get(control_id)
    
    def add_control(self, control: Control):
        """Add a custom control."""
        self._controls[control.control_id] = control
    
    def get_assessment(self, control_id: str) -> Optional[ControlAssessment]:
        """Get the latest assessment for a control."""
        return self._assessments.get(control_id)
    
    def record_assessment(self, assessment: ControlAssessment):
        """Record a control assessment."""
        self._assessments[assessment.control_id] = assessment
    
    def get_audit_event_mappings(self, control_id: str) -> List[str]:
        """Get audit event types that provide evidence for a control."""
        return self._audit_event_mappings.get(control_id, [])
    
    def map_audit_events(self):
        """Map audit event types to controls."""
        self._audit_event_mappings = {
            "SOC2-CC6.1": ["USER_LOGIN", "USER_LOGOUT", "PERMISSION_CHANGE", "ROLE_ASSIGNMENT"],
            "SOC2-CC7.1": ["SECURITY_ALERT", "ANOMALY_DETECTED", "AUDIT_LOG_ACCESS"],
            "SOC2-CC8.1": ["CODE_CHANGE", "DEPLOYMENT", "ROLLBACK"],
            "HIPAA-164.312(b)": ["DATA_ACCESS", "PHI_ACCESS", "AUDIT_LOG_ACCESS"],
            "GDPR-Art15": ["DSAR_REQUEST", "DATA_EXPORT"],
            "GDPR-Art17": ["DATA_DELETION", "ERASURE_REQUEST"],
            "ISO27001-A.12.4.1": ["ALL"],  # All audit events
        }
    
    def get_compliance_summary(
        self,
        framework: Optional[ComplianceFramework] = None,
    ) -> Dict[str, Any]:
        """Get compliance summary statistics."""
        controls = self.get_controls(framework)
        
        status_counts = {status.value: 0 for status in ControlStatus}
        
        for control in controls:
            assessment = self._assessments.get(control.control_id)
            if assessment:
                status_counts[assessment.status.value] += 1
            else:
                status_counts[ControlStatus.NOT_ASSESSED.value] += 1
        
        total = len(controls)
        compliant = status_counts[ControlStatus.COMPLIANT.value]
        
        return {
            "framework": framework.value if framework else "all",
            "total_controls": total,
            "status_counts": status_counts,
            "compliance_percentage": (compliant / total * 100) if total > 0 else 0,
        }


# Singleton
_framework_mapping: Optional[FrameworkMapping] = None


def get_framework_mapping() -> FrameworkMapping:
    """Get the framework mapping singleton."""
    global _framework_mapping
    if _framework_mapping is None:
        _framework_mapping = FrameworkMapping()
    return _framework_mapping
