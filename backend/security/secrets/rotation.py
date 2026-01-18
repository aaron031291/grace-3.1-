"""
Automated Secret Rotation for GRACE

Provides:
- Configurable rotation policies per secret type
- Pre-rotation hooks for validation
- Post-rotation hooks for propagation
- Rollback on rotation failure
- Audit trail of all rotations
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class RotationStatus(str, Enum):
    """Status of a rotation operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    PROPAGATING = "propagating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SecretType(str, Enum):
    """Types of secrets with different rotation policies."""
    DATABASE_PASSWORD = "database_password"
    API_KEY = "api_key"
    ENCRYPTION_KEY = "encryption_key"
    SERVICE_ACCOUNT = "service_account"
    CERTIFICATE = "certificate"
    OAUTH_SECRET = "oauth_secret"
    SIGNING_KEY = "signing_key"
    SSH_KEY = "ssh_key"
    GENERIC = "generic"


@dataclass
class RotationPolicy:
    """
    Rotation policy for a secret type.
    
    Defines when and how secrets should be rotated.
    """
    secret_type: SecretType
    rotation_interval: timedelta = field(default_factory=lambda: timedelta(days=90))
    grace_period: timedelta = field(default_factory=lambda: timedelta(hours=24))
    max_versions_to_keep: int = 5
    auto_rollback_on_failure: bool = True
    require_validation: bool = True
    notify_before_rotation: timedelta = field(default_factory=lambda: timedelta(days=7))
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "secret_type": self.secret_type.value,
            "rotation_interval_days": self.rotation_interval.days,
            "grace_period_hours": self.grace_period.total_seconds() / 3600,
            "max_versions_to_keep": self.max_versions_to_keep,
            "auto_rollback_on_failure": self.auto_rollback_on_failure,
            "require_validation": self.require_validation,
            "notify_before_days": self.notify_before_rotation.days,
            "enabled": self.enabled
        }


@dataclass
class RotationRecord:
    """Record of a rotation operation."""
    rotation_id: str
    secret_name: str
    secret_type: SecretType
    status: RotationStatus
    old_version: str
    new_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    rolled_back: bool = False
    rollback_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging."""
        return {
            "rotation_id": self.rotation_id,
            "secret_name": self.secret_name,
            "secret_type": self.secret_type.value,
            "status": self.status.value,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "rolled_back": self.rolled_back,
            "rollback_reason": self.rollback_reason,
            "metadata": self.metadata
        }


@dataclass
class SecretVersion:
    """A version of a secret."""
    version_id: str
    value: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    active: bool = True
    rotation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RotationHook(ABC):
    """Abstract base class for rotation hooks."""
    
    @abstractmethod
    def execute(
        self,
        secret_name: str,
        old_value: str,
        new_value: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Execute the hook.
        
        Returns:
            True if hook succeeded, False otherwise
        """
        pass


class PreRotationValidator(RotationHook):
    """
    Pre-rotation hook for validating new secret value.
    
    Checks that the new secret is valid before completing rotation.
    """
    
    def __init__(self, validator_fn: Callable[[str, str], bool]):
        """
        Args:
            validator_fn: Function that takes (secret_name, new_value) and returns bool
        """
        self._validator_fn = validator_fn
    
    def execute(
        self,
        secret_name: str,
        old_value: str,
        new_value: str,
        context: Dict[str, Any]
    ) -> bool:
        try:
            return self._validator_fn(secret_name, new_value)
        except Exception as e:
            logger.error(f"Pre-rotation validation failed for {secret_name}: {e}")
            return False


class PostRotationPropagator(RotationHook):
    """
    Post-rotation hook for propagating new secret.
    
    Updates dependent services/systems with the new secret value.
    """
    
    def __init__(self, propagator_fn: Callable[[str, str], bool]):
        """
        Args:
            propagator_fn: Function that takes (secret_name, new_value) and returns bool
        """
        self._propagator_fn = propagator_fn
    
    def execute(
        self,
        secret_name: str,
        old_value: str,
        new_value: str,
        context: Dict[str, Any]
    ) -> bool:
        try:
            return self._propagator_fn(secret_name, new_value)
        except Exception as e:
            logger.error(f"Post-rotation propagation failed for {secret_name}: {e}")
            return False


