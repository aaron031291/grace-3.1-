"""
Deterministic Validation Pipeline
===================================
Finds broken wiring, silent failures, import issues, unwired routers,
broken references, and stale logic WITHOUT using any LLM reasoning.

This is pure deterministic code analysis — AST parsing, import checking,
pattern matching, and structural verification. No non-determinism.

Categories:
1. Import Validation: Can every import resolve?
2. Router Wiring: Are all API routers registered in app.py?
3. Silent Failure Detection: Find except:pass, bare excepts, swallowed errors
4. Broken References: Imports to non-existent modules
5. Stub Detection: TODO, pass, placeholder, simplified implementations
6. Layer 1 Initialization: Are connectors initialized at startup?
7. Configuration Validation: Missing required settings
"""

import ast
import os
import sys
import logging
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent


@dataclass
class Issue:
    """A single deterministic validation issue."""
    category: str
    severity: str  # critical, warning, info
    file: str
    line: Optional[int]
    message: str
    details: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Full deterministic validation report."""
    timestamp: str
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    categories: Dict[str, int]
    issues: List[Issue]
    files_scanned: int
    scan_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "categories": self.categories,
            "issues": [asdict(i) for i in self.issues],
            "files_scanned": self.files_scanned,
            "scan_time_ms": self.scan_time_ms,
        }


# ---------------------------------------------------------------------------
# 1. Silent Failure Detection
# ---------------------------------------------------------------------------

def detect_silent_failures(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Find except blocks that swallow errors without logging.
    These are the #1 source of invisible bugs.
    """
    issues = []
    skip_dirs = {'__pycache__', 'venv', 'node_modules', '.git', 'mcp_repos'}

    for py_file in root.rglob("*.py"):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(root))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue

            body = node.body
            if not body:
                continue

            has_logging = False
            has_raise = False
            is_bare_pass = len(body) == 1 and isinstance(body[0], ast.Pass)

            for stmt in body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        func = sub.func
                        if isinstance(func, ast.Attribute):
                            if func.attr in ('error', 'warning', 'info', 'debug', 'exception', 'critical'):
                                has_logging = True
                        if isinstance(func, ast.Name):
                            if func.id in ('print', 'logging'):
                                has_logging = True
                    if isinstance(sub, ast.Raise):
                        has_raise = True

            if is_bare_pass and not has_logging and not has_raise:
                handler_type = "bare except"
                if node.type:
                    if isinstance(node.type, ast.Name):
                        handler_type = f"except {node.type.id}"
                    elif isinstance(node.type, ast.Attribute):
                        handler_type = f"except {ast.dump(node.type)}"

                issues.append(Issue(
                    category="silent_failure",
                    severity="warning",
                    file=rel_path,
                    line=node.lineno,
                    message=f"Silent failure: {handler_type}: pass (no logging, no re-raise)",
                    fix_suggestion="Add logger.error/warning or re-raise the exception",
                ))

            elif not has_logging and not has_raise and not is_bare_pass:
                all_pass_or_assign = all(
                    isinstance(s, (ast.Pass, ast.Assign, ast.Return, ast.Continue, ast.Break))
                    for s in body
                )
                if all_pass_or_assign:
                    issues.append(Issue(
                        category="silent_failure",
                        severity="info",
                        file=rel_path,
                        line=node.lineno,
                        message="Exception handler with no logging (may silently swallow errors)",
                    ))

    return issues


# ---------------------------------------------------------------------------
# 2. Router Wiring Validation
# ---------------------------------------------------------------------------

