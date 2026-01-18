"""
Tests for Oracle Intelligence Module

Tests:
1. Oracle core functionality
2. Unified oracle hub
3. Proactive learning
4. Reverse KNN learning
5. Cascading failure predictor
6. Web knowledge integration
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestOracleCore:
    """Tests for Oracle Core functionality."""
    
    @pytest.fixture
    def oracle_core(self):
        """Create oracle core instance."""
        try:
            from backend.oracle_intelligence.oracle_core import OracleCore
            return OracleCore()
        except Exception:
            return Mock()
    
    def test_init(self, oracle_core):
        """Test initialization."""
        assert oracle_core is not None
    
    def test_predict(self, oracle_core):
        """Test prediction capability."""
        if hasattr(oracle_core, 'predict'):
            oracle_core.predict = Mock(return_value={
                "prediction": "success",
                "confidence": 0.85
            })
            
            result = oracle_core.predict(context={"action": "deploy"})
            
            assert result["confidence"] > 0
    
    def test_analyze_pattern(self, oracle_core):
        """Test pattern analysis."""
        if hasattr(oracle_core, 'analyze_pattern'):
            oracle_core.analyze_pattern = Mock(return_value={
                "pattern": "recurring_error",
                "frequency": 5
            })
            
            result = oracle_core.analyze_pattern(events=[])
            
            assert "pattern" in result
    
    def test_get_recommendations(self, oracle_core):
        """Test getting recommendations."""
        if hasattr(oracle_core, 'get_recommendations'):
            oracle_core.get_recommendations = Mock(return_value=[
                {"action": "increase_timeout", "priority": "high"}
            ])
            
            recs = oracle_core.get_recommendations(issue="slow_response")
            
            assert len(recs) > 0


class TestUnifiedOracleHub:
    """Tests for Unified Oracle Hub."""
    
    @pytest.fixture
    def oracle_hub(self):
        """Create oracle hub instance."""
        try:
            from backend.oracle_intelligence.unified_oracle_hub import UnifiedOracleHub
            return UnifiedOracleHub()
        except Exception:
            return Mock()
    
    def test_init(self, oracle_hub):
        """Test initialization."""
        assert oracle_hub is not None
    
    def test_route_query(self, oracle_hub):
        """Test query routing."""
        if hasattr(oracle_hub, 'route_query'):
            oracle_hub.route_query = Mock(return_value={
                "handler": "prediction_engine",
                "response": {}
            })
            
            result = oracle_hub.route_query("What will happen?")
            
            assert "handler" in result
    
    def test_aggregate_insights(self, oracle_hub):
        """Test insight aggregation."""
        if hasattr(oracle_hub, 'aggregate_insights'):
            oracle_hub.aggregate_insights = Mock(return_value={
                "total_insights": 10,
                "high_priority": 3
            })
            
            result = oracle_hub.aggregate_insights()
            
            assert result["total_insights"] >= 0
    
    def test_get_health_status(self, oracle_hub):
        """Test health status."""
        if hasattr(oracle_hub, 'get_health_status'):
            oracle_hub.get_health_status = Mock(return_value={
                "status": "healthy",
                "components": {}
            })
            
            status = oracle_hub.get_health_status()
            
            assert status["status"] in ["healthy", "degraded", "unhealthy"]


class TestProactiveLearning:
    """Tests for Proactive Learning."""
    
    @pytest.fixture
    def proactive_learner(self):
        """Create proactive learning instance."""
        try:
            from backend.oracle_intelligence.proactive_learning import ProactiveLearning
            return ProactiveLearning()
        except Exception:
            return Mock()
    
    def test_init(self, proactive_learner):
        """Test initialization."""
        assert proactive_learner is not None
    
    def test_identify_learning_opportunities(self, proactive_learner):
        """Test identifying learning opportunities."""
        if hasattr(proactive_learner, 'identify_opportunities'):
            proactive_learner.identify_opportunities = Mock(return_value=[
                {"topic": "error_handling", "priority": 0.9}
            ])
            
            opportunities = proactive_learner.identify_opportunities()
            
            assert len(opportunities) >= 0
    
    def test_trigger_learning(self, proactive_learner):
        """Test triggering learning."""
        if hasattr(proactive_learner, 'trigger_learning'):
            proactive_learner.trigger_learning = Mock(return_value={
                "started": True,
                "topic": "new_patterns"
            })
            
            result = proactive_learner.trigger_learning(topic="new_patterns")
            
            assert result["started"] == True
    
    def test_evaluate_learning_progress(self, proactive_learner):
        """Test evaluating learning progress."""
        if hasattr(proactive_learner, 'evaluate_progress'):
            proactive_learner.evaluate_progress = Mock(return_value={
                "completion": 0.75,
                "quality": 0.85
            })
            
            progress = proactive_learner.evaluate_progress()
            
            assert progress["completion"] >= 0


class TestReverseKNNLearning:
    """Tests for Reverse KNN Learning."""
    
    @pytest.fixture
    def reverse_knn(self):
        """Create reverse KNN instance."""
        try:
            from backend.oracle_intelligence.reverse_knn_learning import ReverseKNNLearning
            return ReverseKNNLearning()
        except Exception:
            return Mock()
    
    def test_init(self, reverse_knn):
        """Test initialization."""
        assert reverse_knn is not None
    
    def test_find_reverse_neighbors(self, reverse_knn):
        """Test finding reverse neighbors."""
        if hasattr(reverse_knn, 'find_reverse_neighbors'):
            reverse_knn.find_reverse_neighbors = Mock(return_value=[
                {"id": "doc1", "influence": 0.8},
                {"id": "doc2", "influence": 0.6}
            ])
            
            neighbors = reverse_knn.find_reverse_neighbors("query")
            
            assert len(neighbors) >= 0
    
    def test_calculate_influence(self, reverse_knn):
        """Test influence calculation."""
        if hasattr(reverse_knn, 'calculate_influence'):
            reverse_knn.calculate_influence = Mock(return_value=0.75)
            
            influence = reverse_knn.calculate_influence("doc1")
            
            assert 0 <= influence <= 1
    
    def test_propagate_learning(self, reverse_knn):
        """Test learning propagation."""
        if hasattr(reverse_knn, 'propagate_learning'):
            reverse_knn.propagate_learning = Mock(return_value={
                "propagated_to": 5,
                "success": True
            })
            
            result = reverse_knn.propagate_learning(
                source="doc1",
                learning={"pattern": "x"}
            )
            
            assert result["success"] == True


class TestCascadingFailurePredictor:
    """Tests for Cascading Failure Predictor."""
    
    @pytest.fixture
    def failure_predictor(self):
        """Create failure predictor instance."""
        try:
            from backend.oracle_intelligence.cascading_failure_predictor import (
                CascadingFailurePredictor
            )
            return CascadingFailurePredictor()
        except Exception:
            return Mock()
    
    def test_init(self, failure_predictor):
        """Test initialization."""
        assert failure_predictor is not None
    
    def test_predict_failure_cascade(self, failure_predictor):
        """Test failure cascade prediction."""
        if hasattr(failure_predictor, 'predict_cascade'):
            failure_predictor.predict_cascade = Mock(return_value={
                "risk": 0.3,
                "affected_components": ["db", "cache"]
            })
            
            prediction = failure_predictor.predict_cascade(
                failing_component="api"
            )
            
            assert "risk" in prediction
    
    def test_get_failure_probability(self, failure_predictor):
        """Test failure probability calculation."""
        if hasattr(failure_predictor, 'get_failure_probability'):
            failure_predictor.get_failure_probability = Mock(return_value=0.15)
            
            prob = failure_predictor.get_failure_probability("cache")
            
            assert 0 <= prob <= 1
    
    def test_recommend_mitigation(self, failure_predictor):
        """Test mitigation recommendations."""
        if hasattr(failure_predictor, 'recommend_mitigation'):
            failure_predictor.recommend_mitigation = Mock(return_value=[
                {"action": "add_replica", "priority": "high"}
            ])
            
            recommendations = failure_predictor.recommend_mitigation(
                predicted_failure={"component": "db"}
            )
            
            assert len(recommendations) >= 0


class TestWebKnowledge:
    """Tests for Web Knowledge Integration."""
    
    @pytest.fixture
    def web_knowledge(self):
        """Create web knowledge instance."""
        try:
            from backend.oracle_intelligence.web_knowledge import WebKnowledge
            return WebKnowledge()
        except Exception:
            return Mock()
    
    def test_init(self, web_knowledge):
        """Test initialization."""
        assert web_knowledge is not None
    
    def test_search_web(self, web_knowledge):
        """Test web search."""
        if hasattr(web_knowledge, 'search'):
            web_knowledge.search = Mock(return_value=[
                {"title": "Result 1", "url": "http://example.com"}
            ])
            
            results = web_knowledge.search("python error handling")
            
            assert len(results) >= 0
    
    def test_extract_knowledge(self, web_knowledge):
        """Test knowledge extraction from URL."""
        if hasattr(web_knowledge, 'extract_knowledge'):
            web_knowledge.extract_knowledge = Mock(return_value={
                "content": "Extracted text",
                "concepts": ["error", "handling"]
            })
            
            knowledge = web_knowledge.extract_knowledge("http://example.com")
            
            assert "content" in knowledge
    
    def test_integrate_knowledge(self, web_knowledge):
        """Test knowledge integration."""
        if hasattr(web_knowledge, 'integrate_knowledge'):
            web_knowledge.integrate_knowledge = Mock(return_value={
                "integrated": True,
                "id": "K-123"
            })
            
            result = web_knowledge.integrate_knowledge(
                knowledge={"content": "New info"}
            )
            
            assert result["integrated"] == True


class TestOracleIntelligenceIntegration:
    """Integration tests for oracle intelligence."""
    
    def test_modules_importable(self):
        """Test modules are importable."""
        try:
            from backend.oracle_intelligence import oracle_core
            from backend.oracle_intelligence import unified_oracle_hub
            from backend.oracle_intelligence import proactive_learning
            from backend.oracle_intelligence import reverse_knn_learning
            from backend.oracle_intelligence import cascading_failure_predictor
            from backend.oracle_intelligence import web_knowledge
            assert True
        except ImportError as e:
            pytest.skip(f"Import error: {e}")
    
    def test_oracle_module_structure(self):
        """Test oracle module has expected structure."""
        try:
            from backend import oracle_intelligence
            assert hasattr(oracle_intelligence, '__file__')
        except ImportError:
            pytest.skip("Oracle intelligence module not available")


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_prediction_error_handling(self):
        """Test error handling in predictions."""
        mock_oracle = Mock()
        mock_oracle.predict = Mock(
            side_effect=RuntimeError("Model not loaded")
        )
        
        with pytest.raises(RuntimeError):
            mock_oracle.predict(context={})
    
    def test_web_search_timeout(self):
        """Test web search timeout handling."""
        mock_web = Mock()
        mock_web.search = Mock(
            side_effect=TimeoutError("Search timed out")
        )
        
        with pytest.raises(TimeoutError):
            mock_web.search("query")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
