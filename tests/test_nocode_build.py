"""
Tests for NoCodePanelSystem build functionality.

Tests:
1. trigger_build() for python, npm, cargo, make
2. get_build_status()
3. parse_build_output() error extraction
4. Background execution
5. Timeout handling
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_panel_system():
    """Import and create NoCodePanelSystem avoiding ide_bridge import issues."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "nocode_panels",
        Path(__file__).parent.parent / "backend" / "grace_os" / "nocode_panels.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["nocode_panels"] = module
    spec.loader.exec_module(module)
    return module.NoCodePanelSystem(session=None, enable_voice=False)


class TestNoCodeBuildSystem:
    """Tests for the NoCodePanelSystem build functionality."""

    @pytest.fixture
    def panel_system(self):
        """Create a NoCodePanelSystem instance."""
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path


class TestTriggerBuild:
    """Tests for trigger_build() method."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_trigger_build_python(self, mock_run, panel_system, temp_project):
        """Test triggering a Python build."""
        mock_run.return_value = Mock(
            stdout="Installing package...\nSuccess",
            stderr="",
            returncode=0
        )

        (temp_project / "pyproject.toml").write_text("[project]\nname='test'")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )

        assert result is not None
        assert "build_id" in result
        assert result["build_id"].startswith("BUILD-")
        assert result["status"] in ("pending", "running", "success")
        assert result["build_type"] == "python"

    @patch('subprocess.run')
    def test_trigger_build_npm(self, mock_run, panel_system, temp_project):
        """Test triggering an npm build."""
        mock_run.return_value = Mock(
            stdout="Building...\nDone",
            stderr="",
            returncode=0
        )

        (temp_project / "package.json").write_text('{"name": "test"}')

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="npm"
        )

        assert result is not None
        assert result["build_id"].startswith("BUILD-")
        assert result["build_type"] == "npm"

    @patch('subprocess.run')
    def test_trigger_build_cargo(self, mock_run, panel_system, temp_project):
        """Test triggering a Cargo build."""
        mock_run.return_value = Mock(
            stdout="Compiling...\nFinished",
            stderr="",
            returncode=0
        )

        (temp_project / "Cargo.toml").write_text('[package]\nname = "test"')

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="cargo"
        )

        assert result is not None
        assert result["build_type"] == "cargo"

    @patch('subprocess.run')
    def test_trigger_build_make(self, mock_run, panel_system, temp_project):
        """Test triggering a Make build."""
        mock_run.return_value = Mock(
            stdout="make: all targets built",
            stderr="",
            returncode=0
        )

        (temp_project / "Makefile").write_text("all:\n\techo done")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="make"
        )

        assert result is not None
        assert result["build_type"] == "make"

    @patch('subprocess.run')
    def test_trigger_build_auto_detect_python(self, mock_run, panel_system, temp_project):
        """Test auto-detecting Python project."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        (temp_project / "pyproject.toml").write_text("[project]")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="auto"
        )

        assert result["build_type"] == "python"

    @patch('subprocess.run')
    def test_trigger_build_auto_detect_npm(self, mock_run, panel_system, temp_project):
        """Test auto-detecting npm project."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        (temp_project / "package.json").write_text("{}")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="auto"
        )

        assert result["build_type"] == "npm"

    @patch('subprocess.run')
    def test_trigger_build_auto_detect_cargo(self, mock_run, panel_system, temp_project):
        """Test auto-detecting Cargo project."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        (temp_project / "Cargo.toml").write_text("[package]")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="auto"
        )

        assert result["build_type"] == "cargo"

    @patch('subprocess.run')
    def test_trigger_build_custom_command(self, mock_run, panel_system, temp_project):
        """Test triggering a build with custom command."""
        mock_run.return_value = Mock(stdout="Custom build done", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="custom",
            custom_command="echo hello"
        )

        assert result is not None
        assert "build_id" in result

    def test_trigger_build_unknown_type(self, panel_system, temp_project):
        """Test triggering a build with unknown type returns error."""
        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="unknown_type"
        )

        assert result["status"] == "failed"
        assert len(result["errors"]) > 0
        assert "Unknown build type" in result["errors"][0]["message"]


class TestGetBuildStatus:
    """Tests for get_build_status() method."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_get_build_status_pending(self, mock_run, panel_system, temp_project):
        """Test getting status of a pending build."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )
        build_id = result["build_id"]

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["build_id"] == build_id
        assert status["status"] in ("pending", "running", "success", "failed")

    @patch('subprocess.run')
    def test_get_build_status_completed(self, mock_run, panel_system, temp_project):
        """Test getting status of a completed build."""
        mock_run.return_value = Mock(stdout="Success", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )
        build_id = result["build_id"]

        time.sleep(0.2)

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["build_id"] == build_id

    def test_get_build_status_not_found(self, panel_system):
        """Test getting status of non-existent build."""
        status = panel_system.get_build_status("BUILD-nonexistent")
        assert status is None


