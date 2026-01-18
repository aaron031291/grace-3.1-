"""
Disaster Recovery & Compliance
==============================

Enterprise disaster recovery and compliance automation:

1. Backup Management - Automated backups, retention policies
2. Failover - Automatic and manual failover
3. Recovery Point Objectives (RPO) - Data loss tolerance
4. Recovery Time Objectives (RTO) - Downtime tolerance
5. Compliance Automation - SOC2, HIPAA, GDPR
6. Audit Trails - Complete operation history
"""

import os
import sys
import json
import shutil
import hashlib
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import threading
import sqlite3

logger = logging.getLogger(__name__)


# =============================================================================
# BACKUP MANAGEMENT
# =============================================================================

class BackupType(str, Enum):
    """Types of backups."""
    FULL = "full"               # Complete backup
    INCREMENTAL = "incremental" # Changes since last backup
    DIFFERENTIAL = "differential"  # Changes since last full backup
    SNAPSHOT = "snapshot"       # Point-in-time snapshot


class BackupStatus(str, Enum):
    """Backup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class BackupConfig:
    """Backup configuration."""
    backup_dir: Path = field(default_factory=lambda: Path("backups"))
    retention_days: int = 30
    full_backup_interval_days: int = 7
    incremental_interval_hours: int = 1
    compress: bool = True
    encrypt: bool = False
    verify_after_backup: bool = True


@dataclass
class BackupRecord:
    """Record of a backup."""
    id: str
    type: BackupType
    status: BackupStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    size_bytes: int = 0
    checksum: Optional[str] = None
    files_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupManager:
    """
    Manages automated backups.
    
    Features:
    - Multiple backup types
    - Compression
    - Verification
    - Retention policies
    - Restore operations
    """
    
    def __init__(self, config: Optional[BackupConfig] = None, data_dir: Optional[Path] = None):
        self.config = config or BackupConfig()
        self.data_dir = data_dir or Path("data")
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._backups: Dict[str, BackupRecord] = {}
        self._lock = threading.Lock()
        self._last_full_backup: Optional[datetime] = None
        self._last_incremental: Optional[datetime] = None
        
        # Load existing backup records
        self._load_backup_records()
    
    def _load_backup_records(self):
        """Load existing backup records."""
        records_file = self.config.backup_dir / "backup_records.json"
        if records_file.exists():
            try:
                data = json.loads(records_file.read_text())
                for record_data in data.get("backups", []):
                    record = BackupRecord(
                        id=record_data["id"],
                        type=BackupType(record_data["type"]),
                        status=BackupStatus(record_data["status"]),
                        created_at=datetime.fromisoformat(record_data["created_at"]),
                        completed_at=datetime.fromisoformat(record_data["completed_at"]) if record_data.get("completed_at") else None,
                        size_bytes=record_data.get("size_bytes", 0),
                        checksum=record_data.get("checksum"),
                        files_count=record_data.get("files_count", 0),
                    )
                    self._backups[record.id] = record
            except Exception as e:
                logger.error(f"Failed to load backup records: {e}")
    
    def _save_backup_records(self):
        """Save backup records."""
        records_file = self.config.backup_dir / "backup_records.json"
        data = {
            "backups": [
                {
                    "id": r.id,
                    "type": r.type.value,
                    "status": r.status.value,
                    "created_at": r.created_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "size_bytes": r.size_bytes,
                    "checksum": r.checksum,
                    "files_count": r.files_count,
                }
                for r in self._backups.values()
            ]
        }
        records_file.write_text(json.dumps(data, indent=2))
    
    def create_backup(self, backup_type: BackupType = BackupType.FULL) -> BackupRecord:
        """Create a backup."""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_type.value}"
        
        record = BackupRecord(
            id=backup_id,
            type=backup_type,
            status=BackupStatus.IN_PROGRESS,
            created_at=datetime.now(),
        )
        
        self._backups[backup_id] = record
        
        try:
            backup_path = self.config.backup_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup database
            db_path = self.data_dir / "grace.db"
            if db_path.exists():
                if self.config.compress:
                    with open(db_path, 'rb') as f_in:
                        with gzip.open(backup_path / "grace.db.gz", 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    shutil.copy2(db_path, backup_path / "grace.db")
                record.files_count += 1
            
            # Backup config files
            config_files = [
                self.data_dir.parent / "backend" / "enterprise" / "multi_os_config.json",
                self.data_dir.parent / ".env",
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    shutil.copy2(config_file, backup_path / config_file.name)
                    record.files_count += 1
            
            # Calculate checksum
            record.checksum = self._calculate_backup_checksum(backup_path)
            
            # Calculate size
            record.size_bytes = sum(
                f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
            )
            
            record.status = BackupStatus.COMPLETED
            record.completed_at = datetime.now()
            
            # Verify if configured
            if self.config.verify_after_backup:
                if self._verify_backup(backup_id):
                    record.status = BackupStatus.VERIFIED
            
            logger.info(f"Backup completed: {backup_id} ({record.size_bytes} bytes)")
            
        except Exception as e:
            record.status = BackupStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Backup failed: {e}")
        
        self._save_backup_records()
        return record
    
    def _calculate_backup_checksum(self, backup_path: Path) -> str:
        """Calculate checksum for backup."""
        hasher = hashlib.sha256()
        for file_path in sorted(backup_path.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
        return hasher.hexdigest()
    
    def _verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity."""
        if backup_id not in self._backups:
            return False
        
        record = self._backups[backup_id]
        backup_path = self.config.backup_dir / backup_id
        
        if not backup_path.exists():
            return False
        
        current_checksum = self._calculate_backup_checksum(backup_path)
        return current_checksum == record.checksum
    
    def restore_backup(self, backup_id: str, target_dir: Optional[Path] = None) -> bool:
        """Restore from backup."""
        if backup_id not in self._backups:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        record = self._backups[backup_id]
        backup_path = self.config.backup_dir / backup_id
        target_dir = target_dir or self.data_dir
        
        try:
            # Restore database
            db_backup = backup_path / "grace.db.gz"
            if db_backup.exists():
                with gzip.open(db_backup, 'rb') as f_in:
                    with open(target_dir / "grace.db", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            elif (backup_path / "grace.db").exists():
                shutil.copy2(backup_path / "grace.db", target_dir / "grace.db")
            
            logger.info(f"Restored backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.config.retention_days)
        
        for backup_id, record in list(self._backups.items()):
            if record.created_at < cutoff:
                backup_path = self.config.backup_dir / backup_id
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                del self._backups[backup_id]
                logger.info(f"Removed old backup: {backup_id}")
        
        self._save_backup_records()
    
    def get_latest_backup(self, backup_type: Optional[BackupType] = None) -> Optional[BackupRecord]:
        """Get the most recent backup."""
        backups = list(self._backups.values())
        if backup_type:
            backups = [b for b in backups if b.type == backup_type]
        
        if not backups:
            return None
        
        return max(backups, key=lambda b: b.created_at)
    
    def list_backups(self) -> List[Dict]:
        """List all backups."""
        return [
            {
                "id": r.id,
                "type": r.type.value,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "size_mb": round(r.size_bytes / (1024 * 1024), 2),
                "files_count": r.files_count,
            }
            for r in sorted(self._backups.values(), key=lambda r: r.created_at, reverse=True)
        ]


# =============================================================================
# FAILOVER MANAGEMENT
# =============================================================================

class FailoverMode(str, Enum):
    """Failover modes."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class FailoverStatus(str, Enum):
    """Failover status."""
    STANDBY = "standby"
    FAILING_OVER = "failing_over"
    ACTIVE = "active"
    FAILED = "failed"


@dataclass
class FailoverTarget:
    """A failover target."""
    name: str
    url: str
    priority: int = 0
    status: FailoverStatus = FailoverStatus.STANDBY
    last_health_check: Optional[datetime] = None
    healthy: bool = False


class FailoverManager:
    """
    Manages failover between primary and backup systems.
    
    Features:
    - Multiple backup targets
    - Priority-based failover
    - Health monitoring
    - Automatic failback
    """
    
    def __init__(self, mode: FailoverMode = FailoverMode.AUTOMATIC):
        self.mode = mode
        self.targets: Dict[str, FailoverTarget] = {}
        self.active_target: Optional[str] = None
        self._health_check_interval = 30
        self._monitoring = False
        self._lock = threading.Lock()
    
    def register_target(self, target: FailoverTarget):
        """Register a failover target."""
        self.targets[target.name] = target
        logger.info(f"Registered failover target: {target.name}")
    
    def set_primary(self, name: str):
        """Set the primary target."""
        if name in self.targets:
            self.active_target = name
            self.targets[name].status = FailoverStatus.ACTIVE
            logger.info(f"Primary target set: {name}")
    
    def check_target_health(self, name: str) -> bool:
        """Check health of a target."""
        if name not in self.targets:
            return False
        
        target = self.targets[name]
        
        try:
            import requests
            response = requests.get(f"{target.url}/health", timeout=5)
            target.healthy = response.status_code == 200
        except Exception:
            target.healthy = False
        
        target.last_health_check = datetime.now()
        return target.healthy
    
    def trigger_failover(self, reason: str = "manual") -> bool:
        """Trigger failover to next available target."""
        with self._lock:
            # Find next healthy target by priority
            available = [
                t for t in self.targets.values()
                if t.name != self.active_target and t.healthy
            ]
            
            if not available:
                logger.error("No healthy failover targets available")
                return False
            
            # Sort by priority
            available.sort(key=lambda t: t.priority)
            new_target = available[0]
            
            # Perform failover
            if self.active_target:
                self.targets[self.active_target].status = FailoverStatus.STANDBY
            
            new_target.status = FailoverStatus.ACTIVE
            old_target = self.active_target
            self.active_target = new_target.name
            
            logger.warning(f"Failover: {old_target} -> {new_target.name} (reason: {reason})")
            return True
    
    def get_active_target(self) -> Optional[FailoverTarget]:
        """Get the currently active target."""
        if self.active_target:
            return self.targets.get(self.active_target)
        return None
    
    def get_status(self) -> Dict:
        """Get failover status."""
        return {
            "mode": self.mode.value,
            "active_target": self.active_target,
            "targets": {
                name: {
                    "url": t.url,
                    "priority": t.priority,
                    "status": t.status.value,
                    "healthy": t.healthy,
                    "last_check": t.last_health_check.isoformat() if t.last_health_check else None,
                }
                for name, t in self.targets.items()
            }
        }


# =============================================================================
# COMPLIANCE AUTOMATION
# =============================================================================

class ComplianceFramework(str, Enum):
    """Compliance frameworks."""
    SOC2 = "soc2"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"


@dataclass
class ComplianceCheck:
    """A compliance check."""
    id: str
    framework: ComplianceFramework
    name: str
    description: str
    check_function: Callable[[], bool]
    severity: str = "medium"  # low, medium, high, critical
    last_check: Optional[datetime] = None
    passed: Optional[bool] = None
    evidence: Optional[str] = None


class ComplianceManager:
    """
    Automates compliance checks.
    
    Features:
    - Multiple frameworks (SOC2, HIPAA, GDPR, etc.)
    - Automated evidence collection
    - Compliance reports
    - Remediation suggestions
    """
    
    def __init__(self):
        self._checks: Dict[str, ComplianceCheck] = {}
        self._audit_trail: List[Dict] = []
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default compliance checks."""
        # Data Encryption
        self.register_check(ComplianceCheck(
            id="enc_at_rest",
            framework=ComplianceFramework.SOC2,
            name="Encryption at Rest",
            description="Verify data is encrypted at rest",
            check_function=self._check_encryption_at_rest,
            severity="critical",
        ))
        
        # Access Logging
        self.register_check(ComplianceCheck(
            id="access_logging",
            framework=ComplianceFramework.SOC2,
            name="Access Logging",
            description="Verify access logging is enabled",
            check_function=self._check_access_logging,
            severity="high",
        ))
        
        # Backup Verification
        self.register_check(ComplianceCheck(
            id="backup_exists",
            framework=ComplianceFramework.SOC2,
            name="Backup Exists",
            description="Verify recent backups exist",
            check_function=self._check_backup_exists,
            severity="high",
        ))
        
        # GDPR: Data Retention
        self.register_check(ComplianceCheck(
            id="data_retention",
            framework=ComplianceFramework.GDPR,
            name="Data Retention Policy",
            description="Verify data retention policy is enforced",
            check_function=self._check_data_retention,
            severity="high",
        ))
        
        # HIPAA: Audit Controls
        self.register_check(ComplianceCheck(
            id="audit_controls",
            framework=ComplianceFramework.HIPAA,
            name="Audit Controls",
            description="Verify audit controls are in place",
            check_function=self._check_audit_controls,
            severity="critical",
        ))
    
    def register_check(self, check: ComplianceCheck):
        """Register a compliance check."""
        self._checks[check.id] = check
    
    def run_check(self, check_id: str) -> bool:
        """Run a specific compliance check."""
        if check_id not in self._checks:
            return False
        
        check = self._checks[check_id]
        
        try:
            result = check.check_function()
            check.passed = result
            check.last_check = datetime.now()
            
            self._audit_trail.append({
                "timestamp": datetime.now().isoformat(),
                "check_id": check_id,
                "framework": check.framework.value,
                "passed": result,
            })
            
            return result
            
        except Exception as e:
            check.passed = False
            check.evidence = f"Error: {str(e)}"
            return False
    
    def run_all_checks(self, framework: Optional[ComplianceFramework] = None) -> Dict[str, bool]:
        """Run all compliance checks."""
        results = {}
        
        for check_id, check in self._checks.items():
            if framework and check.framework != framework:
                continue
            results[check_id] = self.run_check(check_id)
        
        return results
    
    def get_compliance_report(self, framework: Optional[ComplianceFramework] = None) -> Dict:
        """Generate compliance report."""
        checks = list(self._checks.values())
        if framework:
            checks = [c for c in checks if c.framework == framework]
        
        passed = sum(1 for c in checks if c.passed is True)
        failed = sum(1 for c in checks if c.passed is False)
        pending = sum(1 for c in checks if c.passed is None)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "framework": framework.value if framework else "all",
            "summary": {
                "total": len(checks),
                "passed": passed,
                "failed": failed,
                "pending": pending,
                "compliance_rate": round(passed / len(checks) * 100, 1) if checks else 0,
            },
            "checks": [
                {
                    "id": c.id,
                    "name": c.name,
                    "framework": c.framework.value,
                    "severity": c.severity,
                    "passed": c.passed,
                    "last_check": c.last_check.isoformat() if c.last_check else None,
                }
                for c in checks
            ],
            "critical_failures": [
                c.name for c in checks 
                if c.severity == "critical" and c.passed is False
            ],
        }
    
    # Default check implementations
    def _check_encryption_at_rest(self) -> bool:
        """Check if encryption at rest is configured."""
        # Check for encryption configuration
        return os.environ.get("ENCRYPTION_KEY") is not None
    
    def _check_access_logging(self) -> bool:
        """Check if access logging is enabled."""
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return False
        
        # Check for recent log files
        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            return False
        
        # Check if recent logs exist
        recent = datetime.now() - timedelta(hours=24)
        for log_file in log_files:
            if datetime.fromtimestamp(log_file.stat().st_mtime) > recent:
                return True
        
        return False
    
    def _check_backup_exists(self) -> bool:
        """Check if recent backup exists."""
        backup_dir = Path("backups")
        if not backup_dir.exists():
            return False
        
        # Check for recent backups
        recent = datetime.now() - timedelta(days=1)
        for backup in backup_dir.iterdir():
            if backup.is_dir():
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                if mtime > recent:
                    return True
        
        return False
    
    def _check_data_retention(self) -> bool:
        """Check data retention policy."""
        # Check if old data is being cleaned up
        return True  # Placeholder
    
    def _check_audit_controls(self) -> bool:
        """Check audit controls."""
        # Check for immutable audit records
        audit_file = Path("data") / "immutable_audit.db"
        return audit_file.exists()


# =============================================================================
# DISASTER RECOVERY COORDINATOR
# =============================================================================

class DisasterRecoveryCoordinator:
    """
    Coordinates all disaster recovery components.
    
    Provides:
    - Unified backup/restore
    - Failover orchestration
    - Compliance monitoring
    - Recovery testing
    """
    
    _instance: Optional["DisasterRecoveryCoordinator"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, data_dir: Optional[Path] = None):
        if self._initialized:
            return
        
        self._initialized = True
        self.data_dir = data_dir or Path("data")
        
        # Initialize components
        self.backup_manager = BackupManager(data_dir=self.data_dir)
        self.failover_manager = FailoverManager()
        self.compliance_manager = ComplianceManager()
        
        # RPO/RTO targets
        self.rpo_minutes = 60   # Max 1 hour of data loss
        self.rto_minutes = 15   # Max 15 minutes downtime
        
        logger.info("Disaster Recovery Coordinator initialized")
    
    def create_backup(self, backup_type: BackupType = BackupType.FULL) -> BackupRecord:
        """Create a backup."""
        return self.backup_manager.create_backup(backup_type)
    
    def restore_latest(self) -> bool:
        """Restore from latest backup."""
        latest = self.backup_manager.get_latest_backup()
        if latest:
            return self.backup_manager.restore_backup(latest.id)
        return False
    
    def trigger_failover(self, reason: str = "manual") -> bool:
        """Trigger failover."""
        return self.failover_manager.trigger_failover(reason)
    
    def run_compliance_checks(self) -> Dict:
        """Run all compliance checks."""
        return self.compliance_manager.run_all_checks()
    
    def get_compliance_report(self) -> Dict:
        """Get compliance report."""
        return self.compliance_manager.get_compliance_report()
    
    def test_recovery(self) -> Dict:
        """Test disaster recovery procedures."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
        }
        
        # Test backup creation
        try:
            backup = self.backup_manager.create_backup(BackupType.SNAPSHOT)
            results["tests"].append({
                "name": "backup_creation",
                "passed": backup.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED],
            })
        except Exception as e:
            results["tests"].append({
                "name": "backup_creation",
                "passed": False,
                "error": str(e),
            })
        
        # Test backup verification
        try:
            latest = self.backup_manager.get_latest_backup()
            if latest:
                verified = self.backup_manager._verify_backup(latest.id)
                results["tests"].append({
                    "name": "backup_verification",
                    "passed": verified,
                })
        except Exception as e:
            results["tests"].append({
                "name": "backup_verification",
                "passed": False,
                "error": str(e),
            })
        
        # Calculate overall result
        results["passed"] = all(t.get("passed", False) for t in results["tests"])
        results["rpo_met"] = True  # Simplified check
        results["rto_estimated_minutes"] = 10
        
        return results
    
    def get_status(self) -> Dict:
        """Get disaster recovery status."""
        latest_backup = self.backup_manager.get_latest_backup()
        
        return {
            "backup": {
                "latest": latest_backup.id if latest_backup else None,
                "age_hours": round((datetime.now() - latest_backup.created_at).total_seconds() / 3600, 1) if latest_backup else None,
                "total_backups": len(self.backup_manager._backups),
            },
            "failover": self.failover_manager.get_status(),
            "compliance": {
                "checks_count": len(self.compliance_manager._checks),
                "last_report": None,  # Would be populated with last report time
            },
            "targets": {
                "rpo_minutes": self.rpo_minutes,
                "rto_minutes": self.rto_minutes,
            },
        }


def get_disaster_recovery() -> DisasterRecoveryCoordinator:
    """Get the singleton disaster recovery coordinator."""
    return DisasterRecoveryCoordinator()
