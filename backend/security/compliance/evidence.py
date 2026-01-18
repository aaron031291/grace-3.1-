"""
GRACE Compliance Evidence Collection

Provides automated evidence collection for compliance audits:
- Evidence gathering from audit logs
- Evidence packaging for auditors
- Retention policies
- Chain of custody tracking
- Tamper-evident storage
"""

import gzip
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """Types of compliance evidence."""
    AUDIT_LOG = "audit_log"
    CONFIGURATION = "configuration"
    POLICY_DOCUMENT = "policy_document"
    SCREENSHOT = "screenshot"
    REPORT = "report"
    ATTESTATION = "attestation"
    APPROVAL_RECORD = "approval_record"
    TEST_RESULT = "test_result"
    METRIC = "metric"
    CODE_REVIEW = "code_review"


class EvidenceStatus(str, Enum):
    """Status of evidence."""
    COLLECTED = "collected"
    VERIFIED = "verified"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class ChainOfCustody:
    """Chain of custody record for evidence."""
    timestamp: datetime
    action: str
    actor: str
    notes: str = ""
    integrity_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "actor": self.actor,
            "notes": self.notes,
            "integrity_hash": self.integrity_hash,
        }


@dataclass
class Evidence:
    """A piece of compliance evidence."""
    evidence_id: str
    evidence_type: EvidenceType
    control_ids: List[str]
    title: str
    description: str
    content: Any
    content_hash: str
    collected_at: datetime
    collected_by: str
    source_system: str
    status: EvidenceStatus = EvidenceStatus.COLLECTED
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chain_of_custody: List[ChainOfCustody] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        result = {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "control_ids": self.control_ids,
            "title": self.title,
            "description": self.description,
            "content_hash": self.content_hash,
            "collected_at": self.collected_at.isoformat(),
            "collected_by": self.collected_by,
            "source_system": self.source_system,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "chain_of_custody": [c.to_dict() for c in self.chain_of_custody],
        }
        if include_content:
            result["content"] = self.content
        return result
    
    def add_custody_record(
        self,
        action: str,
        actor: str,
        notes: str = "",
    ):
        """Add a chain of custody record."""
        record = ChainOfCustody(
            timestamp=datetime.utcnow(),
            action=action,
            actor=actor,
            notes=notes,
            integrity_hash=self.content_hash,
        )
        self.chain_of_custody.append(record)
    
    def verify_integrity(self) -> bool:
        """Verify evidence has not been tampered with."""
        current_hash = self._compute_hash(self.content)
        return current_hash == self.content_hash
    
    @staticmethod
    def _compute_hash(content: Any) -> str:
        """Compute hash of content."""
        if isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode()
        return hashlib.sha256(data).hexdigest()


@dataclass
class RetentionPolicy:
    """Evidence retention policy."""
    policy_id: str
    name: str
    evidence_types: List[EvidenceType]
    retention_period: timedelta
    archive_after: Optional[timedelta] = None
    delete_after_archive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "evidence_types": [t.value for t in self.evidence_types],
            "retention_days": self.retention_period.days,
            "archive_after_days": self.archive_after.days if self.archive_after else None,
        }


