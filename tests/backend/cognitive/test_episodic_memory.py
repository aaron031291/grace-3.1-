import pytest
from unittest.mock import MagicMock, patch
import json
import numpy as np
from datetime import datetime, timezone

from backend.cognitive.episodic_memory import Episode, EpisodicBuffer

def test_episode_json_coercion():
    ep = Episode(problem="Test")
    ep.action = {"key": "value"}
    assert ep.action == '{"key": "value"}'
    
    ep.outcome = ["list", "of", "strings"]
    assert ep.outcome == '["list", "of", "strings"]'

def test_record_episode():
    session = MagicMock()
    buffer = EpisodicBuffer(session=session)
    
    ep = buffer.record_episode(
        problem="Test problem",
        action={"method": "run"},
        outcome={"success": True},
        predicted_outcome={"success": True},
        trust_score=0.9
    )
    
    assert ep.problem == "Test problem"
    assert "run" in ep.action
    assert ep.prediction_error == 0.0
    session.add.assert_called_once_with(ep)
    session.commit.assert_called_once()

def test_prediction_error_calculation():
    buffer = EpisodicBuffer(session=MagicMock())
    
    # Perfect match
    err1 = buffer._calculate_prediction_error({"a": 1, "b": 2}, {"a": 1, "b": 2})
    assert err1 == 0.0
    
    # Total failure
    err2 = buffer._calculate_prediction_error({"a": 1}, {"a": 2})
    assert err2 == 1.0
    
    # Partial failure
    err3 = buffer._calculate_prediction_error({"a": 1, "b": 2}, {"a": 1, "b": 3})
    assert err3 == 0.5

@patch('backend.cognitive.episodic_memory.np.dot')
@patch('backend.cognitive.episodic_memory.np.linalg.norm')
def test_recall_similar_semantic(mock_norm, mock_dot):
    session = MagicMock()
    embedder = MagicMock()
    buffer = EpisodicBuffer(session=session, embedder=embedder)
    buffer._use_semantic = True
    
    # Mock query returning 2 episodes
    ep1 = Episode(problem="Issue A", trust_score=0.8, embedding="[0.1, 0.2]")
    ep1.timestamp = datetime.now(timezone.utc)
    ep2 = Episode(problem="Issue B", trust_score=0.5, embedding="[0.8, 0.9]")
    ep2.timestamp = datetime.now(timezone.utc)
    
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [ep1, ep2]
    embedder.embed_text.return_value = [[0.1, 0.2]]
    
    # Mock cosine sim math
    mock_dot.side_effect = [1.0, 0.5]
    mock_norm.return_value = 1.0
    
    results = buffer.recall_similar("Query", k=1)
    
    assert len(results) == 1
    assert results[0] == ep1  # It had higher mock dot product
    embedder.embed_text.assert_called_once_with(["Query"])

def test_recall_similar_text_fallback():
    session = MagicMock()
    buffer = EpisodicBuffer(session=session)
    buffer._use_semantic = False
    
    ep1 = Episode(problem="This is a test problem", trust_score=0.8)
    ep2 = Episode(problem="Completely unrelated issue", trust_score=0.9)
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [ep1, ep2]
    
    results = buffer.recall_similar("This test problem", k=1)
    
    assert len(results) == 1
    assert results[0] == ep1  # High word overlap

def test_index_all_episodes():
    session = MagicMock()
    embedder = MagicMock()
    buffer = EpisodicBuffer(session=session, embedder=embedder)
    
    ep1 = Episode(problem="A", embedding=None)
    ep2 = Episode(problem="B", embedding=None)
    
    session.query.return_value.filter.return_value.all.return_value = [ep1, ep2]
    embedder.embed_text.return_value = [[0.1], [0.2]]
    
    count = buffer.index_all_episodes()
    
    assert count == 2
    assert ep1.embedding == "[0.1]"
    assert ep2.embedding == "[0.2]"
    session.commit.assert_called_once()
