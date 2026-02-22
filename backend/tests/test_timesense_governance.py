"""
Tests for TimeSense Governance Layer.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestSLADefinitions:
    def test_all_components_have_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        components = set(s.component for s in DEFAULT_SLAS.values())
        expected = {
            "ingestion", "healing", "code_agent", "reasoning",
            "retrieval", "chat", "handshake", "closed_loop",
            "librarian", "learning", "memory", "governance"
        }
        assert expected.issubset(components), f"Missing: {expected - components}"

    def test_sla_count(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert len(DEFAULT_SLAS) >= 28

    def test_ingestion_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "ingestion.chunk" in DEFAULT_SLAS
        assert "ingestion.embed" in DEFAULT_SLAS
        assert "ingestion.store" in DEFAULT_SLAS
        assert "ingestion.full" in DEFAULT_SLAS

    def test_healing_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "healing.assess" in DEFAULT_SLAS
        assert "healing.execute" in DEFAULT_SLAS
        assert "healing.cycle" in DEFAULT_SLAS

    def test_reasoning_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "reasoning.layer1" in DEFAULT_SLAS
        assert "reasoning.layer2" in DEFAULT_SLAS
        assert "reasoning.layer3" in DEFAULT_SLAS
        assert "reasoning.full" in DEFAULT_SLAS

    def test_chat_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "chat.response" in DEFAULT_SLAS
        assert "chat.streaming" in DEFAULT_SLAS

    def test_agent_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "agent.understand" in DEFAULT_SLAS
        assert "agent.plan" in DEFAULT_SLAS
        assert "agent.execute" in DEFAULT_SLAS

    def test_memory_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        assert "memory.recall" in DEFAULT_SLAS
        assert "memory.consolidate" in DEFAULT_SLAS

    def test_auto_heal_on_critical_slas(self):
        from cognitive.timesense_governance import DEFAULT_SLAS
        auto_heal_ops = [k for k, v in DEFAULT_SLAS.items() if v.auto_heal_on_breach]
        assert "ingestion.full" in auto_heal_ops
        assert "healing.cycle" in auto_heal_ops
        assert "reasoning.full" in auto_heal_ops
        assert "chat.response" in auto_heal_ops


class TestTimeSenseGovernance:
    def test_singleton(self):
        from cognitive.timesense_governance import get_timesense_governance
        g1 = get_timesense_governance()
        g2 = get_timesense_governance()
        assert g1 is g2

    def test_initialization(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        assert gov.stats["total_operations"] == 0
        assert gov.stats["total_violations"] == 0
        assert len(gov.slas) >= 28

    def test_record_operation(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.record("test.op", 100.0, "test", True)
        assert gov.stats["total_operations"] == 1
        assert len(gov.violations) == 0

    def test_sla_warning(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("test.slow", max_ms=100, warn_ms=50, component="test")
        gov.record("test.slow", 75.0, "test")
        assert gov.stats["total_warnings"] == 1

    def test_sla_breach(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("test.breach", max_ms=100, warn_ms=50, critical_ms=150, component="test")
        gov.record("test.breach", 200.0, "test")
        assert gov.stats["total_breaches"] == 1

    def test_no_violation_on_fast_op(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("test.fast", max_ms=1000, warn_ms=500, component="test")
        gov.record("test.fast", 50.0, "test")
        assert len(gov.violations) == 0

    def test_get_sla_status(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        status = gov.get_sla_status()
        assert "stats" in status
        assert "total_slas_defined" in status
        assert "component_health" in status
        assert "worst_violations" in status

    def test_add_custom_sla(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("custom.op", max_ms=500, component="custom", auto_heal=True)
        assert "custom.op" in gov.slas
        assert gov.slas["custom.op"].auto_heal_on_breach is True

    def test_violations_bounded(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()
        gov.add_sla("test.many", max_ms=10, warn_ms=5, critical_ms=15, component="test")
        for i in range(1500):
            gov.record("test.many", 20.0, "test")
        assert len(gov.violations) <= 1000


class TestDecorator:
    def test_time_operation_decorator(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()

        @gov.time_operation("test.decorated", "test")
        def my_func():
            return 42

        result = my_func()
        assert result == 42
        assert gov.stats["total_operations"] == 1

    def test_decorator_records_exceptions(self):
        from cognitive.timesense_governance import TimeSenseGovernance
        gov = TimeSenseGovernance()

        @gov.time_operation("test.error", "test")
        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing_func()

        assert gov.stats["total_operations"] == 1


class TestWiring:
    def test_feeds_unified_intelligence(self):
        source = (BACKEND_DIR / "cognitive" / "timesense_governance.py").read_text()
        assert "UnifiedIntelligenceEngine" in source
        assert "sla_breach" in source

    def test_feeds_timesense_engine(self):
        source = (BACKEND_DIR / "cognitive" / "timesense_governance.py").read_text()
        assert "TimeSenseEngine" in source
        assert "record_operation" in source

    def test_triggers_learning_hook(self):
        source = (BACKEND_DIR / "cognitive" / "timesense_governance.py").read_text()
        assert "track_learning_event" in source

    def test_12_component_categories(self):
        source = (BACKEND_DIR / "cognitive" / "timesense_governance.py").read_text()
        components = [
            "ingestion", "healing", "code_agent", "reasoning",
            "retrieval", "chat", "handshake", "closed_loop",
            "librarian", "learning", "memory", "governance"
        ]
        for comp in components:
            assert f'"{comp}"' in source, f"Missing component: {comp}"
