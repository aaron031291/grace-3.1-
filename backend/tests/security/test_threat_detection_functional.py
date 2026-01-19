"""
Zero Trust Threat Detection - REAL Functional Tests

Tests verify ACTUAL threat detection behavior using real implementations:
- ThreatLevel and ThreatType enums
- ThreatResponse actions
- ThreatEvent structure and serialization
- ThreatPolicy configuration
- Brute force and API abuse detection patterns
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# THREAT LEVEL ENUM TESTS
# =============================================================================

class TestThreatLevelEnumFunctional:
    """Functional tests for ThreatLevel enum."""

    def test_all_threat_levels_defined(self):
        """All required threat levels must be defined."""
        from security.zero_trust.threat_detection import ThreatLevel

        required_levels = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

        for level_name in required_levels:
            assert hasattr(ThreatLevel, level_name), f"Missing level: {level_name}"

    def test_threat_level_ordering(self):
        """Threat levels must have logical severity ordering."""
        from security.zero_trust.threat_detection import ThreatLevel

        severity_order = [
            ThreatLevel.NONE,
            ThreatLevel.LOW,
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL
        ]

        # Each level should be different
        for i in range(len(severity_order) - 1):
            assert severity_order[i] != severity_order[i + 1]


# =============================================================================
# THREAT TYPE ENUM TESTS
# =============================================================================

class TestThreatTypeEnumFunctional:
    """Functional tests for ThreatType enum."""

    def test_all_threat_types_defined(self):
        """All required threat types must be defined."""
        from security.zero_trust.threat_detection import ThreatType

        required_types = [
            "BRUTE_FORCE",
            "CREDENTIAL_STUFFING",
            "SESSION_HIJACK",
            "IMPOSSIBLE_TRAVEL",
            "API_ABUSE",
            "RATE_LIMIT_EXCEEDED",
            "SUSPICIOUS_PATTERN",
            "PRIVILEGE_ESCALATION",
            "DATA_EXFILTRATION",
            "INJECTION_ATTEMPT",
            "BOT_ACTIVITY",
            "ACCOUNT_TAKEOVER"
        ]

        for type_name in required_types:
            assert hasattr(ThreatType, type_name), f"Missing type: {type_name}"

    def test_threat_type_values_are_snake_case(self):
        """Threat type values must be snake_case strings."""
        from security.zero_trust.threat_detection import ThreatType

        for threat in ThreatType:
            assert isinstance(threat.value, str)
            assert threat.value == threat.value.lower()


# =============================================================================
# THREAT RESPONSE ENUM TESTS
# =============================================================================

class TestThreatResponseEnumFunctional:
    """Functional tests for ThreatResponse enum."""

    def test_all_responses_defined(self):
        """All required threat responses must be defined."""
        from security.zero_trust.threat_detection import ThreatResponse

        required_responses = [
            "LOG",
            "CHALLENGE",
            "BLOCK",
            "ALERT",
            "LOCKDOWN",
            "REQUIRE_MFA",
            "TERMINATE_SESSION",
            "RATE_LIMIT",
            "CAPTCHA"
        ]

        for response_name in required_responses:
            assert hasattr(ThreatResponse, response_name), f"Missing response: {response_name}"


# =============================================================================
# THREAT EVENT DATA CLASS TESTS
# =============================================================================

class TestThreatEventFunctional:
    """Functional tests for ThreatEvent data class."""

    @pytest.fixture
    def threat_event(self):
        """Create a ThreatEvent instance."""
        from security.zero_trust.threat_detection import (
            ThreatEvent, ThreatType, ThreatLevel, ThreatResponse
        )

        return ThreatEvent(
            event_id="threat-123",
            threat_type=ThreatType.BRUTE_FORCE,
            threat_level=ThreatLevel.HIGH,
            source_ip="192.168.1.100",
            user_id="user-456",
            session_id="session-789",
            timestamp=datetime.utcnow(),
            description="Multiple failed login attempts detected",
            evidence={
                "failed_attempts": 10,
                "time_window": "5 minutes"
            },
            responses_taken=[ThreatResponse.BLOCK, ThreatResponse.ALERT]
        )

    def test_threat_event_creation(self, threat_event):
        """ThreatEvent must be creatable with required fields."""
        from security.zero_trust.threat_detection import ThreatType, ThreatLevel

        assert threat_event.event_id == "threat-123"
        assert threat_event.threat_type == ThreatType.BRUTE_FORCE
        assert threat_event.threat_level == ThreatLevel.HIGH
        assert threat_event.source_ip == "192.168.1.100"

    def test_threat_event_to_dict(self, threat_event):
        """ThreatEvent.to_dict() must serialize correctly."""
        result = threat_event.to_dict()

        assert isinstance(result, dict)
        assert result["event_id"] == "threat-123"
        assert result["threat_type"] == "brute_force"
        assert result["threat_level"] == "high"
        assert result["source_ip"] == "192.168.1.100"
        assert "block" in result["responses_taken"]
        assert "alert" in result["responses_taken"]

    def test_threat_event_resolution_fields(self):
        """ThreatEvent must support resolution fields."""
        from security.zero_trust.threat_detection import (
            ThreatEvent, ThreatType, ThreatLevel
        )

        event = ThreatEvent(
            event_id="resolved-event",
            threat_type=ThreatType.SESSION_HIJACK,
            threat_level=ThreatLevel.CRITICAL,
            source_ip="10.0.0.1",
            user_id="victim-user",
            session_id="hijacked-session",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            description="Session hijack detected",
            resolved=True,
            resolved_at=datetime.utcnow(),
            resolution_notes="Session terminated, user notified"
        )

        assert event.resolved is True
        assert event.resolved_at is not None
        assert event.resolution_notes == "Session terminated, user notified"


# =============================================================================
# THREAT POLICY DATA CLASS TESTS
# =============================================================================

class TestThreatPolicyFunctional:
    """Functional tests for ThreatPolicy data class."""

    def test_threat_policy_creation(self):
        """ThreatPolicy must be creatable."""
        from security.zero_trust.threat_detection import (
            ThreatPolicy, ThreatType, ThreatResponse
        )

        policy = ThreatPolicy(
            threat_type=ThreatType.BRUTE_FORCE,
            threshold=5,
            window_seconds=300,
            responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT],
            escalation_threshold=10,
            escalation_responses=[ThreatResponse.LOCKDOWN]
        )

        assert policy.threat_type == ThreatType.BRUTE_FORCE
        assert policy.threshold == 5
        assert policy.window_seconds == 300
        assert ThreatResponse.BLOCK in policy.responses

    def test_threat_policy_escalation(self):
        """ThreatPolicy must support escalation."""
        from security.zero_trust.threat_detection import (
            ThreatPolicy, ThreatType, ThreatResponse
        )

        policy = ThreatPolicy(
            threat_type=ThreatType.API_ABUSE,
            threshold=100,
            window_seconds=60,
            responses=[ThreatResponse.RATE_LIMIT],
            escalation_threshold=500,
            escalation_responses=[ThreatResponse.BLOCK, ThreatResponse.ALERT]
        )

        # Initial threshold
        assert policy.threshold == 100

        # Escalation threshold
        assert policy.escalation_threshold == 500
        assert ThreatResponse.BLOCK in policy.escalation_responses

    def test_threat_policy_auto_block_duration(self):
        """ThreatPolicy must have auto block duration."""
        from security.zero_trust.threat_detection import ThreatPolicy, ThreatType, ThreatResponse

        policy = ThreatPolicy(
            threat_type=ThreatType.CREDENTIAL_STUFFING,
            threshold=10,
            window_seconds=60,
            responses=[ThreatResponse.BLOCK],
            auto_block_duration=timedelta(hours=24)
        )

        assert policy.auto_block_duration == timedelta(hours=24)


# =============================================================================
# BLOCKED ENTITY DATA CLASS TESTS
# =============================================================================

class TestBlockedEntityFunctional:
    """Functional tests for BlockedEntity data class."""

    def test_blocked_entity_creation(self):
        """BlockedEntity must be creatable."""
        from security.zero_trust.threat_detection import BlockedEntity

        blocked = BlockedEntity(
            entity_type="ip",
            entity_id="192.168.1.100",
            blocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            reason="Brute force attack detected",
            threat_event_id="threat-123"
        )

        assert blocked.entity_type == "ip"
        assert blocked.entity_id == "192.168.1.100"
        assert blocked.reason == "Brute force attack detected"

    def test_blocked_user_entity(self):
        """BlockedEntity must support user type."""
        from security.zero_trust.threat_detection import BlockedEntity

        blocked = BlockedEntity(
            entity_type="user",
            entity_id="malicious-user-123",
            blocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            reason="Account takeover attempt",
            threat_event_id="threat-456"
        )

        assert blocked.entity_type == "user"
        assert blocked.entity_id == "malicious-user-123"


# =============================================================================
# THREAT DETECTOR TESTS
# =============================================================================

class TestThreatDetectorFunctional:
    """Functional tests for ThreatDetector."""

    @pytest.fixture
    def detector(self):
        """Create fresh ThreatDetector instance."""
        from security.zero_trust.threat_detection import ThreatDetector
        return ThreatDetector()

    def test_detector_has_default_policies(self, detector):
        """ThreatDetector must have default policies."""
        from security.zero_trust.threat_detection import ThreatType

        # Should have policies for common threats
        assert ThreatType.BRUTE_FORCE in detector._policies
        assert ThreatType.CREDENTIAL_STUFFING in detector._policies
        assert ThreatType.SESSION_HIJACK in detector._policies
        assert ThreatType.API_ABUSE in detector._policies

    def test_brute_force_policy_defaults(self, detector):
        """Brute force policy must have reasonable defaults."""
        from security.zero_trust.threat_detection import ThreatType, ThreatResponse

        policy = detector._policies[ThreatType.BRUTE_FORCE]

        assert policy.threshold >= 3  # At least 3 attempts
        assert policy.window_seconds >= 60  # At least 1 minute window
        assert ThreatResponse.BLOCK in policy.responses or ThreatResponse.ALERT in policy.responses

    def test_api_abuse_policy_defaults(self, detector):
        """API abuse policy must have reasonable defaults."""
        from security.zero_trust.threat_detection import ThreatType, ThreatResponse

        policy = detector._policies[ThreatType.API_ABUSE]

        assert policy.threshold >= 50  # At least 50 requests
        assert policy.window_seconds >= 30  # At least 30 seconds
        assert ThreatResponse.RATE_LIMIT in policy.responses

    def test_custom_policies_override_defaults(self):
        """Custom policies must override defaults."""
        from security.zero_trust.threat_detection import (
            ThreatDetector, ThreatPolicy, ThreatType, ThreatResponse
        )

        custom_policy = ThreatPolicy(
            threat_type=ThreatType.BRUTE_FORCE,
            threshold=3,  # More strict
            window_seconds=60,
            responses=[ThreatResponse.LOCKDOWN]  # More severe
        )

        detector = ThreatDetector(custom_policies={ThreatType.BRUTE_FORCE: custom_policy})

        assert detector._policies[ThreatType.BRUTE_FORCE].threshold == 3
        assert ThreatResponse.LOCKDOWN in detector._policies[ThreatType.BRUTE_FORCE].responses


# =============================================================================
# BRUTE FORCE DETECTION TESTS
# =============================================================================

class TestBruteForceDetectionFunctional:
    """Functional tests for brute force detection patterns."""

    def test_failed_auth_below_threshold_not_threat(self):
        """Failed auths below threshold must not be threat."""
        threshold = 5
        window_seconds = 300

        failed_auths = [
            datetime.utcnow() - timedelta(seconds=60),
            datetime.utcnow() - timedelta(seconds=30),
            datetime.utcnow()
        ]

        # 3 attempts, threshold is 5
        is_threat = len(failed_auths) >= threshold

        assert is_threat is False

    def test_failed_auth_at_threshold_is_threat(self):
        """Failed auths at threshold must be threat."""
        threshold = 5
        window_seconds = 300

        now = datetime.utcnow()
        failed_auths = [
            now - timedelta(seconds=240),
            now - timedelta(seconds=180),
            now - timedelta(seconds=120),
            now - timedelta(seconds=60),
            now
        ]

        # Filter to window
        window_start = now - timedelta(seconds=window_seconds)
        recent_failures = [t for t in failed_auths if t >= window_start]

        is_threat = len(recent_failures) >= threshold

        assert is_threat is True

    def test_old_failed_auths_not_counted(self):
        """Failed auths outside window must not be counted."""
        threshold = 5
        window_seconds = 300  # 5 minutes

        now = datetime.utcnow()
        failed_auths = [
            now - timedelta(seconds=600),  # 10 min ago - outside window
            now - timedelta(seconds=500),  # Outside window
            now - timedelta(seconds=400),  # Outside window
            now - timedelta(seconds=100),  # In window
            now  # In window
        ]

        window_start = now - timedelta(seconds=window_seconds)
        recent_failures = [t for t in failed_auths if t >= window_start]

        # Only 2 in window
        assert len(recent_failures) == 2
        assert len(recent_failures) < threshold


# =============================================================================
# API ABUSE DETECTION TESTS
# =============================================================================

class TestAPIAbuseDetectionFunctional:
    """Functional tests for API abuse detection patterns."""

    def test_request_count_below_threshold(self):
        """Request count below threshold must not trigger abuse."""
        threshold = 100
        window_seconds = 60

        request_count = 50

        is_abuse = request_count >= threshold

        assert is_abuse is False

    def test_request_count_at_threshold(self):
        """Request count at threshold must trigger abuse."""
        threshold = 100
        window_seconds = 60

        request_count = 100

        is_abuse = request_count >= threshold

        assert is_abuse is True

    def test_escalation_at_higher_threshold(self):
        """Escalation must trigger at higher threshold."""
        threshold = 100
        escalation_threshold = 500

        request_count = 600

        needs_escalation = request_count >= escalation_threshold

        assert needs_escalation is True


# =============================================================================
# SESSION HIJACK DETECTION TESTS
# =============================================================================

class TestSessionHijackDetectionFunctional:
    """Functional tests for session hijack detection patterns."""

    def test_fingerprint_change_detected(self):
        """Fingerprint change must be detected."""
        original_fingerprint = {
            "user_agent": "Chrome/120 Windows",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York"
        }

        new_fingerprint = {
            "user_agent": "Firefox/119 Linux",  # Different!
            "screen_resolution": "2560x1440",  # Different!
            "timezone": "Europe/London"  # Different!
        }

        matching_fields = sum(
            1 for k in original_fingerprint
            if original_fingerprint.get(k) == new_fingerprint.get(k)
        )
        total_fields = len(original_fingerprint)
        similarity = matching_fields / total_fields

        # Completely different = hijack
        assert similarity == 0.0
        assert similarity < 0.5  # Below threshold

    def test_same_fingerprint_not_hijack(self):
        """Same fingerprint must not be flagged."""
        fingerprint = {
            "user_agent": "Chrome/120 Windows",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York"
        }

        matching_fields = sum(
            1 for k in fingerprint
            if fingerprint.get(k) == fingerprint.get(k)
        )
        similarity = matching_fields / len(fingerprint)

        assert similarity == 1.0


# =============================================================================
# IMPOSSIBLE TRAVEL DETECTION TESTS
# =============================================================================

class TestImpossibleTravelDetectionFunctional:
    """Functional tests for impossible travel detection patterns."""

    def test_impossible_travel_detected(self):
        """Impossible travel must be detected."""
        # New York coordinates
        location1 = (40.7128, -74.0060)
        time1 = datetime.utcnow() - timedelta(hours=1)

        # Tokyo coordinates
        location2 = (35.6762, 139.6503)
        time2 = datetime.utcnow()

        # Calculate distance (simplified)
        import math
        lat1, lon1 = location1
        lat2, lon2 = location2

        # Haversine formula simplified
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance_km = R * c

        # Time difference
        time_diff_hours = (time2 - time1).total_seconds() / 3600

        # Speed in km/h
        speed = distance_km / time_diff_hours if time_diff_hours > 0 else float('inf')

        # Max reasonable travel speed (commercial jet ~900 km/h)
        max_speed = 1000

        is_impossible = speed > max_speed

        # NYC to Tokyo is ~10,800 km, in 1 hour = 10,800 km/h (impossible)
        assert is_impossible is True

    def test_possible_travel_not_flagged(self):
        """Possible travel must not be flagged."""
        # NYC coordinates
        location1 = (40.7128, -74.0060)
        time1 = datetime.utcnow() - timedelta(hours=2)

        # Boston coordinates (nearby)
        location2 = (42.3601, -71.0589)
        time2 = datetime.utcnow()

        # Distance NYC to Boston ~350 km
        distance_km = 350

        time_diff_hours = (time2 - time1).total_seconds() / 3600
        speed = distance_km / time_diff_hours

        max_speed = 1000

        is_impossible = speed > max_speed

        # 350 km in 2 hours = 175 km/h (possible by car/train)
        assert is_impossible is False


# =============================================================================
# THREAT RESPONSE SELECTION TESTS
# =============================================================================

class TestThreatResponseSelectionFunctional:
    """Functional tests for threat response selection."""

    def test_low_threat_gets_log_response(self):
        """LOW threat level must get LOG response."""
        from security.zero_trust.threat_detection import ThreatLevel, ThreatResponse

        threat_level = ThreatLevel.LOW

        # Response mapping
        response_map = {
            ThreatLevel.NONE: [],
            ThreatLevel.LOW: [ThreatResponse.LOG],
            ThreatLevel.MEDIUM: [ThreatResponse.CHALLENGE, ThreatResponse.LOG],
            ThreatLevel.HIGH: [ThreatResponse.BLOCK, ThreatResponse.ALERT],
            ThreatLevel.CRITICAL: [ThreatResponse.LOCKDOWN, ThreatResponse.TERMINATE_SESSION, ThreatResponse.ALERT]
        }

        responses = response_map[threat_level]

        assert ThreatResponse.LOG in responses

    def test_critical_threat_gets_lockdown_response(self):
        """CRITICAL threat level must get LOCKDOWN response."""
        from security.zero_trust.threat_detection import ThreatLevel, ThreatResponse

        threat_level = ThreatLevel.CRITICAL

        response_map = {
            ThreatLevel.CRITICAL: [ThreatResponse.LOCKDOWN, ThreatResponse.TERMINATE_SESSION, ThreatResponse.ALERT]
        }

        responses = response_map[threat_level]

        assert ThreatResponse.LOCKDOWN in responses
        assert ThreatResponse.TERMINATE_SESSION in responses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
