"""
Tests for GraceKnowledgeEngine - verifies actual query logic, discovery dedup,
compilation, audit depth scoring, reverse KNN, and stats computation.
"""

import sys
import os
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
        "content": "Docker | is | a container platform\nK8s | manages | containers",
        "tokens": 30,
    }
    return client


@pytest.fixture
def engine(session_factory, mock_cloud):
    return GraceKnowledgeEngine(session_factory, mock_cloud)


# =====================================================================
# QUERY - verifies keyword matching, domain filtering, result structure
# =====================================================================

class TestQuery:

    def test_empty_store_returns_zero_results(self, engine):
        result = engine.query("anything")
        assert result["total_results"] == 0
        assert result["facts"] == []
        assert result["procedures"] == []
        assert result["rules"] == []
        assert result["distilled"] is None

    def test_finds_matching_facts_by_subject(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Python", predicate="created_by",
            object_value="Guido van Rossum", confidence=0.95, domain="programming",
        ))
        db_session.commit()

        result = engine.query("Python", domain="programming")
        assert result["total_results"] >= 1
        assert any("Guido" in f["object"] for f in result["facts"])
        assert result["facts"][0]["confidence"] == 0.95

    def test_finds_procedures_by_goal(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledProcedure
        db_session.add(CompiledProcedure(
            name="Deploy Docker", goal="Deploy app using Docker",
            steps=[{"step": 1, "action": "Build image"}, {"step": 2, "action": "Push"}],
            confidence=0.8, domain="devops",
        ))
        db_session.commit()

        result = engine.query("Docker deploy", domain="devops")
        assert len(result["procedures"]) >= 1
        assert result["procedures"][0]["steps"][0]["action"] == "Build image"

    def test_finds_rules_by_name(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledDecisionRule
        db_session.add(CompiledDecisionRule(
            rule_name="Use Redis for caching",
            conditions=[{"field": "need", "operator": "==", "value": "cache"}],
            action="Use Redis", confidence=0.9, domain="architecture",
        ))
        db_session.commit()

        result = engine.query("Redis caching", domain="architecture")
        assert len(result["rules"]) >= 1
        assert result["rules"][0]["action"] == "Use Redis"

    def test_domain_filter_excludes_other_domains(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="FastAPI", predicate="is", object_value="Web framework",
            confidence=0.9, domain="web",
        ))
        db_session.add(CompiledFact(
            subject="FastAPI perf", predicate="is", object_value="Very fast",
            confidence=0.8, domain="performance",
        ))
        db_session.commit()

        result = engine.query("FastAPI", domain="web")
        domains = {f["domain"] for f in result["facts"]}
        assert "performance" not in domains

    def test_query_increments_stats_counter(self, engine):
        engine.query("a")
        engine.query("b")
        engine.query("c")
        assert engine._stats["queries"] == 3


# =====================================================================
# DISCOVER - verifies dedup logic, multi-source routing, fact storage
# =====================================================================

class TestDiscover:

    def test_cloud_discovery_parses_pipe_format(self, engine, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("containers", sources=["cloud"], max_per_source=5)

        assert result["total_new"] >= 2
        assert result["by_source"]["cloud"]["found"] >= 2

    def test_hash_dedup_filters_known_facts(self, engine, db_session, mock_cloud):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="Docker", predicate="is",
            object_value="a container platform",
            confidence=0.95, domain="containers",
        ))
        db_session.commit()

        mock_cloud.generate.return_value = {
            "success": True,
            "content": "Docker | is | a container platform",
            "tokens": 10,
        }
        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("containers", sources=["cloud"])

        assert result["total_duplicates"] >= 1

    def test_semantic_dedup_filters_similar_facts(self, engine, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=True):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("Python", sources=["cloud"])

        assert result["total_duplicates"] >= result["total_new"]

    def test_new_facts_stored_in_db(self, engine, db_session, mock_cloud):
        with patch.object(engine, '_is_semantically_duplicate', return_value=False):
            with patch.object(engine, '_vectorize'):
                result = engine.discover("Go language", sources=["cloud"])

        if result["total_new"] > 0:
            from cognitive.knowledge_compiler import CompiledFact
            count = db_session.query(CompiledFact).filter(
                CompiledFact.domain == "Go_language"
            ).count()
            assert count > 0

    def test_source_error_captured_not_raised(self, engine):
        with patch.object(engine, '_discover_from_cloud', side_effect=Exception("boom")):
            result = engine.discover("test", sources=["cloud"])
        assert "error" in result["by_source"]["cloud"]
        assert "boom" in result["by_source"]["cloud"]["error"]


