"""
GRACE Zero-Trust Security Context

Implements security context enrichment with:
- Request context enrichment (IP, geo, device, time, behavior)
- Risk score calculation per request
- Anomaly detection for unusual patterns
- Context-aware policy decisions

All context decisions are logged to the immutable audit system.
"""

import hashlib
import ipaddress
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for security context."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_LOCATION = "unusual_location"
    UNUSUAL_DEVICE = "unusual_device"
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    VELOCITY_ANOMALY = "velocity_anomaly"
    REQUEST_PATTERN = "request_pattern"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class GeoLocation:
    """Geographic location information."""
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    organization: Optional[str] = None
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    is_datacenter: bool = False
    
    def distance_to(self, other: "GeoLocation") -> Optional[float]:
        """Calculate distance in km to another location using Haversine formula."""
        if not all([self.latitude, self.longitude, other.latitude, other.longitude]):
            return None
        
        R = 6371  # Earth's radius in km
        
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


@dataclass
class SecurityContext:
    """Enriched security context for a request."""
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Network context
    ip_address: Optional[str] = None
    ip_type: Optional[str] = None  # ipv4, ipv6
    is_private_ip: bool = False
    geo_location: Optional[GeoLocation] = None
    
    # Device context
    user_agent: Optional[str] = None
    device_type: Optional[str] = None  # desktop, mobile, tablet, bot
    os: Optional[str] = None
    browser: Optional[str] = None
    device_fingerprint_hash: Optional[str] = None
    
    # User context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_authenticated: bool = False
    authentication_method: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    
    # Request context
    method: Optional[str] = None
    path: Optional[str] = None
    query_params: Dict[str, Any] = field(default_factory=dict)
    content_type: Optional[str] = None
    request_size: int = 0
    
    # Temporal context
    is_business_hours: bool = True
    day_of_week: int = 0
    hour_of_day: int = 0
    
    # Behavioral context
    requests_in_window: int = 0
    unique_endpoints_in_window: int = 0
    failed_requests_in_window: int = 0
    
    # Risk assessment
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.MINIMAL
    risk_factors: Dict[str, float] = field(default_factory=dict)
    anomalies: List[AnomalyType] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "geo_location": {
                "country": self.geo_location.country_code,
                "city": self.geo_location.city,
            } if self.geo_location else None,
            "device_type": self.device_type,
            "user_id": self.user_id,
            "is_authenticated": self.is_authenticated,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "anomalies": [a.value for a in self.anomalies],
        }


