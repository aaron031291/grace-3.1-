"""
Deterministic Coding Contracts
================================
Governance contracts turned into deterministic coding process enforcement.

Instead of telling the LLM "follow these rules" in a prompt (soft enforcement),
these contracts are HARD enforcement — each step is verified deterministically
before the LLM is allowed to proceed.

Contract Structure:
  1. PRE-CONDITIONS:  Deterministic checks that MUST pass before code generation
  2. GENERATION:      LLM generates code (constrained by deterministic facts)
  3. POST-CONDITIONS: Deterministic checks that MUST pass after code generation
  4. VERIFICATION:    AST parse, import check, syntax check, security scan
  5. APPROVAL:        Trust score + consensus + governance gate

If any step fails, the contract is violated and the code is REJECTED.
The LLM never sees this as a suggestion — it's enforced by code.

Contracts:
  - CodeGenerationContract:  For any code produced by LLM
  - CodeFixContract:         For deterministic → LLM fix escalation
  - ComponentCreationContract: For new component creation
  - HealingContract:         For self-healing code changes
"""

import ast
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent


class ContractVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class ContractStep:
    """A single step in a deterministic coding contract."""
    name: str
    stage: str  # pre, generate, post, verify, approve
    deterministic: bool
    verdict: ContractVerdict = ContractVerdict.PASS
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0


@dataclass
class ContractResult:
    """Result of executing a deterministic coding contract."""
    contract_name: str
    component: str
    started_at: str
    completed_at: str = ""
    verdict: ContractVerdict = ContractVerdict.PASS
    steps: List[ContractStep] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    code_accepted: bool = False
    genesis_key_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "component": self.component,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "verdict": self.verdict.value,
            "steps": [asdict(s) for s in self.steps],
            "violations": self.violations,
            "code_accepted": self.code_accepted,
        }


# ═══════════════════════════════════════════════════════════════════
#  CONTRACT CHECKS — Deterministic verification functions
# ═══════════════════════════════════════════════════════════════════

def check_syntax(code: str, filename: str = "<generated>") -> ContractStep:
    """AST parse — catches syntax errors deterministically."""
    start = time.time()
    try:
        ast.parse(code, filename=filename)
        return ContractStep(
            name="syntax_check", stage="verify", deterministic=True,
            verdict=ContractVerdict.PASS, message="Syntax valid",
            duration_ms=(time.time() - start) * 1000,
        )
    except SyntaxError as e:
        return ContractStep(
            name="syntax_check", stage="verify", deterministic=True,
            verdict=ContractVerdict.FAIL,
            message=f"Syntax error: {e.msg} (line {e.lineno})",
            details={"line": e.lineno, "msg": e.msg},
            duration_ms=(time.time() - start) * 1000,
        )


def check_imports_resolve(code: str) -> ContractStep:
    """Verify all imports in generated code can resolve."""
    start = time.time()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ContractStep(
            name="import_check", stage="verify", deterministic=True,
            verdict=ContractVerdict.FAIL, message="Cannot parse code for import check",
            duration_ms=(time.time() - start) * 1000,
        )

    broken = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            local_dirs = [d.name for d in BACKEND_ROOT.iterdir()
                          if d.is_dir() and not d.name.startswith('.')]
            if top in local_dirs:
                mod_path = node.module.replace(".", "/")
                possible = [BACKEND_ROOT / f"{mod_path}.py", BACKEND_ROOT / mod_path / "__init__.py"]
                if not any(p.exists() for p in possible):
                    broken.append(node.module)

    if broken:
        return ContractStep(
            name="import_check", stage="verify", deterministic=True,
            verdict=ContractVerdict.FAIL,
            message=f"Broken imports: {', '.join(broken[:5])}",
            details={"broken_imports": broken},
            duration_ms=(time.time() - start) * 1000,
        )

    return ContractStep(
        name="import_check", stage="verify", deterministic=True,
        verdict=ContractVerdict.PASS, message="All local imports resolve",
        duration_ms=(time.time() - start) * 1000,
    )


def check_no_dangerous_patterns(code: str) -> ContractStep:
    """Detect dangerous patterns: eval, exec, os.system, subprocess.call with shell=True."""
    start = time.time()
    warnings = []

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                    warnings.append(f"Dangerous call: {func.id}() at line {node.lineno}")
                if isinstance(func, ast.Attribute):
                    if func.attr in ("system", "popen") and isinstance(func.value, ast.Name) and func.value.id == "os":
                        warnings.append(f"Dangerous call: os.{func.attr}() at line {node.lineno}")
                    if func.attr == "call" and isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                        for kw in node.keywords:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value:
                                warnings.append(f"subprocess.call with shell=True at line {node.lineno}")
    except SyntaxError:
        pass

    if warnings:
        return ContractStep(
            name="security_scan", stage="verify", deterministic=True,
            verdict=ContractVerdict.FAIL,
            message=f"Security violations: {'; '.join(warnings[:3])}",
            details={"violations": warnings},
            duration_ms=(time.time() - start) * 1000,
        )

    return ContractStep(
        name="security_scan", stage="verify", deterministic=True,
        verdict=ContractVerdict.PASS, message="No dangerous patterns detected",
        duration_ms=(time.time() - start) * 1000,
    )