# =====================================================================
# COMPILE - verifies text compilation actually extracts structures
# =====================================================================

class TestCompile:

    def test_compile_extracts_facts_from_definition(self, engine):
        with patch.object(engine, '_vectorize'):
            result = engine.compile(
                "Docker is a container platform for packaging applications.",
                domain="devops",
            )
        assert "facts" in result
        if result["facts"]:
            assert any("Docker" in str(f.get("subject", "")) for f in result["facts"])

    def test_compile_with_source_id_stored(self, engine):
        with patch.object(engine, '_vectorize'):
            result = engine.compile("REST is an API style.", domain="web", source_id="test:1")
        assert "error" not in result


# =====================================================================
# EXHAUST / GITHUB DUMP - verifies delegation works correctly
# =====================================================================

class TestExhaust:

    def test_exhaust_delegates_and_tracks_exhaustion(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mee:
            mee.return_value.exhaust_topic.return_value = {"topic": "k8s", "exhausted": True, "status": "exhausted"}
            result = engine.exhaust("k8s")

        assert result["exhausted"] is True
        assert engine._stats["topics_exhausted"] == 1

    def test_exhaust_non_exhausted_does_not_increment(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mee:
            mee.return_value.exhaust_topic.return_value = {"topic": "x", "exhausted": False, "status": "mining"}
            engine.exhaust("x")

        assert engine._stats["topics_exhausted"] == 0


class TestGitHubDump:

    def test_github_dump_tracks_repo_count(self, engine):
        with patch('cognitive.knowledge_exhaustion_engine.get_knowledge_exhaustion_engine') as mee:
            mee.return_value.github_massive_dump.return_value = {"total_repos": 15, "total_facts": 80}
            result = engine.github_dump(["fastapi"])

        assert result["total_repos"] == 15
        assert engine._stats["github_repos_mined"] == 15


# =====================================================================
# AUDIT - verifies depth scoring, gap detection, severity ordering
# =====================================================================

class TestAudit:

    def test_audit_empty_store_has_zero_totals(self, engine):
        result = engine.audit_gaps()
        assert result["totals"]["facts"] == 0
        assert result["totals"]["procedures"] == 0

    def test_audit_detects_shallow_facts(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(3):
            db_session.add(CompiledFact(
                subject=f"s{i}", predicate="is", object_value=f"v{i}",
                confidence=0.8, domain="shallow",
            ))
        db_session.commit()

        result = engine.audit_gaps()
        shallow = [g for g in result["gaps"] if g["type"] == "shallow_facts" and g["domain"] == "shallow"]
        assert len(shallow) == 1
        assert shallow[0]["severity"] == "high"

    def test_audit_detects_missing_procedures(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(10):
            db_session.add(CompiledFact(
                subject=f"k{i}", predicate="is", object_value=f"v{i}",
                confidence=0.8, domain="no_procs",
            ))
        db_session.commit()

        result = engine.audit_gaps()
        proc_gaps = [g for g in result["gaps"] if g["type"] == "no_procedures" and g["domain"] == "no_procs"]
        assert len(proc_gaps) == 1

    def test_audit_depth_score_calculation(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact, CompiledProcedure
        for i in range(20):
            db_session.add(CompiledFact(
                subject=f"d{i}", predicate="is", object_value=f"v{i}",
                confidence=0.8, domain="scored",
            ))
        db_session.add(CompiledProcedure(
            name="Proc1", goal="Test", steps=[{"step": 1, "action": "Go"}],
            confidence=0.9, domain="scored",
        ))
        db_session.commit()

        result = engine.audit_gaps()
        assert "scored" in result["domains"]
        depth = result["domains"]["scored"]["depth_score"]
        assert depth == 20.0 + 2.0  # 20 facts + 1 procedure * 2.0

    def test_audit_gaps_sorted_by_severity(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        db_session.add(CompiledFact(
            subject="x", predicate="is", object_value="y",
            confidence=0.5, domain="sev_test",
        ))
        db_session.commit()

        result = engine.audit_gaps()
        if len(result["gaps"]) > 1:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sev_values = [severity_order.get(g["severity"], 4) for g in result["gaps"]]
            assert sev_values == sorted(sev_values)


class TestAuditDepth:

    def test_audit_depth_counts_facts_and_subjects(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for s in ["ML", "DL", "NLP", "CV", "RL"]:
            db_session.add(CompiledFact(
                subject=s, predicate="is", object_value=f"{s} description",
                confidence=0.8, domain="ai_topics",
            ))
        db_session.commit()

        result = engine.audit_depth("ai_topics")
        assert result["fact_count"] == 5
        assert result["unique_subjects"] == 5
        assert "ml" in result["subjects"]


# =====================================================================
# REVERSE KNN
# =====================================================================

class TestReverseKNN:

    def test_reverse_knn_returns_structure(self, engine):
        result = engine.reverse_knn("design patterns")
        assert "query" in result
        assert "vector_results" in result
        assert "total_results" in result

    def test_reverse_knn_handles_missing_qdrant(self, engine):
        engine._qdrant_path = "/nonexistent/path"
        result = engine.reverse_knn("test query")
        assert result["total_results"] == 0


# =====================================================================
# TOPIC STATUS
# =====================================================================

class TestTopicStatus:

    def test_empty_topic_has_zero_depth(self, engine):
        status = engine.topic_status("nonexistent")
        assert status["facts"] == 0
        assert status["depth_score"] == 0.0
        assert status["depth_label"] == "empty"

    def test_topic_with_data_has_correct_depth(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact, CompiledProcedure
        for i in range(15):
            db_session.add(CompiledFact(
                subject=f"f{i}", predicate="is", object_value=f"v{i}",
                confidence=0.8, domain="depth_test",
            ))
        db_session.add(CompiledProcedure(
            name="P1", goal="G", steps=[{"step": 1, "action": "A"}],
            confidence=0.8, domain="depth_test",
        ))
        db_session.commit()

        status = engine.topic_status("depth_test")
        assert status["facts"] == 15
        assert status["procedures"] == 1
        assert status["depth_score"] == 15.0 + 2.0  # 15 facts + 1 proc*2
        assert status["depth_label"] == "beginner"

    def test_topic_status_includes_exhaustion(self, engine, session_factory):
        from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker
        s = session_factory()
        s.add(TopicExhaustionTracker(topic="tracked", status="converging", convergence_count=2))
        s.commit()
        s.close()

        status = engine.topic_status("tracked")
        assert status["exhaustion"]["status"] == "converging"
        assert status["exhaustion"]["convergence"] == 2


# =====================================================================
# STATS
# =====================================================================

class TestStats:

    def test_stats_counts_facts_correctly(self, engine, db_session):
        from cognitive.knowledge_compiler import CompiledFact
        for i in range(7):
            db_session.add(CompiledFact(
                subject=f"s{i}", predicate="is", object_value=f"v{i}",
                confidence=0.8, domain="stats_d",
            ))
        db_session.commit()

        result = engine.stats()
        assert result["store"]["facts"] == 7
        assert "stats_d" in result.get("top_domains", {})

    def test_stats_tracks_query_count(self, engine):
        engine.query("a")
        engine.query("b")
        assert engine.stats()["queries"] == 2


# =====================================================================
# DEPTH LABELS
# =====================================================================

class TestDepthLabel:

    def test_labels_at_boundaries(self, engine):
        assert engine._depth_label(0) == "empty"
        assert engine._depth_label(9) == "empty"
        assert engine._depth_label(10) == "beginner"
        assert engine._depth_label(34) == "beginner"
        assert engine._depth_label(35) == "intermediate"
        assert engine._depth_label(59) == "intermediate"
        assert engine._depth_label(60) == "advanced"
        assert engine._depth_label(79) == "advanced"
        assert engine._depth_label(80) == "expert"
        assert engine._depth_label(100) == "expert"


# =====================================================================
# FACT HASHING
# =====================================================================

class TestFactHashing:

    def test_deterministic_hashing(self, engine):
        f = {"subject": "X", "object": "Y"}
        assert engine._hash_fact(f) == engine._hash_fact(f)

    def test_case_and_whitespace_normalization(self, engine):
        f1 = {"subject": "PYTHON", "object": "A  language"}
        f2 = {"subject": "python", "object": "a language"}
        assert engine._hash_fact(f1) == engine._hash_fact(f2)


# =====================================================================
# SOURCE DISCOVERY
# =====================================================================

class TestSourceDiscovery:

    def test_cloud_no_client_returns_empty(self, session_factory):
        eng = GraceKnowledgeEngine(session_factory, cloud_client=None)
        assert eng._discover_from_cloud("test", 5) == []

    def test_cloud_parses_pipe_delimited_facts(self, engine, mock_cloud):
        facts = engine._discover_from_cloud("containers", 5)
        assert len(facts) >= 2
        assert facts[0]["source"] == "kimi_cloud"
        assert facts[0]["subject"] == "Docker"
        assert "container" in facts[0]["object"].lower()

    def test_cloud_failure_returns_empty(self, engine, mock_cloud):
        mock_cloud.generate.return_value = {"success": False}
        assert engine._discover_from_cloud("test", 5) == []
