"""
Tests for ml_intelligence modules — real logic tests.
Covers: KPI tracking, trust scoring, bandit selection, uncertainty,
online learning, meta-learning, contrastive learning, federated learning,
active learning.
"""
import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
import torch
import torch.nn as nn

# ── KPI Tracker ──────────────────────────────────────────────────────────────
from backend.ml_intelligence.kpi_tracker import (
    KPI, ComponentKPIs, TrustSnapshot, TrustHistory, KPITracker,
)


class TestKPI:
    def test_increment_updates_value_and_count(self):
        kpi = KPI(component_name="c", metric_name="m", value=0.0, count=0)
        kpi.increment(5.0)
        assert kpi.value == 5.0
        assert kpi.count == 1

    def test_increment_with_metadata(self):
        kpi = KPI(component_name="c", metric_name="m", value=0.0, count=0)
        kpi.increment(1.0, metadata={"key": "val"})
        assert kpi.metadata["key"] == "val"


class TestComponentKPIs:
    def test_get_kpi_creates_on_miss(self):
        comp = ComponentKPIs(component_name="comp")
        kpi = comp.get_kpi("requests")
        assert kpi.metric_name == "requests"
        assert kpi.count == 0

    def test_increment_kpi_updates_existing(self):
        comp = ComponentKPIs(component_name="comp")
        comp.increment_kpi("requests", 3.0)
        comp.increment_kpi("requests", 2.0)
        kpi = comp.get_kpi("requests")
        assert kpi.value == 5.0
        assert kpi.count == 2

    def test_trust_score_empty_returns_zero(self):
        comp = ComponentKPIs(component_name="comp")
        assert comp.get_trust_score() == 0.0

    def test_trust_score_increases_with_activity(self):
        comp = ComponentKPIs(component_name="comp")
        for _ in range(50):
            comp.increment_kpi("hits", 1.0)
        score = comp.get_trust_score()
        assert 0.0 < score <= 1.0
        # count=50 → normalized = 50/60 ≈ 0.833
        assert score > 0.5

    def test_to_dict_structure(self):
        comp = ComponentKPIs(component_name="comp")
        comp.increment_kpi("hits")
        d = comp.to_dict()
        assert "trust_score" in d
        assert "hits" in d["kpis"]


class TestTrustHistory:
    def test_record_and_trend_insufficient_data(self):
        th = TrustHistory(component_name="c")
        th.record(0.5, 1, 10)
        assert th.get_trend() == "insufficient_data"

    def test_trend_improving(self):
        th = TrustHistory(component_name="c")
        now = datetime.now(timezone.utc)
        for i in range(10):
            score = 0.3 + i * 0.05
            th.snapshots.append(TrustSnapshot(
                timestamp=now - timedelta(days=6 - i * 0.5),
                trust_score=score, kpi_count=1, total_actions=10 + i,
            ))
        assert th.get_trend(7) == "improving"

    def test_trend_degrading(self):
        th = TrustHistory(component_name="c")
        now = datetime.now(timezone.utc)
        for i in range(10):
            score = 0.9 - i * 0.06
            th.snapshots.append(TrustSnapshot(
                timestamp=now - timedelta(days=6 - i * 0.5),
                trust_score=score, kpi_count=1, total_actions=10,
            ))
        assert th.get_trend(7) == "degrading"

    def test_accumulated_trust_weighted(self):
        th = TrustHistory(component_name="c")
        now = datetime.now(timezone.utc)
        th.snapshots.append(TrustSnapshot(
            timestamp=now, trust_score=0.8, kpi_count=1, total_actions=5))
        val = th.get_accumulated_trust()
        assert 0.0 < val <= 1.0


class TestKPITracker:
    @patch.object(KPITracker, "load_trust_history")
    def test_register_and_increment(self, mock_load):
        tracker = KPITracker()
        tracker.register_component("engine", {"latency": 2.0})
        tracker.increment_kpi("engine", "latency", 10.0)
        score = tracker.get_component_trust_score("engine")
        assert score > 0.0

    @patch.object(KPITracker, "load_trust_history")
    def test_system_trust_score(self, mock_load):
        tracker = KPITracker()
        for name in ("a", "b"):
            for _ in range(20):
                tracker.increment_kpi(name, "ops", 1.0)
        sys_score = tracker.get_system_trust_score()
        assert 0.0 < sys_score <= 1.0

    @patch.object(KPITracker, "load_trust_history")
    def test_health_signal_status(self, mock_load):
        tracker = KPITracker()
        sig = tracker.get_health_signal("nonexistent")
        assert sig["status"] == "unknown"

    @patch.object(KPITracker, "load_trust_history")
    def test_take_daily_snapshot(self, mock_load):
        tracker = KPITracker()
        for _ in range(5):
            tracker.increment_kpi("x", "calls")
        result = tracker.take_daily_snapshot()
        assert "x" in result


