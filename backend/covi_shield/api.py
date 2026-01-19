"""
COVI-SHIELD API Endpoints

REST API for COVI-SHIELD verification, repair, and certificate management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .orchestrator import (
    get_covi_shield,
    VerificationLevel,
    WorkflowType
)
from .models import (
    VerificationRequest,
    VerificationResponse,
    RepairRequest,
    RepairResponse,
    RiskLevel
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/covi-shield", tags=["COVI-SHIELD"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request for code analysis."""
    code: str
    language: str = "python"
    file_path: Optional[str] = None
    verification_level: str = "standard"  # quick, standard, full, repair
    properties_to_verify: List[str] = []
    auto_repair: bool = True
    genesis_key_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response from code analysis."""
    success: bool
    report_id: str
    risk_level: str
    total_issues: int
    total_fixed: int
    certificate_id: Optional[str] = None
    summary: str
    analysis_time_ms: float
    details: Dict[str, Any] = {}


class QuickCheckRequest(BaseModel):
    """Request for quick check."""
    code: str
    language: str = "python"


class QuickCheckResponse(BaseModel):
    """Response from quick check."""
    success: bool
    result_id: str
    risk_level: str
    issues_found: int
    issues: List[Dict[str, Any]] = []
    analysis_time_ms: float


class CertificateVerifyRequest(BaseModel):
    """Request to verify a certificate."""
    certificate_id: str


class CertificateVerifyResponse(BaseModel):
    """Response from certificate verification."""
    valid: bool
    reason: str
    certificate: Optional[Dict[str, Any]] = None


class StatusResponse(BaseModel):
    """COVI-SHIELD status response."""
    operational: bool
    modules_active: Dict[str, bool]
    total_analyses: int
    total_bugs_detected: int
    total_bugs_fixed: int
    detection_rate: float
    correction_rate: float
    uptime_seconds: float


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest):
    """
    Perform comprehensive code analysis.

    Runs COVI-SHIELD's full analysis pipeline:
    - Static analysis for pattern detection
    - Formal verification for proofs
    - Dynamic analysis for runtime behavior
    - Auto-repair for detected issues
    - Certificate generation

    This is the same pipeline triggered on every Genesis Key.
    """
    try:
        shield = get_covi_shield()

        # Map verification level
        level_map = {
            "quick": VerificationLevel.QUICK,
            "standard": VerificationLevel.STANDARD,
            "full": VerificationLevel.FULL,
            "repair": VerificationLevel.REPAIR
        }
        level = level_map.get(request.verification_level.lower(), VerificationLevel.STANDARD)

        # Run analysis
        report = shield.analyze(
            code=request.code,
            language=request.language,
            file_path=request.file_path,
            verification_level=level,
            genesis_key_id=request.genesis_key_id,
            properties_to_verify=request.properties_to_verify if request.properties_to_verify else None,
            auto_repair=request.auto_repair
        )

        return AnalyzeResponse(
            success=report.overall_risk != RiskLevel.CRITICAL,
            report_id=report.report_id,
            risk_level=report.overall_risk.value,
            total_issues=report.total_issues,
            total_fixed=report.total_fixed,
            certificate_id=report.certificate.certificate_id if report.certificate else None,
            summary=report.summary,
            analysis_time_ms=report.analysis_duration_ms,
            details={
                "static_analysis": report.static_analysis.to_dict() if report.static_analysis else None,
                "formal_verification": report.formal_verification.to_dict() if report.formal_verification else None,
                "dynamic_analysis": report.dynamic_analysis.to_dict() if report.dynamic_analysis else None,
                "repairs": [r.to_dict() for r in report.repairs_applied],
                "certificate": report.certificate.to_dict() if report.certificate else None
            }
        )

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check", response_model=QuickCheckResponse)
async def quick_check(request: QuickCheckRequest):
    """
    Perform quick static analysis check.

    Fast analysis for real-time feedback. Only runs static analysis.
    """
    try:
        shield = get_covi_shield()

        result = shield.quick_check(
            code=request.code,
            language=request.language
        )

        return QuickCheckResponse(
            success=result.success,
            result_id=result.result_id,
            risk_level=result.risk_level.value,
            issues_found=result.issues_found,
            issues=result.issues,
            analysis_time_ms=result.analysis_time_ms
        )

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Quick check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair", response_model=RepairResponse)
async def repair_code(request: RepairRequest):
    """
    Generate repair suggestion for code.

    Analyzes code and generates fix suggestions using:
    - Template-based repair
    - Constraint-based repair
    - Pattern matching
    """
    try:
        shield = get_covi_shield()

        # Run quick check to find issues
        result = shield.quick_check(
            code=request.code,
            language=request.language
        )

        if not result.issues:
            return RepairResponse(
                success=True,
                suggestion_id="",
                repaired_code=request.code,
                confidence=1.0,
                validation_passed=True,
                message="No issues found - code is clean"
            )

        # Generate repairs
        repaired_code, suggestions = shield.repair_engine.repair_all(
            code=request.code,
            issues=result.issues,
            genesis_key_id=request.genesis_key_id
        )

        if suggestions:
            best_suggestion = suggestions[0]
            return RepairResponse(
                success=True,
                suggestion_id=best_suggestion.suggestion_id,
                repaired_code=repaired_code,
                confidence=best_suggestion.confidence,
                validation_passed=best_suggestion.validation_passed,
                message=f"Generated {len(suggestions)} repair(s)"
            )
        else:
            return RepairResponse(
                success=False,
                suggestion_id="",
                repaired_code=request.code,
                confidence=0.0,
                validation_passed=False,
                message="Could not generate repairs"
            )

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-certificate", response_model=CertificateVerifyResponse)
async def verify_certificate(request: CertificateVerifyRequest):
    """
    Verify a COVI-SHIELD certificate.

    Checks:
    - Cryptographic signature
    - Expiration
    - Revocation status
    """
    try:
        shield = get_covi_shield()

        is_valid, reason = shield.verify_certificate(request.certificate_id)

        cert = shield.certificate_authority.get_certificate(request.certificate_id)

        return CertificateVerifyResponse(
            valid=is_valid,
            reason=reason,
            certificate=cert.to_dict() if cert else None
        )

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Certificate verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certificate/{certificate_id}")
async def get_certificate(certificate_id: str):
    """Get certificate details and audit report."""
    try:
        shield = get_covi_shield()

        audit = shield.certificate_authority.audit_certificate(certificate_id)

        if "error" in audit:
            raise HTTPException(status_code=404, detail=audit["error"])

        return audit

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Get certificate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get COVI-SHIELD system status.

    Returns operational status and statistics.
    """
    try:
        shield = get_covi_shield()
        status = shield.get_status()

        return StatusResponse(
            operational=status.operational,
            modules_active=status.modules_active,
            total_analyses=status.total_analyses,
            total_bugs_detected=status.total_bugs_detected,
            total_bugs_fixed=status.total_bugs_fixed,
            detection_rate=status.detection_rate,
            correction_rate=status.correction_rate,
            uptime_seconds=status.uptime_seconds
        )

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get detailed statistics from all COVI-SHIELD modules."""
    try:
        shield = get_covi_shield()
        return shield.get_module_stats()

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/cycle")
async def run_learning_cycle():
    """
    Run a learning cycle.

    Analyzes recent verification and repair outcomes to:
    - Update pattern effectiveness
    - Discover new patterns
    - Improve repair strategies
    """
    try:
        shield = get_covi_shield()
        result = shield.run_learning_cycle()

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Learning cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge")
async def export_knowledge():
    """Export learned knowledge for backup or transfer."""
    try:
        shield = get_covi_shield()
        return shield.learning_module.export_knowledge()

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Knowledge export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_patterns():
    """Get all bug patterns in the database."""
    try:
        shield = get_covi_shield()

        patterns = [p.to_dict() for p in shield.static_analyzer.patterns]

        return {
            "total_patterns": len(patterns),
            "patterns": patterns
        }

    except Exception as e:
        logger.error(f"[COVI-SHIELD API] Pattern retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        shield = get_covi_shield()
        status = shield.get_status()

        return {
            "status": "healthy" if status.operational else "unhealthy",
            "operational": status.operational,
            "modules_active": status.modules_active
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
