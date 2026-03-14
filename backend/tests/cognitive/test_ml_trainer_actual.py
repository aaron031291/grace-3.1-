import pytest
import sys
from unittest.mock import MagicMock
from backend.cognitive.ml_trainer import GraceMLTrainer

def test_ml_trainer_observe():
    trainer = GraceMLTrainer()
    
    # 1. Observe a few items
    trainer.observe("loop_1", {"trust_score": 0.9, "latency_ms": 100}, "success")
    trainer.observe("loop_2", {"trust_score": 0.2, "error_count": 5}, "failure")
    
    assert len(trainer._observations) == 2
    assert trainer._observations[0]["loop"] == "loop_1"
    assert trainer._observations[1]["outcome"] == "failure"

def test_ml_trainer_train_insufficient_data():
    trainer = GraceMLTrainer()
    trainer.observe("loop_1", {"trust_score": 0.9}, "success")
    
    res = trainer.train()
    assert res["status"] == "insufficient_data"
    assert not trainer._trained

def test_ml_trainer_train_and_predict():
    sys.modules["api._genesis_tracker"] = MagicMock()
    sys.modules["cognitive.event_bus"] = MagicMock()
    
    trainer = GraceMLTrainer()
    
    # Needs at least 10 items to train, and at least 5 successes for anomaly detection
    for _ in range(8):
        trainer.observe("test_loop", {"trust_score": 0.9, "latency_ms": 50}, "success")
    for _ in range(5):
        trainer.observe("test_loop", {"trust_score": 0.2, "latency_ms": 500}, "failure")
        
    res = trainer.train()
    assert res["status"] == "trained"
    assert trainer._trained
    
    # Predict success
    pred1 = trainer.predict("test_loop", {"trust_score": 0.85, "latency_ms": 60})
    assert pred1["prediction"] == "success"
    
    # Predict failure
    pred2 = trainer.predict("test_loop", {"trust_score": 0.1, "latency_ms": 600})
    assert pred2["prediction"] == "failure"
    
    # Test anomaly
    pred3 = trainer.predict("test_loop", {"trust_score": -999.0, "latency_ms": 99999})
    assert pred3["is_anomaly"] is True

def test_ml_trainer_predict_untrained():
    trainer = GraceMLTrainer()
    res = trainer.predict("loop_1", {})
    assert res["prediction"] == "unknown"
    assert res["reason"] == "not_trained"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
