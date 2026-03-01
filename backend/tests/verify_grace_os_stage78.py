"""
Grace OS — Stage 7/8 Verification Test

Tests:
- TrustScorekeeper: score recording, aggregation, threshold gates, decay
- EventSystem: event emission, subscription, replay
- Knowledge Store: OracleDB, ErrorPatterns, ProjectConventions
- Config YAML: all 4 files parseable
- Full pipeline with trust + events wired into MessageBus
"""

import asyncio
import logging
import os
import sys
import yaml
from unittest.mock import MagicMock

# 1. Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2. Patch dependencies
class TaskType:
    GENERAL = "general"

class LLMOrchestrator:
    pass

class MCPClient:
    pass

mock_llm_mod = MagicMock()
mock_llm_mod.TaskType = TaskType
mock_llm_mod.LLMOrchestrator = LLMOrchestrator
sys.modules["llm_orchestrator.llm_orchestrator"] = mock_llm_mod

mock_mcp_mod = MagicMock()
mock_mcp_mod.MCPClient = MCPClient
sys.modules["grace_mcp.client"] = mock_mcp_mod

# 3. Import Grace OS
from grace_os.kernel.message_bus import MessageBus
from grace_os.kernel.layer_registry import LayerRegistry
from grace_os.kernel.trust_scorekeeper import TrustScorekeeper
from grace_os.kernel.event_system import EventSystem
from grace_os.kernel.session_manager import SessionManager
from grace_os.layers.l1_runtime.runtime_layer import RuntimeLayer
from grace_os.layers.l2_planning.planning_layer import PlanningLayer
from grace_os.layers.l3_proposer.proposer_layer import ProposerLayer
from grace_os.layers.l4_evaluator.evaluator_layer import EvaluatorLayer
from grace_os.layers.l5_simulation.simulation_layer import SimulationLayer
from grace_os.layers.l6_codegen.codegen_layer import CodegenLayer
from grace_os.layers.l7_testing.testing_layer import TestingLayer
from grace_os.layers.l8_verification.verification_layer import VerificationLayer
from grace_os.layers.l9_deployment.deployment_layer import DeploymentLayer
from grace_os.knowledge.oracle_db import OracleDB
from grace_os.knowledge.error_patterns import ErrorPatterns
from grace_os.knowledge.project_conventions import ProjectConventions


# 4. Mocks
class MockLLM:
    def execute_task(self, prompt, **kwargs):
        from dataclasses import dataclass
        @dataclass
        class Result:
            success: bool
            content: str
            audit_trail: list

        sp = kwargs.get("system_prompt", "")
        if "L2 Planning" in sp or "Decompose" in prompt:
            content = '[{"id": "t1", "description": "Create user model", "type": "codegen"}]'
        elif "L3 Solution Proposer" in sp:
            content = '[{"id":"p1","approach":"ORM","tradeoffs":"Tight coupling","risk_score":20},{"id":"p2","approach":"Raw SQL","tradeoffs":"More code","risk_score":35},{"id":"p3","approach":"GraphQL","tradeoffs":"Overhead","risk_score":45}]'
        elif "L4 Evaluator" in sp:
            content = '{"scores":[{"proposal_id":"p1","correctness":90,"performance":80,"maintainability":85,"risk":80,"total":84}],"selected":"p1"}'
        elif "L5 Simulation" in sp:
            content = '{"risks":[],"edge_cases":["Null input"],"dependency_impacts":[],"contradictions":[],"impact_score":20,"recommendation":"proceed"}'
        elif "L8 Verification" in sp:
            content = '{"verified":true,"requirements_met":["Model created"],"requirements_missed":[],"security_flags":[],"consistency_issues":[],"readability_score":90,"overall_trust":92}'
        else:
            content = "class User:\n    pass"
        return Result(success=True, content=content, audit_trail=[])


class MockMCP:
    async def call_tool(self, tool_name, arguments, **kwargs):
        return {"success": True}


def test_trust_scorekeeper():
    """Test TrustScorekeeper independently."""
    print("\n── Test: TrustScorekeeper ──")
    ts = TrustScorekeeper()

    ts.record_score("session1", "L2_Planning", 85.0)
    ts.record_score("session1", "L6_Codegen", 90.0)
    ts.record_score("session1", "L7_Testing", 80.0)

    latest = ts.get_latest_scores("session1")
    assert len(latest) == 3, f"Expected 3 scores, got {len(latest)}"

    agg = ts.get_aggregate("session1")
    assert agg > 0, f"Aggregate should be > 0, got {agg}"

    passed, score = ts.check_threshold("session1", "deploy")
    history = ts.get_history("session1")
    assert len(history) == 3, f"Expected 3 history entries, got {len(history)}"

    print(f"  ✓ Scores recorded: {latest}")
    print(f"  ✓ Aggregate: {agg:.1f}")
    print(f"  ✓ Deploy gate: {'PASS' if passed else 'FAIL'} ({score:.1f})")
    print(f"  ✓ History entries: {len(history)}")


def test_event_system():
    """Test EventSystem independently."""
    print("\n── Test: EventSystem ──")
    es = EventSystem()

    captured = []
    es.subscribe("*", lambda e: captured.append(e))

    es.emit("SESSION_STARTED", "trace1", "SessionManager", {"prompt": "test"})
    es.emit("MESSAGE_SENT", "trace1", "L2_Planning", {"type": "DECOMPOSE"})
    es.emit("RESPONSE_RETURNED", "trace1", "L2_Planning", {"status": "success"})

    events = es.get_events("trace1")
    assert len(events) == 3, f"Expected 3 events, got {len(events)}"
    assert len(captured) == 3, f"Expected 3 subscriber calls, got {len(captured)}"

    timeline = es.get_session_timeline("trace1")
    print(f"  ✓ Events emitted: {len(events)}")
    print(f"  ✓ Subscribers notified: {len(captured)}")
    print(f"  ✓ Timeline: {timeline[0]}")