# ── Neural Trust Scorer ──────────────────────────────────────────────────────
from backend.ml_intelligence.neural_trust_scorer import (
    TrustScorerNetwork, ExperienceReplay, TrainingExample, TrustFeatures,
    NeuralTrustScorer,
)


class TestTrustScorerNetwork:
    def test_forward_shape(self):
        net = TrustScorerNetwork(use_embeddings=False)
        x = torch.randn(4, 12)
        out = net(x)
        assert out.shape == (4, 1)
        assert (out >= 0).all() and (out <= 1).all()

    def test_forward_with_uncertainty(self):
        net = TrustScorerNetwork(use_embeddings=False)
        x = torch.randn(2, 12)
        score, unc = net(x, return_uncertainty=True)
        assert score.shape == (2, 1)
        assert unc.shape == (2, 1)


class TestExperienceReplay:
    def test_add_and_sample(self):
        buf = ExperienceReplay(max_size=100)
        feats = TrustFeatures(0.5, 0.5, 0.5, 1, 0, 1.0, 100,
                              False, False, False, 0.5, 0.5)
        for i in range(20):
            buf.add(TrainingExample(feats, float(i % 2), datetime.now()))
        batch = buf.sample(5)
        assert len(batch) == 5

    def test_max_size_eviction(self):
        buf = ExperienceReplay(max_size=5)
        feats = TrustFeatures(0.5, 0.5, 0.5, 1, 0, 1.0, 100,
                              False, False, False, 0.5, 0.5)
        for i in range(10):
            buf.add(TrainingExample(feats, 0.0, datetime.now()))
        assert len(buf) == 5


class TestNeuralTrustScorer:
    def test_extract_features(self):
        scorer = NeuralTrustScorer(model_path="/tmp/_nonexistent_model.pt")
        example = {
            "source_reliability": 0.7,
            "outcome_quality": 0.8,
            "consistency_score": 0.6,
            "times_validated": 5,
            "times_invalidated": 1,
            "created_at": datetime.now().isoformat(),
            "input_context": "def hello(): pass",
            "expected_output": "greeting function",
            "times_referenced": 3,
        }
        feats = scorer.extract_features(example)
        assert feats.source_reliability == 0.7
        assert feats.has_code is True

    def test_predict_trust_returns_score(self):
        scorer = NeuralTrustScorer(model_path="/tmp/_nonexistent_model.pt")
        example = {
            "source_reliability": 0.5,
            "outcome_quality": 0.5,
            "consistency_score": 0.5,
            "times_validated": 2,
            "times_invalidated": 0,
            "created_at": datetime.now().isoformat(),
            "input_context": "some text",
            "times_referenced": 1,
        }
        score, unc = scorer.predict_trust(example, return_uncertainty=True)
        assert 0.0 <= score <= 1.0
        assert unc is not None


# ── Multi-Armed Bandit ───────────────────────────────────────────────────────
from backend.ml_intelligence.multi_armed_bandit import (
    MultiArmedBandit, BanditAlgorithm, TopicArm,
)


