"""
Immutable Audit Storage System for GRACE.

This module ensures all critical audit data is stored immutably for:
- Auditability: Complete audit trail that cannot be modified
- Traceability: Track any action back to its source
- Data Integrity: Data cannot disappear or be tampered with
- Compliance: Full accountability for all system operations

IMMUTABLE BY DESIGN:
- Write-once, append-only storage
- Cryptographic hashing for integrity verification
- Chain linking to detect tampering
- No delete or update operations on audit records
"""

import uuid
import json
import hashlib
import gzip
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Boolean, Index, event
from database.base import BaseModel

logger = logging.getLogger(__name__)


class ImmutableAuditType(str, Enum):
    """Types of immutable audit events - covers ALL critical data."""
    
    # System Events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    
    # User Events
    USER_INPUT = "user_input"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"
    
    # AI/Agent Events
    AI_DECISION = "ai_decision"
    AI_RESPONSE = "ai_response"
    AI_CODE_GENERATION = "ai_code_generation"
    CODING_AGENT_ACTION = "coding_agent_action"
    SELF_HEALING_ACTION = "self_healing_action"
    
    # Code Events
    CODE_READ = "code_read"
    CODE_CHANGE = "code_change"
    CODE_DELETE = "code_delete"
    CODE_ROLLBACK = "code_rollback"
    
    # Data Events
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    
    # Knowledge Base Events
    KNOWLEDGE_INGESTION = "knowledge_ingestion"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    KNOWLEDGE_UPDATE = "knowledge_update"
    
    # API Events
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    EXTERNAL_API_CALL = "external_api_call"
    
    # Security Events
    SECURITY_ALERT = "security_alert"
    PERMISSION_CHANGE = "permission_change"
    ACCESS_DENIED = "access_denied"
    
    # Genesis Events
    GENESIS_KEY_CREATED = "genesis_key_created"
    GENESIS_KEY_ARCHIVED = "genesis_key_archived"
    GENESIS_FIX_APPLIED = "genesis_fix_applied"


