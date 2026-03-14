"""Tests for backend/ml_intelligence/multi_armed_bandit.py"""
import importlib
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "multi_armed_bandit",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "ml_intelligence" / "multi_armed_bandit.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

MultiArmedBandit = _mod.MultiArmedBandit
BanditAlgorithm = _mod.BanditAlgorithm
TopicArm = _mod.TopicArm
BanditContext = _mod.BanditContext


@pytest.fixture
def bandit(tmp_path):
    b = MultiArmedBandit(
        algorithm=BanditAlgorithm.UCB1,
        save_path=str(tmp_path / "test_bandit.json"),
    )
    b.arms.clear()
    b.total_pulls = 0
    b.exp3_weights.clear()
    return b


# ── TopicArm defaults ───────────────────────────────────────

class TestTopicArmDefaults:
    def test_default_values(self):
        arm = TopicArm(topic_id="t1", topic_name="Topic 1")
        assert arm.pulls == 0
        assert arm.total_reward == 0.0
        assert arm.successes == 1
        assert arm.failures == 1


# ── MultiArmedBandit ────────────────────────────────────────

class TestAddArm:
    def test_add_arm(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        assert "t1" in bandit.arms
        assert bandit.arms["t1"].topic_name == "Topic 1"

    def test_add_arm_duplicate_ignored(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        bandit.add_arm("t1", "OVERWRITTEN")
        assert bandit.arms["t1"].topic_name == "Topic 1"


class TestSelectArm:
    def test_no_arms_raises(self, bandit):
        with pytest.raises(ValueError, match="No arms available"):
            bandit.select_arm()

    def test_all_excluded_raises(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        with pytest.raises(ValueError, match="No available arms after exclusions"):
            bandit.select_arm(exclude_topics=["t1"])

    def test_ucb1_unpulled_selected_first(self, bandit):
        bandit.add_arm("pulled", "Pulled")
        bandit.arms["pulled"].pulls = 5
        bandit.arms["pulled"].mean_reward = 0.9
        bandit.total_pulls = 5
        bandit.add_arm("unpulled", "Unpulled")
        selected = bandit.select_arm()
        assert selected == "unpulled"

    def test_select_increments_pulls(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        assert bandit.total_pulls == 0
        assert bandit.arms["t1"].pulls == 0
        bandit.select_arm()
        assert bandit.total_pulls == 1
        assert bandit.arms["t1"].pulls == 1


class TestUpdateReward:
    def test_mean_reward(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        bandit.select_arm()  # pulls = 1
        bandit.update_reward("t1", 0.8)
        assert bandit.arms["t1"].mean_reward == pytest.approx(0.8)

    def test_success_incremented(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        bandit.select_arm()
        initial = bandit.arms["t1"].successes
        bandit.update_reward("t1", 0.5)
        assert bandit.arms["t1"].successes == initial + 1

    def test_failure_incremented(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        bandit.select_arm()
        initial = bandit.arms["t1"].failures
        bandit.update_reward("t1", 0.49)
        assert bandit.arms["t1"].failures == initial + 1


class TestStats:
    def test_get_arm_stats_structure(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        stats = bandit.get_arm_stats("t1")
        assert "topic_id" in stats
        assert "topic_name" in stats
        assert "pulls" in stats
        assert "mean_reward" in stats
        assert "total_reward" in stats
        assert "success_rate" in stats
        assert "last_pulled" in stats

    def test_get_all_stats_structure(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        stats = bandit.get_all_stats()
        assert "total_pulls" in stats
        assert "num_arms" in stats
        assert "algorithm" in stats
        assert "arms" in stats
        assert "top_performers" in stats


class TestRecommendNextTopics:
    def test_returns_top_k(self, bandit):
        for i in range(5):
            bandit.add_arm(f"t{i}", f"Topic {i}")
        result = bandit.recommend_next_topics(k=3)
        assert len(result) == 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in result)

    def test_excludes_topics(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        bandit.add_arm("t2", "Topic 2")
        result = bandit.recommend_next_topics(exclude_topics=["t1"])
        topic_ids = [r[0] for r in result]
        assert "t1" not in topic_ids

    def test_empty_available_returns_empty(self, bandit):
        bandit.add_arm("t1", "Topic 1")
        result = bandit.recommend_next_topics(exclude_topics=["t1"])
        assert result == []


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        save_path = str(tmp_path / "roundtrip_bandit.json")
        b1 = MultiArmedBandit(
            algorithm=BanditAlgorithm.UCB1,
            save_path=save_path,
        )
        b1.arms.clear()
        b1.total_pulls = 0
        b1.exp3_weights.clear()

        b1.add_arm("t1", "Topic 1")
        b1.add_arm("t2", "Topic 2")
        b1.select_arm()
        b1.save_state()

        b2 = MultiArmedBandit(
            algorithm=BanditAlgorithm.UCB1,
            save_path=save_path,
        )
        assert "t1" in b2.arms
        assert "t2" in b2.arms
        assert b2.total_pulls == 1


class TestAlgorithms:
    def test_thompson_sampling_selects(self, tmp_path):
        b = MultiArmedBandit(
            algorithm=BanditAlgorithm.THOMPSON_SAMPLING,
            save_path=str(tmp_path / "ts_bandit.json"),
        )
        b.arms.clear()
        b.total_pulls = 0
        b.exp3_weights.clear()

        b.add_arm("t1", "Topic 1")
        b.add_arm("t2", "Topic 2")
        selected = b.select_arm()
        assert selected in ("t1", "t2")

    def test_epsilon_greedy_exploits_when_zero(self, tmp_path):
        b = MultiArmedBandit(
            algorithm=BanditAlgorithm.EPSILON_GREEDY,
            epsilon=0.0,
            save_path=str(tmp_path / "eg_bandit.json"),
        )
        b.arms.clear()
        b.total_pulls = 0
        b.exp3_weights.clear()

        b.add_arm("bad", "Bad Topic")
        b.add_arm("good", "Good Topic")
        b.arms["bad"].mean_reward = 0.1
        b.arms["bad"].pulls = 10
        b.arms["good"].mean_reward = 0.9
        b.arms["good"].pulls = 10
        b.total_pulls = 20

        selected = b.select_arm()
        assert selected == "good"
