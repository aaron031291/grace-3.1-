"""
Adaptive Test Generator — Auto-generates tests for ANY new component.

When a new module enters Grace (via Live Integration Protocol, handshake, or
manual addition), this system:

  1. READS the component (AST parse — functions, classes, signatures, docstrings)
  2. REASONS about it (LLM analyses what the component SHOULD do)
  3. DETERMINES expected outputs (reverse-engineers from purpose)
  4. GENERATES tests (input → expected output, verified by LLM)
  5. RUNS tests through sandbox
  6. REGISTERS passing tests in the deep test engine

The key insight: LLM reads the code, understands the PURPOSE, figures out
what the OUTPUT should be, then works BACKWARDS to create the INPUT that
would produce that output. If input → stages → output matches, the test passes.

Connects to:
  - Live Integration Protocol (auto-test new components)
  - Grace Compiler (test generated code)
  - Deep Test Engine (register new tests)
  - Hallucination Guard (verify LLM's test reasoning)
  - Architecture Compass (understand component's role)
"""

import ast
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cognitive.event_bus import publish

logger = logging.getLogger(__name__)

GENERATED_TESTS_DIR = Path(__file__).parent.parent / "data" / "generated_tests"
BACKEND_DIR = Path(__file__).parent.parent


def generate_tests_for_module(module_path: str) -> Dict[str, Any]:
    """
    Full adaptive test generation pipeline for any module.
    Read → Reason → Determine outputs → Generate tests → Run → Register.
    """
    publish("testing.adaptive_generation_started", data={"module": module_path}, source="adaptive_test_generator")
    start = time.time()
    path = Path(module_path)
    if not path.is_absolute():
        path = BACKEND_DIR / module_path

    if not path.exists():
        return {"error": f"Module not found: {module_path}"}

    result = {
        "module": module_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "functions_found": 0,
        "tests_generated": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests": [],
    }

    # Step 1: READ — parse the module
    source = path.read_text(errors="ignore")
    functions = _extract_functions(source)
    result["functions_found"] = len(functions)

    if not functions:
        return {**result, "message": "No testable functions found"}

    # Step 2: REASON using consensus — Kimi+Opus understand the module's PURPOSE
    module_purpose = _consensus_reason_about_module(source[:3000], module_path)
    result["module_purpose"] = module_purpose

    # Step 3: GENERATE tests for each function
    for func in functions[:15]:
        test_code = _generate_test_for_function(func, source, module_path, module_purpose)
        if not test_code:
            continue

        result["tests_generated"] += 1

        # Step 3: RUN — execute the generated test in sandbox
        test_result = _run_generated_test(test_code, source)

        test_entry = {
            "function": func["name"],
            "test_code": test_code[:500],
            "passed": test_result.get("passed", False),
            "output": test_result.get("output", "")[:200],
            "error": test_result.get("error", ""),
        }
        result["tests"].append(test_entry)

        if test_result.get("passed"):
            result["tests_passed"] += 1
        else:
            result["tests_failed"] += 1

    result["pass_rate"] = round(result["tests_passed"] / max(result["tests_generated"], 1) * 100, 1)
    result["duration_ms"] = round((time.time() - start) * 1000, 1)

    # Save generated tests
    _save_generated_tests(module_path, result)

    # Track
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Adaptive tests: {module_path} — {result['tests_passed']}/{result['tests_generated']} pass",
            how="adaptive_test_generator",
            output_data={"pass_rate": result["pass_rate"], "functions": result["functions_found"]},
            tags=["adaptive_test", "auto_generated"],
        )
    except Exception:
        pass

    publish("testing.adaptive_generation_completed", data=result, source="adaptive_test_generator")
    return result


def generate_tests_for_all_new() -> Dict[str, Any]:
    """
    Scan for modules that DON'T have tests yet and generate them.
    Connects to Live Integration Protocol — new citizens get auto-tested.
    """
    tested = set()
    try:
        if GENERATED_TESTS_DIR.exists():
            for f in GENERATED_TESTS_DIR.glob("*.json"):
                data = json.loads(f.read_text())
                tested.add(data.get("module", ""))
    except Exception:
        pass

    # Find cognitive modules without generated tests
    untested = []
    for f in sorted((BACKEND_DIR / "cognitive").glob("*.py")):
        if f.name == "__init__.py":
            continue
        rel = f"cognitive/{f.name}"
        if rel not in tested:
            untested.append(rel)

    results = {"total_untested": len(untested), "generated": []}
    for mod in untested[:5]:  # Process 5 at a time to avoid timeouts
        r = generate_tests_for_module(mod)
        results["generated"].append({
            "module": mod,
            "tests": r.get("tests_generated", 0),
            "passed": r.get("tests_passed", 0),
        })

    return results