class SecretRotator:
    """
    Core secret rotation engine.
    
    Handles the complete rotation lifecycle:
    1. Generate new secret value
    2. Validate new secret (pre-rotation hooks)
    3. Store new version
    4. Propagate to dependent systems (post-rotation hooks)
    5. Update active version
    6. Rollback on failure
    """
    
    def __init__(
        self,
        vault=None,
        audit_storage=None
    ):
        """
        Initialize the rotator.
        
        Args:
            vault: SecretsVault instance for secret storage
            audit_storage: ImmutableAuditStorage for audit logging
        """
        self._vault = vault
        self._audit = audit_storage
        
        self._policies: Dict[SecretType, RotationPolicy] = {}
        self._secret_types: Dict[str, SecretType] = {}
        
        self._pre_hooks: Dict[str, List[RotationHook]] = {}
        self._post_hooks: Dict[str, List[RotationHook]] = {}
        
        self._generators: Dict[SecretType, Callable[[], str]] = {}
        
        self._rotation_history: List[RotationRecord] = []
        self._active_rotations: Dict[str, RotationRecord] = {}
        
        self._lock = threading.Lock()
        
        self._initialize_default_policies()
        self._initialize_default_generators()
    
    def _initialize_default_policies(self):
        """Set up default rotation policies."""
        self._policies = {
            SecretType.DATABASE_PASSWORD: RotationPolicy(
                secret_type=SecretType.DATABASE_PASSWORD,
                rotation_interval=timedelta(days=90),
                require_validation=True
            ),
            SecretType.API_KEY: RotationPolicy(
                secret_type=SecretType.API_KEY,
                rotation_interval=timedelta(days=365),
                require_validation=True
            ),
            SecretType.ENCRYPTION_KEY: RotationPolicy(
                secret_type=SecretType.ENCRYPTION_KEY,
                rotation_interval=timedelta(days=365),
                require_validation=True,
                max_versions_to_keep=10
            ),
            SecretType.CERTIFICATE: RotationPolicy(
                secret_type=SecretType.CERTIFICATE,
                rotation_interval=timedelta(days=365),
                notify_before_rotation=timedelta(days=30)
            ),
            SecretType.OAUTH_SECRET: RotationPolicy(
                secret_type=SecretType.OAUTH_SECRET,
                rotation_interval=timedelta(days=180)
            ),
            SecretType.GENERIC: RotationPolicy(
                secret_type=SecretType.GENERIC,
                rotation_interval=timedelta(days=90)
            )
        }
    
    def _initialize_default_generators(self):
        """Set up default secret generators."""
        import secrets
        import string
        
        def generate_password(length: int = 32) -> str:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        
        def generate_api_key() -> str:
            return f"grace_{secrets.token_urlsafe(32)}"
        
        def generate_encryption_key() -> str:
            import base64
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        self._generators = {
            SecretType.DATABASE_PASSWORD: generate_password,
            SecretType.API_KEY: generate_api_key,
            SecretType.ENCRYPTION_KEY: generate_encryption_key,
            SecretType.OAUTH_SECRET: lambda: secrets.token_urlsafe(48),
            SecretType.GENERIC: lambda: secrets.token_urlsafe(32)
        }
    
    def set_vault(self, vault):
        """Set the secrets vault."""
        self._vault = vault
    
    def set_audit_storage(self, audit_storage):
        """Set the audit storage."""
        self._audit = audit_storage
    
    def register_policy(self, policy: RotationPolicy):
        """Register a rotation policy for a secret type."""
        self._policies[policy.secret_type] = policy
        logger.info(f"Registered rotation policy for {policy.secret_type.value}")
    
    def register_secret_type(self, secret_name: str, secret_type: SecretType):
        """Register a secret's type for policy lookup."""
        self._secret_types[secret_name] = secret_type
    
    def register_generator(
        self,
        secret_type: SecretType,
        generator: Callable[[], str]
    ):
        """Register a custom secret generator."""
        self._generators[secret_type] = generator
    
    def add_pre_rotation_hook(
        self,
        secret_name: str,
        hook: RotationHook
    ):
        """Add a pre-rotation validation hook."""
        if secret_name not in self._pre_hooks:
            self._pre_hooks[secret_name] = []
        self._pre_hooks[secret_name].append(hook)
    
    def add_post_rotation_hook(
        self,
        secret_name: str,
        hook: RotationHook
    ):
        """Add a post-rotation propagation hook."""
        if secret_name not in self._post_hooks:
            self._post_hooks[secret_name] = []
        self._post_hooks[secret_name].append(hook)
    
    def rotate(
        self,
        secret_name: str,
        new_value: Optional[str] = None,
        force: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RotationRecord:
        """
        Rotate a secret.
        
        Args:
            secret_name: Name of the secret to rotate
            new_value: Optional new value (generated if not provided)
            force: Force rotation even if not due
            metadata: Optional metadata for the rotation record
            
        Returns:
            RotationRecord with rotation details
        """
        if not self._vault:
            raise RuntimeError("Vault not configured for rotation")
        
        secret_type = self._secret_types.get(secret_name, SecretType.GENERIC)
        policy = self._policies.get(secret_type, self._policies[SecretType.GENERIC])
        
        rotation_id = f"ROT-{uuid.uuid4().hex[:12]}"
        old_version = self._get_current_version(secret_name)
        new_version = f"v{int(time.time())}"
        
        record = RotationRecord(
            rotation_id=rotation_id,
            secret_name=secret_name,
            secret_type=secret_type,
            status=RotationStatus.PENDING,
            old_version=old_version,
            new_version=new_version,
            started_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._active_rotations[secret_name] = record
        
        try:
            old_value = self._vault.get(secret_name)
            if old_value is None and not force:
                raise ValueError(f"Secret {secret_name} does not exist")
            
            record.status = RotationStatus.IN_PROGRESS
            
            if new_value is None:
                generator = self._generators.get(secret_type)
                if generator:
                    new_value = generator()
                else:
                    import secrets as sec
                    new_value = sec.token_urlsafe(32)
            
            if policy.require_validation:
                record.status = RotationStatus.VALIDATING
                if not self._run_pre_hooks(secret_name, old_value or "", new_value):
                    raise ValueError("Pre-rotation validation failed")
            
            self._vault.set(
                secret_name,
                new_value,
                metadata={
                    "version": new_version,
                    "rotation_id": rotation_id,
                    "previous_version": old_version
                }
            )
            
            record.status = RotationStatus.PROPAGATING
            if not self._run_post_hooks(secret_name, old_value or "", new_value):
                if policy.auto_rollback_on_failure:
                    self._rollback(secret_name, old_value, record)
                    raise ValueError("Post-rotation propagation failed - rolled back")
            
            record.status = RotationStatus.COMPLETED
            record.completed_at = datetime.utcnow()
            
            self._audit_rotation(record)
            self._cleanup_old_versions(secret_name, policy.max_versions_to_keep)
            
            logger.info(
                f"Successfully rotated secret {secret_name} "
                f"from {old_version} to {new_version}"
            )
            
        except Exception as e:
            record.status = RotationStatus.FAILED
            record.error = str(e)
            record.completed_at = datetime.utcnow()
            
            self._audit_rotation(record)
            logger.error(f"Rotation failed for {secret_name}: {e}")
            raise
        
        finally:
            with self._lock:
                if secret_name in self._active_rotations:
                    del self._active_rotations[secret_name]
                self._rotation_history.append(record)
        
        return record
    
    def _get_current_version(self, secret_name: str) -> str:
        """Get current version of a secret."""
        if self._vault:
            metadata = self._vault.get_metadata(secret_name)
            if metadata:
                return metadata.get("version", "v0")
        return "v0"
    
    def _run_pre_hooks(
        self,
        secret_name: str,
        old_value: str,
        new_value: str
    ) -> bool:
        """Run all pre-rotation hooks."""
        hooks = self._pre_hooks.get(secret_name, [])
        context = {"stage": "pre_rotation"}
        
        for hook in hooks:
            try:
                if not hook.execute(secret_name, old_value, new_value, context):
                    return False
            except Exception as e:
                logger.error(f"Pre-rotation hook failed: {e}")
                return False
        
        return True
    
    def _run_post_hooks(
        self,
        secret_name: str,
        old_value: str,
        new_value: str
    ) -> bool:
        """Run all post-rotation hooks."""
        hooks = self._post_hooks.get(secret_name, [])
        context = {"stage": "post_rotation"}
        
        for hook in hooks:
            try:
                if not hook.execute(secret_name, old_value, new_value, context):
                    return False
            except Exception as e:
                logger.error(f"Post-rotation hook failed: {e}")
                return False
        
        return True
    
    def _rollback(
        self,
        secret_name: str,
        old_value: Optional[str],
        record: RotationRecord
    ):
        """Rollback a failed rotation."""
        if old_value and self._vault:
            try:
                self._vault.set(
                    secret_name,
                    old_value,
                    metadata={
                        "version": record.old_version,
                        "rolled_back_from": record.new_version,
                        "rollback_rotation_id": record.rotation_id
                    }
                )
                record.rolled_back = True
                record.status = RotationStatus.ROLLED_BACK
                logger.info(f"Rolled back secret {secret_name} to {record.old_version}")
            except Exception as e:
                record.rollback_reason = f"Rollback failed: {e}"
                logger.error(f"Rollback failed for {secret_name}: {e}")
    
    def _audit_rotation(self, record: RotationRecord):
        """Log rotation to immutable audit."""
        if not self._audit:
            return
        
        try:
            from genesis.immutable_audit_storage import ImmutableAuditType
            
            self._audit.record(
                audit_type=ImmutableAuditType.SECURITY_ALERT,
                action_description=f"Secret rotation: {record.secret_name}",
                actor_type="system",
                actor_id="secret_rotator",
                component="secrets",
                severity="info" if record.status == RotationStatus.COMPLETED else "warning",
                action_data=record.to_dict(),
                context={
                    "rotation_id": record.rotation_id,
                    "status": record.status.value
                }
            )
        except ImportError:
            logger.debug("Audit storage not available")
        except Exception as e:
            logger.warning(f"Failed to audit rotation: {e}")
    
    def _cleanup_old_versions(self, secret_name: str, max_versions: int):
        """Remove old versions beyond the limit."""
        pass
    
    def get_secrets_due_for_rotation(self) -> List[Dict[str, Any]]:
        """Get list of secrets due for rotation."""
        due_secrets = []
        
        if not self._vault:
            return due_secrets
        
        for secret_name, secret_type in self._secret_types.items():
            policy = self._policies.get(secret_type, self._policies[SecretType.GENERIC])
            
            if not policy.enabled:
                continue
            
            metadata = self._vault.get_metadata(secret_name)
            if not metadata:
                continue
            
            last_rotated_str = metadata.get("last_rotated")
            if last_rotated_str:
                last_rotated = datetime.fromisoformat(last_rotated_str)
            else:
                last_rotated = datetime.fromisoformat(
                    metadata.get("created_at", datetime.utcnow().isoformat())
                )
            
            next_rotation = last_rotated + policy.rotation_interval
            now = datetime.utcnow()
            
            if now >= next_rotation:
                due_secrets.append({
                    "secret_name": secret_name,
                    "secret_type": secret_type.value,
                    "last_rotated": last_rotated.isoformat(),
                    "due_date": next_rotation.isoformat(),
                    "overdue_by": (now - next_rotation).days
                })
            elif now >= next_rotation - policy.notify_before_rotation:
                due_secrets.append({
                    "secret_name": secret_name,
                    "secret_type": secret_type.value,
                    "last_rotated": last_rotated.isoformat(),
                    "due_date": next_rotation.isoformat(),
                    "days_until_due": (next_rotation - now).days,
                    "upcoming": True
                })
        
        return due_secrets
    
    def get_rotation_history(
        self,
        secret_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get rotation history."""
        history = self._rotation_history
        
        if secret_name:
            history = [r for r in history if r.secret_name == secret_name]
        
        history = sorted(history, key=lambda r: r.started_at, reverse=True)
        
        return [r.to_dict() for r in history[:limit]]


class RotationScheduler:
    """
    Background scheduler for automatic secret rotation.
    
    Runs periodic checks and triggers rotation for due secrets.
    """
    
    def __init__(
        self,
        rotator: SecretRotator,
        check_interval: timedelta = timedelta(hours=1)
    ):
        self._rotator = rotator
        self._check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start the rotation scheduler."""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Rotation scheduler started")
    
    def stop(self):
        """Stop the rotation scheduler."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Rotation scheduler stopped")
    
    def _run(self):
        """Main scheduler loop."""
        while self._running:
            try:
                self._check_and_rotate()
            except Exception as e:
                logger.error(f"Rotation check failed: {e}")
            
            self._stop_event.wait(self._check_interval.total_seconds())
    
    def _check_and_rotate(self):
        """Check for due secrets and rotate them."""
        due_secrets = self._rotator.get_secrets_due_for_rotation()
        
        for secret_info in due_secrets:
            if secret_info.get("upcoming"):
                continue
            
            secret_name = secret_info["secret_name"]
            try:
                logger.info(f"Auto-rotating secret: {secret_name}")
                self._rotator.rotate(secret_name, metadata={"auto_rotated": True})
            except Exception as e:
                logger.error(f"Auto-rotation failed for {secret_name}: {e}")


_rotator: Optional[SecretRotator] = None
_scheduler: Optional[RotationScheduler] = None


def get_secret_rotator() -> SecretRotator:
    """Get the secret rotator singleton."""
    global _rotator
    if _rotator is None:
        _rotator = SecretRotator()
    return _rotator


def get_rotation_scheduler() -> RotationScheduler:
    """Get the rotation scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = RotationScheduler(get_secret_rotator())
    return _scheduler
