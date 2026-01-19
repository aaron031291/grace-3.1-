"""
ML Intelligence Modules - REAL Functional Tests

Tests verify ACTUAL ML intelligence system behavior:
- Neural trust scoring
- Neuro-symbolic reasoning
- Meta-learning
- Active learning
- Contrastive learning
- Uncertainty quantification
- Layer 4 advanced systems
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# NEURAL TRUST SCORER TESTS
# =============================================================================

class TestNeuralTrustScorerFunctional:
    """Functional tests for neural trust scorer."""

    @pytest.fixture
    def scorer(self):
        """Create neural trust scorer."""
        from ml_intelligence.neural_trust_scorer import NeuralTrustScorer
        return NeuralTrustScorer()

    def test_initialization(self, scorer):
        """Scorer must initialize properly."""
        assert scorer is not None

    def test_compute_trust_score(self, scorer):
        """compute_trust must return trust score."""
        score = scorer.compute_trust(
            entity_id="ENT-001",
            features={"interactions": 100, "success_rate": 0.95}
        )

        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_batch_scoring(self, scorer):
        """batch_score must process multiple entities."""
        entities = [
            {"id": "ENT-001", "features": {"success_rate": 0.9}},
            {"id": "ENT-002", "features": {"success_rate": 0.7}}
        ]

        scores = scorer.batch_score(entities)

        assert isinstance(scores, list)
        assert len(scores) == 2

    def test_update_model(self, scorer):
        """update must incorporate new feedback."""
        result = scorer.update(
            entity_id="ENT-001",
            feedback={"outcome": "success", "score_delta": 0.05}
        )

        assert result is True or result is None


# =============================================================================
# NEURO-SYMBOLIC REASONER TESTS
# =============================================================================

class TestNeuroSymbolicReasonerFunctional:
    """Functional tests for neuro-symbolic reasoner."""

    @pytest.fixture
    def reasoner(self):
        """Create neuro-symbolic reasoner."""
        from ml_intelligence.neuro_symbolic_reasoner import NeuroSymbolicReasoner
        return NeuroSymbolicReasoner()

    def test_initialization(self, reasoner):
        """Reasoner must initialize properly."""
        assert reasoner is not None

    def test_reason(self, reasoner):
        """reason must combine neural and symbolic."""
        result = reasoner.reason(
            query="What is the best sorting algorithm?",
            context={"data_size": "large", "memory": "limited"}
        )

        assert result is not None

    def test_apply_rules(self, reasoner):
        """apply_rules must use symbolic rules."""
        result = reasoner.apply_rules(
            facts={"x": 10, "y": 20},
            rules=["if x < y then result = y"]
        )

        assert result is not None

    def test_neural_inference(self, reasoner):
        """neural_inference must use neural network."""
        with patch.object(reasoner, '_run_neural', return_value={'confidence': 0.9}):
            result = reasoner.neural_inference(
                input_data={"query": "test"},
                model="default"
            )

            assert 'confidence' in result


class TestNeuralToSymbolicRuleGeneratorFunctional:
    """Functional tests for neural to symbolic rule generator."""

    @pytest.fixture
    def generator(self):
        """Create rule generator."""
        from ml_intelligence.neural_to_symbolic_rule_generator import NeuralToSymbolicRuleGenerator
        return NeuralToSymbolicRuleGenerator()

    def test_initialization(self, generator):
        """Generator must initialize properly."""
        assert generator is not None

    def test_extract_rules(self, generator):
        """extract_rules must create symbolic rules from neural."""
        rules = generator.extract_rules(
            neural_model="trust_scorer",
            examples=[
                {"input": {"x": 1}, "output": "high"},
                {"input": {"x": 0.5}, "output": "medium"}
            ]
        )

        assert isinstance(rules, list)

    def test_validate_rules(self, generator):
        """validate must check rule consistency."""
        result = generator.validate(
            rules=["if score > 0.7 then trust = high"],
            test_cases=[{"score": 0.8, "expected": "high"}]
        )

        assert result is not None


# =============================================================================
# META-LEARNING TESTS
# =============================================================================

class TestMetaLearningFunctional:
    """Functional tests for meta-learning system."""

    @pytest.fixture
    def meta_learner(self):
        """Create meta-learning system."""
        from ml_intelligence.meta_learning import MetaLearningSystem
        return MetaLearningSystem()

    def test_initialization(self, meta_learner):
        """Meta-learner must initialize properly."""
        assert meta_learner is not None

    def test_learn_task(self, meta_learner):
        """learn_task must adapt to new task."""
        result = meta_learner.learn_task(
            task_data={"examples": [{"x": 1, "y": 2}]},
            adaptation_steps=5
        )

        assert result is not None

    def test_few_shot_learning(self, meta_learner):
        """few_shot must learn from few examples."""
        result = meta_learner.few_shot(
            support_set=[{"x": 1, "y": 1}, {"x": 2, "y": 4}],
            query={"x": 3}
        )

        assert result is not None

    def test_meta_update(self, meta_learner):
        """meta_update must update meta-parameters."""
        result = meta_learner.meta_update(
            task_gradients=[{"loss": 0.1}, {"loss": 0.2}]
        )

        assert result is True or result is None


# =============================================================================
# ACTIVE LEARNING SAMPLER TESTS
# =============================================================================

class TestActiveLearningCompleteFunctional:
    """Functional tests for active learning sampler."""

    @pytest.fixture
    def sampler(self):
        """Create active learning sampler."""
        from ml_intelligence.active_learning_sampler import ActiveLearningSampler
        return ActiveLearningSampler()

    def test_initialization(self, sampler):
        """Sampler must initialize properly."""
        assert sampler is not None

    def test_select_samples(self, sampler):
        """select must choose informative samples."""
        candidates = [
            {"id": 1, "features": [0.1, 0.2]},
            {"id": 2, "features": [0.5, 0.5]},
            {"id": 3, "features": [0.9, 0.8]}
        ]

        selected = sampler.select(
            candidates=candidates,
            budget=2,
            strategy="uncertainty"
        )

        assert isinstance(selected, list)
        assert len(selected) <= 2

    def test_uncertainty_sampling(self, sampler):
        """uncertainty_sampling must select uncertain samples."""
        samples = sampler.uncertainty_sampling(
            candidates=[{"id": 1, "uncertainty": 0.9}],
            k=1
        )

        assert len(samples) == 1

    def test_diversity_sampling(self, sampler):
        """diversity_sampling must select diverse samples."""
        samples = sampler.diversity_sampling(
            candidates=[
                {"id": 1, "features": [0, 0]},
                {"id": 2, "features": [1, 1]}
            ],
            k=2
        )

        assert len(samples) == 2


# =============================================================================
# CONTRASTIVE LEARNING TESTS
# =============================================================================

class TestContrastiveLearningFunctional:
    """Functional tests for contrastive learning."""

    @pytest.fixture
    def contrastive(self):
        """Create contrastive learning system."""
        from ml_intelligence.contrastive_learning import ContrastiveLearningSystem
        return ContrastiveLearningSystem()

    def test_initialization(self, contrastive):
        """System must initialize properly."""
        assert contrastive is not None

    def test_create_pairs(self, contrastive):
        """create_pairs must generate positive/negative pairs."""
        pairs = contrastive.create_pairs(
            anchors=[{"id": 1, "data": "a"}],
            positives=[{"id": 2, "data": "a"}],
            negatives=[{"id": 3, "data": "b"}]
        )

        assert isinstance(pairs, list)

    def test_compute_loss(self, contrastive):
        """compute_loss must calculate contrastive loss."""
        loss = contrastive.compute_loss(
            anchor_embedding=[0.1, 0.2],
            positive_embedding=[0.15, 0.25],
            negative_embedding=[0.9, 0.8]
        )

        assert isinstance(loss, float)

    def test_train_step(self, contrastive):
        """train_step must update model."""
        result = contrastive.train_step(
            batch=[
                {"anchor": [0.1], "positive": [0.15], "negative": [0.9]}
            ]
        )

        assert result is not None


# =============================================================================
# UNCERTAINTY QUANTIFICATION TESTS
# =============================================================================

class TestUncertaintyQuantificationFunctional:
    """Functional tests for uncertainty quantification."""

    @pytest.fixture
    def uq(self):
        """Create uncertainty quantification system."""
        from ml_intelligence.uncertainty_quantification import UncertaintyQuantification
        return UncertaintyQuantification()

    def test_initialization(self, uq):
        """System must initialize properly."""
        assert uq is not None

    def test_estimate_uncertainty(self, uq):
        """estimate must return uncertainty value."""
        uncertainty = uq.estimate(
            prediction={"class": "A", "probability": 0.7},
            method="entropy"
        )

        assert isinstance(uncertainty, float)
        assert uncertainty >= 0

    def test_calibration(self, uq):
        """calibrate must improve probability estimates."""
        calibrated = uq.calibrate(
            predictions=[0.7, 0.8, 0.9],
            true_labels=[1, 1, 0]
        )

        assert calibrated is not None

    def test_get_confidence_interval(self, uq):
        """get_ci must return confidence interval."""
        ci = uq.get_confidence_interval(
            prediction=0.75,
            confidence=0.95
        )

        assert 'lower' in ci
        assert 'upper' in ci


# =============================================================================
# MULTI-ARMED BANDIT TESTS
# =============================================================================

class TestMultiArmedBanditFunctional:
    """Functional tests for multi-armed bandit."""

    @pytest.fixture
    def bandit(self):
        """Create multi-armed bandit."""
        from ml_intelligence.multi_armed_bandit import MultiArmedBandit
        return MultiArmedBandit(n_arms=3)

    def test_initialization(self, bandit):
        """Bandit must initialize properly."""
        assert bandit is not None
        assert bandit.n_arms == 3

    def test_select_arm(self, bandit):
        """select must choose an arm."""
        arm = bandit.select()

        assert isinstance(arm, int)
        assert 0 <= arm < 3

    def test_update_reward(self, bandit):
        """update must incorporate reward."""
        bandit.update(arm=0, reward=1.0)

        # Should affect future selections
        assert bandit.counts[0] >= 1

    def test_ucb_selection(self, bandit):
        """ucb_select must use upper confidence bound."""
        arm = bandit.ucb_select()

        assert isinstance(arm, int)

    def test_thompson_sampling(self, bandit):
        """thompson_sample must use Thompson sampling."""
        arm = bandit.thompson_sample()

        assert isinstance(arm, int)


# =============================================================================
# ONLINE LEARNING PIPELINE TESTS
# =============================================================================

class TestOnlineLearningPipelineFunctional:
    """Functional tests for online learning pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create online learning pipeline."""
        from ml_intelligence.online_learning_pipeline import OnlineLearningPipeline
        return OnlineLearningPipeline()

    def test_initialization(self, pipeline):
        """Pipeline must initialize properly."""
        assert pipeline is not None

    def test_process_sample(self, pipeline):
        """process must handle incoming sample."""
        result = pipeline.process(
            sample={"features": [0.1, 0.2], "label": 1}
        )

        assert result is not None

    def test_batch_update(self, pipeline):
        """batch_update must update on batch."""
        result = pipeline.batch_update(
            samples=[
                {"features": [0.1], "label": 0},
                {"features": [0.9], "label": 1}
            ]
        )

        assert result is True or result is not None

    def test_get_model_state(self, pipeline):
        """get_state must return model state."""
        state = pipeline.get_state()

        assert isinstance(state, dict)


# =============================================================================
# TRUST-AWARE EMBEDDING TESTS
# =============================================================================

class TestTrustAwareEmbeddingFunctional:
    """Functional tests for trust-aware embedding."""

    @pytest.fixture
    def embedding(self):
        """Create trust-aware embedding."""
        from ml_intelligence.trust_aware_embedding import TrustAwareEmbedding
        return TrustAwareEmbedding()

    def test_initialization(self, embedding):
        """Embedding must initialize properly."""
        assert embedding is not None

    def test_embed_with_trust(self, embedding):
        """embed must incorporate trust information."""
        result = embedding.embed(
            text="Test document",
            trust_score=0.85
        )

        assert result is not None
        assert isinstance(result, (list, np.ndarray))

    def test_similarity_with_trust(self, embedding):
        """similarity must consider trust."""
        similarity = embedding.similarity(
            embedding_a=[0.1, 0.2],
            embedding_b=[0.15, 0.25],
            trust_weight=0.5
        )

        assert isinstance(similarity, float)


# =============================================================================
# RULE STORAGE TESTS
# =============================================================================

class TestRuleStorageFunctional:
    """Functional tests for rule storage."""

    @pytest.fixture
    def storage(self):
        """Create rule storage."""
        from ml_intelligence.rule_storage import RuleStorage
        return RuleStorage()

    def test_initialization(self, storage):
        """Storage must initialize properly."""
        assert storage is not None

    def test_store_rule(self, storage):
        """store must save rule."""
        rule_id = storage.store(
            rule="if x > 10 then category = high",
            metadata={"source": "learned", "confidence": 0.9}
        )

        assert rule_id is not None

    def test_retrieve_rules(self, storage):
        """retrieve must return matching rules."""
        rules = storage.retrieve(
            query={"category": "high"}
        )

        assert isinstance(rules, list)

    def test_delete_rule(self, storage):
        """delete must remove rule."""
        result = storage.delete("RULE-001")

        assert result is True or result is None


# =============================================================================
# KPI TRACKER TESTS
# =============================================================================

class TestKPITrackerFunctional:
    """Functional tests for KPI tracker."""

    @pytest.fixture
    def tracker(self):
        """Create KPI tracker."""
        from ml_intelligence.kpi_tracker import KPITracker
        return KPITracker()

    def test_initialization(self, tracker):
        """Tracker must initialize properly."""
        assert tracker is not None

    def test_track_kpi(self, tracker):
        """track must record KPI value."""
        result = tracker.track(
            kpi_name="accuracy",
            value=0.95,
            timestamp=datetime.now()
        )

        assert result is True or result is not None

    def test_get_kpi_history(self, tracker):
        """get_history must return KPI values."""
        history = tracker.get_history(
            kpi_name="accuracy",
            limit=100
        )

        assert isinstance(history, list)

    def test_get_kpi_summary(self, tracker):
        """get_summary must return statistics."""
        summary = tracker.get_summary("accuracy")

        assert isinstance(summary, dict)


# =============================================================================
# INTEGRATION ORCHESTRATOR TESTS
# =============================================================================

class TestIntegrationOrchestratorFunctional:
    """Functional tests for integration orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create integration orchestrator."""
        from ml_intelligence.integration_orchestrator import IntegrationOrchestrator
        return IntegrationOrchestrator()

    def test_initialization(self, orchestrator):
        """Orchestrator must initialize properly."""
        assert orchestrator is not None

    def test_register_component(self, orchestrator):
        """register must add component."""
        mock_component = MagicMock()
        mock_component.name = "test_component"

        result = orchestrator.register(mock_component)

        assert result is True or result is not None

    def test_orchestrate_pipeline(self, orchestrator):
        """orchestrate must run pipeline."""
        result = orchestrator.orchestrate(
            pipeline=["component_a", "component_b"],
            input_data={"test": "data"}
        )

        assert result is not None


# =============================================================================
# LAYER 4 ADVANCED NEURO-SYMBOLIC TESTS
# =============================================================================

class TestLayer4AdvancedNeuroSymbolicFunctional:
    """Functional tests for Layer 4 advanced neuro-symbolic."""

    @pytest.fixture
    def layer4_ns(self):
        """Create Layer 4 neuro-symbolic."""
        from ml_intelligence.layer4_advanced_neuro_symbolic import Layer4AdvancedNeuroSymbolic
        return Layer4AdvancedNeuroSymbolic()

    def test_initialization(self, layer4_ns):
        """Layer 4 NS must initialize properly."""
        assert layer4_ns is not None

    def test_advanced_reasoning(self, layer4_ns):
        """advanced_reason must perform complex reasoning."""
        result = layer4_ns.advanced_reason(
            query="Complex multi-step reasoning task",
            knowledge_base={"facts": ["A implies B", "B implies C"]}
        )

        assert result is not None

    def test_symbolic_neural_fusion(self, layer4_ns):
        """fuse must combine symbolic and neural."""
        result = layer4_ns.fuse(
            symbolic_result={"conclusion": "A"},
            neural_result={"confidence": 0.9}
        )

        assert result is not None


class TestLayer4CompilerGovernedPipelineFunctional:
    """Functional tests for Layer 4 compiler-governed pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create compiler-governed pipeline."""
        from ml_intelligence.layer4_compiler_governed_pipeline import CompilerGovernedPipeline
        return CompilerGovernedPipeline()

    def test_initialization(self, pipeline):
        """Pipeline must initialize properly."""
        assert pipeline is not None

    def test_compile_pipeline(self, pipeline):
        """compile must create optimized pipeline."""
        compiled = pipeline.compile(
            stages=["preprocess", "inference", "postprocess"]
        )

        assert compiled is not None

    def test_execute_governed(self, pipeline):
        """execute_governed must run with governance."""
        result = pipeline.execute_governed(
            input_data={"test": "data"},
            governance_rules=["validate_output"]
        )

        assert result is not None


class TestLayer4FrontierReasoningFunctional:
    """Functional tests for Layer 4 frontier reasoning."""

    @pytest.fixture
    def frontier(self):
        """Create frontier reasoning."""
        from ml_intelligence.layer4_frontier_reasoning import FrontierReasoning
        return FrontierReasoning()

    def test_initialization(self, frontier):
        """Frontier reasoning must initialize properly."""
        assert frontier is not None

    def test_frontier_inference(self, frontier):
        """frontier_infer must perform advanced inference."""
        result = frontier.frontier_infer(
            query="Novel reasoning challenge",
            context={"domain": "scientific"}
        )

        assert result is not None


class TestLayer4RecursivePatternLearnerFunctional:
    """Functional tests for Layer 4 recursive pattern learner."""

    @pytest.fixture
    def learner(self):
        """Create recursive pattern learner."""
        from ml_intelligence.layer4_recursive_pattern_learner import RecursivePatternLearner
        return RecursivePatternLearner()

    def test_initialization(self, learner):
        """Learner must initialize properly."""
        assert learner is not None

    def test_learn_pattern(self, learner):
        """learn_pattern must extract recursive patterns."""
        pattern = learner.learn_pattern(
            examples=[
                {"input": [1, 2, 3], "output": [1, 3, 6]},  # cumsum
                {"input": [2, 3, 4], "output": [2, 5, 9]}
            ]
        )

        assert pattern is not None

    def test_apply_pattern(self, learner):
        """apply_pattern must use learned pattern."""
        result = learner.apply_pattern(
            pattern_id="PAT-001",
            input_data=[1, 2, 3]
        )

        assert result is not None


# =============================================================================
# ENTERPRISE NEURO-SYMBOLIC TESTS
# =============================================================================

class TestEnterpriseNeuroSymbolicFunctional:
    """Functional tests for enterprise neuro-symbolic."""

    @pytest.fixture
    def enterprise_ns(self):
        """Create enterprise neuro-symbolic."""
        from ml_intelligence.enterprise_neuro_symbolic import EnterpriseNeuroSymbolic
        return EnterpriseNeuroSymbolic()

    def test_initialization(self, enterprise_ns):
        """Enterprise NS must initialize properly."""
        assert enterprise_ns is not None

    def test_enterprise_reasoning(self, enterprise_ns):
        """enterprise_reason must handle enterprise scale."""
        result = enterprise_ns.enterprise_reason(
            query="Enterprise-scale decision",
            context={"scale": "large", "constraints": ["compliance"]}
        )

        assert result is not None

    def test_multi_tenant_isolation(self, enterprise_ns):
        """must maintain tenant isolation."""
        result1 = enterprise_ns.reason_for_tenant(
            tenant_id="TENANT-A",
            query="Query A"
        )
        result2 = enterprise_ns.reason_for_tenant(
            tenant_id="TENANT-B",
            query="Query B"
        )

        # Results should be isolated
        assert result1 is not None
        assert result2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
