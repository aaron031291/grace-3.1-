"""
Logic tests for core.services -- chat, code, data, files, govern,
system, workspace, tasks, project.

All external deps (DB, LLM, file system, subprocess) are mocked.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from backend.core.services import (
    code_service,
    data_service,
    files_service,
    govern_service,
    system_service,
    tasks_service,
    project_service,
    chat_service,
    workspace_service,
)


# ---- chat_service ----

class TestChatServiceListChats:
    def test_list_chats_returns_formatted(self):
        chat = SimpleNamespace(id=1, title="Hello", model="qwen3:14b",
                               created_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
        mock_repo = MagicMock()
        mock_repo.get_all_chats.return_value = [chat]
        mock_repo.count.return_value = 1
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            result = chat_service.list_chats(limit=10)
        assert result["total"] == 1
        assert result["chats"][0]["title"] == "Hello"
        assert result["chats"][0]["created_at"] == "2025-01-01T00:00:00+00:00"

    def test_list_chats_empty(self):
        mock_repo = MagicMock()
        mock_repo.get_all_chats.return_value = []
        mock_repo.count.return_value = 0
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            result = chat_service.list_chats()
        assert result["chats"] == []
        assert result["total"] == 0


class TestChatServiceGetChat:
    def test_get_chat_found(self):
        chat = SimpleNamespace(id=42, title="Test", model="qwen3:14b")
        mock_repo = MagicMock()
        mock_repo.get.return_value = chat
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            result = chat_service.get_chat({"chat_id": 42})
        assert result["id"] == 42

    def test_get_chat_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            result = chat_service.get_chat({"chat_id": 999})
        assert result == {"error": "Chat not found"}


class TestSendPrompt:
    def test_send_prompt_no_rag_returns_response(self):
        chat = SimpleNamespace(id=1, model="qwen3:14b", temperature=0.7)
        mock_repo = MagicMock()
        mock_repo.get.return_value = chat
        mock_hist = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.return_value = "Generated answer"
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo), \
             patch("models.repositories.ChatHistoryRepository", return_value=mock_hist), \
             patch("llm_orchestrator.factory.get_llm_client", return_value=mock_client):
            result = chat_service.send_prompt({"chat_id": 1, "message": "hi", "use_rag": False})
        assert result["message"] == "Generated answer"
        assert result["chat_id"] == 1

    def test_send_prompt_no_rag_chat_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo), \
             patch("models.repositories.ChatHistoryRepository", return_value=MagicMock()), \
             patch("llm_orchestrator.factory.get_llm_client", return_value=MagicMock()):
            result = chat_service.send_prompt({"chat_id": 1, "message": "hi", "use_rag": False})
        assert result == {"error": "Chat not found"}


class TestDeleteChat:
    def test_delete_chat(self):
        mock_repo = MagicMock()
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            result = chat_service.delete_chat({"chat_id": 5})
        assert result == {"deleted": True}
        mock_repo.delete.assert_called_once_with(5)

    def test_delete_chat_commits(self):
        mock_repo = MagicMock()
        mock_sess = MagicMock()
        with patch.object(chat_service, "get_session_factory", return_value=MagicMock(return_value=mock_sess)), \
             patch("models.repositories.ChatRepository", return_value=mock_repo):
            chat_service.delete_chat({"chat_id": 10})
        mock_sess.commit.assert_called_once()


# ---- code_service ----

class TestCodeServiceSafe:
    def test_safe_blocks_traversal(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            with pytest.raises(ValueError, match="Path traversal"):
                code_service._safe("../../etc/passwd")

    def test_safe_allows_subpath(self, tmp_path):
        (tmp_path / "sub").mkdir()
        with patch.object(code_service, "_kb", return_value=tmp_path):
            result = code_service._safe("sub")
            assert str(tmp_path / "sub") in str(result)


class TestCodeServiceReadFile:
    def test_read_file_exists(self, tmp_path):
        (tmp_path / "hello.py").write_text("print('hi')")
        with patch.object(code_service, "_kb", return_value=tmp_path):
            result = code_service.read_file("hello.py")
        assert result["content"] == "print('hi')"
        assert result["language"] == "py"

    def test_read_file_not_found(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            result = code_service.read_file("nope.py")
        assert result == {"error": "Not found"}


class TestCodeServiceWriteDelete:
    def test_write_and_delete(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            w = code_service.write_file("test.txt", "data")
            assert w["saved"] is True
            assert (tmp_path / "test.txt").read_text() == "data"
            d = code_service.delete_file("test.txt")
            assert d["deleted"] is True
            assert not (tmp_path / "test.txt").exists()

    def test_delete_not_found(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            result = code_service.delete_file("gone.txt")
        assert result == {"error": "Not found"}


class TestCodeServiceCreateFile:
    def test_create_file_empty(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            result = code_service.create_file("newfile.py", "")
        assert result["created"] is True
        assert (tmp_path / "newfile.py").exists()

    def test_create_file_with_content(self, tmp_path):
        with patch.object(code_service, "_kb", return_value=tmp_path):
            code_service.create_file("code.py", "x = 1")
        assert (tmp_path / "code.py").read_text() == "x = 1"


class TestCodeServiceListProjects:
    def test_list_projects_empty(self, tmp_path):
        with patch.object(code_service, "PROJECTS_META", tmp_path / "projects.json"):
            result = code_service.list_projects()
        assert result == {"projects": []}

    def test_list_projects_with_data(self, tmp_path):
        meta = tmp_path / "projects.json"
        meta.write_text(json.dumps([{"name": "proj1"}]))
        with patch.object(code_service, "PROJECTS_META", meta):
            result = code_service.list_projects()
        assert result["projects"] == [{"name": "proj1"}]


# ---- data_service ----

class TestDataServiceSources:
    def test_add_api_source(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            result = data_service.add_api({"name": "TestAPI", "url": "https://api.test.com"})
            assert result["name"] == "TestAPI"
            assert result["id"].startswith("api-")
            sources = data_service.api_sources()
            assert len(sources["sources"]) == 1

    def test_add_web_source(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            result = data_service.add_web({"name": "TestWeb", "url": "https://web.test.com"})
            assert result["name"] == "TestWeb"
            assert result["id"].startswith("web-")
            sources = data_service.web_sources()
            assert len(sources["sources"]) == 1


class TestDataServiceDelete:
    def test_delete_existing_source(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            src = data_service.add_api({"name": "ToDelete", "url": "http://x"})
            result = data_service.delete_source(src["id"])
            assert result["deleted"] is True

    def test_delete_nonexistent_source(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            result = data_service.delete_source("fake-id")
        assert result == {"error": "Not found"}


class TestDataServiceStats:
    def test_stats_counts(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            data_service.add_api({"name": "A", "url": "http://a"})
            data_service.add_web({"name": "B", "url": "http://b"})
            data_service.add_web({"name": "C", "url": "http://c"})
            result = data_service.stats()
            assert result["api_source_count"] == 1
            assert result["web_source_count"] == 2

    def test_stats_empty(self, tmp_path):
        with patch.object(data_service, "DATA_DIR", tmp_path):
            result = data_service.stats()
            assert result["api_source_count"] == 0
            assert result["web_source_count"] == 0


# ---- files_service ----

class TestFilesServiceTree:
    def test_tree_structure(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file.txt").write_text("x")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.tree()
        assert result["type"] == "directory"
        children_names = [c["name"] for c in result["children"]]
        assert "sub" in children_names

    def test_tree_with_subpath(self, tmp_path):
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "a.txt").write_text("a")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.tree("dir1")
        assert result["name"] == "dir1"


class TestFilesServiceReadWrite:
    def test_read_existing(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Hello")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.read("doc.md")
        assert result["content"] == "# Hello"

    def test_write_creates(self, tmp_path):
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.write("newfile.txt", "content here")
        assert result["saved"] is True
        assert (tmp_path / "newfile.txt").read_text() == "content here"


class TestFilesServiceSearch:
    def test_search_finds_match(self, tmp_path):
        (tmp_path / "note.md").write_text("important keyword here")
        (tmp_path / "other.txt").write_text("nothing special")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.search("keyword")
        assert result["total"] == 1
        assert result["results"][0]["name"] == "note.md"

    def test_search_no_match(self, tmp_path):
        (tmp_path / "note.md").write_text("hello world")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.search("zzzznotfound")
        assert result["total"] == 0


class TestFilesServiceCreateDelete:
    def test_create_with_directory(self, tmp_path):
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.create("readme.md", "# Doc", directory="docs")
        assert result["created"] is True
        assert (tmp_path / "docs" / "readme.md").exists()

    def test_delete_file(self, tmp_path):
        (tmp_path / "del.txt").write_text("bye")
        with patch.object(files_service, "_kb", return_value=tmp_path):
            result = files_service.delete("del.txt")
        assert result["deleted"] is True
        assert not (tmp_path / "del.txt").exists()


# ---- govern_service ----

class TestGovernPersona:
    def test_get_persona_default(self, tmp_path):
        with patch.object(govern_service, "PERSONA_FILE", tmp_path / "persona.json"), \
             patch.object(govern_service, "RULES_DIR", tmp_path / "rules"):
            result = govern_service.get_persona()
        assert result == {"personal": "", "professional": ""}

    def test_update_persona(self, tmp_path):
        with patch.object(govern_service, "PERSONA_FILE", tmp_path / "persona.json"), \
             patch.object(govern_service, "RULES_DIR", tmp_path / "rules"):
            govern_service.update_persona(personal="Kind", professional="Engineer")
            result = govern_service.get_persona()
        assert result["personal"] == "Kind"
        assert result["professional"] == "Engineer"


class TestGovernRules:
    def test_list_rules_empty(self, tmp_path):
        with patch.object(govern_service, "RULES_DIR", tmp_path / "rules"), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.list_rules()
        assert result["documents"] == []

    def test_list_rules_with_docs(self, tmp_path):
        rules_dir = tmp_path / "rules"
        cat = rules_dir / "safety"
        cat.mkdir(parents=True)
        (cat / "rule1.md").write_text("do no harm")
        with patch.object(govern_service, "RULES_DIR", rules_dir), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.list_rules()
        assert result["total"] == 1
        assert result["documents"][0]["category"] == "safety"


class TestGovernRuleContent:
    def test_get_rule_found(self, tmp_path):
        rules_dir = tmp_path / "rules"
        (rules_dir / "ethics").mkdir(parents=True)
        (rules_dir / "ethics" / "r1.md").write_text("Be fair")
        with patch.object(govern_service, "RULES_DIR", rules_dir), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.get_rule_content("ethics/r1.md")
        assert result["content"] == "Be fair"

    def test_get_rule_not_found(self, tmp_path):
        with patch.object(govern_service, "RULES_DIR", tmp_path / "rules"), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.get_rule_content("nope/missing.md")
        assert result == {"error": "Not found"}


class TestGovernSaveRule:
    def test_save_rule_existing(self, tmp_path):
        rules_dir = tmp_path / "rules"
        (rules_dir / "cat").mkdir(parents=True)
        (rules_dir / "cat" / "r.md").write_text("old")
        with patch.object(govern_service, "RULES_DIR", rules_dir), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.save_rule_content("cat/r.md", "new")
        assert result["saved"] is True
        assert (rules_dir / "cat" / "r.md").read_text() == "new"

    def test_save_rule_not_found(self, tmp_path):
        with patch.object(govern_service, "RULES_DIR", tmp_path / "rules"), \
             patch.object(govern_service, "PERSONA_FILE", tmp_path / "p.json"):
            result = govern_service.save_rule_content("x/y.md", "data")
        assert result == {"error": "Not found"}


# ---- system_service ----

class TestSystemServiceGC:
    def test_gc_collect_returns_int(self):
        result = system_service.gc_collect()
        assert isinstance(result["collected"], int)

    def test_gc_collect_nonnegative(self):
        result = system_service.gc_collect()
        assert result["collected"] >= 0


class TestSystemServicePauseResume:
    def test_pause_runtime(self):
        with patch.dict("sys.modules", {"app": MagicMock(app=MagicMock())}):
            result = system_service.pause_runtime()
        assert result == {"status": "paused"}

    def test_resume_runtime(self):
        with patch.dict("sys.modules", {"app": MagicMock(app=MagicMock())}):
            result = system_service.resume_runtime()
        assert result == {"status": "resumed"}


class TestSystemServiceHealth:
    def test_health_dashboard(self):
        import psutil as _real_psutil
        with patch.object(_real_psutil, "cpu_percent", return_value=25.0), \
             patch.object(_real_psutil, "virtual_memory", return_value=SimpleNamespace(percent=60.0)), \
             patch.object(_real_psutil, "disk_usage", return_value=SimpleNamespace(percent=45.0)):
            result = system_service.get_health_dashboard()
        assert result["cpu_percent"] == 25.0
        assert result["memory_percent"] == 60.0

    def test_health_dashboard_high_load(self):
        import psutil as _real_psutil
        with patch.object(_real_psutil, "cpu_percent", return_value=99.9), \
             patch.object(_real_psutil, "virtual_memory", return_value=SimpleNamespace(percent=88.0)), \
             patch.object(_real_psutil, "disk_usage", return_value=SimpleNamespace(percent=10.0)):
            result = system_service.get_health_dashboard()
        assert result["disk_percent"] == 10.0


# ---- tasks_service ----

class TestTasksSchedule:
    def test_schedule_task(self, tmp_path):
        with patch.object(tasks_service, "SCHED_PATH", tmp_path / "tasks.json"):
            result = tasks_service.schedule_task({
                "title": "Build CI", "priority": "high",
                "scheduled_for": "2026-04-01T00:00:00Z",
            })
        assert result["title"] == "Build CI"
        assert result["priority"] == "high"
        assert result["id"].startswith("sched-")

    def test_schedule_and_get(self, tmp_path):
        with patch.object(tasks_service, "SCHED_PATH", tmp_path / "tasks.json"):
            tasks_service.schedule_task({"title": "A", "scheduled_for": "2099-01-01T00:00:00Z"})
            tasks_service.schedule_task({"title": "B", "scheduled_for": "2099-01-02T00:00:00Z"})
            result = tasks_service.get_scheduled()
        assert len(result["tasks"]) == 2


class TestTasksDelete:
    def test_delete_scheduled(self, tmp_path):
        with patch.object(tasks_service, "SCHED_PATH", tmp_path / "tasks.json"):
            task = tasks_service.schedule_task({"title": "Remove me"})
            tasks_service.delete_scheduled(task["id"])
            result = tasks_service.get_scheduled()
        assert len(result["tasks"]) == 0

    def test_delete_nonexistent_noop(self, tmp_path):
        with patch.object(tasks_service, "SCHED_PATH", tmp_path / "tasks.json"):
            result = tasks_service.delete_scheduled("fake-id")
        assert result["deleted"] is True


class TestTasksOverdue:
    def test_overdue_marking(self, tmp_path):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        sched = tmp_path / "tasks.json"
        sched.write_text(json.dumps([
            {"id": "sched-old", "title": "Old", "scheduled_for": past, "status": "scheduled"},
        ]))
        with patch.object(tasks_service, "SCHED_PATH", sched):
            result = tasks_service.get_scheduled()
        assert result["tasks"][0]["status"] == "overdue"

    def test_future_stays_scheduled(self, tmp_path):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        sched = tmp_path / "tasks.json"
        sched.write_text(json.dumps([
            {"id": "sched-new", "title": "Future", "scheduled_for": future, "status": "scheduled"},
        ]))
        with patch.object(tasks_service, "SCHED_PATH", sched):
            result = tasks_service.get_scheduled()
        assert result["tasks"][0]["status"] == "scheduled"


# ---- project_service ----

class TestProjectCreate:
    def test_create_project(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            result = project_service.create_project("My App", description="test", project_type="fullstack")
        assert result["id"] == "my-app"
        assert result["name"] == "My App"
        assert result["status"] == "active"
        assert (tmp_path / "my-app" / "frontend").is_dir()
        assert (tmp_path / "my-app" / "tests").is_dir()

    def test_create_duplicate_errors(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            project_service.create_project("Dup")
            result = project_service.create_project("Dup")
        assert "error" in result


class TestProjectGet:
    def test_get_project_found(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            project_service.create_project("Found")
            result = project_service.get_project("found")
        assert result["name"] == "Found"
        assert "tree" in result

    def test_get_project_not_found(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            result = project_service.get_project("nonexistent")
        assert result == {"error": "Project not found"}


class TestProjectFiles:
    def test_write_and_read_project_file(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            project_service.create_project("Files Test")
            project_service.write_project_file("files-test", "backend/main.py", "print('hi')")
            result = project_service.read_project_file("files-test", "backend/main.py")
        assert result["content"] == "print('hi')"

    def test_read_missing_file(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            result = project_service.read_project_file("nope", "missing.py")
        assert result == {"error": "File not found"}


class TestProjectContext:
    def test_get_project_context(self, tmp_path):
        proj_dir = tmp_path / "ctx-proj"
        proj_dir.mkdir()
        (proj_dir / "app.py").write_text("import flask")
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            result = project_service.get_project_context("ctx-proj")
        assert "ctx-proj" in result
        assert "import flask" in result

    def test_get_project_context_missing(self, tmp_path):
        with patch.object(project_service, "PROJECTS_DIR", tmp_path):
            result = project_service.get_project_context("missing-proj")
        assert result == ""


# ---- workspace_service ----

class TestWorkspaceList:
    def test_ws_list(self):
        mock_mod = MagicMock()
        mock_mod._list_workspaces_sync.return_value = [{"id": "w1"}]
        with patch.dict("sys.modules", {"genesis.internal_vcs": mock_mod}):
            result = workspace_service.ws_list()
        assert result["workspaces"] == [{"id": "w1"}]

    def test_ws_list_empty(self):
        mock_mod = MagicMock()
        mock_mod._list_workspaces_sync.return_value = []
        with patch.dict("sys.modules", {"genesis.internal_vcs": mock_mod}):
            result = workspace_service.ws_list()
        assert result["workspaces"] == []
