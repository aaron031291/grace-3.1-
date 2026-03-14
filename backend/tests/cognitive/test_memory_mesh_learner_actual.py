import pytest
import json
from unittest.mock import MagicMock
from backend.cognitive.memory_mesh_learner import MemoryMeshLearner

def test_identify_knowledge_gaps():
    session = MagicMock()
    learner = MemoryMeshLearner(session)
    
    # Mock LearningExample
    class MockExample:
        def __init__(self, metadata, context):
            self.id = "ex-1"
            self.example_metadata = json.dumps(metadata)
            self.input_context = json.dumps(context)
            self.trust_score = 0.9

    ex1 = MockExample({"data_confidence": 0.9, "operational_confidence": 0.2}, {"topic": "python_ast"})
    ex2 = MockExample({"data_confidence": 0.9, "operational_confidence": 0.8}, {"topic": "pytest"})
    
    session.query.return_value.limit.return_value.all.return_value = [ex1, ex2]
    
    gaps = learner.identify_knowledge_gaps()
    assert len(gaps) == 1
    assert gaps[0]["topic"] == "python_ast"
    assert gaps[0]["recommendation"] == "practice"

def test_identify_high_value_topics():
    session = MagicMock()
    learner = MemoryMeshLearner(session)
    
    class MockExample:
        def __init__(self, context, trust_score):
            self.input_context = json.dumps(context)
            self.trust_score = trust_score

    # 5 examples for standard_topic with high trust
    examples = [MockExample({"topic": "standard_topic"}, 0.9)] * 5
    # 2 examples for low_topic
    examples.extend([MockExample({"topic": "low_topic"}, 0.9)] * 2)
    # 5 examples for untrusted_topic with low trust
    examples.extend([MockExample({"topic": "untrusted_topic"}, 0.3)] * 5)
    
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = examples
    
    topics = learner.identify_high_value_topics(min_occurrences=5, min_trust_score=0.8)
    assert len(topics) == 1
    assert topics[0]["topic"] == "standard_topic"
    assert topics[0]["occurrences"] == 5

def test_identify_related_topic_clusters():
    session = MagicMock()
    learner = MemoryMeshLearner(session)
    
    class MockExample:
        def __init__(self, file_path, topic):
            self.example_metadata = json.dumps({"file_path": file_path})
            self.input_context = json.dumps({"topic": topic})

    examples = [
        MockExample("file1.py", "topic_A"),
        MockExample("file1.py", "topic_B"),
        MockExample("file2.py", "topic_A"),
        MockExample("file2.py", "topic_B"),
        MockExample("file3.py", "topic_C"),
    ]
    
    session.query.return_value.limit.return_value.all.return_value = examples
    
    clusters = learner.identify_related_topic_clusters(min_correlation=0.5)
    
    assert len(clusters) >= 1
    assert clusters[0]["topic1"] == "topic_A"
    assert clusters[0]["topic2"] == "topic_B"
    assert clusters[0]["recommendation"] == "study_together"

def test_analyze_failure_patterns():
    session = MagicMock()
    learner = MemoryMeshLearner(session)
    
    class MockExample:
        def __init__(self, topic, validated, invalidated):
            self.id = "ex-1"
            self.input_context = json.dumps({"topic": topic})
            self.example_metadata = "{}"
            self.times_validated = validated
            self.times_invalidated = invalidated
            self.trust_score = 0.3

    ex1 = MockExample("failing_topic", 0, 5)
    
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = [ex1]
    
    patterns = learner.analyze_failure_patterns()
    assert len(patterns) == 1
    assert patterns[0]["topic"] == "failing_topic"
    assert patterns[0]["urgency"] == "high"

@pytest.fixture
def mock_learner():
    session = MagicMock()
    return MemoryMeshLearner(session)

def test_get_learning_suggestions(mock_learner):
    import sys
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    mock_learner.identify_knowledge_gaps = MagicMock(return_value=[{"topic": "gap1", "reason": "r1"}])
    mock_learner.identify_high_value_topics = MagicMock(return_value=[{"topic": "hv1", "reason": "r2"}])
    mock_learner.identify_related_topic_clusters = MagicMock(return_value=[])
    mock_learner.analyze_failure_patterns = MagicMock(return_value=[{"topic": "fail1", "urgency": "high", "reason": "r3"}])
    
    suggestions = mock_learner.get_learning_suggestions()
    
    assert "timestamp" in suggestions
    assert len(suggestions["knowledge_gaps"]) == 1
    assert len(suggestions["high_value_topics"]) == 1
    assert len(suggestions["failure_patterns"]) == 1
    
    # Check priorities compilation
    priorities = suggestions["top_priorities"]
    assert len(priorities) == 3
    # First is high urgency fail
    assert priorities[0]["topic"] == "fail1"
    assert priorities[0]["priority"] == 1
    # Second is gap
    assert priorities[1]["topic"] == "gap1"
    # Third is high value
    assert priorities[2]["topic"] == "hv1"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
