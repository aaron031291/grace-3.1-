import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.cognitive.qwen_triad_orchestrator import QwenTriadOrchestrator, TriadContext, get_triad_orchestrator

def test_singleton():
    o1 = get_triad_orchestrator()
    o2 = get_triad_orchestrator()
    assert o1 is o2

@pytest.mark.asyncio
async def test_triage():
    orchestrator = QwenTriadOrchestrator()
    ctx = TriadContext(prompt="test prompt")
    
    with patch("llm_orchestrator.factory.get_llm_for_task") as mock_get_llm:
        mock_client = MagicMock()
        mock_client.generate.return_value = "code|medium|yes|yes"
        mock_get_llm.return_value = mock_client
        
        await orchestrator._triage(ctx)
        
        assert ctx.triage["intent"] == "code"
        assert ctx.triage["needs_code"] is True

@pytest.mark.asyncio
async def test_run_triad():
    orchestrator = QwenTriadOrchestrator()
    ctx = TriadContext(prompt="test prompt")
    ctx.triage = {"needs_code": True, "needs_reasoning": True}
    
    with patch("backend.cognitive.qwen_triad_orchestrator.QwenTriadOrchestrator._call_model", side_effect=["code resp", "reason resp", "fast resp"]) as mock_call:
        await orchestrator._run_triad(ctx)
        
        assert mock_call.call_count == 3
        assert ctx.code_output == "code resp"
        assert ctx.reason_output == "reason resp"
        assert ctx.fast_output == "fast resp"

@pytest.mark.asyncio
async def test_build_subsystem_summary():
    orchestrator = QwenTriadOrchestrator()
    ctx = TriadContext(prompt="test prompt")
    
    ctx.diagnostic_context = {"health": "good"}
    ctx.trust_context = {"system_trust": 0.99}
    
    res = orchestrator._build_subsystem_summary(ctx)
    assert "good" in res
    assert "0.99" in res

@pytest.mark.asyncio
async def test_synthesize():
    orchestrator = QwenTriadOrchestrator()
    ctx = TriadContext(prompt="test prompt")
    ctx.code_output = "code"
    ctx.fast_output = "fast"
    ctx.reason_output = "reason"
    
    with patch("llm_orchestrator.factory.get_llm_for_task") as mock_get_llm:
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "synthesis 123"}}
        mock_get_llm.return_value = mock_client
        
        await orchestrator._synthesize(ctx)
        
        assert ctx.synthesis == "synthesis 123"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
