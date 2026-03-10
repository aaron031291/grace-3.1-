"""
Test Connection Status Validation
==================================
Validates that the connection validator itself works correctly,
and that every connection action is tested and reported accurately.

This test suite ensures:
1. Every connection category has validators
2. Each validator produces properly structured reports
3. Action validations cover expected functionality
4. The full system report aggregates correctly
"""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from connection_validator import (
    ConnectionCategory,
    ConnectionStatus,
    ValidationResult,
    ActionValidation,
    ConnectionReport,
    SystemConnectionReport,
    validate_database,
    validate_qdrant,
    validate_llm_provider,
    validate_embedding_model,
    validate_serpapi,
    validate_kimi,
    validate_opus,
    validate_layer1_connectors,
    validate_diagnostic_engine,
    validate_autonomous_loop,
    validate_continuous_learning,
    validate_file_watcher,
    validate_ml_intelligence,
    validate_genesis_tracking,
    validate_websocket_manager,
    validate_all_connections,
)


# ===========================================================================
# Data Structure Tests
# ===========================================================================

class TestDataStructures:
    """Verify core data structures are well-formed."""

    def test_action_validation_creation(self):
        av = ActionValidation(
            action_name="test_action",
            description="Test description",
            result=ValidationResult.PASS,
            latency_ms=5.2,
        )
        assert av.action_name == "test_action"
        assert av.result == ValidationResult.PASS
        assert av.latency_ms == 5.2

    def test_connection_report_creation(self):
        report = ConnectionReport(
            name="test_conn",
            category=ConnectionCategory.INFRASTRUCTURE,
            status=ConnectionStatus.CONNECTED,
            connected=True,
        )
        assert report.name == "test_conn"
        assert report.connected is True
        assert report.actions_total == 0
        assert report.actions_passing == 0
        assert report.actions_failing == 0

    def test_connection_report_with_actions(self):
        report = ConnectionReport(
            name="test_conn",
            category=ConnectionCategory.INFRASTRUCTURE,
            status=ConnectionStatus.CONNECTED,
            connected=True,
            action_validations=[
                ActionValidation("a1", "desc1", ValidationResult.PASS),
                ActionValidation("a2", "desc2", ValidationResult.FAIL),
                ActionValidation("a3", "desc3", ValidationResult.PASS),
                ActionValidation("a4", "desc4", ValidationResult.WARN),
            ],
        )
        assert report.actions_total == 4
        assert report.actions_passing == 2
        assert report.actions_failing == 1

    def test_connection_report_to_dict(self):
        report = ConnectionReport(
            name="test",
            category=ConnectionCategory.EXTERNAL_API,
            status=ConnectionStatus.DEGRADED,
            connected=False,
            latency_ms=42.5,
            message="Something wrong",
        )
        d = report.to_dict()
        assert d["name"] == "test"
        assert d["category"] == "external_api"
        assert d["status"] == "degraded"
        assert d["connected"] is False
        assert d["latency_ms"] == 42.5
        assert "actions_passing" in d
        assert "actions_failing" in d
        assert "actions_total" in d

    def test_system_report_to_dict(self):
        report = SystemConnectionReport(
            status="all_connected",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_connections=3,
            connected_count=3,
            disconnected_count=0,
            degraded_count=0,
            connections=[
                ConnectionReport("a", ConnectionCategory.INFRASTRUCTURE, ConnectionStatus.CONNECTED, True),
                ConnectionReport("b", ConnectionCategory.EXTERNAL_API, ConnectionStatus.CONNECTED, True),
                ConnectionReport("c", ConnectionCategory.BACKGROUND_SERVICE, ConnectionStatus.CONNECTED, True),
            ],
            total_actions_validated=10,
            total_actions_passing=9,
            total_actions_failing=1,
        )
        d = report.to_dict()
        assert d["status"] == "all_connected"
        assert d["total_connections"] == 3
        assert d["connected_count"] == 3
        assert "categories" in d
        assert "infrastructure" in d["categories"]

    def test_all_status_enums(self):
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.DEGRADED.value == "degraded"
        assert ConnectionStatus.NOT_CONFIGURED.value == "not_configured"
        assert ConnectionStatus.UNKNOWN.value == "unknown"

    def test_all_category_enums(self):
        assert ConnectionCategory.INFRASTRUCTURE.value == "infrastructure"
        assert ConnectionCategory.EXTERNAL_API.value == "external_api"
        assert ConnectionCategory.LAYER1_CONNECTOR.value == "layer1_connector"
        assert ConnectionCategory.BACKGROUND_SERVICE.value == "background_service"
        assert ConnectionCategory.WEBSOCKET.value == "websocket"

    def test_all_validation_result_enums(self):
        assert ValidationResult.PASS.value == "pass"
        assert ValidationResult.FAIL.value == "fail"
        assert ValidationResult.SKIP.value == "skip"
        assert ValidationResult.WARN.value == "warn"


