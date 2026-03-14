"""
Tests for cognitive_framework modules:
  - events.py (CognitiveEvent)
  - dependency_graph.py (DependencyGraph)
  - consequence_engine.py (ConsequenceEngine, ConsequenceResult)
  - escalation_manager.py (EscalationManager)
"""

import sys
import importlib
import importlib.util
import pathlib
import pytest

_base = pathlib.Path(__file__).resolve().parents[3] / "backend"

# events.py first (dependency of consequence_engine / escalation_manager)
_events_spec = importlib.util.spec_from_file_location(
    "cognitive_framework.events",
    str(_base / "cognitive_framework" / "events.py"),
)
_events_mod = importlib.util.module_from_spec(_events_spec)
sys.modules["cognitive_framework.events"] = _events_mod
_events_spec.loader.exec_module(_events_mod)
CognitiveEvent = _events_mod.CognitiveEvent

# dependency_graph
_dg_spec = importlib.util.spec_from_file_location(
    "cognitive_framework.dependency_graph",
    str(_base / "cognitive_framework" / "dependency_graph.py"),
)
_dg_mod = importlib.util.module_from_spec(_dg_spec)
sys.modules["cognitive_framework.dependency_graph"] = _dg_mod
_dg_spec.loader.exec_module(_dg_mod)
DependencyGraph = _dg_mod.DependencyGraph

# consequence_engine
_ce_spec = importlib.util.spec_from_file_location(
    "cognitive_framework.consequence_engine",
    str(_base / "cognitive_framework" / "consequence_engine.py"),
)
_ce_mod = importlib.util.module_from_spec(_ce_spec)
_ce_spec.loader.exec_module(_ce_mod)
ConsequenceEngine = _ce_mod.ConsequenceEngine
ConsequenceResult = _ce_mod.ConsequenceResult

