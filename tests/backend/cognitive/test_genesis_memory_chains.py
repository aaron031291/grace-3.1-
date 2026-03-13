import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from models.database_models import (
    LearningExample,
    Episode,
    Procedure
)
from models.genesis_key_models import GenesisKey
from backend.cognitive.genesis_memory_chains import GenesisMemoryChain

def test_calculate_trust_trend():
    session = MagicMock()
    chain = GenesisMemoryChain(session)
    
    # Not enough data
    assert chain._calculate_trust_trend([0.5, 0.6]) == "insufficient_data"
    
    # Improving (first third vs last third difference > 0.1)
    # [0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 0.9, 1.0]
    # First 3rd: [0.1, 0.2] avg 0.15. Last 3rd: [0.9, 1.0] avg 0.95. Diff 0.8 > 0.1
    res = chain._calculate_trust_trend([0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 0.9, 1.0])
    assert res == "improving"
    
    # Declining
    res = chain._calculate_trust_trend([1.0, 0.9, 0.8, 0.5, 0.4, 0.2, 0.1])
    assert res == "declining"
    
    # Stable
    res = chain._calculate_trust_trend([0.5, 0.55, 0.5, 0.55, 0.5, 0.52])
    assert res == "stable"

def test_calculate_knowledge_depth():
    session = MagicMock()
    chain = GenesisMemoryChain(session)
    
    # 3 Learning Examples (2 distinct types), 2 Episodes, 1 Procedure (Success = 0.8)
    ex1 = LearningExample(example_type="code")
    ex2 = LearningExample(example_type="code")
    ex3 = LearningExample(example_type="concept")
    
    ep1 = Episode()
    ep2 = Episode()
    
    proc1 = Procedure(success_rate=0.8)
    
    depth = chain._calculate_knowledge_depth([ex1, ex2, ex3], [ep1, ep2], [proc1])
    
    assert depth["depth_layers"] == 3  # Learning, Episodic, Procedural all exist
    assert depth["breadth_types"] == 2  # 'code', 'concept'
    assert depth["mastery_score"] == 0.8
    assert depth["overall_depth"] == (3/3 + 0.8) / 2  # 0.9

def test_calculate_learning_velocity():
    session = MagicMock()
    chain = GenesisMemoryChain(session)
    
    now = datetime.now(timezone.utc)
    
    # Not enough data
    assert chain._calculate_learning_velocity([LearningExample()])["velocity"] == "not_enough_data"
    
    # Rapid (10+ per day)
    # 20 examples over 1 day
    examples = [LearningExample(created_at=now + timedelta(hours=i*1.2)) for i in range(20)]
    vel = chain._calculate_learning_velocity(examples)
    assert vel["velocity"] == "rapid"
    
    # Minimal (< 0.5 per day)
    # 2 examples over 10 days
    examples = [LearningExample(created_at=now), LearningExample(created_at=now + timedelta(days=10))]
    vel = chain._calculate_learning_velocity(examples)
    assert vel["velocity"] == "minimal"

def test_get_memory_chain_narrative():
    session = MagicMock()
    chain = GenesisMemoryChain(session)
    
    # Mocking get_memory_chain dependencies
    gk = GenesisKey(key_id="Test Key", who_actor="testing")
    session.query.return_value.filter.return_value.first.return_value = gk
    
    # Return empty lists for learning, episodic, procedural to test base narrative
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    session.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = []
    
    narrative = chain.get_learning_narrative("test_id")
    
    assert "Genesis Key: Test Key" in narrative
    assert "Source: testing" in narrative
    assert "Total learning examples: 0" in narrative
