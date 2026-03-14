import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import BaseModel
from backend.cognitive.learning_memory import (
    LearningMemoryManager,
    TrustScorer,
    LearningExample,
    LearningPattern,
    _to_json_str,
    _from_json_str
)

@pytest.fixture
def test_session():
    # Setup in-memory sqlite
    engine = create_engine("sqlite:///:memory:")
    # Create specific tables to avoid global metadata duplicate index issues
    try:
        LearningExample.__table__.create(engine, checkfirst=True)
    except Exception:
        pass
    try:
        LearningPattern.__table__.create(engine, checkfirst=True)
    except Exception:
        pass
        
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_json_converters():
    assert _to_json_str(None) == "{}"
    assert _to_json_str({"a": 1}) == '{"a": 1}'
    assert _to_json_str("already a string") == "already a string"
    assert _to_json_str(123) == '123'
    
    assert _from_json_str(None) == {}
    assert _from_json_str({"a": 1}) == {"a": 1}
    assert _from_json_str('{"a": 1}') == {"a": 1}
    assert _from_json_str("not json") == {"raw": "not json"}

def test_trust_scorer():
    scorer = TrustScorer()
    
    # High trust scenario
    score1 = scorer.calculate_trust_score(
        source="system_observation_success",
        outcome_quality=0.9,
        consistency_score=0.8,
        validation_history={"validated": 5, "invalidated": 0},
        age_days=1
    )
    assert score1 > 0.8
    
    # Low trust scenario
    score2 = scorer.calculate_trust_score(
        source="assumed",
        outcome_quality=0.2,
        consistency_score=0.1,
        validation_history={"validated": 0, "invalidated": 5},
        age_days=100  # Will be hit by decay
    )
    assert score2 < 0.3

def test_ingest_learning_data(test_session):
    manager = LearningMemoryManager(test_session, knowledge_base_path="/tmp")
    
    data = {
        "context": {"state": "initial"},
        "expected": {"action": "move_up"},
        "actual": {"action": "move_up"}
    }
    
    example = manager.ingest_learning_data(
        learning_type="feedback",
        learning_data=data,
        source="system_observation_success",
    )
    
    assert example.id is not None
    assert example.example_type == "feedback"
    assert "move_up" in example.expected_output
    assert example.trust_score > 0.5  # Should be decent trust

def test_extract_pattern(test_session):
    manager = LearningMemoryManager(test_session, knowledge_base_path="/tmp")
    
    # Create 3 similar examples manually
    ex1 = LearningExample(
        example_type="behavior",
        input_context=_to_json_str({"a": 1, "b": 2}),
        expected_output=_to_json_str({"c": 3}),
        actual_output=_to_json_str({"c": 3}),
        trust_score=0.9,
        source="test"
    )
    ex2 = LearningExample(
        example_type="behavior",
        input_context=_to_json_str({"a": 1, "b": 3}),
        expected_output=_to_json_str({"c": 3}),
        actual_output=_to_json_str({"c": 3}),
        trust_score=0.9,
        source="test"
    )
    ex3 = LearningExample(
        example_type="behavior",
        input_context=_to_json_str({"a": 1, "b": 4}),
        expected_output=_to_json_str({"c": 3}),
        actual_output=_to_json_str({"c": 3}),
        trust_score=0.9,
        source="test"
    )
    test_session.add_all([ex1, ex2, ex3])
    test_session.commit()
    
    # Should extract a pattern
    manager._extract_pattern([ex1, ex2, ex3])
    
    patterns = test_session.query(LearningPattern).all()
    assert len(patterns) == 1
    assert patterns[0].pattern_type == "behavior"
    
    # 'a' should be identified as common precondition
    preconditions = _from_json_str(patterns[0].preconditions)
    assert "a" in preconditions

def test_update_trust_on_usage(test_session):
    manager = LearningMemoryManager(test_session, knowledge_base_path="/tmp")
    
    ex = LearningExample(
        example_type="test",
        trust_score=0.5,
        source="test"
    )
    test_session.add(ex)
    test_session.commit()
    
    manager.update_trust_on_usage(ex.id, outcome_success=True)
    
    # Refresh ex
    test_session.refresh(ex)
    assert ex.times_referenced == 1
    assert ex.times_validated == 1
    assert ex.trust_score > 0.5  # Boosted

if __name__ == "__main__":
    pytest.main(['-v', __file__])