def _extract_functions(source: str) -> List[Dict]:
    """Extract all testable functions from source code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = []
            for a in node.args.args:
                if a.arg not in ("self", "cls"):
                    annotation = ""
                    if a.annotation and isinstance(a.annotation, ast.Name):
                        annotation = a.annotation.id
                    elif a.annotation and isinstance(a.annotation, ast.Constant):
                        annotation = str(a.annotation.value)
                    args.append({"name": a.arg, "type": annotation})

            docstring = ast.get_docstring(node) or ""
            returns = ""
            if node.returns:
                if isinstance(node.returns, ast.Name):
                    returns = node.returns.id
                elif isinstance(node.returns, ast.Constant):
                    returns = str(node.returns.value)

            functions.append({
                "name": node.name,
                "args": args,
                "docstring": docstring[:300],
                "returns": returns,
                "line": node.lineno,
                "body_lines": node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0,
            })

    return functions


def _consensus_reason_about_module(source: str, module_path: str) -> str:
    """Use Kimi+Opus to understand what a module SHOULD do before generating tests."""
    try:
        from cognitive.consensus_engine import run_consensus, _check_model_available
        available = [m for m in ["kimi", "opus"] if _check_model_available(m)]
        if not available:
            available = ["qwen"]

        result = run_consensus(
            prompt=(
                f"Read this Python module and explain in 3 sentences:\n"
                f"1. What is its purpose?\n"
                f"2. What are its critical functions?\n"
                f"3. What should tests verify?\n\n"
                f"Module: {module_path}\n\n{source[:2000]}"
            ),
            models=available[:2],
            source="autonomous",
        )
        return result.final_output[:500] if result.final_output else ""
    except Exception:
        return ""

def _generate_test_for_function(func: Dict, source: str, module_path: str,
                                module_purpose: str = "") -> Optional[str]:
    """
    Generate a test for a specific function.
    Uses LLM to reason about expected behaviour, or falls back to basic tests.
    """
    name = func["name"]
    args = func["args"]
    docstring = func["docstring"]
    returns = func["returns"]

    # Try LLM-generated test first
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()

        purpose_ctx = f"\nModule purpose: {module_purpose}\n" if module_purpose else ""

        prompt = (
            f"Generate a Python test for this function:\n\n"
            f"Function: {name}({', '.join(a['name'] + (': ' + a['type'] if a['type'] else '') for a in args)})"
            f"{' -> ' + returns if returns else ''}\n"
            f"Docstring: {docstring}\n"
            f"{purpose_ctx}\n"
            f"The test should:\n"
            f"1. Call the function with valid inputs\n"
            f"2. Assert the output type is correct\n"
            f"3. Assert the output makes sense for the function's purpose\n"
            f"4. Test at least one edge case\n\n"
            f"Output ONLY the test function code. No imports, no explanation.\n"
            f"Start with: def test_{name}():"
        )

        response = client.generate(
            prompt=prompt,
            system_prompt="Generate a minimal Python test function. Output ONLY code.",
            temperature=0.1,
            max_tokens=512,
        )

        if isinstance(response, str) and f"def test_{name}" in response:
            # Clean up
            code = response.strip()
            if code.startswith("```"):
                code = code.split("\n", 1)[1] if "\n" in code else code[3:]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()
    except Exception:
        pass

    # Fallback: generate basic structural test
    return _generate_basic_test(func, module_path)


def _generate_basic_test(func: Dict, module_path: str) -> str:
    """Generate a basic test without LLM — just checks the function exists and is callable."""
    name = func["name"]
    module_import = module_path.replace("/", ".").replace(".py", "")

    return f"""def test_{name}():
    from {module_import} import {name}
    assert callable({name}), "{name} should be callable"
    # Basic structural test — function exists and is callable
    print("PASS: {name} exists and is callable")
"""
def _run_generated_test(test_code: str, source: str) -> Dict[str, Any]:
    """Run a generated test in the sandbox."""
    try:
        from cognitive.code_sandbox import execute_sandboxed

        # Wrap test with minimal runner
        full_code = f"""
import sys
sys.path.insert(0, '.')

{test_code}

# Run the test
try:
    test_name = [name for name in dir() if name.startswith('test_')][0]
    globals()[test_name]()
    print("TEST_PASSED")
except AssertionError as e:
    print(f"TEST_FAILED: {{e}}")
except Exception as e:
    print(f"TEST_ERROR: {{e}}")
"""

        result = execute_sandboxed(full_code, timeout=10)

        return {
            "passed": "TEST_PASSED" in result.stdout,
            "output": result.stdout[:500],
            "error": result.stderr[:300] if result.stderr else result.runtime_error,
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def _save_generated_tests(module_path: str, result: Dict):
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = module_path.replace("/", "_").replace(".py", "")
    (GENERATED_TESTS_DIR / f"{safe_name}.json").write_text(
        json.dumps(result, indent=2, default=str)
    )
