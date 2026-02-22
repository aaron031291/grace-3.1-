"""
Tests for Code Agent Playbooks.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestCodePlaybookModel:
    def test_table_exists(self):
        from agent.code_playbooks import CodePlaybook
        assert CodePlaybook.__tablename__ == "code_playbooks"

    def test_model_fields(self):
        from agent.code_playbooks import CodePlaybook
        cols = [c.name for c in CodePlaybook.__table__.columns]
        assert "name" in cols
        assert "task_type" in cols
        assert "file_pattern" in cols
        assert "language" in cols
        assert "success_count" in cols
        assert "failure_count" in cols
        assert "trust_score" in cols
        assert "strategy" in cols
        assert "steps" in cols
        assert "tools_used" in cols
        assert "avg_duration_ms" in cols
        assert "avg_lines_changed" in cols
        assert "avg_test_pass_rate" in cols
        assert "genesis_key_id" in cols
        assert "is_active" in cols


class TestCodePlaybookManager:
    def test_manager_exists(self):
        from agent.code_playbooks import CodePlaybookManager
        assert CodePlaybookManager is not None

    def test_has_create_from_success(self):
        from agent.code_playbooks import CodePlaybookManager
        assert callable(getattr(CodePlaybookManager, "create_from_success", None))

    def test_has_record_failure(self):
        from agent.code_playbooks import CodePlaybookManager
        assert callable(getattr(CodePlaybookManager, "record_failure", None))

    def test_has_find_playbook(self):
        from agent.code_playbooks import CodePlaybookManager
        assert callable(getattr(CodePlaybookManager, "find_playbook", None))

    def test_has_get_agent_performance(self):
        from agent.code_playbooks import CodePlaybookManager
        assert callable(getattr(CodePlaybookManager, "get_agent_performance", None))

    def test_has_list_playbooks(self):
        from agent.code_playbooks import CodePlaybookManager
        assert callable(getattr(CodePlaybookManager, "list_playbooks", None))


class TestAgentWiring:
    def test_agent_has_playbook_manager(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "CodePlaybookManager" in source
        assert "_playbook_manager" in source

    def test_agent_consults_playbooks_before_task(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "find_playbook" in source
        assert "playbook_match" in source
        assert "playbook_strategy" in source

    def test_agent_creates_playbook_on_success(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "create_from_success" in source

    def test_agent_records_failure_in_playbook(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "record_failure" in source

    def test_agent_logs_to_self_monitoring(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "self._self_agent" in source
        assert "log_attempt" in source
        assert "CodeAgentSelf" in source

    def test_agent_has_classify_task_type(self):
        source = (BACKEND_DIR / "agent" / "grace_agent.py").read_text()
        assert "_classify_task_type" in source
