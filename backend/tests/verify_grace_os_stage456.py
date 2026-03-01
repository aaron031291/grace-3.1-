"""
Grace OS — Stage 4/5/6 Verification Test

End-to-end test for the full 9-layer pipeline:
L1 (Runtime) → L2 (Planning) → L3 (Proposer) → L4 (Evaluator)
→ L5 (Simulation) → L6 (Codegen) → L7 (Testing) → L8 (Verification)
→ L9 (Deployment Gate)
"""

import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock

# 1. Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2. Define Mocks for dependency injection
class TaskType:
    GENERAL = "general"

class LLMOrchestrator:
    pass

class MCPClient:
    pass

# 3. Patch sys.modules BEFORE importing layers
mock_llm_mod = MagicMock()
mock_llm_mod.TaskType = TaskType
mock_llm_mod.LLMOrchestrator = LLMOrchestrator
sys.modules["llm_orchestrator.llm_orchestrator"] = mock_llm_mod

mock_mcp_mod = MagicMock()
mock_mcp_mod.MCPClient = MCPClient
sys.modules["grace_mcp.client"] = mock_mcp_mod

# 4. Now import Grace OS components
from grace_os.kernel.message_bus import MessageBus
from grace_os.kernel.layer_registry import LayerRegistry
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

# 5. Functional mocks
class MockLLM:
    """Responds with valid JSON for each layer type."""
    def execute_task(self, prompt, **kwargs):
        from dataclasses import dataclass

        @dataclass
        class Result:
            success: bool
            content: str
            audit_trail: list

        system_prompt = kwargs.get("system_prompt", "")

        # L2 Planning
        if "L2 Planning" in system_prompt or "Decompose" in prompt:
            content = '[{"id": "t1", "description": "Add GET /api/users endpoint", "type": "codegen"}]'

        # L3 Proposer
        elif "L3 Solution Proposer" in system_prompt:
            content = (
                '[{"id":"p1","approach":"Flask Blueprint with SQLAlchemy","tradeoffs":"Tight ORM coupling","risk_score":20},'
                '{"id":"p2","approach":"Raw SQL with connection pooling","tradeoffs":"More control, more code","risk_score":35},'
                '{"id":"p3","approach":"FastAPI with Pydantic models","tradeoffs":"Modern but migration needed","risk_score":45}]'
            )

        # L4 Evaluator
        elif "L4 Evaluator" in system_prompt:
            content = (
                '{"scores":[{"proposal_id":"p1","correctness":90,"performance":80,"maintainability":85,"risk":80,"total":84},'
                '{"proposal_id":"p2","correctness":75,"performance":90,"maintainability":60,"risk":65,"total":73},'
                '{"proposal_id":"p3","correctness":85,"performance":85,"maintainability":90,"risk":55,"total":79}],'
                '"selected":"p1"}'
            )

        # L5 Simulation
        elif "L5 Simulation" in system_prompt:
            content = (
                '{"risks":["Route collision with existing /api/admin"],'
                '"edge_cases":["Empty user list","Invalid user ID"],'
                '"dependency_impacts":["models.py needs User model"],'
                '"contradictions":[],"impact_score":25,"recommendation":"proceed"}'
            )

        # L8 Verification
        elif "L8 Verification" in system_prompt:
            content = (
                '{"verified":true,"requirements_met":["GET endpoint created"],'
                '"requirements_missed":[],"security_flags":[],'
                '"consistency_issues":[],"readability_score":85,"overall_trust":88}'
            )

        # L6 Codegen (default)
        else:
            content = "from flask import Blueprint\nusers_bp = Blueprint('users', __name__)\n@users_bp.route('/api/users')\ndef get_users():\n    return {'users': []}"

        return Result(success=True, content=content, audit_trail=[])

class MockMCP:
    async def call_tool(self, tool_name, arguments, **kwargs):
        return {"success": True, "content": f"Mock {tool_name} executed"}


async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("Stage456Test")

    print("=" * 70)
    print("  Grace OS — Stage 4/5/6 Verification: Full 9-Layer Pipeline")
    print("=" * 70)

    # 1. Initialize Kernel
    bus = MessageBus()
    registry = LayerRegistry()

    # 2. Shared Services
    llm = MockLLM()
    mcp = MockMCP()

    # 3. Initialize ALL 9 layers
    layers = {
        "L1": RuntimeLayer(bus, registry, llm, mcp),
        "L2": PlanningLayer(bus, registry, llm, mcp),
        "L3": ProposerLayer(bus, registry, llm, mcp),
        "L4": EvaluatorLayer(bus, registry, llm, mcp),
        "L5": SimulationLayer(bus, registry, llm, mcp),
        "L6": CodegenLayer(bus, registry, llm, mcp),
        "L7": TestingLayer(bus, registry, llm, mcp),
        "L8": VerificationLayer(bus, registry, llm, mcp),
        "L9": DeploymentLayer(bus, registry, llm, mcp),
    }

    # Start all layers
    for name, layer in layers.items():
        layer.start()
        logger.info(f"✓ {name} ({layer.layer_name}) started")

    print("\n" + "-" * 70)
    print("  All 9 layers registered. Starting session...")
    print("-" * 70 + "\n")

    # 4. Session Manager
    session_mgr = SessionManager(bus, registry, trust_threshold=80.0)

    # 5. Run full pipeline
    trace_id = await session_mgr.start_session("Add a REST endpoint for listing users")

    # 6. Wait for async processing
    await asyncio.sleep(0.5)

    # 7. Check results
    status = session_mgr.get_session_status(trace_id)

    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"  Status:      {status['status']}")
    print(f"  Trust Score:  {status['trust_score']:.1f}")
    print(f"  Tasks:        {status['tasks_count']}")
    print(f"  Duration:     {status['duration_sec']:.2f}s")
    if status['error']:
        print(f"  Error:        {status['error']}")
    print("=" * 70)

    # 8. Assertions
    if status["status"] == "completed":
        print("\n  ✅ STAGE 4/5/6 VERIFICATION PASSED — Full 9-layer pipeline operational!")
    else:
        print(f"\n  ❌ VERIFICATION FAILED — Status: {status['status']}, Error: {status['error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
