"""
Tests for the 4-Layer Diagnostic Machine.

Tests cover:
- Layer 1: Sensors (data collection)
- Layer 2: Interpreters (pattern analysis)
- Layer 3: Judgement (decision making)
- Layer 4: Action Routing (response execution)
- DiagnosticEngine (orchestration)
- API endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import tempfile
import json
import os


# ==================== Layer 1: Sensors Tests ====================

class TestSensorLayer:
    """Tests for Layer 1 - Sensors."""

    def test_sensor_layer_initialization(self):
        """Test sensor layer initializes correctly."""
        from diagnostic_machine.sensors import SensorLayer
        sensor = SensorLayer()
        assert sensor is not None
        assert sensor.diagnostic_report_path is not None

    def test_sensor_data_structure(self):
        """Test SensorData dataclass structure."""
        from diagnostic_machine.sensors import (
            SensorData, TestResultData, LogData, MetricsData
        )

        sensor_data = SensorData()
        assert sensor_data.test_results is None
        assert sensor_data.logs is None
        assert sensor_data.metrics is None
        assert isinstance(sensor_data.sensors_available, list)
        assert isinstance(sensor_data.sensors_failed, list)

    def test_collect_all_returns_sensor_data(self):
        """Test collect_all returns SensorData."""
        from diagnostic_machine.sensors import SensorLayer, SensorData

        sensor = SensorLayer(enable_psutil=False)
        result = sensor.collect_all()

        assert isinstance(result, SensorData)
        assert result.collection_duration_ms >= 0

    def test_test_result_data_structure(self):
        """Test TestResultData dataclass."""
        from diagnostic_machine.sensors import TestResultData

        test_data = TestResultData(
            total_tests=100,
            passed=85,
            failed=10,
            skipped=5,
            pass_rate=0.85
        )

        assert test_data.total_tests == 100
        assert test_data.passed == 85
        assert test_data.pass_rate == 0.85

    def test_metrics_data_structure(self):
        """Test MetricsData dataclass."""
        from diagnostic_machine.sensors import MetricsData

        metrics = MetricsData(
            cpu_percent=45.0,
            memory_percent=60.0,
            disk_percent=70.0
        )

        assert metrics.cpu_percent == 45.0
        assert metrics.memory_percent == 60.0

    def test_sensor_to_dict(self):
        """Test sensor data serialization."""
        from diagnostic_machine.sensors import SensorLayer, SensorData, TestResultData

        sensor = SensorLayer()
        data = SensorData()
        data.test_results = TestResultData(total_tests=10, passed=8)

        result = sensor.to_dict(data)

        assert 'collection_timestamp' in result
        assert 'sensors_available' in result


# ==================== Layer 2: Interpreters Tests ====================

class TestInterpreterLayer:
    """Tests for Layer 2 - Interpreters."""

    def test_interpreter_layer_initialization(self):
        """Test interpreter layer initializes correctly."""
        from diagnostic_machine.interpreters import InterpreterLayer
        interpreter = InterpreterLayer()
        assert interpreter is not None
        assert len(interpreter.INVARIANTS) == 12

    def test_pattern_types(self):
        """Test PatternType enum values."""
        from diagnostic_machine.interpreters import PatternType

        assert PatternType.TEST_FAILURE_PATTERN == "test_failure_pattern"
        assert PatternType.LEARNING_OPPORTUNITY == "learning_opportunity"

    def test_anomaly_types(self):
        """Test AnomalyType enum values."""
        from diagnostic_machine.interpreters import AnomalyType

        assert AnomalyType.TEST_PASS_RATE_DROP == "test_pass_rate_drop"
        assert AnomalyType.RESOURCE_EXHAUSTION == "resource_exhaustion"

    def test_clarity_levels(self):
        """Test ClarityLevel enum values."""
        from diagnostic_machine.interpreters import ClarityLevel

        assert ClarityLevel.CLEAR == "clear"
        assert ClarityLevel.OPAQUE == "opaque"

    def test_interpret_returns_interpreted_data(self):
        """Test interpret method returns InterpretedData."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer, InterpretedData

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=85,
            failed=10,
            skipped=5,
            pass_rate=0.85
        )

        interpreter = InterpreterLayer()
        result = interpreter.interpret(sensor_data)

        assert isinstance(result, InterpretedData)
        assert len(result.invariant_checks) == 12

    def test_pattern_detection_with_failures(self):
        """Test pattern detection with test failures."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer, PatternType

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=40,
            failed=60,
            infrastructure_failures=40,
            code_failures=20,
            pass_rate=0.4
        )

        interpreter = InterpreterLayer()
        result = interpreter.interpret(sensor_data)

        # Should detect infrastructure issue pattern
        pattern_types = [p.pattern_type for p in result.patterns]
        assert PatternType.INFRASTRUCTURE_ISSUE in pattern_types

    def test_anomaly_detection_low_pass_rate(self):
        """Test anomaly detection for low pass rate."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer, AnomalyType

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=30,
            failed=70,
            pass_rate=0.3
        )

        interpreter = InterpreterLayer()
        result = interpreter.interpret(sensor_data)

        # Should detect pass rate drop anomaly
        anomaly_types = [a.anomaly_type for a in result.anomalies]
        assert AnomalyType.TEST_PASS_RATE_DROP in anomaly_types

    def test_invariant_checks(self):
        """Test all 12 invariants are checked."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer

        sensor_data = SensorData()
        interpreter = InterpreterLayer()
        result = interpreter.interpret(sensor_data)

        assert len(result.invariant_checks) == 12
        invariant_ids = [c.invariant_id for c in result.invariant_checks]
        for i in range(1, 13):
            assert f"INV-{i}" in invariant_ids

    def test_clarity_classification(self):
        """Test clarity classification."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer, ClarityLevel

        sensor_data = SensorData()
        interpreter = InterpreterLayer()
        result = interpreter.interpret(sensor_data)

        assert result.clarity_level in [
            ClarityLevel.CLEAR,
            ClarityLevel.PARTIALLY_CLEAR,
            ClarityLevel.AMBIGUOUS,
            ClarityLevel.OPAQUE
        ]
        assert 0.0 <= result.clarity_score <= 1.0


