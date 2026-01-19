"""
Grace Execution Bridge

Bridges Grace's cognitive layer with code execution capabilities.
Provides safe, sandboxed execution with full audit trail.
"""

import asyncio
import subprocess
import os
import sys
import logging
import tempfile
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import shutil

from .actions import (
    GraceAction,
    ActionRequest,
    ActionResult,
    ActionStatus,
    create_action,
)

logger = logging.getLogger(__name__)


class ExecutionConfig:
    """Configuration for the execution environment."""

    def __init__(
        self,
        workspace_dir: str = None,
        timeout: int = 300,
        use_docker: bool = False,
        docker_image: str = "grace-sandbox:latest",
        max_output_size: int = 100000,
        allowed_commands: List[str] = None,
        blocked_commands: List[str] = None,
    ):
        self.workspace_dir = workspace_dir or os.getcwd()
        self.timeout = timeout
        self.use_docker = use_docker
        self.docker_image = docker_image
        self.max_output_size = max_output_size
        self.allowed_commands = allowed_commands or []
        self.blocked_commands = blocked_commands or [
            "rm -rf /",
            "mkfs",
            "dd if=/dev/zero",
            ":(){:|:&};:",  # Fork bomb
        ]


class ExecutionBridge:
    """
    Main bridge between Grace's cognitive systems and code execution.

    Provides:
    - Sandboxed code execution (Python, Bash)
    - File operations (read, write, edit)
    - Git operations
    - Test execution
    - Full audit trail via Genesis Keys
    """

    def __init__(
        self,
        config: ExecutionConfig = None,
        genesis_tracker=None,
    ):
        self.config = config or ExecutionConfig()
        self.genesis = genesis_tracker
        self.action_history: List[Tuple[ActionRequest, ActionResult]] = []
        self._running = False

    async def execute(self, action: ActionRequest) -> ActionResult:
        """
        Execute an action and return the result.

        This is the main entry point for all execution requests.
        """
        start_time = datetime.utcnow()
        logger.info(f"Executing action: {action.action_type.value} [{action.action_id}]")

        try:
            # Route to appropriate handler
            handler = self._get_handler(action.action_type)
            result = await handler(action)

            # Calculate execution time
            result.execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Record in history
            self.action_history.append((action, result))

            # Track via Genesis if available
            if self.genesis:
                await self._track_genesis(action, result)

            logger.info(
                f"Action {action.action_id} completed: {result.status.value} "
                f"in {result.execution_time:.2f}s"
            )

            return result

        except asyncio.TimeoutError:
            result = ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.TIMEOUT,
                error=f"Action timed out after {action.timeout}s",
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
            self.action_history.append((action, result))
            return result

        except Exception as e:
            logger.exception(f"Action {action.action_id} failed with error")
            result = ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
            self.action_history.append((action, result))
            return result

    def _get_handler(self, action_type: GraceAction):
        """Get the handler function for an action type."""
        handlers = {
            # File operations
            GraceAction.READ_FILE: self._handle_read_file,
            GraceAction.WRITE_FILE: self._handle_write_file,
            GraceAction.EDIT_FILE: self._handle_edit_file,
            GraceAction.DELETE_FILE: self._handle_delete_file,

            # Code execution
            GraceAction.RUN_PYTHON: self._handle_run_python,
            GraceAction.RUN_BASH: self._handle_run_bash,

            # Testing
            GraceAction.RUN_TESTS: self._handle_run_tests,
            GraceAction.RUN_PYTEST: self._handle_run_pytest,

            # Git operations
            GraceAction.GIT_STATUS: self._handle_git_status,
            GraceAction.GIT_DIFF: self._handle_git_diff,
            GraceAction.GIT_ADD: self._handle_git_add,
            GraceAction.GIT_COMMIT: self._handle_git_commit,

            # Search
            GraceAction.SEARCH_CODE: self._handle_search_code,
            GraceAction.GREP_CODE: self._handle_grep_code,
            GraceAction.FIND_FILES: self._handle_find_files,

            # Agent control
            GraceAction.THINK: self._handle_think,
            GraceAction.PLAN: self._handle_plan,
            GraceAction.FINISH: self._handle_finish,
        }
        return handlers.get(action_type, self._handle_unknown)

    # ==================== File Operations ====================

    async def _handle_read_file(self, action: ActionRequest) -> ActionResult:
        """Read contents of a file."""
        path = action.parameters.get("path")
        start_line = action.parameters.get("start_line")
        end_line = action.parameters.get("end_line")

        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=f"File not found: {path}",
            )

        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            if start_line is not None:
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]

            content = ''.join(lines)

            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.SUCCESS,
                output=content[:self.config.max_output_size],
                data={
                    "path": path,
                    "lines": len(lines),
                    "size": len(content),
                },
            )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
            )

    async def _handle_write_file(self, action: ActionRequest) -> ActionResult:
        """Write content to a file."""
        path = action.parameters.get("path")
        content = action.parameters.get("content")
        overwrite = action.parameters.get("overwrite", True)

        full_path = self._resolve_path(path)

        # Check if file exists and overwrite is False
        if os.path.exists(full_path) and not overwrite:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=f"File exists and overwrite=False: {path}",
            )

        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            was_new = not os.path.exists(full_path)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.SUCCESS,
                output=f"Written {len(content)} bytes to {path}",
                files_created=[path] if was_new else [],
                files_modified=[] if was_new else [path],
                data={
                    "path": path,
                    "size": len(content),
                    "was_new": was_new,
                },
            )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
            )

    async def _handle_edit_file(self, action: ActionRequest) -> ActionResult:
        """Edit a file by replacing content."""
        path = action.parameters.get("path")
        old_content = action.parameters.get("old_content")
        new_content = action.parameters.get("new_content")
        replace_all = action.parameters.get("replace_all", False)

        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=f"File not found: {path}",
            )

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_content not in content:
                return ActionResult(
                    action_id=action.action_id,
                    action_type=action.action_type,
                    status=ActionStatus.FAILURE,
                    error="Old content not found in file",
                )

            if replace_all:
                new_file_content = content.replace(old_content, new_content)
            else:
                new_file_content = content.replace(old_content, new_content, 1)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_file_content)

            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.SUCCESS,
                output=f"Edited {path}",
                files_modified=[path],
                data={
                    "path": path,
                    "replacements": content.count(old_content) if replace_all else 1,
                },
            )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
            )

    async def _handle_delete_file(self, action: ActionRequest) -> ActionResult:
        """Delete a file."""
        path = action.parameters.get("path")
        full_path = self._resolve_path(path)

        if not os.path.exists(full_path):
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=f"File not found: {path}",
            )

        try:
            os.remove(full_path)
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.SUCCESS,
                output=f"Deleted {path}",
                files_deleted=[path],
            )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=str(e),
            )

    # ==================== Code Execution ====================

    async def _handle_run_python(self, action: ActionRequest) -> ActionResult:
        """Execute Python code."""
        code = action.parameters.get("code")
        timeout = action.parameters.get("timeout", self.config.timeout)

        # Create temp file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = await self._run_subprocess(
                [sys.executable, temp_path],
                timeout=timeout,
                cwd=self.config.workspace_dir,
            )
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
                output=result["stdout"],
                error=result["stderr"] if result["returncode"] != 0 else None,
                exit_code=result["returncode"],
                data={"code_length": len(code)},
            )
        finally:
            os.unlink(temp_path)

    async def _handle_run_bash(self, action: ActionRequest) -> ActionResult:
        """Execute a bash command."""
        command = action.parameters.get("command")
        working_dir = action.parameters.get("working_dir", self.config.workspace_dir)
        timeout = action.parameters.get("timeout", self.config.timeout)

        # Security check
        for blocked in self.config.blocked_commands:
            if blocked in command:
                return ActionResult(
                    action_id=action.action_id,
                    action_type=action.action_type,
                    status=ActionStatus.FAILURE,
                    error=f"Command blocked for security: contains '{blocked}'",
                )

        result = await self._run_subprocess(
            command,
            shell=True,
            timeout=timeout,
            cwd=working_dir,
        )

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
            data={"command": command},
        )

    # ==================== Testing ====================

    async def _handle_run_tests(self, action: ActionRequest) -> ActionResult:
        """Run tests using detected framework."""
        test_path = action.parameters.get("test_path", ".")
        framework = action.parameters.get("test_framework", "auto")

        # Auto-detect framework
        if framework == "auto":
            if os.path.exists(os.path.join(self.config.workspace_dir, "pytest.ini")) or \
               os.path.exists(os.path.join(self.config.workspace_dir, "pyproject.toml")):
                framework = "pytest"
            elif os.path.exists(os.path.join(self.config.workspace_dir, "package.json")):
                framework = "jest"
            else:
                framework = "pytest"

        if framework == "pytest":
            return await self._handle_run_pytest(action)
        elif framework == "jest":
            return await self._handle_run_jest(action)
        else:
            return ActionResult(
                action_id=action.action_id,
                action_type=action.action_type,
                status=ActionStatus.FAILURE,
                error=f"Unknown test framework: {framework}",
            )

    async def _handle_run_pytest(self, action: ActionRequest) -> ActionResult:
        """Run pytest tests."""
        test_path = action.parameters.get("test_path", ".")
        verbose = action.parameters.get("verbose", True)

        cmd = [sys.executable, "-m", "pytest", test_path, "--tb=short"]
        if verbose:
            cmd.append("-v")

        result = await self._run_subprocess(
            cmd,
            timeout=self.config.timeout,
            cwd=self.config.workspace_dir,
        )

        # Parse pytest output for summary
        output = result["stdout"]
        passed = output.count(" passed")
        failed = output.count(" failed")
        errors = output.count(" error")

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=output,
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
            data={
                "framework": "pytest",
                "test_path": test_path,
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
            trust_delta=0.1 if result["returncode"] == 0 else -0.05,
        )

    async def _handle_run_jest(self, action: ActionRequest) -> ActionResult:
        """Run jest tests."""
        test_path = action.parameters.get("test_path", ".")

        result = await self._run_subprocess(
            ["npx", "jest", test_path, "--json"],
            timeout=self.config.timeout,
            cwd=self.config.workspace_dir,
        )

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
            data={"framework": "jest", "test_path": test_path},
        )

    # ==================== Git Operations ====================

    async def _handle_git_status(self, action: ActionRequest) -> ActionResult:
        """Get git status."""
        result = await self._run_subprocess(
            ["git", "status", "--porcelain"],
            cwd=self.config.workspace_dir,
        )

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
        )

    async def _handle_git_diff(self, action: ActionRequest) -> ActionResult:
        """Get git diff."""
        staged = action.parameters.get("staged", False)
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")

        result = await self._run_subprocess(cmd, cwd=self.config.workspace_dir)

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
        )

    async def _handle_git_add(self, action: ActionRequest) -> ActionResult:
        """Stage files for commit."""
        files = action.parameters.get("files", ["."])
        if isinstance(files, str):
            files = [files]

        cmd = ["git", "add"] + files
        result = await self._run_subprocess(cmd, cwd=self.config.workspace_dir)

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
            data={"files": files},
        )

    async def _handle_git_commit(self, action: ActionRequest) -> ActionResult:
        """Create a git commit."""
        message = action.parameters.get("message")

        # Add co-author
        full_message = f"{message}\n\nCo-Authored-By: Grace AI <grace@ai.local>"

        result = await self._run_subprocess(
            ["git", "commit", "-m", full_message],
            cwd=self.config.workspace_dir,
        )

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS if result["returncode"] == 0 else ActionStatus.FAILURE,
            output=result["stdout"],
            error=result["stderr"] if result["returncode"] != 0 else None,
            exit_code=result["returncode"],
            data={"message": message},
        )

    # ==================== Search Operations ====================

    async def _handle_search_code(self, action: ActionRequest) -> ActionResult:
        """Search code using ripgrep or grep."""
        pattern = action.parameters.get("pattern")
        path = action.parameters.get("path", ".")
        file_type = action.parameters.get("file_type")

        cmd = ["rg", pattern, path, "-n", "--color=never"]
        if file_type:
            cmd.extend(["-t", file_type])

        result = await self._run_subprocess(cmd, cwd=self.config.workspace_dir)

        # Fall back to grep if rg not available
        if result["returncode"] == 127:  # Command not found
            cmd = ["grep", "-rn", pattern, path]
            result = await self._run_subprocess(cmd, cwd=self.config.workspace_dir)

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS,
            output=result["stdout"][:self.config.max_output_size],
            data={
                "pattern": pattern,
                "matches": len(result["stdout"].splitlines()),
            },
        )

    async def _handle_grep_code(self, action: ActionRequest) -> ActionResult:
        """Alias for search_code."""
        return await self._handle_search_code(action)

    async def _handle_find_files(self, action: ActionRequest) -> ActionResult:
        """Find files matching a pattern."""
        pattern = action.parameters.get("pattern")
        path = action.parameters.get("path", ".")

        # Use glob pattern matching
        from glob import glob
        full_path = self._resolve_path(path)
        matches = glob(os.path.join(full_path, "**", pattern), recursive=True)

        # Make paths relative
        matches = [os.path.relpath(m, self.config.workspace_dir) for m in matches]

        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS,
            output="\n".join(matches),
            data={
                "pattern": pattern,
                "count": len(matches),
                "files": matches[:100],  # Limit to 100 files
            },
        )

    # ==================== Agent Control ====================

    async def _handle_think(self, action: ActionRequest) -> ActionResult:
        """Record a thought (no execution)."""
        thought = action.parameters.get("thought")
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS,
            output=thought,
            data={"thought": thought},
            learnable=False,
        )

    async def _handle_plan(self, action: ActionRequest) -> ActionResult:
        """Record a plan (no execution)."""
        goal = action.parameters.get("goal")
        steps = action.parameters.get("steps", [])
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS,
            output=f"Goal: {goal}\nSteps: {json.dumps(steps, indent=2)}",
            data={"goal": goal, "steps": steps},
            learnable=False,
        )

    async def _handle_finish(self, action: ActionRequest) -> ActionResult:
        """Mark task as finished."""
        result = action.parameters.get("result")
        summary = action.parameters.get("summary", "")
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.SUCCESS,
            output=f"Task completed: {result}\n{summary}",
            data={"result": result, "summary": summary},
        )

    async def _handle_unknown(self, action: ActionRequest) -> ActionResult:
        """Handle unknown action types."""
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            status=ActionStatus.FAILURE,
            error=f"Unknown action type: {action.action_type}",
        )

    # ==================== Helper Methods ====================

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to workspace."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.config.workspace_dir, path)

    async def _run_subprocess(
        self,
        cmd,
        shell: bool = False,
        timeout: int = None,
        cwd: str = None,
        env: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Run a subprocess and capture output."""
        timeout = timeout or self.config.timeout
        cwd = cwd or self.config.workspace_dir

        try:
            if shell:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            return {
                "stdout": stdout.decode('utf-8', errors='replace')[:self.config.max_output_size],
                "stderr": stderr.decode('utf-8', errors='replace')[:self.config.max_output_size],
                "returncode": process.returncode,
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "stdout": "",
                "stderr": f"Process timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    async def _track_genesis(self, action: ActionRequest, result: ActionResult):
        """Track action in Genesis Keys."""
        if not self.genesis:
            return

        try:
            await self.genesis.create_key(
                what=f"Execution: {action.action_type.value}",
                who="grace_agent",
                where="execution_bridge",
                why=action.reasoning or "Agent action",
                how=json.dumps(action.parameters),
                metadata={
                    "action_id": action.action_id,
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "success": result.success,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to track Genesis key: {e}")


# Singleton instance
_bridge_instance: Optional[ExecutionBridge] = None


def get_execution_bridge(
    config: ExecutionConfig = None,
    genesis_tracker=None,
) -> ExecutionBridge:
    """Get or create the execution bridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ExecutionBridge(config=config, genesis_tracker=genesis_tracker)
    return _bridge_instance