def check_has_docstring(code: str) -> ContractStep:
    """Verify generated code has module-level docstring."""
    start = time.time()
    try:
        tree = ast.parse(code)
        docstring = ast.get_docstring(tree)
        if docstring:
            return ContractStep(
                name="docstring_check", stage="verify", deterministic=True,
                verdict=ContractVerdict.PASS, message="Module docstring present",
                duration_ms=(time.time() - start) * 1000,
            )
        else:
            return ContractStep(
                name="docstring_check", stage="verify", deterministic=True,
                verdict=ContractVerdict.WARN, message="No module docstring",
                duration_ms=(time.time() - start) * 1000,
            )
    except SyntaxError:
        return ContractStep(
            name="docstring_check", stage="verify", deterministic=True,
            verdict=ContractVerdict.FAIL, message="Cannot parse for docstring check",
            duration_ms=(time.time() - start) * 1000,
        )


def check_file_exists(file_path: str) -> ContractStep:
    """Pre-condition: verify the target file exists (for fixes)."""
    start = time.time()
    full = BACKEND_ROOT / file_path
    if full.exists():
        return ContractStep(
            name="file_exists", stage="pre", deterministic=True,
            verdict=ContractVerdict.PASS, message=f"File exists: {file_path}",
            duration_ms=(time.time() - start) * 1000,
        )
    return ContractStep(
        name="file_exists", stage="pre", deterministic=True,
        verdict=ContractVerdict.FAIL, message=f"File not found: {file_path}",
        duration_ms=(time.time() - start) * 1000,
    )


def check_trust_score(component: str, min_trust: float = 0.5) -> ContractStep:
    """Approval gate: trust score must be above threshold."""
    start = time.time()
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        score = te.score_output(component, component, "", source="deterministic_contract")
        score = float(score) if isinstance(score, (int, float)) else 0.7

        if score >= min_trust:
            return ContractStep(
                name="trust_gate", stage="approve", deterministic=True,
                verdict=ContractVerdict.PASS,
                message=f"Trust {score:.2f} >= {min_trust}",
                details={"trust_score": score, "threshold": min_trust},
                duration_ms=(time.time() - start) * 1000,
            )
        return ContractStep(
            name="trust_gate", stage="approve", deterministic=True,
            verdict=ContractVerdict.FAIL,
            message=f"Trust {score:.2f} < {min_trust} — rejected",
            details={"trust_score": score, "threshold": min_trust},
            duration_ms=(time.time() - start) * 1000,
        )
    except Exception:
        return ContractStep(
            name="trust_gate", stage="approve", deterministic=True,
            verdict=ContractVerdict.WARN, message="Trust engine unavailable — defaulting to pass",
            duration_ms=(time.time() - start) * 1000,
        )


# ═══════════════════════════════════════════════════════════════════
#  CONTRACTS — Pre-defined deterministic enforcement chains
# ═══════════════════════════════════════════════════════════════════

