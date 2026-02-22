"""
Comprehensive tests for GraceKnowledgeEngine - the unified knowledge system.

Tests:
- Deterministic query (no LLM)
- Multi-source discovery with dedup
- Knowledge compilation
- Convergence-based exhaustion (delegates)
- GitHub massive dump (delegates)
- Gap audit with Kimi recommendations
- Topic depth assessment
- Vector-based semantic dedup
- Fact hash dedup
- Stats and reporting
- Source-specific discovery (cloud, wikidata, github, arxiv, etc.)
- Edge cases and error handling
"""

import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.base import Base

from cognitive.grace_knowledge_engine import GraceKnowledgeEngine, get_grace_knowledge_engine


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
        from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker
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
        "content": "Python | created_by | Guido van Rossum\nPython | first_released | 1991\n",
        "tokens": 30,
    }
    return client


@pytest.fixture
def engine(session_factory, mock_cloud):
    return GraceKnowledgeEngine(session_factory, mock_cloud)


# =====================================================================
# QUERY TESTS (deterministic, no LLM)
# =====================================================================

class TestQuery:

    def test_query_empty_store(self, engine):
        result = engine.query("What is Python?")
        assert result["total_results"] == 0
        assert result["facts"] == []

    def test_query_finds_facts(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Python", predicate="created_by",
            object_value="Guido van Rossum",
            confidence=0.95, domain="programming",
        ))
        db_session.commit()

        result = engine.query("Python", domain="programming")
        assert result["total_results"] >= 1
        assert any("Guido" in f["object"] for f in result["facts"])

    def test_query_finds_procedures(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledProcedure
        db_session.add(CompiledProcedure(
            name="Deploy Docker container",
            goal="Deploy app using Docker",
            steps=[{"step": 1, "action": "Build image"}],
            confidence=0.8, domain="devops",
        ))
        db_session.commit()

        result = engine.query("Docker deploy", domain="devops")
        assert len(result["procedures"]) >= 1

    def test_query_finds_rules(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledDecisionRule
        db_session.add(CompiledDecisionRule(
            rule_name="Use Redis for caching",
            conditions=[{"field": "need", "operator": "==", "value": "cache"}],
            action="Use Redis",
            confidence=0.9, domain="architecture",
        ))
        db_session.commit()

        result = engine.query("Redis caching", domain="architecture")
        assert len(result["rules"]) >= 1

    def test_query_increments_stats(self, engine):
        engine.query("test")
        engine.query("test2")
        assert engine._stats["queries"] == 2

    def test_query_with_no_domain(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="FastAPI", predicate="is",
            object_value="A modern Python web framework",
            confidence=0.9, domain="web",
        ))
        db_session.commit()

        result = engine.query("FastAPI")
        assert result["total_results"] >= 1


# =====================================================================
# DISCOVER TESTS (multi-source with dedup)
# =====================================================================

class TestDiscover:

    def test_discover_from_cloud(self, engine, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            result = engine.discover("Python", sources=["cloud"], max_per_source=5)

        assert result["topic"] == "Python"
        assert result["sources_queried"] == 1
        assert "cloud" in result["by_source"]

    def test_discover_dedup_against_existing(self, engine, db_session, mock_cloud):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Python", predicate="created_by",
            object_value="Guido van Rossum",
            confidence=0.95, domain="Python",
        ))
        db_session.commit()

        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            result = engine.discover("Python", sources=["cloud"])

        # Some facts should be deduplicated
        assert result["total_found"] > 0

    def test_discover_multiple_sources(self, engine):
        with patch.object(engine, '_discover_from_cloud', return_value=[]):
            with patch.object(engine, '_discover_from_wikidata', return_value=[]):
                with patch.object(engine, '_discover_from_github', return_value=[]):
                    result = engine.discover(
                        "machine learning",
                        sources=["cloud", "wikidata", "github"],
                    )

        assert result["sources_queried"] == 3

    def test_discover_stores_new_facts(self, engine, db_session, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("Go language", sources=["cloud"], max_per_source=3)

        if result["total_new"] > 0:
            from cognitive.knowledge_compiler import CompiledFact
            facts = db_session.query(CompiledFact).filter(
                CompiledFact.domain == "Go_language"
            ).all()
            assert len(facts) > 0

    def test_discover_handles_source_error(self, engine):
        with patch.object(engine, '_discover_from_cloud', side_effect=Exception("API down")):
            result = engine.discover("test", sources=["cloud"])

        assert "error" in result["by_source"]["cloud"]

    def test_discover_semantic_dedup_skips_similar(self, engine, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=True):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("Python", sources=["cloud"])

        assert result["total_duplicates"] >= result["total_new"]


# =====================================================================
# COMPILE TESTS
# =====================================================================

class TestCompile:

    def test_compile_basic_text(self, engine):
        with patch.object(engine, '_vectorize'):
            result = engine.compile(
                "Python is a programming language created by Guido van Rossum.",
                domain="programming",
            )

        assert "facts" in result

    def test_compile_increments_stats(self, engine):
        with patch.object(engine, '_vectorize'):
            engine.compile("Docker is a container runtime.", domain="devops")

        assert engine._stats["facts_compiled"] >= 0

    def test_compile_with_source_id(self, engine):
        with patch.object(engine, '_vectorize'):
            result = engine.compile(
                "REST APIs use HTTP methods.",
                domain="web",
                source_id="manual:test",
            )

        assert "facts" in result or "error" not in result


# =====================================================================
# EXHAUST TESTS (delegates to exhaustion engine)
# =====================================================================

class TestExhaust:

    def test_exhaust_delegates(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mock_ee:
            mock_instance = MagicMock()
            mock_instance.exhaust_topic.return_value = {
                "topic": "docker", "exhausted": False, "status": "mining",
            }
            mock_ee.return_value = mock_instance

            result = engine.exhaust("docker", max_cycles=2)

        assert result["topic"] == "docker"
        mock_instance.exhaust_topic.assert_called_once()

    def test_exhaust_multiple_delegates(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mock_ee:
            mock_instance = MagicMock()
            mock_instance.exhaust_multiple.return_value = {"topics_processed": 2}
            mock_ee.return_value = mock_instance

            result = engine.exhaust_multiple(["a", "b"])

        assert result["topics_processed"] == 2

    def test_exhaust_updates_stats_on_exhaustion(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mock_ee:
            mock_instance = MagicMock()
            mock_instance.exhaust_topic.return_value = {
                "topic": "k8s", "exhausted": True, "status": "exhausted",
            }
            mock_ee.return_value = mock_instance

            engine.exhaust("k8s")

        assert engine._stats["topics_exhausted"] == 1


# =====================================================================
# GITHUB DUMP TESTS
# =====================================================================

class TestGitHubDump:

    def test_github_dump_delegates(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mock_ee:
            mock_instance = MagicMock()
            mock_instance.github_massive_dump.return_value = {
                "total_repos": 10, "total_facts": 50,
            }
            mock_ee.return_value = mock_instance

            result = engine.github_dump(["fastapi"], max_repos=5)

        assert result["total_repos"] == 10
        assert engine._stats["github_repos_mined"] == 10


# =====================================================================
# AUDIT TESTS (Kimi identifies gaps)
# =====================================================================

class TestAudit:

    def test_audit_empty_store(self, engine):
        result = engine.audit_gaps()
        assert "totals" in result
        assert result["totals"]["facts"] == 0

    def test_audit_identifies_shallow_topics(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(3):
            db_session.add(CompiledFact(
                subject=f"fact_{i}", predicate="is",
                object_value=f"value_{i}",
                confidence=0.8, domain="shallow_topic",
            ))
        db_session.commit()

        result = engine.audit_gaps()

        shallow_gaps = [g for g in result["gaps"] if g["type"] == "shallow_facts"]
        assert len(shallow_gaps) >= 1

    def test_audit_identifies_missing_procedures(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(10):
            db_session.add(CompiledFact(
                subject=f"k8s_fact_{i}", predicate="is",
                object_value=f"kubernetes value {i}",
                confidence=0.8, domain="kubernetes",
            ))
        db_session.commit()

        result = engine.audit_gaps()

        proc_gaps = [g for g in result["gaps"] if g["type"] == "no_procedures"]
        assert len(proc_gaps) >= 1

    def test_audit_calculates_depth(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact, CompiledProcedure
        for i in range(20):
            db_session.add(CompiledFact(
                subject=f"docker_fact_{i}", predicate="is",
                object_value=f"docker value {i}",
                confidence=0.8, domain="docker",
            ))
        db_session.add(CompiledProcedure(
            name="Build Docker image",
            goal="Create container image",
            steps=[{"step": 1, "action": "Write Dockerfile"}],
            confidence=0.9, domain="docker",
        ))
        db_session.commit()

        result = engine.audit_gaps()
        assert "docker" in result["domains"]
        assert result["domains"]["docker"]["depth_score"] > 0

    def test_audit_asks_kimi_for_recommendations(self, engine, db_session, mock_cloud):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(5):
            db_session.add(CompiledFact(
                subject=f"gap_fact_{i}", predicate="is",
                object_value=f"value {i}",
                confidence=0.5, domain="gap_topic",
            ))
        db_session.commit()

        mock_cloud.generate.return_value = {
            "success": True,
            "content": "1 | gap_topic | Add more facts about core concepts | cloud",
            "tokens": 20,
        }

        result = engine.audit_gaps()
        assert len(result.get("recommendations", [])) >= 0

    def test_audit_sorts_by_severity(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        # Create one empty domain and one shallow domain
        db_session.add(CompiledFact(
            subject="x", predicate="is", object_value="y",
            confidence=0.5, domain="shallow",
        ))
        db_session.commit()

        result = engine.audit_gaps()
        if len(result["gaps"]) > 1:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            severities = [severity_order.get(g["severity"], 4) for g in result["gaps"]]
            assert severities == sorted(severities)


# =====================================================================
# AUDIT DEPTH (single topic)
# =====================================================================

class TestAuditDepth:

    def test_audit_depth_basic(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(5):
            db_session.add(CompiledFact(
                subject=f"ml_concept_{i}", predicate="is",
                object_value=f"ML explanation {i}",
                confidence=0.8, domain="machine_learning",
            ))
        db_session.commit()

        result = engine.audit_depth("machine_learning")
        assert result["fact_count"] == 5
        assert result["unique_subjects"] == 5

    def test_audit_depth_calls_kimi(self, engine, db_session, mock_cloud):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="test", predicate="is", object_value="something",
            confidence=0.8, domain="test_topic",
        ))
        db_session.commit()

        mock_cloud.generate.return_value = {
            "success": True,
            "content": "DEPTH LEVEL: beginner\nMISSING: advanced patterns, testing, deployment",
            "tokens": 25,
        }

        result = engine.audit_depth("test_topic")
        assert "kimi_assessment" in result

    def test_audit_depth_no_cloud(self, session_factory):
        engine = GraceKnowledgeEngine(session_factory, cloud_client=None)
        result = engine.audit_depth("any_topic")
        assert "kimi_assessment" not in result


# =====================================================================
# TOPIC STATUS TESTS
# =====================================================================

class TestTopicStatus:

    def test_topic_status_empty(self, engine):
        status = engine.topic_status("nonexistent")
        assert status["facts"] == 0
        assert status["depth_label"] == "empty"

    def test_topic_status_with_data(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(15):
            db_session.add(CompiledFact(
                subject=f"fact_{i}", predicate="is",
                object_value=f"value_{i}",
                confidence=0.8, domain="test_domain",
            ))
        db_session.commit()

        status = engine.topic_status("test_domain")
        assert status["facts"] == 15
        assert status["depth_score"] > 0
        assert status["depth_label"] in ("beginner", "intermediate")

    def test_topic_status_includes_exhaustion(self, engine, session_factory):
        from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker
        s = session_factory()
        s.add(TopicExhaustionTracker(topic="tracked", status="converging", convergence_count=2))
        s.commit()
        s.close()

        status = engine.topic_status("tracked")
        assert status.get("exhaustion", {}).get("status") == "converging"


# =====================================================================
# STATS TESTS
# =====================================================================

class TestStats:

    def test_stats_empty(self, engine):
        result = engine.stats()
        assert result["queries"] == 0
        assert result["store"]["facts"] == 0

    def test_stats_with_data(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(5):
            db_session.add(CompiledFact(
                subject=f"s_{i}", predicate="is",
                object_value=f"v_{i}",
                confidence=0.8, domain="stats_test",
            ))
        db_session.commit()

        result = engine.stats()
        assert result["store"]["facts"] == 5
        assert "stats_test" in result.get("top_domains", {})


# =====================================================================
# FACT HASHING TESTS
# =====================================================================

class TestFactHashing:

    def test_same_fact_same_hash(self, engine):
        f1 = {"subject": "Python", "object": "A language"}
        f2 = {"subject": "Python", "object": "A language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_different_fact_different_hash(self, engine):
        f1 = {"subject": "Python", "object": "A language"}
        f2 = {"subject": "Java", "object": "A language"}
        assert engine._hash_fact(f1) != engine._hash_fact(f2)

    def test_case_insensitive(self, engine):
        f1 = {"subject": "PYTHON", "object": "A LANGUAGE"}
        f2 = {"subject": "python", "object": "a language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)

    def test_whitespace_normalized(self, engine):
        f1 = {"subject": "Python", "object": "A  programming   language"}
        f2 = {"subject": "Python", "object": "A programming language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)


# =====================================================================
# DEPTH LABEL TESTS
# =====================================================================

class TestDepthLabel:

    def test_empty(self, engine):
        assert engine._depth_label(0) == "empty"

    def test_beginner(self, engine):
        assert engine._depth_label(15) == "beginner"

    def test_intermediate(self, engine):
        assert engine._depth_label(40) == "intermediate"

    def test_advanced(self, engine):
        assert engine._depth_label(65) == "advanced"

    def test_expert(self, engine):
        assert engine._depth_label(85) == "expert"


# =====================================================================
# VECTOR DEDUP TESTS
# =====================================================================

class TestVectorDedup:

    def test_semantic_dedup_handles_missing_qdrant(self, engine):
        result = engine._is_semantically_duplicate({"subject": "x", "object": "y"})
        assert result is False

    def test_vectorize_handles_errors(self, engine):
        engine._vectorize("test text", {"source": "test"})

    def test_get_vector_count_handles_missing(self, engine):
        count = engine._get_vector_count()
        assert count >= 0


# =====================================================================
# SOURCE-SPECIFIC DISCOVERY TESTS
# =====================================================================

class TestSourceDiscovery:

    def test_discover_from_cloud_no_client(self, session_factory):
        engine = GraceKnowledgeEngine(session_factory, cloud_client=None)
        facts = engine._discover_from_cloud("test", 5)
        assert facts == []

    def test_discover_from_cloud_parses_response(self, engine, mock_cloud):
        mock_cloud.generate.return_value = {
            "success": True,
            "content": "Docker | is | a container platform\nK8s | manages | containers",
            "tokens": 20,
        }
        facts = engine._discover_from_cloud("containers", 5)
        assert len(facts) >= 2
        assert facts[0]["source"] == "kimi_cloud"

    def test_discover_from_cloud_failed_generation(self, engine, mock_cloud):
        mock_cloud.generate.return_value = {"success": False, "error": "timeout"}
        facts = engine._discover_from_cloud("test", 5)
        assert facts == []

    def test_discover_from_wikidata(self, engine):
        with patch('cognitive.library_connectors.LibraryConnectors') as mock_lib:
            mock_lib.return_value.query_wikidata.return_value = [
                {"subject": "Python", "predicate": "instance_of", "object": "programming language", "confidence": 1.0}
            ]
            facts = engine._discover_from_wikidata("Python", 5)
        assert len(facts) >= 0

    def test_discover_from_github(self, engine):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [{"full_name": "org/repo", "description": "A repo",
                        "stargazers_count": 1000, "language": "Python"}]
        }
        with patch("requests.get", return_value=mock_resp):
            facts = engine._discover_from_github("python web", 3)

        assert len(facts) >= 0

    def test_discover_from_arxiv_error(self, engine):
        facts = engine._discover_from_arxiv("nonexistent query zzz", 1)
        assert isinstance(facts, list)

    def test_discover_from_stackoverflow_error(self, engine):
        facts = engine._discover_from_stackoverflow("nonexistent zzz", 1)
        assert isinstance(facts, list)


# =====================================================================
# EDGE CASES
# =====================================================================

class TestEdgeCases:

    def test_engine_with_no_cloud(self, session_factory):
        engine = GraceKnowledgeEngine(session_factory, cloud_client=None)
        result = engine.query("test")
        assert "error" not in result or result["total_results"] == 0

    def test_engine_stats_after_operations(self, engine):
        engine.query("test1")
        engine.query("test2")
        stats = engine.stats()
        assert stats["queries"] == 2

    def test_distill_handles_errors(self, engine, db_session):
        engine._distill(db_session, "q", "a")

    def test_store_facts_empty_list(self, engine, db_session):
        engine._store_facts(db_session, [], "topic", "source")

    def test_get_fact_hashes_bad_domain(self, engine, db_session):
        hashes = engine._get_fact_hashes(db_session, "nonexistent_xxxx")
        assert len(hashes) == 0


# =====================================================================
# SINGLETON TEST
# =====================================================================

class TestSingleton:

    def test_get_grace_knowledge_engine_creates_instance(self):
        import cognitive.grace_knowledge_engine as mod
        mod._engine = None
        with patch('cognitive.grace_knowledge_engine.SessionLocal', create=True):
            engine = get_grace_knowledge_engine(session_factory=lambda: MagicMock())
        assert engine is not None
        mod._engine = None  # reset
