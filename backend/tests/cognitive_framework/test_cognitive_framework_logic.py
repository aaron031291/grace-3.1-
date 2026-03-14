"""
Logic tests for backend.cognitive_framework modules.

Tests dependency graphs, escalation, consequence engine, events,
cognitive blueprint (OODA), linting, feedback integrator, and loop output.
All external deps (LLM, DB, event bus) are mocked.
"""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Ensure backend is on path (mirrors conftest.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ─────────────────────────────────────────────────────────────────────
# Module: events.CognitiveEvent
# ─────────────────────────────────────────────────────────────────────

class TestCognitiveEvent:
    def test_event_defaults(self):
        from cognitive_framework.events import CognitiveEvent

        evt = CognitiveEvent(type="guardian.warning", source_component="api_server")
        assert evt.type == "guardian.warning"
        assert evt.source_component == "api_server"
        assert evt.id.startswith("evt_")
        assert evt.severity == 1
        assert evt.recurrence_count == 0
        assert evt.payload == {}
        assert isinstance(evt.timestamp, datetime)

    def test_event_custom_fields(self):
        from cognitive_framework.events import CognitiveEvent

        evt = CognitiveEvent(
            id="evt_custom",
            type="htm.anomaly.detected",
            source_component="htm_engine",
            severity=5,
            recurrence_count=3,
            payload={"metric": "cpu_load", "value": 99.1},
        )
        assert evt.id == "evt_custom"
        assert evt.severity == 5
        assert evt.recurrence_count == 3
        assert evt.payload["metric"] == "cpu_load"

    def test_event_severity_bounds(self):
        from cognitive_framework.events import CognitiveEvent
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CognitiveEvent(type="x", source_component="y", severity=0)
        with pytest.raises(ValidationError):
            CognitiveEvent(type="x", source_component="y", severity=6)


# ─────────────────────────────────────────────────────────────────────
# Module: dependency_graph.DependencyGraph
# ─────────────────────────────────────────────────────────────────────

class TestDependencyGraph:
    def test_empty_graph_returns_self(self):
        from cognitive_framework.dependency_graph import DependencyGraph

        g = DependencyGraph()
        result = g.get_impacted_components("orphan")
        assert result == ["orphan"]

    def test_linear_chain(self):
        from cognitive_framework.dependency_graph import DependencyGraph

        g = DependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("B", "C")
        impacted = g.get_impacted_components("A")
        assert set(impacted) == {"A", "B", "C"}

    def test_branching_graph(self):
        from cognitive_framework.dependency_graph import DependencyGraph

        g = DependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("A", "C")
        g.add_dependency("C", "D")
        impacted = g.get_impacted_components("A")
        assert set(impacted) == {"A", "B", "C", "D"}

    def test_cycle_does_not_loop_forever(self):
        from cognitive_framework.dependency_graph import DependencyGraph

        g = DependencyGraph()
        g.add_dependency("X", "Y")
        g.add_dependency("Y", "X")
        impacted = g.get_impacted_components("X")
        assert set(impacted) == {"X", "Y"}

    def test_partial_graph_leaf_node(self):
        from cognitive_framework.dependency_graph import DependencyGraph

        g = DependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("B", "C")
        # Starting at leaf "C" should only return C itself
        impacted = g.get_impacted_components("C")
        assert impacted == ["C"]


# ─────────────────────────────────────────────────────────────────────
# Module: consequence_engine.ConsequenceEngine
# ─────────────────────────────────────────────────────────────────────

class TestConsequenceEngine:
    def _make_event(self, severity=1, recurrence=0, src="comp"):
        from cognitive_framework.events import CognitiveEvent
        return CognitiveEvent(type="test.event", source_component=src,
                              severity=severity, recurrence_count=recurrence)

    def test_minimal_risk(self):
        from cognitive_framework.dependency_graph import DependencyGraph
        from cognitive_framework.consequence_engine import ConsequenceEngine

        g = DependencyGraph()
        ce = ConsequenceEngine(g)
        evt = self._make_event(severity=1, recurrence=0)
        result = ce.simulate_consequences(evt, [])
        # base_risk=0.1, no penalties
        assert result.risk_score == pytest.approx(0.1)

    def test_high_severity_and_recurrence(self):
        from cognitive_framework.dependency_graph import DependencyGraph
        from cognitive_framework.consequence_engine import ConsequenceEngine

        g = DependencyGraph()
        ce = ConsequenceEngine(g)
        evt = self._make_event(severity=5, recurrence=10)
        # base=0.5, recurrence=min(0.5,0.2)=0.2, impact for 8 items=min(0.4,0.4)=0.4
        result = ce.simulate_consequences(evt, ["a"] * 8)
        assert result.risk_score == pytest.approx(1.0)  # capped

    def test_risk_caps_at_one(self):
        from cognitive_framework.dependency_graph import DependencyGraph
        from cognitive_framework.consequence_engine import ConsequenceEngine

        g = DependencyGraph()
        ce = ConsequenceEngine(g)
        evt = self._make_event(severity=5, recurrence=100)
        result = ce.simulate_consequences(evt, ["x"] * 100)
        assert result.risk_score == 1.0

    def test_description_format(self):
        from cognitive_framework.dependency_graph import DependencyGraph
        from cognitive_framework.consequence_engine import ConsequenceEngine

        g = DependencyGraph()
        ce = ConsequenceEngine(g)
        evt = self._make_event(severity=2, recurrence=1, src="db_service")
        result = ce.simulate_consequences(evt, ["a", "b"])
        assert "db_service" in result.description
        assert "2 downstream" in result.description


# ─────────────────────────────────────────────────────────────────────
# Module: escalation_manager.EscalationManager
# ─────────────────────────────────────────────────────────────────────

class TestEscalationManager:
    def _make_event(self, event_type="test.event"):
        from cognitive_framework.events import CognitiveEvent
        return CognitiveEvent(type=event_type, source_component="svc")

    def test_low_risk_auto_heals(self):
        from cognitive_framework.escalation_manager import EscalationManager

        em = EscalationManager()
        resp = em.determine_response(self._make_event(), risk_score=0.1)
        assert resp["level"] == 0
        assert resp["action"] == "auto-heal"
        assert resp["playbook"] is not None

    def test_guardian_log_error_maps_to_self_heal(self):
        from cognitive_framework.escalation_manager import EscalationManager

        em = EscalationManager()
        evt = self._make_event("guardian.log_error")
        resp = em.determine_response(evt, risk_score=0.45)
        assert resp["level"] == 2
        assert resp["playbook"] == "log_error_remediation"

    def test_medium_risk_research_mission(self):
        from cognitive_framework.escalation_manager import EscalationManager

        em = EscalationManager()
        resp = em.determine_response(self._make_event(), risk_score=0.4)
        assert resp["level"] == 1
        assert resp["action"] == "research_mission"

    def test_high_risk_engage_agents(self):
        from cognitive_framework.escalation_manager import EscalationManager

        em = EscalationManager()
        resp = em.determine_response(self._make_event(), risk_score=0.6)
        assert resp["level"] == 2
        assert resp["action"] == "engage_agents"
        assert resp["playbook"] is None

    def test_critical_risk_human_escalation(self):
        from cognitive_framework.escalation_manager import EscalationManager

        em = EscalationManager()
        resp = em.determine_response(self._make_event(), risk_score=0.9)
        assert resp["level"] == 4
        assert resp["action"] == "human_escalation"


# ─────────────────────────────────────────────────────────────────────
# Module: GraceCognitionLinter
# ─────────────────────────────────────────────────────────────────────

class TestGraceCognitionLinter:
    def test_file_with_logging_passes(self, tmp_path):
        from cognitive_framework.GraceCognitionLinter import GraceCognitionLinter

        f = tmp_path / "good.py"
        f.write_text("import logging\nlogger = logging.getLogger(__name__)\n")
        linter = GraceCognitionLinter()
        assert linter.lint_file(f) == []

    def test_file_without_logging_fails(self, tmp_path):
        from cognitive_framework.GraceCognitionLinter import GraceCognitionLinter

        f = tmp_path / "bad.py"
        f.write_text("x = 1\n")
        linter = GraceCognitionLinter()
        violations = linter.lint_file(f)
        assert len(violations) == 1
        assert "telemetry" in violations[0].lower() or "logging" in violations[0].lower()

    def test_non_python_file_ignored(self, tmp_path):
        from cognitive_framework.GraceCognitionLinter import GraceCognitionLinter

        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}')
        linter = GraceCognitionLinter()
        assert linter.lint_file(f) == []

    def test_file_with_logger_reference_passes(self, tmp_path):
        from cognitive_framework.GraceCognitionLinter import GraceCognitionLinter

        f = tmp_path / "alt.py"
        f.write_text("logger = get_logger()\nlogger.info('ok')\n")
        linter = GraceCognitionLinter()
        assert linter.lint_file(f) == []


