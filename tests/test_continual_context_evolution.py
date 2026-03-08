import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure backend module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.verification.context_shadower import ContextShadower

def test_shadower_requires_vvt():
    shadower = ContextShadower()
    
    # Mock VVT Gauntlet to fail
    with patch('backend.verification.deterministic_vvt_pipeline.vvt_vault.run_all_layers') as mock_vvt:
        mock_vvt.return_value = False
        
        result = shadower.propose_module_update("test.py", "print('hello')", "test")
        
        assert result["success"] is False
        assert result["status"] == "VVT_FAILED"
        mock_vvt.assert_called_once()

def test_shadower_mints_trust_coin_on_success():
    shadower = ContextShadower()
    
    # Mock VVT Gauntlet to pass
    with patch('backend.verification.deterministic_vvt_pipeline.vvt_vault.run_all_layers') as mock_vvt:
        mock_vvt.return_value = True
        
        # Mock the atomic swap so we don't actually rename files during test
        with patch.object(shadower, '_atomic_modules_swap') as mock_swap:
            mock_swap.return_value = True
            
            result = shadower.propose_module_update("backend/api/test.py", "print('hello vvt')", "test")
            
            assert result["success"] is True
            assert result["trust_coin"] == "VVT_PLATINUM_COIN"
            assert result["status"] == "ATOMIC_SWAP_COMPLETE"
            mock_vvt.assert_called_once()
            mock_swap.assert_called_once()

def test_unified_memory_trust_gate():
    # Attempt to bypass using unified memory without the required VVT coin
    from backend.cognitive.unified_memory import get_unified_memory
    
    # We shouldn't need a DB connection just to hit the gate if we mock the session
    with patch('backend.database.session.get_session_factory') as mock_db:
        mem = get_unified_memory()
        
        # Attempting to store memory with no coin
        result_no_coin = mem.store_episode("test problem", "test action", "test outcome", source="system")
        assert result_no_coin == "TRUST_GATE_REJECTED"
        
        # Attempting to store memory with invalid coin
        result_bad_coin = mem.store_episode("test problem", "test action", "test outcome", source="system", trust_coin="FAKE_COIN")
        assert result_bad_coin == "TRUST_GATE_REJECTED"
        
        # Attempting to store memory from non-system source even with coin
        result_bad_source = mem.store_episode("test problem", "test action", "test outcome", source="user_input", trust_coin="VVT_PLATINUM_COIN")
        assert result_bad_source == "TRUST_GATE_REJECTED"

def test_memory_heat_circuit_breaker():
    from backend.cognitive.unified_memory import UnifiedMemory
    
    # Reset circuit breaker
    UnifiedMemory._heat_breaker_active = False
    
    with patch('backend.database.session.get_session_factory') as mock_db:
        mem = UnifiedMemory("postgresql://dummy")
        
        # Manually trip it
        UnifiedMemory._heat_breaker_active = True
        
        # Verify it blocks writes
        result = mem.store_learning("test", {}, source="system")
        assert result == "CIRCUIT_BREAKER_ACTIVE_READ_ONLY"
