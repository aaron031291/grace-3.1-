"""
GRACE Zero-Trust Network Security

Provides network-level security controls:
- IP allowlist/blocklist management
- Geo-blocking by country
- Request signing and verification
- Mutual TLS support
- Network security middleware

All network security decisions are logged to the immutable audit system.
"""

import hashlib
import hmac
import ipaddress
import logging
import re
import ssl
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class IPFilterAction(str, Enum):
    """Action to take for IP filter matches."""
    ALLOW = "allow"
    BLOCK = "block"
    CHALLENGE = "challenge"
    LOG = "log"


@dataclass
class IPRule:
    """An IP filter rule."""
    pattern: str  # CIDR notation or single IP
    action: IPFilterAction
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    priority: int = 0
    
    def matches(self, ip: str) -> bool:
        """Check if IP matches this rule."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            if "/" in self.pattern:
                network = ipaddress.ip_network(self.pattern, strict=False)
                return ip_obj in network
            else:
                return ip_obj == ipaddress.ip_address(self.pattern)
        except ValueError:
            return False
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class IPFilter:
    """
    IP allowlist/blocklist management.
    
    Supports:
    - CIDR notation
    - Expiring rules
    - Priority-based matching
    - Default policy
    """
    
    def __init__(
        self,
        default_action: IPFilterAction = IPFilterAction.ALLOW,
    ):
        self._rules: List[IPRule] = []
        self._default_action = default_action
        self._lock = threading.RLock()
        
        # Pre-built sets for fast lookup
        self._blocked_ips: Set[str] = set()
        self._allowed_ips: Set[str] = set()
        
        logger.info("[NETWORK] IP filter initialized")
    
    def add_rule(self, rule: IPRule):
        """Add an IP filter rule."""
        with self._lock:
            self._rules.append(rule)
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            self._rebuild_fast_lookup()
        
        logger.info(f"[NETWORK] Added IP rule: {rule.pattern} -> {rule.action.value}")
    
    def remove_rule(self, pattern: str) -> bool:
        """Remove a rule by pattern."""
        with self._lock:
            before_count = len(self._rules)
            self._rules = [r for r in self._rules if r.pattern != pattern]
            self._rebuild_fast_lookup()
            return len(self._rules) < before_count
    
    def block_ip(
        self,
        ip: str,
        reason: str = "",
        duration: Optional[timedelta] = None,
    ):
        """Block an IP address."""
        expires_at = datetime.utcnow() + duration if duration else None
        
        rule = IPRule(
            pattern=ip,
            action=IPFilterAction.BLOCK,
            reason=reason,
            expires_at=expires_at,
            priority=100,  # High priority
        )
        self.add_rule(rule)
    
    def allow_ip(self, ip: str, reason: str = ""):
        """Explicitly allow an IP address."""
        rule = IPRule(
            pattern=ip,
            action=IPFilterAction.ALLOW,
            reason=reason,
            priority=100,
        )
        self.add_rule(rule)
    
    def check_ip(self, ip: str) -> Tuple[IPFilterAction, Optional[str]]:
        """
        Check an IP against the filter rules.
        
        Returns:
            Tuple of (action, reason)
        """
        # Fast path for known IPs
        if ip in self._blocked_ips:
            return IPFilterAction.BLOCK, "IP blocklisted"
        if ip in self._allowed_ips:
            return IPFilterAction.ALLOW, "IP allowlisted"
        
        with self._lock:
            # Clean expired rules
            self._clean_expired_rules()
            
            # Check rules in priority order
            for rule in self._rules:
                if rule.matches(ip):
                    return rule.action, rule.reason
        
        return self._default_action, "Default policy"
    
    def _rebuild_fast_lookup(self):
        """Rebuild fast lookup sets for single IPs."""
        self._blocked_ips.clear()
        self._allowed_ips.clear()
        
        for rule in self._rules:
            if "/" not in rule.pattern and not rule.is_expired:
                if rule.action == IPFilterAction.BLOCK:
                    self._blocked_ips.add(rule.pattern)
                elif rule.action == IPFilterAction.ALLOW:
                    self._allowed_ips.add(rule.pattern)
    
    def _clean_expired_rules(self):
        """Remove expired rules."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if not r.is_expired]
        if len(self._rules) < before:
            self._rebuild_fast_lookup()
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all active rules."""
        with self._lock:
            self._clean_expired_rules()
            return [
                {
                    "pattern": r.pattern,
                    "action": r.action.value,
                    "reason": r.reason,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                }
                for r in self._rules
            ]


class GeoFilter:
    """
    Geographic IP filtering.
    
    Blocks or challenges requests from specific countries.
    """
    
    def __init__(
        self,
        blocked_countries: Optional[Set[str]] = None,
        allowed_countries: Optional[Set[str]] = None,
        challenge_countries: Optional[Set[str]] = None,
        default_action: IPFilterAction = IPFilterAction.ALLOW,
    ):
        self._blocked = blocked_countries or set()
        self._allowed = allowed_countries or set()
        self._challenge = challenge_countries or set()
        self._default = default_action
        
        self._geoip_db = None
        self._initialize_geoip()
        
        logger.info("[NETWORK] Geo filter initialized")
    
    def _initialize_geoip(self):
        """Initialize GeoIP database."""
        try:
            import geoip2.database
            
            # Try common locations
            db_paths = [
                "/usr/share/GeoIP/GeoLite2-Country.mmdb",
                "data/GeoLite2-Country.mmdb",
                "GeoLite2-Country.mmdb",
            ]
            
            for path in db_paths:
                try:
                    self._geoip_db = geoip2.database.Reader(path)
                    logger.info(f"[NETWORK] GeoIP database loaded from {path}")
                    break
                except FileNotFoundError:
                    continue
            
            if not self._geoip_db:
                logger.warning("[NETWORK] GeoIP database not found")
                
        except ImportError:
            logger.warning("[NETWORK] geoip2 library not installed")
    
    def get_country(self, ip: str) -> Optional[str]:
        """Get country code for an IP address."""
        if not self._geoip_db:
            return None
        
        try:
            response = self._geoip_db.country(ip)
            return response.country.iso_code
        except Exception:
            return None
    
    def check_ip(self, ip: str) -> Tuple[IPFilterAction, Optional[str]]:
        """Check an IP against geo rules."""
        country = self.get_country(ip)
        
        if not country:
            return self._default, "Unknown country"
        
        if country in self._blocked:
            return IPFilterAction.BLOCK, f"Country blocked: {country}"
        
        if country in self._challenge:
            return IPFilterAction.CHALLENGE, f"Country requires challenge: {country}"
        
        if self._allowed and country not in self._allowed:
            return IPFilterAction.BLOCK, f"Country not in allowlist: {country}"
        
        return IPFilterAction.ALLOW, f"Country allowed: {country}"
    
    def block_country(self, country_code: str):
        """Add a country to blocklist."""
        self._blocked.add(country_code.upper())
        logger.info(f"[NETWORK] Blocked country: {country_code}")
    
    def unblock_country(self, country_code: str):
        """Remove a country from blocklist."""
        self._blocked.discard(country_code.upper())
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "blocked_countries": list(self._blocked),
            "allowed_countries": list(self._allowed),
            "challenge_countries": list(self._challenge),
            "default_action": self._default.value,
        }


class RequestSigner:
    """
    Request signing with HMAC-SHA256.
    
    Signs outgoing requests for authentication.
    """
    
    def __init__(
        self,
        secret_key: bytes,
        algorithm: str = "sha256",
        include_timestamp: bool = True,
        timestamp_tolerance: int = 300,  # 5 minutes
    ):
        self._secret = secret_key
        self._algorithm = algorithm
        self._include_timestamp = include_timestamp
        self._tolerance = timestamp_tolerance
    
    def sign_request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        timestamp: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Generate signature headers for a request.
        
        Returns:
            Dictionary of headers to add to request
        """
        timestamp = timestamp or int(time.time())
        
        # Build canonical request
        canonical = self._build_canonical_request(
            method=method,
            path=path,
            body=body,
            headers=headers,
            timestamp=timestamp,
        )
        
        # Generate signature
        signature = hmac.new(
            self._secret,
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        result = {
            "X-Signature": signature,
            "X-Signature-Algorithm": f"HMAC-{self._algorithm.upper()}",
        }
        
        if self._include_timestamp:
            result["X-Signature-Timestamp"] = str(timestamp)
        
        return result
    
    def _build_canonical_request(
        self,
        method: str,
        path: str,
        body: Optional[bytes],
        headers: Optional[Dict[str, str]],
        timestamp: int,
    ) -> str:
        """Build canonical request string for signing."""
        parts = [
            method.upper(),
            path,
        ]
        
        if self._include_timestamp:
            parts.append(str(timestamp))
        
        if body:
            body_hash = hashlib.sha256(body).hexdigest()
            parts.append(body_hash)
        
        return "\n".join(parts)


class RequestVerifier:
    """
    Request signature verification.
    
    Verifies incoming signed requests.
    """
    
    def __init__(
        self,
        secret_key: bytes,
        timestamp_tolerance: int = 300,
    ):
        self._secret = secret_key
        self._tolerance = timestamp_tolerance
        self._used_nonces: Dict[str, datetime] = {}
        self._lock = threading.RLock()
    
    def verify_request(
        self,
        method: str,
        path: str,
        signature: str,
        timestamp: Optional[int] = None,
        body: Optional[bytes] = None,
        nonce: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a request signature.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check timestamp
        if timestamp:
            now = int(time.time())
            if abs(now - timestamp) > self._tolerance:
                return False, "Request timestamp expired"
        
        # Check nonce for replay prevention
        if nonce:
            with self._lock:
                if nonce in self._used_nonces:
                    return False, "Nonce already used (replay detected)"
                
                self._used_nonces[nonce] = datetime.utcnow()
                self._clean_old_nonces()
        
        # Build expected signature
        parts = [method.upper(), path]
        if timestamp:
            parts.append(str(timestamp))
        if body:
            parts.append(hashlib.sha256(body).hexdigest())
        
        canonical = "\n".join(parts)
        
        expected = hmac.new(
            self._secret,
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        
        # Constant-time comparison
        if hmac.compare_digest(signature, expected):
            return True, None
        else:
            return False, "Invalid signature"
    
    def _clean_old_nonces(self):
        """Remove old nonces beyond tolerance window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self._tolerance * 2)
        self._used_nonces = {
            k: v for k, v in self._used_nonces.items() if v > cutoff
        }


@dataclass
class MTLSConfig:
    """Mutual TLS configuration."""
    enabled: bool = False
    ca_cert_path: Optional[str] = None
    server_cert_path: Optional[str] = None
    server_key_path: Optional[str] = None
    client_cert_required: bool = True
    verify_client_cert: bool = True
    allowed_client_subjects: Optional[List[str]] = None
    
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for mTLS."""
        if not self.enabled:
            return None
        
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            # Load server certificate
            if self.server_cert_path and self.server_key_path:
                context.load_cert_chain(
                    self.server_cert_path,
                    self.server_key_path,
                )
            
            # Load CA for client verification
            if self.ca_cert_path:
                context.load_verify_locations(self.ca_cert_path)
            
            if self.client_cert_required:
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                context.verify_mode = ssl.CERT_OPTIONAL
            
            # Security settings
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers("ECDHE+AESGCM:DHE+AESGCM:ECDHE+CHACHA20:DHE+CHACHA20")
            
            logger.info("[NETWORK] mTLS SSL context created")
            return context
            
        except Exception as e:
            logger.error(f"[NETWORK] Failed to create mTLS context: {e}")
            return None


class NetworkSecurityMiddleware:
    """
    FastAPI middleware combining all network security checks.
    """
    
    def __init__(
        self,
        ip_filter: Optional[IPFilter] = None,
        geo_filter: Optional[GeoFilter] = None,
        request_verifier: Optional[RequestVerifier] = None,
        enable_audit: bool = True,
    ):
        self._ip_filter = ip_filter or IPFilter()
        self._geo_filter = geo_filter
        self._verifier = request_verifier
        self._enable_audit = enable_audit
        
        logger.info("[NETWORK] Network security middleware initialized")
    
    async def __call__(self, request, call_next):
        """Process request through network security checks."""
        from fastapi import Response
        from starlette.requests import Request
        
        # Get client IP
        ip = self._get_client_ip(request)
        
        # IP filter check
        action, reason = self._ip_filter.check_ip(ip)
        
        if action == IPFilterAction.BLOCK:
            self._audit_block(ip, reason, "ip_filter")
            return Response(
                content='{"error": "Access denied"}',
                status_code=403,
                media_type="application/json",
            )
        
        # Geo filter check
        if self._geo_filter:
            geo_action, geo_reason = self._geo_filter.check_ip(ip)
            
            if geo_action == IPFilterAction.BLOCK:
                self._audit_block(ip, geo_reason, "geo_filter")
                return Response(
                    content='{"error": "Access denied from your region"}',
                    status_code=403,
                    media_type="application/json",
                )
            
            if geo_action == IPFilterAction.CHALLENGE:
                # Add header for challenge requirement
                request.state.requires_challenge = True
                request.state.challenge_reason = geo_reason
        
        # Signature verification
        if self._verifier:
            signature = request.headers.get("X-Signature")
            if signature:
                timestamp_str = request.headers.get("X-Signature-Timestamp")
                timestamp = int(timestamp_str) if timestamp_str else None
                nonce = request.headers.get("X-Nonce")
                
                body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
                
                is_valid, error = self._verifier.verify_request(
                    method=request.method,
                    path=request.url.path,
                    signature=signature,
                    timestamp=timestamp,
                    body=body,
                    nonce=nonce,
                )
                
                if not is_valid:
                    self._audit_block(ip, error or "Invalid signature", "signature")
                    return Response(
                        content='{"error": "Invalid request signature"}',
                        status_code=401,
                        media_type="application/json",
                    )
        
        # Continue to next middleware/handler
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        # Check forwarded headers (reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "0.0.0.0"
    
    def _audit_block(self, ip: str, reason: str, source: str):
        """Audit a blocked request."""
        if not self._enable_audit:
            return
        
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.SECURITY_ALERT,
                    action_description=f"Network block: {reason}",
                    actor_type="network",
                    actor_id="network_security",
                    severity="warning",
                    component="zero_trust.network",
                    context={
                        "ip": ip,
                        "reason": reason,
                        "source": source,
                    },
                )
        except Exception as e:
            logger.debug(f"[NETWORK] Audit failed: {e}")


# Singletons
_ip_filter: Optional[IPFilter] = None
_geo_filter: Optional[GeoFilter] = None


def get_ip_filter() -> IPFilter:
    """Get IP filter singleton."""
    global _ip_filter
    if _ip_filter is None:
        _ip_filter = IPFilter()
    return _ip_filter


def get_geo_filter() -> GeoFilter:
    """Get geo filter singleton."""
    global _geo_filter
    if _geo_filter is None:
        _geo_filter = GeoFilter()
    return _geo_filter