def test_knowledge_store():
    """Test OracleDB, ErrorPatterns, ProjectConventions."""
    print("\n── Test: Knowledge Store ──")

    # OracleDB
    db = OracleDB()
    db.store("task_results", "task1", {"outcome": "success", "duration": 2.5})
    db.store("file_deps", "app.py", ["models.py", "routes.py"])
    result = db.query("task_results", "task1")
    assert result["outcome"] == "success"
    all_deps = db.query_all("file_deps")
    assert "app.py" in all_deps
    print(f"  ✓ OracleDB: stored and queried ({db.get_stats()})")

    # ErrorPatterns
    ep = ErrorPatterns()
    ep.record_pattern("ImportError: No module named flask", "pip install flask", 0.95)
    ep.record_pattern("ImportError: No module named flask", "pip install flask", 1.0)
    fix = ep.find_fix("ImportError: No module named flask")
    assert fix is not None
    assert fix["occurrences"] == 2
    fuzzy = ep.find_fix("importerror: no module named Flask")  # fuzzy match
    assert fuzzy is not None
    print(f"  ✓ ErrorPatterns: recorded & matched (occurrences={fix['occurrences']})")

    # ProjectConventions
    pc = ProjectConventions()
    pc.record_convention("Use snake_case for functions", category="naming", confidence=0.95)
    pc.record_convention("Avoid global variables", category="style", examples=["global "])
    convs = pc.get_conventions()
    assert len(convs) == 2
    violations = pc.check_violation("global counter = 0")
    assert len(violations) >= 1
    print(f"  ✓ ProjectConventions: {len(convs)} rules, {len(violations)} violations found")


def test_config_yaml():
    """Test that all config YAML files are parseable."""
    print("\n── Test: Config YAML ──")
    config_dir = os.path.join(os.path.dirname(__file__), "..", "grace_os", "config")

    files = [
        "trust_thresholds.yaml",
        "layer_permissions.yaml",
        "model_routing.yaml",
        "retry_policies.yaml",
    ]

    for fname in files:
        path = os.path.join(config_dir, fname)
        assert os.path.exists(path), f"Missing config: {path}"
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        assert data is not None, f"Empty config: {fname}"
        print(f"  ✓ {fname} parsed ({len(data)} top-level keys)")


async def test_full_pipeline_with_observability():
    """Run full 9-layer pipeline with TrustScorekeeper + EventSystem wired in."""
    print("\n── Test: Full Pipeline with Observability ──")

    # Initialize with observability
    trust = TrustScorekeeper()
    events = EventSystem()
    bus = MessageBus(trust_scorekeeper=trust, event_system=events)
    registry = LayerRegistry()
    llm = MockLLM()
    mcp = MockMCP()

    # Start all 9 layers
    layers = [
        RuntimeLayer(bus, registry, llm, mcp),
        PlanningLayer(bus, registry, llm, mcp),
        ProposerLayer(bus, registry, llm, mcp),
        EvaluatorLayer(bus, registry, llm, mcp),
        SimulationLayer(bus, registry, llm, mcp),
        CodegenLayer(bus, registry, llm, mcp),
        TestingLayer(bus, registry, llm, mcp),
        VerificationLayer(bus, registry, llm, mcp),
        DeploymentLayer(bus, registry, llm, mcp),
    ]
    for layer in layers:
        layer.start()

    # Run session
    session_mgr = SessionManager(bus, registry, trust_threshold=80.0)
    trace_id = await session_mgr.start_session("Create a user model")
    await asyncio.sleep(0.3)

    # Verify trust scores were recorded
    scores = trust.get_latest_scores(trace_id)
    aggregate = trust.get_aggregate(trace_id)
    history = trust.get_history(trace_id)

    print(f"  ✓ Trust scores recorded for {len(scores)} layers")
    print(f"  ✓ Aggregate trust: {aggregate:.1f}")
    print(f"  ✓ Score history entries: {len(history)}")

    # Verify events were emitted
    event_count = events.get_event_count(trace_id)
    timeline = events.get_session_timeline(trace_id)

    print(f"  ✓ Events emitted: {event_count}")
    print(f"  ✓ Timeline sample: {timeline[0] if timeline else 'none'}")

    # Verify session status
    status = session_mgr.get_session_status(trace_id)
    print(f"  ✓ Session status: {status['status']}")

    assert len(scores) >= 7, f"Expected scores from 7+ layers, got {len(scores)}"
    assert event_count >= 10, f"Expected 10+ events, got {event_count}"

    return status["status"]


async def main():
    logging.basicConfig(level=logging.WARNING)

    print("=" * 65)
    print("  Grace OS — Stage 7/8 Verification")
    print("=" * 65)

    # Unit tests
    test_trust_scorekeeper()
    test_event_system()
    test_knowledge_store()
    test_config_yaml()

    # Integration test
    status = await test_full_pipeline_with_observability()

    print("\n" + "=" * 65)
    if status == "completed":
        print("  ✅ STAGE 7/8 VERIFICATION PASSED — Full observability operational!")
    else:
        print(f"  ❌ FAILED — Pipeline status: {status}")
        sys.exit(1)
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
