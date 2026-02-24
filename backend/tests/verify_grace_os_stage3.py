import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock

# 1. Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2. Define Mocks for the layer dependency injection
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

# 4. Now import the actual Grace OS components
from grace_os.kernel.message_bus import MessageBus
from grace_os.kernel.layer_registry import LayerRegistry
from grace_os.kernel.session_manager import SessionManager
from grace_os.layers.l2_planning.planning_layer import PlanningLayer
from grace_os.layers.l6_codegen.codegen_layer import CodegenLayer
from grace_os.layers.l7_testing.testing_layer import TestingLayer

# 5. Define functional mocks for the runtime
class MockLLM:
    def execute_task(self, prompt, **kwargs):
        from dataclasses import dataclass
        @dataclass
        class Result:
            success: bool
            content: str
            audit_trail: list
        
        if "Decompose" in prompt:
            # Mocking a JSON task graph
            content = '[{"id": "t1", "description": "Write hello world", "type": "codegen"}]'
        else:
            content = "print('hello world')"
            
        return Result(success=True, content=content, audit_trail=[])

class MockMCP:
    async def call_tool(self, tool_name, arguments, **kwargs):
        print(f"MockMCP: Called {tool_name} with {arguments}")
        return {"success": True, "content": "Tool call successful"}

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("GraceBootstrap")

    # 1. Initialize Kernel
    bus = MessageBus()
    registry = LayerRegistry()
    
    # 2. Shared Services (Functional Mocks)
    llm = MockLLM()
    mcp = MockMCP()
    
    # 3. Initialize Layers
    l2 = PlanningLayer(bus, registry, llm, mcp)
    l6 = CodegenLayer(bus, registry, llm, mcp)
    l7 = TestingLayer(bus, registry, llm, mcp)
    
    # Start Layers
    l2.start()
    l6.start()
    l7.start()
    
    logger.info("Kernel and Layers initialized and running.")

    # 4. Session Manager
    session_mgr = SessionManager(bus, registry)
    
    # 5. Start a session
    trace_id = await session_mgr.start_session("Create a hello world script.")
    
    # 6. Monitor (Wait a bit for async messages to flow)
    # The session_mgr.start_session awaits the planning response, 
    # but the subsequent EXECUTE_TASK in a real loop might be async.
    # In our current SessionManager, it only triggers L2 and waits for planning.
    
    await asyncio.sleep(1)
    
    status = session_mgr.get_session_status(trace_id)
    logger.info(f"Final Session Status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
