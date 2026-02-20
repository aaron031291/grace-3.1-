"""
FAILURE RESILIENCE TESTS

Tests what happens when things go WRONG:
- Null/None/empty inputs
- Corrupted data
- Services unavailable
- Timeouts
- Invalid types
- Boundary conditions
- Concurrent access
- Resource exhaustion
- Malicious inputs
- Cascade failures

The system should NEVER crash. It should degrade gracefully.
Zero warnings, zero skips.
"""

import sys
import os
import time
import threading
import hashlib
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BD = Path(__file__).parent.parent


# ============================================================================
# NULL / NONE / EMPTY INPUTS
# ============================================================================

class TestNullInputs:
    """Every component must handle None/empty without crashing."""

    def test_ambiguity_none_query(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        assert ci.detect_ambiguity(None) is None
        assert ci.detect_ambiguity("") is None

    def test_ambiguity_whitespace_only(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        assert ci.detect_ambiguity("   ") is None

    def test_governance_empty_text(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("")
        assert result is not None
        assert "passed" in result

    def test_routing_empty_query(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter
        r = ReasoningRouter()
        d = r.classify("")
        assert d is not None
        assert d.tier is not None

    def test_dedup_empty_content(self):
        from cognitive.deduplication_engine import DeduplicationEngine
        de = DeduplicationEngine()
        dup, h = de.check_file_duplicate(content=b"")
        assert dup is False

    def test_dedup_none_path(self):
        from cognitive.deduplication_engine import DeduplicationEngine
        de = DeduplicationEngine()
        dup, h = de.check_file_duplicate(file_path=None, content=None)
        assert dup is False

    def test_genesis_router_empty_prompt(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        r = GenesisHashRouter()
        assert r.route("") is None
        assert r.route(None) is None
        assert r.has_genesis_ref("") is False
        assert r.has_genesis_ref(None) is False

    def test_chunker_empty_text(self):
        from ingestion.service import TextChunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk_text("")
        assert chunks == [] or len(chunks) == 0

    def test_enrichment_all_none(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.enrich_response("Original.", None, None)
        assert result == "Original."

    def test_hash_empty_string(self):
        from ingestion.service import TextIngestionService
        h = TextIngestionService.compute_file_hash("")
        assert len(h) == 64

    def test_organizer_empty_filename(self):
        from librarian.knowledge_organizer import KnowledgeOrganizer
        org = KnowledgeOrganizer()
        result = org.classify_document("", "")
        assert result == "general"

    def test_hia_empty_text(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score, violations = HonestyEnforcer.check_output("")
        assert 0 <= score <= 1.0

    def test_safety_validator_empty(self):
        from security.governance_middleware import OutputSafetyValidator
        result = OutputSafetyValidator.validate("")
        assert result is not None
        assert "safe" in result


# ============================================================================
# CORRUPTED / INVALID DATA
# ============================================================================

class TestCorruptedData:
    """System must handle bad data without crashing."""

    def test_chunker_binary_garbage(self):
        from ingestion.service import TextChunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        garbage = "\x00\x01\x02\xff\xfe" * 100
        chunks = chunker.chunk_text(garbage)
        assert isinstance(chunks, list)

    def test_unicode_in_ambiguity(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("这是中文测试 🎉 émojis and spëcial çhars")
        assert result is None or isinstance(result, dict)

    def test_unicode_in_governance(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("Ünïcödé tëxt with 日本語 and العربية")
        assert result is not None

    def test_very_long_text_in_routing(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter
        r = ReasoningRouter()
        long_query = "word " * 10000
        d = r.classify(long_query)
        assert d is not None

    def test_special_chars_in_genesis_ref(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        r = GenesisHashRouter()
        refs = r.detect_genesis_refs("Genesis#valid_ref but also Genesis#<script>alert(1)</script>")
        assert isinstance(refs, list)

    def test_negative_numbers_in_sla(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.record("test.negative", -100.0, "test")
        assert gov.stats["total_operations"] == 1

    def test_zero_division_in_kpi(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_kpi_integrity(0.0, 0, 0)
        assert isinstance(score, float)

    def test_extreme_trust_scores(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score1, _ = IntegrityEnforcer.check_trust_consistency(0.0, 0, 0)
        score2, _ = IntegrityEnforcer.check_trust_consistency(1.0, 1000, 0)
        score3, _ = IntegrityEnforcer.check_trust_consistency(0.5, 50, 50)
        assert all(0 <= s <= 1.0 for s in [score1, score2, score3])


# ============================================================================
# BOUNDARY CONDITIONS
# ============================================================================

class TestBoundaryConditions:
    """Test edge cases and limits."""

    def test_single_char_query(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("x")
        assert result is None or isinstance(result, dict)

    def test_single_word_classification(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter
        r = ReasoningRouter()
        d = r.classify("x")
        assert d.tier is not None

    def test_max_depth_pipeline(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(max_depth=0)
        result = engine.expand_from_seed("test")
        assert result.neighbors_found == 0

    def test_max_nodes_zero(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine(max_total_nodes=0)
        graph = engine.get_knowledge_graph()
        assert graph["total_nodes"] == 0

    def test_sla_exact_threshold(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("test.exact", max_ms=100, warn_ms=50, critical_ms=150)
        gov.record("test.exact", 100.0)  # Exactly at max = warning (above warn, at max)
        assert gov.stats["total_warnings"] == 1

    def test_dedup_same_hash_different_content(self):
        from cognitive.deduplication_engine import DeduplicationEngine
        de = DeduplicationEngine()
        de.check_file_duplicate(content=b"content_a")
        dup, _ = de.check_file_duplicate(content=b"content_a")
        assert dup is True
        dup2, _ = de.check_file_duplicate(content=b"content_b")
        assert dup2 is False

    def test_audit_trail_memory_limit(self):
        from security.governance_middleware import AuditTrailManager
        manager = AuditTrailManager(max_trail_size=3)
        for i in range(10):
            manager.record(f"a{i}", f"q{i}", f"r{i}", {"safe": True, "violations": []})
        assert len(manager._trail) <= 3

    def test_swarm_bus_max_feed(self):
        from cognitive.swarm_comms import SwarmCommBus, SwarmMessage
        bus = SwarmCommBus(max_feed_size=5)
        for i in range(20):
            bus.post(SwarmMessage(sender="a", message_type="discovery", topic=f"t{i}"))
        recent = bus.get_recent(100)
        assert len(recent) <= 5


# ============================================================================
# CONCURRENT ACCESS
# ============================================================================

class TestConcurrency:
    """Test thread safety under concurrent access."""

    def test_dedup_concurrent_access(self):
        from cognitive.deduplication_engine import DeduplicationEngine
        de = DeduplicationEngine()
        results = []

        def check(content):
            dup, h = de.check_file_duplicate(content=content)
            results.append((content, dup))

        threads = [threading.Thread(target=check, args=(f"content_{i}".encode(),)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(results) == 20
        non_dup = [r for r in results if not r[1]]
        assert len(non_dup) == 20

    def test_swarm_bus_concurrent_posts(self):
        from cognitive.swarm_comms import SwarmCommBus, SwarmMessage
        bus = SwarmCommBus()

        def post(sender, count):
            for i in range(count):
                bus.post(SwarmMessage(sender=sender, message_type="discovery", topic=f"{sender}_{i}"))

        threads = [
            threading.Thread(target=post, args=("agent_a", 10)),
            threading.Thread(target=post, args=("agent_b", 10)),
            threading.Thread(target=post, args=("agent_c", 10)),
        ]
        for t in threads: t.start()
        for t in threads: t.join()

        recent = bus.get_recent(100)
        assert len(recent) == 30

    def test_task_log_concurrent_writes(self):
        from cognitive.swarm_comms import SharedTaskLog, TaskLogEntry
        log = SharedTaskLog()

        def log_tasks(agent, count):
            for i in range(count):
                log.log_task(TaskLogEntry(
                    task_type="search", topic=f"{agent}_topic_{i}",
                    agent=agent, status="completed"
                ))

        threads = [
            threading.Thread(target=log_tasks, args=("a", 20)),
            threading.Thread(target=log_tasks, args=("b", 20)),
        ]
        for t in threads: t.start()
        for t in threads: t.join()

        stats = log.get_stats()
        assert stats["total_entries"] == 40

    def test_timesense_concurrent_records(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()

        def record(n):
            for i in range(n):
                gov.record(f"test.concurrent_{i}", float(i), "test")

        threads = [threading.Thread(target=record, args=(50,)) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert gov.stats["total_operations"] == 200


# ============================================================================
# MALICIOUS INPUTS
# ============================================================================

class TestMaliciousInputs:
    """Test security against injection and attacks."""

    def test_sql_injection_in_query(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.detect_ambiguity("'; DROP TABLE users; --")
        assert result is None or isinstance(result, dict)

    def test_xss_in_governance(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        result = ci.check_governance("<script>alert('xss')</script>")
        assert result is not None

    def test_path_traversal_in_organizer(self):
        from librarian.knowledge_organizer import KnowledgeOrganizer
        org = KnowledgeOrganizer()
        result = org.classify_document("../../../etc/passwd", "root:x:0:0")
        assert result is not None

    def test_massive_input_doesnt_crash(self):
        from cognitive.chat_intelligence import ChatIntelligence
        ci = ChatIntelligence()
        huge = "A" * 1000000
        result = ci.detect_ambiguity(huge)
        assert result is None or isinstance(result, dict)

    def test_null_bytes_handled(self):
        from ingestion.service import TextChunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        text_with_nulls = "Hello\x00World\x00Test" * 10
        chunks = chunker.chunk_text(text_with_nulls)
        assert isinstance(chunks, list)


# ============================================================================
# GRACEFUL DEGRADATION
# ============================================================================

class TestGracefulDegradation:
    """Test that missing services don't crash the system."""

    def test_kimi_feedback_without_ingestion(self):
        from cognitive.kimi_knowledge_feedback import KimiKnowledgeFeedback
        fb = KimiKnowledgeFeedback()
        # Without a running ingestion service, should fail gracefully
        result = fb.feed_answer("test?", "A" * 300, confidence=0.9)
        assert result is False or result is True  # Either works, but doesn't crash

    def test_pipeline_without_retriever(self):
        from cognitive.unified_learning_pipeline import NeighborByNeighborEngine
        engine = NeighborByNeighborEngine()
        result = engine.expand_from_seed("test", "test text")
        assert result.neighbors_found == 0  # No retriever = no neighbors, but no crash

    def test_author_discovery_report_always_works(self):
        from cognitive.author_discovery_engine import get_author_discovery_engine
        engine = get_author_discovery_engine()
        report = engine.get_report()
        assert isinstance(report, dict)
        assert "top_authors" in report

    def test_handshake_status_without_db(self):
        from genesis.handshake_protocol import HandshakeProtocol
        proto = HandshakeProtocol()
        status = proto.get_status()
        assert isinstance(status, dict)
        assert "running" in status

    def test_timesense_without_engine(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.record("test.no_engine", 100.0, "test")
        assert gov.stats["total_operations"] == 1

    def test_organizer_coverage_without_files(self):
        from librarian.knowledge_organizer import KnowledgeOrganizer
        org = KnowledgeOrganizer(kb_path="/tmp/nonexistent_kb_path_xyz")
        report = org.get_coverage_report()
        assert isinstance(report, dict)
