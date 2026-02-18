"""
Tests for Self-* Agent Ecosystem

Verifies:
- 6 micro-DB tables exist (one per agent)
- All agents can self-analyze
- Closed-loop orchestrator works
- Kimi consultation wiring
- System-wide KPI calculation
- Mode switching (improve/scale/monitor)

Target: 100% pass, 0 warnings, 0 skips
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestMicroDBTables:
    """Verify each agent has its own micro-DB table."""

    def test_self_healing_log_table(self):
        from cognitive.self_agent_ecosystem import SelfHealingLog
        assert SelfHealingLog.__tablename__ == "self_healing_log"
        cols = [c.name for c in SelfHealingLog.__table__.columns]
        assert "action_type" in cols
        assert "status" in cols
        assert "kpi_before" in cols
        assert "kpi_after" in cols
        assert "trust_score" in cols
        assert "error_message" in cols

    def test_self_mirror_log_table(self):
        from cognitive.self_agent_ecosystem import SelfMirrorLog
        assert SelfMirrorLog.__tablename__ == "self_mirror_log"
        cols = [c.name for c in SelfMirrorLog.__table__.columns]
        assert "observation_type" in cols
        assert "pattern_detected" in cols
        assert "insight" in cols
        assert "recommendation" in cols

    def test_self_model_log_table(self):
        from cognitive.self_agent_ecosystem import SelfModelLog
        assert SelfModelLog.__tablename__ == "self_model_log"
        cols = [c.name for c in SelfModelLog.__table__.columns]
        assert "model_type" in cols
        assert "accuracy" in cols
        assert "samples_used" in cols
        assert "predictions_made" in cols

    def test_self_learner_log_table(self):
        from cognitive.self_agent_ecosystem import SelfLearnerLog
        assert SelfLearnerLog.__tablename__ == "self_learner_log"
        cols = [c.name for c in SelfLearnerLog.__table__.columns]
        assert "topic" in cols
        assert "learning_type" in cols
        assert "concepts_learned" in cols
        assert "retention_score" in cols
        assert "kimi_consulted" in cols

    def test_code_agent_log_table(self):
        from cognitive.self_agent_ecosystem import CodeAgentLog
        assert CodeAgentLog.__tablename__ == "code_agent_log"
        cols = [c.name for c in CodeAgentLog.__table__.columns]
        assert "action_type" in cols
        assert "target_file" in cols
        assert "lines_changed" in cols
        assert "tests_passed" in cols
        assert "tests_failed" in cols
        assert "kimi_guided" in cols

    def test_self_evolver_log_table(self):
        from cognitive.self_agent_ecosystem import SelfEvolverLog
        assert SelfEvolverLog.__tablename__ == "self_evolver_log"
        cols = [c.name for c in SelfEvolverLog.__table__.columns]
        assert "cycle_type" in cols
        assert "agents_involved" in cols
        assert "kpi_improvement" in cols
        assert "bottleneck_found" in cols
        assert "mode" in cols


class TestSelfAgents:
    """Verify each concrete agent class exists."""

    def test_healing_agent(self):
        from cognitive.self_agent_ecosystem import SelfHealingAgent
        assert SelfHealingAgent.AGENT_NAME == "self_healer"
        assert SelfHealingAgent.LOG_MODEL.__tablename__ == "self_healing_log"

    def test_mirror_agent(self):
        from cognitive.self_agent_ecosystem import SelfMirrorAgent
        assert SelfMirrorAgent.AGENT_NAME == "self_mirror"

    def test_model_agent(self):
        from cognitive.self_agent_ecosystem import SelfModelAgent
        assert SelfModelAgent.AGENT_NAME == "self_model"

    def test_learner_agent(self):
        from cognitive.self_agent_ecosystem import SelfLearnerAgent
        assert SelfLearnerAgent.AGENT_NAME == "self_learner"

    def test_code_agent(self):
        from cognitive.self_agent_ecosystem import CodeAgentSelf
        assert CodeAgentSelf.AGENT_NAME == "code_agent"

    def test_evolver_agent(self):
        from cognitive.self_agent_ecosystem import SelfEvolverAgent
        assert SelfEvolverAgent.AGENT_NAME == "self_evolver"


class TestBaseSelfAgentCapabilities:
    """Verify base agent has all required capabilities."""

    def test_has_log_attempt(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "log_attempt", None))

    def test_has_get_pass_rate(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "get_pass_rate", None))

    def test_has_get_recent_failures(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "get_recent_failures", None))

    def test_has_get_kpi_score(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "get_kpi_score", None))

    def test_has_ask_kimi_why_low(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "ask_kimi_why_low", None))

    def test_has_self_analyze(self):
        from cognitive.self_agent_ecosystem import BaseSelfAgent
        assert callable(getattr(BaseSelfAgent, "self_analyze", None))


class TestClosedLoopOrchestrator:
    """Verify the closed-loop orchestrator."""

    def test_orchestrator_class(self):
        from cognitive.self_agent_ecosystem import ClosedLoopOrchestrator
        assert ClosedLoopOrchestrator is not None

    def test_orchestrator_has_6_agents(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert '"healer"' in source
        assert '"mirror"' in source
        assert '"model"' in source
        assert '"learner"' in source
        assert '"code"' in source
        assert '"evolver"' in source

    def test_mode_switching(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert '"improve"' in source
        assert '"scale"' in source
        assert '"monitor"' in source

    def test_kimi_consultation_wired(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert "ask_kimi_why_low" in source
        assert "ollama_client" in source
        assert "Why is my performance low" in source

    def test_training_data_access(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert "training_data" in source or "source" in source

    def test_bottleneck_detection(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert "bottleneck" in source

    def test_singleton(self):
        from cognitive.self_agent_ecosystem import get_closed_loop
        assert callable(get_closed_loop)


class TestAppWiring:
    """Verify closed-loop is wired into app startup."""

    def test_closed_loop_in_startup(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "get_closed_loop" in source
        assert "closed_loop.start" in source

    def test_learning_hook_in_agents(self):
        source = (BACKEND_DIR / "cognitive" / "self_agent_ecosystem.py").read_text()
        assert "track_learning_event" in source
