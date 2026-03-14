import pytest
from unittest.mock import MagicMock
from backend.cognitive.predictive_context_loader import TopicRelationshipGraph, WhitelistTrigger, PredictiveContextLoader

def test_topic_graph():
    graph = TopicRelationshipGraph()
    assert "HTTP methods" in graph.get_related_topics("REST API", depth=1)
    
    graph.learn_relationship("REST API", "GraphQL Basics")
    assert "GraphQL Basics" in graph.get_related_topics("REST API", depth=1)

def test_whitelist_trigger():
    trigger = WhitelistTrigger()
    assert trigger.should_prefetch("I need a REST API", {}) is True
    assert trigger.should_prefetch("hello world", {}) is False
    assert trigger.get_prefetch_depth("REST API", {"complexity": 0.8}) == 3

def test_predictive_context_loader():
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = {"chunks": [{"text": "data"}]}
    
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    
    loader = PredictiveContextLoader(session=mock_session, retriever=mock_retriever)
    res = loader.process_query("REST API", {"complexity": 0.8})
    
    assert "main_result" in res
    assert len(res["prefetched_contexts"]) > 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