# escalation_manager
_em_spec = importlib.util.spec_from_file_location(
    "cognitive_framework.escalation_manager",
    str(_base / "cognitive_framework" / "escalation_manager.py"),
)
_em_mod = importlib.util.module_from_spec(_em_spec)
_em_spec.loader.exec_module(_em_mod)
EscalationManager = _em_mod.EscalationManager


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_event(**overrides):
    defaults = {"type": "test.event", "source_component": "test_comp"}
    defaults.update(overrides)
    return CognitiveEvent(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
#  CognitiveEvent
# ═══════════════════════════════════════════════════════════════════════════════

class TestCognitiveEvent:
    def test_create_with_required_fields(self):
        evt = CognitiveEvent(type="guardian.warning", source_component="guardian")
        assert evt.type == "guardian.warning"
        assert evt.source_component == "guardian"

    def test_default_id_prefix(self):
        evt = _make_event()
        assert evt.id.startswith("evt_")
        assert len(evt.id) > 4

    def test_default_severity_is_1(self):
        evt = _make_event()
        assert evt.severity == 1

    def test_default_recurrence_count_is_0(self):
        evt = _make_event()
        assert evt.recurrence_count == 0

    def test_custom_severity_within_range(self):
        for sev in (1, 2, 3, 4, 5):
            evt = _make_event(severity=sev)
            assert evt.severity == sev

    def test_severity_out_of_range_rejected(self):
        with pytest.raises(Exception):
            _make_event(severity=0)
        with pytest.raises(Exception):
            _make_event(severity=6)

    def test_payload_defaults_to_empty_dict(self):
        evt = _make_event()
        assert evt.payload == {}

    def test_payload_custom(self):
        evt = _make_event(payload={"key": "value"})
        assert evt.payload == {"key": "value"}

    def test_unique_ids(self):
        ids = {_make_event().id for _ in range(50)}
        assert len(ids) == 50


# ═══════════════════════════════════════════════════════════════════════════════
#  DependencyGraph
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyGraph:
    def test_empty_graph_returns_self(self):
        g = DependencyGraph()
        result = g.get_impacted_components("A")
        assert result == ["A"]

    def test_single_dependency(self):
        g = DependencyGraph()
        g.add_dependency("A", "B")
        result = g.get_impacted_components("A")
        assert set(result) == {"A", "B"}

    def test_chain_dependency(self):
        g = DependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("B", "C")
        result = g.get_impacted_components("A")
        assert set(result) == {"A", "B", "C"}

    def test_diamond_dependency_no_duplicates(self):
        g = DependencyGraph()
        g.add_dependency("A", "B")
        g.add_dependency("A", "C")
        g.add_dependency("B", "D")
        g.add_dependency("C", "D")
        result = g.get_impacted_components("A")
        assert set(result) == {"A", "B", "C", "D"}
        assert len(result) == 4  # no duplicates

    def test_isolated_component(self):
        g = DependencyGraph()
        g.add_dependency("X", "Y")
        result = g.get_impacted_components("Z")
        assert result == ["Z"]

    def test_leaf_node_returns_self(self):
        g = DependencyGraph()
        g.add_dependency("A", "B")
        result = g.get_impacted_components("B")
        assert result == ["B"]


# ═══════════════════════════════════════════════════════════════════════════════
#  ConsequenceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsequenceEngine:
    def _engine(self):
        return ConsequenceEngine(DependencyGraph())

    def test_low_severity_no_recurrence_no_impacts(self):
        engine = self._engine()
        evt = _make_event(severity=1, recurrence_count=0)
        result = engine.simulate_consequences(evt, [evt.source_component])
        # base_risk = 1*0.1 = 0.1, recurrence = 0, impact = 1*0.05 = 0.05
        assert result.risk_score == pytest.approx(0.15)

    def test_high_severity_increases_risk(self):
        engine = self._engine()
        evt = _make_event(severity=5, recurrence_count=0)
        result = engine.simulate_consequences(evt, [evt.source_component])
        # base_risk = 5*0.1 = 0.5, impact = 0.05
        assert result.risk_score == pytest.approx(0.55)

    def test_recurrence_penalty_capped_at_02(self):
        engine = self._engine()
        evt = _make_event(severity=1, recurrence_count=100)
        result = engine.simulate_consequences(evt, [evt.source_component])
        # base_risk = 0.1, recurrence = min(100*0.05, 0.2) = 0.2, impact = 0.05
        assert result.risk_score == pytest.approx(0.35)

    def test_impact_penalty_capped_at_04(self):
        engine = self._engine()
        evt = _make_event(severity=1, recurrence_count=0)
        many_components = [f"c{i}" for i in range(50)]
        result = engine.simulate_consequences(evt, many_components)
        # base_risk = 0.1, recurrence = 0, impact = min(50*0.05, 0.4) = 0.4
        assert result.risk_score == pytest.approx(0.5)

    def test_risk_capped_at_1(self):
        engine = self._engine()
        evt = _make_event(severity=5, recurrence_count=100)
        many_components = [f"c{i}" for i in range(50)]
        result = engine.simulate_consequences(evt, many_components)
        # base=0.5 + recurrence=0.2 + impact=0.4 = 1.1 → capped at 1.0
        assert result.risk_score == pytest.approx(1.0)

    def test_description_contains_source_and_impact_count(self):
        engine = self._engine()
        evt = _make_event(source_component="guardian")
        impacts = ["guardian", "memory", "agents"]
        result = engine.simulate_consequences(evt, impacts)
        assert "guardian" in result.description
        assert "3" in result.description

    def test_consequence_result_attributes(self):
        cr = ConsequenceResult(risk_score=0.42, description="test desc")
        assert cr.risk_score == 0.42
        assert cr.description == "test desc"


# ═══════════════════════════════════════════════════════════════════════════════
#  EscalationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscalationManager:
    def _mgr(self):
        return EscalationManager()

    def test_low_risk_auto_heal(self):
        mgr = self._mgr()
        evt = _make_event(type="htm.anomaly.detected")
        resp = mgr.determine_response(evt, risk_score=0.2)
        assert resp["level"] == 0
        assert resp["action"] == "auto-heal"
        assert resp["playbook"] is not None

    def test_risk_030_is_auto_heal(self):
        mgr = self._mgr()
        evt = _make_event()
        resp = mgr.determine_response(evt, risk_score=0.3)
        assert resp["level"] == 0
        assert resp["action"] == "auto-heal"

    def test_risk_031_to_05_research_mission(self):
        mgr = self._mgr()
        evt = _make_event()
        resp = mgr.determine_response(evt, risk_score=0.4)
        assert resp["level"] == 1
        assert resp["action"] == "research_mission"

    def test_risk_051_to_07_engage_agents(self):
        mgr = self._mgr()
        evt = _make_event()
        resp = mgr.determine_response(evt, risk_score=0.6)
        assert resp["level"] == 2
        assert resp["action"] == "engage_agents"

    def test_risk_above_07_human_escalation(self):
        mgr = self._mgr()
        evt = _make_event()
        resp = mgr.determine_response(evt, risk_score=0.9)
        assert resp["level"] == 4
        assert resp["action"] == "human_escalation"

    def test_guardian_log_error_special_case_mid_risk(self):
        mgr = self._mgr()
        evt = _make_event(type="guardian.log_error")
        resp = mgr.determine_response(evt, risk_score=0.45)
        assert resp["level"] == 2
        assert resp["action"] == "self_heal"
        assert resp["playbook"] == "log_error_remediation"

    def test_guardian_log_error_special_case_high_risk(self):
        mgr = self._mgr()
        evt = _make_event(type="guardian.log_error")
        resp = mgr.determine_response(evt, risk_score=0.9)
        assert resp["level"] == 2
        assert resp["action"] == "self_heal"
        assert resp["playbook"] == "log_error_remediation"

    def test_guardian_log_error_low_risk_uses_auto_heal(self):
        mgr = self._mgr()
        evt = _make_event(type="guardian.log_error")
        resp = mgr.determine_response(evt, risk_score=0.2)
        # risk <= 0.3 takes priority over the log_error branch
        assert resp["level"] == 0
        assert resp["action"] == "auto-heal"

    def test_response_always_has_required_keys(self):
        mgr = self._mgr()
        for risk in (0.0, 0.3, 0.4, 0.6, 0.8, 1.0):
            evt = _make_event()
            resp = mgr.determine_response(evt, risk_score=risk)
            assert "risk_score" in resp
            assert "playbook" in resp
            assert "level" in resp
            assert "action" in resp

    def test_risk_score_preserved_in_response(self):
        mgr = self._mgr()
        evt = _make_event()
        resp = mgr.determine_response(evt, risk_score=0.55)
        assert resp["risk_score"] == 0.55
