"""
Spindle Blackbox Scanner — Proactive invisible-problem detector for Grace.

Runs inside the Spindle daemon on a schedule (default 120s) and deterministically
finds all "invisible" problems:  silent components, dead event handlers, orphaned
files, degradation trends, unregistered brains, plus every issue the existing
deterministic_validator already catches.

Results are published to the event bus so the healing / governance / UI layers
can act on them without anyone having to manually grep logs.
"""

import ast
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/

_PREFIX = "[SPINDLE-BLACKBOX]"


# ══════════════════════════════════════════════════════════════════════════════
#  Data classes
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BlackboxAlert:
    """A single issue surfaced by the blackbox scanner."""
    category: str
    severity: str  # critical, warning, info
    title: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    fix_suggestion: Optional[str] = None
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    occurrences: int = 1

    @property
    def key(self) -> str:
        """Stable identity used for delta comparison across scans."""
        return f"{self.category}::{self.file}::{self.line}::{self.title}"


@dataclass
class BlackboxReport:
    """Aggregated output of a full blackbox scan."""
    timestamp: str
    scan_duration_ms: float
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    categories: Dict[str, int]
    alerts: List[BlackboxAlert]
    new_alerts: List[BlackboxAlert]
    resolved_alerts: List[BlackboxAlert]
    files_scanned: int


# ══════════════════════════════════════════════════════════════════════════════
#  Individual detectors
# ══════════════════════════════════════════════════════════════════════════════

def _py_files(root: Path) -> List[Path]:
    """All .py files under *root*, excluding __pycache__ and .venv."""
    return [
        p for p in root.rglob("*.py")
        if "__pycache__" not in str(p) and ".venv" not in str(p)
    ]


# ── Existing validator bridge ────────────────────────────────────────────────

def _run_deterministic_validators(root: Path) -> List[BlackboxAlert]:
    """Call every detector in deterministic_validator and map Issues → Alerts."""
    alerts: List[BlackboxAlert] = []
    try:
        from deterministic_validator import (
            detect_silent_failures,
            detect_unwired_routers,
            detect_broken_imports,
            detect_stubs,
            validate_configuration,
            run_full_validation,
            Issue,
        )
    except Exception as exc:
        logger.warning("%s Could not import deterministic_validator: %s", _PREFIX, exc)
        return alerts

    detectors = [
        ("silent_failure", detect_silent_failures),
        ("unwired_router", detect_unwired_routers),
        ("broken_import", detect_broken_imports),
        ("stub", detect_stubs),
        ("config", validate_configuration),
    ]
    for category_tag, fn in detectors:
        try:
            issues: List[Issue] = fn(root)
            for issue in issues:
                alerts.append(BlackboxAlert(
                    category=issue.category or category_tag,
                    severity=issue.severity,
                    title=issue.message,
                    description=issue.message,
                    file=issue.file,
                    line=issue.line,
                    fix_suggestion=issue.fix_suggestion,
                ))
        except Exception as exc:
            logger.warning("%s Detector %s failed: %s", _PREFIX, category_tag, exc)
    return alerts


# ── Orphan finder bridge ─────────────────────────────────────────────────────

def _run_orphan_finder(root: Path) -> List[BlackboxAlert]:
    alerts: List[BlackboxAlert] = []
    try:
        from find_orphans import find_orphans
    except Exception as exc:
        logger.warning("%s Could not import find_orphans: %s", _PREFIX, exc)
        return alerts
    try:
        orphans = find_orphans(str(root))
        for rel in orphans:
            alerts.append(BlackboxAlert(
                category="orphan_file",
                severity="info",
                title=f"Orphaned file: {rel}",
                description=f"{rel} is never imported by any other module.",
                file=rel,
                fix_suggestion="Delete if unused, or add an import / registration.",
            ))
    except Exception as exc:
        logger.warning("%s Orphan finder failed: %s", _PREFIX, exc)
    return alerts


# ── NEW: No-output components ───────────────────────────────────────────────

_OUTPUT_PATTERNS = re.compile(
    r"""
        \blogger\b        |
        \blogging\b       |
        \bprint\s*\(      |
        \breturn\b        |
        \bpublish\s*\(    |
        \bpublish_async\s*\( |
        \bemit\s*\(       |
        \byield\b
    """,
    re.VERBOSE,
)