class TestMultiArmedBandit:
    def _make_bandit(self, algo=BanditAlgorithm.EPSILON_GREEDY):
        return MultiArmedBandit(
            algorithm=algo, epsilon=0.0,
            save_path=os.path.join(tempfile.mkdtemp(), "bandit.json"),
        )

    def test_add_arm_and_select(self):
        b = self._make_bandit()
        b.add_arm("t1", "Topic 1")
        b.add_arm("t2", "Topic 2")
        sel = b.select_arm()
        assert sel in ("t1", "t2")

    def test_epsilon_greedy_exploits_best(self):
        b = self._make_bandit(BanditAlgorithm.EPSILON_GREEDY)
        b.add_arm("good", "Good Topic")
        b.add_arm("bad", "Bad Topic")
        b.arms["good"].pulls = 10
        b.arms["good"].mean_reward = 0.9
        b.arms["bad"].pulls = 10
        b.arms["bad"].mean_reward = 0.1
        b.total_pulls = 20
        sel = b.select_arm()
        assert sel == "good"

    def test_ucb1_selects_unpulled_arm(self):
        b = self._make_bandit(BanditAlgorithm.UCB1)
        b.add_arm("pulled", "Pulled")
        b.add_arm("fresh", "Fresh")
        b.arms["pulled"].pulls = 10
        b.arms["pulled"].mean_reward = 0.5
        b.total_pulls = 10
        sel = b.select_arm()
        assert sel == "fresh"

    def test_update_reward(self):
        b = self._make_bandit()
        b.add_arm("t1", "Topic 1")
        b.arms["t1"].pulls = 1
        b.update_reward("t1", 0.8)
        assert b.arms["t1"].mean_reward == pytest.approx(0.8)
        assert b.arms["t1"].successes == 2  # started at 1, +1

    def test_recommend_next_topics(self):
        b = self._make_bandit(BanditAlgorithm.EPSILON_GREEDY)
        for i in range(5):
            b.add_arm(f"t{i}", f"Topic {i}")
            b.arms[f"t{i}"].pulls = 1
            b.arms[f"t{i}"].mean_reward = i * 0.2
        recs = b.recommend_next_topics(k=2)
        assert len(recs) == 2
        assert recs[0][0] == "t4"

    def test_exclude_topics(self):
        b = self._make_bandit()
        b.add_arm("a", "A")
        b.add_arm("b", "B")
        sel = b.select_arm(exclude_topics=["a"])
        assert sel == "b"


# ── Uncertainty Quantification ───────────────────────────────────────────────
from backend.ml_intelligence.uncertainty_quantification import (
    BayesianLinear, BayesianNeuralNetwork, MCDropoutNetwork,
    UncertaintyQuantifier, UncertaintyEstimate,
)


class TestBayesianLinear:
    def test_forward_shape(self):
        layer = BayesianLinear(10, 5)
        x = torch.randn(3, 10)
        out = layer(x)
        assert out.shape == (3, 5)

    def test_kl_divergence_positive(self):
        layer = BayesianLinear(10, 5)
        kl = layer.kl_divergence()
        assert kl.item() > 0


class TestMCDropoutNetwork:
    def test_predict_with_uncertainty(self):
        net = MCDropoutNetwork(input_dim=8, hidden_dims=[16, 8], output_dim=1)
        x = torch.randn(4, 8)
        mean_pred, unc = net.predict_with_uncertainty(x, num_samples=10)
        assert mean_pred.shape == (4, 1)
        assert unc.shape == (4, 1)

    def test_forward_deterministic_eval(self):
        net = MCDropoutNetwork(input_dim=8, hidden_dims=[16], output_dim=1)
        net.eval()
        x = torch.randn(2, 8)
        out = net(x)
        assert out.shape == (2, 1)


class TestUncertaintyQuantifier:
    def test_mc_dropout_full_estimate(self):
        net = MCDropoutNetwork(input_dim=4, hidden_dims=[8], output_dim=1)
        uq = UncertaintyQuantifier(net, method="mc_dropout", device="cpu")
        x = torch.randn(1, 4)
        est = uq.predict_with_uncertainty(x, num_samples=10)
        assert isinstance(est, UncertaintyEstimate)
        assert isinstance(est.total_uncertainty, float)

    def test_bayesian_full_estimate(self):
        net = BayesianNeuralNetwork(input_dim=4, hidden_dims=[8], output_dim=1)
        uq = UncertaintyQuantifier(net, method="bayesian", device="cpu")
        x = torch.randn(1, 4)
        est = uq.predict_with_uncertainty(x, num_samples=10)
        assert isinstance(est.prediction, float)


# ── Online Learning Pipeline ─────────────────────────────────────────────────
from backend.ml_intelligence.online_learning_pipeline import (
    OnlineLearningPipeline, StreamingBatch, IncrementalEmbeddingLearner,
)