def detect_unwired_routers(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Find API router files in backend/api/ that are NOT registered in app.py.
    """
    issues = []
    api_dir = root / "api"
    app_file = root / "app.py"

    if not app_file.exists() or not api_dir.exists():
        return issues

    app_source = app_file.read_text(errors="ignore")

    for py_file in api_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "__init__.py":
            continue

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        has_router = False
        router_prefix = None

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "router":
                        has_router = True
                        if isinstance(node.value, ast.Call):
                            for kw in node.value.keywords:
                                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                    router_prefix = kw.value.value

        if not has_router:
            continue

        module_name = py_file.stem
        import_patterns = [
            f"from api.{module_name}",
            f"api.{module_name}",
            f"{module_name}_router",
            f"{module_name}.router",
        ]

        is_registered = any(p in app_source for p in import_patterns)

        if not is_registered:
            issues.append(Issue(
                category="unwired_router",
                severity="critical",
                file=f"api/{py_file.name}",
                line=None,
                message=f"Router in api/{py_file.name} (prefix: {router_prefix}) is NOT registered in app.py",
                details={"prefix": router_prefix, "module": module_name},
                fix_suggestion=f"Add 'from api.{module_name} import router as {module_name}_router' and 'app.include_router({module_name}_router)' to app.py",
            ))

    return issues


# ---------------------------------------------------------------------------
# 3. Broken Import Detection
# ---------------------------------------------------------------------------

def detect_broken_imports(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Find imports that reference modules/packages that don't exist.
    Only checks local project imports (not pip packages).
    """
    issues = []
    skip_dirs = {'__pycache__', 'venv', 'node_modules', '.git', 'mcp_repos', 'knowledge_base'}

    known_broken = set()

    for py_file in root.rglob("*.py"):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        rel_path = str(py_file.relative_to(root))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module_path = node.module.replace(".", "/")
                top_level = node.module.split(".")[0]

                local_dirs = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith('.')]

                if top_level not in local_dirs:
                    continue

                possible_paths = [
                    root / f"{module_path}.py",
                    root / module_path / "__init__.py",
                ]

                exists = any(p.exists() for p in possible_paths)

                if not exists and node.module not in known_broken:
                    known_broken.add(node.module)
                    issues.append(Issue(
                        category="broken_import",
                        severity="critical",
                        file=rel_path,
                        line=node.lineno,
                        message=f"Import from non-existent module: '{node.module}'",
                        details={"module": node.module, "checked_paths": [str(p) for p in possible_paths]},
                        fix_suggestion=f"Fix the import path or create the missing module",
                    ))

    return issues


# ---------------------------------------------------------------------------
# 4. Stub/Placeholder Detection
# ---------------------------------------------------------------------------