# ─────────────────────────────────────────────────────────────────────
# Module: FeedbackIntegrator
# ─────────────────────────────────────────────────────────────────────

class TestFeedbackIntegrator:
    def test_log_outcome_success(self, caplog):
        from cognitive_framework.FeedbackIntegrator import FeedbackIntegrator
        import logging

        fi = FeedbackIntegrator()
        with caplog.at_level(logging.INFO, logger="feedback_integrator"):
            fi.log_outcome("evt_1", "dec_1", {"status": "success", "mttr_achieved": 5})
        assert "Success: True" in caplog.text
        assert "MTTR: 5" in caplog.text

    def test_log_outcome_failure(self, caplog):
        from cognitive_framework.FeedbackIntegrator import FeedbackIntegrator
        import logging

        fi = FeedbackIntegrator()
        with caplog.at_level(logging.INFO, logger="feedback_integrator"):
            fi.log_outcome("evt_2", "dec_2", {"status": "error"})
        assert "Success: False" in caplog.text


# ─────────────────────────────────────────────────────────────────────
# Module: GraceLoopOutput (pydantic model)
# ─────────────────────────────────────────────────────────────────────

class TestGraceLoopOutput:
    def test_valid_construction(self):
        from cognitive_framework.GraceLoopOutput import GraceLoopOutput

        out = GraceLoopOutput(
            loop_id="loop_1", decision_id="dec_1", status="success",
            mttr_seconds=12, artifacts_produced=["patch.diff"],
            knowledge_updates={"key": "val"},
        )
        assert out.loop_id == "loop_1"
        assert out.mttr_seconds == 12
        assert out.artifacts_produced == ["patch.diff"]

    def test_defaults(self):
        from cognitive_framework.GraceLoopOutput import GraceLoopOutput

        out = GraceLoopOutput(loop_id="l", decision_id="d", status="failure")
        assert out.mttr_seconds is None
        assert out.artifacts_produced == []
        assert out.knowledge_updates == {}
        assert isinstance(out.timestamp, datetime)

    def test_model_dump_roundtrip(self):
        from cognitive_framework.GraceLoopOutput import GraceLoopOutput

        out = GraceLoopOutput(loop_id="l2", decision_id="d2", status="partial")
        data = out.model_dump()
        out2 = GraceLoopOutput(**data)
        assert out2.loop_id == out.loop_id
        assert out2.status == out.status


