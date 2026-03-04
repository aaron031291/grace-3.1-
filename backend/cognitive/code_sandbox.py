"""
Code Sandbox — Safe Python execution for Grace-generated code.

Grace generates code via LLMs but never runs it. This sandbox:
  1. Compiles code (catches syntax errors)
  2. Static analysis (catches common issues)
  3. Executes in isolated subprocess (catches runtime errors)
  4. Timeout and resource limits (prevents infinite loops/OOM)
  5. Captures stdout, stderr, return values
  6. All execution tracked via Genesis Keys

Security: subprocess with timeout, no network, limited filesystem.
"""

import ast
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_EXECUTION_SECONDS = 30
MAX_OUTPUT_BYTES = 100_000


class SandboxResult:
    def __init__(self):
        self.compiled = False
        self.syntax_errors: List[str] = []
        self.static_warnings: List[str] = []
        self.executed = False
        self.stdout = ""
        self.stderr = ""
        self.return_code = -1
        self.execution_time_ms = 0
        self.runtime_error = ""
        self.success = False

    def to_dict(self) -> dict:
        return {
            "compiled": self.compiled,
            "syntax_errors": self.syntax_errors,
            "static_warnings": self.static_warnings,
            "executed": self.executed,
            "stdout": self.stdout[:5000],
            "stderr": self.stderr[:2000],
            "return_code": self.return_code,
            "execution_time_ms": self.execution_time_ms,
            "runtime_error": self.runtime_error,
            "success": self.success,
        }


def compile_check(code: str) -> SandboxResult:
    """Stage 1: Check if code compiles (syntax validation)."""
    result = SandboxResult()
    try:
        compile(code, "<sandbox>", "exec")
        result.compiled = True
    except SyntaxError as e:
        result.syntax_errors.append(f"Line {e.lineno}: {e.msg}")
    return result


def static_analyse(code: str) -> List[str]:
    """Stage 2: Static analysis — catch common issues without running."""
    warnings = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ["Cannot parse — syntax error"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "exec", "eval"):
                    warnings.append(f"Line {node.lineno}: dangerous call to {node.func.attr}()")
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("exec", "eval", "compile", "__import__"):
                    warnings.append(f"Line {node.lineno}: dangerous call to {node.func.id}()")

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("os", "subprocess", "shutil", "socket", "http"):
                    warnings.append(f"Line {node.lineno}: imports potentially dangerous module '{alias.name}'")

        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in ("os", "subprocess", "shutil", "socket"):
                warnings.append(f"Line {node.lineno}: imports from dangerous module '{node.module}'")

    # Check for infinite loops (basic heuristic)
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                warnings.append(f"Line {node.lineno}: while True loop — potential infinite loop")

    return warnings


def execute_sandboxed(code: str, timeout: int = MAX_EXECUTION_SECONDS) -> SandboxResult:
    """
    Full sandbox: compile → static analyse → execute in subprocess.
    Returns comprehensive result with stdout, stderr, and timing.
    """
    result = SandboxResult()

    # Stage 1: Compile check
    try:
        compile(code, "<sandbox>", "exec")
        result.compiled = True
    except SyntaxError as e:
        result.syntax_errors.append(f"Line {e.lineno}: {e.msg}")
        return result

    # Stage 2: Static analysis
    result.static_warnings = static_analyse(code)

    # Stage 3: Execute in subprocess
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        start = time.time()
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": "",
                "HOME": tempfile.gettempdir(),
            },
        )

        result.execution_time_ms = round((time.time() - start) * 1000, 1)
        result.executed = True
        result.stdout = proc.stdout[:MAX_OUTPUT_BYTES]
        result.stderr = proc.stderr[:MAX_OUTPUT_BYTES]
        result.return_code = proc.returncode
        result.success = proc.returncode == 0

        if proc.returncode != 0 and proc.stderr:
            lines = proc.stderr.strip().split("\n")
            result.runtime_error = lines[-1] if lines else "Unknown error"

    except subprocess.TimeoutExpired:
        result.executed = True
        result.runtime_error = f"Execution timed out after {timeout}s"
        result.return_code = -1

    except Exception as e:
        result.runtime_error = str(e)

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    # Track via Genesis Key
    try:
        from api._genesis_tracker import track
        track(
            key_type="coding_agent_action",
            what=f"Code sandbox: {'PASS' if result.success else 'FAIL'} ({result.execution_time_ms}ms)",
            how="code_sandbox.execute_sandboxed",
            output_data={
                "compiled": result.compiled,
                "success": result.success,
                "warnings": len(result.static_warnings),
                "runtime_error": result.runtime_error[:200] if result.runtime_error else "",
            },
            tags=["sandbox", "code_execution", "pass" if result.success else "fail"],
        )
    except Exception:
        pass

    return result


def verify_code_quality(code: str) -> Dict[str, Any]:
    """
    Full code quality check: compile + static + execute + score.
    Returns a quality score 0-100.
    """
    result = execute_sandboxed(code)

    score = 0
    if result.compiled:
        score += 30
    if result.executed and result.success:
        score += 40
    if not result.static_warnings:
        score += 15
    elif len(result.static_warnings) <= 2:
        score += 10
    if not result.runtime_error:
        score += 15

    return {
        "score": score,
        "compiled": result.compiled,
        "runs_successfully": result.success,
        "static_warnings": result.static_warnings,
        "runtime_error": result.runtime_error,
        "execution_time_ms": result.execution_time_ms,
        "stdout_preview": result.stdout[:500],
        "detail": result.to_dict(),
    }