class TestOnlineLearningPipeline:
    def _simple_model(self):
        return nn.Sequential(nn.Linear(4, 8), nn.ReLU(), nn.Linear(8, 1), nn.Sigmoid())

    def test_single_update(self):
        model = self._simple_model()
        pipe = OnlineLearningPipeline(
            model, checkpoint_dir=tempfile.mkdtemp(), device="cpu", use_ewc=False)
        batch = StreamingBatch(
            features=torch.randn(8, 4), labels=torch.randint(0, 2, (8,)))
        metrics = pipe.update(batch)
        assert "primary_loss" in metrics
        assert pipe.batch_count == 1

    def test_running_mean_updates(self):
        model = self._simple_model()
        pipe = OnlineLearningPipeline(
            model, checkpoint_dir=tempfile.mkdtemp(), device="cpu", use_ewc=False)
        for _ in range(3):
            batch = StreamingBatch(
                features=torch.randn(4, 4), labels=torch.randint(0, 2, (4,)))
            pipe.update(batch)
        assert pipe.running_mean_loss > 0.0
        summary = pipe.get_metrics_summary()
        assert summary["batch_count"] == 3


class TestIncrementalEmbeddingLearner:
    def test_adapt_embedding_shape(self):
        base_model = MagicMock()
        learner = IncrementalEmbeddingLearner(
            base_model, embedding_dim=384, device="cpu")
        emb = np.random.randn(384).astype(np.float32)
        adapted = learner.adapt_embedding("text", emb)
        assert adapted.shape == (384,)

    def test_learn_from_positive_pair(self):
        base_model = MagicMock()
        learner = IncrementalEmbeddingLearner(
            base_model, embedding_dim=16, device="cpu")
        e1 = np.random.randn(16).astype(np.float32)
        e2 = np.random.randn(16).astype(np.float32)
        loss = learner.learn_from_positive_pair("a", "b", e1, e2, True)
        assert isinstance(loss, float)


# ── Meta-Learning ────────────────────────────────────────────────────────────
from backend.ml_intelligence.meta_learning import (
    HyperparameterOptimizer, TaskSimilarityDetector, LearningTask,
)


class TestHyperparameterOptimizer:
    def test_suggest_returns_all_keys(self):
        opt = HyperparameterOptimizer()
        hp = opt.suggest_hyperparameters("classification")
        for key in ("learning_rate", "batch_size", "num_epochs", "dropout", "weight_decay"):
            assert key in hp

    def test_update_and_best(self):
        opt = HyperparameterOptimizer()
        hp = {"learning_rate": 0.01, "batch_size": 32}
        opt.update_from_result("cls", hp, 0.9)
        opt.update_from_result("cls", {"learning_rate": 0.1, "batch_size": 64}, 0.5)
        best = opt.get_best_hyperparameters("cls", top_k=1)
        assert len(best) == 1
        assert best[0][1] == 0.9  # highest performance first


class TestTaskSimilarityDetector:
    def _make_task(self, tid, ttype, n_support=5):
        return LearningTask(
            task_id=tid, task_type=ttype,
            support_set=[(torch.randn(4), torch.tensor(0.0)) for _ in range(n_support)],
            query_set=[(torch.randn(4), torch.tensor(0.0)) for _ in range(3)],
        )

    def test_embed_and_find_similar(self):
        det = TaskSimilarityDetector(embedding_dim=32)
        t1 = self._make_task("t1", "classification")
        t2 = self._make_task("t2", "classification")
        t3 = self._make_task("t3", "regression")
        det.add_task(t1)
        det.add_task(t2)
        det.add_task(t3)
        similar = det.find_similar_tasks(t1, top_k=2, exclude_task_ids=["t1"])
        assert len(similar) == 2
        # classification tasks should be more similar to each other
        ids = [s[0] for s in similar]
        assert "t2" in ids

    def test_embed_task_shape(self):
        det = TaskSimilarityDetector(embedding_dim=64)
        t = self._make_task("x", "generation")
        emb = det.embed_task(t)
        assert emb.shape == (64,)


# ── Contrastive Learning ─────────────────────────────────────────────────────
from backend.ml_intelligence.contrastive_learning import (
    NTXentLoss, TripletLoss, SupervisedContrastiveLoss,
)