class EvidenceCollector:
    """
    Collects evidence from various sources.
    
    Gathers evidence from:
    - Audit logs
    - Configuration files
    - System metrics
    - Test results
    """
    
    def __init__(self):
        self._evidence_store: Dict[str, Evidence] = {}
        self._lock = threading.RLock()
        
        logger.info("[EVIDENCE] Evidence collector initialized")
    
    def collect_from_audit(
        self,
        control_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        audit_types: Optional[List[str]] = None,
        collected_by: str = "system",
    ) -> Evidence:
        """
        Collect evidence from audit logs.
        
        Args:
            control_ids: Controls this evidence supports
            start_time: Start of evidence period
            end_time: End of evidence period
            audit_types: Types of audit records to collect
            collected_by: Who collected the evidence
            
        Returns:
            Evidence object
        """
        try:
            from genesis.immutable_audit_storage import get_immutable_audit_storage
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                
                # Get audit records for the period
                records = storage.get_audit_trail(
                    start_time=start_time,
                    end_time=end_time,
                    limit=10000,
                )
                
                if audit_types:
                    records = [r for r in records if r.get("audit_type") in audit_types]
                
                content = {
                    "period_start": start_time.isoformat(),
                    "period_end": end_time.isoformat(),
                    "record_count": len(records),
                    "audit_types": list(set(r.get("audit_type", "unknown") for r in records)),
                    "records": records,
                }
                
                evidence = self._create_evidence(
                    evidence_type=EvidenceType.AUDIT_LOG,
                    control_ids=control_ids,
                    title=f"Audit Log Evidence: {start_time.date()} to {end_time.date()}",
                    description=f"Collected {len(records)} audit records",
                    content=content,
                    collected_by=collected_by,
                    source_system="immutable_audit",
                )
                
                return evidence
                
        except Exception as e:
            logger.error(f"[EVIDENCE] Audit collection failed: {e}")
            raise
    
    def collect_configuration(
        self,
        control_ids: List[str],
        config_path: str,
        collected_by: str = "system",
    ) -> Evidence:
        """Collect configuration file as evidence."""
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration not found: {config_path}")
        
        content = {
            "path": str(path),
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "content": path.read_text() if path.suffix in [".json", ".yaml", ".yml", ".toml", ".ini"] else "[binary file]",
        }
        
        evidence = self._create_evidence(
            evidence_type=EvidenceType.CONFIGURATION,
            control_ids=control_ids,
            title=f"Configuration: {path.name}",
            description=f"Configuration file from {config_path}",
            content=content,
            collected_by=collected_by,
            source_system="filesystem",
        )
        
        return evidence
    
    def collect_test_result(
        self,
        control_ids: List[str],
        test_name: str,
        passed: bool,
        details: Dict[str, Any],
        collected_by: str = "system",
    ) -> Evidence:
        """Collect test result as evidence."""
        content = {
            "test_name": test_name,
            "passed": passed,
            "executed_at": datetime.utcnow().isoformat(),
            "details": details,
        }
        
        evidence = self._create_evidence(
            evidence_type=EvidenceType.TEST_RESULT,
            control_ids=control_ids,
            title=f"Test Result: {test_name}",
            description=f"{'PASSED' if passed else 'FAILED'}: {test_name}",
            content=content,
            collected_by=collected_by,
            source_system="test_framework",
            tags={"result": "passed" if passed else "failed"},
        )
        
        return evidence
    
    def collect_metric(
        self,
        control_ids: List[str],
        metric_name: str,
        value: Any,
        unit: str,
        collected_by: str = "system",
    ) -> Evidence:
        """Collect a metric as evidence."""
        content = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "collected_at": datetime.utcnow().isoformat(),
        }
        
        evidence = self._create_evidence(
            evidence_type=EvidenceType.METRIC,
            control_ids=control_ids,
            title=f"Metric: {metric_name}",
            description=f"{metric_name}: {value} {unit}",
            content=content,
            collected_by=collected_by,
            source_system="metrics",
        )
        
        return evidence
    
    def _create_evidence(
        self,
        evidence_type: EvidenceType,
        control_ids: List[str],
        title: str,
        description: str,
        content: Any,
        collected_by: str,
        source_system: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> Evidence:
        """Create and store evidence."""
        content_hash = Evidence._compute_hash(content)
        
        evidence = Evidence(
            evidence_id=f"EV-{uuid.uuid4().hex[:12]}",
            evidence_type=evidence_type,
            control_ids=control_ids,
            title=title,
            description=description,
            content=content,
            content_hash=content_hash,
            collected_at=datetime.utcnow(),
            collected_by=collected_by,
            source_system=source_system,
            tags=tags or {},
        )
        
        evidence.add_custody_record(
            action="collected",
            actor=collected_by,
            notes=f"Evidence collected from {source_system}",
        )
        
        with self._lock:
            self._evidence_store[evidence.evidence_id] = evidence
        
        logger.info(f"[EVIDENCE] Collected: {evidence.evidence_id} - {title}")
        
        return evidence
    
    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        with self._lock:
            return self._evidence_store.get(evidence_id)
    
    def get_evidence_for_control(self, control_id: str) -> List[Evidence]:
        """Get all evidence for a control."""
        with self._lock:
            return [
                e for e in self._evidence_store.values()
                if control_id in e.control_ids
            ]
    
    def verify_evidence(
        self,
        evidence_id: str,
        verifier: str,
    ) -> bool:
        """Verify evidence integrity and mark as verified."""
        with self._lock:
            evidence = self._evidence_store.get(evidence_id)
            if not evidence:
                return False
            
            if evidence.verify_integrity():
                evidence.status = EvidenceStatus.VERIFIED
                evidence.add_custody_record(
                    action="verified",
                    actor=verifier,
                    notes="Integrity verified",
                )
                return True
            else:
                evidence.status = EvidenceStatus.REJECTED
                evidence.add_custody_record(
                    action="verification_failed",
                    actor=verifier,
                    notes="Hash mismatch detected",
                )
                logger.warning(f"[EVIDENCE] Integrity check failed: {evidence_id}")
                return False


class EvidencePackager:
    """
    Packages evidence for auditors.
    
    Creates tamper-evident export packages.
    """
    
    def __init__(
        self,
        output_dir: str = "data/evidence_packages",
    ):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_package(
        self,
        evidence_list: List[Evidence],
        package_name: str,
        prepared_by: str,
        include_content: bool = True,
    ) -> str:
        """
        Create an evidence package.
        
        Args:
            evidence_list: Evidence to include
            package_name: Name for the package
            prepared_by: Who prepared the package
            include_content: Whether to include full content
            
        Returns:
            Path to the package file
        """
        package_id = f"PKG-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow()
        
        package_data = {
            "package_id": package_id,
            "package_name": package_name,
            "created_at": timestamp.isoformat(),
            "prepared_by": prepared_by,
            "evidence_count": len(evidence_list),
            "evidence": [e.to_dict(include_content=include_content) for e in evidence_list],
        }
        
        # Compute package hash
        package_hash = hashlib.sha256(
            json.dumps(package_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        package_data["package_hash"] = package_hash
        
        # Add chain of custody for packaging
        for evidence in evidence_list:
            evidence.add_custody_record(
                action="packaged",
                actor=prepared_by,
                notes=f"Included in package {package_id}",
            )
        
        # Write package
        filename = f"{package_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json.gz"
        filepath = self._output_dir / filename
        
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            json.dump(package_data, f, indent=2, default=str)
        
        # Write manifest
        manifest = {
            "package_id": package_id,
            "package_file": filename,
            "package_hash": package_hash,
            "created_at": timestamp.isoformat(),
            "evidence_ids": [e.evidence_id for e in evidence_list],
        }
        
        manifest_path = self._output_dir / f"{package_name}_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"[EVIDENCE] Package created: {filepath}")
        
        return str(filepath)
    
    def verify_package(self, package_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify a package has not been tampered with."""
        try:
            with gzip.open(package_path, "rt", encoding="utf-8") as f:
                package_data = json.load(f)
            
            stored_hash = package_data.pop("package_hash", None)
            computed_hash = hashlib.sha256(
                json.dumps(package_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            is_valid = stored_hash == computed_hash
            
            return is_valid, {
                "package_id": package_data.get("package_id"),
                "stored_hash": stored_hash,
                "computed_hash": computed_hash,
                "evidence_count": package_data.get("evidence_count"),
            }
            
        except Exception as e:
            return False, {"error": str(e)}


class RetentionManager:
    """
    Manages evidence retention policies.
    """
    
    def __init__(self):
        self._policies: Dict[str, RetentionPolicy] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Set up default retention policies."""
        policies = [
            RetentionPolicy(
                policy_id="default",
                name="Default Retention",
                evidence_types=list(EvidenceType),
                retention_period=timedelta(days=365 * 7),  # 7 years
                archive_after=timedelta(days=365 * 2),  # Archive after 2 years
            ),
            RetentionPolicy(
                policy_id="audit_logs",
                name="Audit Log Retention",
                evidence_types=[EvidenceType.AUDIT_LOG],
                retention_period=timedelta(days=365 * 7),  # 7 years for compliance
            ),
            RetentionPolicy(
                policy_id="test_results",
                name="Test Result Retention",
                evidence_types=[EvidenceType.TEST_RESULT],
                retention_period=timedelta(days=365 * 3),  # 3 years
                archive_after=timedelta(days=365),
            ),
        ]
        
        for policy in policies:
            self._policies[policy.policy_id] = policy
    
    def get_policy(self, evidence_type: EvidenceType) -> RetentionPolicy:
        """Get applicable policy for evidence type."""
        for policy in self._policies.values():
            if evidence_type in policy.evidence_types:
                return policy
        return self._policies["default"]
    
    def check_retention(self, evidence: Evidence) -> Dict[str, Any]:
        """Check retention status of evidence."""
        policy = self.get_policy(evidence.evidence_type)
        age = datetime.utcnow() - evidence.collected_at
        
        should_archive = policy.archive_after and age > policy.archive_after
        should_delete = age > policy.retention_period
        
        return {
            "evidence_id": evidence.evidence_id,
            "policy_id": policy.policy_id,
            "age_days": age.days,
            "retention_days": policy.retention_period.days,
            "should_archive": should_archive,
            "should_delete": should_delete,
        }


# Singletons
_collector: Optional[EvidenceCollector] = None
_packager: Optional[EvidencePackager] = None


def get_evidence_collector() -> EvidenceCollector:
    """Get evidence collector singleton."""
    global _collector
    if _collector is None:
        _collector = EvidenceCollector()
    return _collector


def get_evidence_packager() -> EvidencePackager:
    """Get evidence packager singleton."""
    global _packager
    if _packager is None:
        _packager = EvidencePackager()
    return _packager