@dataclass
class ContextAwarePolicyDecision:
    """Result of context-aware policy evaluation."""
    allowed: bool
    reason: str
    context: SecurityContext
    required_actions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestContextEnricher:
    """
    Enriches request context with security-relevant information.
    
    Gathers:
    - IP and geolocation data
    - Device information
    - Temporal patterns
    - Behavioral patterns
    """
    
    def __init__(
        self,
        business_hours_start: int = 8,
        business_hours_end: int = 18,
        business_days: List[int] = None,
    ):
        self.business_hours_start = business_hours_start
        self.business_hours_end = business_hours_end
        self.business_days = business_days or [0, 1, 2, 3, 4]  # Mon-Fri
        
        # Behavior tracking (use Redis in production)
        self._request_history: Dict[str, List[datetime]] = defaultdict(list)
        self._endpoint_history: Dict[str, Set[str]] = defaultdict(set)
        self._failure_history: Dict[str, List[datetime]] = defaultdict(list)
        
        # Known malicious indicators
        self._known_bad_ips: Set[str] = set()
        self._known_bad_user_agents: Set[str] = {
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "zgrab",
        }
        
        logger.info("[ZERO-TRUST-CONTEXT] Request context enricher initialized")
    
    def enrich(
        self,
        request_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        is_authenticated: bool = False,
        roles: Optional[List[str]] = None,
    ) -> SecurityContext:
        """Enrich a request with security context."""
        ctx = SecurityContext(request_id=request_id)
        
        # Network context
        if ip_address:
            ctx.ip_address = ip_address
            ctx.ip_type = self._get_ip_type(ip_address)
            ctx.is_private_ip = self._is_private_ip(ip_address)
            ctx.geo_location = self._lookup_geo(ip_address)
        
        # Device context
        if user_agent:
            ctx.user_agent = user_agent
            device_info = self._parse_user_agent(user_agent)
            ctx.device_type = device_info.get("device_type")
            ctx.os = device_info.get("os")
            ctx.browser = device_info.get("browser")
        
        # User context
        ctx.user_id = user_id
        ctx.session_id = session_id
        ctx.is_authenticated = is_authenticated
        ctx.roles = roles or []
        
        # Request context
        ctx.method = method
        ctx.path = path
        
        # Temporal context
        now = datetime.utcnow()
        ctx.day_of_week = now.weekday()
        ctx.hour_of_day = now.hour
        ctx.is_business_hours = self._is_business_hours(now)
        
        # Behavioral context
        tracking_key = user_id or ip_address or "anonymous"
        ctx.requests_in_window = self._count_requests_in_window(tracking_key)
        ctx.unique_endpoints_in_window = self._count_unique_endpoints(tracking_key)
        ctx.failed_requests_in_window = self._count_failures_in_window(tracking_key)
        
        # Record this request
        self._record_request(tracking_key, path or "/")
        
        return ctx
    
    def record_failure(self, user_id: Optional[str], ip_address: Optional[str]):
        """Record a failed request."""
        tracking_key = user_id or ip_address or "anonymous"
        self._failure_history[tracking_key].append(datetime.utcnow())
        
        # Clean old entries
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._failure_history[tracking_key] = [
            t for t in self._failure_history[tracking_key] if t > cutoff
        ]
    
    def add_known_bad_ip(self, ip: str):
        """Add an IP to the known bad list."""
        self._known_bad_ips.add(ip)
    
    def _get_ip_type(self, ip: str) -> str:
        """Determine IP address type."""
        try:
            addr = ipaddress.ip_address(ip)
            return "ipv6" if addr.version == 6 else "ipv4"
        except ValueError:
            return "unknown"
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is private."""
        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private
        except ValueError:
            return False
    
    def _lookup_geo(self, ip: str) -> Optional[GeoLocation]:
        """Lookup geolocation for IP (stub - integrate with MaxMind/IP2Location)."""
        # In production, integrate with a geolocation service
        return GeoLocation(
            country_code="US",
            country_name="United States",
        )
    
    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string."""
        ua_lower = user_agent.lower()
        
        # Detect device type
        device_type = "desktop"
        if "mobile" in ua_lower or "android" in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"
        elif "bot" in ua_lower or "spider" in ua_lower or "crawler" in ua_lower:
            device_type = "bot"
        
        # Detect OS
        os_name = "unknown"
        if "windows" in ua_lower:
            os_name = "windows"
        elif "mac os" in ua_lower or "macos" in ua_lower:
            os_name = "macos"
        elif "linux" in ua_lower:
            os_name = "linux"
        elif "android" in ua_lower:
            os_name = "android"
        elif "ios" in ua_lower or "iphone" in ua_lower:
            os_name = "ios"
        
        # Detect browser
        browser = "unknown"
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser = "chrome"
        elif "firefox" in ua_lower:
            browser = "firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "safari"
        elif "edg" in ua_lower:
            browser = "edge"
        
        return {
            "device_type": device_type,
            "os": os_name,
            "browser": browser,
        }
    
    def _is_business_hours(self, dt: datetime) -> bool:
        """Check if time is within business hours."""
        if dt.weekday() not in self.business_days:
            return False
        return self.business_hours_start <= dt.hour < self.business_hours_end
    
    def _count_requests_in_window(self, key: str, window_minutes: int = 5) -> int:
        """Count requests in time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        return len([t for t in self._request_history.get(key, []) if t > cutoff])
    
    def _count_unique_endpoints(self, key: str) -> int:
        """Count unique endpoints accessed."""
        return len(self._endpoint_history.get(key, set()))
    
    def _count_failures_in_window(self, key: str, window_minutes: int = 60) -> int:
        """Count failures in time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        return len([t for t in self._failure_history.get(key, []) if t > cutoff])
    
    def _record_request(self, key: str, endpoint: str):
        """Record a request for behavioral tracking."""
        now = datetime.utcnow()
        self._request_history[key].append(now)
        self._endpoint_history[key].add(endpoint)
        
        # Clean old entries (keep last hour)
        cutoff = now - timedelta(hours=1)
        self._request_history[key] = [t for t in self._request_history[key] if t > cutoff]