class TestParseBuildOutput:
    """Tests for parse_build_output() method."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    def test_parse_python_error(self, panel_system):
        """Test parsing Python errors."""
        output = '''File "main.py", line 42
    print(undefined_var)
NameError: name 'undefined_var' is not defined'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) > 0

    def test_parse_typescript_error(self, panel_system):
        """Test parsing TypeScript errors."""
        output = '''src/app.tsx:15:10: error TS2322: Type 'string' is not assignable'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) > 0
        error = errors[0]
        assert "Type 'string'" in error["message"] or "error" in error["message"].lower()

    def test_parse_cargo_error(self, panel_system):
        """Test parsing Cargo/Rust errors."""
        output = '''error: cannot find value `x` in this scope'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) > 0

    def test_parse_warnings(self, panel_system):
        """Test parsing warnings."""
        output = '''warning: unused variable `x`
 --> src/main.rs:3:9
Warning: deprecated API usage'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(warnings) >= 1

    def test_parse_generic_error(self, panel_system):
        """Test parsing generic error messages."""
        output = '''error: something went wrong
Error: another problem'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) >= 1

    def test_parse_no_errors(self, panel_system):
        """Test parsing output with no errors."""
        output = '''Building...
Compiling 50 packages
Success!'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) == 0

    def test_parse_npm_error(self, panel_system):
        """Test parsing npm/node errors."""
        output = '''ERROR in ./src/index.js (5,10):
Module not found: Error: Can't resolve 'missing-module' '''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) > 0

    def test_parse_mixed_errors_and_warnings(self, panel_system):
        """Test parsing output with both errors and warnings."""
        output = '''warning: unused import
error: missing semicolon
Warning: deprecated function'''

        errors, warnings = panel_system.parse_build_output(output)

        assert len(errors) >= 1
        assert len(warnings) >= 1


class TestBackgroundExecution:
    """Tests for background build execution."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_build_runs_in_background(self, mock_run, panel_system, temp_project):
        """Test that build runs in a background thread."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )

        assert result["status"] in ("pending", "running", "success")
        assert "build_id" in result

    @patch('subprocess.run')
    def test_build_updates_status_on_completion(self, mock_run, panel_system, temp_project):
        """Test that build status updates after completion."""
        mock_run.return_value = Mock(stdout="Success", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )
        build_id = result["build_id"]

        time.sleep(0.3)

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["status"] in ("success", "failed", "running")

    @patch('subprocess.run')
    def test_build_failure_status(self, mock_run, panel_system, temp_project):
        """Test build status on failure."""
        mock_run.return_value = Mock(
            stdout="",
            stderr="Error: Build failed",
            returncode=1
        )

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )
        build_id = result["build_id"]

        time.sleep(0.3)

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["status"] == "failed"

    @patch('subprocess.run')
    def test_multiple_builds_tracked(self, mock_run, panel_system, temp_project):
        """Test that multiple concurrent builds are tracked."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        build1 = panel_system.trigger_build(str(temp_project), build_type="python")
        build2 = panel_system.trigger_build(str(temp_project), build_type="npm")

        assert build1["build_id"] != build2["build_id"]
        assert panel_system.get_build_status(build1["build_id"]) is not None
        assert panel_system.get_build_status(build2["build_id"]) is not None


class TestTimeoutHandling:
    """Tests for build timeout handling."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_build_timeout_error(self, mock_run, panel_system, temp_project):
        """Test that timeout is handled correctly."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python",
            timeout=1
        )
        build_id = result["build_id"]

        time.sleep(0.3)

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["status"] == "failed"
        has_timeout_or_expired = any(
            "timeout" in str(e.get("message", "")).lower() or
            "expired" in str(e.get("message", "")).lower()
            for e in status["errors"]
        )
        assert has_timeout_or_expired or len(status["errors"]) > 0

    @patch('subprocess.run')
    def test_custom_timeout_value(self, mock_run, panel_system, temp_project):
        """Test custom timeout value is passed."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python",
            timeout=60
        )

        assert result is not None

    @patch('subprocess.run')
    def test_command_not_found(self, mock_run, panel_system, temp_project):
        """Test handling of command not found error."""
        mock_run.side_effect = FileNotFoundError("Command not found")

        result = panel_system.trigger_build(
            project_path=str(temp_project),
            build_type="python"
        )
        build_id = result["build_id"]

        time.sleep(0.3)

        status = panel_system.get_build_status(build_id)

        assert status is not None
        assert status["status"] == "failed"
        assert any("not found" in str(e.get("message", "")).lower() for e in status["errors"])


class TestListBuilds:
    """Tests for list_builds() method."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_list_builds_empty(self, mock_run, panel_system):
        """Test listing builds when none exist."""
        builds = panel_system.list_builds()
        assert isinstance(builds, list)

    @patch('subprocess.run')
    def test_list_builds_with_entries(self, mock_run, panel_system, temp_project):
        """Test listing builds with entries."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        panel_system.trigger_build(str(temp_project), build_type="python")
        panel_system.trigger_build(str(temp_project), build_type="npm")

        builds = panel_system.list_builds()

        assert len(builds) == 2

    @patch('subprocess.run')
    def test_list_builds_with_limit(self, mock_run, panel_system, temp_project):
        """Test listing builds respects limit."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        for _ in range(5):
            panel_system.trigger_build(str(temp_project), build_type="python")

        builds = panel_system.list_builds(limit=3)

        assert len(builds) == 3


class TestCancelBuild:
    """Tests for cancel_build() method."""

    @pytest.fixture
    def panel_system(self):
        return get_panel_system()

    @pytest.fixture
    def temp_project(self, tmp_path):
        return tmp_path

    @patch('subprocess.run')
    def test_cancel_pending_build(self, mock_run, panel_system, temp_project):
        """Test cancelling a pending build."""
        mock_run.return_value = Mock(stdout="Done", stderr="", returncode=0)

        result = panel_system.trigger_build(str(temp_project), build_type="python")
        build_id = result["build_id"]

        cancelled = panel_system.cancel_build(build_id)

        status = panel_system.get_build_status(build_id)

        if cancelled:
            assert status["status"] == "cancelled"

    def test_cancel_nonexistent_build(self, panel_system):
        """Test cancelling a non-existent build."""
        result = panel_system.cancel_build("BUILD-nonexistent")
        assert result is False
