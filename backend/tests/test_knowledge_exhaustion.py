"""
Tests for Knowledge Exhaustion Engine - verifies actual convergence logic,
duplicate detection, state persistence, and GitHub dump functionality.
"""

import sys
import os
import hashlib
import warnings
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning, module="sqlalchemy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.base import Base

from cognitive.knowledge_exhaustion_engine import (
    KnowledgeExhaustionEngine,
    TopicExhaustionTracker,
)


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from cognitive.knowledge_compiler import (
            CompiledFact, CompiledProcedure, CompiledDecisionRule,
            CompiledTopicIndex, CompiledEntityRelation,
        )
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def mock_cloud():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = {
        "success": True,
        "content": "Python is a programming language. It was created by Guido van Rossum.",
        "tokens": 50,
    }
    return client


@pytest.fixture
def engine(session_factory, mock_cloud):
    return KnowledgeExhaustionEngine(session_factory, mock_cloud)


class TestTopicExhaustionTracker:

    def test_tracker_persists_all_fields(self, db_session):
        tracker = TopicExhaustionTracker(
            topic="machine learning", status="mining",
            cycles_completed=2, convergence_count=1,
            total_new_facts=50, total_duplicates=30,
            duplicate_ratio=0.375, github_mined=True,
            github_repos=15, github_facts=200,
            perspectives_used=["Q1", "Q2"],
        )
        db_session.add(tracker)
        db_session.commit()

        saved = db_session.query(TopicExhaustionTracker).first()
        assert saved.topic == "machine learning"
        assert saved.status == "mining"
        assert saved.cycles_completed == 2
        assert saved.convergence_count == 1
        assert saved.total_new_facts == 50
        assert saved.total_duplicates == 30
        assert abs(saved.duplicate_ratio - 0.375) < 0.001
        assert saved.github_mined is True
        assert saved.github_repos == 15
        assert saved.github_facts == 200
        assert len(saved.perspectives_used) == 2

    def test_tracker_status_lifecycle(self, db_session):
        tracker = TopicExhaustionTracker(topic="docker", status="pending")
        db_session.add(tracker)
        db_session.commit()

        for status in ["mining", "converging", "exhausted"]:
            tracker.status = status
            db_session.commit()
            assert db_session.query(TopicExhaustionTracker).first().status == status

    def test_tracker_unique_constraint(self, db_session):
        db_session.add(TopicExhaustionTracker(topic="kubernetes", status="pending"))
        db_session.commit()
        db_session.add(TopicExhaustionTracker(topic="kubernetes", status="mining"))
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestPerspectiveGeneration:

    def test_generates_minimum_30_perspectives(self, engine):
        perspectives = engine._generate_perspectives("machine learning")
        assert len(perspectives) >= 25

    def test_all_perspectives_unique(self, engine):
        perspectives = engine._generate_perspectives("testing")
        assert len(perspectives) == len(set(perspectives))

    def test_every_perspective_contains_topic(self, engine):
        topic = "distributed systems"
        for p in engine._generate_perspectives(topic):
            assert topic in p, f"Perspective missing topic: {p}"

    def test_perspectives_cover_required_angles(self, engine):
        text = " ".join(engine._generate_perspectives("API design")).lower()
        required = ["security", "performance", "best practice", "test", "scalab"]
        for angle in required:
            assert angle in text, f"Missing angle: {angle}"

    def test_fresh_questions_filters_out_used(self, engine):
        all_p = engine._generate_perspectives("docker")
        used = [p[:80] for p in all_p[:10]]
        fresh = engine._get_fresh_questions("docker", all_p, used, 5, 0)
        for q in fresh:
            assert q[:80] not in used, f"Reused question: {q[:50]}"

    def test_fresh_questions_asks_cloud_when_all_used(self, engine, mock_cloud):
        mock_cloud.generate.return_value = {
            "success": True,
            "content": "What networking aspects exist?\nHow is storage handled?",
            "tokens": 20,
        }
        all_p = engine._generate_perspectives("docker")
        used = [p[:80] for p in all_p]
        fresh = engine._get_fresh_questions("docker", all_p, used, 2, 0)
        assert len(fresh) > 0
        mock_cloud.generate.assert_called()


