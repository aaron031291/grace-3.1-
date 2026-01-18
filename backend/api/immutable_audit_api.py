"""
Immutable Audit API - Access to immutable audit records for compliance and traceability.

This API provides read-only access to the immutable audit trail.
All audit records are cryptographically linked and cannot be modified.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from genesis.immutable_audit_storage import (
    ImmutableAuditStorage,
    ImmutableAuditType,
    ImmutableAuditRecord,
    get_immutable_audit_storage
)

router = APIRouter(prefix="/immutable-audit", tags=["immutable-audit"])


class AuditRecordResponse(BaseModel):
    """Response model for an audit record."""
    record_id: str
    record_hash: str
    previous_hash: Optional[str]
    audit_type: str
    severity: str
    actor_type: str
    actor_id: Optional[str]
    actor_name: Optional[str]
    session_id: Optional[str]
    action_description: str
    component: Optional[str]
    file_path: Optional[str]
    function_name: Optional[str]
    line_number: Optional[int]
    event_timestamp: datetime
    recorded_at: Optional[datetime]
    reason: Optional[str]
    parent_record_id: Optional[str]
    genesis_key_id: Optional[str]
    verified: bool

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    """Response for audit trail queries."""
    records: List[AuditRecordResponse]
    total: int
    offset: int
    limit: int
    chain_verified: bool


class AuditStatisticsResponse(BaseModel):
    """Response for audit statistics."""
    total_records: int
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    date_range: Dict[str, Optional[str]]
    chain_verified: bool


class ChainIntegrityResponse(BaseModel):
    """Response for chain integrity verification."""
    is_valid: bool
    issues: List[str]
    total_records: int


@router.get("/trail", response_model=AuditTrailResponse)
async def get_audit_trail(
    audit_type: Optional[str] = Query(None, description="Filter by audit type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    component: Optional[str] = Query(None, description="Filter by component"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: Session = Depends(get_db)
):
    """
    Get the immutable audit trail with filters.
    
    All records are cryptographically linked and cannot be modified.
    Use this endpoint for compliance auditing and traceability.
    """
    storage = get_immutable_audit_storage(session)
    
    # Convert string to enum if provided
    audit_type_enum = None
    if audit_type:
        try:
            audit_type_enum = ImmutableAuditType(audit_type)
        except ValueError:
            pass
    
    records = storage.get_audit_trail(
        audit_type=audit_type_enum,
        actor_id=actor_id,
        component=component,
        file_path=file_path,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    
    # Verify chain integrity
    is_valid, _ = storage.verify_chain_integrity()
    
    return AuditTrailResponse(
        records=[AuditRecordResponse.model_validate(r) for r in records],
        total=len(records),
        offset=offset,
        limit=limit,
        chain_verified=is_valid
    )


@router.get("/record/{record_id}", response_model=AuditRecordResponse)
async def get_audit_record(
    record_id: str,
    session: Session = Depends(get_db)
):
    """Get a specific audit record by ID."""
    storage = get_immutable_audit_storage(session)
    record = storage.get_record_by_id(record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    
    return AuditRecordResponse.model_validate(record)


@router.get("/record/{record_id}/related", response_model=List[AuditRecordResponse])
async def get_related_records(
    record_id: str,
    session: Session = Depends(get_db)
):
    """Get all records related to a parent record."""
    storage = get_immutable_audit_storage(session)
    records = storage.get_related_records(record_id)
    return [AuditRecordResponse.model_validate(r) for r in records]


@router.get("/genesis/{genesis_key_id}", response_model=List[AuditRecordResponse])
async def get_genesis_audit_trail(
    genesis_key_id: str,
    session: Session = Depends(get_db)
):
    """Get all audit records for a specific Genesis Key."""
    storage = get_immutable_audit_storage(session)
    records = storage.get_genesis_audit_trail(genesis_key_id)
    return [AuditRecordResponse.model_validate(r) for r in records]


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    session: Session = Depends(get_db)
):
    """Get statistics about the immutable audit storage."""
    storage = get_immutable_audit_storage(session)
    stats = storage.get_statistics()
    return AuditStatisticsResponse(**stats)


@router.get("/verify-chain", response_model=ChainIntegrityResponse)
async def verify_chain_integrity(
    session: Session = Depends(get_db)
):
    """
    Verify the integrity of the audit chain.
    
    This checks that no records have been tampered with by
    verifying the cryptographic hash chain.
    """
    storage = get_immutable_audit_storage(session)
    is_valid, issues = storage.verify_chain_integrity()
    
    # Get total count
    stats = storage.get_statistics()
    
    return ChainIntegrityResponse(
        is_valid=is_valid,
        issues=issues,
        total_records=stats["total_records"]
    )


@router.get("/types", response_model=List[str])
async def get_audit_types():
    """Get all available audit types."""
    return [t.value for t in ImmutableAuditType]


@router.post("/export")
async def export_audit_trail(
    start_time: Optional[datetime] = Query(None, description="Export start time"),
    end_time: Optional[datetime] = Query(None, description="Export end time"),
    session: Session = Depends(get_db)
):
    """
    Export audit trail to a verified archive file.
    
    Creates a tamper-evident export with integrity checksums.
    Returns the path to the exported file.
    """
    storage = get_immutable_audit_storage(session)
    export_path = storage.export_audit_trail(
        start_time=start_time,
        end_time=end_time
    )
    
    return {
        "status": "success",
        "export_path": str(export_path),
        "message": "Audit trail exported with integrity checksums"
    }
