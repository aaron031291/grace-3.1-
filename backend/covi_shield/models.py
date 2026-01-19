"""
COVI-SHIELD Data Models

Defines all data structures for verification, analysis, and repair operations.
"""

import uuid
import hashlib
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create a simple BaseModel fallback
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)


# ============================================================================
# ENUMS
# ============================================================================

class RiskLevel(str, Enum):
    """Risk severity levels for detected issues."""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"          # Should be fixed before deployment
    MEDIUM = "medium"      # Should be addressed soon
    LOW = "low"            # Minor issue, can be deferred
    INFO = "info"          # Informational only


class CertificateStatus(str, Enum):
    """Status of verification certificates."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class AnalysisPhase(str, Enum):
    """Analysis phases in the verification pipeline."""
    PRE_FLIGHT = "pre_flight"    # Before execution
    IN_FLIGHT = "in_flight"      # During execution
    POST_FLIGHT = "post_flight"  # After execution


class BugCategory(str, Enum):
    """Categories of detected bugs."""
    SYNTAX = "syntax"
    TYPE = "type"
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    API = "api"
    NUMERICAL = "numerical"
    RESOURCE = "resource"


class RepairStrategy(str, Enum):
    """Strategies for automatic repair."""
    TEMPLATE = "template"        # Template-based repair
    SYNTHESIS = "synthesis"      # Program synthesis
    NEURAL = "neural"            # Neural code generation
    CONSTRAINT = "constraint"    # Constraint-based repair
    SEARCH = "search"            # Search-based repair


class ProofType(str, Enum):
    """Types of formal proofs."""
    TYPE_SAFETY = "type_safety"
    MEMORY_SAFETY = "memory_safety"
    EXCEPTION_SAFETY = "exception_safety"
    TERMINATION = "termination"
    INVARIANT = "invariant"
    PRECONDITION = "precondition"
    POSTCONDITION = "postcondition"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class BugPattern:
    """Represents a known bug pattern for detection."""
    pattern_id: str
    name: str
    description: str
    category: BugCategory
    severity: RiskLevel
    detection_logic: str  # AST pattern or regex
    repair_templates: List[str] = field(default_factory=list)
    effectiveness: float = 0.0  # 0.0 to 1.0
    occurrences: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "detection_logic": self.detection_logic,
            "repair_templates": self.repair_templates,
            "effectiveness": self.effectiveness,
            "occurrences": self.occurrences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class VerificationResult:
    """Result of a verification operation."""
    result_id: str = field(default_factory=lambda: f"VR-{uuid.uuid4().hex[:16]}")
    genesis_key_id: Optional[str] = None
    phase: AnalysisPhase = AnalysisPhase.PRE_FLIGHT
    success: bool = True
    risk_level: RiskLevel = RiskLevel.INFO
    issues_found: int = 0
    issues_fixed: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    proofs: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    analysis_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "genesis_key_id": self.genesis_key_id,
            "phase": self.phase.value,
            "success": self.success,
            "risk_level": self.risk_level.value,
            "issues_found": self.issues_found,
            "issues_fixed": self.issues_fixed,
            "issues": self.issues,
            "proofs": self.proofs,
            "metrics": self.metrics,
            "analysis_time_ms": self.analysis_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class VerificationCertificate:
    """Formal certificate proving system properties."""
    certificate_id: str = field(default_factory=lambda: f"CERT-{uuid.uuid4().hex[:12]}")
    genesis_key_id: Optional[str] = None
    status: CertificateStatus = CertificateStatus.PENDING
    properties_verified: List[str] = field(default_factory=list)
    proof_type: ProofType = ProofType.TYPE_SAFETY
    proof_data: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    witness: Optional[str] = None
    signature: Optional[str] = None
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def sign(self, secret_key: str) -> None:
        """Sign the certificate with a secret key."""
        data = f"{self.certificate_id}:{self.genesis_key_id}:{','.join(self.properties_verified)}"
        self.signature = hashlib.sha256(f"{data}:{secret_key}".encode()).hexdigest()

    def verify_signature(self, secret_key: str) -> bool:
        """Verify the certificate signature."""
        if not self.signature:
            return False
        data = f"{self.certificate_id}:{self.genesis_key_id}:{','.join(self.properties_verified)}"
        expected = hashlib.sha256(f"{data}:{secret_key}".encode()).hexdigest()
        return self.signature == expected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "genesis_key_id": self.genesis_key_id,
            "status": self.status.value,
            "properties_verified": self.properties_verified,
            "proof_type": self.proof_type.value,
            "proof_data": self.proof_data,
            "assumptions": self.assumptions,
            "witness": self.witness,
            "signature": self.signature,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class RepairSuggestion:
    """Suggestion for automatic code repair."""
    suggestion_id: str = field(default_factory=lambda: f"RS-{uuid.uuid4().hex[:12]}")
    genesis_key_id: Optional[str] = None
    issue_id: str = ""
    strategy: RepairStrategy = RepairStrategy.TEMPLATE
    title: str = ""
    description: str = ""
    original_code: str = ""
    repaired_code: str = ""
    diff: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    validation_passed: bool = False
    tests_passed: bool = False
    alternative_repairs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "genesis_key_id": self.genesis_key_id,
            "issue_id": self.issue_id,
            "strategy": self.strategy.value,
            "title": self.title,
            "description": self.description,
            "original_code": self.original_code,
            "repaired_code": self.repaired_code,
            "diff": self.diff,
            "confidence": self.confidence,
            "validation_passed": self.validation_passed,
            "tests_passed": self.tests_passed,
            "alternative_repairs": self.alternative_repairs,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AnalysisReport:
    """Comprehensive analysis report."""
    report_id: str = field(default_factory=lambda: f"AR-{uuid.uuid4().hex[:12]}")
    genesis_key_id: Optional[str] = None
    title: str = ""
    summary: str = ""
    phase: AnalysisPhase = AnalysisPhase.PRE_FLIGHT

    # Static analysis
    static_analysis: Optional[VerificationResult] = None

    # Formal verification
    formal_verification: Optional[VerificationResult] = None

    # Dynamic analysis
    dynamic_analysis: Optional[VerificationResult] = None

    # Repairs
    repairs_suggested: List[RepairSuggestion] = field(default_factory=list)
    repairs_applied: List[RepairSuggestion] = field(default_factory=list)

    # Certificate
    certificate: Optional[VerificationCertificate] = None

    # Overall
    overall_risk: RiskLevel = RiskLevel.INFO
    total_issues: int = 0
    total_fixed: int = 0
    analysis_duration_ms: float = 0.0

    # Metrics and GRACE integration
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "genesis_key_id": self.genesis_key_id,
            "title": self.title,
            "summary": self.summary,
            "phase": self.phase.value,
            "static_analysis": self.static_analysis.to_dict() if self.static_analysis else None,
            "formal_verification": self.formal_verification.to_dict() if self.formal_verification else None,
            "dynamic_analysis": self.dynamic_analysis.to_dict() if self.dynamic_analysis else None,
            "repairs_suggested": [r.to_dict() for r in self.repairs_suggested],
            "repairs_applied": [r.to_dict() for r in self.repairs_applied],
            "certificate": self.certificate.to_dict() if self.certificate else None,
            "overall_risk": self.overall_risk.value,
            "total_issues": self.total_issues,
            "total_fixed": self.total_fixed,
            "analysis_duration_ms": self.analysis_duration_ms,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ShieldStatus:
    """Overall COVI-SHIELD system status."""
    operational: bool = True
    modules_active: Dict[str, bool] = field(default_factory=dict)
    total_analyses: int = 0
    total_bugs_detected: int = 0
    total_bugs_fixed: int = 0
    total_certificates_issued: int = 0
    false_positive_rate: float = 0.0
    detection_rate: float = 0.0
    correction_rate: float = 0.0
    learning_improvement: float = 0.0
    uptime_seconds: float = 0.0
    last_analysis: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operational": self.operational,
            "modules_active": self.modules_active,
            "total_analyses": self.total_analyses,
            "total_bugs_detected": self.total_bugs_detected,
            "total_bugs_fixed": self.total_bugs_fixed,
            "total_certificates_issued": self.total_certificates_issued,
            "false_positive_rate": self.false_positive_rate,
            "detection_rate": self.detection_rate,
            "correction_rate": self.correction_rate,
            "learning_improvement": self.learning_improvement,
            "uptime_seconds": self.uptime_seconds,
            "last_analysis": self.last_analysis.isoformat() if self.last_analysis else None
        }


# ============================================================================
# PYDANTIC MODELS FOR API
# ============================================================================

class VerificationRequest(BaseModel):
    """API request for verification."""
    code: str
    language: str = "python"
    file_path: Optional[str] = None
    verification_level: str = "standard"
    properties_to_verify: List[str] = []
    auto_repair: bool = True
    genesis_key_id: Optional[str] = None


class VerificationResponse(BaseModel):
    """API response for verification."""
    success: bool
    result_id: str
    risk_level: str
    issues_found: int
    issues_fixed: int
    certificate_id: Optional[str] = None
    report: Dict[str, Any] = {}
    message: str = ""


class RepairRequest(BaseModel):
    """API request for repair."""
    code: str
    issue_type: str
    language: str = "python"
    strategy: str = "template"
    genesis_key_id: Optional[str] = None


class RepairResponse(BaseModel):
    """API response for repair."""
    success: bool
    suggestion_id: str
    repaired_code: str
    confidence: float
    validation_passed: bool
    message: str = ""