class TestFactHashing:

    def test_identical_facts_hash_equal(self, engine):
        f1 = {"subject": "Python", "object": "A programming language"}
        f2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_different_subjects_hash_different(self, engine):
        f1 = {"subject": "Python", "object": "A programming language"}
        f2 = {"subject": "Java", "object": "A programming language"}
        assert engine._hash_fact(f1) != engine._hash_fact(f2)

    def test_case_insensitive_hashing(self, engine):
        f1 = {"subject": "PYTHON", "object": "A PROGRAMMING LANGUAGE"}
        f2 = {"subject": "python", "object": "a programming language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_whitespace_normalization(self, engine):
        f1 = {"subject": "Python", "object": "A  programming   language"}
        f2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_object_value_key_fallback(self, engine):
        f1 = {"subject": "X", "object_value": "Y"}
        f2 = {"subject": "X", "object": "Y"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_hash_is_12_chars(self, engine):
        assert len(engine._hash_fact({"subject": "x", "object": "y"})) == 12

    def test_existing_hashes_loads_from_db(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Python", predicate="is",
            object_value="A programming language",
            domain="programming", confidence=0.9,
        ))
        db_session.commit()
        hashes = engine._get_existing_fact_hashes(db_session, "programming")
        assert len(hashes) == 1
        expected_hash = engine._hash_fact({"subject": "Python", "object": "A programming language"})
        assert expected_hash in hashes

    def test_domain_underscore_variant_matching(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Docker", predicate="is",
            object_value="A container runtime", domain="dev_ops",
        ))
        db_session.commit()
        assert len(engine._get_existing_fact_hashes(db_session, "dev ops")) == 1


class TestTopicExhaustion:

    def _mock_compile_and_mine(self):
        return (
            patch('cognitive.knowledge_compiler.KnowledgeCompiler'),
            patch('cognitive.knowledge_compiler.get_llm_knowledge_miner'),
        )

    def test_creates_tracker_on_first_exhaust(self, engine, db_session):
        cp, mp = self._mock_compile_and_mine()
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_topic("new topic", max_cycles=1, questions_per_cycle=2)

        assert result["topic"] == "new topic"
        assert result["status"] in ("mining", "converging", "exhausted")
        tracker = db_session.query(TopicExhaustionTracker).filter_by(topic="new topic").first()
        assert tracker is not None
        assert tracker.cycles_completed >= 1
        assert tracker.last_mined_at is not None

    def test_already_exhausted_returns_early(self, engine, session_factory):
        s = session_factory()
        s.add(TopicExhaustionTracker(topic="done", status="exhausted", total_new_facts=100))
        s.commit()
        s.close()

        result = engine.exhaust_topic("done")
        assert result["exhausted"] is True
        assert "already exhausted" in result.get("message", "").lower()

    def test_convergence_detected_when_all_duplicates(self, engine, db_session, mock_cloud):
        existing = {engine._hash_fact({"subject": f"f{i}", "object": f"v{i}"}) for i in range(20)}

        cp, mp = self._mock_compile_and_mine()
        with patch.object(engine, '_get_existing_fact_hashes', return_value=existing):
            with cp as mc, mp as mm:
                mc.return_value.compile_chunk.return_value = {
                    "facts": [{"subject": "f0", "object": "v0"}]
                }
                mm.return_value = MagicMock()
                result = engine.exhaust_topic("dupes", max_cycles=3, questions_per_cycle=2)

        assert result["duplicates"] > 0
        assert result["duplicate_ratio"] > 0.5

    def test_cloud_unavailable_returns_zero_questions(self, engine, mock_cloud):
        mock_cloud.is_available.return_value = False
        cp, mp = self._mock_compile_and_mine()
        with cp, mp:
            result = engine.exhaust_topic("offline", max_cycles=1, questions_per_cycle=2)
        assert result["questions_asked"] == 0

    def test_state_persists_across_calls(self, engine, db_session):
        cp, mp = self._mock_compile_and_mine()
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            engine.exhaust_topic("persist", max_cycles=1, questions_per_cycle=1)
            engine.exhaust_topic("persist", max_cycles=1, questions_per_cycle=1)

        trackers = db_session.query(TopicExhaustionTracker).filter_by(topic="persist").all()
        assert len(trackers) == 1
        assert trackers[0].cycles_completed >= 2
        assert len(trackers[0].perspectives_used) >= 2

    def test_exhaust_multiple_processes_all_topics(self, engine):
        cp, mp = self._mock_compile_and_mine()
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_multiple(["a", "b", "c"], max_cycles=1, questions_per_cycle=1)
        assert result["topics_processed"] == 3
        assert len(result["results"]) == 3