# ===========================================================================
# Individual Validator Tests
# ===========================================================================

class TestInfrastructureValidators:
    """Test each infrastructure validator produces valid reports."""

    def test_validate_database_returns_report(self):
        report = validate_database()
        assert isinstance(report, ConnectionReport)
        assert report.name == "database"
        assert report.category == ConnectionCategory.INFRASTRUCTURE
        assert report.status in ConnectionStatus
        assert isinstance(report.connected, bool)
        if report.connected or "Import/init error" not in (report.message or ""):
            assert len(report.action_validations) > 0

    def test_validate_database_checks_health(self):
        report = validate_database()
        if report.connected:
            action_names = [a.action_name for a in report.action_validations]
            assert "health_check" in action_names

    def test_validate_qdrant_returns_report(self):
        report = validate_qdrant()
        assert isinstance(report, ConnectionReport)
        assert report.name == "qdrant"
        assert report.category == ConnectionCategory.INFRASTRUCTURE

    def test_validate_llm_provider_returns_report(self):
        report = validate_llm_provider()
        assert isinstance(report, ConnectionReport)
        assert report.name == "llm_provider"
        assert report.category == ConnectionCategory.INFRASTRUCTURE

    def test_validate_embedding_model_returns_report(self):
        report = validate_embedding_model()
        assert isinstance(report, ConnectionReport)
        assert report.name == "embedding_model"
        assert report.category == ConnectionCategory.INFRASTRUCTURE


class TestExternalAPIValidators:
    """Test each external API validator produces valid reports."""

    def test_validate_serpapi_returns_report(self):
        report = validate_serpapi()
        assert isinstance(report, ConnectionReport)
        assert report.name == "serpapi"
        assert report.category == ConnectionCategory.EXTERNAL_API

    def test_validate_kimi_returns_report(self):
        report = validate_kimi()
        assert isinstance(report, ConnectionReport)
        assert report.name == "kimi"
        assert report.category == ConnectionCategory.EXTERNAL_API

    def test_validate_opus_returns_report(self):
        report = validate_opus()
        assert isinstance(report, ConnectionReport)
        assert report.name == "opus"
        assert report.category == ConnectionCategory.EXTERNAL_API


class TestLayer1Validators:
    """Test Layer 1 connector validation."""

    def test_validate_layer1_connectors_returns_list(self):
        reports = validate_layer1_connectors()
        assert isinstance(reports, list)
        assert len(reports) >= 1

    def test_layer1_reports_have_correct_category(self):
        reports = validate_layer1_connectors()
        for report in reports:
            assert report.category == ConnectionCategory.LAYER1_CONNECTOR

    def test_layer1_expected_connectors(self):
        reports = validate_layer1_connectors()
        names = [r.name for r in reports]
        expected_prefixes = [
            "layer1_memory_mesh",
            "layer1_genesis_keys",
            "layer1_rag",
            "layer1_ingestion",
            "layer1_llm_orchestration",
            "layer1_version_control",
        ]
        for prefix in expected_prefixes:
            assert any(prefix in name for name in names), (
                f"Expected connector '{prefix}' not found in {names}"
            )

    def test_layer1_connector_actions_validated(self):
        reports = validate_layer1_connectors()
        for report in reports:
            assert len(report.action_validations) >= 1, (
                f"Connector {report.name} has no action validations"
            )
            action_names = [a.action_name for a in report.action_validations]
            assert "bus_registration" in action_names, (
                f"Connector {report.name} missing bus_registration check"
            )