def detect_no_output_components(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find classes that have methods but produce no logging, return, print, or event emit."""
    alerts: List[BlackboxAlert] = []
    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py))
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [
                n for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith("_")
            ]
            if not methods:
                continue
            # Get the source lines covered by each public method
            has_output = False
            for meth in methods:
                start = meth.lineno - 1
                end = meth.end_lineno or meth.lineno
                lines = source.splitlines()[start:end]
                body_text = "\n".join(lines)
                if _OUTPUT_PATTERNS.search(body_text):
                    has_output = True
                    break
            if not has_output:
                rel = str(py.relative_to(root))
                alerts.append(BlackboxAlert(
                    category="no_output_component",
                    severity="warning",
                    title=f"Silent component: {node.name}",
                    description=(
                        f"Class {node.name} in {rel} has public methods but no "
                        "logging, return, print, or event publish."
                    ),
                    file=rel,
                    line=node.lineno,
                    fix_suggestion="Add logging or return values so behaviour is observable.",
                ))
    return alerts


# ── NEW: Dead event handlers ────────────────────────────────────────────────

def detect_dead_event_handlers(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find subscribe(...) calls whose topics are never published anywhere."""
    alerts: List[BlackboxAlert] = []
    subscribed_topics: List[Tuple[str, str, int]] = []  # (topic, file, line)
    published_topics: Set[str] = set()

    sub_re = re.compile(r"""subscribe\(\s*["']([^"']+)["']""")
    pub_re = re.compile(r"""publish(?:_async)?\(\s*["']([^"']+)["']""")

    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            for m in sub_re.finditer(line):
                subscribed_topics.append((m.group(1), rel, i))
            for m in pub_re.finditer(line):
                published_topics.add(m.group(1))

    for topic, fpath, lineno in subscribed_topics:
        # Skip wildcards — they match many topics
        if "*" in topic:
            continue
        # Check if any published topic could match
        matched = topic in published_topics
        if not matched:
            # Check prefix match (topic "llm.called" matches published "llm.called")
            prefix = topic.rsplit(".", 1)[0] + ".*" if "." in topic else None
            if prefix and prefix in published_topics:
                matched = True
        if not matched:
            alerts.append(BlackboxAlert(
                category="dead_event_handler",
                severity="warning",
                title=f"Dead handler for topic '{topic}'",
                description=(
                    f"A handler subscribes to '{topic}' in {fpath}:{lineno} "
                    "but no module ever publishes to this topic."
                ),
                file=fpath,
                line=lineno,
                fix_suggestion="Remove the dead handler or add the missing publish() call.",
            ))
    return alerts


# ── NEW: Degradation signals ────────────────────────────────────────────────

def detect_degradation_signals(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check log files for components with rising error rates."""
    alerts: List[BlackboxAlert] = []
    log_dir = root.parent / "logs"
    if not log_dir.exists():
        return alerts

    error_re = re.compile(r"\b(ERROR|CRITICAL|Exception|Traceback)\b", re.IGNORECASE)

    for log_file in log_dir.glob("*.log"):
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        if not lines:
            continue
        total = len(lines)
        errors = sum(1 for ln in lines if error_re.search(ln))
        if total < 20:
            continue
        error_rate = errors / total
        if error_rate > 0.25:
            severity = "critical" if error_rate > 0.50 else "warning"
            alerts.append(BlackboxAlert(
                category="degradation_signal",
                severity=severity,
                title=f"High error rate in {log_file.name}",
                description=(
                    f"{log_file.name}: {errors}/{total} lines "
                    f"({error_rate:.0%}) contain error indicators."
                ),
                file=str(log_file.relative_to(root.parent)),
                fix_suggestion="Investigate the errors in this log and heal the owning component.",
            ))
    return alerts


# ── NEW: Unregistered brains ────────────────────────────────────────────────

def detect_unregistered_brains(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Compare TRIGGER_REGISTRY brain references against actually registered brains."""
    alerts: List[BlackboxAlert] = []

    # 1. Gather brain names referenced in the trigger registry
    try:
        from core.unified_trigger_brain import TRIGGER_REGISTRY
    except Exception as exc:
        logger.warning("%s Could not import TRIGGER_REGISTRY: %s", _PREFIX, exc)
        return alerts

    trigger_brains: Set[str] = {t.brain for t in TRIGGER_REGISTRY}

    # 2. Gather brains actually registered in execution_registry
    registered_brains: Set[str] = set()
    try:
        from core.execution_registry import get_registry
        reg = get_registry()
        registered_brains = set(reg._brains.keys()) if hasattr(reg, "_brains") else set()
    except Exception:
        # Fallback: parse the static brains_map from the source
        reg_file = root / "core" / "execution_registry.py"
        if reg_file.exists():
            try:
                src = reg_file.read_text(encoding="utf-8", errors="ignore")
                registered_brains = set(re.findall(r'"(\w+)":\s*\(', src))
            except Exception:
                pass

    if not registered_brains:
        return alerts  # Can't compare if we don't know what's registered

    for brain in sorted(trigger_brains - registered_brains):
        alerts.append(BlackboxAlert(
            category="unregistered_brain",
            severity="critical",
            title=f"Trigger references unregistered brain '{brain}'",
            description=(
                f"The TRIGGER_REGISTRY has trigger(s) targeting brain '{brain}' "
                "but this brain is not present in the execution registry."
            ),
            file="core/unified_trigger_brain.py",
            fix_suggestion=f"Register the '{brain}' brain in execution_registry.init_registry().",
        ))
    return alerts


# ── NEW: Silent returns ─────────────────────────────────────────────────────

def detect_silent_returns(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find except blocks that return None/{}/[]/False with no logging."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", "node_modules", ".git", "mcp_repos"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler) or not node.body:
                continue
            if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
                continue
            ret = node.body[0]
            val = ret.value
            is_sentinel = (
                val is None
                or (isinstance(val, ast.Constant) and val.value in (None, False, 0))
                or isinstance(val, (ast.List, ast.Dict)) and not (val.elts if isinstance(val, ast.List) else val.keys)
            )
            if is_sentinel:
                alerts.append(BlackboxAlert(
                    category="silent_return", severity="warning",
                    title=f"Silent return on error in {rel}:{node.lineno}",
                    description=f"except block returns sentinel value with no logging.",
                    file=rel, line=node.lineno,
                    fix_suggestion="Log the exception before returning a fallback.",
                ))
    return alerts


# ── NEW: Zombie threads ─────────────────────────────────────────────────────

_ZOMBIE_THREAD_RE = re.compile(
    r"^\s*(?!.*=\s*).*threading\.Thread\(.*\)\.start\(\)", re.MULTILINE
)
_ZOMBIE_TASK_RE = re.compile(
    r"^\s*(?!.*=\s*).*asyncio\.create_task\(", re.MULTILINE
)


def detect_zombie_threads(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find thread/task starts not assigned to a variable (no lifecycle tracking)."""
    alerts: List[BlackboxAlert] = []
    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            if _ZOMBIE_THREAD_RE.match(line) or _ZOMBIE_TASK_RE.match(line):
                alerts.append(BlackboxAlert(
                    category="zombie_thread", severity="warning",
                    title=f"Untracked background thread/task",
                    description=f"Thread or task started but not assigned to a variable for lifecycle management.",
                    file=rel, line=i,
                    fix_suggestion="Assign to a variable and add a shutdown/join path.",
                ))
    return alerts


# ── NEW: Missing timeouts ───────────────────────────────────────────────────

_TIMEOUT_CALL_RE = re.compile(
    r"requests\.(get|post|put|delete|patch|head)\(|"
    r"socket\.create_connection\(|"
    r"Redis\(|"
    r"urlopen\(",
)


def detect_missing_timeouts(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find HTTP/socket/Redis calls without timeout=."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", "node_modules", ".git", "mcp_repos", "tests"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(lines, 1):
            if _TIMEOUT_CALL_RE.search(line):
                context = " ".join(lines[max(0, i - 1):min(len(lines), i + 3)])
                if "timeout" not in context:
                    alerts.append(BlackboxAlert(
                        category="missing_timeout", severity="warning",
                        title=f"No timeout on external call",
                        description=f"Call in {rel}:{i} has no timeout — can hang forever.",
                        file=rel, line=i,
                        fix_suggestion="Add timeout= parameter to prevent infinite blocking.",
                    ))
    return alerts


# ── NEW: Unmonitored services ───────────────────────────────────────────────

def detect_unmonitored_services(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find classes with start()/run()/_loop() that are not in health checks."""
    alerts: List[BlackboxAlert] = []
    health_file = root / "api" / "health.py"
    health_source = ""
    if health_file.exists():
        try:
            health_source = health_file.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            pass
    if not health_source:
        return alerts

    skip = {"__pycache__", ".venv", ".git", "tests", "mcp_repos"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip) or "test_" in py.name:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            method_names = {
                n.name for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            has_lifecycle = method_names & {"start", "run", "_loop", "_run_loop", "_heartbeat_loop"}
            if not has_lifecycle:
                continue
            if node.name.lower() in health_source:
                continue
            alerts.append(BlackboxAlert(
                category="unmonitored_service", severity="critical",
                title=f"Unmonitored service: {node.name}",
                description=f"{node.name} in {rel} has start/run methods but is not in health checks.",
                file=rel, line=node.lineno,
                fix_suggestion=f"Add {node.name} to api/health.py checks.",
            ))
    return alerts


# ── NEW: Circular imports ───────────────────────────────────────────────────

def detect_circular_imports(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Detect circular import chains among top-level imports."""
    alerts: List[BlackboxAlert] = []
    graph: Dict[str, Set[str]] = {}
    file_map: Dict[str, str] = {}  # module_key -> rel path

    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "node_modules"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        rel = str(py.relative_to(root))
        parts = list(py.relative_to(root).with_suffix("").parts)
        key = ".".join(parts)
        file_map[key] = rel
        graph.setdefault(key, set())

        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for node in ast.iter_child_nodes(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                targets = [node.module]
            for t in targets:
                if t in file_map or any(t.startswith(k.split(".")[0]) for k in file_map):
                    graph[key].add(t)

    cycles_found: List[List[str]] = []
    visited: Set[str] = set()

    def _dfs(node: str, path: List[str]):
        if len(cycles_found) >= 20 or len(path) > 5:
            return
        for dep in graph.get(node, []):
            if dep in path:
                idx = path.index(dep)
                cycle = path[idx:] + [dep]
                cycle_key = "->".join(sorted(cycle))
                if cycle_key not in visited:
                    visited.add(cycle_key)
                    cycles_found.append(cycle)
                return
            _dfs(dep, path + [dep])

    for mod in list(graph.keys()):
        if len(cycles_found) >= 20:
            break
        _dfs(mod, [mod])

    for cycle in cycles_found:
        chain = " → ".join(cycle)
        alerts.append(BlackboxAlert(
            category="circular_import", severity="warning",
            title=f"Circular import chain ({len(cycle) - 1} modules)",
            description=f"Import cycle: {chain}",
            file=file_map.get(cycle[0], cycle[0]),
            fix_suggestion="Break the cycle with deferred/lazy imports.",
        ))
    return alerts


# ── NEW: Duplicate routes ───────────────────────────────────────────────────

_ROUTER_PREFIX_RE = re.compile(r'APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)')
_ROUTE_DECORATOR_RE = re.compile(
    r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']*)["\']'
)


def detect_duplicate_routes(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find (method, path) combinations registered more than once."""
    alerts: List[BlackboxAlert] = []
    seen: Dict[str, List[str]] = {}  # "(METHOD, /full/path)" -> [files]
    api_dir = root / "api"
    if not api_dir.exists():
        return alerts

    for py in api_dir.glob("*.py"):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        prefix_m = _ROUTER_PREFIX_RE.search(source)
        prefix = prefix_m.group(1) if prefix_m else ""
        for m in _ROUTE_DECORATOR_RE.finditer(source):
            method = m.group(1).upper()
            path = prefix + m.group(2)
            key = f"{method} {path}"
            seen.setdefault(key, []).append(rel)

    for key, files in seen.items():
        if len(files) > 1:
            alerts.append(BlackboxAlert(
                category="duplicate_route", severity="critical",
                title=f"Duplicate route: {key}",
                description=f"Route {key} is registered in: {', '.join(files)}",
                file=files[0],
                fix_suggestion="Remove the duplicate or use distinct paths.",
            ))
    return alerts


# ── NEW: Unused models ──────────────────────────────────────────────────────

def detect_unused_models(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find model classes defined in models/ that are never used elsewhere."""
    alerts: List[BlackboxAlert] = []
    models_dir = root / "models"
    if not models_dir.exists():
        return alerts

    model_classes: List[Tuple[str, str, int]] = []
    for py in models_dir.glob("*.py"):
        if py.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_classes.append((node.name, rel, node.lineno))

    all_source = ""
    for py in _py_files(root):
        rel = str(py.relative_to(root))
        if rel.startswith("models"):
            continue
        try:
            all_source += py.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            continue

    for name, mfile, lineno in model_classes:
        if name not in all_source:
            alerts.append(BlackboxAlert(
                category="unused_model", severity="info",
                title=f"Unused model: {name}",
                description=f"Model {name} in {mfile} is never referenced outside models/.",
                file=mfile, line=lineno,
                fix_suggestion="Delete the model if it's dead code, or integrate it.",
            ))
    return alerts


# ── NEW: Phantom env vars ───────────────────────────────────────────────────

_ENV_VAR_RE = re.compile(r'os\.(?:environ\.get|getenv|environ\[)\s*\(\s*["\'](\w+)')
_SKIP_ENV = {"PATH", "HOME", "USER", "PYTHONPATH", "VIRTUAL_ENV", "LANG", "TERM",
             "SHELL", "LOGNAME", "HOSTNAME", "PWD", "TMPDIR", "TMP", "TEMP",
             "IS_SPINDLE_DAEMON", "PYTHONDONTWRITEBYTECODE"}


def detect_phantom_env_vars(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find env vars referenced in code but never defined in config files."""
    alerts: List[BlackboxAlert] = []
    env_refs: Dict[str, List[Tuple[str, int]]] = {}

    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            for m in _ENV_VAR_RE.finditer(line):
                var = m.group(1)
                if var not in _SKIP_ENV:
                    env_refs.setdefault(var, []).append((rel, i))

    config_text = ""
    for cfg in ["settings.py", ".env", "docker-compose.yml"]:
        fp = root / cfg
        if not fp.exists():
            fp = root.parent / cfg
        if fp.exists():
            try:
                config_text += fp.read_text(encoding="utf-8", errors="ignore") + "\n"
            except Exception:
                pass

    for var, locations in env_refs.items():
        if var not in config_text:
            first_file, first_line = locations[0]
            alerts.append(BlackboxAlert(
                category="phantom_env_var", severity="warning",
                title=f"Phantom env var: {var}",
                description=f"{var} is read in {len(locations)} place(s) but not defined in settings/env/compose.",
                file=first_file, line=first_line,
                fix_suggestion=f"Add {var} to settings.py or .env file.",
            ))
    return alerts


# ── NEW: Fire-and-forget coroutines ─────────────────────────────────────────

_FIRE_FORGET_RE = re.compile(
    r"^\s+(?!await\s)(?!\w+\s*=)"
    r"(?:asyncio\.ensure_future\(|"
    r"loop\.call_soon_threadsafe\(|"
    r"\w+\.run_coroutine_threadsafe\()",
    re.MULTILINE,
)


def detect_fire_and_forget_coroutines(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find async calls dispatched without tracking the result."""
    alerts: List[BlackboxAlert] = []
    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            if _FIRE_FORGET_RE.match(line):
                alerts.append(BlackboxAlert(
                    category="fire_and_forget", severity="warning",
                    title="Fire-and-forget coroutine",
                    description=f"Async dispatch without result tracking in {rel}:{i}",
                    file=rel, line=i,
                    fix_suggestion="Store the future/task and handle exceptions.",
                ))
    return alerts


# ── NEW: Missing error propagation ──────────────────────────────────────────

def detect_missing_error_propagation(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find functions returning None on error where return type is not Optional."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "tests"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ret_ann = node.returns
            if ret_ann is None:
                continue
            ann_str = ast.dump(ret_ann)
            if "Optional" in ann_str or "None" in ann_str:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.ExceptHandler):
                    for stmt in child.body:
                        if isinstance(stmt, ast.Return) and (
                            stmt.value is None or
                            (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)
                        ):
                            alerts.append(BlackboxAlert(
                                category="missing_error_propagation", severity="info",
                                title=f"Error swallowed in {node.name}()",
                                description=f"{node.name} returns None on error but annotation expects non-Optional.",
                                file=rel, line=child.lineno,
                                fix_suggestion="Raise the exception or change return type to Optional.",
                            ))
    return alerts


# ── NEW: Disconnected feedback loops ────────────────────────────────────────

_FEEDBACK_KEYWORDS = re.compile(r"\b(feedback|bidirectional|two.way|closed.loop)\b", re.I)


def detect_disconnected_feedback_loops(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find modules claiming feedback-loop semantics that only have one-way imports."""
    alerts: List[BlackboxAlert] = []
    imports_of: Dict[str, Set[str]] = {}
    feedback_files: Set[str] = set()

    for py in _py_files(root):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        if _FEEDBACK_KEYWORDS.search(source[:500]):
            feedback_files.add(rel)
        imported = set()
        try:
            tree = ast.parse(source)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[-1])
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        imported.add(a.name.split(".")[-1])
        except Exception:
            pass
        imports_of[rel] = imported

    for ff in feedback_files:
        stem = Path(ff).stem
        imports_me = any(stem in deps for r, deps in imports_of.items() if r != ff)
        if not imports_me:
            alerts.append(BlackboxAlert(
                category="disconnected_feedback_loop", severity="warning",
                title=f"One-way feedback loop: {ff}",
                description=f"{ff} claims feedback-loop semantics but nothing imports it back.",
                file=ff,
                fix_suggestion="Wire the return path or remove feedback-loop claims.",
            ))
    return alerts


# ── NEW: Missing shutdown hooks ─────────────────────────────────────────────

_LIFECYCLE_START = {"start", "run", "begin", "launch"}
_LIFECYCLE_STOP = {"stop", "close", "shutdown", "cleanup", "__del__", "__aexit__", "dispose"}


def detect_missing_shutdown_hooks(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find classes with start/run but no stop/close/shutdown."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "tests", "mcp_repos"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip) or "test_" in py.name:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = {
                n.name for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            has_start = bool(methods & _LIFECYCLE_START)
            has_stop = bool(methods & _LIFECYCLE_STOP)
            if has_start and not has_stop:
                alerts.append(BlackboxAlert(
                    category="missing_shutdown", severity="warning",
                    title=f"No shutdown hook: {node.name}",
                    description=f"{node.name} in {rel} has start/run but no stop/close/shutdown.",
                    file=rel, line=node.lineno,
                    fix_suggestion="Add a stop()/close()/shutdown() method.",
                ))
    return alerts


# ── NEW: Schema drift ──────────────────────────────────────────────────────

def detect_schema_drift(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find model columns not mentioned in any migration file."""
    alerts: List[BlackboxAlert] = []
    models_dir = root / "models"
    migration_dir = root / "database" / "migrations"
    if not models_dir.exists() or not migration_dir.exists():
        return alerts

    migration_text = ""
    for mf in migration_dir.glob("*.py"):
        try:
            migration_text += mf.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            pass
    if not migration_text:
        return alerts

    col_re = re.compile(r'Column\(\s*["\'](\w+)["\']')
    for py in models_dir.glob("*.py"):
        if py.name.startswith("_"):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for m in col_re.finditer(source):
            col = m.group(1)
            if col not in migration_text:
                line = source[:m.start()].count("\n") + 1
                alerts.append(BlackboxAlert(
                    category="schema_drift", severity="warning",
                    title=f"Column '{col}' has no migration",
                    description=f"Column '{col}' defined in {rel} but not in any migration file.",
                    file=rel, line=line,
                    fix_suggestion=f"Create a migration for column '{col}'.",
                ))
    return alerts


# ── NEW: Hardcoded secrets ──────────────────────────────────────────────────

_SECRET_RE = re.compile(
    r'(?:api_key|password|secret|token|auth_token|private_key)\s*=\s*["\']([^"\'{}\s]{8,})["\']',
    re.IGNORECASE,
)


def detect_hardcoded_secrets(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find hardcoded secrets in source files."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "tests", "mcp_repos", "training_corpus"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip) or "test_" in py.name:
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(lines, 1):
            if "getenv" in line or "environ" in line or "settings." in line:
                continue
            m = _SECRET_RE.search(line)
            if m:
                val = m.group(1)
                if val.startswith(("os.", "settings", "{", "self.", "config")):
                    continue
                alerts.append(BlackboxAlert(
                    category="hardcoded_secret", severity="critical",
                    title=f"Possible hardcoded secret in {rel}",
                    description=f"Line {i} contains what looks like a hardcoded credential.",
                    file=rel, line=i,
                    fix_suggestion="Move to environment variable or settings.py.",
                ))
    return alerts


# ── NEW: Unreachable code ───────────────────────────────────────────────────

_CONTROL_EXIT = (ast.Return, ast.Raise, ast.Continue, ast.Break)


def detect_unreachable_code(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find statements after return/raise/break/continue in the same block."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            _check_block_unreachable(node.body, rel, alerts)
    return alerts


def _check_block_unreachable(stmts: list, rel: str, alerts: List[BlackboxAlert]):
    for i, stmt in enumerate(stmts):
        if isinstance(stmt, _CONTROL_EXIT) and i < len(stmts) - 1:
            next_stmt = stmts[i + 1]
            if not isinstance(next_stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                alerts.append(BlackboxAlert(
                    category="unreachable_code", severity="info",
                    title=f"Unreachable code after {type(stmt).__name__}",
                    description=f"Code at line {getattr(next_stmt, 'lineno', '?')} is unreachable.",
                    file=rel, line=getattr(next_stmt, "lineno", None),
                    fix_suggestion="Remove the dead code.",
                ))
            break


# ── NEW: Stale triggers ─────────────────────────────────────────────────────

def detect_stale_triggers(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find trigger registry entries pointing to non-existent functions/modules."""
    alerts: List[BlackboxAlert] = []
    try:
        from core.unified_trigger_brain import TRIGGER_REGISTRY
    except Exception:
        return alerts

    for trigger in TRIGGER_REGISTRY:
        callable_path = getattr(trigger, "callable_path", None) or getattr(trigger, "function", None)
        if not callable_path or not isinstance(callable_path, str):
            continue
        parts = callable_path.rsplit(".", 1)
        if len(parts) != 2:
            continue
        mod_path, _func_name = parts
        file_path = root / mod_path.replace(".", os.sep)
        exists = file_path.with_suffix(".py").exists() or (file_path / "__init__.py").exists()
        if not exists:
            alerts.append(BlackboxAlert(
                category="stale_trigger", severity="warning",
                title=f"Stale trigger: {callable_path}",
                description=f"Trigger points to {callable_path} but module does not exist.",
                file="core/unified_trigger_brain.py",
                fix_suggestion="Update or remove the stale trigger entry.",
            ))
    return alerts


# ── NEW: Networking black box detectors ─────────────────────────────────────

def detect_missing_http_timeouts(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find requests.get/post/put/delete/patch calls without timeout= parameter."""
    alerts: List[BlackboxAlert] = []
    call_re = re.compile(r"""requests\.(get|post|put|delete|patch|head)\s*\(""")
    timeout_re = re.compile(r"""timeout\s*=""")
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            if call_re.search(line) and not timeout_re.search(line):
                # Check next few lines too (multi-line calls)
                block = "\n".join(source.splitlines()[i-1:min(i+4, len(source.splitlines()))])
                if not timeout_re.search(block):
                    alerts.append(BlackboxAlert(
                        category="missing_http_timeout",
                        severity="warning",
                        title=f"HTTP call without timeout",
                        description=f"requests.{call_re.search(line).group(1)}() at {rel}:{i} has no timeout= parameter. Can block forever.",
                        file=rel, line=i,
                        fix_suggestion="Add timeout=10 (or appropriate value) to the requests call.",
                    ))
    return alerts


def detect_swallowed_network_errors(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find except/catch blocks around network calls that silently swallow errors."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    # Pattern: 'except' followed by 'pass' or empty body near fetch/requests/websocket code
    pass_re = re.compile(r"""except\s*(?:Exception)?(?:\s+as\s+\w+)?\s*:\s*$""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(lines):
            stripped = line.strip()
            if pass_re.match(stripped):
                # Check if next non-empty line is just 'pass'
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    if next_line == "pass":
                        # Check if surrounding context is network-related
                        context_start = max(0, i - 10)
                        context = "\n".join(lines[context_start:i])
                        if re.search(r"requests\.|fetch|websocket|zmq|socket|httpx|aiohttp|WebSocket", context, re.IGNORECASE):
                            alerts.append(BlackboxAlert(
                                category="swallowed_network_error",
                                severity="warning",
                                title=f"Silently swallowed network error",
                                description=f"except/pass block near network call at {rel}:{i+1}. Failures become invisible.",
                                file=rel, line=i + 1,
                                fix_suggestion="Log the error or publish a diagnostic event instead of pass.",
                            ))
                    break
    return alerts


def detect_websocket_subscriber_leaks(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find WebSocket handlers that subscribe to event_bus but never unsubscribe on disconnect."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos"}
    ws_decorator_re = re.compile(r"""@\w+\.websocket\(""")
    subscribe_re = re.compile(r"""subscribe\s*\(\s*["']\*["']""")
    unsubscribe_re = re.compile(r"""unsubscribe\s*\(""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not subscribe_re.search(source):
            continue
        rel = str(py.relative_to(root))
        lines = source.splitlines()
        # Find websocket functions that subscribe but don't unsubscribe
        in_ws_func = False
        ws_func_start = 0
        func_has_subscribe = False
        func_has_unsubscribe = False
        for i, line in enumerate(lines):
            if ws_decorator_re.search(line):
                in_ws_func = True
                ws_func_start = i + 1
                func_has_subscribe = False
                func_has_unsubscribe = False
                continue
            if in_ws_func:
                if subscribe_re.search(line):
                    func_has_subscribe = True
                if unsubscribe_re.search(line):
                    func_has_unsubscribe = True
                # Detect end of function (next def/class at same or lower indent, or EOF)
                if (line.strip().startswith("def ") or line.strip().startswith("class ") or line.strip().startswith("@router.")) and i > ws_func_start + 2:
                    if func_has_subscribe and not func_has_unsubscribe:
                        alerts.append(BlackboxAlert(
                            category="websocket_subscriber_leak",
                            severity="critical",
                            title=f"WebSocket handler leaks event subscribers",
                            description=f"WebSocket at {rel}:{ws_func_start} calls subscribe('*') but never unsubscribe() on disconnect. Handlers accumulate.",
                            file=rel, line=ws_func_start,
                            fix_suggestion="Add 'finally: unsubscribe(\"*\", handler)' after the WebSocket send loop.",
                        ))
                    in_ws_func = False
        # Check last function in file
        if in_ws_func and func_has_subscribe and not func_has_unsubscribe:
            alerts.append(BlackboxAlert(
                category="websocket_subscriber_leak",
                severity="critical",
                title=f"WebSocket handler leaks event subscribers",
                description=f"WebSocket at {rel}:{ws_func_start} calls subscribe('*') but never unsubscribe() on disconnect.",
                file=rel, line=ws_func_start,
                fix_suggestion="Add 'finally: unsubscribe(\"*\", handler)' after the WebSocket send loop.",
            ))
    return alerts


def detect_zmq_bridge_problems(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Detect ZMQ bridge issues: no recv timeout, no reconnect, silent bind failures."""
    alerts: List[BlackboxAlert] = []
    event_bus = root / "cognitive" / "event_bus.py"
    if not event_bus.exists():
        return alerts
    try:
        source = event_bus.read_text(encoding="utf-8", errors="ignore")
        lines = source.splitlines()
    except Exception:
        return alerts
    rel = str(event_bus.relative_to(root))
    # Check for blocking recv without timeout
    for i, line in enumerate(lines, 1):
        if "recv_string()" in line and "timeout" not in line and "poll" not in line.lower():
            # Check surrounding context for a poller
            context = "\n".join(lines[max(0, i-10):i])
            if "poll" not in context.lower():
                alerts.append(BlackboxAlert(
                    category="zmq_no_recv_timeout",
                    severity="critical",
                    title="ZMQ recv_string() blocks forever (no timeout/poller)",
                    description=f"ZMQ sub socket at {rel}:{i} uses blocking recv with no timeout. If Spindle dies, this thread hangs forever.",
                    file=rel, line=i,
                    fix_suggestion="Use zmq.Poller with a timeout, or set RCVTIMEO on the socket.",
                ))
    # Check for missing reconnect logic
    if "while True:" in source and "_zmq_bridge_loop" in source:
        if "reconnect" not in source.lower() and "restart" not in source.lower():
            alerts.append(BlackboxAlert(
                category="zmq_no_reconnect",
                severity="warning",
                title="ZMQ bridge has no reconnect/restart logic",
                description=f"If _zmq_bridge_loop crashes, the bridge thread dies permanently. No auto-restart.",
                file=rel,
                fix_suggestion="Wrap the bridge loop in a retry with backoff, or monitor and restart the thread.",
            ))
    return alerts


def detect_missing_frontend_timeouts(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Detect frontend fetch() calls without AbortController timeout."""
    alerts: List[BlackboxAlert] = []
    frontend_root = root.parent / "frontend" / "src"
    if not frontend_root.exists():
        return alerts
    skip = {"node_modules", ".git", "dist", "build"}
    fetch_re = re.compile(r"""fetch\s*\(""")
    abort_re = re.compile(r"""AbortController|signal\s*:|timeout""", re.IGNORECASE)
    for f in frontend_root.rglob("*.jsx"):
        if any(s in f.parts for s in skip):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not fetch_re.search(source):
            continue
        rel = str(f.relative_to(root.parent))
        has_abort = abort_re.search(source)
        if not has_abort:
            # Count fetch calls
            count = len(fetch_re.findall(source))
            if count > 0:
                alerts.append(BlackboxAlert(
                    category="frontend_no_fetch_timeout",
                    severity="warning",
                    title=f"Frontend file has {count} fetch() call(s) with no timeout",
                    description=f"{rel} makes {count} fetch() calls but uses no AbortController/signal for timeouts. UI can hang if backend is slow.",
                    file=rel,
                    fix_suggestion="Use AbortController with AbortSignal.timeout(ms) on fetch calls.",
                ))
    return alerts


def detect_no_retry_http_clients(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find HTTP client modules that make external API calls without retry logic."""
    alerts: List[BlackboxAlert] = []
    # Check LLM clients and similar external-facing modules
    client_dirs = [root / "llm_orchestrator", root / "scraping"]
    retry_re = re.compile(r"""retry|backoff|retries|attempt|max_retries""", re.IGNORECASE)
    request_re = re.compile(r"""requests\.(get|post|put|delete|patch)|httpx\.|aiohttp\.""")
    skip = {"__pycache__", ".venv"}
    for cdir in client_dirs:
        if not cdir.exists():
            continue
        for py in cdir.rglob("*.py"):
            if any(s in py.parts for s in skip):
                continue
            try:
                source = py.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not request_re.search(source):
                continue
            rel = str(py.relative_to(root))
            if not retry_re.search(source):
                alerts.append(BlackboxAlert(
                    category="no_retry_http_client",
                    severity="warning",
                    title=f"HTTP client has no retry logic",
                    description=f"{rel} makes external HTTP calls but has no retry/backoff logic. Transient failures cause immediate failure.",
                    file=rel,
                    fix_suggestion="Add retry with exponential backoff for transient errors (429, 500, 502, 503, ConnectionError).",
                ))
    return alerts


def detect_no_backend_offline_indicator(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check if the frontend App has a global backend-offline banner."""
    alerts: List[BlackboxAlert] = []
    app_jsx = root.parent / "frontend" / "src" / "App.jsx"
    if not app_jsx.exists():
        return alerts
    try:
        source = app_jsx.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return alerts
    offline_re = re.compile(r"""offline|backend.*(down|unreachable|disconnected)|connection.*(lost|failed|status)""", re.IGNORECASE)
    if not offline_re.search(source):
        alerts.append(BlackboxAlert(
            category="no_offline_indicator",
            severity="info",
            title="Frontend has no global backend-offline indicator",
            description="App.jsx has no visible 'backend offline' banner. Users see blank/loading tabs when backend is down.",
            file="frontend/src/App.jsx",
            fix_suggestion="Add a banner that shows when healthCheck() returns null, indicating backend is unreachable.",
        ))
    return alerts


# ── NEW: Half-open / no-keepalive connections ───────────────────────────────

def detect_no_keepalive_connections(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find HTTP sessions / connection pools created without keepalive or pool limits."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    session_re = re.compile(r"""(requests\.Session|httpx\.Client|httpx\.AsyncClient|aiohttp\.ClientSession)\s*\(""")
    pool_re = re.compile(r"""pool_connections|pool_maxsize|limits|max_keepalive|keepalive|pool_size""", re.IGNORECASE)
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not session_re.search(source):
            continue
        rel = str(py.relative_to(root))
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if session_re.search(line):
                block = "\n".join(lines[max(0, i - 1):min(i + 8, len(lines))])
                if not pool_re.search(block):
                    alerts.append(BlackboxAlert(
                        category="no_keepalive_or_pool_limit",
                        severity="warning",
                        title=f"HTTP session without pool/keepalive config",
                        description=f"Session created at {rel}:{i} has no pool_connections, pool_maxsize, or keepalive config. Can exhaust connections.",
                        file=rel, line=i,
                        fix_suggestion="Set pool_connections, pool_maxsize, or connection limits on the session.",
                    ))
    return alerts


# ── NEW: Unclosed connections / sockets ─────────────────────────────────────

def detect_unclosed_connections(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find socket/connection opens that are not in a with-block or try/finally."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    open_re = re.compile(r"""(socket\.create_connection|socket\.socket|open\s*\(|urlopen\s*\()\s*""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not open_re.search(source):
            continue
        rel = str(py.relative_to(root))
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if open_re.search(stripped):
                # Check if it's inside a 'with' statement
                if stripped.startswith("with "):
                    continue
                # Check if previous non-empty line is 'with'
                for j in range(i - 2, max(i - 4, -1), -1):
                    if j >= 0 and lines[j].strip().startswith("with "):
                        break
                else:
                    # Check for try/finally nearby
                    context = "\n".join(lines[max(0, i - 3):min(i + 10, len(lines))])
                    if "finally" not in context and ".close()" not in context:
                        alerts.append(BlackboxAlert(
                            category="unclosed_connection",
                            severity="warning",
                            title=f"Connection opened without with-block or close()",
                            description=f"Connection at {rel}:{i} is not in a with-block and has no visible close(). May leak file descriptors.",
                            file=rel, line=i,
                            fix_suggestion="Use a with-block or ensure close() in a finally block.",
                        ))
    return alerts


# ── NEW: No circuit breaker coverage ────────────────────────────────────────

def detect_missing_circuit_breakers(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find external service calls that aren't protected by a circuit breaker."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus", "tests"}
    external_re = re.compile(r"""(requests\.(get|post|put|delete|patch)|httpx\.(get|post)|aiohttp)\s*\(""")
    breaker_re = re.compile(r"""circuit.?breaker|get_breaker|CircuitBreaker|cb\.|breaker\.""", re.IGNORECASE)
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not external_re.search(source):
            continue
        rel = str(py.relative_to(root))
        # Check if the file has ANY circuit breaker usage
        if not breaker_re.search(source):
            # Only flag files that call external URLs (not localhost)
            if re.search(r"""https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)""", source):
                alerts.append(BlackboxAlert(
                    category="no_circuit_breaker",
                    severity="info",
                    title=f"External HTTP calls without circuit breaker",
                    description=f"{rel} makes external HTTP calls but has no circuit breaker protection. Cascading failures possible.",
                    file=rel,
                    fix_suggestion="Wrap external calls with get_breaker('service_name').call(lambda: ...)",
                ))
    return alerts


# ── NEW: Unbounded queue / no backpressure ──────────────────────────────────

def detect_unbounded_queues(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find asyncio.Queue() or queue.Queue() created without maxsize."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    queue_re = re.compile(r"""(asyncio\.Queue|queue\.Queue)\s*\(\s*\)""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(source.splitlines(), 1):
            if queue_re.search(line):
                alerts.append(BlackboxAlert(
                    category="unbounded_queue",
                    severity="warning",
                    title=f"Queue without maxsize (no backpressure)",
                    description=f"Queue at {rel}:{i} has no maxsize. Under load, memory grows unbounded until OOM.",
                    file=rel, line=i,
                    fix_suggestion="Set maxsize (e.g. Queue(maxsize=1000)) and handle QueueFull.",
                ))
    return alerts


# ── NEW: No WebSocket heartbeat / ping ──────────────────────────────────────

def detect_no_websocket_heartbeat(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find WebSocket endpoints that have no ping/pong or heartbeat mechanism."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos"}
    ws_re = re.compile(r"""@\w+\.websocket\(""")
    heartbeat_re = re.compile(r"""ping|pong|heartbeat|health_update|keep.?alive""", re.IGNORECASE)
    timeout_re = re.compile(r"""wait_for.*timeout|asyncio\.timeout|RCVTIMEO""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not ws_re.search(source):
            continue
        rel = str(py.relative_to(root))
        lines = source.splitlines()
        in_ws = False
        ws_start = 0
        func_body = []
        for i, line in enumerate(lines):
            if ws_re.search(line):
                # Flush previous
                if in_ws and func_body:
                    body = "\n".join(func_body)
                    if not heartbeat_re.search(body) and not timeout_re.search(body):
                        alerts.append(BlackboxAlert(
                            category="no_websocket_heartbeat",
                            severity="info",
                            title=f"WebSocket has no heartbeat/ping mechanism",
                            description=f"WebSocket at {rel}:{ws_start} has no ping/pong or timeout. Half-open connections won't be detected.",
                            file=rel, line=ws_start,
                            fix_suggestion="Add periodic ping/pong, or use asyncio.wait_for with a timeout on receive.",
                        ))
                in_ws = True
                ws_start = i + 1
                func_body = []
                continue
            if in_ws:
                func_body.append(line)
                # Detect end of function
                if line.strip() and not line[0].isspace() and i > ws_start + 2:
                    body = "\n".join(func_body)
                    if not heartbeat_re.search(body) and not timeout_re.search(body):
                        alerts.append(BlackboxAlert(
                            category="no_websocket_heartbeat",
                            severity="info",
                            title=f"WebSocket has no heartbeat/ping mechanism",
                            description=f"WebSocket at {rel}:{ws_start} has no ping/pong or timeout.",
                            file=rel, line=ws_start,
                            fix_suggestion="Add periodic ping/pong, or use asyncio.wait_for with a timeout on receive.",
                        ))
                    in_ws = False
        # Check last function in file
        if in_ws and func_body:
            body = "\n".join(func_body)
            if not heartbeat_re.search(body) and not timeout_re.search(body):
                alerts.append(BlackboxAlert(
                    category="no_websocket_heartbeat",
                    severity="info",
                    title=f"WebSocket has no heartbeat/ping mechanism",
                    description=f"WebSocket at {rel}:{ws_start} has no ping/pong or timeout.",
                    file=rel, line=ws_start,
                    fix_suggestion="Add periodic ping/pong, or use asyncio.wait_for with a timeout on receive.",
                ))
    return alerts


# ── NEW: Fire-and-forget HTTP requests ──────────────────────────────────────

def detect_fire_and_forget_http(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find HTTP calls whose response is never checked or assigned."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    call_re = re.compile(r"""^\s*requests\.(get|post|put|delete|patch)\s*\(""")
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(py.relative_to(root))
        for i, line in enumerate(lines, 1):
            # Line starts with requests.post(...) with no assignment
            if call_re.match(line):
                stripped = line.strip()
                if not stripped.startswith(("r ", "r=", "res ", "res=", "resp", "response", "_", "result")):
                    if "=" not in stripped.split("requests.")[0]:
                        alerts.append(BlackboxAlert(
                            category="fire_and_forget_http",
                            severity="warning",
                            title=f"Fire-and-forget HTTP request",
                            description=f"HTTP call at {rel}:{i} discards the response. No way to know if it succeeded.",
                            file=rel, line=i,
                            fix_suggestion="Assign the response and check status_code or raise_for_status().",
                        ))
    return alerts


# ── NEW: No idempotency on retries ─────────────────────────────────────────

def detect_no_idempotency_on_retry(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find retry loops around POST/PUT/DELETE that don't use idempotency keys."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos", "training_corpus"}
    retry_re = re.compile(r"""(for\s+\w+\s+in\s+range|while\s+.*retries|retry|attempt|@retry|backoff)""", re.IGNORECASE)
    mutating_re = re.compile(r"""requests\.(post|put|delete|patch)\s*\(""")
    idempotency_re = re.compile(r"""idempoten|Idempotency.Key|X-Request-ID|dedup""", re.IGNORECASE)
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not retry_re.search(source) or not mutating_re.search(source):
            continue
        rel = str(py.relative_to(root))
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if retry_re.search(line):
                # Check the next 15 lines for a mutating call without idempotency
                block = "\n".join(lines[i:min(i + 15, len(lines))])
                if mutating_re.search(block) and not idempotency_re.search(block):
                    alerts.append(BlackboxAlert(
                        category="no_idempotency_on_retry",
                        severity="info",
                        title=f"Retry loop with mutating HTTP call, no idempotency key",
                        description=f"Retry logic at {rel}:{i} retries POST/PUT/DELETE but has no idempotency key. Can cause duplicate processing.",
                        file=rel, line=i,
                        fix_suggestion="Add an Idempotency-Key or X-Request-ID header to prevent duplicate side effects.",
                    ))
                    break  # One alert per file is enough
    return alerts


# ── NEW: Frontend silent catch blocks ───────────────────────────────────────

def detect_frontend_silent_catches(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find frontend .catch(() => {}) and catch { /* silent */ } around network calls."""
    alerts: List[BlackboxAlert] = []
    frontend_root = root.parent / "frontend" / "src"
    if not frontend_root.exists():
        return alerts
    skip = {"node_modules", ".git", "dist", "build"}
    silent_re = re.compile(r"""\.catch\s*\(\s*\(\s*\)\s*=>\s*\{\s*\}\s*\)|\.catch\s*\(\s*\(\s*\)\s*=>\s*(?:null|undefined)\s*\)|catch\s*\{\s*/\*\s*silent""")
    for f in frontend_root.rglob("*.jsx"):
        if any(s in f.parts for s in skip):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = str(f.relative_to(root.parent))
        lines = source.splitlines()
        count = 0
        for i, line in enumerate(lines, 1):
            if silent_re.search(line):
                count += 1
        if count > 0:
            alerts.append(BlackboxAlert(
                category="frontend_silent_catch",
                severity="warning",
                title=f"Frontend has {count} silent .catch() block(s)",
                description=f"{rel} has {count} .catch(() => {{}}) blocks that silently swallow network errors. Users see blank/loading state.",
                file=rel,
                fix_suggestion="Log errors, show a toast notification, or set an error state for the UI.",
            ))
    return alerts


# ── NEW: Frontend WS without reconnect ──────────────────────────────────────

def detect_frontend_ws_no_reconnect(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find frontend WebSocket connections that have no reconnect logic."""
    alerts: List[BlackboxAlert] = []
    frontend_root = root.parent / "frontend" / "src"
    if not frontend_root.exists():
        return alerts
    skip = {"node_modules", ".git", "dist", "build"}
    ws_re = re.compile(r"""new\s+WebSocket\s*\(""")
    reconnect_re = re.compile(r"""reconnect|setTimeout\s*\(\s*connect|onclose.*connect""", re.IGNORECASE)
    for f in frontend_root.rglob("*.jsx"):
        if any(s in f.parts for s in skip):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not ws_re.search(source):
            continue
        rel = str(f.relative_to(root.parent))
        if not reconnect_re.search(source):
            alerts.append(BlackboxAlert(
                category="frontend_ws_no_reconnect",
                severity="warning",
                title=f"Frontend WebSocket has no reconnect logic",
                description=f"{rel} creates a WebSocket but has no reconnect on close/error. Connection loss is permanent.",
                file=rel,
                fix_suggestion="Add an onclose handler that reconnects with exponential backoff.",
            ))
    return alerts


# ── NEW: No error rate tracking / aggregation ──────────────────────────────

def detect_no_error_rate_tracking(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check if the codebase has any error rate counting / metrics aggregation."""
    alerts: List[BlackboxAlert] = []
    metrics_re = re.compile(r"""error.?count|error.?rate|failure.?count|prometheus|statsd|metrics\.inc|counter\.inc|error_counter""", re.IGNORECASE)
    # Scan all API files for any form of error counting
    api_dir = root / "api"
    if not api_dir.exists():
        return alerts
    has_metrics = False
    for py in api_dir.rglob("*.py"):
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
            if metrics_re.search(source):
                has_metrics = True
                break
        except Exception:
            continue
    if not has_metrics:
        alerts.append(BlackboxAlert(
            category="no_error_rate_tracking",
            severity="info",
            title="No error rate tracking in API layer",
            description="No error counter, metrics, or rate tracking found in api/. Individual errors are logged but never aggregated.",
            file="api/",
            fix_suggestion="Add a simple error counter (dict or prometheus) to track error rates per endpoint per time window.",
        ))
    return alerts


# ── NEW: No latency tracking ───────────────────────────────────────────────

def detect_no_latency_tracking(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check if HTTP/API calls track response latency."""
    alerts: List[BlackboxAlert] = []
    latency_re = re.compile(r"""latency|response.?time|elapsed|duration_ms|perf_counter|timer|histogram""", re.IGNORECASE)
    # Check LLM orchestrator and API layer
    check_dirs = [root / "llm_orchestrator", root / "api"]
    for cdir in check_dirs:
        if not cdir.exists():
            continue
        has_latency = False
        for py in cdir.rglob("*.py"):
            try:
                source = py.read_text(encoding="utf-8", errors="ignore")
                if latency_re.search(source):
                    has_latency = True
                    break
            except Exception:
                continue
        if not has_latency:
            rel = str(cdir.relative_to(root))
            alerts.append(BlackboxAlert(
                category="no_latency_tracking",
                severity="info",
                title=f"No latency tracking in {rel}/",
                description=f"No response time or latency measurement found in {rel}/. Slowdowns are invisible until timeout.",
                file=rel,
                fix_suggestion="Measure time.perf_counter() around external calls and log or publish latency metrics.",
            ))
    return alerts


# ── NEW: Stale WebSocket state (frontend) ──────────────────────────────────

def detect_frontend_stale_ws_state(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find frontend WebSocket consumers that show 'connected' but have no staleness check."""
    alerts: List[BlackboxAlert] = []
    frontend_root = root.parent / "frontend" / "src"
    if not frontend_root.exists():
        return alerts
    skip = {"node_modules", ".git", "dist", "build"}
    ws_re = re.compile(r"""new\s+WebSocket\s*\(""")
    stale_re = re.compile(r"""last.?message|last.?update|stale|heartbeat.?timeout|ping.?interval|data.?age""", re.IGNORECASE)
    for f in frontend_root.rglob("*.jsx"):
        if any(s in f.parts for s in skip):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not ws_re.search(source):
            continue
        rel = str(f.relative_to(root.parent))
        if not stale_re.search(source):
            alerts.append(BlackboxAlert(
                category="frontend_stale_ws_state",
                severity="info",
                title=f"WebSocket consumer has no staleness detection",
                description=f"{rel} reads from a WebSocket but never checks if data is stale. UI may show old data after silent disconnect.",
                file=rel,
                fix_suggestion="Track lastMessageTime and show a 'data may be stale' indicator after N seconds of silence.",
            ))
    return alerts


# ── NEW: IPC echo loop risk ────────────────────────────────────────────────

def detect_ipc_echo_loop_risk(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find event bus subscribers that publish to the same bus without source filtering."""
    alerts: List[BlackboxAlert] = []
    skip = {"__pycache__", ".venv", ".git", "mcp_repos"}
    sub_re = re.compile(r"""subscribe\s*\(\s*["']\*["']""")
    pub_re = re.compile(r"""publish\s*\(|publish_async\s*\(""")
    source_filter_re = re.compile(r"""source.*==|\.source\s*!=|zmq_peer|skip.*source""", re.IGNORECASE)
    for py in root.rglob("*.py"):
        if any(s in py.parts for s in skip):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not sub_re.search(source) or not pub_re.search(source):
            continue
        rel = str(py.relative_to(root))
        # File subscribes to everything AND publishes — check for source filtering
        if not source_filter_re.search(source):
            alerts.append(BlackboxAlert(
                category="ipc_echo_loop_risk",
                severity="warning",
                title=f"Potential IPC echo loop: subscribe('*') + publish without source filter",
                description=f"{rel} subscribes to all events and publishes events but has no source filter to prevent echo loops.",
                file=rel,
                fix_suggestion="Check event.source before re-publishing to avoid infinite echo loops.",
            ))
    return alerts


# ══════════════════════════════════════════════════════════════════════════════
#  Frontend black-box detectors
# ══════════════════════════════════════════════════════════════════════════════

def _jsx_files(root: Path) -> List[Tuple[Path, str]]:
    """Yield (path, relative_path) for all .jsx/.tsx files under frontend/src."""
    frontend = root.parent / "frontend" / "src"
    if not frontend.exists():
        return []
    skip = {"node_modules", ".git", "dist", "build"}
    results = []
    for ext in ("*.jsx", "*.tsx", "*.js"):
        for f in frontend.rglob(ext):
            if any(s in f.parts for s in skip):
                continue
            results.append((f, str(f.relative_to(root.parent))))
    return results


def detect_no_error_boundary_wrapping(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check if lazy-loaded routes/tabs are wrapped in ErrorBoundary."""
    alerts: List[BlackboxAlert] = []
    app_file = root.parent / "frontend" / "src" / "App.jsx"
    if not app_file.exists():
        return alerts
    try:
        source = app_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return alerts
    has_lazy = "lazy(" in source
    has_boundary = "ErrorBoundary" in source
    if has_lazy and not has_boundary:
        alerts.append(BlackboxAlert(
            category="no_error_boundary",
            severity="warning",
            title="Lazy-loaded components not wrapped in ErrorBoundary",
            description="App.jsx uses lazy() for code-splitting but no ErrorBoundary wraps them. A chunk load failure crashes the whole app.",
            file="frontend/src/App.jsx",
            fix_suggestion="Wrap <Suspense> blocks with <ErrorBoundary> to catch chunk load and render failures.",
        ))
    return alerts


def detect_useeffect_memory_leaks(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find setInterval/setTimeout/addEventListener in useEffect without cleanup return."""
    alerts: List[BlackboxAlert] = []
    effect_re = re.compile(r"""useEffect\s*\(\s*\(\s*\)\s*=>\s*\{""")
    timer_re = re.compile(r"""setInterval\s*\(|setTimeout\s*\(|addEventListener\s*\(""")
    cleanup_re = re.compile(r"""return\s*\(\s*\)\s*=>|clearInterval|clearTimeout|removeEventListener""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not timer_re.search(source):
            continue
        lines = source.splitlines()
        in_effect = False
        effect_start = 0
        brace_depth = 0
        effect_body = []
        for i, line in enumerate(lines, 1):
            if effect_re.search(line):
                in_effect = True
                effect_start = i
                brace_depth = line.count("{") - line.count("}")
                effect_body = [line]
                continue
            if in_effect:
                brace_depth += line.count("{") - line.count("}")
                effect_body.append(line)
                if brace_depth <= 0:
                    body = "\n".join(effect_body)
                    if timer_re.search(body) and not cleanup_re.search(body):
                        alerts.append(BlackboxAlert(
                            category="useeffect_memory_leak",
                            severity="warning",
                            title=f"useEffect timer/listener without cleanup",
                            description=f"useEffect at {rel}:{effect_start} sets interval/timeout/listener but has no cleanup return. Leaks on unmount.",
                            file=rel, line=effect_start,
                            fix_suggestion="Return a cleanup function: return () => { clearInterval(id); }",
                        ))
                    in_effect = False
                    effect_body = []
    return alerts


def detect_fetch_race_conditions(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find components that fetch in useEffect without aborting previous requests."""
    alerts: List[BlackboxAlert] = []
    effect_re = re.compile(r"""useEffect\s*\(""")
    fetch_re = re.compile(r"""fetch\s*\(|\.then\s*\(""")
    abort_re = re.compile(r"""AbortController|abort|cancelled|ignore|stale|isMounted|active""", re.IGNORECASE)
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not effect_re.search(source) or not fetch_re.search(source):
            continue
        lines = source.splitlines()
        in_effect = False
        effect_start = 0
        brace_depth = 0
        effect_body = []
        found_any = False
        for i, line in enumerate(lines, 1):
            if effect_re.search(line):
                in_effect = True
                effect_start = i
                brace_depth = line.count("{") - line.count("}")
                effect_body = [line]
                continue
            if in_effect:
                brace_depth += line.count("{") - line.count("}")
                effect_body.append(line)
                if brace_depth <= 0:
                    body = "\n".join(effect_body)
                    if fetch_re.search(body) and not abort_re.search(body):
                        if not found_any:
                            alerts.append(BlackboxAlert(
                                category="fetch_race_condition",
                                severity="info",
                                title=f"useEffect fetch without abort/cancellation",
                                description=f"useEffect at {rel}:{effect_start} fetches data but doesn't abort on re-render. Responses can arrive out of order.",
                                file=rel, line=effect_start,
                                fix_suggestion="Use AbortController or a `let active = true` flag with cleanup to prevent stale updates.",
                            ))
                            found_any = True
                    in_effect = False
                    effect_body = []
    return alerts


def detect_missing_empty_states(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find .map() rendering without a length check or empty fallback."""
    alerts: List[BlackboxAlert] = []
    map_re = re.compile(r"""\.map\s*\(\s*\(""")
    empty_re = re.compile(r"""\.length\s*(===?\s*0|>\s*0|!)|empty|no\s+(items|results|data)|nothing\s+to|"No\s+|'No\s+""", re.IGNORECASE)
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not map_re.search(source):
            continue
        map_count = len(map_re.findall(source))
        if not empty_re.search(source) and map_count >= 2:
            alerts.append(BlackboxAlert(
                category="missing_empty_state",
                severity="info",
                title=f"Component renders lists without empty state fallback",
                description=f"{rel} has {map_count} .map() calls but no empty state check. Zero results shows a blank void.",
                file=rel,
                fix_suggestion="Add {items.length === 0 && <div>No items found</div>} before or around .map() calls.",
            ))
    return alerts


def detect_dangerously_set_innerhtml(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find dangerouslySetInnerHTML usage (XSS risk)."""
    alerts: List[BlackboxAlert] = []
    danger_re = re.compile(r"""dangerouslySetInnerHTML""")
    sanitize_re = re.compile(r"""DOMPurify|sanitize|dompurify|xss|escapeHtml""", re.IGNORECASE)
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if danger_re.search(line):
                if not sanitize_re.search(source):
                    alerts.append(BlackboxAlert(
                        category="xss_dangerously_set",
                        severity="critical",
                        title=f"dangerouslySetInnerHTML without sanitization",
                        description=f"{rel}:{i} uses dangerouslySetInnerHTML with no DOMPurify/sanitize. XSS vulnerability.",
                        file=rel, line=i,
                        fix_suggestion="Sanitize with DOMPurify.sanitize(html) before injecting.",
                    ))
    return alerts


def detect_localstorage_secrets(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find localStorage usage storing tokens, keys, or secrets."""
    alerts: List[BlackboxAlert] = []
    storage_re = re.compile(r"""localStorage\.(setItem|getItem)\s*\(\s*['"]([^'"]+)['"]""")
    secret_words = {"token", "key", "secret", "password", "api_key", "apikey", "auth", "jwt", "bearer", "credential"}
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(source.splitlines(), 1):
            m = storage_re.search(line)
            if m:
                stored_key = m.group(2).lower()
                if any(w in stored_key for w in secret_words):
                    alerts.append(BlackboxAlert(
                        category="localstorage_secret",
                        severity="warning",
                        title=f"Sensitive data in localStorage: '{m.group(2)}'",
                        description=f"{rel}:{i} stores '{m.group(2)}' in localStorage. Accessible to any XSS attack.",
                        file=rel, line=i,
                        fix_suggestion="Use httpOnly cookies for auth tokens, or encrypt before storing.",
                    ))
    return alerts


def detect_console_log_in_production(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find excessive console.log calls in frontend production code."""
    alerts: List[BlackboxAlert] = []
    console_re = re.compile(r"""console\.(log|debug|info|warn|error)\s*\(""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        count = len(console_re.findall(source))
        if count >= 5:
            alerts.append(BlackboxAlert(
                category="console_log_pollution",
                severity="info",
                title=f"Excessive console logging ({count} calls)",
                description=f"{rel} has {count} console.log/warn/error calls. Pollutes browser console, leaks internal info.",
                file=rel,
                fix_suggestion="Remove debug logs or gate behind import.meta.env.DEV check.",
            ))
    return alerts


def detect_no_loading_states(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find components with fetch calls but no loading indicator state."""
    alerts: List[BlackboxAlert] = []
    fetch_re = re.compile(r"""fetch\s*\(""")
    loading_re = re.compile(r"""loading|isLoading|setLoading|pending|fetching|spinner|skeleton""", re.IGNORECASE)
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not fetch_re.search(source):
            continue
        fetch_count = len(fetch_re.findall(source))
        if fetch_count >= 2 and not loading_re.search(source):
            alerts.append(BlackboxAlert(
                category="no_loading_state",
                severity="info",
                title=f"Component fetches data ({fetch_count}x) with no loading indicator",
                description=f"{rel} makes {fetch_count} fetch calls but has no loading/spinner state. Users see blank content while waiting.",
                file=rel,
                fix_suggestion="Add a loading state: const [loading, setLoading] = useState(true);",
            ))
    return alerts


def detect_missing_key_prop(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find .map() JSX rendering that might be missing key props."""
    alerts: List[BlackboxAlert] = []
    # Pattern: .map((item) => (<div ... without key=
    map_re = re.compile(r"""\.map\s*\(\s*\([^)]*\)\s*=>\s*\(?\s*<\w+(?!\s[^>]*key\s*=)""")
    # Also catch .map((item, i) => <tag without key
    map_re2 = re.compile(r"""\.map\s*\(\s*\([^)]*,\s*\w+\)\s*=>\s*\(?\s*<\w+(?!\s[^>]*key\s*=)""")
    for fpath, rel in _jsx_files(root):
        if "node_modules" in str(fpath):
            continue
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Simple heuristic: .map() calls that don't have key= nearby
        maps = re.findall(r"""\.map\s*\(""", source)
        keys = re.findall(r"""key\s*=\s*\{""", source)
        if len(maps) > len(keys) + 1 and len(maps) >= 3:
            alerts.append(BlackboxAlert(
                category="missing_key_prop",
                severity="info",
                title=f"Possible missing key props in list rendering",
                description=f"{rel} has {len(maps)} .map() calls but only {len(keys)} key= props. Missing keys cause subtle re-render bugs.",
                file=rel,
                fix_suggestion="Add key={item.id} or key={index} to the root element in each .map() callback.",
            ))
    return alerts


def detect_no_frontend_error_reporting(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Check if the frontend has any error reporting/tracking service."""
    alerts: List[BlackboxAlert] = []
    frontend_root = root.parent / "frontend" / "src"
    if not frontend_root.exists():
        return alerts
    tracking_re = re.compile(r"""Sentry|LogRocket|Bugsnag|DataDog|trackError|reportError|errorReporting|window\.onerror|globalThis\.onerror""", re.IGNORECASE)
    found = False
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
            if tracking_re.search(source):
                found = True
                break
        except Exception:
            continue
    if not found:
        alerts.append(BlackboxAlert(
            category="no_frontend_error_reporting",
            severity="info",
            title="No frontend error reporting/tracking service",
            description="No Sentry, LogRocket, Bugsnag, or custom error reporting found. JS errors are only visible in browser console.",
            file="frontend/src/",
            fix_suggestion="Add window.onerror / window.onunhandledrejection handler that posts errors to backend.",
        ))
    return alerts


def detect_missing_accessibility(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find interactive elements without accessibility attributes."""
    alerts: List[BlackboxAlert] = []
    onclick_re = re.compile(r"""onClick\s*=\s*\{""")
    a11y_re = re.compile(r"""aria-label|aria-describedby|role=|onKeyDown|onKeyPress|onKeyUp|tabIndex""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        onclick_count = len(onclick_re.findall(source))
        a11y_count = len(a11y_re.findall(source))
        # Flag if many click handlers but very few accessibility attrs
        if onclick_count >= 5 and a11y_count == 0:
            alerts.append(BlackboxAlert(
                category="missing_accessibility",
                severity="info",
                title=f"Component has {onclick_count} onClick handlers, no keyboard/ARIA support",
                description=f"{rel} has {onclick_count} click handlers but no aria-label, role, onKeyDown, or tabIndex. Not keyboard/screen-reader accessible.",
                file=rel,
                fix_suggestion="Add onKeyDown handlers, aria-label, role='button', and tabIndex={0} to interactive elements.",
            ))
    return alerts


def detect_unhandled_promise_rejections(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find async functions or .then() chains with no .catch() or try/catch."""
    alerts: List[BlackboxAlert] = []
    async_re = re.compile(r"""async\s+\w+\s*=\s*async\s*\(|async\s+function\s+\w+|const\s+\w+\s*=\s*async""")
    try_re = re.compile(r"""try\s*\{""")
    catch_re = re.compile(r"""\.catch\s*\(|catch\s*\(""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        async_count = len(async_re.findall(source))
        try_count = len(try_re.findall(source))
        catch_count = len(catch_re.findall(source))
        # If many async functions but very few error handlers
        if async_count >= 3 and (try_count + catch_count) == 0:
            alerts.append(BlackboxAlert(
                category="unhandled_promise_rejection",
                severity="warning",
                title=f"Component has {async_count} async functions with no error handling",
                description=f"{rel} has {async_count} async functions but no try/catch or .catch(). Unhandled rejections crash silently.",
                file=rel,
                fix_suggestion="Wrap async calls in try/catch, or add .catch() to promise chains.",
            ))
    return alerts


def detect_inline_styles_overuse(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find components with excessive inline styles (maintenance / performance issue)."""
    alerts: List[BlackboxAlert] = []
    style_re = re.compile(r"""style\s*=\s*\{\s*\{""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        count = len(style_re.findall(source))
        lines = len(source.splitlines())
        # Flag extremely style-heavy files
        if count >= 40 and lines < 400:
            alerts.append(BlackboxAlert(
                category="excessive_inline_styles",
                severity="info",
                title=f"Excessive inline styles ({count} in {lines} lines)",
                description=f"{rel} has {count} inline style objects in {lines} lines. Creates new objects on every render, hurts performance.",
                file=rel,
                fix_suggestion="Extract repeated styles to const objects outside the component, or use CSS/CSS modules.",
            ))
    return alerts


def detect_no_suspense_fallback_error(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find Suspense boundaries without a sibling ErrorBoundary (chunk load failures crash)."""
    alerts: List[BlackboxAlert] = []
    suspense_re = re.compile(r"""<Suspense""")
    boundary_re = re.compile(r"""<ErrorBoundary|errorElement|ErrorBoundary""")
    for fpath, rel in _jsx_files(root):
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if suspense_re.search(source) and not boundary_re.search(source):
            alerts.append(BlackboxAlert(
                category="suspense_without_error_boundary",
                severity="warning",
                title="<Suspense> without <ErrorBoundary>",
                description=f"{rel} uses <Suspense> for code splitting but has no ErrorBoundary. Chunk load failures (CDN blip, deploy) crash the whole app.",
                file=rel,
                fix_suggestion="Wrap <Suspense> with <ErrorBoundary fallback={<ChunkError />}> to catch lazy load failures.",
            ))
    return alerts


def detect_hardcoded_api_urls(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Find hardcoded http://localhost URLs in frontend code (won't work in prod)."""
    alerts: List[BlackboxAlert] = []
    url_re = re.compile(r"""['"]https?://localhost[:\d]*""")
    config_re = re.compile(r"""API_BASE|VITE_|import\.meta\.env|getApiBase|config/api""")
    for fpath, rel in _jsx_files(root):
        if "config/" in rel:
            continue  # Config files are expected to have these
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if url_re.search(line) and not config_re.search(line):
                alerts.append(BlackboxAlert(
                    category="hardcoded_api_url",
                    severity="warning",
                    title=f"Hardcoded localhost URL in component",
                    description=f"{rel}:{i} has a hardcoded localhost URL. Won't work in production/deployment.",
                    file=rel, line=i,
                    fix_suggestion="Use API_BASE_URL from config/api.js instead of hardcoded URLs.",
                ))
    return alerts


def detect_provenance_drift(root: Path = BACKEND_ROOT) -> List[BlackboxAlert]:
    """Detector #58: Compare current codebase against the provenance baseline (SHA-256 manifest)."""
    alerts: List[BlackboxAlert] = []
    try:
        project_root = root.parent  # backend/ → grace root
        from core.file_artifact_tracker import FileArtifactTracker
        tracker = FileArtifactTracker(str(project_root))
        if not tracker.baseline_path.exists():
            return []  # No baseline yet — skip silently
        drifts = tracker.detect_drift()
        for d in drifts[:50]:  # Cap to avoid flood
            dtype = d.get("type", "unknown")
            dpath = d.get("path", "unknown")
            if dtype == "modified":
                alerts.append(BlackboxAlert(
                    category="provenance_drift",
                    severity="warning",
                    title=f"File modified since last stable boot: {dpath}",
                    description=f"SHA-256 mismatch. Expected: {d.get('expected','?')[:12]}… Got: {d.get('actual','?')[:12]}…",
                    file=dpath,
                    fix_suggestion="Review the change. If intentional, re-run provenance baseline. If unexpected, investigate.",
                ))
            elif dtype == "new":
                alerts.append(BlackboxAlert(
                    category="provenance_drift",
                    severity="info",
                    title=f"New file since last stable boot: {dpath}",
                    description="File not present in the last provenance baseline.",
                    file=dpath,
                ))
            elif dtype == "deleted":
                alerts.append(BlackboxAlert(
                    category="provenance_drift",
                    severity="warning",
                    title=f"File deleted since last stable boot: {dpath}",
                    description="File was in the provenance baseline but no longer exists.",
                    file=dpath,
                    fix_suggestion="Verify deletion was intentional. If not, restore from backup.",
                ))
        if len(drifts) > 50:
            alerts.append(BlackboxAlert(
                category="provenance_drift",
                severity="info",
                title=f"Provenance drift: {len(drifts)} total changes (showing first 50)",
                description=f"Full drift count: {len(drifts)} files changed since last stable boot.",
            ))
    except FileNotFoundError:
        pass  # No baseline — skip
    except Exception as e:
        logger.warning("Provenance drift detector failed: %s", e)
    return alerts


# ══════════════════════════════════════════════════════════════════════════════
#  Scanner
# ══════════════════════════════════════════════════════════════════════════════

class SpindleBlackboxScanner:
    """Aggregates all blackbox detectors and produces delta-aware reports."""

    def __init__(self, root: Path = BACKEND_ROOT):
        self._root = root
        self._last_report: Optional[BlackboxReport] = None
        self._alert_history: Dict[str, BlackboxAlert] = {}  # key → alert
        self._lock = threading.Lock()

    # ── public API ───────────────────────────────────────────────────────

    def run_scan(self) -> BlackboxReport:
        """Execute every detector and return a categorised report."""
        logger.info("%s Starting full blackbox scan …", _PREFIX)
        t0 = time.time()

        all_alerts: List[BlackboxAlert] = []

        detectors = [
            ("deterministic_validators", lambda: _run_deterministic_validators(self._root)),
            ("orphan_finder", lambda: _run_orphan_finder(self._root)),
            ("no_output_components", lambda: detect_no_output_components(self._root)),
            ("dead_event_handlers", lambda: detect_dead_event_handlers(self._root)),
            ("degradation_signals", lambda: detect_degradation_signals(self._root)),
            ("unregistered_brains", lambda: detect_unregistered_brains(self._root)),
            ("silent_returns", lambda: detect_silent_returns(self._root)),
            ("zombie_threads", lambda: detect_zombie_threads(self._root)),
            ("missing_timeouts", lambda: detect_missing_timeouts(self._root)),
            ("unmonitored_services", lambda: detect_unmonitored_services(self._root)),
            ("circular_imports", lambda: detect_circular_imports(self._root)),
            ("duplicate_routes", lambda: detect_duplicate_routes(self._root)),
            ("unused_models", lambda: detect_unused_models(self._root)),
            ("phantom_env_vars", lambda: detect_phantom_env_vars(self._root)),
            ("fire_and_forget", lambda: detect_fire_and_forget_coroutines(self._root)),
            ("missing_error_propagation", lambda: detect_missing_error_propagation(self._root)),
            ("disconnected_feedback_loops", lambda: detect_disconnected_feedback_loops(self._root)),
            ("missing_shutdown", lambda: detect_missing_shutdown_hooks(self._root)),
            ("schema_drift", lambda: detect_schema_drift(self._root)),
            ("hardcoded_secrets", lambda: detect_hardcoded_secrets(self._root)),
            ("unreachable_code", lambda: detect_unreachable_code(self._root)),
            ("stale_triggers", lambda: detect_stale_triggers(self._root)),
            ("missing_http_timeouts", lambda: detect_missing_http_timeouts(self._root)),
            ("swallowed_network_errors", lambda: detect_swallowed_network_errors(self._root)),
            ("websocket_subscriber_leaks", lambda: detect_websocket_subscriber_leaks(self._root)),
            ("zmq_bridge_problems", lambda: detect_zmq_bridge_problems(self._root)),
            ("missing_frontend_timeouts", lambda: detect_missing_frontend_timeouts(self._root)),
            ("no_retry_http_clients", lambda: detect_no_retry_http_clients(self._root)),
            ("no_backend_offline_indicator", lambda: detect_no_backend_offline_indicator(self._root)),
            ("no_keepalive_connections", lambda: detect_no_keepalive_connections(self._root)),
            ("unclosed_connections", lambda: detect_unclosed_connections(self._root)),
            ("missing_circuit_breakers", lambda: detect_missing_circuit_breakers(self._root)),
            ("unbounded_queues", lambda: detect_unbounded_queues(self._root)),
            ("no_websocket_heartbeat", lambda: detect_no_websocket_heartbeat(self._root)),
            ("fire_and_forget_http", lambda: detect_fire_and_forget_http(self._root)),
            ("no_idempotency_on_retry", lambda: detect_no_idempotency_on_retry(self._root)),
            ("frontend_silent_catches", lambda: detect_frontend_silent_catches(self._root)),
            ("frontend_ws_no_reconnect", lambda: detect_frontend_ws_no_reconnect(self._root)),
            ("no_error_rate_tracking", lambda: detect_no_error_rate_tracking(self._root)),
            ("no_latency_tracking", lambda: detect_no_latency_tracking(self._root)),
            ("frontend_stale_ws_state", lambda: detect_frontend_stale_ws_state(self._root)),
            ("ipc_echo_loop_risk", lambda: detect_ipc_echo_loop_risk(self._root)),
            ("no_error_boundary", lambda: detect_no_error_boundary_wrapping(self._root)),
            ("useeffect_memory_leaks", lambda: detect_useeffect_memory_leaks(self._root)),
            ("fetch_race_conditions", lambda: detect_fetch_race_conditions(self._root)),
            ("missing_empty_states", lambda: detect_missing_empty_states(self._root)),
            ("xss_dangerously_set", lambda: detect_dangerously_set_innerhtml(self._root)),
            ("localstorage_secrets", lambda: detect_localstorage_secrets(self._root)),
            ("console_log_pollution", lambda: detect_console_log_in_production(self._root)),
            ("no_loading_states", lambda: detect_no_loading_states(self._root)),
            ("missing_key_props", lambda: detect_missing_key_prop(self._root)),
            ("no_frontend_error_reporting", lambda: detect_no_frontend_error_reporting(self._root)),
            ("missing_accessibility", lambda: detect_missing_accessibility(self._root)),
            ("unhandled_promise_rejections", lambda: detect_unhandled_promise_rejections(self._root)),
            ("excessive_inline_styles", lambda: detect_inline_styles_overuse(self._root)),
            ("suspense_without_error_boundary", lambda: detect_no_suspense_fallback_error(self._root)),
            ("hardcoded_api_urls", lambda: detect_hardcoded_api_urls(self._root)),
            ("provenance_drift", lambda: detect_provenance_drift(self._root)),
        ]

        for name, fn in detectors:
            try:
                logger.info("%s Running detector: %s", _PREFIX, name)
                results = fn()
                all_alerts.extend(results)
                logger.info("%s  └─ %s: %d issue(s)", _PREFIX, name, len(results))
            except Exception as exc:
                logger.error("%s Detector %s crashed: %s", _PREFIX, name, exc, exc_info=True)

        elapsed_ms = (time.time() - t0) * 1000

        # ── delta computation ────────────────────────────────────────────
        current_keys: Dict[str, BlackboxAlert] = {}
        now = datetime.now(timezone.utc)
        for alert in all_alerts:
            key = alert.key
            if key in self._alert_history:
                prev = self._alert_history[key]
                alert.first_seen = prev.first_seen
                alert.occurrences = prev.occurrences + 1
            alert.last_seen = now
            current_keys[key] = alert

        previous_keys = set(self._alert_history.keys())
        new_keys = set(current_keys.keys()) - previous_keys
        resolved_keys = previous_keys - set(current_keys.keys())

        new_alerts = [current_keys[k] for k in new_keys]
        resolved_alerts = [self._alert_history[k] for k in resolved_keys]

        # ── build report ─────────────────────────────────────────────────
        categories: Dict[str, int] = {}
        for a in all_alerts:
            categories[a.category] = categories.get(a.category, 0) + 1

        py_count = sum(1 for _ in _py_files(self._root))

        report = BlackboxReport(
            timestamp=now.isoformat(),
            scan_duration_ms=round(elapsed_ms, 2),
            total_issues=len(all_alerts),
            critical_count=sum(1 for a in all_alerts if a.severity == "critical"),
            warning_count=sum(1 for a in all_alerts if a.severity == "warning"),
            info_count=sum(1 for a in all_alerts if a.severity == "info"),
            categories=categories,
            alerts=all_alerts,
            new_alerts=new_alerts,
            resolved_alerts=resolved_alerts,
            files_scanned=py_count,
        )

        with self._lock:
            self._last_report = report
            self._alert_history = current_keys

        logger.info(
            "%s Scan complete: %d issues (%d critical, %d warning, %d info) "
            "| %d new | %d resolved | %d files | %.0fms",
            _PREFIX,
            report.total_issues,
            report.critical_count,
            report.warning_count,
            report.info_count,
            len(new_alerts),
            len(resolved_alerts),
            py_count,
            elapsed_ms,
        )
        return report

    def get_alerts(self) -> List[BlackboxAlert]:
        """Return new alerts from the most recent scan (delta since prior scan)."""
        with self._lock:
            if self._last_report is None:
                return []
            return list(self._last_report.new_alerts)

    def get_latest_report(self) -> Optional[BlackboxReport]:
        """Return the cached report from the last completed scan."""
        with self._lock:
            return self._last_report

    def publish_alerts(self, report: BlackboxReport) -> None:
        """Publish critical and warning alerts to the event bus."""
        try:
            from cognitive.event_bus import publish
        except Exception as exc:
            logger.warning("%s Cannot import event_bus.publish: %s", _PREFIX, exc)
            return

        significant = [a for a in report.alerts if a.severity in ("critical", "warning")]
        if not significant:
            return

        publish("blackbox.scan_completed", {
            "timestamp": report.timestamp,
            "total_issues": report.total_issues,
            "critical_count": report.critical_count,
            "warning_count": report.warning_count,
            "new_count": len(report.new_alerts),
            "resolved_count": len(report.resolved_alerts),
        }, source="spindle_blackbox_scanner")

        for alert in significant:
            publish(f"blackbox.alert.{alert.severity}", {
                "category": alert.category,
                "title": alert.title,
                "description": alert.description,
                "file": alert.file,
                "line": alert.line,
                "fix_suggestion": alert.fix_suggestion,
                "occurrences": alert.occurrences,
            }, source="spindle_blackbox_scanner")


# ══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ══════════════════════════════════════════════════════════════════════════════

_scanner: Optional[SpindleBlackboxScanner] = None
_scanner_lock = threading.Lock()


def get_blackbox_scanner() -> SpindleBlackboxScanner:
    """Return (or create) the module-level singleton scanner."""
    global _scanner
    if _scanner is None:
        with _scanner_lock:
            if _scanner is None:
                _scanner = SpindleBlackboxScanner()
    return _scanner
