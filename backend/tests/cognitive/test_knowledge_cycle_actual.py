import pytest
from backend.cognitive.knowledge_cycle import KnowledgeExpansionCycle, get_knowledge_cycle

def test_singleton():
    c1 = get_knowledge_cycle()
    c2 = get_knowledge_cycle()
    assert c1 is c2

def test_config():
    cycle = KnowledgeExpansionCycle()
    assert cycle.config.max_depth == 3

def test_deduplicate():
    cycle = KnowledgeExpansionCycle()
    records = [{"content": "hello", "source": "rag"}, {"content": "hello", "source": "magma"}]
    dedup = cycle._deduplicate(records)
    
    assert len(dedup) == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