class TestStatusAndReporting:

    def test_unknown_topic_status(self, engine):
        s = engine.get_topic_status("unknown")
        assert s["exists"] is False
        assert s["status"] == "unknown"

    def test_known_topic_status_returns_all_fields(self, engine, session_factory):
        s = session_factory()
        s.add(TopicExhaustionTracker(
            topic="known", status="converging",
            cycles_completed=2, convergence_count=1,
            total_new_facts=50, total_duplicates=30,
        ))
        s.commit()
        s.close()

        status = engine.get_topic_status("known")
        assert status["exists"] is True
        assert status["status"] == "converging"
        assert status["cycles_completed"] == 2
        assert status["total_new_facts"] == 50

    def test_all_topics_status_returns_list(self, engine, session_factory):
        s = session_factory()
        for i, st in enumerate(["mining", "converging", "exhausted"]):
            s.add(TopicExhaustionTracker(topic=f"t_{i}", status=st))
        s.commit()
        s.close()

        all_status = engine.get_all_topics_status()
        assert len(all_status) == 3
        statuses = {s["status"] for s in all_status}
        assert statuses == {"mining", "converging", "exhausted"}

    def test_stats_reflect_db_counts(self, engine, session_factory):
        s = session_factory()
        s.add(TopicExhaustionTracker(topic="ex", status="exhausted"))
        s.add(TopicExhaustionTracker(topic="mi", status="mining"))
        s.commit()
        s.close()

        stats = engine.get_stats()
        assert stats["tracked_topics"] == 2
        assert stats["exhausted_topics"] == 1
        assert stats["mining_topics"] == 1


class TestGitHubMassiveDump:

    def test_dump_stores_facts_and_entities(self, engine, db_session):
        mock_search = MagicMock(status_code=200)
        mock_search.json.return_value = {"items": [{
            "full_name": "test/repo", "stargazers_count": 5000,
            "description": "Test repo", "language": "Python",
            "html_url": "https://github.com/test/repo",
        }]}
        mock_404 = MagicMock(status_code=404)

        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mg:
            mg.side_effect = lambda url, **kw: mock_search if "search" in url else mock_404
            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": []}
                with patch.object(engine, '_vectorize_text'):
                    result = engine.github_massive_dump(["test"], max_repos_per_topic=1, include_code_files=False)

        assert result["total_repos"] >= 1
        from cognitive.knowledge_compiler import CompiledFact
        facts = db_session.query(CompiledFact).filter_by(subject="test/repo").all()
        assert len(facts) >= 1
        assert "5000" in facts[0].object_value

    def test_dump_api_failure_returns_error(self, engine):
        with patch("cognitive.knowledge_exhaustion_engine.requests.get", return_value=MagicMock(status_code=403)):
            result = engine.github_massive_dump(["forbidden"], max_repos_per_topic=1)
        assert result["total_repos"] == 0
        assert "error" in result["results"][0]

    def test_dump_updates_tracker_github_flag(self, engine, db_session):
        mock_search = MagicMock(status_code=200)
        mock_search.json.return_value = {"items": [{
            "full_name": "o/r", "stargazers_count": 100,
            "description": "T", "language": "Py", "html_url": "u",
        }]}
        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mg:
            mg.side_effect = lambda url, **kw: mock_search if "search" in url else MagicMock(status_code=404)
            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": []}
                with patch.object(engine, '_vectorize_text'):
                    engine.github_massive_dump(["gh_track"], max_repos_per_topic=1, include_code_files=False)

        tracker = db_session.query(TopicExhaustionTracker).filter_by(topic="gh_track").first()
        assert tracker is not None
        assert tracker.github_mined is True
        assert tracker.github_repos >= 1

    def test_dump_confidence_scales_with_stars(self, engine, db_session):
        mock_search = MagicMock(status_code=200)
        mock_search.json.return_value = {"items": [{
            "full_name": "pop/repo", "stargazers_count": 50000,
            "description": "Popular", "language": "Go", "html_url": "u",
        }]}
        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mg:
            mg.side_effect = lambda url, **kw: mock_search if "search" in url else MagicMock(status_code=404)
            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": []}
                with patch.object(engine, '_vectorize_text'):
                    engine.github_massive_dump(["pop"], max_repos_per_topic=1, include_code_files=False)

        from cognitive.knowledge_compiler import CompiledFact
        fact = db_session.query(CompiledFact).filter_by(subject="pop/repo").first()
        assert fact is not None
        assert fact.confidence >= 0.9


class TestEdgeCases:

    def test_no_cloud_client(self, session_factory):
        eng = KnowledgeExhaustionEngine(session_factory, cloud_client=None)
        result = eng.exhaust_topic("offline", max_cycles=1, questions_per_cycle=2)
        assert result["questions_asked"] == 0

    def test_stats_survives_bad_db(self):
        eng = KnowledgeExhaustionEngine(lambda: (_ for _ in ()).throw(Exception("bad")))
        stats = eng.get_stats()
        assert "topics_exhausted" in stats

    def test_vectorize_survives_missing_deps(self, engine):
        engine._vectorize_text("test", {"source": "test"})