def detect_stubs(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Find TODO, placeholder, simplified implementations that indicate
    incomplete functionality.
    """
    issues = []
    skip_dirs = {'__pycache__', 'venv', 'node_modules', '.git', 'mcp_repos', 'knowledge_base', 'tests'}
    patterns = [
        ("TODO", "warning"),
        ("FIXME", "warning"),
        ("HACK", "info"),
        ("placeholder", "info"),
        ("simplified", "info"),
    ]

    for py_file in root.rglob("*.py"):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue

        try:
            lines = py_file.read_text(errors="ignore").split("\n")
        except Exception:
            continue

        rel_path = str(py_file.relative_to(root))

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped.startswith("#") and "\"\"\"" not in stripped and "'''" not in stripped:
                for pattern, severity in patterns:
                    if pattern in stripped and stripped.startswith("#"):
                        continue
                    if pattern.lower() in stripped.lower() and ("comment" not in stripped.lower()):
                        if pattern == "TODO" and "# TODO" in line:
                            issues.append(Issue(
                                category="stub",
                                severity=severity,
                                file=rel_path,
                                line=line_num,
                                message=f"Incomplete implementation: {stripped[:120]}",
                            ))
                            break

    return issues


# ---------------------------------------------------------------------------
# 5. Layer 1 Initialization Check
# ---------------------------------------------------------------------------

def check_layer1_initialization(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Verify that Layer 1 connectors are actually initialized at app startup.
    """
    issues = []
    app_file = root / "app.py"

    if not app_file.exists():
        return issues

    app_source = app_file.read_text(errors="ignore")

    if "initialize_layer1" not in app_source and "Layer1MessageBus" not in app_source:
        issues.append(Issue(
            category="unwired_initialization",
            severity="critical",
            file="app.py",
            line=None,
            message="Layer 1 message bus and connectors are NEVER initialized at app startup",
            details={
                "connectors_defined": [
                    "MemoryMeshConnector",
                    "GenesisKeysConnector",
                    "RAGConnector",
                    "IngestionConnector",
                    "LLMOrchestrationConnector",
                    "VersionControlConnector",
                ],
                "initialization_function": "layer1.initialize.initialize_layer1()",
            },
            fix_suggestion="Add Layer 1 initialization to app.py lifespan: from layer1.initialize import initialize_layer1; initialize_layer1()",
        ))

    init_file = root / "layer1" / "initialize.py"
    if init_file.exists():
        init_source = init_file.read_text(errors="ignore")
        if "initialize_layer1" not in init_source:
            issues.append(Issue(
                category="unwired_initialization",
                severity="warning",
                file="layer1/initialize.py",
                line=None,
                message="Layer 1 initialize.py exists but may not have initialize_layer1() function",
            ))

    return issues


# ---------------------------------------------------------------------------
# 6. Configuration Validation
# ---------------------------------------------------------------------------

def validate_configuration(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Check for configuration issues — missing required values,
    empty strings for required keys, etc.
    """
    issues = []

    try:
        sys.path.insert(0, str(root))
        from settings import settings

        critical_checks = [
            ("LLM_PROVIDER", getattr(settings, 'LLM_PROVIDER', ''), "LLM provider not configured"),
        ]

        provider = getattr(settings, 'LLM_PROVIDER', 'ollama')

        if provider == 'kimi':
            critical_checks.append(
                ("KIMI_API_KEY", getattr(settings, 'KIMI_API_KEY', ''), "Kimi is the LLM provider but KIMI_API_KEY is empty")
            )
        elif provider == 'openai':
            critical_checks.append(
                ("LLM_API_KEY", getattr(settings, 'LLM_API_KEY', ''), "OpenAI is the LLM provider but LLM_API_KEY is empty")
            )

        for name, value, msg in critical_checks:
            if not value:
                issues.append(Issue(
                    category="config_missing",
                    severity="critical",
                    file="settings.py",
                    line=None,
                    message=msg,
                    details={"setting": name, "value": "(empty)"},
                ))

        optional_checks = [
            ("KIMI_API_KEY", getattr(settings, 'KIMI_API_KEY', ''), "Kimi API key not configured — consensus engine limited"),
            ("OPUS_API_KEY", getattr(settings, 'OPUS_API_KEY', ''), "Opus API key not configured — consensus engine limited"),
            ("SERPAPI_KEY", getattr(settings, 'SERPAPI_KEY', ''), "SerpAPI key not configured — internet search disabled"),
        ]

        for name, value, msg in optional_checks:
            if not value:
                issues.append(Issue(
                    category="config_missing",
                    severity="info",
                    file="settings.py",
                    line=None,
                    message=msg,
                    details={"setting": name},
                ))

    except ImportError as e:
        issues.append(Issue(
            category="config_missing",
            severity="critical",
            file="settings.py",
            line=None,
            message=f"Cannot import settings: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 7. Kimi/Opus Connectivity Validation
# ---------------------------------------------------------------------------

def validate_kimi_opus(root: Path = BACKEND_ROOT) -> List[Issue]:
    """
    Validate Kimi and Opus are properly wired and can actually connect.
    Goes beyond just checking if API key is set.
    """
    issues = []

    try:
        sys.path.insert(0, str(root))
        from settings import settings

        # Kimi validation
        kimi_key = getattr(settings, 'KIMI_API_KEY', '')
        if kimi_key:
            try:
                from llm_orchestrator.kimi_client import KimiLLMClient
                client = KimiLLMClient()
                if not client.is_running():
                    issues.append(Issue(
                        category="kimi_opus_connectivity",
                        severity="warning",
                        file="llm_orchestrator/kimi_client.py",
                        line=None,
                        message="Kimi API key is set but is_running() returns False — API may be unreachable",
                        fix_suggestion="Verify KIMI_API_KEY is valid and KIMI_BASE_URL is correct",
                    ))
                else:
                    models = client.get_all_models()
                    if not models:
                        issues.append(Issue(
                            category="kimi_opus_connectivity",
                            severity="info",
                            file="llm_orchestrator/kimi_client.py",
                            line=None,
                            message="Kimi is running but get_all_models() returned empty — model listing may not be supported",
                        ))
            except Exception as e:
                issues.append(Issue(
                    category="kimi_opus_connectivity",
                    severity="warning",
                    file="llm_orchestrator/kimi_client.py",
                    line=None,
                    message=f"Kimi client initialization failed: {e}",
                ))

        # Opus validation
        opus_key = getattr(settings, 'OPUS_API_KEY', '')
        if opus_key:
            try:
                from llm_orchestrator.opus_client import OpusLLMClient
                client = OpusLLMClient()
                if not client.is_running():
                    issues.append(Issue(
                        category="kimi_opus_connectivity",
                        severity="warning",
                        file="llm_orchestrator/opus_client.py",
                        line=None,
                        message="Opus API key is set but is_running() returns False — API may be unreachable",
                        fix_suggestion="Verify OPUS_API_KEY is valid and OPUS_BASE_URL is correct",
                    ))
            except Exception as e:
                issues.append(Issue(
                    category="kimi_opus_connectivity",
                    severity="warning",
                    file="llm_orchestrator/opus_client.py",
                    line=None,
                    message=f"Opus client initialization failed: {e}",
                ))

    except ImportError:
        pass

    return issues


# ---------------------------------------------------------------------------
# Full Validation Pipeline
# ---------------------------------------------------------------------------

def run_full_validation(root: Path = BACKEND_ROOT) -> ValidationReport:
    """
    Run the complete deterministic validation pipeline.
    No LLM needed. Pure structural analysis.
    """
    import time
    start = time.time()

    all_issues: List[Issue] = []

    logger.info("[DETERMINISTIC-VALIDATOR] Running silent failure detection...")
    all_issues.extend(detect_silent_failures(root))

    logger.info("[DETERMINISTIC-VALIDATOR] Running router wiring check...")
    all_issues.extend(detect_unwired_routers(root))

    logger.info("[DETERMINISTIC-VALIDATOR] Running broken import detection...")
    all_issues.extend(detect_broken_imports(root))

    logger.info("[DETERMINISTIC-VALIDATOR] Running Layer 1 initialization check...")
    all_issues.extend(check_layer1_initialization(root))

    logger.info("[DETERMINISTIC-VALIDATOR] Running configuration validation...")
    all_issues.extend(validate_configuration(root))

    logger.info("[DETERMINISTIC-VALIDATOR] Running Kimi/Opus connectivity validation...")
    all_issues.extend(validate_kimi_opus(root))

    elapsed = (time.time() - start) * 1000

    py_files = sum(1 for _ in root.rglob("*.py")
                   if '__pycache__' not in str(_) and 'venv' not in str(_))

    categories = {}
    for issue in all_issues:
        categories[issue.category] = categories.get(issue.category, 0) + 1

    report = ValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_issues=len(all_issues),
        critical_count=sum(1 for i in all_issues if i.severity == "critical"),
        warning_count=sum(1 for i in all_issues if i.severity == "warning"),
        info_count=sum(1 for i in all_issues if i.severity == "info"),
        categories=categories,
        issues=all_issues,
        files_scanned=py_files,
        scan_time_ms=round(elapsed, 2),
    )

    logger.info(
        f"[DETERMINISTIC-VALIDATOR] Complete: {report.total_issues} issues "
        f"({report.critical_count} critical, {report.warning_count} warning, {report.info_count} info) "
        f"in {report.files_scanned} files ({elapsed:.0f}ms)"
    )

    return report
