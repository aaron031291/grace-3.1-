"""
GRACE Compliance API

REST API endpoints for compliance management:
- Compliance status and reporting
- Evidence management
- DSAR handling
- Continuous monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


# Request/Response Models
class ControlResponse(BaseModel):
    control_id: str
    name: str
    description: str
    framework: str
    category: str
    status: Optional[str] = None
    severity: str


class ComplianceSummaryResponse(BaseModel):
    framework: str
    total_controls: int
    status_counts: dict
    compliance_percentage: float


class EvidenceRequest(BaseModel):
    control_ids: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None


class EvidenceResponse(BaseModel):
    evidence_id: str
    evidence_type: str
    control_ids: List[str]
    title: str
    description: str
    collected_at: datetime
    status: str


class DSARRequest(BaseModel):
    subject_id: str
    reason: str
    assets: Optional[List[str]] = None


class DSARResponse(BaseModel):
    request_id: str
    subject_id: str
    status: str
    requested_at: datetime
    completed_at: Optional[datetime] = None


class ViolationResponse(BaseModel):
    violation_id: str
    control_id: str
    framework: str
    severity: str
    description: str
    detected_at: datetime
    auto_remediated: bool


class AlertResponse(BaseModel):
    alert_id: str
    control_id: str
    severity: str
    title: str
    status: str
    created_at: datetime


# Endpoints
@router.get("/frameworks")
async def list_frameworks():
    """List available compliance frameworks."""
    from .frameworks import ComplianceFramework
    
    return {
        "frameworks": [
            {"id": f.value, "name": f.name}
            for f in ComplianceFramework
        ]
    }


@router.get("/controls", response_model=List[ControlResponse])
async def list_controls(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """List compliance controls."""
    from .frameworks import ComplianceFramework, ControlCategory, get_framework_mapping
    
    mapping = get_framework_mapping()
    
    fw = ComplianceFramework(framework) if framework else None
    cat = ControlCategory(category) if category else None
    
    controls = mapping.get_controls(framework=fw, category=cat)
    
    return [
        ControlResponse(
            control_id=c.control_id,
            name=c.name,
            description=c.description,
            framework=c.framework.value,
            category=c.category.value,
            status=mapping.get_assessment(c.control_id).status.value if mapping.get_assessment(c.control_id) else None,
            severity=c.severity.value,
        )
        for c in controls
    ]


@router.get("/controls/{control_id}")
async def get_control(control_id: str):
    """Get a specific control."""
    from .frameworks import get_framework_mapping
    
    mapping = get_framework_mapping()
    control = mapping.get_control(control_id)
    
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    assessment = mapping.get_assessment(control_id)
    
    return {
        "control": control.to_dict(),
        "assessment": assessment.to_dict() if assessment else None,
    }


@router.get("/summary", response_model=ComplianceSummaryResponse)
async def get_compliance_summary(
    framework: Optional[str] = Query(None, description="Filter by framework"),
):
    """Get compliance summary."""
    from .frameworks import ComplianceFramework, get_framework_mapping
    
    mapping = get_framework_mapping()
    fw = ComplianceFramework(framework) if framework else None
    
    summary = mapping.get_compliance_summary(framework=fw)
    
    return ComplianceSummaryResponse(**summary)


@router.post("/evidence/collect", response_model=EvidenceResponse)
async def collect_evidence(request: EvidenceRequest):
    """Collect evidence from audit logs."""
    from .evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    
    start_time = request.start_time or (datetime.utcnow() - timedelta(days=30))
    end_time = request.end_time or datetime.utcnow()
    
    evidence = collector.collect_from_audit(
        control_ids=request.control_ids,
        start_time=start_time,
        end_time=end_time,
        collected_by="api",
    )
    
    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        evidence_type=evidence.evidence_type.value,
        control_ids=evidence.control_ids,
        title=evidence.title,
        description=evidence.description,
        collected_at=evidence.collected_at,
        status=evidence.status.value,
    )


@router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    """Get evidence details."""
    from .evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    evidence = collector.get_evidence(evidence_id)
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return evidence.to_dict(include_content=True)


@router.get("/evidence")
async def list_evidence(
    control_id: Optional[str] = Query(None, description="Filter by control"),
):
    """List evidence."""
    from .evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    
    if control_id:
        evidence_list = collector.get_evidence_for_control(control_id)
    else:
        evidence_list = list(collector._evidence_store.values())
    
    return [e.to_dict() for e in evidence_list]


@router.post("/evidence/{evidence_id}/verify")
async def verify_evidence(evidence_id: str):
    """Verify evidence integrity."""
    from .evidence import get_evidence_collector
    
    collector = get_evidence_collector()
    success = collector.verify_evidence(evidence_id, "api")
    
    if not success:
        raise HTTPException(status_code=400, detail="Verification failed")
    
    return {"status": "verified", "evidence_id": evidence_id}


@router.post("/dsar", response_model=DSARResponse)
async def create_dsar(request: DSARRequest):
    """Create a Data Subject Access Request (DSAR)."""
    from .data_governance import get_right_to_erasure
    
    handler = get_right_to_erasure()
    erasure_request = handler.create_request(
        subject_id=request.subject_id,
        requested_by="api",
        reason=request.reason,
        assets=request.assets,
    )
    
    return DSARResponse(
        request_id=erasure_request.request_id,
        subject_id=erasure_request.subject_id,
        status=erasure_request.status,
        requested_at=erasure_request.requested_at,
    )


@router.post("/dsar/{request_id}/process")
async def process_dsar(request_id: str):
    """Process a DSAR request."""
    from .data_governance import get_right_to_erasure
    
    handler = get_right_to_erasure()
    result = handler.process_request(request_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/dsar/{request_id}")
async def get_dsar(request_id: str):
    """Get DSAR status."""
    from .data_governance import get_right_to_erasure
    
    handler = get_right_to_erasure()
    request = handler.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return request.to_dict()


@router.get("/violations", response_model=List[ViolationResponse])
async def list_violations():
    """List active compliance violations."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    violations = monitor.get_active_violations()
    
    return [
        ViolationResponse(
            violation_id=v.violation_id,
            control_id=v.control_id,
            framework=v.framework.value,
            severity=v.severity.value,
            description=v.description,
            detected_at=v.detected_at,
            auto_remediated=v.auto_remediated,
        )
        for v in violations
    ]


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List compliance alerts."""
    from .continuous_monitoring import AlertStatus, get_compliance_monitor
    
    monitor = get_compliance_monitor()
    
    if status:
        alerts = [
            a for a in monitor._alerts.values()
            if a.status == AlertStatus(status)
        ]
    else:
        alerts = monitor.get_open_alerts()
    
    return [
        AlertResponse(
            alert_id=a.alert_id,
            control_id=a.control_id,
            severity=a.severity.value,
            title=a.title,
            status=a.status.value,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    success = monitor.acknowledge_alert(alert_id, "api")
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "acknowledged", "alert_id": alert_id}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolution_notes: str = ""):
    """Resolve an alert."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    success = monitor.resolve_alert(alert_id, resolution_notes)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "resolved", "alert_id": alert_id}