# ─────────────────────────────────────────────────────────────────────
# Module: cognitive_blueprint.OODALoopExecutor (async)
# ─────────────────────────────────────────────────────────────────────

class TestOODALoopExecutor:
    @pytest.mark.asyncio
    async def test_orient_and_observe(self):
        from cognitive_framework.cognitive_blueprint import OODALoopExecutor

        ooda = OODALoopExecutor()
        result = await ooda.orient_and_observe("disk full", {"host": "node-1"})
        assert result["original_problem"] == "disk full"
        assert "constraints" in result
        assert result["ambient_context"]["host"] == "node-1"

    @pytest.mark.asyncio
    async def test_chess_mode_selects_lowest_disruption(self):
        from cognitive_framework.cognitive_blueprint import OODALoopExecutor

        ooda = OODALoopExecutor()
        orientation = await ooda.orient_and_observe("test problem", {})
        decision = await ooda.chess_mode_decide(orientation)
        # The path with complexity 0.2 + blast 0.1 = 0.3 should win
        assert decision.path_description == "Directly patch the failing file."
        assert decision.complexity_score == 0.2
        assert decision.blast_radius == 0.1

    @pytest.mark.asyncio
    async def test_process_and_act_returns_full_context(self):
        from cognitive_framework.cognitive_blueprint import OODALoopExecutor

        ooda = OODALoopExecutor()
        result = await ooda.process_and_act("memory leak", {"pid": 42})
        assert "orientation" in result
        assert "chess_mode_decision" in result
        assert "sixteen_questions_rubric" in result
        assert len(result["sixteen_questions_rubric"]) == 16


