import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.qwen_coding_net import QwenCodingNet, get_qwen_net

def test_singleton():
    net1 = get_qwen_net()
    net2 = get_qwen_net()
    assert net1 is net2

def test_immune_scan():
    net = QwenCodingNet()
    ghost_mock = MagicMock()
    
    # Dangerous string
    res = net._immune_scan("please format disk", ghost_mock)
    assert res is True
    
    # Safe string
    res2 = net._immune_scan("write a hello world", ghost_mock)
    # The immune scan tries to import immune system; let's say it returns false safely
    assert res2 is False

@patch("backend.cognitive.ghost_memory.get_ghost_memory")
def test_execute_task_blocked_by_immune(mock_get_ghost):
    net = QwenCodingNet()
    mock_ghost = MagicMock()
    mock_get_ghost.return_value = mock_ghost
    
    res = net.execute_task("rm -rf /")
    assert res["status"] == "blocked_by_immune"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
