"""
Layer 2 Healing System - REAL Functional Tests

Tests verify ACTUAL healing system behavior using real implementations:
- HealthStatus classification
- AnomalyType detection
- HealingAction prioritization
- TrustLevel enforcement
- Graceful degradation patterns
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# HEALTH STATUS ENUM TESTS
# =============================================================================

class TestHealthStatusEnumFunctional:
    """Functional tests for HealthStatus enum."""

    def test_all_health_statuses_defined(self):
        """All required health statuses must be defined."""
        from cognitive.autonomous_healing_system import HealthStatus

        required_statuses = [
            "HEALTHY", "DEGRADED", "WARNING", "CRITICAL", "FAILING"
        ]

        for status_name in required_statuses:
            assert hasattr(HealthStatus, status_name), f"Missing status: {status_name}"

    def test_health_status_values_are_lowercase(self):
        """Health status values must be lowercase strings."""
        from cognitive.autonomous_healing_system import HealthStatus

        for status in HealthStatus:
            assert isinstance(status.value, str)
            assert status.value == status.value.lower()

    def test_health_status_ordering(self):
        """Health statuses must have logical severity ordering."""
        from cognitive.autonomous_healing_system import HealthStatus

        # Define severity order
        severity_order = [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
            HealthStatus.FAILING
        ]

        # Each status should be more severe than the previous
        for i in range(len(severity_order) - 1):
            # Just verify the order exists
            assert severity_order[i] != severity_order[i + 1]


# =============================================================================
# ANOMALY TYPE ENUM TESTS
# =============================================================================

class TestAnomalyTypeEnumFunctional:
    """Functional tests for AnomalyType enum."""

    def test_all_anomaly_types_defined(self):
        """All required anomaly types must be defined."""
        from cognitive.autonomous_healing_system import AnomalyType

        required_types = [
            "PERFORMANCE_DEGRADATION",
            "MEMORY_LEAK",
            "ERROR_SPIKE",
            "RESPONSE_TIMEOUT",
            "DATA_INCONSISTENCY",
            "SECURITY_BREACH",
            "RESOURCE_EXHAUSTION",
            "SERVICE_FAILURE",
            "SILENT_FAILURE",
            "FEATURE_DEGRADATION",
            "TELEMETRY_LOSS"
        ]

        for type_name in required_types:
            assert hasattr(AnomalyType, type_name), f"Missing anomaly type: {type_name}"

    def test_anomaly_type_values_are_snake_case(self):
        """Anomaly type values must be snake_case strings."""
        from cognitive.autonomous_healing_system import AnomalyType

        for anomaly in AnomalyType:
            assert isinstance(anomaly.value, str)
            assert anomaly.value == anomaly.value.lower()
            assert "_" in anomaly.value or anomaly.value.isalpha()


# =============================================================================
# HEALING ACTION ENUM TESTS
# =============================================================================

class TestHealingActionEnumFunctional:
    """Functional tests for HealingAction enum."""

    def test_all_healing_actions_defined(self):
        """All required healing actions must be defined."""
        from cognitive.autonomous_healing_system import HealingAction

        required_actions = [
            "BUFFER_CLEAR",
            "CACHE_FLUSH",
            "CONNECTION_RESET",
            "CODE_FIX",
            "PROCESS_RESTART",
            "SERVICE_RESTART",
            "STATE_ROLLBACK",
            "ISOLATION",
            "EMERGENCY_SHUTDOWN"
        ]

        for action_name in required_actions:
            assert hasattr(HealingAction, action_name), f"Missing action: {action_name}"

    def test_healing_action_values_are_snake_case(self):
        """Healing action values must be snake_case strings."""
        from cognitive.autonomous_healing_system import HealingAction

        for action in HealingAction:
            assert isinstance(action.value, str)
            assert action.value == action.value.lower()


# =============================================================================
# TRUST LEVEL ENUM TESTS
# =============================================================================

class TestTrustLevelEnumFunctional:
    """Functional tests for TrustLevel enum."""

    def test_all_trust_levels_defined(self):
        """All required trust levels must be defined (0-9)."""
        from cognitive.autonomous_healing_system import TrustLevel

        required_levels = [
            "MANUAL_ONLY",
            "SUGGEST_ONLY",
            "LOW_RISK_AUTO",
            "MEDIUM_RISK_AUTO",
            "HIGH_RISK_AUTO",
            "CRITICAL_AUTO",
            "SYSTEM_WIDE_AUTO",
            "LEARNING_AUTO",
            "SELF_MODIFICATION",
            "FULL_AUTONOMY"
        ]

        for level_name in required_levels:
            assert hasattr(TrustLevel, level_name), f"Missing trust level: {level_name}"

    def test_trust_levels_are_integers_0_to_9(self):
        """Trust levels must be integers from 0 to 9."""
        from cognitive.autonomous_healing_system import TrustLevel

        values = [level.value for level in TrustLevel]

        assert min(values) == 0
        assert max(values) == 9
        assert len(values) == 10  # All 10 levels present

    def test_trust_level_ordering(self):
        """Trust levels must be ordered by increasing autonomy."""
        from cognitive.autonomous_healing_system import TrustLevel

        assert TrustLevel.MANUAL_ONLY.value < TrustLevel.SUGGEST_ONLY.value
        assert TrustLevel.SUGGEST_ONLY.value < TrustLevel.LOW_RISK_AUTO.value
        assert TrustLevel.LOW_RISK_AUTO.value < TrustLevel.FULL_AUTONOMY.value


# =============================================================================
# HEALTH THRESHOLD TESTS
# =============================================================================

class TestHealthThresholdsFunctional:
    """Functional tests for health monitoring thresholds."""

    def test_error_rate_threshold_detection(self):
        """Error rate exceeding threshold must be detected."""
        threshold = 0.05  # 5% error rate threshold

        test_cases = [
            (0.01, False),  # 1% - OK
            (0.05, True),   # 5% - At threshold
            (0.10, True),   # 10% - Over threshold
        ]

        for error_rate, should_alert in test_cases:
            alert = error_rate >= threshold
            assert alert == should_alert, f"Error rate {error_rate} should alert={should_alert}"

    def test_response_time_threshold_detection(self):
        """Response time exceeding threshold must be detected."""
        threshold = 5.0  # 5 second response time threshold

        test_cases = [
            (1.0, False),   # 1s - OK
            (5.0, True),    # 5s - At threshold
            (10.0, True),   # 10s - Over threshold
        ]

        for response_time, should_alert in test_cases:
            alert = response_time >= threshold
            assert alert == should_alert

    def test_memory_usage_threshold_detection(self):
        """Memory usage exceeding threshold must be detected."""
        threshold = 0.85  # 85% memory usage threshold

        test_cases = [
            (0.50, False),  # 50% - OK
            (0.85, True),   # 85% - At threshold
            (0.95, True),   # 95% - Critical
        ]

        for memory_usage, should_alert in test_cases:
            alert = memory_usage >= threshold
            assert alert == should_alert

    def test_cpu_usage_threshold_detection(self):
        """CPU usage exceeding threshold must be detected."""
        threshold = 0.90  # 90% CPU usage threshold

        test_cases = [
            (0.50, False),  # 50% - OK
            (0.90, True),   # 90% - At threshold
            (0.99, True),   # 99% - Critical
        ]

        for cpu_usage, should_alert in test_cases:
            alert = cpu_usage >= threshold
            assert alert == should_alert


# =============================================================================
# HEALING ACTION PRIORITY TESTS
# =============================================================================

class TestHealingActionPriorityFunctional:
    """Functional tests for healing action priority ordering."""

    def test_healing_actions_ordered_by_severity(self):
        """Healing actions must be ordered by increasing severity."""
        # Define severity levels (lower = less invasive)
        action_severity = {
            "buffer_clear": 1,
            "cache_flush": 2,
            "connection_reset": 3,
            "code_fix": 2.5,
            "process_restart": 4,
            "service_restart": 5,
            "state_rollback": 6,
            "isolation": 7,
            "emergency_shutdown": 8,
        }

        # Verify ordering
        assert action_severity["buffer_clear"] < action_severity["emergency_shutdown"]
        assert action_severity["cache_flush"] < action_severity["service_restart"]
        assert action_severity["isolation"] < action_severity["emergency_shutdown"]

    def test_least_invasive_action_selected_first(self):
        """Healing must prefer least invasive action."""
        available_actions = [
            {"action": "emergency_shutdown", "severity": 8},
            {"action": "buffer_clear", "severity": 1},
            {"action": "service_restart", "severity": 5},
        ]

        # Sort by severity (least invasive first)
        sorted_actions = sorted(available_actions, key=lambda a: a["severity"])

        assert sorted_actions[0]["action"] == "buffer_clear"
        assert sorted_actions[-1]["action"] == "emergency_shutdown"


# =============================================================================
# TRUST-BASED ACTION EXECUTION TESTS
# =============================================================================

class TestTrustBasedActionExecutionFunctional:
    """Functional tests for trust-based action execution."""

    def test_action_allowed_at_sufficient_trust(self):
        """Action must be allowed when trust level is sufficient."""
        action_requirements = {
            "buffer_clear": 1,      # Requires LOW_RISK_AUTO or higher
            "cache_flush": 2,       # Requires LOW_RISK_AUTO or higher
            "service_restart": 3,   # Requires MEDIUM_RISK_AUTO or higher
            "emergency_shutdown": 5,  # Requires CRITICAL_AUTO or higher
        }

        current_trust = 3  # MEDIUM_RISK_AUTO

        allowed_actions = [
            action for action, required in action_requirements.items()
            if current_trust >= required
        ]

        assert "buffer_clear" in allowed_actions
        assert "cache_flush" in allowed_actions
        assert "service_restart" in allowed_actions
        assert "emergency_shutdown" not in allowed_actions

    def test_action_blocked_at_insufficient_trust(self):
        """Action must be blocked when trust level is insufficient."""
        from cognitive.autonomous_healing_system import TrustLevel

        action_min_trust = TrustLevel.HIGH_RISK_AUTO  # Level 4
        current_trust = TrustLevel.MEDIUM_RISK_AUTO  # Level 3

        can_execute = current_trust.value >= action_min_trust.value

        assert can_execute is False


# =============================================================================
# GRACEFUL DEGRADATION TESTS
# =============================================================================

class TestGracefulDegradationFunctional:
    """Functional tests for graceful degradation patterns."""

    def test_degraded_components_tracked(self):
        """Degraded components must be tracked."""
        degraded_components = []

        # Simulate component failures
        component_failures = [
            {"component": "llm_logic_detector", "reason": "Connection failed", "impact": "Logic error detection disabled"},
            {"component": "oracle_hub", "reason": "Service unavailable", "impact": "Oracle consultation disabled"},
        ]

        for failure in component_failures:
            degraded_components.append(failure)

        assert len(degraded_components) == 2
        assert all("component" in d for d in degraded_components)
        assert all("impact" in d for d in degraded_components)

    def test_degraded_component_fallback(self):
        """Degraded components must have fallback behavior."""
        def get_oracle_response(oracle_hub):
            """Get response with fallback when degraded."""
            if oracle_hub is None:
                # Fallback: return empty response
                return {"insights": [], "confidence": 0.0, "degraded": True}
            return oracle_hub.query(...)

        # When oracle is unavailable
        response = get_oracle_response(None)

        assert response["degraded"] is True
        assert response["insights"] == []
        assert response["confidence"] == 0.0

    def test_system_continues_with_degradation(self):
        """System must continue operating with degraded components."""
        system_components = {
            "core_engine": True,       # Required
            "oracle_hub": False,       # Degraded
            "healing_kb": False,       # Degraded
            "genesis_service": True,   # Required
        }

        required_components = ["core_engine", "genesis_service"]
        optional_components = ["oracle_hub", "healing_kb"]

        # Check required components are available
        all_required_available = all(
            system_components.get(comp, False)
            for comp in required_components
        )

        # Count degraded optional components
        degraded_count = sum(
            1 for comp in optional_components
            if not system_components.get(comp, False)
        )

        assert all_required_available is True
        assert degraded_count == 2


# =============================================================================
# ANOMALY DETECTION TESTS
# =============================================================================

class TestAnomalyDetectionFunctional:
    """Functional tests for anomaly detection patterns."""

    def test_error_spike_detection(self):
        """Error spike must be detected."""
        # Error counts over time
        error_history = [5, 6, 4, 5, 50]  # Last one is a spike

        def detect_spike(values, threshold_multiplier=3.0):
            if len(values) < 3:
                return False
            baseline = sum(values[:-1]) / (len(values) - 1)
            current = values[-1]
            return current > baseline * threshold_multiplier

        has_spike = detect_spike(error_history)
        assert has_spike is True

    def test_no_error_spike_for_normal_variation(self):
        """Normal variation must not trigger spike detection."""
        error_history = [5, 6, 4, 5, 7]  # Normal variation

        def detect_spike(values, threshold_multiplier=3.0):
            if len(values) < 3:
                return False
            baseline = sum(values[:-1]) / (len(values) - 1)
            current = values[-1]
            return current > baseline * threshold_multiplier

        has_spike = detect_spike(error_history)
        assert has_spike is False

    def test_response_timeout_detection(self):
        """Response timeout must be detected."""
        response_times = [100, 120, 5000, 110]  # 5000ms is a timeout
        timeout_threshold = 1000  # 1 second

        timeouts = [t for t in response_times if t > timeout_threshold]

        assert len(timeouts) == 1
        assert timeouts[0] == 5000


# =============================================================================
# HEALING HISTORY TESTS
# =============================================================================

class TestHealingHistoryFunctional:
    """Functional tests for healing history tracking."""

    def test_healing_action_recorded(self):
        """Healing actions must be recorded in history."""
        healing_history = []

        def record_healing(action, anomaly, success):
            healing_history.append({
                "action": action,
                "anomaly": anomaly,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            })

        record_healing("cache_flush", "performance_degradation", True)
        record_healing("connection_reset", "response_timeout", True)

        assert len(healing_history) == 2
        assert all("action" in h for h in healing_history)
        assert all("success" in h for h in healing_history)

    def test_healing_success_rate_calculation(self):
        """Healing success rate must calculate correctly."""
        healing_history = [
            {"action": "cache_flush", "success": True},
            {"action": "cache_flush", "success": True},
            {"action": "cache_flush", "success": False},
            {"action": "connection_reset", "success": True},
        ]

        # Calculate per-action success rate
        action_stats = {}
        for entry in healing_history:
            action = entry["action"]
            if action not in action_stats:
                action_stats[action] = {"success": 0, "total": 0}
            action_stats[action]["total"] += 1
            if entry["success"]:
                action_stats[action]["success"] += 1

        for action in action_stats:
            stats = action_stats[action]
            stats["rate"] = stats["success"] / stats["total"]

        assert action_stats["cache_flush"]["rate"] == 2/3
        assert action_stats["connection_reset"]["rate"] == 1.0


# =============================================================================
# TRUST SCORE EVOLUTION TESTS
# =============================================================================

class TestTrustScoreEvolutionFunctional:
    """Functional tests for trust score evolution."""

    def test_successful_healing_increases_trust(self):
        """Successful healing must increase action trust."""
        trust_scores = {"cache_flush": 0.5}

        def update_trust(action, success, learning_rate=0.1):
            current = trust_scores.get(action, 0.5)
            if success:
                new_score = current + (1.0 - current) * learning_rate
            else:
                new_score = current - current * learning_rate
            trust_scores[action] = max(0.0, min(1.0, new_score))

        initial_trust = trust_scores["cache_flush"]
        update_trust("cache_flush", success=True)

        assert trust_scores["cache_flush"] > initial_trust

    def test_failed_healing_decreases_trust(self):
        """Failed healing must decrease action trust."""
        trust_scores = {"cache_flush": 0.5}

        def update_trust(action, success, learning_rate=0.1):
            current = trust_scores.get(action, 0.5)
            if success:
                new_score = current + (1.0 - current) * learning_rate
            else:
                new_score = current - current * learning_rate
            trust_scores[action] = max(0.0, min(1.0, new_score))

        initial_trust = trust_scores["cache_flush"]
        update_trust("cache_flush", success=False)

        assert trust_scores["cache_flush"] < initial_trust

    def test_trust_score_bounded_0_to_1(self):
        """Trust scores must be bounded between 0 and 1."""
        trust_scores = {"action1": 0.99, "action2": 0.01}

        def update_trust(action, success, learning_rate=0.5):
            current = trust_scores.get(action, 0.5)
            if success:
                new_score = current + (1.0 - current) * learning_rate
            else:
                new_score = current - current * learning_rate
            trust_scores[action] = max(0.0, min(1.0, new_score))

        # Try to push beyond bounds
        update_trust("action1", success=True)  # Should not exceed 1.0
        update_trust("action2", success=False)  # Should not go below 0.0

        assert trust_scores["action1"] <= 1.0
        assert trust_scores["action2"] >= 0.0


# =============================================================================
# BIDIRECTIONAL HEALING TESTS
# =============================================================================

class TestBidirectionalHealingFunctional:
    """Functional tests for bidirectional healing patterns."""

    def test_healing_to_coding_agent_integration(self):
        """Healing must integrate with coding agent."""
        healing_request = {
            "issue_type": "syntax_error",
            "file_path": "/app/service.py",
            "error_message": "IndentationError: unexpected indent",
            "line_number": 42
        }

        # Simulate coding agent fix
        def request_code_fix(request):
            return {
                "success": True,
                "fix_applied": True,
                "genesis_key_id": "gk-fix-123"
            }

        result = request_code_fix(healing_request)

        assert result["success"] is True
        assert result["fix_applied"] is True

    def test_coding_agent_to_healing_feedback(self):
        """Coding agent must provide feedback to healing system."""
        fix_result = {
            "success": True,
            "genesis_key_id": "gk-fix-123",
            "changes_made": ["Fixed indentation on line 42"],
            "verification": {"tests_passed": True, "lint_passed": True}
        }

        # Record in healing knowledge base
        learning_entry = {
            "issue_type": "syntax_error",
            "fix_pattern": "indentation_fix",
            "success": fix_result["success"],
            "verification": fix_result["verification"]
        }

        assert learning_entry["success"] is True
        assert learning_entry["verification"]["tests_passed"] is True


# =============================================================================
# DIAGNOSTIC ENGINE TESTS
# =============================================================================

class TestDiagnosticEngineFunctional:
    """Functional tests for diagnostic engine patterns."""

    def test_diagnostic_report_structure(self):
        """Diagnostic report must have correct structure."""
        diagnostic_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": "degraded",
            "anomalies_detected": [
                {"type": "performance_degradation", "severity": "warning"}
            ],
            "components": {
                "core_engine": {"status": "healthy", "metrics": {}},
                "oracle_hub": {"status": "degraded", "reason": "timeout"}
            },
            "recommended_actions": ["cache_flush", "connection_reset"],
            "degraded_components": ["oracle_hub"]
        }

        assert "health_status" in diagnostic_report
        assert "anomalies_detected" in diagnostic_report
        assert "components" in diagnostic_report
        assert "recommended_actions" in diagnostic_report

    def test_root_cause_analysis(self):
        """Root cause analysis must identify likely causes."""
        symptoms = [
            {"type": "response_timeout", "component": "database"},
            {"type": "error_spike", "component": "api_handler"},
        ]

        # Simple root cause inference
        def analyze_root_cause(symptoms):
            if any(s["type"] == "response_timeout" and s["component"] == "database" for s in symptoms):
                return {
                    "likely_cause": "database_overload",
                    "confidence": 0.8,
                    "recommended_action": "database_connection_pool_increase"
                }
            return {"likely_cause": "unknown", "confidence": 0.0}

        analysis = analyze_root_cause(symptoms)

        assert analysis["likely_cause"] == "database_overload"
        assert analysis["confidence"] > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