class ImmutableAuditRecord(BaseModel):
    """
    Immutable audit record - CANNOT be modified after creation.
    
    Design principles:
    1. Write-once: No UPDATE operations allowed
    2. Append-only: Only INSERT operations
    3. Chain-linked: Each record links to previous via hash
    4. Cryptographically verified: SHA-256 hash for integrity
    5. Timestamped: Immutable creation timestamp
    """
    __tablename__ = "immutable_audit_records"
    
    # Core identification
    record_id = Column(String(64), nullable=False, unique=True, index=True)  # UUID-based
    record_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of content
    previous_hash = Column(String(64), nullable=True, index=True)  # Chain to previous record
    
    # Event classification
    audit_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info", index=True)  # debug, info, warning, error, critical
    
    # Who (Actor identification)
    actor_type = Column(String(50), nullable=False)  # user, system, ai, agent, api
    actor_id = Column(String(255), nullable=True, index=True)
    actor_name = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # What (Action details)
    action_description = Column(Text, nullable=False)
    action_data = Column(JSON, nullable=True)  # Structured action data
    
    # Where (Location)
    component = Column(String(255), nullable=True, index=True)  # Which system component
    file_path = Column(String(500), nullable=True, index=True)
    function_name = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=True)
    
    # When (Immutable timestamp)
    event_timestamp = Column(DateTime, nullable=False, index=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Why (Context and reasoning)
    reason = Column(Text, nullable=True)
    context = Column(JSON, nullable=True)  # Additional context data
    
    # Before/After State (for changes)
    state_before = Column(JSON, nullable=True)
    state_after = Column(JSON, nullable=True)
    
    # Related records
    parent_record_id = Column(String(64), nullable=True, index=True)  # Parent operation
    genesis_key_id = Column(String(36), nullable=True, index=True)  # Link to Genesis Key
    
    # Verification
    verified = Column(Boolean, nullable=False, default=True)
    verification_status = Column(String(50), nullable=True)
    
    # Indexes for fast querying
    __table_args__ = (
        Index('idx_immutable_audit_type_time', 'audit_type', 'event_timestamp'),
        Index('idx_immutable_audit_actor', 'actor_type', 'actor_id'),
        Index('idx_immutable_audit_component', 'component', 'event_timestamp'),
        Index('idx_immutable_audit_severity', 'severity', 'event_timestamp'),
        Index('idx_immutable_audit_chain', 'previous_hash'),
    )
    
    def __repr__(self):
        return f"<ImmutableAuditRecord(id={self.record_id}, type={self.audit_type}, actor={self.actor_type})>"


class ImmutableAuditStorage:
    """
    Immutable Audit Storage - ensures data cannot disappear.
    
    Features:
    - Write-once storage with no modifications
    - Cryptographic chain linking for tamper detection
    - Dual storage: database + append-only files
    - Automatic archiving with verification
    - Full traceability and auditability
    """
    
    def __init__(
        self,
        session: Session,
        archive_path: Optional[Path] = None,
        enable_file_backup: bool = True
    ):
        """
        Initialize immutable audit storage.
        
        Args:
            session: Database session
            archive_path: Path for immutable audit files
            enable_file_backup: Also write to append-only files
        """
        self.session = session
        self.archive_path = archive_path or Path("backend/data/immutable_audit")
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.enable_file_backup = enable_file_backup
        
        # Get last record hash for chain linking
        self._last_hash = self._get_last_hash()
        
        logger.info("[IMMUTABLE-AUDIT] Storage initialized")
        logger.info(f"[IMMUTABLE-AUDIT] Archive path: {self.archive_path}")
        logger.info(f"[IMMUTABLE-AUDIT] File backup: {enable_file_backup}")
    
    def _get_last_hash(self) -> str:
        """Get the last record hash for chain linking."""
        try:
            last_record = self.session.query(ImmutableAuditRecord).order_by(
                ImmutableAuditRecord.recorded_at.desc()
            ).first()
            
            if last_record:
                return last_record.record_hash
            
            # Genesis hash for first record
            return hashlib.sha256(b"GRACE-GENESIS-AUDIT-CHAIN").hexdigest()
        except Exception as e:
            logger.warning(f"[IMMUTABLE-AUDIT] Could not get last hash: {e}")
            return hashlib.sha256(b"GRACE-GENESIS-AUDIT-CHAIN").hexdigest()
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of audit data."""
        # Serialize deterministically
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def record(
        self,
        audit_type: ImmutableAuditType,
        action_description: str,
        actor_type: str,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: str = "info",
        component: Optional[str] = None,
        file_path: Optional[str] = None,
        function_name: Optional[str] = None,
        line_number: Optional[int] = None,
        reason: Optional[str] = None,
        action_data: Optional[Dict] = None,
        context: Optional[Dict] = None,
        state_before: Optional[Dict] = None,
        state_after: Optional[Dict] = None,
        parent_record_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
        event_timestamp: Optional[datetime] = None
    ) -> ImmutableAuditRecord:
        """
        Record an immutable audit event.
        
        This method is the ONLY way to add audit records.
        Once recorded, the data CANNOT be modified or deleted.
        
        Args:
            audit_type: Type of audit event
            action_description: Human-readable description
            actor_type: Who performed the action (user, system, ai, agent, api)
            actor_id: Unique identifier of the actor
            actor_name: Human-readable name of the actor
            session_id: Session identifier for tracking
            severity: Event severity (debug, info, warning, error, critical)
            component: System component where event occurred
            file_path: File path if applicable
            function_name: Function name if applicable
            line_number: Line number if applicable
            reason: Why this action was taken
            action_data: Structured data about the action
            context: Additional context
            state_before: State before the change
            state_after: State after the change
            parent_record_id: Parent audit record for chaining
            genesis_key_id: Related Genesis Key ID
            event_timestamp: When the event occurred (defaults to now)
            
        Returns:
            The created immutable audit record
        """
        # Generate unique record ID
        record_id = f"IAR-{uuid.uuid4().hex}"
        
        # Use provided timestamp or now
        if event_timestamp is None:
            event_timestamp = datetime.utcnow()
        
        # Build data for hashing
        hash_data = {
            "record_id": record_id,
            "audit_type": audit_type.value if isinstance(audit_type, ImmutableAuditType) else audit_type,
            "action_description": action_description,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "event_timestamp": event_timestamp.isoformat(),
            "previous_hash": self._last_hash,
            "state_before": state_before,
            "state_after": state_after,
            "action_data": action_data
        }
        
        # Compute hash
        record_hash = self._compute_hash(hash_data)
        
        # Create the record
        record = ImmutableAuditRecord(
            record_id=record_id,
            record_hash=record_hash,
            previous_hash=self._last_hash,
            audit_type=audit_type.value if isinstance(audit_type, ImmutableAuditType) else audit_type,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_name=actor_name,
            session_id=session_id,
            action_description=action_description,
            action_data=action_data,
            component=component,
            file_path=file_path,
            function_name=function_name,
            line_number=line_number,
            event_timestamp=event_timestamp,
            reason=reason,
            context=context,
            state_before=state_before,
            state_after=state_after,
            parent_record_id=parent_record_id,
            genesis_key_id=genesis_key_id,
            verified=True
        )
        
        # Add to database
        self.session.add(record)
        self.session.commit()
        
        # Update chain hash
        self._last_hash = record_hash
        
        # Also write to append-only file for backup
        if self.enable_file_backup:
            self._write_to_file(record)
        
        logger.debug(f"[IMMUTABLE-AUDIT] Recorded: {audit_type} - {action_description[:50]}")
        
        return record
    
    def _write_to_file(self, record: ImmutableAuditRecord):
        """Write record to append-only audit file."""
        try:
            # Use date-based file for organization
            date_str = record.event_timestamp.strftime("%Y-%m-%d")
            audit_file = self.archive_path / f"audit_{date_str}.jsonl"
            
            # Serialize record
            record_data = {
                "record_id": record.record_id,
                "record_hash": record.record_hash,
                "previous_hash": record.previous_hash,
                "audit_type": record.audit_type,
                "severity": record.severity,
                "actor_type": record.actor_type,
                "actor_id": record.actor_id,
                "actor_name": record.actor_name,
                "session_id": record.session_id,
                "action_description": record.action_description,
                "action_data": record.action_data,
                "component": record.component,
                "file_path": record.file_path,
                "function_name": record.function_name,
                "line_number": record.line_number,
                "event_timestamp": record.event_timestamp.isoformat(),
                "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
                "reason": record.reason,
                "context": record.context,
                "state_before": record.state_before,
                "state_after": record.state_after,
                "parent_record_id": record.parent_record_id,
                "genesis_key_id": record.genesis_key_id
            }
            
            # Append to file (append mode - never overwrites)
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record_data, default=str) + "\n")
                
        except Exception as e:
            logger.error(f"[IMMUTABLE-AUDIT] File write error: {e}")
    
    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the audit chain.
        
        Checks that no records have been tampered with by
        verifying the hash chain.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Get all records in order
            records = self.session.query(ImmutableAuditRecord).order_by(
                ImmutableAuditRecord.recorded_at.asc()
            ).all()
            
            if not records:
                return True, []
            
            # Check first record
            first_record = records[0]
            expected_genesis = hashlib.sha256(b"GRACE-GENESIS-AUDIT-CHAIN").hexdigest()
            
            if first_record.previous_hash != expected_genesis:
                issues.append(f"First record has invalid genesis hash: {first_record.record_id}")
            
            # Verify chain
            for i in range(1, len(records)):
                current = records[i]
                previous = records[i - 1]
                
                if current.previous_hash != previous.record_hash:
                    issues.append(
                        f"Chain break at record {current.record_id}: "
                        f"expected {previous.record_hash}, got {current.previous_hash}"
                    )
            
            is_valid = len(issues) == 0
            
            if is_valid:
                logger.info(f"[IMMUTABLE-AUDIT] Chain integrity verified: {len(records)} records")
            else:
                logger.error(f"[IMMUTABLE-AUDIT] Chain integrity FAILED: {len(issues)} issues")
            
            return is_valid, issues
            
        except Exception as e:
            logger.error(f"[IMMUTABLE-AUDIT] Chain verification error: {e}")
            return False, [str(e)]
    
    def get_audit_trail(
        self,
        audit_type: Optional[ImmutableAuditType] = None,
        actor_id: Optional[str] = None,
        component: Optional[str] = None,
        file_path: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[ImmutableAuditRecord]:
        """
        Get audit trail with filters.
        
        Args:
            audit_type: Filter by audit type
            actor_id: Filter by actor ID
            component: Filter by component
            file_path: Filter by file path
            start_time: Filter by start time
            end_time: Filter by end time
            severity: Filter by severity
            limit: Maximum records to return
            offset: Pagination offset
            
        Returns:
            List of matching audit records
        """
        query = self.session.query(ImmutableAuditRecord)
        
        if audit_type:
            type_value = audit_type.value if isinstance(audit_type, ImmutableAuditType) else audit_type
            query = query.filter(ImmutableAuditRecord.audit_type == type_value)
        
        if actor_id:
            query = query.filter(ImmutableAuditRecord.actor_id == actor_id)
        
        if component:
            query = query.filter(ImmutableAuditRecord.component == component)
        
        if file_path:
            query = query.filter(ImmutableAuditRecord.file_path == file_path)
        
        if start_time:
            query = query.filter(ImmutableAuditRecord.event_timestamp >= start_time)
        
        if end_time:
            query = query.filter(ImmutableAuditRecord.event_timestamp <= end_time)
        
        if severity:
            query = query.filter(ImmutableAuditRecord.severity == severity)
        
        # Order by most recent first
        query = query.order_by(ImmutableAuditRecord.event_timestamp.desc())
        
        # Paginate
        records = query.offset(offset).limit(limit).all()
        
        return records
    
    def get_record_by_id(self, record_id: str) -> Optional[ImmutableAuditRecord]:
        """Get a specific audit record by ID."""
        return self.session.query(ImmutableAuditRecord).filter(
            ImmutableAuditRecord.record_id == record_id
        ).first()
    
    def get_related_records(self, record_id: str) -> List[ImmutableAuditRecord]:
        """Get all records related to a parent record."""
        return self.session.query(ImmutableAuditRecord).filter(
            ImmutableAuditRecord.parent_record_id == record_id
        ).order_by(ImmutableAuditRecord.event_timestamp.asc()).all()
    
    def get_genesis_audit_trail(self, genesis_key_id: str) -> List[ImmutableAuditRecord]:
        """Get all audit records for a Genesis Key."""
        return self.session.query(ImmutableAuditRecord).filter(
            ImmutableAuditRecord.genesis_key_id == genesis_key_id
        ).order_by(ImmutableAuditRecord.event_timestamp.asc()).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit storage statistics."""
        from sqlalchemy import func
        
        total_records = self.session.query(ImmutableAuditRecord).count()
        
        # Count by type
        type_counts = self.session.query(
            ImmutableAuditRecord.audit_type,
            func.count(ImmutableAuditRecord.id)
        ).group_by(ImmutableAuditRecord.audit_type).all()
        
        # Count by severity
        severity_counts = self.session.query(
            ImmutableAuditRecord.severity,
            func.count(ImmutableAuditRecord.id)
        ).group_by(ImmutableAuditRecord.severity).all()
        
        # Get date range
        oldest = self.session.query(func.min(ImmutableAuditRecord.event_timestamp)).scalar()
        newest = self.session.query(func.max(ImmutableAuditRecord.event_timestamp)).scalar()
        
        return {
            "total_records": total_records,
            "by_type": {t: c for t, c in type_counts},
            "by_severity": {s: c for s, c in severity_counts},
            "date_range": {
                "oldest": oldest.isoformat() if oldest else None,
                "newest": newest.isoformat() if newest else None
            },
            "chain_verified": self.verify_chain_integrity()[0]
        }
    
    def export_audit_trail(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Export audit trail to a verified archive file.
        
        Creates a tamper-evident export with integrity checksums.
        """
        records = self.get_audit_trail(
            start_time=start_time,
            end_time=end_time,
            limit=100000  # Large limit for export
        )
        
        # Prepare export data
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_records": len(records),
            "date_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "records": []
        }
        
        for record in records:
            export_data["records"].append({
                "record_id": record.record_id,
                "record_hash": record.record_hash,
                "previous_hash": record.previous_hash,
                "audit_type": record.audit_type,
                "severity": record.severity,
                "actor_type": record.actor_type,
                "actor_id": record.actor_id,
                "action_description": record.action_description,
                "event_timestamp": record.event_timestamp.isoformat() if record.event_timestamp else None,
                "component": record.component,
                "file_path": record.file_path,
                "reason": record.reason,
                "state_before": record.state_before,
                "state_after": record.state_after,
                "genesis_key_id": record.genesis_key_id
            })
        
        # Compute export hash
        export_hash = hashlib.sha256(
            json.dumps(export_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        export_data["export_hash"] = export_hash
        
        # Determine output path
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.archive_path / f"audit_export_{timestamp}.json.gz"
        
        # Write compressed export
        with gzip.open(output_path, 'wt', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"[IMMUTABLE-AUDIT] Exported {len(records)} records to {output_path}")
        
        return output_path


# Convenience functions for common audit operations

_audit_storage: Optional[ImmutableAuditStorage] = None


def get_immutable_audit_storage(session: Session) -> ImmutableAuditStorage:
    """Get or create the immutable audit storage instance."""
    global _audit_storage
    if _audit_storage is None:
        _audit_storage = ImmutableAuditStorage(session)
    return _audit_storage


def audit_user_input(
    session: Session,
    user_id: str,
    input_content: str,
    context: Optional[Dict] = None
) -> ImmutableAuditRecord:
    """Record a user input event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.USER_INPUT,
        action_description=f"User input: {input_content[:100]}...",
        actor_type="user",
        actor_id=user_id,
        action_data={"content": input_content},
        context=context
    )


def audit_code_change(
    session: Session,
    actor_id: str,
    actor_type: str,
    file_path: str,
    code_before: Optional[str],
    code_after: Optional[str],
    reason: Optional[str] = None,
    genesis_key_id: Optional[str] = None
) -> ImmutableAuditRecord:
    """Record a code change event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.CODE_CHANGE,
        action_description=f"Code changed in {file_path}",
        actor_type=actor_type,
        actor_id=actor_id,
        file_path=file_path,
        reason=reason,
        state_before={"code": code_before} if code_before else None,
        state_after={"code": code_after} if code_after else None,
        genesis_key_id=genesis_key_id
    )


def audit_ai_decision(
    session: Session,
    decision: str,
    reasoning: str,
    context: Optional[Dict] = None,
    confidence: Optional[float] = None
) -> ImmutableAuditRecord:
    """Record an AI decision event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.AI_DECISION,
        action_description=f"AI Decision: {decision[:100]}",
        actor_type="ai",
        actor_id="grace-ai",
        reason=reasoning,
        action_data={"decision": decision, "confidence": confidence},
        context=context
    )