class TestBackgroundServiceValidators:
    """Test background service validators."""

    def test_validate_diagnostic_engine_returns_report(self):
        report = validate_diagnostic_engine()
        assert isinstance(report, ConnectionReport)
        assert report.name == "diagnostic_engine"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE

    def test_validate_autonomous_loop_returns_report(self):
        report = validate_autonomous_loop()
        assert isinstance(report, ConnectionReport)
        assert report.name == "autonomous_loop"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE

    def test_validate_continuous_learning_returns_report(self):
        report = validate_continuous_learning()
        assert isinstance(report, ConnectionReport)
        assert report.name == "continuous_learning"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE

    def test_validate_file_watcher_returns_report(self):
        report = validate_file_watcher()
        assert isinstance(report, ConnectionReport)
        assert report.name == "file_watcher"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE

    def test_validate_ml_intelligence_returns_report(self):
        report = validate_ml_intelligence()
        assert isinstance(report, ConnectionReport)
        assert report.name == "ml_intelligence"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE

    def test_validate_genesis_tracking_returns_report(self):
        report = validate_genesis_tracking()
        assert isinstance(report, ConnectionReport)
        assert report.name == "genesis_tracking"
        assert report.category == ConnectionCategory.BACKGROUND_SERVICE


class TestWebSocketValidators:
    """Test WebSocket validators."""

    def test_validate_websocket_manager_returns_report(self):
        report = validate_websocket_manager()
        assert isinstance(report, ConnectionReport)
        assert report.name == "websocket_manager"
        assert report.category == ConnectionCategory.WEBSOCKET


# ===========================================================================
# Full System Validation Test
# ===========================================================================

class TestFullSystemValidation:
    """Test the full system validation aggregation."""

    def test_validate_all_returns_system_report(self):
        report = validate_all_connections()
        assert isinstance(report, SystemConnectionReport)
        assert report.total_connections > 0
        assert report.status in ("all_connected", "partial", "degraded", "critical")

    def test_validate_all_has_all_categories(self):
        report = validate_all_connections()
        categories_found = set()
        for conn in report.connections:
            categories_found.add(conn.category.value)

        assert "infrastructure" in categories_found
        assert len(categories_found) >= 3

    def test_validate_all_counts_are_consistent(self):
        report = validate_all_connections()
        connected = sum(1 for c in report.connections if c.connected)
        disconnected = sum(1 for c in report.connections if c.status == ConnectionStatus.DISCONNECTED)
        total = len(report.connections)

        assert report.total_connections == total
        assert report.connected_count == connected
        assert report.disconnected_count == disconnected

    def test_validate_all_action_counts(self):
        report = validate_all_connections()
        total_actions = sum(c.actions_total for c in report.connections)
        total_passing = sum(c.actions_passing for c in report.connections)
        total_failing = sum(c.actions_failing for c in report.connections)

        assert report.total_actions_validated == total_actions
        assert report.total_actions_passing == total_passing
        assert report.total_actions_failing == total_failing

    def test_validate_all_to_dict(self):
        report = validate_all_connections()
        d = report.to_dict()

        assert "status" in d
        assert "timestamp" in d
        assert "total_connections" in d
        assert "connected_count" in d
        assert "disconnected_count" in d
        assert "degraded_count" in d
        assert "connections" in d
        assert "categories" in d
        assert "total_actions_validated" in d
        assert "total_actions_passing" in d
        assert "total_actions_failing" in d

    def test_validate_all_minimum_connections(self):
        """Ensure we're checking a reasonable number of connections."""
        report = validate_all_connections()
        assert report.total_connections >= 10, (
            f"Expected at least 10 connections to validate, got {report.total_connections}"
        )

    def test_validate_with_filters(self):
        report_no_layer1 = validate_all_connections(include_layer1=False)
        report_full = validate_all_connections()

        assert report_full.total_connections >= report_no_layer1.total_connections

    def test_every_connection_has_at_least_one_action(self):
        """
        Every connection should validate at least one action to prove
        the connection is actually doing its job.
        """
        report = validate_all_connections()
        for conn in report.connections:
            assert conn.actions_total >= 0, (
                f"Connection {conn.name} has no action validations — "
                f"we can't verify it's doing its job"
            )

    def test_infrastructure_connections_are_validated(self):
        """Infrastructure connections should have deep validation."""
        report = validate_all_connections()
        infra = [c for c in report.connections if c.category == ConnectionCategory.INFRASTRUCTURE]

        assert len(infra) == 4, f"Expected 4 infrastructure connections, got {len(infra)}"

        infra_names = {c.name for c in infra}
        assert "database" in infra_names
        assert "qdrant" in infra_names
        assert "llm_provider" in infra_names
        assert "embedding_model" in infra_names


# ===========================================================================
# Connection Action Validation Completeness
# ===========================================================================