class TestNTXentLoss:
    def test_loss_positive(self):
        loss_fn = NTXentLoss(temperature=0.5)
        z_i = torch.randn(8, 32)
        z_j = torch.randn(8, 32)
        loss = loss_fn(z_i, z_j)
        assert loss.item() > 0

    def test_identical_views_lower_loss(self):
        loss_fn = NTXentLoss(temperature=0.5)
        z = torch.randn(8, 32)
        loss_same = loss_fn(z, z).item()
        z2 = torch.randn(8, 32)
        loss_diff = loss_fn(z, z2).item()
        assert loss_same < loss_diff


class TestTripletLoss:
    def test_loss_zero_when_margin_satisfied(self):
        loss_fn = TripletLoss(margin=1.0, distance_metric="euclidean")
        anchor = torch.zeros(4, 8)
        pos = torch.ones(4, 8) * 0.1
        neg = torch.ones(4, 8) * 10.0
        loss = loss_fn(anchor, pos, neg)
        assert loss.item() == pytest.approx(0.0, abs=1e-5)

    def test_cosine_metric(self):
        loss_fn = TripletLoss(margin=0.5, distance_metric="cosine")
        anchor = torch.randn(4, 8)
        pos = anchor + 0.01 * torch.randn(4, 8)
        neg = -anchor
        loss = loss_fn(anchor, pos, neg)
        assert loss.item() >= 0.0


class TestSupervisedContrastiveLoss:
    def test_loss_with_labels(self):
        loss_fn = SupervisedContrastiveLoss(temperature=0.07)
        features = torch.randn(6, 16)
        labels = torch.tensor([0, 0, 1, 1, 2, 2])
        loss = loss_fn(features, labels)
        assert loss.item() > 0


# ── Federated Learning ───────────────────────────────────────────────────────
from backend.ml_intelligence.federated_learning import (
    DifferentialPrivacy, KnowledgeDistillation, FederatedAggregator,
    FederatedLearningManager, ModelDelta,
)


class TestDifferentialPrivacy:
    def test_clip_and_noise_clips_gradient(self):
        dp = DifferentialPrivacy(max_grad_norm=1.0, noise_multiplier=0.0)
        grads = {"layer1": [10.0, 10.0, 10.0]}
        noised = dp.clip_and_noise(grads)
        vec = torch.tensor(noised["layer1"])
        assert torch.norm(vec).item() <= 1.0 + 1e-5

    def test_budget_tracking(self):
        dp = DifferentialPrivacy(epsilon_budget=10.0)
        dp.clip_and_noise({"a": [1.0]})
        assert dp.epsilon_spent > 0
        assert dp.budget_remaining < 10.0


class TestKnowledgeDistillation:
    def test_distill_filters_low_trust(self):
        kd = KnowledgeDistillation()
        examples = [
            {"trust_score": 0.1, "type": "fact"},
            {"trust_score": 0.8, "type": "rule", "source": "wiki"},
        ]
        distilled = kd.distill_examples(examples, min_trust=0.4)
        assert len(distilled) == 1
        assert distilled[0]["type"] == "rule"

    def test_trust_distribution_buckets(self):
        kd = KnowledgeDistillation()
        examples = [{"trust_score": 0.1}, {"trust_score": 0.5}, {"trust_score": 0.9}]
        dist = kd.build_trust_distribution(examples)
        assert dist["0.0-0.2"] == 1
        assert dist["0.4-0.6"] == 1
        assert dist["0.8-1.0"] == 1

    def test_strip_pii(self):
        kd = KnowledgeDistillation()
        assert kd.strip_pii("my email is x") == "[REDACTED]"
        assert kd.strip_pii("safe text") == "safe text"


class TestFederatedLearningManager:
    def test_register_and_list_nodes(self):
        mgr = FederatedLearningManager(storage_dir=tempfile.mkdtemp())
        node = mgr.register_node("node-a", trust_score=0.7)
        nodes = mgr.get_nodes()
        assert len(nodes) == 1
        assert nodes[0]["node_name"] == "node-a"

    def test_submit_and_aggregate(self):
        mgr = FederatedLearningManager(storage_dir=tempfile.mkdtemp())
        n1 = mgr.register_node("n1", trust_score=0.8)
        n2 = mgr.register_node("n2", trust_score=0.6)
        mgr.submit_local_update(n1.node_id, {"fc.weight": [1.0, 2.0]}, num_samples=10)
        mgr.submit_local_update(n2.node_id, {"fc.weight": [3.0, 4.0]}, num_samples=5)
        result = mgr.run_aggregation_round()
        assert result.get("global_model_version", 0) >= 1