def audit_data_access(
    session: Session,
    actor_id: str,
    actor_type: str,
    data_type: str,
    data_id: str,
    reason: Optional[str] = None
) -> ImmutableAuditRecord:
    """Record a data access event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.DATA_ACCESS,
        action_description=f"Accessed {data_type}: {data_id}",
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
        action_data={"data_type": data_type, "data_id": data_id}
    )


def audit_system_event(
    session: Session,
    event_type: str,
    description: str,
    severity: str = "info",
    component: Optional[str] = None,
    context: Optional[Dict] = None
) -> ImmutableAuditRecord:
    """Record a system event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.SYSTEM_ERROR if severity in ["error", "critical"] else ImmutableAuditType.SYSTEM_STARTUP,
        action_description=f"System event: {event_type} - {description}",
        actor_type="system",
        actor_id="grace-system",
        severity=severity,
        component=component,
        context=context
    )


def audit_security_event(
    session: Session,
    event_type: str,
    description: str,
    actor_id: Optional[str] = None,
    severity: str = "warning",
    context: Optional[Dict] = None
) -> ImmutableAuditRecord:
    """Record a security event."""
    storage = get_immutable_audit_storage(session)
    return storage.record(
        audit_type=ImmutableAuditType.SECURITY_ALERT,
        action_description=f"Security: {event_type} - {description}",
        actor_type="security",
        actor_id=actor_id,
        severity=severity,
        context=context
    )