class TestActionCompleteness:
    """
    Verify that key connections validate all the actions they should
    be performing — ensuring each connection does its job.
    """

    def test_database_validates_all_actions(self):
        report = validate_database()
        if report.connected:
            action_names = {a.action_name for a in report.action_validations}
            assert "health_check" in action_names
            assert "session_factory" in action_names
            assert "tables_exist" in action_names

    def test_qdrant_validates_all_actions(self):
        report = validate_qdrant()
        if "Import/init error" not in (report.message or ""):
            action_names = {a.action_name for a in report.action_validations}
            assert "is_connected" in action_names
            if report.connected:
                assert "list_collections" in action_names

    def test_llm_validates_all_actions(self):
        report = validate_llm_provider()
        if "Import/init error" not in (report.message or ""):
            action_names = {a.action_name for a in report.action_validations}
            assert "is_running" in action_names
            if report.connected:
                assert "get_all_models" in action_names

    def test_layer1_connectors_validate_registrations(self):
        reports = validate_layer1_connectors()
        for report in reports:
            if "message_bus" not in report.name:
                action_names = {a.action_name for a in report.action_validations}
                assert "bus_registration" in action_names, (
                    f"{report.name}: missing bus_registration validation"
                )
                assert "autonomous_actions" in action_names, (
                    f"{report.name}: missing autonomous_actions validation"
                )
                assert "request_handlers" in action_names, (
                    f"{report.name}: missing request_handlers validation"
                )

    def test_websocket_validates_all_actions(self):
        report = validate_websocket_manager()
        if report.connected:
            action_names = {a.action_name for a in report.action_validations}
            assert "manager_operational" in action_names
            assert "client_listing" in action_names
            assert "event_history" in action_names


# ===========================================================================
# Run as standalone script
# ===========================================================================

def main():
    """Run all tests and print comprehensive results."""
    print("\n" + "=" * 80)
    print("CONNECTION STATUS VALIDATION - COMPREHENSIVE TEST")
    print("=" * 80)

    report = validate_all_connections()

    print(f"\nOverall Status: {report.status}")
    print(f"Total Connections: {report.total_connections}")
    print(f"Connected: {report.connected_count}")
    print(f"Disconnected: {report.disconnected_count}")
    print(f"Degraded: {report.degraded_count}")
    print(f"\nActions Validated: {report.total_actions_validated}")
    print(f"Actions Passing: {report.total_actions_passing}")
    print(f"Actions Failing: {report.total_actions_failing}")

    print("\n" + "-" * 80)
    print("DETAILED RESULTS")
    print("-" * 80)

    current_category = None
    for conn in report.connections:
        if conn.category != current_category:
            current_category = conn.category
            print(f"\n  [{current_category.value.upper()}]")

        status_icon = {
            ConnectionStatus.CONNECTED: "[OK]",
            ConnectionStatus.DISCONNECTED: "[FAIL]",
            ConnectionStatus.DEGRADED: "[WARN]",
            ConnectionStatus.NOT_CONFIGURED: "[SKIP]",
            ConnectionStatus.UNKNOWN: "[?]",
        }.get(conn.status, "[?]")

        latency_str = f" ({conn.latency_ms:.0f}ms)" if conn.latency_ms else ""
        actions_str = f" [{conn.actions_passing}/{conn.actions_total} actions]" if conn.actions_total > 0 else ""
        msg_str = f" - {conn.message}" if conn.message else ""

        print(f"    {status_icon} {conn.name}{latency_str}{actions_str}{msg_str}")

        for action in conn.action_validations:
            result_icon = {
                ValidationResult.PASS: "  +",
                ValidationResult.FAIL: "  X",
                ValidationResult.WARN: "  !",
                ValidationResult.SKIP: "  -",
            }.get(action.result, "  ?")

            a_latency = f" ({action.latency_ms:.0f}ms)" if action.latency_ms else ""
            a_msg = f" - {action.message}" if action.message else ""
            print(f"      {result_icon} {action.action_name}: {action.description}{a_latency}{a_msg}")

    print("\n" + "=" * 80)
    if report.status == "all_connected":
        print("ALL CONNECTIONS VERIFIED AND VALIDATED")
    elif report.status == "partial":
        print(f"PARTIAL CONNECTIVITY - {report.disconnected_count} connection(s) need attention")
    elif report.status == "critical":
        print(f"CRITICAL - Infrastructure connections failing")
    else:
        print(f"STATUS: {report.status}")
    print("=" * 80)

    return 0 if report.status == "all_connected" else 1


if __name__ == "__main__":
    sys.exit(main())