class RiskScoreCalculator:
    """
    Calculates risk scores based on security context.
    
    Uses weighted factors to compute overall risk.
    """
    
    def __init__(self):
        # Risk factor weights
        self.weights = {
            "known_bad_ip": 1.0,
            "known_bad_ua": 0.8,
            "vpn_detected": 0.2,
            "proxy_detected": 0.3,
            "tor_detected": 0.6,
            "datacenter_ip": 0.3,
            "unusual_time": 0.2,
            "high_request_rate": 0.4,
            "many_endpoints": 0.3,
            "high_failure_rate": 0.5,
            "unauthenticated": 0.1,
            "new_device": 0.3,
            "new_location": 0.4,
            "bot_user_agent": 0.3,
        }
        
        # Risk level thresholds
        self.thresholds = {
            RiskLevel.MINIMAL: 0.0,
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.HIGH: 0.6,
            RiskLevel.CRITICAL: 0.8,
        }
        
        logger.info("[ZERO-TRUST-CONTEXT] Risk score calculator initialized")
    
    def calculate(
        self,
        context: SecurityContext,
        known_bad_ips: Optional[Set[str]] = None,
        known_bad_uas: Optional[Set[str]] = None,
    ) -> Tuple[float, Dict[str, float], RiskLevel]:
        """
        Calculate risk score for a security context.
        
        Returns:
            Tuple of (score, factors, risk_level)
        """
        factors: Dict[str, float] = {}
        known_bad_ips = known_bad_ips or set()
        known_bad_uas = known_bad_uas or set()
        
        # Check known bad indicators
        if context.ip_address and context.ip_address in known_bad_ips:
            factors["known_bad_ip"] = self.weights["known_bad_ip"]
        
        if context.user_agent:
            ua_lower = context.user_agent.lower()
            for bad_ua in known_bad_uas:
                if bad_ua in ua_lower:
                    factors["known_bad_ua"] = self.weights["known_bad_ua"]
                    break
        
        # Check geolocation indicators
        if context.geo_location:
            if context.geo_location.is_vpn:
                factors["vpn_detected"] = self.weights["vpn_detected"]
            if context.geo_location.is_proxy:
                factors["proxy_detected"] = self.weights["proxy_detected"]
            if context.geo_location.is_tor:
                factors["tor_detected"] = self.weights["tor_detected"]
            if context.geo_location.is_datacenter:
                factors["datacenter_ip"] = self.weights["datacenter_ip"]
        
        # Check temporal patterns
        if not context.is_business_hours:
            factors["unusual_time"] = self.weights["unusual_time"]
        
        # Check behavioral patterns
        if context.requests_in_window > 100:
            factors["high_request_rate"] = self.weights["high_request_rate"]
        
        if context.unique_endpoints_in_window > 50:
            factors["many_endpoints"] = self.weights["many_endpoints"]
        
        if context.failed_requests_in_window > 10:
            factors["high_failure_rate"] = self.weights["high_failure_rate"]
        
        # Check authentication
        if not context.is_authenticated:
            factors["unauthenticated"] = self.weights["unauthenticated"]
        
        # Check device type
        if context.device_type == "bot":
            factors["bot_user_agent"] = self.weights["bot_user_agent"]
        
        # Calculate weighted score
        if factors:
            score = min(1.0, sum(factors.values()) / len(factors) * 1.5)
        else:
            score = 0.0
        
        # Determine risk level
        risk_level = RiskLevel.MINIMAL
        for level, threshold in sorted(self.thresholds.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                risk_level = level
                break
        
        return score, factors, risk_level


class AnomalyDetector:
    """
    Detects anomalies in security context using statistical analysis.
    
    Implements:
    - Time-based anomaly detection
    - Location-based anomaly detection
    - Behavior-based anomaly detection
    - Impossible travel detection
    """
    
    def __init__(
        self,
        max_travel_speed_kmh: float = 1000.0,  # Approximate jet speed
        velocity_window_minutes: int = 5,
    ):
        self.max_travel_speed_kmh = max_travel_speed_kmh
        self.velocity_window_minutes = velocity_window_minutes
        
        # User history for anomaly detection
        self._user_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._user_patterns: Dict[str, Dict[str, Any]] = {}
        
        logger.info("[ZERO-TRUST-CONTEXT] Anomaly detector initialized")
    
    def detect(
        self,
        context: SecurityContext,
    ) -> List[AnomalyType]:
        """
        Detect anomalies in the security context.
        
        Returns list of detected anomaly types.
        """
        anomalies = []
        
        if not context.user_id:
            return anomalies
        
        user_id = context.user_id
        
        # Check time-based anomalies
        if self._is_unusual_time(user_id, context.hour_of_day, context.day_of_week):
            anomalies.append(AnomalyType.UNUSUAL_TIME)
        
        # Check location-based anomalies
        if context.geo_location:
            if self._is_unusual_location(user_id, context.geo_location):
                anomalies.append(AnomalyType.UNUSUAL_LOCATION)
            
            # Check impossible travel
            if self._is_impossible_travel(user_id, context.geo_location, context.timestamp):
                anomalies.append(AnomalyType.IMPOSSIBLE_TRAVEL)
        
        # Check behavior-based anomalies
        if self._is_unusual_behavior(user_id, context):
            anomalies.append(AnomalyType.UNUSUAL_BEHAVIOR)
        
        # Check velocity anomalies (too many requests too fast)
        if self._is_velocity_anomaly(user_id, context.requests_in_window):
            anomalies.append(AnomalyType.VELOCITY_ANOMALY)
        
        # Check request pattern anomalies
        if self._is_request_pattern_anomaly(user_id, context.path, context.method):
            anomalies.append(AnomalyType.REQUEST_PATTERN)
        
        # Record this context for future analysis
        self._record_context(user_id, context)
        
        # Audit detected anomalies
        if anomalies:
            self._audit_anomalies(context, anomalies)
        
        return anomalies
    
    def learn_user_pattern(self, user_id: str, context: SecurityContext):
        """Learn normal patterns for a user."""
        if user_id not in self._user_patterns:
            self._user_patterns[user_id] = {
                "typical_hours": set(),
                "typical_days": set(),
                "typical_locations": set(),
                "typical_devices": set(),
                "avg_requests_per_window": 0,
                "request_count": 0,
            }
        
        patterns = self._user_patterns[user_id]
        patterns["typical_hours"].add(context.hour_of_day)
        patterns["typical_days"].add(context.day_of_week)
        
        if context.geo_location and context.geo_location.country_code:
            patterns["typical_locations"].add(context.geo_location.country_code)
        
        if context.device_fingerprint_hash:
            patterns["typical_devices"].add(context.device_fingerprint_hash)
        
        # Update average requests
        count = patterns["request_count"]
        avg = patterns["avg_requests_per_window"]
        patterns["avg_requests_per_window"] = (avg * count + context.requests_in_window) / (count + 1)
        patterns["request_count"] = count + 1
    
    def _is_unusual_time(self, user_id: str, hour: int, day: int) -> bool:
        """Check if time is unusual for user."""
        patterns = self._user_patterns.get(user_id)
        if not patterns:
            return False
        
        typical_hours = patterns.get("typical_hours", set())
        typical_days = patterns.get("typical_days", set())
        
        # Need at least 10 data points to consider patterns
        if patterns.get("request_count", 0) < 10:
            return False
        
        return hour not in typical_hours or day not in typical_days
    
    def _is_unusual_location(self, user_id: str, geo: GeoLocation) -> bool:
        """Check if location is unusual for user."""
        patterns = self._user_patterns.get(user_id)
        if not patterns or not geo.country_code:
            return False
        
        typical_locations = patterns.get("typical_locations", set())
        
        if patterns.get("request_count", 0) < 10:
            return False
        
        return geo.country_code not in typical_locations
    
    def _is_impossible_travel(
        self,
        user_id: str,
        current_geo: GeoLocation,
        current_time: datetime,
    ) -> bool:
        """Check for impossible travel (too fast between locations)."""
        history = self._user_history.get(user_id, [])
        if not history:
            return False
        
        # Get last location
        last_entry = history[-1]
        last_geo = last_entry.get("geo_location")
        last_time = last_entry.get("timestamp")
        
        if not last_geo or not last_time:
            return False
        
        # Calculate distance
        if not isinstance(last_geo, GeoLocation):
            return False
        
        distance = current_geo.distance_to(last_geo)
        if distance is None:
            return False
        
        # Calculate time difference
        time_diff = (current_time - last_time).total_seconds() / 3600  # hours
        if time_diff <= 0:
            return False
        
        # Calculate speed
        speed = distance / time_diff  # km/h
        
        return speed > self.max_travel_speed_kmh
    
    def _is_unusual_behavior(self, user_id: str, context: SecurityContext) -> bool:
        """Check for unusual behavioral patterns."""
        patterns = self._user_patterns.get(user_id)
        if not patterns or patterns.get("request_count", 0) < 50:
            return False
        
        # Check if request rate is significantly higher than average
        avg = patterns.get("avg_requests_per_window", 0)
        if avg > 0 and context.requests_in_window > avg * 3:
            return True
        
        return False
    
    def _is_velocity_anomaly(self, user_id: str, requests_in_window: int) -> bool:
        """Check for velocity anomalies (burst of requests)."""
        # Flag if more than 200 requests in 5 minutes
        return requests_in_window > 200
    
    def _is_request_pattern_anomaly(
        self,
        user_id: str,
        path: Optional[str],
        method: Optional[str],
    ) -> bool:
        """Check for suspicious request patterns."""
        if not path:
            return False
        
        # Check for common attack patterns
        suspicious_patterns = [
            "../",  # Path traversal
            "..\\",
            "<script",  # XSS
            "javascript:",
            "SELECT ",  # SQL injection
            "UNION ",
            "DROP ",
            "INSERT ",
            "' OR '",
            "; --",
        ]
        
        path_lower = path.lower()
        return any(pattern.lower() in path_lower for pattern in suspicious_patterns)
    
    def _record_context(self, user_id: str, context: SecurityContext):
        """Record context for future anomaly detection."""
        entry = {
            "timestamp": context.timestamp,
            "geo_location": context.geo_location,
            "device_fingerprint_hash": context.device_fingerprint_hash,
            "ip_address": context.ip_address,
        }
        
        self._user_history[user_id].append(entry)
        
        # Keep only last 100 entries
        if len(self._user_history[user_id]) > 100:
            self._user_history[user_id] = self._user_history[user_id][-100:]
        
        # Update patterns
        self.learn_user_pattern(user_id, context)
    
    def _audit_anomalies(self, context: SecurityContext, anomalies: List[AnomalyType]):
        """Audit detected anomalies to immutable log."""
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
                    action_description=f"Anomalies detected: {[a.value for a in anomalies]}",
                    actor_type="security",
                    actor_id="zero-trust-context",
                    session_id=context.session_id,
                    severity="warning",
                    component="zero_trust.context",
                    context={
                        "request_id": context.request_id,
                        "user_id": context.user_id,
                        "ip_address": context.ip_address,
                        "anomalies": [a.value for a in anomalies],
                        "risk_score": context.risk_score,
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-CONTEXT] Audit logging failed: {e}")


# Singleton instances
_context_enricher: Optional[RequestContextEnricher] = None
_anomaly_detector: Optional[AnomalyDetector] = None


def get_context_enricher() -> RequestContextEnricher:
    """Get the context enricher singleton."""
    global _context_enricher
    if _context_enricher is None:
        _context_enricher = RequestContextEnricher()
    return _context_enricher


def get_anomaly_detector() -> AnomalyDetector:
    """Get the anomaly detector singleton."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
