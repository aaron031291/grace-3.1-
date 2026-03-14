import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.reverse_knn import ReverseKNNOracle, get_reverse_knn

def test_singleton():
    r1 = get_reverse_knn()
    r2 = get_reverse_knn()
    assert r1 is r2

def test_scan_knowledge_gaps_text_fallback():
    oracle = ReverseKNNOracle()
    # If no embeddings, uses fallback
    res = oracle.scan_knowledge_gaps()
    assert "sparse_regions" in res
    assert "demand_gaps" in res
    assert "summary" in res

@patch("backend.cognitive.reverse_knn.ReverseKNNOracle._load_all_embeddings")
def test_scan_knowledge_gaps_with_embeddings(mock_load):
    # Mock some embeddings
    mock_load.return_value = [
        ("id1", [0.1, 0.2, 0.3], {"source": "test"}),
        ("id2", [0.9, 0.8, 0.7], {"source": "test"})
    ]
    oracle = ReverseKNNOracle()
    res = oracle.scan_knowledge_gaps(k=10, distance_threshold=0.6, min_neighbours=3)
    
    assert res["summary"]["total_embeddings"] == 2
    # Should have sparse regions since min_neighbours is 3 and we only have 2
    assert len(res["sparse_regions"]) > 0

def test_log_query():
    oracle = ReverseKNNOracle()
    oracle.log_query("test query", False)
    assert len(oracle._query_log) == 1
    assert oracle.get_demand_gaps()[0]["topic"] == "test"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