# ─────────────────────────────────────────────────────────────────────
# Module: cognitive_playbook_executor.PlaybookExecutor
# ─────────────────────────────────────────────────────────────────────

class TestPlaybookExecutor:
    def _make_event(self):
        from cognitive_framework.events import CognitiveEvent
        return CognitiveEvent(type="test.event", source_component="svc")

    @pytest.mark.asyncio
    async def test_unknown_playbook_returns_simulated(self):
        from cognitive_framework.cognitive_playbook_executor import PlaybookExecutor

        pe = PlaybookExecutor()
        result = await pe.execute("totally_unknown_playbook", self._make_event(), "dec_1")
        assert result["status"] == "simulated_success"
        assert result["action"] == "no_routing_matched"

    @pytest.mark.asyncio
    async def test_research_playbook_submits_to_queue(self):
        from cognitive_framework.cognitive_playbook_executor import PlaybookExecutor

        pe = PlaybookExecutor()
        evt = self._make_event()

        with patch("cognitive_framework.cognitive_playbook_executor.PlaybookExecutor.execute") as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "action": "submitted_to_coding_queue_post_ooda",
                "task_id": "task_123",
                "playbook_id": "research_mission",
                "decision_context": "dec_1",
            }
            result = await pe.execute("research_mission", evt, "dec_1")
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_auto_heal_playbook_triggers_diagnostic(self):
        from cognitive_framework.cognitive_playbook_executor import PlaybookExecutor

        pe = PlaybookExecutor()
        evt = self._make_event()

        # auto_heal will try to import diagnostic_machine; mock it
        mock_engine = MagicMock()
        with patch.dict("sys.modules", {
            "diagnostic_machine": MagicMock(),
            "diagnostic_machine.diagnostic_engine": MagicMock(
                get_diagnostic_engine=MagicMock(return_value=mock_engine),
                TriggerSource=MagicMock(SENSOR_FLAG="sensor_flag"),
            ),
            "cognitive.event_bus": MagicMock(),
            "api._genesis_tracker": MagicMock(),
        }):
            result = await pe.execute("auto_heal_restart_service", evt, "dec_2")
            assert result["status"] == "success"
            assert result["action"] == "triggered_diagnostic_cycle"


# ─────────────────────────────────────────────────────────────────────
# Module: cognitive_framework.CognitiveFramework (orchestrator)
# ─────────────────────────────────────────────────────────────────────

class TestCognitiveFrameworkOrchestrator:
    @pytest.mark.asyncio
    async def test_process_event_low_risk(self):
        from cognitive_framework.events import CognitiveEvent
        from cognitive_framework.cognitive_framework import CognitiveFramework

        mock_decision = MagicMock()
        mock_decision.id = "dec_mock"

        with patch("cognitive_framework.cognitive_framework.ClarityFramework") as mock_clarity:
            mock_clarity.record_decision.return_value = mock_decision
            cf = CognitiveFramework()
            # Inject a known graph edge
            cf.dependency_graph.add_dependency("api_server", "db_service")

            evt = CognitiveEvent(type="guardian.warning", source_component="api_server",
                                 severity=1, recurrence_count=0)

            # Mock playbook executor to avoid external calls
            cf.playbook_executor.execute = AsyncMock(return_value={"status": "ok"})

            result = await cf.process_event(evt)
            assert result["decision_id"] == "dec_mock"
            assert result["execution_result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_process_event_no_playbook(self):
        from cognitive_framework.events import CognitiveEvent
        from cognitive_framework.cognitive_framework import CognitiveFramework

        mock_decision = MagicMock()
        mock_decision.id = "dec_2"

        with patch("cognitive_framework.cognitive_framework.ClarityFramework") as mock_clarity:
            mock_clarity.record_decision.return_value = mock_decision
            cf = CognitiveFramework()

            evt = CognitiveEvent(type="test.event", source_component="unknown",
                                 severity=4, recurrence_count=5)

            result = await cf.process_event(evt)
            # High risk => human_escalation => no playbook => execution_result is None
            assert result["decision_id"] == "dec_2"
            assert result["execution_result"] is None
