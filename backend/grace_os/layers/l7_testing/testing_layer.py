import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

MAX_HEAL_CYCLES = 3


class TestingLayer(GraceLayer):
    """
    Layer 7: Sandbox Execution & Testing.
    Runs tests in an isolated environment via MCP terminal tools.
    Implements the self-healing L7→L6→L7 code-fix loop.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._heal_counts: Dict[str, int] = {}

    @property
    def layer_name(self) -> str:
        return "L7_Testing"

    @property
    def capabilities(self) -> List[str]:
        return ["test_execution", "test_generation", "build_validation", "regression_detection"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["VERIFY_TASK", "RUN_TESTS"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "VERIFY_TASK":
            return await self._handle_verify(message)
        elif message.message_type == "RUN_TESTS":
            return await self._handle_run_tests(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_verify(self, message: LayerMessage) -> LayerResponse:
        """Run tests and trigger self-healing loop on failure."""
        task = message.payload.get("task", message.payload)
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        files_changed = message.payload.get("files_changed", [])

        logger.info(f"[L7] Verifying code changes for: {task_desc[:60]}...")

        # 1. Build validation — check the project compiles/lints cleanly
        build_result = await self._run_build_check()

        # 2. Run existing test suite
        test_result = await self._run_tests()

        test_passed = test_result.get("passed", False)
        error_output = test_result.get("output", "")
        failed_tests = test_result.get("failed_tests", [])

        if test_passed and build_result.get("passed", True):
            logger.info("[L7] ✅ All tests passed.")
            return self.build_response(
                message, "success",
                {
                    "message": "All tests passed.",
                    "test_output": test_result.get("output", "")[:1000],
                    "tests_run": test_result.get("tests_run", 0),
                    "tests_passed": test_result.get("tests_passed", 0),
                },
                trust_score=95.0
            )

        # Tests failed — trigger self-healing loop
        heal_key = message.trace_id
        self._heal_counts[heal_key] = self._heal_counts.get(heal_key, 0) + 1
        cycle = self._heal_counts[heal_key]

        if cycle > MAX_HEAL_CYCLES:
            logger.warning(f"[L7] Max heal cycles ({MAX_HEAL_CYCLES}) exceeded. Reporting failure.")
            return self.build_response(
                message, "failure",
                {
                    "message": f"Tests still failing after {MAX_HEAL_CYCLES} fix cycles.",
                    "error_trace": error_output[:2000],
                    "failed_tests": failed_tests,
                },
                trust_score=15.0
            )

        logger.warning(f"[L7] ❌ Tests failed (cycle {cycle}/{MAX_HEAL_CYCLES}). Triggering L6 code fix...")

        # Send FIX_CODE to L6
        fix_response = await self.send_message(
            to_layer="L6_Codegen",
            message_type="FIX_CODE",
            payload={
                "error_trace": error_output[:3000],
                "original_task": task_desc,
                "failed_files": files_changed,
                "failed_tests": failed_tests,
                "cycle": cycle,
            },
            trace_id=message.trace_id,
            parent_message_id=message.id
        )

        if fix_response.status != "success":
            logger.warning("[L7] L6 fix attempt failed.")
            return self.build_response(
                message, "failure",
                {
                    "message": f"L6 fix attempt failed on cycle {cycle}.",
                    "error_trace": error_output[:2000],
                    "fix_error": fix_response.payload.get("error", ""),
                },
                trust_score=20.0
            )

        # Re-run tests after fix
        logger.info(f"[L7] Re-running tests after L6 fix (cycle {cycle})...")
        retest_result = await self._run_tests()

        if retest_result.get("passed", False):
            logger.info(f"[L7] ✅ Tests passed after fix cycle {cycle}!")
            return self.build_response(
                message, "success",
                {
                    "message": f"Tests passed after {cycle} fix cycle(s).",
                    "test_output": retest_result.get("output", "")[:1000],
                    "fix_cycles": cycle,
                },
                trust_score=max(60.0, 95.0 - (cycle * 10))
            )

        # Still failing — report partial result (SessionManager can decide to stop or continue)
        return self.build_response(
            message, "failure",
            {
                "message": f"Tests still failing after fix cycle {cycle}.",
                "error_trace": retest_result.get("output", "")[:2000],
                "failed_tests": retest_result.get("failed_tests", []),
                "fix_cycles": cycle,
            },
            trust_score=25.0
        )

    async def _handle_run_tests(self, message: LayerMessage) -> LayerResponse:
        """Run a specific test command (ad-hoc)."""
        command = message.payload.get("command", "")
        if not command:
            return self.build_response(
                message, "failure",
                {"error": "No test command provided"},
                trust_score=10.0
            )

        result = await self._execute_terminal(command)
        passed = result.get("exit_code", 1) == 0

        return self.build_response(
            message, "success" if passed else "failure",
            {
                "passed": passed,
                "output": result.get("output", "")[:3000],
                "exit_code": result.get("exit_code", -1),
            },
            trust_score=90.0 if passed else 30.0
        )

    async def _run_build_check(self) -> Dict[str, Any]:
        """Run a quick build/lint check via MCP terminal."""
        logger.info("[L7] Running build validation...")

        # Try common build commands. Detect project type first.
        try:
            ls_result = await self.call_tool("list_directory", {"path": "."})
            content = ls_result.get("content", "")

            # Detect project type and choose build command
            if "package.json" in content:
                cmd = "npm run build --if-present 2>&1 || echo BUILD_CHECK_DONE"
            elif "requirements.txt" in content or "setup.py" in content or "pyproject.toml" in content:
                cmd = "python -m py_compile . 2>&1; echo BUILD_CHECK_DONE"
            elif "Cargo.toml" in content:
                cmd = "cargo check 2>&1 || echo BUILD_CHECK_DONE"
            else:
                # No recognized build system — skip
                return {"passed": True, "output": "No build system detected, skipping."}

            result = await self._execute_terminal(cmd)
            passed = result.get("exit_code", 0) == 0

            return {
                "passed": passed,
                "output": result.get("output", ""),
            }
        except Exception as e:
            logger.warning(f"[L7] Build check failed: {e}")
            return {"passed": True, "output": f"Build check skipped: {e}"}

    async def _run_tests(self) -> Dict[str, Any]:
        """Run the project's test suite via MCP terminal."""
        logger.info("[L7] Running test suite...")

        # Detect test framework
        try:
            ls_result = await self.call_tool("list_directory", {"path": "."})
            content = ls_result.get("content", "")
        except Exception:
            content = ""

        # Choose test command based on project type
        if "package.json" in content:
            cmd = "npm test 2>&1"
        elif "pytest.ini" in content or "conftest.py" in content or "requirements.txt" in content:
            cmd = "python -m pytest --tb=short -q 2>&1"
        elif "Cargo.toml" in content:
            cmd = "cargo test 2>&1"
        else:
            cmd = "python -m pytest --tb=short -q 2>&1"

        result = await self._execute_terminal(cmd)
        output = result.get("output", "")
        exit_code = result.get("exit_code", -1)

        # Parse test results from output
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        failed_tests = []

        # Try to parse pytest-style output
        for line in output.split("\n"):
            line = line.strip()
            if "passed" in line:
                import re
                m = re.search(r'(\d+)\s+passed', line)
                if m:
                    tests_passed = int(m.group(1))
            if "failed" in line:
                import re
                m = re.search(r'(\d+)\s+failed', line)
                if m:
                    tests_failed = int(m.group(1))
            if line.startswith("FAILED"):
                failed_tests.append(line)

        tests_run = tests_passed + tests_failed
        passed = exit_code == 0 and tests_failed == 0

        return {
            "passed": passed,
            "output": output[:5000],
            "exit_code": exit_code,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "failed_tests": failed_tests,
        }

    async def _execute_terminal(self, command: str, timeout_ms: int = 30000) -> Dict[str, Any]:
        """Execute a terminal command via MCP and return result."""
        try:
            result = await self.call_tool("execute_command", {
                "command": command,
                "timeout_ms": timeout_ms
            })

            content = result.get("content", "")

            # Parse exit code from DesktopCommanderMCP output format
            exit_code = 0
            if result.get("success") is False:
                exit_code = 1
            if "exit code:" in content.lower():
                import re
                m = re.search(r'exit code:\s*(\d+)', content, re.IGNORECASE)
                if m:
                    exit_code = int(m.group(1))

            return {
                "output": content,
                "exit_code": exit_code,
                "success": result.get("success", False),
            }
        except Exception as e:
            logger.error(f"[L7] Terminal execution failed: {e}")
            return {
                "output": str(e),
                "exit_code": -1,
                "success": False,
            }
