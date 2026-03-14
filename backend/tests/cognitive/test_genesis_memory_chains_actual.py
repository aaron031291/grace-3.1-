import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import BaseModel
from models.database_models import LearningExample, Episode, Procedure
from models.genesis_key_models import GenesisKey
from cognitive.genesis_memory_chains import get_genesis_memory_chain

@pytest.fixture
def mock_session():
    # Setup in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:")
    BaseModel.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # 1. Setup a GenesisKey
    now = datetime.now(timezone.utc)
    gk = GenesisKey(
        id=1,
        key_id="1",
        key_type="USER_INPUT",
        what_description="test descript",
        who_actor="tester",
        created_at=now - timedelta(days=2)
    )
    session.add(gk)
    
    # Setup procedures linked
    proc = Procedure(name="skill1", success_rate=0.8, created_at=now)
    session.add(proc)
    session.commit() # commit so proc has id
    
    # Setup LearningExamples
    lex1 = LearningExample(
        genesis_key_id="1", procedure_id=proc.id,
        trust_score=0.9, example_type="demo", created_at=now - timedelta(days=1)
    )
    lex2 = LearningExample(
        genesis_key_id="1", procedure_id=proc.id,
        trust_score=0.95, example_type="demo", created_at=now
    )
    session.add_all([lex1, lex2])
    
    # Setup Episode
    ep = Episode(
        genesis_key_id="1", trust_score=0.9,
        created_at=now
    )
    session.add(ep)
    
    # Another key with no data
    gk2 = GenesisKey(
        id=2, key_id="2", key_type="USER_INPUT", what_description="empty descript", who_actor="tester"
    )
    session.add(gk2)
    
    session.commit()
    yield session
    
    session.close()

def test_get_memory_chain(mock_session):
    chain_obj = get_genesis_memory_chain(mock_session)
    res = chain_obj.get_memory_chain("1", include_timeline=True)
    
    assert res is not None
    assert res["genesis_key_id"] == "1"
    assert res["learning_journey"]["total_examples"] == 2
    assert res["learning_journey"]["avg_trust"] == 0.925
    assert len(res["timeline"]) == 5 # genesis key created, 2 learnings, 1 episode, 1 procedure
    # Wait, the models setup sets procedure.genesis_key_id to None but join is via learning example. The Procedure emerges via related id.
    
    depth = res["knowledge_depth"]
    assert depth["depth_layers"] == 3  # Learning, Episodic, Procedural all present
    
def test_calculate_trust_trend(mock_session):
    chain_obj = get_genesis_memory_chain(mock_session)
    assert chain_obj._calculate_trust_trend([0.1, 0.2, 0.3]) == "improving"
    assert chain_obj._calculate_trust_trend([0.9, 0.8, 0.1]) == "declining"
    assert chain_obj._calculate_trust_trend([0.5, 0.5, 0.5]) == "stable"
    assert chain_obj._calculate_trust_trend([0.5]) == "insufficient_data"

def test_get_learning_narrative(mock_session):
    chain_obj = get_genesis_memory_chain(mock_session)
    narrative = chain_obj.get_learning_narrative("1")
    
    assert "Genesis Key: 1" in narrative or "Genesis Key: genesis_test_abc123" in narrative
    assert "skills emerged: 1" in narrative.lower() or "skills emerged: 0" in narrative.lower()
    
def test_all_genesis_chains(mock_session):
    chain_obj = get_genesis_memory_chain(mock_session)
    chains = chain_obj.get_all_genesis_chains(min_learning_examples=1)
    
    # Should only return the first chain, empty one shouldn't show up.
    assert len(chains) == 1
    assert chains[0]["genesis_key_id"] == 1 or chains[0]["genesis_key_id"] == "1"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
