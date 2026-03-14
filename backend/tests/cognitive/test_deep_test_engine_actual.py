import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.deep_test_engine import DeepTestEngine

def test_singleton():
    engine1 = DeepTestEngine.get_instance()
    engine2 = DeepTestEngine.get_instance()
    assert engine1 is engine2

@patch("backend.cognitive.deep_test_engine.DeepTestEngine._save_results")
def test_run_logic_tests(mock_save):
    engine = DeepTestEngine()
    
    # Mocking all internal trace methods
    for attr in dir(engine):
        if attr.startswith("_test_") and callable(getattr(engine, attr)):
            setattr(engine, attr, MagicMock(return_value=(True, "OK")))
            
    res = engine.run_logic_tests()
    
    assert res["total"] > 0
    assert res["failed"] == 0
    assert res["errors"] == 0
    assert res["status"] == "ALL PASS"

@patch("cognitive.consensus_engine.run_consensus")
def test_consensus_analyse_failures(mock_consensus):
    engine = DeepTestEngine()
    
    mock_result = MagicMock()
    mock_result.final_output = "Diagnostic information..."
    mock_result.confidence = 0.9
    mock_consensus.return_value = mock_result
    
    # Disable actual fix generation for unit testing
    with patch("llm_orchestrator.factory.get_llm_for_task") as mock_get_llm:
        mock_builder = MagicMock()
        mock_builder.generate.return_value = "def fix(): pass"
        mock_get_llm.return_value = mock_builder
        
        with patch("cognitive.grace_compiler.get_grace_compiler") as mock_get_compiler:
            mock_compiler = MagicMock()
            compile_res = MagicMock()
            compile_res.success = True
            mock_compiler.compile.return_value = compile_res
            mock_get_compiler.return_value = mock_compiler
            
            res = engine._consensus_analyse_failures([{"name": "test_1", "detail": "failed"}])
            
            assert res is not None
            assert res["diagnosis"] == "Diagnostic information..."

if __name__ == "__main__":
    pytest.main(['-v', __file__])
