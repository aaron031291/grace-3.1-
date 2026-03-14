import pytest
from unittest.mock import patch
from backend.cognitive.self_healing import SelfHealer, get_healer

def test_singleton():
    h1 = get_healer()
    h2 = get_healer()
    assert h1 is h2

@patch("backend.cognitive.self_healing.SelfHealer._check_database", return_value=False)
@patch("backend.cognitive.self_healing.SelfHealer._heal_database", return_value=True)
@patch("backend.cognitive.self_healing.SelfHealer._check_qdrant", return_value=False)
@patch("backend.cognitive.self_healing.SelfHealer._heal_qdrant", return_value=False)
@patch("backend.cognitive.self_healing.SelfHealer._check_llm", return_value=True)
@patch("backend.cognitive.self_healing.SelfHealer._check_memory", return_value=False)
@patch("backend.cognitive.self_healing.SelfHealer._heal_memory")
def test_check_and_heal(m_heal_mem, m_chk_mem, m_chk_llm, m_heal_qdrant, m_chk_qdrant, m_heal_db, m_chk_db):
    healer = SelfHealer()
    res = healer.check_and_heal()
    
    assert "database" in res["healed"]
    assert "qdrant" in res["failed"]
    assert "qdrant->keyword_search" in res.get("fallbacks_active", []) or "qdrant→keyword_search" in res.get("fallbacks_active", [])
    assert "memory_gc" in res["healed"]
    assert m_heal_mem.called

if __name__ == "__main__":
    pytest.main(['-v', __file__])
