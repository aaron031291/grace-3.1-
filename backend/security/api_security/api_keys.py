"""
API Key Management System for GRACE.

Provides:
- API key generation with configurable entropy
- Key scoping (per-endpoint, per-resource)
- Key expiration and rotation
- Usage tracking and quotas
- Key revocation with audit trail
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class APIKeyScope(str, Enum):
    """API key scope levels."""
    FULL_ACCESS = "full_access"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    ENDPOINT_SPECIFIC = "endpoint_specific"
    RESOURCE_SPECIFIC = "resource_specific"


class APIKeyStatus(str, Enum):
    """API key status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    RATE_LIMITED = "rate_limited"
    SUSPENDED = "suspended"


@dataclass
class APIKeyQuota:
    """Quota configuration for an API key."""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    max_request_size_bytes: int = 10 * 1024 * 1024
    max_response_size_bytes: int = 50 * 1024 * 1024
    burst_allowance: int = 10


@dataclass
class APIKeyUsage:
    """Usage tracking for an API key."""
    total_requests: int = 0
    requests_this_minute: int = 0
    requests_this_hour: int = 0
    requests_this_day: int = 0
    last_request_at: Optional[datetime] = None
    last_minute_reset: Optional[datetime] = None
    last_hour_reset: Optional[datetime] = None
    last_day_reset: Optional[datetime] = None
    bytes_transferred: int = 0
    errors_count: int = 0


@dataclass
class APIKey:
    """API key data structure."""
    key_id: str
    key_hash: str
    name: str
    description: str
    owner_id: str
    scope: APIKeyScope
    status: APIKeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_rotated_at: Optional[datetime]
    allowed_endpoints: Set[str] = field(default_factory=set)
    allowed_resources: Set[str] = field(default_factory=set)
    allowed_ips: Set[str] = field(default_factory=set)
    quota: APIKeyQuota = field(default_factory=APIKeyQuota)
    usage: APIKeyUsage = field(default_factory=APIKeyUsage)
    metadata: Dict[str, Any] = field(default_factory=dict)
    revocation_reason: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


