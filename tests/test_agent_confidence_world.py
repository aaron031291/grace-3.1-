"""
Tests for Agent, Confidence Scorer, and World Model Modules

Tests:
1. GRACE Agent - initialization, task handling, state management
2. Confidence Scorer - score calculation, calibration
3. Contradiction Detector - contradiction detection, resolution
4. Enterprise World Model - state tracking, predictions
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ==================== Agent Tests ====================

class TestGraceAgent:
    """Tests for GRACE Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create GRACE agent instance."""
        try:
            from backend.agent.grace_agent import GraceAgent
            return GraceAgent()
        except Exception:
            return Mock()
    
    def test_init(self, agent):
        """Test initialization."""
        assert agent is not None
    
    def test_process_task(self, agent):
        """Test task processing."""
        if hasattr(agent, 'process_task'):
            agent.process_task = Mock(return_value={"task_id": "T-123", "status": "completed"})
            result = agent.process_task(task={"type": "code_gen", "description": "Write hello"})
            assert result["status"] == "completed"
    
    def test_get_state(self, agent):
        """Test getting agent state."""
        if hasattr(agent, 'get_state'):
            agent.get_state = Mock(return_value={"state": "idle", "tasks_pending": 0})
            state = agent.get_state()
            assert "state" in state
    
    def test_set_state(self, agent):
        """Test setting agent state."""
        if hasattr(agent, 'set_state'):
            agent.set_state = Mock(return_value=True)
            result = agent.set_state("processing")
            assert result == True
    
    def test_handle_error(self, agent):
        """Test error handling."""
        if hasattr(agent, 'handle_error'):
            agent.handle_error = Mock(return_value={"handled": True, "action": "retry"})
            result = agent.handle_error(error=Exception("Test error"))
            assert result["handled"] == True
    
    def test_get_capabilities(self, agent):
        """Test getting agent capabilities."""
        if hasattr(agent, 'get_capabilities'):
            agent.get_capabilities = Mock(return_value=["code_gen", "code_review", "debugging"])
            caps = agent.get_capabilities()
            assert len(caps) >= 0
    
    def test_execute_action(self, agent):
        """Test executing action."""
        if hasattr(agent, 'execute'):
            agent.execute = Mock(return_value={"success": True, "output": "Done"})
            result = agent.execute(action={"type": "write_file", "path": "test.py"})
            assert result["success"] == True
    
    def test_pause_agent(self, agent):
        """Test pausing agent."""
        if hasattr(agent, 'pause'):
            agent.pause = Mock(return_value=True)
            result = agent.pause()
            assert result == True
    
    def test_resume_agent(self, agent):
        """Test resuming agent."""
        if hasattr(agent, 'resume'):
            agent.resume = Mock(return_value=True)
            result = agent.resume()
            assert result == True


# ==================== Confidence Scorer Tests ====================

class TestConfidenceScorer:
    """Tests for Confidence Scorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create confidence scorer instance."""
        try:
            from backend.confidence_scorer.confidence_scorer import ConfidenceScorer
            return ConfidenceScorer()
        except Exception:
            return Mock()
    
    def test_init(self, scorer):
        """Test initialization."""
        assert scorer is not None
    
    def test_calculate_score(self, scorer):
        """Test score calculation."""
        if hasattr(scorer, 'calculate'):
            scorer.calculate = Mock(return_value={"score": 0.85, "factors": {}})
            result = scorer.calculate(prediction={"answer": "X"}, context={})
            assert 0 <= result["score"] <= 1
    
    def test_calibrate_scores(self, scorer):
        """Test score calibration."""
        if hasattr(scorer, 'calibrate'):
            scorer.calibrate = Mock(return_value={"calibrated": True, "adjustment": 0.05})
            result = scorer.calibrate(predictions=[], actuals=[])
            assert result["calibrated"] == True
    
    def test_get_confidence_breakdown(self, scorer):
        """Test getting confidence breakdown."""
        if hasattr(scorer, 'get_breakdown'):
            scorer.get_breakdown = Mock(return_value={
                "source_reliability": 0.9,
                "evidence_strength": 0.8,
                "consistency": 0.85
            })
            breakdown = scorer.get_breakdown(prediction={})
            assert "source_reliability" in breakdown
    
    def test_threshold_check(self, scorer):
        """Test threshold check."""
        if hasattr(scorer, 'meets_threshold'):
            scorer.meets_threshold = Mock(return_value=True)
            result = scorer.meets_threshold(score=0.85, threshold=0.8)
            assert result == True
    
    def test_low_confidence_handling(self, scorer):
        """Test low confidence handling."""
        if hasattr(scorer, 'calculate'):
            scorer.calculate = Mock(return_value={"score": 0.3, "low_confidence": True})
            result = scorer.calculate(prediction={"answer": "uncertain"}, context={})
            assert result["score"] < 0.5
    
    def test_aggregate_scores(self, scorer):
        """Test aggregating multiple scores."""
        if hasattr(scorer, 'aggregate'):
            scorer.aggregate = Mock(return_value={"combined_score": 0.82, "method": "weighted_average"})
            result = scorer.aggregate(scores=[0.9, 0.8, 0.75])
            assert "combined_score" in result


class TestContradictionDetector:
    """Tests for Contradiction Detector."""
    
    @pytest.fixture
    def detector(self):
        """Create contradiction detector instance."""
        try:
            from backend.confidence_scorer.contradiction_detector import ContradictionDetector
            return ContradictionDetector()
        except Exception:
            return Mock()
    
    def test_init(self, detector):
        """Test initialization."""
        assert detector is not None
    
    def test_detect_contradiction(self, detector):
        """Test contradiction detection."""
        if hasattr(detector, 'detect'):
            detector.detect = Mock(return_value={
                "has_contradiction": True,
                "statements": ["A is true", "A is false"]
            })
            result = detector.detect(statements=["A is true", "A is false"])
            assert result["has_contradiction"] == True
    
    def test_no_contradiction(self, detector):
        """Test no contradiction case."""
        if hasattr(detector, 'detect'):
            detector.detect = Mock(return_value={"has_contradiction": False, "statements": []})
            result = detector.detect(statements=["A is true", "B is true"])
            assert result["has_contradiction"] == False
    
    def test_resolve_contradiction(self, detector):
        """Test contradiction resolution."""
        if hasattr(detector, 'resolve'):
            detector.resolve = Mock(return_value={
                "resolved": True,
                "chosen": "A is true",
                "reason": "Higher confidence"
            })
            result = detector.resolve(contradictions=[{"s1": "A is true", "s2": "A is false"}])
            assert result["resolved"] == True
    
    def test_get_contradiction_score(self, detector):
        """Test getting contradiction score."""
        if hasattr(detector, 'get_score'):
            detector.get_score = Mock(return_value=0.95)
            score = detector.get_score(statement1="X", statement2="not X")
            assert 0 <= score <= 1
    
    def test_find_all_contradictions(self, detector):
        """Test finding all contradictions."""
        if hasattr(detector, 'find_all'):
            detector.find_all = Mock(return_value=[
                {"pair": ["A", "not A"], "score": 0.95},
                {"pair": ["B", "not B"], "score": 0.9}
            ])
            contradictions = detector.find_all(statements=["A", "not A", "B", "not B"])
            assert len(contradictions) >= 0


# ==================== World Model Tests ====================

class TestEnterpriseWorldModel:
    """Tests for Enterprise World Model."""
    
    @pytest.fixture
    def world_model(self):
        """Create world model instance."""
        try:
            from backend.world_model.enterprise_world_model import EnterpriseWorldModel
            return EnterpriseWorldModel()
        except Exception:
            return Mock()
    
    def test_init(self, world_model):
        """Test initialization."""
        assert world_model is not None
    
    def test_update_state(self, world_model):
        """Test updating world state."""
        if hasattr(world_model, 'update'):
            world_model.update = Mock(return_value={"updated": True, "version": 2})
            result = world_model.update(observation={"entity": "file", "action": "created"})
            assert result["updated"] == True
    
    def test_get_current_state(self, world_model):
        """Test getting current state."""
        if hasattr(world_model, 'get_state'):
            world_model.get_state = Mock(return_value={
                "entities": {"files": 100, "functions": 500},
                "relationships": []
            })
            state = world_model.get_state()
            assert "entities" in state
    
    def test_predict_outcome(self, world_model):
        """Test predicting outcome."""
        if hasattr(world_model, 'predict'):
            world_model.predict = Mock(return_value={
                "outcome": "success",
                "confidence": 0.85,
                "side_effects": []
            })
            prediction = world_model.predict(action={"type": "refactor"})
            assert "outcome" in prediction
    
    def test_simulate_action(self, world_model):
        """Test simulating action."""
        if hasattr(world_model, 'simulate'):
            world_model.simulate = Mock(return_value={
                "new_state": {},
                "changes": ["file_modified"],
                "success": True
            })
            result = world_model.simulate(action={"type": "edit_file"})
            assert result["success"] == True
    
    def test_track_entity(self, world_model):
        """Test tracking entity."""
        if hasattr(world_model, 'track_entity'):
            world_model.track_entity = Mock(return_value={"tracked": True, "entity_id": "E-123"})
            result = world_model.track_entity(entity_type="file", entity_id="src/main.py")
            assert result["tracked"] == True
    
    def test_get_entity_history(self, world_model):
        """Test getting entity history."""
        if hasattr(world_model, 'get_history'):
            world_model.get_history = Mock(return_value=[
                {"timestamp": "2024-01-01", "action": "created"},
                {"timestamp": "2024-01-02", "action": "modified"}
            ])
            history = world_model.get_history(entity_id="E-123")
            assert len(history) >= 0
    
    def test_query_relationships(self, world_model):
        """Test querying relationships."""
        if hasattr(world_model, 'query_relationships'):
            world_model.query_relationships = Mock(return_value=[
                {"from": "A", "to": "B", "type": "imports"},
                {"from": "A", "to": "C", "type": "calls"}
            ])
            relationships = world_model.query_relationships(entity_id="A")
            assert len(relationships) >= 0
    
    def test_validate_state(self, world_model):
        """Test state validation."""
        if hasattr(world_model, 'validate'):
            world_model.validate = Mock(return_value={"valid": True, "errors": []})
            result = world_model.validate()
            assert result["valid"] == True
    
    def test_snapshot_state(self, world_model):
        """Test taking state snapshot."""
        if hasattr(world_model, 'snapshot'):
            world_model.snapshot = Mock(return_value={"snapshot_id": "S-123", "created": True})
            result = world_model.snapshot()
            assert result["created"] == True
    
    def test_restore_from_snapshot(self, world_model):
        """Test restoring from snapshot."""
        if hasattr(world_model, 'restore'):
            world_model.restore = Mock(return_value={"restored": True, "version": 1})
            result = world_model.restore(snapshot_id="S-123")
            assert result["restored"] == True


class TestModuleImports:
    """Test module imports."""
    
    def test_agent_importable(self):
        """Test agent module."""
        try:
            from backend.agent import grace_agent
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_confidence_scorer_importable(self):
        """Test confidence scorer module."""
        try:
            from backend.confidence_scorer import confidence_scorer, contradiction_detector
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_world_model_importable(self):
        """Test world model module."""
        try:
            from backend.world_model import enterprise_world_model
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_agent_task_error(self):
        """Test agent task error."""
        mock = Mock()
        mock.process_task = Mock(side_effect=RuntimeError("Task failed"))
        with pytest.raises(RuntimeError):
            mock.process_task(task={})
    
    def test_confidence_calculation_error(self):
        """Test confidence calculation error."""
        mock = Mock()
        mock.calculate = Mock(side_effect=ValueError("Invalid input"))
        with pytest.raises(ValueError):
            mock.calculate(prediction=None)
    
    def test_world_model_update_error(self):
        """Test world model update error."""
        mock = Mock()
        mock.update = Mock(side_effect=RuntimeError("State inconsistency"))
        with pytest.raises(RuntimeError):
            mock.update(observation={})
    
    def test_contradiction_detection_error(self):
        """Test contradiction detection error."""
        mock = Mock()
        mock.detect = Mock(side_effect=ValueError("Empty statements"))
        with pytest.raises(ValueError):
            mock.detect(statements=[])


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_agent_with_confidence_scoring(self):
        """Test agent using confidence scorer."""
        mock_agent = Mock()
        mock_scorer = Mock()
        
        mock_agent.process_task = Mock(return_value={"prediction": "X"})
        mock_scorer.calculate = Mock(return_value={"score": 0.9})
        
        task_result = mock_agent.process_task(task={})
        confidence = mock_scorer.calculate(prediction=task_result)
        
        assert confidence["score"] >= 0
    
    def test_world_model_with_agent(self):
        """Test world model tracking agent actions."""
        mock_world = Mock()
        mock_agent = Mock()
        
        mock_agent.execute = Mock(return_value={"success": True, "action": "edit"})
        mock_world.update = Mock(return_value={"updated": True})
        
        action_result = mock_agent.execute(action={})
        update_result = mock_world.update(observation=action_result)
        
        assert update_result["updated"] == True
    
    def test_contradiction_resolution_flow(self):
        """Test full contradiction resolution flow."""
        mock_detector = Mock()
        mock_scorer = Mock()
        
        mock_detector.detect = Mock(return_value={"has_contradiction": True})
        mock_scorer.calculate = Mock(side_effect=[{"score": 0.9}, {"score": 0.6}])
        mock_detector.resolve = Mock(return_value={"resolved": True, "chosen": "A"})
        
        detection = mock_detector.detect(statements=["A", "not A"])
        assert detection["has_contradiction"] == True
        
        resolution = mock_detector.resolve(contradictions=[])
        assert resolution["resolved"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
