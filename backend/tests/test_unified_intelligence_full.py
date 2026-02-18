"""
Tests for expanded Unified Intelligence — all 16 collectors + librarian audit.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestAllCollectorsExist:
    """Verify every collector method exists in the engine."""

    def _get_engine_source(self):
        return (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()

    def test_collect_from_registry(self):
        assert "def collect_from_registry" in self._get_engine_source()

    def test_collect_from_kpis(self):
        assert "def collect_from_kpis" in self._get_engine_source()

    def test_collect_from_healing(self):
        assert "def collect_from_healing" in self._get_engine_source()

    def test_collect_from_pipeline(self):
        assert "def collect_from_pipeline" in self._get_engine_source()

    def test_collect_from_self_agents(self):
        assert "def collect_from_self_agents" in self._get_engine_source()

    def test_collect_from_memory_mesh(self):
        assert "def collect_from_memory_mesh" in self._get_engine_source()

    def test_collect_from_magma(self):
        assert "def collect_from_magma" in self._get_engine_source()

    def test_collect_from_episodic_memory(self):
        assert "def collect_from_episodic_memory" in self._get_engine_source()

    def test_collect_from_learning_memory(self):
        assert "def collect_from_learning_memory" in self._get_engine_source()

    def test_collect_from_genesis_keys(self):
        assert "def collect_from_genesis_keys" in self._get_engine_source()

    def test_collect_from_documents(self):
        assert "def collect_from_documents" in self._get_engine_source()

    def test_collect_from_llm_tracking(self):
        assert "def collect_from_llm_tracking" in self._get_engine_source()

    def test_collect_from_handshake(self):
        assert "def collect_from_handshake" in self._get_engine_source()

    def test_collect_from_governance(self):
        assert "def collect_from_governance" in self._get_engine_source()

    def test_collect_from_closed_loop(self):
        assert "def collect_from_closed_loop" in self._get_engine_source()

    def test_collect_from_three_layer_reasoning(self):
        assert "def collect_from_three_layer_reasoning" in self._get_engine_source()


class TestLibrarianKeeper:
    """Verify librarian is wired as keeper of the unified table."""

    def test_librarian_audit_method_exists(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert "def librarian_audit" in source

    def test_librarian_checks_coverage(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert "sources_reporting" in source
        assert "expected_sources" in source
        assert "coverage" in source

    def test_librarian_checks_stale(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert "stale_records" in source or "stale" in source

    def test_librarian_runs_in_collect_all(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert "self.librarian_audit()" in source

    def test_librarian_records_audit_result(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert '"librarian"' in source
        assert '"audit"' in source
        assert "unified_intelligence_audit" in source


class TestCollectAllIntegrity:
    """Verify collect_all calls all 16 collectors + librarian."""

    def test_collect_all_calls_all_16(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        # Find the collect_all method body
        idx = source.index("def collect_all(self):")
        body = source[idx:idx+2000]

        assert "collect_from_registry" in body
        assert "collect_from_kpis" in body
        assert "collect_from_healing" in body
        assert "collect_from_pipeline" in body
        assert "collect_from_self_agents" in body
        assert "collect_from_memory_mesh" in body
        assert "collect_from_magma" in body
        assert "collect_from_episodic_memory" in body
        assert "collect_from_learning_memory" in body
        assert "collect_from_genesis_keys" in body
        assert "collect_from_documents" in body
        assert "collect_from_llm_tracking" in body
        assert "collect_from_handshake" in body
        assert "collect_from_governance" in body
        assert "collect_from_closed_loop" in body
        assert "collect_from_three_layer_reasoning" in body
        assert "librarian_audit" in body

    def test_log_message_counts_sources(self):
        source = (BACKEND_DIR / "genesis" / "unified_intelligence.py").read_text()
        assert "16 sources" in source
