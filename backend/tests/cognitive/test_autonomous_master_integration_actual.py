import pytest
from pathlib import Path
from backend.cognitive.autonomous_master_integration import AutonomousMasterIntegration

class MockSession:
    def add(self, item):
        pass
    def commit(self):
        pass
    def refresh(self, item):
        pass
    def query(self, *args, **kwargs):
        class MockQuery:
            def filter_by(self, **kw):
                return self
            def first(self):
                return {"id": "genesis_key_123"}
        return MockQuery()

def test_master_integration_initialization(monkeypatch):
    import backend.cognitive.autonomous_master_integration as ami
    
    # Mock imported functions in ami
    monkeypatch.setattr(ami, "get_layer1_integration", lambda session: "layer1_mock")
    monkeypatch.setattr(ami, "get_genesis_trigger_pipeline", lambda session, knowledge_base_path, orchestrator: "trigger_pipeline_mock")
    monkeypatch.setattr(ami, "get_memory_mesh_learner", lambda session: "memory_learner_mock")
    
    class MockOrchestrator:
        def __init__(self, *args, **kwargs):
            self.started = False
        def start(self):
            self.started = True
        def get_status(self):
            return {"total_subagents": 0}
    
    monkeypatch.setattr(ami, "LearningOrchestrator", MockOrchestrator)
    
    master = AutonomousMasterIntegration(
        session=MockSession(),
        knowledge_base_path=Path("/test"),
        enable_learning=True
    )
    
    master.initialize()
    
    assert master.layer1 == "layer1_mock"
    assert master.trigger_pipeline == "trigger_pipeline_mock"
    assert master.memory_learner == "memory_learner_mock"
    assert master.learning_orchestrator.started is True

def test_master_integration_process_input(monkeypatch):
    master = AutonomousMasterIntegration(
        session=MockSession(),
        knowledge_base_path=Path("/test"),
        enable_learning=False
    )
    
    class MockLayer1:
        def process_user_input(self, *args, **kwargs):
            return {"genesis_key_id": "genesis_key_123"}
    
    class MockTriggerPipeline:
        def on_genesis_key_created(self, key):
            return {"actions_triggered": ["trigger_A", "trigger_B"]}
            
    master.layer1 = MockLayer1()
    master.trigger_pipeline = MockTriggerPipeline()
    master.memory_learner = None # optional mock
    
    result = master.process_input("hello", "user_input", "user_1")
    
    assert master.total_inputs_processed == 1
    assert "genesis_key_id" in result
    assert result["genesis_key_id"] == "genesis_key_123"
    assert "trigger_A" in result["autonomous_actions"]["actions_triggered"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