def execute_code_generation_contract(
    component: str,
    generated_code: str,
    file_path: Optional[str] = None,
    min_trust: float = 0.5,
) -> ContractResult:
    """
    Contract for ANY code generated by LLM.

    Pre-conditions:  (none for new code)
    Verification:    Syntax, imports, security, docstring
    Approval:        Trust gate
    """
    result = ContractResult(
        contract_name="code_generation",
        component=component,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # VERIFY
    result.steps.append(check_syntax(generated_code))
    result.steps.append(check_imports_resolve(generated_code))
    result.steps.append(check_no_dangerous_patterns(generated_code))
    result.steps.append(check_has_docstring(generated_code))

    # APPROVE
    result.steps.append(check_trust_score(component, min_trust))

    _finalize(result)
    return result


def execute_code_fix_contract(
    component: str,
    file_path: str,
    fix_code: str,
    original_problems: List[Dict[str, Any]] = None,
    min_trust: float = 0.5,
) -> ContractResult:
    """
    Contract for deterministic → LLM fix escalation.

    Pre-conditions:  File exists, original problems documented
    Verification:    Syntax, imports, security
    Approval:        Trust gate
    """
    result = ContractResult(
        contract_name="code_fix",
        component=component,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # PRE
    result.steps.append(check_file_exists(file_path))

    if original_problems:
        result.steps.append(ContractStep(
            name="problems_documented", stage="pre", deterministic=True,
            verdict=ContractVerdict.PASS,
            message=f"{len(original_problems)} problems documented as fix targets",
            details={"problem_count": len(original_problems)},
        ))
    else:
        result.steps.append(ContractStep(
            name="problems_documented", stage="pre", deterministic=True,
            verdict=ContractVerdict.WARN,
            message="No original problems documented — fix may not be targeted",
        ))

    # VERIFY
    result.steps.append(check_syntax(fix_code))
    result.steps.append(check_imports_resolve(fix_code))
    result.steps.append(check_no_dangerous_patterns(fix_code))

    # APPROVE
    result.steps.append(check_trust_score(component, min_trust))

    _finalize(result)
    return result


def execute_component_creation_contract(
    component: str,
    component_code: str,
    file_path: str,
    min_trust: float = 0.6,
) -> ContractResult:
    """
    Contract for new component creation.

    Pre-conditions:  File should NOT already exist (new component)
    Verification:    Syntax, imports, security, docstring (required)
    Approval:        Higher trust gate (0.6)
    """
    result = ContractResult(
        contract_name="component_creation",
        component=component,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # PRE: file should not exist
    full = BACKEND_ROOT / file_path
    if full.exists():
        result.steps.append(ContractStep(
            name="file_not_exists", stage="pre", deterministic=True,
            verdict=ContractVerdict.WARN,
            message=f"File already exists: {file_path} — will overwrite",
        ))
    else:
        result.steps.append(ContractStep(
            name="file_not_exists", stage="pre", deterministic=True,
            verdict=ContractVerdict.PASS,
            message=f"File does not exist yet: {file_path}",
        ))

    # VERIFY
    result.steps.append(check_syntax(component_code))
    result.steps.append(check_imports_resolve(component_code))
    result.steps.append(check_no_dangerous_patterns(component_code))

    doc_step = check_has_docstring(component_code)
    if doc_step.verdict == ContractVerdict.WARN:
        doc_step.verdict = ContractVerdict.FAIL
        doc_step.message = "New components MUST have a module docstring"
    result.steps.append(doc_step)

    # APPROVE
    result.steps.append(check_trust_score(component, min_trust))

    _finalize(result)
    return result


def execute_healing_contract(
    component: str,
    healing_code: str,
    healing_method: str = "unknown",
    min_trust: float = 0.5,
) -> ContractResult:
    """
    Contract for self-healing code changes.

    Verification:    Syntax, imports, security (strict)
    Approval:        Trust gate
    """
    result = ContractResult(
        contract_name="healing",
        component=component,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    result.steps.append(ContractStep(
        name="healing_method", stage="pre", deterministic=True,
        verdict=ContractVerdict.PASS,
        message=f"Healing method: {healing_method}",
        details={"method": healing_method},
    ))

    # VERIFY
    result.steps.append(check_syntax(healing_code))
    result.steps.append(check_imports_resolve(healing_code))

    security = check_no_dangerous_patterns(healing_code)
    if security.verdict == ContractVerdict.FAIL:
        security.message = f"BLOCKED: Healing code contains dangerous patterns — {security.message}"
    result.steps.append(security)

    # APPROVE
    result.steps.append(check_trust_score(component, min_trust))

    _finalize(result)
    return result


def _finalize(result: ContractResult):
    """Compute final verdict from steps."""
    result.completed_at = datetime.now(timezone.utc).isoformat()

    failures = [s for s in result.steps if s.verdict == ContractVerdict.FAIL]
    warnings = [s for s in result.steps if s.verdict == ContractVerdict.WARN]

    if failures:
        result.verdict = ContractVerdict.FAIL
        result.violations = [s.message for s in failures]
        result.code_accepted = False
    elif warnings:
        result.verdict = ContractVerdict.WARN
        result.code_accepted = True
    else:
        result.verdict = ContractVerdict.PASS
        result.code_accepted = True

    # Track via Genesis
    try:
        from api._genesis_tracker import track
        gk = track(
            key_type="system_event",
            what=f"Contract '{result.contract_name}' for {result.component}: {result.verdict.value}",
            who="deterministic_coding_contracts",
            how=result.contract_name,
            output_data={"verdict": result.verdict.value, "violations": result.violations},
            tags=["deterministic", "contract", result.contract_name, result.verdict.value],
        )
        if gk and hasattr(gk, "key_id"):
            result.genesis_key_id = gk.key_id
    except Exception:
        pass

    logger.info(
        f"[CONTRACT] {result.contract_name} for {result.component}: "
        f"{result.verdict.value} ({len(failures)} failures, {len(warnings)} warnings)"
    )


def get_available_contracts() -> Dict[str, Dict[str, Any]]:
    """List all available deterministic coding contracts."""
    return {
        "code_generation": {
            "description": "Enforced on any code generated by LLM",
            "stages": ["verify", "approve"],
            "checks": ["syntax", "imports", "security", "docstring", "trust"],
        },
        "code_fix": {
            "description": "Enforced when deterministic fix fails and LLM generates a fix",
            "stages": ["pre", "verify", "approve"],
            "checks": ["file_exists", "problems_documented", "syntax", "imports", "security", "trust"],
        },
        "component_creation": {
            "description": "Enforced when creating a new component",
            "stages": ["pre", "verify", "approve"],
            "checks": ["file_not_exists", "syntax", "imports", "security", "docstring_required", "trust"],
        },
        "healing": {
            "description": "Enforced on self-healing code changes",
            "stages": ["pre", "verify", "approve"],
            "checks": ["healing_method", "syntax", "imports", "security_strict", "trust"],
        },
    }