@router.get("/monitoring/status")
async def get_monitoring_status():
    """Get continuous monitoring status."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    
    return {
        "running": monitor._running,
        "check_interval_seconds": monitor._check_interval.total_seconds(),
        "active_violations": len(monitor.get_active_violations()),
        "open_alerts": len(monitor.get_open_alerts()),
    }


@router.post("/monitoring/start")
async def start_monitoring():
    """Start continuous compliance monitoring."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    monitor.start()
    
    return {"status": "started"}


@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop continuous compliance monitoring."""
    from .continuous_monitoring import get_compliance_monitor
    
    monitor = get_compliance_monitor()
    monitor.stop()
    
    return {"status": "stopped"}


@router.get("/drift")
async def get_drift_report():
    """Get compliance drift report."""
    from .continuous_monitoring import get_drift_detector
    
    detector = get_drift_detector()
    drifts = detector.get_drift_report()
    
    return {"drifts": drifts}


@router.get("/data-classification")
async def classify_content(content: str = Query(..., description="Content to classify")):
    """Classify content for data sensitivity."""
    from .data_governance import get_classification_policy
    
    policy = get_classification_policy()
    result = policy.classify(content)
    
    return {
        "classification": result["classification"].value,
        "categories": [c.value for c in result["categories"]],
        "matched_rules": result["matched_rules"],
    }


@router.get("/lineage/{asset_id}")
async def get_data_lineage(asset_id: str):
    """Get data lineage for an asset."""
    from .data_governance import get_data_lineage
    
    lineage = get_data_lineage()
    result = lineage.get_lineage(asset_id)
    
    return result