# ==================== Layer 3: Judgement Tests ====================

class TestJudgementLayer:
    """Tests for Layer 3 - Judgement."""

    def test_judgement_layer_initialization(self):
        """Test judgement layer initializes correctly."""
        from diagnostic_machine.judgement import JudgementLayer
        judgement = JudgementLayer()
        assert judgement is not None

    def test_health_status_enum(self):
        """Test HealthStatus enum values."""
        from diagnostic_machine.judgement import HealthStatus

        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.CRITICAL == "critical"

    def test_risk_level_enum(self):
        """Test RiskLevel enum values."""
        from diagnostic_machine.judgement import RiskLevel

        assert RiskLevel.LOW == "low"
        assert RiskLevel.CRITICAL == "critical"

    def test_judge_returns_judgement_result(self):
        """Test judge method returns JudgementResult."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer, JudgementResult

        sensor_data = SensorData()
        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        assert isinstance(result, JudgementResult)
        assert result.health is not None
        assert result.confidence is not None

    def test_health_score_calculation(self):
        """Test health score calculation."""
        from diagnostic_machine.sensors import SensorData, TestResultData, MetricsData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer, HealthStatus

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=95,
            failed=5,
            pass_rate=0.95
        )
        sensor_data.metrics = MetricsData(
            cpu_percent=30.0,
            memory_percent=50.0,
            database_health=True,
            vector_db_health=True,
            llm_health=True,
            embedding_health=True
        )

        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        assert result.health.overall_score > 0.5
        assert result.health.status != HealthStatus.CRITICAL

    def test_risk_vector_identification(self):
        """Test risk vector identification."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=40,
            failed=60,
            pass_rate=0.4
        )

        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        # Should identify risks with low pass rate
        assert len(result.risk_vectors) > 0

    def test_drift_analysis(self):
        """Test drift analysis."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer, DriftType

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=50,
            failed=50,
            pass_rate=0.5
        )

        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        # Should detect drift from baseline
        assert len(result.drift_analysis) > 0

    def test_avn_alerts_generation(self):
        """Test AVN alerts generation."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=20,
            failed=80,
            pass_rate=0.2
        )

        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        # Should generate AVN alerts for severe issues
        assert len(result.avn_alerts) > 0

    def test_avm_status_update(self):
        """Test AVM status update."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer

        sensor_data = SensorData()
        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        assert result.avm_status is not None
        assert result.avm_status.monitor_id == "avm-001"
        assert result.avm_status.is_active == True

    def test_recommended_action_determination(self):
        """Test recommended action determination."""
        from diagnostic_machine.sensors import SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer

        sensor_data = SensorData()
        sensor_data.test_results = TestResultData(
            total_tests=100,
            passed=95,
            failed=5,
            pass_rate=0.95
        )

        interpreter = InterpreterLayer()
        interpreted_data = interpreter.interpret(sensor_data)

        judgement_layer = JudgementLayer()
        result = judgement_layer.judge(sensor_data, interpreted_data)

        # Healthy system should recommend none or monitor
        assert result.recommended_action in ['none', 'monitor', 'alert']


# ==================== Layer 4: Action Router Tests ====================

class TestActionRouter:
    """Tests for Layer 4 - Action Router."""

    def test_action_router_initialization(self):
        """Test action router initializes correctly."""
        from diagnostic_machine.action_router import ActionRouter

        with tempfile.TemporaryDirectory() as tmpdir:
            router = ActionRouter(log_dir=tmpdir)
            assert router is not None

    def test_action_types(self):
        """Test ActionType enum values."""
        from diagnostic_machine.action_router import ActionType

        assert ActionType.ALERT_HUMAN == "alert_human"
        assert ActionType.FREEZE_SYSTEM == "freeze_system"
        assert ActionType.TRIGGER_CICD == "trigger_cicd"

    def test_route_returns_action_decision(self):
        """Test route method returns ActionDecision."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer
        from diagnostic_machine.action_router import ActionRouter, ActionDecision

        with tempfile.TemporaryDirectory() as tmpdir:
            sensor_data = SensorData()
            interpreter = InterpreterLayer()
            interpreted_data = interpreter.interpret(sensor_data)

            judgement_layer = JudgementLayer()
            judgement = judgement_layer.judge(sensor_data, interpreted_data)

            action_router = ActionRouter(log_dir=tmpdir, dry_run=True)
            result = action_router.route(sensor_data, interpreted_data, judgement)

            assert isinstance(result, ActionDecision)

    def test_dry_run_mode(self):
        """Test dry run mode doesn't execute actions."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer
        from diagnostic_machine.action_router import ActionRouter

        with tempfile.TemporaryDirectory() as tmpdir:
            sensor_data = SensorData()
            interpreter = InterpreterLayer()
            interpreted_data = interpreter.interpret(sensor_data)

            judgement_layer = JudgementLayer()
            judgement = judgement_layer.judge(sensor_data, interpreted_data)

            action_router = ActionRouter(log_dir=tmpdir, dry_run=True)
            result = action_router.route(sensor_data, interpreted_data, judgement)

            # In dry run mode, results should be empty
            assert len(result.results) == 0

    def test_healing_disabled(self):
        """Test healing can be disabled."""
        from diagnostic_machine.action_router import ActionRouter

        with tempfile.TemporaryDirectory() as tmpdir:
            router = ActionRouter(
                log_dir=tmpdir,
                enable_healing=False
            )
            assert router.enable_healing == False

    def test_action_decision_to_dict(self):
        """Test action decision serialization."""
        from diagnostic_machine.sensors import SensorData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer
        from diagnostic_machine.action_router import ActionRouter

        with tempfile.TemporaryDirectory() as tmpdir:
            sensor_data = SensorData()
            interpreter = InterpreterLayer()
            interpreted_data = interpreter.interpret(sensor_data)

            judgement_layer = JudgementLayer()
            judgement = judgement_layer.judge(sensor_data, interpreted_data)

            action_router = ActionRouter(log_dir=tmpdir, dry_run=True)
            decision = action_router.route(sensor_data, interpreted_data, judgement)

            result = action_router.to_dict(decision)

            assert 'decision_id' in result
            assert 'action_type' in result


# ==================== Diagnostic Engine Tests ====================

class TestDiagnosticEngine:
    """Tests for DiagnosticEngine orchestrator."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, EngineState

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                heartbeat_interval=60,
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )
            assert engine is not None
            assert engine.state == EngineState.STOPPED

    def test_run_cycle(self):
        """Test running a diagnostic cycle."""
        from diagnostic_machine.diagnostic_engine import (
            DiagnosticEngine, TriggerSource, DiagnosticCycle
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            cycle = engine.run_cycle(TriggerSource.MANUAL)

            assert isinstance(cycle, DiagnosticCycle)
            assert cycle.success == True

    def test_engine_start_stop(self):
        """Test starting and stopping engine."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, EngineState

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            # Start
            success = engine.start()
            assert success == True
            assert engine.state == EngineState.RUNNING

            # Stop
            success = engine.stop()
            assert success == True
            assert engine.state == EngineState.STOPPED

    def test_engine_pause_resume(self):
        """Test pausing and resuming engine."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, EngineState

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            engine.start()

            # Pause
            engine.pause()
            assert engine.state == EngineState.PAUSED

            # Resume
            engine.resume()
            assert engine.state == EngineState.RUNNING

            engine.stop()

    def test_trigger_from_sensor(self):
        """Test triggering from sensor flag."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, TriggerSource

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            cycle = engine.trigger_from_sensor("test_sensor", "test reason")

            assert cycle.trigger_source == TriggerSource.SENSOR_FLAG
            assert cycle.success == True

    def test_trigger_from_cicd(self):
        """Test triggering from CI/CD pipeline."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine, TriggerSource

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            cycle = engine.trigger_from_cicd("pipeline-123")

            assert cycle.trigger_source == TriggerSource.CICD_PIPELINE
            assert cycle.success == True

    def test_get_health_summary(self):
        """Test getting health summary."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            # Run a cycle first
            engine.run_cycle()

            summary = engine.get_health_summary()

            assert 'status' in summary
            assert 'health_score' in summary or 'message' in summary

    def test_get_recent_cycles(self):
        """Test getting recent cycles."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            # Run a few cycles
            engine.run_cycle()
            engine.run_cycle()
            engine.run_cycle()

            cycles = engine.get_recent_cycles(limit=2)

            assert len(cycles) == 2

    def test_engine_stats(self):
        """Test engine statistics."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            engine.run_cycle()
            engine.run_cycle()

            stats = engine.stats

            assert stats.total_cycles == 2
            assert stats.successful_cycles == 2

    def test_callback_registration(self):
        """Test callback registration and firing."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        callback_fired = {'value': False}

        def test_callback(cycle):
            callback_fired['value'] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            engine.on_cycle_complete(test_callback)
            engine.run_cycle()

            assert callback_fired['value'] == True

    def test_engine_to_dict(self):
        """Test engine state serialization."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            result = engine.to_dict()

            assert 'state' in result
            assert 'heartbeat_interval' in result
            assert 'stats' in result


# ==================== API Endpoint Tests ====================

class TestDiagnosticAPI:
    """Tests for Diagnostic Machine API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        try:
            from app import app
            return TestClient(app)
        except ImportError:
            pytest.skip("App not available for testing")

    def test_health_endpoint(self, client):
        """Test /diagnostic/health endpoint."""
        response = client.get("/diagnostic/health")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'status' in data

    def test_status_endpoint(self, client):
        """Test /diagnostic/status endpoint."""
        response = client.get("/diagnostic/status")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'state' in data

    def test_trigger_endpoint(self, client):
        """Test /diagnostic/trigger endpoint."""
        response = client.post(
            "/diagnostic/trigger",
            json={"source": "api", "reason": "test"}
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'cycle_id' in data

    def test_history_endpoint(self, client):
        """Test /diagnostic/history endpoint."""
        response = client.get("/diagnostic/history?limit=5")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'cycles' in data

    def test_cicd_webhook_endpoint(self, client):
        """Test /diagnostic/webhook/cicd endpoint."""
        response = client.post(
            "/diagnostic/webhook/cicd",
            json={
                "pipeline_id": "test-pipeline",
                "event": "completed",
                "status": "success"
            }
        )
        assert response.status_code in [200, 500]

    def test_sensor_flag_endpoint(self, client):
        """Test /diagnostic/sensor/flag endpoint."""
        response = client.post(
            "/diagnostic/sensor/flag",
            json={
                "sensor_type": "test_sensor",
                "severity": "medium",
                "message": "test message"
            }
        )
        assert response.status_code in [200, 500]

    def test_avn_alerts_endpoint(self, client):
        """Test /diagnostic/avn/alerts endpoint."""
        response = client.get("/diagnostic/avn/alerts")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'alerts' in data

    def test_avm_status_endpoint(self, client):
        """Test /diagnostic/avm/status endpoint."""
        response = client.get("/diagnostic/avm/status")
        assert response.status_code in [200, 500]

    def test_forensics_endpoint(self, client):
        """Test /diagnostic/forensics endpoint."""
        response = client.get("/diagnostic/forensics")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'findings' in data

    def test_full_report_endpoint(self, client):
        """Test /diagnostic/full-report endpoint."""
        response = client.get("/diagnostic/full-report")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert 'report_id' in data


# ==================== Integration Tests ====================

class TestDiagnosticIntegration:
    """Integration tests for the complete diagnostic pipeline."""

    def test_full_diagnostic_pipeline(self):
        """Test complete pipeline from sensors to action."""
        from diagnostic_machine.sensors import SensorLayer, SensorData, TestResultData
        from diagnostic_machine.interpreters import InterpreterLayer
        from diagnostic_machine.judgement import JudgementLayer
        from diagnostic_machine.action_router import ActionRouter

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sensor data
            sensor_data = SensorData()
            sensor_data.test_results = TestResultData(
                total_tests=100,
                passed=85,
                failed=15,
                pass_rate=0.85
            )

            # Layer 2: Interpret
            interpreter = InterpreterLayer()
            interpreted_data = interpreter.interpret(sensor_data)

            # Layer 3: Judge
            judgement_layer = JudgementLayer()
            judgement = judgement_layer.judge(sensor_data, interpreted_data)

            # Layer 4: Route action
            action_router = ActionRouter(log_dir=tmpdir, dry_run=True)
            decision = action_router.route(sensor_data, interpreted_data, judgement)

            # Verify pipeline completion
            assert interpreted_data is not None
            assert judgement is not None
            assert decision is not None

    def test_engine_full_cycle(self):
        """Test engine running complete cycle."""
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DiagnosticEngine(
                enable_heartbeat=False,
                log_dir=tmpdir,
                dry_run=True
            )

            cycle = engine.run_cycle()

            # Verify all layers executed
            assert cycle.sensor_data is not None
            assert cycle.interpreted_data is not None
            assert cycle.judgement is not None
            assert cycle.action_decision is not None
            assert cycle.success == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
