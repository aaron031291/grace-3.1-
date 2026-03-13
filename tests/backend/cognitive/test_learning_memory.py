import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime, timezone, timedelta

from backend.cognitive.learning_memory import (
    LearningExample, 
    LearningPattern,
    TrustScorer,
    LearningMemoryManager
)

def test_json_coercion_learning_models():
    ex = LearningExample(example_type="test")
    ex.input_context = {"data": 1}
    assert ex.input_context == '{"data": 1}'
    
    pat = LearningPattern(pattern_name="p1", pattern_type="t1")
    pat.actions = {"act": True}
    assert pat.actions == '{"act": "True"}' or pat.actions == '{"act": true}'

def test_trust_scorer_calculation():
    scorer = TrustScorer()
    
    # Excellent source, good outcome, perfect consistency, no decay
    score1 = scorer.calculate_trust_score(
        source="user_feedback_positive",
        outcome_quality=1.0,
        consistency_score=1.0,
        validation_history={'validated': 10, 'invalidated': 0},
        age_days=0
    )
    # Weights: source(0.9*0.4) + outcome(1.0*0.3) + const(1.0*0.2) + val(1.0*0.1)
    # = 0.36 + 0.3 + 0.2 + 0.1 = 0.96
    assert 0.95 <= score1 <= 0.97
    
    # Half-life decay check (90 days)
    score2 = scorer.calculate_trust_score(
        source="user_feedback_positive",
        outcome_quality=1.0,
        consistency_score=1.0,
        validation_history={'validated': 10, 'invalidated': 0},
        age_days=90
    )
    # Score should be exactly half of score1 due to decay
    assert 0.47 <= score2 <= 0.49

def test_trust_update_on_validation():
    scorer = TrustScorer()
    ex = LearningExample(trust_score=0.5, times_validated=0, times_invalidated=0)
    
    # Validate boosts trust
    scorer.update_trust_on_validation(ex, True)
    assert ex.times_validated == 1
    assert ex.trust_score == pytest.approx(0.55)
    
    # Invalidate reduces trust
    scorer.update_trust_on_validation(ex, False)
    assert ex.times_invalidated == 1
    assert ex.trust_score == pytest.approx(0.44)

@patch("core.kpi_recorder.record_component_kpi")
def test_ingest_learning_data(mock_kpi):
    session = MagicMock()
    manager = LearningMemoryManager(session=session)
    
    # Mocking similar_examples empty
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
    
    ex = manager.ingest_learning_data(
        learning_type="test_feedback",
        learning_data={"context": {"user": "a"}, "expected": {"out": 1}, "actual": {"out": 1}},
        source="system_observation_success"
    )
    
    assert ex.example_type == "test_feedback"
    assert "user" in ex.input_context
    assert ex.outcome_quality == 1.0  # expected matching actual
    assert mock_kpi.called
    session.add.assert_called_with(ex)
    session.flush.assert_called_once()

def test_pattern_extraction_trigger():
    session = MagicMock()
    manager = LearningMemoryManager(session=session)
    
    # Mock existing similar examples to be 3
    ex1 = LearningExample(example_type="test_feedback", input_context='{"a": 1}', expected_output='{"out": 1}', trust_score=0.9)
    ex2 = LearningExample(example_type="test_feedback", input_context='{"a": 1}', expected_output='{"out": 1}', trust_score=0.8)
    ex3 = LearningExample(example_type="test_feedback", input_context='{"a": 1}', expected_output='{"out": 1}', trust_score=0.9)
    
    # For calculation
    ex1.id = "1"
    ex2.id = "2"
    ex3.id = "3"
    
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = [ex1, ex2, ex3]
    
    new_ex = LearningExample(example_type="test_feedback")
    
    # Call internal check
    manager._check_pattern_extraction(new_ex)
    
    # Should have added a LearningPattern
    added_obj = session.add.call_args[0][0]
    assert isinstance(added_obj, LearningPattern)
    assert added_obj.pattern_type == "test_feedback"
    assert "a" in added_obj.preconditions
    assert "out" in added_obj.expected_outcomes
    session.commit.assert_called()

def test_decay_trust_scores():
    session = MagicMock()
    manager = LearningMemoryManager(session=session)
    
    # Mock two examples, one brand new, one 90 days old
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=90)
    
    ex_new = LearningExample(
        source="inferred", trust_score=0.5, created_at=now,
        times_validated=0, times_invalidated=0, outcome_quality=0.5, consistency_score=0.5
    )
    ex_old = LearningExample(
        source="inferred", trust_score=0.5, created_at=old,
        times_validated=0, times_invalidated=0, outcome_quality=0.5, consistency_score=0.5
    )
    
    session.query.return_value.all.return_value = [ex_new, ex_old]
    
    manager.decay_trust_scores()
    
    # Old example should have roughly half the trust score weight of new
    assert ex_old.recency_weight < ex_new.recency_weight
    assert ex_old.trust_score < ex_new.trust_score
    session.commit.assert_called_once()
