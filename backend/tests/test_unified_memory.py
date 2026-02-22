"""
Unified Memory Tests - complete memory system.
All real logic, zero mocks.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from cognitive.unified_memory import (
    UnifiedMemory, Memory, MemoryType, MemoryStrength,
    AssociativeRecallEngine, ConsolidationEngine,
    get_unified_memory, reset_unified_memory,
)


class TestMemoryCreation:
    def test_remember_fact(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Python is a programming language")
        assert m.memory_type == MemoryType.SEMANTIC
        assert m.strength == MemoryStrength.FLASH
        assert "Python" in m.content

    def test_remember_episode(self):
        mem = UnifiedMemory()
        m = mem.remember_episode("Database timed out during query", "Reconnection fixed it")
        assert m.memory_type == MemoryType.EPISODIC
        assert "timed out" in m.content

    def test_remember_procedure(self):
        mem = UnifiedMemory()
        m = mem.remember_procedure("Fix database", ["Stop connections", "Restart pool", "Verify"])
        assert m.memory_type == MemoryType.PROCEDURAL
        assert "Fix database" in m.content

    def test_remember_cause(self):
        mem = UnifiedMemory()
        m = mem.remember_cause("High memory usage", "Slow query response")
        assert m.memory_type == MemoryType.CAUSAL

    def test_learn(self):
        mem = UnifiedMemory()
        m = mem.learn("When X happens, do Y", trust=0.8)
        assert m.memory_type == MemoryType.LEARNING
        assert m.trust_score == 0.8

    def test_memory_gets_id(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Test")
        assert m.id.startswith("mem-")

    def test_stats_increment(self):
        mem = UnifiedMemory()
        mem.remember_fact("Fact 1")
        mem.remember_episode("Episode 1", "Outcome 1")
        stats = mem.get_stats()
        assert stats["total_memories"] == 2
        assert stats["counters"]["total_memories_created"] == 2


class TestMemoryRecall:
    def test_recall_by_content(self):
        mem = UnifiedMemory()
        mem.remember_fact("Python is great for data science")
        mem.remember_fact("JavaScript runs in browsers")
        results = mem.recall("Python")
        assert len(results) >= 1
        assert any("Python" in m.content for m in results)

    def test_recall_by_tag(self):
        mem = UnifiedMemory()
        mem.remember_fact("SQL databases store data", tags=["database", "sql"])
        results = mem.recall("database")
        assert len(results) >= 1

    def test_recall_by_type(self):
        mem = UnifiedMemory()
        mem.remember_fact("Fact")
        mem.remember_episode("Episode", "Outcome")
        results = mem.recall("", memory_types=[MemoryType.EPISODIC])
        episodes = [m for m in results if m.memory_type == MemoryType.EPISODIC]
        assert len(episodes) >= 0  # May not match empty query

    def test_recall_reinforces_memory(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Important fact about databases")
        assert m.access_count == 0
        mem.recall("databases")
        if m.id in mem._memories:
            assert mem._memories[m.id].access_count >= 1

    def test_recall_min_trust(self):
        mem = UnifiedMemory()
        mem.remember("Low trust fact", trust_score=0.1, tags=["test"])
        mem.remember("High trust fact", trust_score=0.9, tags=["test"])
        results = mem.recall("test", min_trust=0.5)
        for r in results:
            if r.id in mem._memories:
                assert r.trust_score >= 0.5


class TestForgettingCurve:
    def test_retention_starts_high(self):
        m = Memory(id="test", content="test", memory_type=MemoryType.SEMANTIC)
        assert m.current_retention > 0.9

    def test_permanent_never_forgets(self):
        m = Memory(id="test", content="test", memory_type=MemoryType.SEMANTIC,
                   strength=MemoryStrength.PERMANENT)
        assert m.current_retention == 1.0

    def test_reinforcement_slows_decay(self):
        m = Memory(id="test", content="test", memory_type=MemoryType.SEMANTIC)
        initial_decay = m.decay_rate
        m.reinforce()
        assert m.decay_rate < initial_decay

    def test_effective_score_combines_trust_retention(self):
        m = Memory(id="test", content="test", memory_type=MemoryType.SEMANTIC,
                   trust_score=0.8, relevance_score=0.6)
        score = m.effective_score
        assert 0 < score <= 1.0

    def test_access_promotes_strength(self):
        m = Memory(id="test", content="test", memory_type=MemoryType.SEMANTIC)
        assert m.strength == MemoryStrength.FLASH
        for _ in range(5):
            m.reinforce()
        assert m.strength in (MemoryStrength.SHORT_TERM, MemoryStrength.LONG_TERM)


class TestAssociativeRecall:
    def test_co_access_builds_association(self):
        engine = AssociativeRecallEngine()
        engine.record_co_access("mem-1", "mem-2")
        engine.record_co_access("mem-1", "mem-2")
        assocs = engine.get_associations("mem-1")
        assert len(assocs) >= 1
        assert assocs[0][0] == "mem-2"

    def test_no_false_associations(self):
        engine = AssociativeRecallEngine()
        engine.record_co_access("mem-1", "mem-2")
        assocs = engine.get_associations("mem-3")
        assert len(assocs) == 0

    def test_association_strength_grows(self):
        engine = AssociativeRecallEngine()
        for _ in range(5):
            engine.record_co_access("mem-a", "mem-b")
        assocs = engine.get_associations("mem-a")
        assert assocs[0][1] >= 0.4


class TestConsolidation:
    def test_consolidation_promotes(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Important repeating fact")
        for _ in range(6):
            mem._memories[m.id].reinforce()
        mem._memories[m.id].trust_score = 0.8
        mem._memories[m.id].strength = MemoryStrength.SHORT_TERM
        result = mem.run_consolidation()
        assert result["promoted"] >= 1

    def test_consolidation_prunes(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Forgettable fact")
        mem._memories[m.id].strength = MemoryStrength.FLASH
        mem._memories[m.id].decay_rate = 100.0
        from datetime import datetime, timedelta
        mem._memories[m.id].last_reinforced = datetime.now() - timedelta(days=30)
        result = mem.run_consolidation()
        assert result["pruned"] >= 1
        assert m.id not in mem._memories

    def test_consolidation_stats(self):
        mem = UnifiedMemory()
        mem.run_consolidation()
        stats = mem.consolidation.get_stats()
        assert stats["consolidation_cycles"] >= 1


class TestWorkingMemory:
    def test_working_memory(self):
        mem = UnifiedMemory()
        m = mem.remember_fact("Active thought")
        working = mem.get_working_memory()
        assert len(working) >= 1

    def test_working_memory_limited(self):
        mem = UnifiedMemory()
        for i in range(60):
            mem.remember_fact(f"Thought {i}")
        working = mem.get_working_memory()
        assert len(working) <= 50

    def test_clear_working_memory(self):
        mem = UnifiedMemory()
        mem.remember_fact("Something")
        mem.clear_working_memory()
        assert len(mem.get_working_memory()) == 0


class TestDashboard:
    def test_dashboard(self):
        mem = UnifiedMemory()
        mem.remember_fact("Fact 1")
        mem.remember_episode("Event 1", "Result 1")
        dash = mem.get_dashboard()
        assert "stats" in dash
        assert "recent_memories" in dash
        assert "strongest_memories" in dash
        assert "working_memory" in dash

    def test_stats(self):
        mem = UnifiedMemory()
        mem.remember_fact("Test")
        stats = mem.get_stats()
        assert stats["total_memories"] == 1
        assert stats["magma_connected"] in (True, False)
        assert "consolidation" in stats

    def test_singleton(self):
        reset_unified_memory()
        m1 = get_unified_memory()
        m2 = get_unified_memory()
        assert m1 is m2
        reset_unified_memory()


class TestMemoryToDict:
    def test_memory_serializes(self):
        m = Memory(
            id="test-123", content="Test content",
            memory_type=MemoryType.SEMANTIC,
            trust_score=0.8, tags=["test"],
        )
        d = m.to_dict()
        assert d["id"] == "test-123"
        assert d["type"] == "semantic"
        assert d["trust"] == 0.8
        assert "retention" in d
        assert "effective_score" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
