"""
GRACE Zero-Trust Threat Detection System

Provides real-time threat detection with:
- Brute force detection
- Credential stuffing detection
- Session hijacking detection
- Impossible travel detection
- API abuse pattern detection
- Self-healing threat responses (GRACE-aligned)

All threat events are logged to the immutable audit system.
"""

import hashlib
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of detected threats."""
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_HIJACK = "session_hijack"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    API_ABUSE = "api_abuse"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    INJECTION_ATTEMPT = "injection_attempt"
    BOT_ACTIVITY = "bot_activity"
    ACCOUNT_TAKEOVER = "account_takeover"


class ThreatResponse(str, Enum):
    """Response actions for threats."""
    LOG = "log"
    CHALLENGE = "challenge"
    BLOCK = "block"
    ALERT = "alert"
    LOCKDOWN = "lockdown"
    REQUIRE_MFA = "require_mfa"
    TERMINATE_SESSION = "terminate_session"
    RATE_LIMIT = "rate_limit"
    CAPTCHA = "captcha"


@dataclass
class ThreatEvent:
    """A detected threat event."""
    event_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    source_ip: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    timestamp: datetime
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    responses_taken: List[ThreatResponse] = field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "threat_type": self.threat_type.value,
            "threat_level": self.threat_level.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "evidence": self.evidence,
            "responses_taken": [r.value for r in self.responses_taken],
            "resolved": self.resolved,
        }


@dataclass
class ThreatPolicy:
    """Policy for handling a specific threat type."""
    threat_type: ThreatType
    threshold: int
    window_seconds: int
    responses: List[ThreatResponse]
    escalation_threshold: int = 3
    escalation_responses: List[ThreatResponse] = field(default_factory=list)
    auto_block_duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    notify_security: bool = True


@dataclass
class BlockedEntity:
    """A blocked IP or user."""
    entity_type: str  # "ip" or "user"
    entity_id: str
    blocked_at: datetime
    expires_at: datetime
    reason: str
    threat_event_id: str


class ThreatDetector:
    """
    Core threat detection engine.
    
    Monitors for various attack patterns and triggers
    appropriate responses based on configured policies.
    """
    
    def __init__(
        self,
        custom_policies: Optional[Dict[ThreatType, ThreatPolicy]] = None,
    ):
        self._policies: Dict[ThreatType, ThreatPolicy] = {}
        self._initialize_default_policies()
        
        if custom_policies:
            self._policies.update(custom_policies)
        
        # Tracking data structures
        self._failed_auths: Dict[str, List[datetime]] = defaultdict(list)
        self._request_counts: Dict[str, List[datetime]] = defaultdict(list)
        self._session_fingerprints: Dict[str, Dict[str, Any]] = {}
        self._user_locations: Dict[str, List[Tuple[datetime, str, float, float]]] = defaultdict(list)
        self._password_hashes: Dict[str, Set[str]] = defaultdict(set)
        
        # Blocked entities
        self._blocked_ips: Dict[str, BlockedEntity] = {}
        self._blocked_users: Dict[str, BlockedEntity] = {}
        
        # Threat history
        self._threat_events: List[ThreatEvent] = []
        self._active_threats: Dict[str, ThreatEvent] = {}
        
        # Response callbacks
        self._response_handlers: Dict[ThreatResponse, List[Callable]] = defaultdict(list)
        
        self._lock = threading.RLock()
        
        logger.info("[THREAT-DETECTION] Threat detector initialized")
    
    def _initialize_default_policies(self):
        """Set up default threat policies."""
        self._policies = {
            ThreatType.BRUTE_FORCE: ThreatPolicy(
                threat_type=ThreatType.BRUTE_FORCE,
                threshold=5,
                window_seconds=300,  # 5 failed attempts in 5 minutes
                responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT],
                escalation_threshold=10,
                escalation_responses=[ThreatResponse.LOCKDOWN, ThreatResponse.ALERT],
                auto_block_duration=timedelta(hours=1),
            ),
            ThreatType.CREDENTIAL_STUFFING: ThreatPolicy(
                threat_type=ThreatType.CREDENTIAL_STUFFING,
                threshold=10,
                window_seconds=60,  # 10 different users, same password pattern
                responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT],
                auto_block_duration=timedelta(hours=24),
            ),
            ThreatType.SESSION_HIJACK: ThreatPolicy(
                threat_type=ThreatType.SESSION_HIJACK,
                threshold=1,  # Any detection is critical
                window_seconds=1,
                responses=[ThreatResponse.TERMINATE_SESSION, ThreatResponse.ALERT, ThreatResponse.REQUIRE_MFA],
            ),
            ThreatType.IMPOSSIBLE_TRAVEL: ThreatPolicy(
                threat_type=ThreatType.IMPOSSIBLE_TRAVEL,
                threshold=1,
                window_seconds=1,
                responses=[ThreatResponse.CHALLENGE, ThreatResponse.REQUIRE_MFA],
            ),
            ThreatType.API_ABUSE: ThreatPolicy(
                threat_type=ThreatType.API_ABUSE,
                threshold=100,
                window_seconds=60,  # 100 requests per minute
                responses=[ThreatResponse.RATE_LIMIT, ThreatResponse.LOG],
                escalation_threshold=500,
                escalation_responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT],
            ),
            ThreatType.INJECTION_ATTEMPT: ThreatPolicy(
                threat_type=ThreatType.INJECTION_ATTEMPT,
                threshold=1,
                window_seconds=1,
                responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT],
                auto_block_duration=timedelta(days=7),
            ),
            ThreatType.DATA_EXFILTRATION: ThreatPolicy(
                threat_type=ThreatType.DATA_EXFILTRATION,
                threshold=1,
                window_seconds=1,
                responses=[ThreatResponse.TERMINATE_SESSION, ThreatResponse.LOCKDOWN, ThreatResponse.ALERT],
            ),
        }
    
    def register_response_handler(
        self,
        response: ThreatResponse,
        handler: Callable[[ThreatEvent], None],
    ):
        """Register a callback for a threat response."""
        self._response_handlers[response].append(handler)
    
    def check_brute_force(
        self,
        identifier: str,
        success: bool,
        ip_address: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """
        Check for brute force attack.
        
        Args:
            identifier: User ID or IP being tracked
            success: Whether authentication succeeded
            ip_address: Source IP
            
        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        with self._lock:
            now = datetime.utcnow()
            policy = self._policies[ThreatType.BRUTE_FORCE]
            window_start = now - timedelta(seconds=policy.window_seconds)
            
            if success:
                # Clear failed attempts on success
                self._failed_auths[identifier] = []
                return None
            
            # Record failed attempt
            self._failed_auths[identifier].append(now)
            
            # Clean old attempts
            self._failed_auths[identifier] = [
                t for t in self._failed_auths[identifier] if t > window_start
            ]
            
            failure_count = len(self._failed_auths[identifier])
            
            if failure_count >= policy.threshold:
                # Determine threat level
                if failure_count >= policy.escalation_threshold:
                    level = ThreatLevel.CRITICAL
                    responses = policy.escalation_responses or policy.responses
                else:
                    level = ThreatLevel.HIGH
                    responses = policy.responses
                
                event = self._create_threat_event(
                    threat_type=ThreatType.BRUTE_FORCE,
                    threat_level=level,
                    source_ip=ip_address,
                    user_id=identifier if not identifier.count(".") else None,
                    description=f"Brute force detected: {failure_count} failed attempts in {policy.window_seconds}s",
                    evidence={
                        "failure_count": failure_count,
                        "window_seconds": policy.window_seconds,
                        "identifier": identifier,
                    },
                )
                
                self._execute_responses(event, responses, ip_address, identifier)
                return event
            
            return None
    
    def check_credential_stuffing(
        self,
        ip_address: str,
        password_hash: str,
        user_id: str,
    ) -> Optional[ThreatEvent]:
        """
        Check for credential stuffing attack.
        
        Detects when same password is tried against many accounts.
        """
        with self._lock:
            now = datetime.utcnow()
            policy = self._policies[ThreatType.CREDENTIAL_STUFFING]
            
            # Track password hash per IP
            key = f"{ip_address}:{password_hash[:16]}"
            self._password_hashes[key].add(user_id)
            
            unique_users = len(self._password_hashes[key])
            
            if unique_users >= policy.threshold:
                event = self._create_threat_event(
                    threat_type=ThreatType.CREDENTIAL_STUFFING,
                    threat_level=ThreatLevel.CRITICAL,
                    source_ip=ip_address,
                    description=f"Credential stuffing detected: same password tried on {unique_users} accounts",
                    evidence={
                        "unique_users_targeted": unique_users,
                        "ip_address": ip_address,
                    },
                )
                
                self._execute_responses(event, policy.responses, ip_address)
                
                # Clear tracking for this pattern
                del self._password_hashes[key]
                
                return event
            
            return None
    
    def check_session_hijack(
        self,
        session_id: str,
        ip_address: str,
        user_agent: str,
        user_id: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """
        Check for session hijacking.
        
        Detects when session characteristics change mid-session.
        """
        with self._lock:
            fingerprint = {
                "ip": ip_address,
                "ua_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16],
            }
            
            if session_id in self._session_fingerprints:
                stored = self._session_fingerprints[session_id]
                
                # Check for changes
                ip_changed = stored["ip"] != fingerprint["ip"]
                ua_changed = stored["ua_hash"] != fingerprint["ua_hash"]
                
                if ip_changed and ua_changed:
                    # Both changed - high confidence hijack
                    policy = self._policies[ThreatType.SESSION_HIJACK]
                    
                    event = self._create_threat_event(
                        threat_type=ThreatType.SESSION_HIJACK,
                        threat_level=ThreatLevel.CRITICAL,
                        source_ip=ip_address,
                        user_id=user_id,
                        session_id=session_id,
                        description="Session hijacking detected: IP and User-Agent changed mid-session",
                        evidence={
                            "original_ip": stored["ip"],
                            "new_ip": ip_address,
                            "ip_changed": ip_changed,
                            "ua_changed": ua_changed,
                        },
                    )
                    
                    self._execute_responses(event, policy.responses, ip_address, user_id)
                    return event
            else:
                # First request for this session
                self._session_fingerprints[session_id] = fingerprint
            
            return None
    
    def check_impossible_travel(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        ip_address: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """
        Check for impossible travel.
        
        Detects when user appears in distant locations faster than possible.
        """
        with self._lock:
            import math
            
            now = datetime.utcnow()
            max_speed_kmh = 1000  # Max believable speed (supersonic flight)
            
            if user_id in self._user_locations and self._user_locations[user_id]:
                last = self._user_locations[user_id][-1]
                last_time, last_ip, last_lat, last_lon = last
                
                # Calculate distance using Haversine
                R = 6371  # Earth radius in km
                lat1, lat2 = math.radians(last_lat), math.radians(latitude)
                dlat = math.radians(latitude - last_lat)
                dlon = math.radians(longitude - last_lon)
                
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance_km = R * c
                
                # Calculate time difference
                time_diff_hours = (now - last_time).total_seconds() / 3600
                
                if time_diff_hours > 0:
                    speed_kmh = distance_km / time_diff_hours
                    
                    if speed_kmh > max_speed_kmh:
                        policy = self._policies[ThreatType.IMPOSSIBLE_TRAVEL]
                        
                        event = self._create_threat_event(
                            threat_type=ThreatType.IMPOSSIBLE_TRAVEL,
                            threat_level=ThreatLevel.HIGH,
                            source_ip=ip_address,
                            user_id=user_id,
                            description=f"Impossible travel: {distance_km:.0f}km in {time_diff_hours:.1f}h ({speed_kmh:.0f}km/h)",
                            evidence={
                                "distance_km": distance_km,
                                "time_hours": time_diff_hours,
                                "implied_speed_kmh": speed_kmh,
                                "from_location": {"lat": last_lat, "lon": last_lon},
                                "to_location": {"lat": latitude, "lon": longitude},
                            },
                        )
                        
                        self._execute_responses(event, policy.responses, ip_address, user_id)
                        return event
            
            # Record location
            self._user_locations[user_id].append((now, ip_address, latitude, longitude))
            
            # Keep only last 10 locations
            if len(self._user_locations[user_id]) > 10:
                self._user_locations[user_id] = self._user_locations[user_id][-10:]
            
            return None
    
    def check_api_abuse(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """
        Check for API abuse patterns.
        
        Detects abnormally high request rates.
        """
        with self._lock:
            now = datetime.utcnow()
            policy = self._policies[ThreatType.API_ABUSE]
            window_start = now - timedelta(seconds=policy.window_seconds)
            
            # Record request
            self._request_counts[identifier].append(now)
            
            # Clean old requests
            self._request_counts[identifier] = [
                t for t in self._request_counts[identifier] if t > window_start
            ]
            
            request_count = len(self._request_counts[identifier])
            
            if request_count >= policy.threshold:
                if request_count >= policy.escalation_threshold:
                    level = ThreatLevel.HIGH
                    responses = policy.escalation_responses or policy.responses
                else:
                    level = ThreatLevel.MEDIUM
                    responses = policy.responses
                
                event = self._create_threat_event(
                    threat_type=ThreatType.API_ABUSE,
                    threat_level=level,
                    source_ip=identifier if "." in identifier else None,
                    user_id=identifier if "." not in identifier else None,
                    description=f"API abuse detected: {request_count} requests in {policy.window_seconds}s",
                    evidence={
                        "request_count": request_count,
                        "window_seconds": policy.window_seconds,
                        "endpoint": endpoint,
                    },
                )
                
                self._execute_responses(event, responses, identifier if "." in identifier else None)
                return event
            
            return None
    
    def check_injection_attempt(
        self,
        input_data: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[ThreatEvent]:
        """
        Check for injection attacks (SQL, XSS, command).
        """
        # Common injection patterns
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE",
            "UNION SELECT",
            "1=1--",
            "' OR ''='",
        ]
        
        xss_patterns = [
            "<script>",
            "javascript:",
            "onerror=",
            "onload=",
            "<img src=x",
        ]
        
        cmd_patterns = [
            "; ls",
            "| cat",
            "`whoami`",
            "$(id)",
            "; rm -rf",
        ]
        
        input_lower = input_data.lower()
        detected_patterns = []
        
        for pattern in sql_patterns:
            if pattern.lower() in input_lower:
                detected_patterns.append(("SQL", pattern))
        
        for pattern in xss_patterns:
            if pattern.lower() in input_lower:
                detected_patterns.append(("XSS", pattern))
        
        for pattern in cmd_patterns:
            if pattern.lower() in input_lower:
                detected_patterns.append(("Command", pattern))
        
        if detected_patterns:
            policy = self._policies[ThreatType.INJECTION_ATTEMPT]
            
            event = self._create_threat_event(
                threat_type=ThreatType.INJECTION_ATTEMPT,
                threat_level=ThreatLevel.CRITICAL,
                source_ip=ip_address,
                user_id=user_id,
                description=f"Injection attempt detected: {len(detected_patterns)} patterns",
                evidence={
                    "detected_patterns": [{"type": p[0], "pattern": p[1]} for p in detected_patterns],
                    "input_sample": input_data[:200],
                },
            )
            
            self._execute_responses(event, policy.responses, ip_address, user_id)
            return event
        
        return None
    
    def is_blocked(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[BlockedEntity]]:
        """Check if IP or user is blocked."""
        now = datetime.utcnow()
        
        with self._lock:
            if ip_address and ip_address in self._blocked_ips:
                blocked = self._blocked_ips[ip_address]
                if now < blocked.expires_at:
                    return True, blocked
                else:
                    del self._blocked_ips[ip_address]
            
            if user_id and user_id in self._blocked_users:
                blocked = self._blocked_users[user_id]
                if now < blocked.expires_at:
                    return True, blocked
                else:
                    del self._blocked_users[user_id]
        
        return False, None
    
    def block(
        self,
        entity_type: str,
        entity_id: str,
        duration: timedelta,
        reason: str,
        threat_event_id: str,
    ):
        """Block an IP or user."""
        now = datetime.utcnow()
        
        blocked = BlockedEntity(
            entity_type=entity_type,
            entity_id=entity_id,
            blocked_at=now,
            expires_at=now + duration,
            reason=reason,
            threat_event_id=threat_event_id,
        )
        
        with self._lock:
            if entity_type == "ip":
                self._blocked_ips[entity_id] = blocked
            elif entity_type == "user":
                self._blocked_users[entity_id] = blocked
        
        logger.warning(f"[THREAT-DETECTION] Blocked {entity_type} {entity_id} until {blocked.expires_at}")
    
    def unblock(self, entity_type: str, entity_id: str) -> bool:
        """Manually unblock an IP or user."""
        with self._lock:
            if entity_type == "ip" and entity_id in self._blocked_ips:
                del self._blocked_ips[entity_id]
                logger.info(f"[THREAT-DETECTION] Unblocked IP {entity_id}")
                return True
            elif entity_type == "user" and entity_id in self._blocked_users:
                del self._blocked_users[entity_id]
                logger.info(f"[THREAT-DETECTION] Unblocked user {entity_id}")
                return True
        return False
    
    def get_active_threats(self) -> List[ThreatEvent]:
        """Get list of active (unresolved) threats."""
        with self._lock:
            return list(self._active_threats.values())
    
    def get_threat_history(
        self,
        limit: int = 100,
        threat_type: Optional[ThreatType] = None,
        min_level: Optional[ThreatLevel] = None,
    ) -> List[ThreatEvent]:
        """Get threat history with optional filters."""
        with self._lock:
            events = self._threat_events.copy()
        
        if threat_type:
            events = [e for e in events if e.threat_type == threat_type]
        
        if min_level:
            level_order = [ThreatLevel.NONE, ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            min_idx = level_order.index(min_level)
            events = [e for e in events if level_order.index(e.threat_level) >= min_idx]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def resolve_threat(
        self,
        event_id: str,
        resolution_notes: Optional[str] = None,
    ) -> bool:
        """Mark a threat as resolved."""
        with self._lock:
            if event_id in self._active_threats:
                event = self._active_threats[event_id]
                event.resolved = True
                event.resolved_at = datetime.utcnow()
                event.resolution_notes = resolution_notes
                del self._active_threats[event_id]
                
                self._audit_threat(event, "resolved")
                return True
        return False
    
    def _create_threat_event(
        self,
        threat_type: ThreatType,
        threat_level: ThreatLevel,
        description: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> ThreatEvent:
        """Create and record a threat event."""
        import uuid
        
        event = ThreatEvent(
            event_id=f"TE-{uuid.uuid4().hex[:12]}",
            threat_type=threat_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            description=description,
            evidence=evidence or {},
        )
        
        with self._lock:
            self._threat_events.append(event)
            self._active_threats[event.event_id] = event
            
            # Keep only last 1000 events
            if len(self._threat_events) > 1000:
                self._threat_events = self._threat_events[-1000:]
        
        self._audit_threat(event, "detected")
        
        logger.warning(
            f"[THREAT-DETECTION] {threat_level.value.upper()} threat: "
            f"{threat_type.value} - {description}"
        )
        
        return event
    
    def _execute_responses(
        self,
        event: ThreatEvent,
        responses: List[ThreatResponse],
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Execute threat response actions."""
        policy = self._policies.get(event.threat_type)
        
        for response in responses:
            try:
                if response == ThreatResponse.BLOCK:
                    duration = policy.auto_block_duration if policy else timedelta(hours=1)
                    
                    if ip_address:
                        self.block("ip", ip_address, duration, event.description, event.event_id)
                    if user_id:
                        self.block("user", user_id, duration, event.description, event.event_id)
                
                elif response == ThreatResponse.TERMINATE_SESSION:
                    if event.session_id:
                        self._terminate_session(event.session_id)
                
                elif response == ThreatResponse.ALERT:
                    self._send_alert(event)
                
                # Execute custom handlers
                for handler in self._response_handlers.get(response, []):
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"[THREAT-DETECTION] Handler failed: {e}")
                
                event.responses_taken.append(response)
                
            except Exception as e:
                logger.error(f"[THREAT-DETECTION] Response {response.value} failed: {e}")
    
    def _terminate_session(self, session_id: str):
        """Terminate a session."""
        try:
            # Integration point for session management
            logger.warning(f"[THREAT-DETECTION] Terminating session: {session_id}")
            # TODO: Integrate with session manager
        except Exception as e:
            logger.error(f"[THREAT-DETECTION] Session termination failed: {e}")
    
    def _send_alert(self, event: ThreatEvent):
        """Send security alert."""
        try:
            logger.critical(
                f"[SECURITY-ALERT] {event.threat_level.value.upper()}: "
                f"{event.threat_type.value} - {event.description}"
            )
            # TODO: Integrate with alerting system (email, Slack, PagerDuty, etc.)
        except Exception as e:
            logger.error(f"[THREAT-DETECTION] Alert failed: {e}")
    
    def _audit_threat(self, event: ThreatEvent, action: str):
        """Audit threat to immutable log."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            severity_map = {
                ThreatLevel.NONE: "info",
                ThreatLevel.LOW: "warning",
                ThreatLevel.MEDIUM: "warning",
                ThreatLevel.HIGH: "error",
                ThreatLevel.CRITICAL: "critical",
            }
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.SECURITY_ALERT,
                    action_description=f"Threat {action}: {event.threat_type.value}",
                    actor_type="security",
                    actor_id="threat_detector",
                    session_id=event.session_id,
                    severity=severity_map.get(event.threat_level, "warning"),
                    component="zero_trust.threat_detection",
                    context=event.to_dict(),
                )
        except Exception as e:
            logger.debug(f"[THREAT-DETECTION] Audit failed: {e}")


class SelfHealingThreatResponse:
    """
    GRACE-aligned self-healing threat response.
    
    Automatically adapts defenses based on threat patterns.
    """
    
    def __init__(self, detector: ThreatDetector):
        self._detector = detector
        self._threat_patterns: Dict[str, int] = defaultdict(int)
        self._defense_adjustments: Dict[str, Any] = {}
        
        # Register as handler
        detector.register_response_handler(ThreatResponse.LOG, self._learn_from_threat)
        detector.register_response_handler(ThreatResponse.BLOCK, self._learn_from_threat)
    
    def _learn_from_threat(self, event: ThreatEvent):
        """Learn from threats to improve detection."""
        pattern_key = f"{event.threat_type.value}:{event.source_ip or 'unknown'}"
        self._threat_patterns[pattern_key] += 1
        
        # If pattern repeats, adjust defenses
        if self._threat_patterns[pattern_key] >= 3:
            self._adjust_defense(event)
    
    def _adjust_defense(self, event: ThreatEvent):
        """Automatically adjust defenses based on patterns."""
        logger.info(f"[SELF-HEALING] Adjusting defenses for pattern: {event.threat_type.value}")
        
        # Example: Reduce thresholds for repeated attack sources
        policy = self._detector._policies.get(event.threat_type)
        if policy and event.source_ip:
            # Make this IP more sensitive to detection
            # This is where GRACE's learning would integrate
            self._defense_adjustments[event.source_ip] = {
                "threshold_multiplier": 0.5,
                "adjusted_at": datetime.utcnow(),
            }


# Singleton
_detector: Optional[ThreatDetector] = None


def get_threat_detector() -> ThreatDetector:
    """Get the threat detector singleton."""
    global _detector
    if _detector is None:
        _detector = ThreatDetector()
    return _detector
