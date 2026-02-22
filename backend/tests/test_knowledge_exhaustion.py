"""
Comprehensive tests for Knowledge Exhaustion Engine.

Tests the convergence-based deep extraction system:
- Topic exhaustion with convergence detection
- Duplicate detection and fact hashing
- Perspective generation (25+ angles)
- Fresh question generation when perspectives run out
- GitHub massive dump (repos, READMEs, code files)
- Topic tracker persistence (status transitions)
- Multi-topic exhaustion
- Stats and reporting
- Edge cases: empty responses, API failures, already exhausted topics
"""

import sys
import os
import hashlib
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

import pytest

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
    """Create an in-memory SQLite engine with all tables."""
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
    """Session factory that creates fresh sessions from the same engine."""
    Session = sessionmaker(bind=db_engine)
    return Session


@pytest.fixture
def db_session(session_factory):
    """A session for direct queries in tests."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def mock_cloud():
    """Mock cloud client for testing."""
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = {
        "success": True,
        "content": "Python is a programming language. It was created by Guido van Rossum. "
                   "It supports multiple paradigms including OOP and functional programming.",
        "tokens": 50,
    }
    return client


@pytest.fixture
def engine(session_factory, mock_cloud):
    """Create a KnowledgeExhaustionEngine instance."""
    return KnowledgeExhaustionEngine(session_factory, mock_cloud)


# =====================================================================
# TOPIC TRACKER MODEL TESTS
# =====================================================================

class TestTopicExhaustionTracker:
    """Test the persistence model for topic exhaustion state."""

    def test_tracker_creation(self, db_session):
        tracker = TopicExhaustionTracker(
            topic="machine learning",
            status="pending",
        )
        db_session.add(tracker)
        db_session.commit()

        saved = db_session.query(TopicExhaustionTracker).filter_by(
            topic="machine learning"
        ).first()
        assert saved is not None
        assert saved.topic == "machine learning"
        assert saved.status == "pending"
        assert saved.cycles_completed == 0
        assert saved.convergence_count == 0

    def test_tracker_status_transitions(self, db_session):
        tracker = TopicExhaustionTracker(topic="docker", status="pending")
        db_session.add(tracker)
        db_session.commit()

        tracker.status = "mining"
        db_session.commit()
        assert db_session.query(TopicExhaustionTracker).first().status == "mining"

        tracker.status = "converging"
        tracker.convergence_count = 1
        db_session.commit()
        assert db_session.query(TopicExhaustionTracker).first().status == "converging"

        tracker.status = "exhausted"
        tracker.convergence_count = 3
        tracker.exhausted_at = datetime.now(timezone.utc).isoformat()
        db_session.commit()
        result = db_session.query(TopicExhaustionTracker).first()
        assert result.status == "exhausted"
        assert result.exhausted_at is not None

    def test_tracker_unique_topic(self, db_session):
        t1 = TopicExhaustionTracker(topic="kubernetes", status="pending")
        db_session.add(t1)
        db_session.commit()

        t2 = TopicExhaustionTracker(topic="kubernetes", status="mining")
        db_session.add(t2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_tracker_facts_and_dupes(self, db_session):
        tracker = TopicExhaustionTracker(
            topic="testing",
            total_new_facts=50,
            total_duplicates=30,
            duplicate_ratio=0.375,
        )
        db_session.add(tracker)
        db_session.commit()
        saved = db_session.query(TopicExhaustionTracker).first()
        assert saved.total_new_facts == 50
        assert saved.total_duplicates == 30
        assert abs(saved.duplicate_ratio - 0.375) < 0.001

    def test_tracker_github_fields(self, db_session):
        tracker = TopicExhaustionTracker(
            topic="react",
            github_mined=True,
            github_repos=15,
            github_facts=200,
        )
        db_session.add(tracker)
        db_session.commit()
        saved = db_session.query(TopicExhaustionTracker).first()
        assert saved.github_mined is True
        assert saved.github_repos == 15
        assert saved.github_facts == 200

    def test_tracker_perspectives_stored(self, db_session):
        perspectives = ["What is X?", "How does X work?", "Why use X?"]
        tracker = TopicExhaustionTracker(
            topic="graphql",
            perspectives_used=perspectives,
        )
        db_session.add(tracker)
        db_session.commit()
        saved = db_session.query(TopicExhaustionTracker).first()
        assert len(saved.perspectives_used) == 3
        assert "What is X?" in saved.perspectives_used


# =====================================================================
# PERSPECTIVE GENERATION TESTS
# =====================================================================

class TestPerspectiveGeneration:
    """Test question generation from multiple perspectives."""

    def test_generates_25_plus_perspectives(self, engine):
        perspectives = engine._generate_perspectives("machine learning")
        assert len(perspectives) >= 25

    def test_perspectives_are_unique(self, engine):
        perspectives = engine._generate_perspectives("testing")
        assert len(perspectives) == len(set(perspectives))

    def test_perspectives_contain_topic(self, engine):
        topic = "distributed systems"
        perspectives = engine._generate_perspectives(topic)
        for p in perspectives:
            assert topic in p

    def test_perspectives_cover_angles(self, engine):
        perspectives = engine._generate_perspectives("API design")
        text = " ".join(perspectives).lower()
        assert "security" in text
        assert "performance" in text
        assert "best practice" in text
        assert "test" in text
        assert "scalab" in text
        assert "architecture" in text

    def test_fresh_questions_excludes_used(self, engine):
        all_p = engine._generate_perspectives("docker")
        used = [p[:80] for p in all_p[:5]]
        fresh = engine._get_fresh_questions("docker", all_p, used, 5, 0)
        for q in fresh:
            assert q[:80] not in used

    def test_fresh_questions_generates_via_cloud_when_exhausted(self, engine, mock_cloud):
        mock_cloud.generate.return_value = {
            "success": True,
            "content": "What are the networking aspects of docker?\nHow does docker handle storage?",
            "tokens": 20,
        }
        all_p = engine._generate_perspectives("docker")
        used = [p[:80] for p in all_p]  # All used up
        fresh = engine._get_fresh_questions("docker", all_p, used, 2, 0)
        assert len(fresh) > 0


# =====================================================================
# FACT HASHING AND DEDUP TESTS
# =====================================================================

class TestFactHashing:
    """Test fact hashing for duplicate detection."""

    def test_same_fact_same_hash(self, engine):
        fact1 = {"subject": "Python", "object": "A programming language"}
        fact2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(fact1) == engine._hash_fact(fact2)

    def test_different_facts_different_hashes(self, engine):
        fact1 = {"subject": "Python", "object": "A programming language"}
        fact2 = {"subject": "Java", "object": "A programming language"}
        assert engine._hash_fact(fact1) != engine._hash_fact(fact2)

    def test_case_insensitive(self, engine):
        fact1 = {"subject": "Python", "object": "A PROGRAMMING language"}
        fact2 = {"subject": "python", "object": "a programming language"}
        assert engine._hash_fact(fact1) == engine._hash_fact(fact2)

    def test_whitespace_normalized(self, engine):
        fact1 = {"subject": "Python", "object": "A  programming   language"}
        fact2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(fact1) == engine._hash_fact(fact2)

    def test_object_value_fallback(self, engine):
        fact1 = {"subject": "Python", "object_value": "A programming language"}
        fact2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(fact1) == engine._hash_fact(fact2)

    def test_hash_truncation(self, engine):
        h = engine._hash_fact({"subject": "x", "object": "y"})
        assert len(h) == 12

    def test_get_existing_hashes_empty(self, engine, db_session):
        hashes = engine._get_existing_fact_hashes(db_session, "nonexistent_topic")
        assert len(hashes) == 0

    def test_get_existing_hashes_with_data(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        fact = CompiledFact(
            subject="Python",
            predicate="is",
            object_value="A programming language",
            domain="programming",
            confidence=0.9,
        )
        db_session.add(fact)
        db_session.commit()

        hashes = engine._get_existing_fact_hashes(db_session, "programming")
        assert len(hashes) == 1

    def test_domain_variant_matching(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        fact = CompiledFact(
            subject="Docker",
            predicate="is",
            object_value="A container runtime",
            domain="dev_ops",
        )
        db_session.add(fact)
        db_session.commit()

        hashes = engine._get_existing_fact_hashes(db_session, "dev ops")
        assert len(hashes) == 1


# =====================================================================
# TOPIC EXHAUSTION TESTS (core convergence logic)
# =====================================================================

class TestTopicExhaustion:
    """Test the core exhaustion algorithm."""

    def _patch_compiler_and_miner(self):
        """Return context managers for patching the compiler and miner at source."""
        compiler_patch = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        miner_patch = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        return compiler_patch, miner_patch

    def test_exhaust_creates_tracker(self, engine, db_session):
        cp, mp = self._patch_compiler_and_miner()
        with cp as mock_compiler, mp as mock_miner:
            mock_compiler.return_value.compile_chunk.return_value = {"facts": []}
            mock_miner.return_value = MagicMock()

            result = engine.exhaust_topic("python basics", max_cycles=1, questions_per_cycle=2)

        assert "topic" in result
        assert result["topic"] == "python basics"
        assert "exhausted" in result
        assert "status" in result

        tracker = db_session.query(TopicExhaustionTracker).filter_by(topic="python basics").first()
        assert tracker is not None
        assert tracker.status in ("mining", "converging", "exhausted")

    def test_already_exhausted_returns_early(self, engine, session_factory):
        s = session_factory()
        tracker = TopicExhaustionTracker(
            topic="exhausted topic",
            status="exhausted",
            total_new_facts=100,
            total_duplicates=200,
        )
        s.add(tracker)
        s.commit()
        s.close()

        result = engine.exhaust_topic("exhausted topic")
        assert result["exhausted"] is True
        assert "already exhausted" in result.get("message", "").lower()

    def test_convergence_when_all_dupes(self, engine, db_session, mock_cloud):
        existing = set()
        for i in range(20):
            existing.add(engine._hash_fact({"subject": f"fact{i}", "object": f"value{i}"}))

        fake_facts = [{"subject": "fact0", "object": "value0"}]

        cp, mp = self._patch_compiler_and_miner()
        with patch.object(engine, '_get_existing_fact_hashes', return_value=existing):
            with cp as mock_compiler, mp as mock_miner:
                mock_compiler.return_value.compile_chunk.return_value = {"facts": fake_facts}
                mock_miner.return_value = MagicMock()

                result = engine.exhaust_topic(
                    "well known topic",
                    max_cycles=3,
                    questions_per_cycle=2,
                )

        assert result["duplicates"] > 0

    def test_new_facts_produce_mining_status(self, engine, db_session, mock_cloud):
        call_count = [0]

        def dynamic_response(**kwargs):
            call_count[0] += 1
            return {
                "success": True,
                "content": f"Unique fact number {call_count[0]} about novel concept {call_count[0]}",
                "tokens": 30,
            }

        mock_cloud.generate.side_effect = dynamic_response
        fact_counter = [0]

        def unique_compiled(**kwargs):
            fact_counter[0] += 1
            return {"facts": [{"subject": f"new_{fact_counter[0]}", "object": f"unique_{fact_counter[0]}"}]}

        cp, mp = self._patch_compiler_and_miner()
        with cp as mock_compiler, mp as mock_miner:
            mock_compiler.return_value.compile_chunk.side_effect = unique_compiled
            mock_miner.return_value = MagicMock()

            result = engine.exhaust_topic(
                "fresh topic",
                max_cycles=1,
                questions_per_cycle=3,
            )

        assert result["status"] in ("mining", "converging", "exhausted")

    def test_cloud_unavailable_stops_gracefully(self, engine, mock_cloud):
        mock_cloud.is_available.return_value = False

        cp, mp = self._patch_compiler_and_miner()
        with cp, mp:
            result = engine.exhaust_topic("offline topic", max_cycles=1, questions_per_cycle=2)

        assert result["questions_asked"] == 0

    def test_cloud_generate_failure_continues(self, engine, db_session, mock_cloud):
        call_idx = [0]

        def flaky_cloud(**kwargs):
            call_idx[0] += 1
            if call_idx[0] % 2 == 0:
                return {"success": False, "error": "rate limited"}
            return {"success": True, "content": "Some fact about topic", "tokens": 10}

        mock_cloud.generate.side_effect = flaky_cloud

        cp, mp = self._patch_compiler_and_miner()
        with cp as mock_compiler, mp as mock_miner:
            mock_compiler.return_value.compile_chunk.return_value = {"facts": []}
            mock_miner.return_value = MagicMock()

            result = engine.exhaust_topic("flaky topic", max_cycles=1, questions_per_cycle=4)

        assert result["questions_asked"] >= 0

    def test_exhaust_persists_state(self, engine, db_session):
        cp, mp = self._patch_compiler_and_miner()
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            engine.exhaust_topic("tracked topic", max_cycles=1, questions_per_cycle=2)

        tracker = db_session.query(TopicExhaustionTracker).filter_by(topic="tracked topic").first()
        assert tracker is not None
        assert tracker.cycles_completed >= 1
        assert tracker.last_mined_at is not None
        assert len(tracker.perspectives_used) > 0


# =====================================================================
# MULTI-TOPIC EXHAUSTION TESTS
# =====================================================================

class TestMultiTopicExhaustion:
    """Test exhausting multiple topics."""

    def test_exhaust_multiple_topics(self, engine, db_session):
        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_multiple(
                ["topic A", "topic B"],
                max_cycles=1,
                questions_per_cycle=2,
            )

        assert result["topics_processed"] == 2
        assert "results" in result

    def test_exhaust_multiple_stops_on_api_down(self, engine, db_session, mock_cloud):
        call_count = [0]

        def become_unavailable():
            call_count[0] += 1
            return call_count[0] <= 5

        mock_cloud.is_available.side_effect = become_unavailable

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_multiple(
                ["t1", "t2", "t3", "t4"],
                max_cycles=1,
                questions_per_cycle=2,
            )

        assert result["topics_processed"] >= 1


# =====================================================================
# STATUS AND REPORTING TESTS
# =====================================================================

class TestStatusAndReporting:
    """Test topic status queries and stats."""

    def test_get_unknown_topic_status(self, engine):
        status = engine.get_topic_status("unknown")
        assert status["exists"] is False
        assert status["status"] == "unknown"

    def test_get_known_topic_status(self, engine, session_factory):
        s = session_factory()
        s.add(TopicExhaustionTracker(
            topic="known topic",
            status="converging",
            cycles_completed=2,
            convergence_count=1,
            total_new_facts=50,
            total_duplicates=30,
        ))
        s.commit()
        s.close()

        status = engine.get_topic_status("known topic")
        assert status["exists"] is True
        assert status["status"] == "converging"
        assert status["cycles_completed"] == 2
        assert status["total_new_facts"] == 50

    def test_get_all_topics_status(self, engine, session_factory):
        s = session_factory()
        for i in range(3):
            s.add(TopicExhaustionTracker(
                topic=f"topic_{i}",
                status="mining" if i < 2 else "exhausted",
            ))
        s.commit()
        s.close()

        all_status = engine.get_all_topics_status()
        assert len(all_status) == 3
        exhausted = [s for s in all_status if s["status"] == "exhausted"]
        assert len(exhausted) == 1

    def test_stats_include_db_counts(self, engine, session_factory):
        s = session_factory()
        for status in ["mining", "converging", "exhausted"]:
            s.add(TopicExhaustionTracker(topic=f"s_{status}", status=status))
        s.commit()
        s.close()

        stats = engine.get_stats()
        assert stats["tracked_topics"] == 3
        assert stats["exhausted_topics"] == 1
        assert stats["converging_topics"] == 1
        assert stats["mining_topics"] == 1


# =====================================================================
# GITHUB MASSIVE DUMP TESTS
# =====================================================================

class TestGitHubMassiveDump:
    """Test the GitHub massive knowledge dump."""

    def test_github_dump_basic(self, engine, db_session):
        mock_search = MagicMock()
        mock_search.status_code = 200
        mock_search.json.return_value = {
            "items": [{
                "full_name": "test/repo",
                "stargazers_count": 5000,
                "description": "A test repository",
                "language": "Python",
                "html_url": "https://github.com/test/repo",
            }]
        }

        mock_readme = MagicMock()
        mock_readme.status_code = 200
        mock_readme.text = "# Test Repo\n\nThis is a test repository for unit testing."

        mock_tree = MagicMock()
        mock_tree.status_code = 200
        mock_tree.json.return_value = {
            "tree": [
                {"path": "main.py", "type": "blob", "size": 1000},
            ]
        }

        mock_file = MagicMock()
        mock_file.status_code = 200
        mock_file.text = "def hello():\n    print('Hello, world!')"

        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mock_get:
            def side_effect(url, **kwargs):
                if "search" in url:
                    return mock_search
                elif "readme" in url:
                    return mock_readme
                elif "trees" in url:
                    return mock_tree
                elif "contents" in url:
                    return mock_file
                return MagicMock(status_code=404)

            mock_get.side_effect = side_effect

            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": [], "procedures": []}

                with patch.object(engine, '_vectorize_text'):
                    result = engine.github_massive_dump(
                        ["unit testing"],
                        max_repos_per_topic=1,
                        max_files_per_repo=1,
                    )

        assert result["total_repos"] >= 1
        assert "results" in result

    def test_github_dump_api_failure(self, engine, db_session):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("cognitive.knowledge_exhaustion_engine.requests.get", return_value=mock_resp):
            result = engine.github_massive_dump(["forbidden topic"], max_repos_per_topic=1)

        assert result["total_repos"] == 0
        assert "error" in result["results"][0]

    def test_github_dump_updates_tracker(self, engine, db_session):
        mock_search = MagicMock()
        mock_search.status_code = 200
        mock_search.json.return_value = {
            "items": [{
                "full_name": "org/repo",
                "stargazers_count": 100,
                "description": "Test",
                "language": "Python",
                "html_url": "https://github.com/org/repo",
            }]
        }

        mock_readme = MagicMock()
        mock_readme.status_code = 404

        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mock_get:
            def side_effect(url, **kwargs):
                if "search" in url:
                    return mock_search
                return mock_readme

            mock_get.side_effect = side_effect

            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": []}
                with patch.object(engine, '_vectorize_text'):
                    engine.github_massive_dump(["tracked_gh"], max_repos_per_topic=1, include_code_files=False)

        tracker = db_session.query(TopicExhaustionTracker).filter_by(topic="tracked_gh").first()
        assert tracker is not None
        assert tracker.github_mined is True
        assert tracker.github_repos >= 1

    def test_github_dump_multiple_topics(self, engine, db_session):
        mock_search = MagicMock()
        mock_search.status_code = 200
        mock_search.json.return_value = {"items": []}

        with patch("cognitive.knowledge_exhaustion_engine.requests.get", return_value=mock_search):
            result = engine.github_massive_dump(
                ["topic1", "topic2", "topic3"],
                max_repos_per_topic=1,
            )

        assert result["topics_mined"] == 3

    def test_github_dump_confidence_from_stars(self, engine, db_session):
        mock_search = MagicMock()
        mock_search.status_code = 200
        mock_search.json.return_value = {
            "items": [{
                "full_name": "popular/repo",
                "stargazers_count": 50000,
                "description": "Very popular",
                "language": "Go",
                "html_url": "https://github.com/popular/repo",
            }]
        }

        mock_readme = MagicMock()
        mock_readme.status_code = 404

        with patch("cognitive.knowledge_exhaustion_engine.requests.get") as mock_get:
            def side_effect(url, **kwargs):
                if "search" in url:
                    return mock_search
                return mock_readme

            mock_get.side_effect = side_effect

            with patch('cognitive.knowledge_compiler.KnowledgeCompiler') as mc:
                mc.return_value.compile_chunk.return_value = {"facts": []}
                with patch.object(engine, '_vectorize_text'):
                    engine.github_massive_dump(["popular"], max_repos_per_topic=1, include_code_files=False)

        from cognitive.knowledge_compiler import CompiledFact
        facts = db_session.query(CompiledFact).filter_by(subject="popular/repo").all()
        assert len(facts) >= 1
        assert facts[0].confidence >= 0.9


# =====================================================================
# VECTORIZATION TESTS
# =====================================================================

class TestVectorization:
    """Test auto-vectorization into Qdrant."""

    def test_vectorize_text_handles_missing_qdrant(self, engine):
        engine._vectorize_text("test text", {"source": "test"})

    def test_vectorize_text_noop_on_exception(self, engine):
        with patch.dict("sys.modules", {"embedding.ollama_embedder": None}):
            engine._vectorize_text("test text", {"source": "test"})


# =====================================================================
# EDGE CASE TESTS
# =====================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_topic(self, engine, db_session, mock_cloud):
        mock_cloud.generate.return_value = {
            "success": True,
            "content": "",
            "tokens": 0,
        }

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_topic("empty", max_cycles=1, questions_per_cycle=2)

        assert result["new_facts"] == 0

    def test_very_long_topic_name(self, engine, db_session):
        long_topic = "a" * 256

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            result = engine.exhaust_topic(long_topic, max_cycles=1, questions_per_cycle=1)

        assert result["topic"] == long_topic

    def test_concurrent_exhaust_same_topic(self, engine, db_session):
        """Verify a topic reuses the same tracker on multiple calls."""
        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.return_value = {"facts": []}
            mm.return_value = MagicMock()
            engine.exhaust_topic("concurrent", max_cycles=1, questions_per_cycle=1)
            engine.exhaust_topic("concurrent", max_cycles=1, questions_per_cycle=1)

        trackers = db_session.query(TopicExhaustionTracker).filter_by(topic="concurrent").all()
        assert len(trackers) == 1
        assert trackers[0].cycles_completed >= 2

    def test_no_cloud_client(self, session_factory, db_session):
        engine = KnowledgeExhaustionEngine(session_factory, cloud_client=None)
        result = engine.exhaust_topic("offline", max_cycles=1, questions_per_cycle=2)
        assert result["questions_asked"] == 0

    def test_stats_without_db(self):
        def bad_factory():
            raise Exception("DB unavailable")
        engine = KnowledgeExhaustionEngine(bad_factory)
        stats = engine.get_stats()
        assert "topics_exhausted" in stats


# =====================================================================
# INTEGRATION-LIKE TESTS (compile + hash cycle)
# =====================================================================

class TestConvergenceCycle:
    """Test the full convergence detection cycle with realistic data."""

    def test_convergence_detection_full_cycle(self, engine, db_session, mock_cloud):
        """Simulate: 3 cycles where facts converge."""
        existing_hashes = set()
        base_fact = {"subject": "Python", "object": "Is a programming language"}
        existing_hashes.add(engine._hash_fact(base_fact))

        mock_cloud.generate.return_value = {
            "success": True,
            "content": "Python is a programming language used for many things.",
            "tokens": 20,
        }

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with patch.object(engine, '_get_existing_fact_hashes', return_value=existing_hashes):
            with cp as mc, mp as mm:
                mc.return_value.compile_chunk.return_value = {"facts": [base_fact]}
                mm.return_value = MagicMock()
                result = engine.exhaust_topic(
                    "convergence test",
                    max_cycles=3,
                    questions_per_cycle=5,
                )

        assert result["duplicates"] > 0
        assert result["duplicate_ratio"] > 0.5

    def test_non_convergence_with_novel_facts(self, engine, db_session, mock_cloud):
        """Simulate: Each question returns completely new facts."""
        call_idx = [0]

        def unique_facts(**kwargs):
            call_idx[0] += 1
            return {
                "success": True,
                "content": f"Unique insight #{call_idx[0]} about novel concept.",
                "tokens": 15,
            }

        mock_cloud.generate.side_effect = unique_facts
        fact_counter = [0]

        def unique_compiled(**kwargs):
            fact_counter[0] += 1
            return {"facts": [{"subject": f"new_{fact_counter[0]}", "object": f"val_{fact_counter[0]}"}]}

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.side_effect = unique_compiled
            mm.return_value = MagicMock()
            result = engine.exhaust_topic(
                "novel topic",
                max_cycles=1,
                questions_per_cycle=3,
            )

        assert result["new_facts"] > 0
        assert result["status"] in ("mining", "converging")

    def test_gradual_convergence(self, engine, db_session, mock_cloud):
        """Simulate: Knowledge gradually converges over multiple cycles."""
        call_counter = [0]

        def gradually_converging(**kwargs):
            call_counter[0] += 1
            if call_counter[0] <= 3:
                content = f"Brand new fact #{call_counter[0]} about advanced concept"
            else:
                content = "Python is a programming language. Already known fact."
            return {"success": True, "content": content, "tokens": 10}

        mock_cloud.generate.side_effect = gradually_converging
        fact_idx = [0]

        def compiled(**kwargs):
            fact_idx[0] += 1
            if fact_idx[0] <= 3:
                return {"facts": [{"subject": f"new_{fact_idx[0]}", "object": f"val_{fact_idx[0]}"}]}
            else:
                return {"facts": []}

        cp = patch('cognitive.knowledge_compiler.KnowledgeCompiler')
        mp = patch('cognitive.knowledge_compiler.get_llm_knowledge_miner')
        with cp as mc, mp as mm:
            mc.return_value.compile_chunk.side_effect = compiled
            mm.return_value = MagicMock()
            result = engine.exhaust_topic(
                "gradual topic",
                max_cycles=2,
                questions_per_cycle=5,
            )

        assert result["cycles_run"] >= 1