class APIKeyManager:
    """
    Manages API keys with full lifecycle support.
    
    Features:
    - Cryptographically secure key generation
    - Scoped access control
    - Usage tracking and quotas
    - Key rotation and revocation
    - Audit trail integration
    """
    
    def __init__(self, audit_storage=None):
        self._keys: Dict[str, APIKey] = {}
        self._key_hash_index: Dict[str, str] = {}
        self._audit = audit_storage
        self._default_expiry_days = 365
        self._key_prefix = "gk_"
        self._key_entropy_bytes = 32
        
    def _get_audit_storage(self):
        """Lazy load audit storage."""
        if self._audit is None:
            try:
                from backend.genesis.immutable_audit_storage import (
                    get_immutable_audit_storage,
                    ImmutableAuditType
                )
                self._audit = get_immutable_audit_storage()
            except ImportError:
                pass
        return self._audit
    
    def _audit_event(
        self,
        action: str,
        key_id: str,
        actor_id: str,
        details: Optional[Dict] = None,
        severity: str = "info"
    ):
        """Record an audit event for API key operations."""
        audit = self._get_audit_storage()
        if audit:
            try:
                from backend.genesis.immutable_audit_storage import ImmutableAuditType
                audit.record(
                    audit_type=ImmutableAuditType.SECURITY_ALERT,
                    action_description=f"API Key {action}: {key_id}",
                    actor_type="api",
                    actor_id=actor_id,
                    severity=severity,
                    component="api_security.api_keys",
                    action_data={
                        "action": action,
                        "key_id": key_id,
                        "details": details or {}
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to record audit event: {e}")
        
        logger.info(f"[API-KEY] {action}: key_id={key_id}, actor={actor_id}")
    
    def generate_key(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        scope: APIKeyScope = APIKeyScope.READ_ONLY,
        expires_in_days: Optional[int] = None,
        allowed_endpoints: Optional[Set[str]] = None,
        allowed_resources: Optional[Set[str]] = None,
        allowed_ips: Optional[Set[str]] = None,
        quota: Optional[APIKeyQuota] = None,
        entropy_bytes: Optional[int] = None
    ) -> tuple[str, APIKey]:
        """
        Generate a new API key.
        
        Args:
            name: Human-readable name for the key
            owner_id: ID of the key owner
            description: Description of key purpose
            scope: Access scope for the key
            expires_in_days: Days until expiration (None = use default)
            allowed_endpoints: Set of allowed endpoint patterns
            allowed_resources: Set of allowed resource IDs
            allowed_ips: Set of allowed IP addresses
            quota: Quota configuration
            entropy_bytes: Entropy bytes for key generation (default 32)
            
        Returns:
            Tuple of (raw_key, APIKey object)
        """
        entropy = entropy_bytes or self._key_entropy_bytes
        raw_key = self._key_prefix + secrets.token_urlsafe(entropy)
        key_hash = self._hash_key(raw_key)
        key_id = f"apk_{secrets.token_hex(8)}"
        
        now = datetime.utcnow()
        expiry_days = expires_in_days if expires_in_days is not None else self._default_expiry_days
        expires_at = now + timedelta(days=expiry_days) if expiry_days > 0 else None
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            description=description,
            owner_id=owner_id,
            scope=scope,
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            expires_at=expires_at,
            last_rotated_at=None,
            allowed_endpoints=allowed_endpoints or set(),
            allowed_resources=allowed_resources or set(),
            allowed_ips=allowed_ips or set(),
            quota=quota or APIKeyQuota(),
            usage=APIKeyUsage(),
            metadata={}
        )
        
        self._keys[key_id] = api_key
        self._key_hash_index[key_hash] = key_id
        
        self._audit_event(
            action="created",
            key_id=key_id,
            actor_id=owner_id,
            details={
                "name": name,
                "scope": scope.value,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        )
        
        return raw_key, api_key
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def validate_key(
        self,
        raw_key: str,
        endpoint: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> tuple[bool, Optional[APIKey], Optional[str]]:
        """
        Validate an API key.
        
        Args:
            raw_key: The raw API key string
            endpoint: The endpoint being accessed
            resource_id: The resource being accessed
            client_ip: The client's IP address
            
        Returns:
            Tuple of (is_valid, api_key, error_message)
        """
        if not raw_key:
            return False, None, "API key required"
        
        key_hash = self._hash_key(raw_key)
        key_id = self._key_hash_index.get(key_hash)
        
        if not key_id:
            return False, None, "Invalid API key"
        
        api_key = self._keys.get(key_id)
        if not api_key:
            return False, None, "API key not found"
        
        if api_key.status == APIKeyStatus.REVOKED:
            return False, api_key, "API key has been revoked"
        
        if api_key.status == APIKeyStatus.SUSPENDED:
            return False, api_key, "API key is suspended"
        
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            api_key.status = APIKeyStatus.EXPIRED
            return False, api_key, "API key has expired"
        
        if api_key.allowed_ips and client_ip and client_ip not in api_key.allowed_ips:
            return False, api_key, "IP address not allowed"
        
        if api_key.scope == APIKeyScope.ENDPOINT_SPECIFIC:
            if endpoint and api_key.allowed_endpoints:
                if not self._match_endpoint(endpoint, api_key.allowed_endpoints):
                    return False, api_key, "Endpoint not allowed for this key"
        
        if api_key.scope == APIKeyScope.RESOURCE_SPECIFIC:
            if resource_id and api_key.allowed_resources:
                if resource_id not in api_key.allowed_resources:
                    return False, api_key, "Resource not allowed for this key"
        
        quota_ok, quota_error = self._check_quota(api_key)
        if not quota_ok:
            return False, api_key, quota_error
        
        self._record_usage(api_key)
        
        return True, api_key, None
    
    def _match_endpoint(self, endpoint: str, allowed: Set[str]) -> bool:
        """Check if an endpoint matches allowed patterns."""
        for pattern in allowed:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                if endpoint.startswith(pattern[:-1]):
                    return True
            elif pattern == endpoint:
                return True
        return False
    
    def _check_quota(self, api_key: APIKey) -> tuple[bool, Optional[str]]:
        """Check if the API key is within quota limits."""
        now = datetime.utcnow()
        usage = api_key.usage
        quota = api_key.quota
        
        if usage.last_minute_reset is None or (now - usage.last_minute_reset).seconds >= 60:
            usage.requests_this_minute = 0
            usage.last_minute_reset = now
        
        if usage.last_hour_reset is None or (now - usage.last_hour_reset).seconds >= 3600:
            usage.requests_this_hour = 0
            usage.last_hour_reset = now
        
        if usage.last_day_reset is None or (now - usage.last_day_reset).days >= 1:
            usage.requests_this_day = 0
            usage.last_day_reset = now
        
        if usage.requests_this_minute >= quota.requests_per_minute + quota.burst_allowance:
            return False, "Rate limit exceeded (per minute)"
        
        if usage.requests_this_hour >= quota.requests_per_hour:
            return False, "Rate limit exceeded (per hour)"
        
        if usage.requests_this_day >= quota.requests_per_day:
            return False, "Rate limit exceeded (per day)"
        
        return True, None
    
    def _record_usage(self, api_key: APIKey):
        """Record API key usage."""
        now = datetime.utcnow()
        api_key.usage.total_requests += 1
        api_key.usage.requests_this_minute += 1
        api_key.usage.requests_this_hour += 1
        api_key.usage.requests_this_day += 1
        api_key.usage.last_request_at = now
    
    def rotate_key(
        self,
        key_id: str,
        actor_id: str,
        expires_in_days: Optional[int] = None
    ) -> tuple[Optional[str], Optional[APIKey]]:
        """
        Rotate an API key, generating a new key value.
        
        Args:
            key_id: ID of the key to rotate
            actor_id: ID of the actor performing rotation
            expires_in_days: New expiry period
            
        Returns:
            Tuple of (new_raw_key, updated_api_key)
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return None, None
        
        old_hash = api_key.key_hash
        if old_hash in self._key_hash_index:
            del self._key_hash_index[old_hash]
        
        new_raw_key = self._key_prefix + secrets.token_urlsafe(self._key_entropy_bytes)
        new_hash = self._hash_key(new_raw_key)
        
        api_key.key_hash = new_hash
        api_key.last_rotated_at = datetime.utcnow()
        
        if expires_in_days is not None:
            api_key.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        self._key_hash_index[new_hash] = key_id
        
        self._audit_event(
            action="rotated",
            key_id=key_id,
            actor_id=actor_id,
            details={
                "new_expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None
            }
        )
        
        return new_raw_key, api_key
    
    def revoke_key(
        self,
        key_id: str,
        actor_id: str,
        reason: str
    ) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: ID of the key to revoke
            actor_id: ID of the actor performing revocation
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        
        api_key.status = APIKeyStatus.REVOKED
        api_key.revocation_reason = reason
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_by = actor_id
        
        self._audit_event(
            action="revoked",
            key_id=key_id,
            actor_id=actor_id,
            details={"reason": reason},
            severity="warning"
        )
        
        return True
    
    def suspend_key(self, key_id: str, actor_id: str, reason: str) -> bool:
        """Temporarily suspend an API key."""
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        
        api_key.status = APIKeyStatus.SUSPENDED
        api_key.metadata["suspension_reason"] = reason
        api_key.metadata["suspended_at"] = datetime.utcnow().isoformat()
        api_key.metadata["suspended_by"] = actor_id
        
        self._audit_event(
            action="suspended",
            key_id=key_id,
            actor_id=actor_id,
            details={"reason": reason},
            severity="warning"
        )
        
        return True
    
    def reactivate_key(self, key_id: str, actor_id: str) -> bool:
        """Reactivate a suspended API key."""
        api_key = self._keys.get(key_id)
        if not api_key or api_key.status != APIKeyStatus.SUSPENDED:
            return False
        
        api_key.status = APIKeyStatus.ACTIVE
        api_key.metadata.pop("suspension_reason", None)
        api_key.metadata.pop("suspended_at", None)
        api_key.metadata.pop("suspended_by", None)
        
        self._audit_event(
            action="reactivated",
            key_id=key_id,
            actor_id=actor_id
        )
        
        return True
    
    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key info (without the hash)."""
        api_key = self._keys.get(key_id)
        if not api_key:
            return None
        
        return {
            "key_id": api_key.key_id,
            "name": api_key.name,
            "description": api_key.description,
            "owner_id": api_key.owner_id,
            "scope": api_key.scope.value,
            "status": api_key.status.value,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "last_rotated_at": api_key.last_rotated_at.isoformat() if api_key.last_rotated_at else None,
            "allowed_endpoints": list(api_key.allowed_endpoints),
            "allowed_resources": list(api_key.allowed_resources),
            "quota": asdict(api_key.quota),
            "usage": {
                "total_requests": api_key.usage.total_requests,
                "requests_this_day": api_key.usage.requests_this_day,
                "last_request_at": api_key.usage.last_request_at.isoformat() if api_key.usage.last_request_at else None
            }
        }
    
    def list_keys(
        self,
        owner_id: Optional[str] = None,
        status: Optional[APIKeyStatus] = None
    ) -> List[Dict[str, Any]]:
        """List API keys with optional filters."""
        results = []
        for key_id, api_key in self._keys.items():
            if owner_id and api_key.owner_id != owner_id:
                continue
            if status and api_key.status != status:
                continue
            results.append(self.get_key_info(key_id))
        return results
    
    def update_quota(
        self,
        key_id: str,
        actor_id: str,
        quota: APIKeyQuota
    ) -> bool:
        """Update the quota for an API key."""
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        
        old_quota = asdict(api_key.quota)
        api_key.quota = quota
        
        self._audit_event(
            action="quota_updated",
            key_id=key_id,
            actor_id=actor_id,
            details={
                "old_quota": old_quota,
                "new_quota": asdict(quota)
            }
        )
        
        return True
    
    def update_scopes(
        self,
        key_id: str,
        actor_id: str,
        scope: Optional[APIKeyScope] = None,
        allowed_endpoints: Optional[Set[str]] = None,
        allowed_resources: Optional[Set[str]] = None,
        allowed_ips: Optional[Set[str]] = None
    ) -> bool:
        """Update the scope and permissions for an API key."""
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        
        changes = {}
        
        if scope is not None:
            changes["scope"] = {"old": api_key.scope.value, "new": scope.value}
            api_key.scope = scope
        
        if allowed_endpoints is not None:
            changes["allowed_endpoints"] = {
                "old": list(api_key.allowed_endpoints),
                "new": list(allowed_endpoints)
            }
            api_key.allowed_endpoints = allowed_endpoints
        
        if allowed_resources is not None:
            changes["allowed_resources"] = {
                "old": list(api_key.allowed_resources),
                "new": list(allowed_resources)
            }
            api_key.allowed_resources = allowed_resources
        
        if allowed_ips is not None:
            changes["allowed_ips"] = {
                "old": list(api_key.allowed_ips),
                "new": list(allowed_ips)
            }
            api_key.allowed_ips = allowed_ips
        
        self._audit_event(
            action="scopes_updated",
            key_id=key_id,
            actor_id=actor_id,
            details=changes
        )
        
        return True


_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get the API key manager singleton."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
