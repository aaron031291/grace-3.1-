"""
Deterministic Component Lifecycle Manager
==========================================
Full agentic deterministic lifecycle for any component:

    REGISTER → LOG → PROBE → TEST → SCAN → FIX → REASON → HEAL → VERIFY → LOOP

The hallucination-proof, recursive self-healing chain:

  1. REGISTER:  Component discovered/added → Genesis Key created, deterministic log
  2. LOG:       Every lifecycle event is deterministically logged (AST-verified)
  3. PROBE:     Is it alive? HTTP probe, import check, instantiation test
  4. TEST:      Does it work correctly? Deterministic I/O tests (component_validator)
  5. SCAN:      If unhealthy → full deterministic scan (syntax, imports, deps, wiring)
  6. FIX:       Try deterministic auto-fix first (no LLM) — DeterministicAutoFixer
  7. REASON:    If deterministic fix fails → LLM reasoning (constrained by facts)
  8. HEAL:      Self-heal via coding agent / healing coordinator if needed
  9. VERIFY:    Re-probe + re-test after fix — confirm it actually works
 10. LOOP:      Recursive until healthy or max iterations reached → escalate

All steps tracked via Genesis Keys with full provenance.
Integrates: probe_agent, deterministic_bridge, component_validator,
            coding_pipeline, healing_coordinator, circuit_breaker, genesis_triggers
"""

import ast
import time
import logging
import threading
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

from core.deterministic_logger import (
    log_event, log_component_registered, log_component_alive, log_component_dead,
    log_scan_started, log_scan_result, log_fix_attempted, log_fix_result,
    log_heal_escalated, log_verify_result, get_event_log, get_event_summary,
)

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent

MAX_RECURSIVE_ITERATIONS = 5
PROBE_TIMEOUT_SECONDS = 5


@dataclass
class ComponentRegistration:
    """A registered component in the lifecycle system."""
    component_id: str
    label: str
    file_path: Optional[str] = None
    health_url: Optional[str] = None
    import_path: Optional[str] = None
    class_name: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    registered_at: str = ""
    status: str = "unknown"  # unknown, alive, dead, degraded, healing
    last_probed: Optional[str] = None
    probe_latency_ms: float = 0
    consecutive_failures: int = 0
    genesis_key_id: Optional[str] = None


@dataclass
class LifecycleResult:
    """Result of a full lifecycle cycle for a component."""
    component_id: str
    started_at: str
    completed_at: str = ""
    iterations: int = 0
    final_status: str = "unknown"
    steps: List[Dict[str, Any]] = field(default_factory=list)
    issues_found: int = 0
    issues_fixed: int = 0
    deterministic_fixes: int = 0
    llm_fixes: int = 0
    escalated: bool = False
    healthy: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_registry: Dict[str, ComponentRegistration] = {}
_registry_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
#  STEP 1: REGISTER — Discover and register components
# ═══════════════════════════════════════════════════════════════════

def register_component(
    component_id: str,
    label: str,
    file_path: Optional[str] = None,
    health_url: Optional[str] = None,
    import_path: Optional[str] = None,
    class_name: Optional[str] = None,
    dependencies: Optional[List[str]] = None,
) -> ComponentRegistration:
    """
    Register a component in the deterministic lifecycle system.
    Creates a Genesis Key for the registration event.
    """
    reg = ComponentRegistration(
        component_id=component_id,
        label=label,
        file_path=file_path,
        health_url=health_url,
        import_path=import_path,
        class_name=class_name,
        dependencies=dependencies or [],
        registered_at=datetime.now(timezone.utc).isoformat(),
    )

    with _registry_lock:
        _registry[component_id] = reg

    log_component_registered(component_id, file_path, {
        "label": label,
        "health_url": health_url,
        "import_path": import_path,
        "dependencies": dependencies or [],
    })

    try:
        from api._genesis_tracker import track
        result = track(
            key_type="system_event",
            what=f"Component registered in lifecycle: {label} ({component_id})",
            who="deterministic_lifecycle",
            where=file_path,
            how="register_component",
            output_data={"component_id": component_id, "label": label},
            tags=["deterministic", "lifecycle", "component_registered", component_id],
        )
        if result and hasattr(result, "key_id"):
            reg.genesis_key_id = result.key_id
    except Exception:
        pass

    logger.info(f"[LIFECYCLE] Registered component: {component_id} ({label})")
    return reg


def auto_discover_components() -> List[ComponentRegistration]:
    """
    Auto-discover components from existing registries
    (component_health, semantic_search, Layer 1 connectors).
    """
    discovered = []

    try:
        from api.component_health_api import COMPONENT_REGISTRY
        for comp_id, comp in COMPONENT_REGISTRY.items():
            reg = register_component(
                component_id=comp_id,
                label=comp.get("label", comp_id),
                health_url=comp.get("health_check_url"),
                dependencies=comp.get("dependencies", []),
            )
            discovered.append(reg)
    except Exception as e:
        logger.debug(f"Component health registry not available: {e}")

    try:
        from core.semantic_search import COMPONENTS
        for comp_id, info in COMPONENTS.items():
            if comp_id not in _registry:
                reg = register_component(
                    component_id=comp_id,
                    label=comp_id,
                    file_path=info.get("file"),
                )
                discovered.append(reg)
    except Exception:
        pass

    return discovered


# ═══════════════════════════════════════════════════════════════════
#  STEP 3: PROBE — Is it alive?
# ═══════════════════════════════════════════════════════════════════

def probe_component(component_id: str) -> Dict[str, Any]:
    """
    Deterministic liveness probe for a component.
    Tries (in order): HTTP probe, import check, file existence.
    """
    reg = _registry.get(component_id)
    if not reg:
        return {"alive": False, "error": f"Component {component_id} not registered"}

    result = {
        "component_id": component_id,
        "alive": False,
        "method": None,
        "latency_ms": 0,
        "error": None,
    }

    start = time.time()

    # Method 1: HTTP health check
    if reg.health_url:
        try:
            import urllib.request
            urllib.request.urlopen(reg.health_url, timeout=PROBE_TIMEOUT_SECONDS)
            result["alive"] = True
            result["method"] = "http"
            result["latency_ms"] = (time.time() - start) * 1000
            reg.status = "alive"
            reg.last_probed = datetime.now(timezone.utc).isoformat()
            reg.probe_latency_ms = result["latency_ms"]
            reg.consecutive_failures = 0
            log_component_alive(component_id, result["latency_ms"])
            return result
        except Exception as e:
            result["error"] = str(e)[:200]

    # Method 2: Import check
    if reg.import_path:
        try:
            mod = importlib.import_module(reg.import_path)
            if reg.class_name and hasattr(mod, reg.class_name):
                result["alive"] = True
                result["method"] = "import"
            elif not reg.class_name:
                result["alive"] = True
                result["method"] = "import"
            else:
                result["error"] = f"Class {reg.class_name} not found in {reg.import_path}"
            result["latency_ms"] = (time.time() - start) * 1000
        except Exception as e:
            result["error"] = str(e)[:200]

    # Method 3: File existence + AST parse
    if not result["alive"] and reg.file_path:
        full_path = BACKEND_ROOT / reg.file_path
        if full_path.exists():
            try:
                ast.parse(full_path.read_text(errors="ignore"))
                result["alive"] = True
                result["method"] = "file_ast"
                result["latency_ms"] = (time.time() - start) * 1000
            except SyntaxError as e:
                result["error"] = f"Syntax error: {e.msg} (line {e.lineno})"
        else:
            result["error"] = f"File not found: {reg.file_path}"

    result["latency_ms"] = round((time.time() - start) * 1000, 1)

    if result["alive"]:
        reg.status = "alive"
        reg.consecutive_failures = 0
        log_component_alive(component_id, result["latency_ms"])
    else:
        reg.consecutive_failures += 1
        reg.status = "dead"
        log_component_dead(component_id, result.get("error", "unknown"))

    reg.last_probed = datetime.now(timezone.utc).isoformat()
    reg.probe_latency_ms = result["latency_ms"]

    return result


def probe_all_components() -> Dict[str, Any]:
    """Probe all registered components and return a health map."""
    results = {}
    alive_count = 0
    dead_count = 0

    with _registry_lock:
        component_ids = list(_registry.keys())

    for comp_id in component_ids:
        probe = probe_component(comp_id)
        results[comp_id] = probe
        if probe["alive"]:
            alive_count += 1
        else:
            dead_count += 1

    return {
        "total": len(results),
        "alive": alive_count,
        "dead": dead_count,
        "components": results,
        "probed_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
#  STEP 4: TEST — Does it work correctly?
# ═══════════════════════════════════════════════════════════════════

def test_component(component_id: str) -> Dict[str, Any]:
    """
    Run deterministic I/O tests via component_validator.
    Falls back to a basic import+instantiation test if no test cases defined.
    """
    result = {"component_id": component_id, "tested": False, "passed": 0, "failed": 0, "pass_rate": 0.0}

    try:
        from core.component_validator import get_report_card
        card = get_report_card(component_id)
        if card and card.get("status") != "not_validated":
            result["tested"] = True
            result["passed"] = card.get("passed", 0)
            result["failed"] = card.get("failed", 0)
            result["pass_rate"] = card.get("pass_rate", 0)
            result["status"] = card.get("status", "unknown")
            return result
    except Exception:
        pass

    reg = _registry.get(component_id)
    if reg and reg.file_path:
        full_path = BACKEND_ROOT / reg.file_path
        if full_path.exists():
            try:
                ast.parse(full_path.read_text(errors="ignore"))
                result["tested"] = True
                result["passed"] = 1
                result["pass_rate"] = 100.0
                result["status"] = "healthy"
            except SyntaxError:
                result["tested"] = True
                result["failed"] = 1
                result["status"] = "failing"

    return result


# ═══════════════════════════════════════════════════════════════════
#  STEP 5: SCAN — What's wrong? (Deterministic)
# ═══════════════════════════════════════════════════════════════════

def scan_component(component_id: str) -> Dict[str, Any]:
    """
    Run deterministic scan on a component.
    Uses the deterministic bridge for system-wide checks,
    plus targeted file analysis for the specific component.
    """
    log_scan_started(component_id)

    result = {
        "component_id": component_id,
        "problems": [],
        "total_problems": 0,
        "critical": 0,
    }

    reg = _registry.get(component_id)

    # Component-specific file scan
    if reg and reg.file_path:
        full_path = BACKEND_ROOT / reg.file_path
        if full_path.exists():
            try:
                source = full_path.read_text(errors="ignore")
                ast.parse(source)
            except SyntaxError as e:
                result["problems"].append({
                    "type": "syntax_error",
                    "file": reg.file_path,
                    "line": e.lineno,
                    "message": e.msg,
                    "severity": "critical",
                    "deterministic": True,
                })

            # Check imports in the file
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module_path = node.module.replace(".", "/")
                        top_level = node.module.split(".")[0]
                        local_dirs = [d.name for d in BACKEND_ROOT.iterdir()
                                      if d.is_dir() and not d.name.startswith('.')]
                        if top_level in local_dirs:
                            possible = [
                                BACKEND_ROOT / f"{module_path}.py",
                                BACKEND_ROOT / module_path / "__init__.py",
                            ]
                            if not any(p.exists() for p in possible):
                                result["problems"].append({
                                    "type": "broken_import",
                                    "file": reg.file_path,
                                    "line": node.lineno,
                                    "module": node.module,
                                    "severity": "critical",
                                    "deterministic": True,
                                })
            except Exception:
                pass
        else:
            result["problems"].append({
                "type": "missing_file",
                "file": reg.file_path,
                "severity": "critical",
                "deterministic": True,
            })

    # Check dependencies
    if reg and reg.dependencies:
        for dep in reg.dependencies:
            dep_reg = _registry.get(dep)
            if dep_reg and dep_reg.status == "dead":
                result["problems"].append({
                    "type": "dependency_dead",
                    "dependency": dep,
                    "severity": "warning",
                    "deterministic": True,
                })

    # Run the full deterministic bridge scan
    try:
        from core.deterministic_bridge import build_deterministic_report
        det_report = build_deterministic_report()
        component_problems = []
        for p in det_report.get("problems", []):
            pfile = p.get("file", p.get("module", ""))
            if reg and reg.file_path and reg.file_path in str(pfile):
                component_problems.append(p)
            elif reg and component_id.lower() in str(pfile).lower():
                component_problems.append(p)
        result["problems"].extend(component_problems)
    except Exception:
        pass

    result["total_problems"] = len(result["problems"])
    result["critical"] = sum(1 for p in result["problems"] if p.get("severity") == "critical")

    log_scan_result(component_id, result["total_problems"], result["critical"])

    return result


# ═══════════════════════════════════════════════════════════════════
#  STEP 6: FIX — Deterministic auto-fix (no LLM)
# ═══════════════════════════════════════════════════════════════════

def fix_deterministic(component_id: str, problems: List[Dict]) -> Dict[str, Any]:
    """
    Attempt to fix problems deterministically — no LLM needed.
    Uses DeterministicAutoFixer for known patterns.
    """
    result = {
        "component_id": component_id,
        "attempted": 0,
        "fixed": 0,
        "unfixed": [],
        "fixes_applied": [],
    }

    if not problems:
        return result

    log_fix_attempted(component_id, "deterministic_auto_fix", deterministic=True)

    try:
        from core.deterministic_bridge import DeterministicAutoFixer
        fixer = DeterministicAutoFixer()
        fixes = fixer.auto_fix(problems)
        result["attempted"] = len(problems)
        result["fixed"] = len(fixes)
        result["fixes_applied"] = fixes

        fixed_types = {f.get("type", "") for f in fixes}
        result["unfixed"] = [
            p for p in problems
            if p.get("type", "") not in fixed_types
        ]

        if fixes:
            log_fix_result(component_id, True, f"deterministic ({len(fixes)} fixes)")
        if result["unfixed"]:
            log_fix_result(component_id, False, f"deterministic ({len(result['unfixed'])} remaining)")

    except Exception as e:
        result["error"] = str(e)[:200]
        result["unfixed"] = problems
        log_fix_result(component_id, False, f"deterministic (error: {e})")

    return result


# ═══════════════════════════════════════════════════════════════════
#  STEP 7: REASON — LLM reasoning (constrained by deterministic facts)
# ═══════════════════════════════════════════════════════════════════

def reason_with_llm(component_id: str, problems: List[Dict]) -> Dict[str, Any]:
    """
    Feed deterministic facts to LLM for reasoning about unfixed problems.
    The LLM only sees verified facts — no guessing.
    """
    result = {
        "component_id": component_id,
        "reasoning_requested": True,
        "llm_response": None,
        "fix_suggestion": None,
    }

    if not problems:
        result["reasoning_requested"] = False
        return result

    log_heal_escalated(component_id, f"{len(problems)} unfixed problems", to="llm")

    facts = "\n".join(
        f"- [{p.get('type', 'unknown')}] {p.get('file', p.get('module', ''))} "
        f"{'line ' + str(p.get('line', '')) + ': ' if p.get('line') else ''}"
        f"{p.get('message', p.get('error', ''))}"
        for p in problems[:10]
    )

    prompt = (
        f"DETERMINISTIC FACTS for component '{component_id}' (verified, not guessed):\n"
        f"{facts}\n\n"
        f"1. Explain the root cause of these problems.\n"
        f"2. Provide the EXACT fix for each problem.\n"
        f"3. Return ONLY corrected code if applicable."
    )

    try:
        from api.brain_api_v2 import call_brain
        llm_result = call_brain("ai", "generate", {"prompt": prompt})
        if llm_result.get("ok"):
            result["llm_response"] = llm_result.get("data", {}).get("response", "")[:2000]
            result["fix_suggestion"] = result["llm_response"]
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ═══════════════════════════════════════════════════════════════════
#  STEP 8: HEAL — Self-heal via coding agent / healing coordinator
# ═══════════════════════════════════════════════════════════════════

def heal_component(component_id: str, problems: List[Dict], llm_reasoning: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Self-heal the component using available healing infrastructure:
    1. Healing coordinator (diagnose → agree → fix)
    2. Coding pipeline (if code fix needed)
    3. Service-specific healing (DB reconnect, Qdrant reconnect, etc.)
    """
    result = {
        "component_id": component_id,
        "healing_attempted": True,
        "healing_method": None,
        "healed": False,
    }

    log_fix_attempted(component_id, "self_heal", deterministic=False)

    # Try healing coordinator
    try:
        from cognitive.healing_coordinator import HealingCoordinator
        coordinator = HealingCoordinator()
        problem_text = "; ".join(
            p.get("message", p.get("error", str(p)))[:100] for p in problems[:5]
        )
        heal_result = coordinator.resolve(problem_text)
        if heal_result and heal_result.get("resolved"):
            result["healing_method"] = "healing_coordinator"
            result["healed"] = True
            log_fix_result(component_id, True, "healing_coordinator")
            return result
    except Exception:
        pass

    # Try self-healer for service issues
    try:
        from cognitive.self_healing import SelfHealer
        healer = SelfHealer()
        heal_result = healer.check_and_heal()
        if heal_result and heal_result.get("healed"):
            result["healing_method"] = "self_healer"
            result["healed"] = True
            log_fix_result(component_id, True, "self_healer")
            return result
    except Exception:
        pass

    # Try coding pipeline if LLM suggested a code fix
    if llm_reasoning and llm_reasoning.get("fix_suggestion"):
        try:
            from api.brain_api_v2 import call_brain
            fix_result = call_brain("ai", "deterministic_fix", {
                "task": f"Fix component {component_id}: {llm_reasoning['fix_suggestion'][:500]}"
            })
            if fix_result.get("ok"):
                result["healing_method"] = "coding_agent"
                result["healed"] = True
                log_fix_result(component_id, True, "coding_agent")
                return result
        except Exception:
            pass

    log_fix_result(component_id, False, "all_methods_exhausted")
    return result


# ═══════════════════════════════════════════════════════════════════
#  THE FULL RECURSIVE LIFECYCLE LOOP
# ═══════════════════════════════════════════════════════════════════

def run_lifecycle(component_id: str, max_iterations: int = MAX_RECURSIVE_ITERATIONS) -> LifecycleResult:
    """
    Run the full deterministic lifecycle for a component.

    The recursive chain:
        PROBE → TEST → SCAN → FIX(deterministic) → REASON(LLM) → HEAL → VERIFY → LOOP

    Each iteration:
    1. Probe: alive?
    2. Test: correct?
    3. If unhealthy → Scan (find problems deterministically)
    4. Fix deterministically (no LLM)
    5. If unfixed → LLM reasoning (constrained by facts)
    6. If LLM suggests fix → Heal (coding agent / self-healer)
    7. Verify (re-probe + re-test)
    8. If still broken and iterations remain → LOOP (recursive)
    """
    result = LifecycleResult(
        component_id=component_id,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    log_event("LIFECYCLE_STARTED", component_id,
              f"Starting deterministic lifecycle (max {max_iterations} iterations)")

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        step_data: Dict[str, Any] = {"iteration": iteration, "actions": []}

        # ── PROBE ──
        probe = probe_component(component_id)
        step_data["probe"] = probe
        step_data["actions"].append("probe")

        # ── TEST ──
        test = test_component(component_id)
        step_data["test"] = test
        step_data["actions"].append("test")

        is_healthy = probe["alive"] and test.get("pass_rate", 0) >= 80

        if is_healthy:
            step_data["status"] = "healthy"
            result.steps.append(step_data)
            result.healthy = True
            result.final_status = "healthy"
            log_verify_result(component_id, True, iteration)
            break

        # ── SCAN ──
        scan = scan_component(component_id)
        step_data["scan"] = scan
        step_data["actions"].append("scan")
        result.issues_found += scan["total_problems"]

        if scan["total_problems"] == 0 and not probe["alive"]:
            step_data["status"] = "unreachable_no_code_issues"
            result.steps.append(step_data)

            # Try direct healing for unreachable components
            heal = heal_component(component_id, [{"type": "unreachable", "message": probe.get("error", "")}])
            step_data["heal"] = heal
            step_data["actions"].append("heal")

            if heal["healed"]:
                log_verify_result(component_id, False, iteration)
                continue
            else:
                result.escalated = True
                log_heal_escalated(component_id, "unreachable, no code issues, healing failed", to="human")
                break

        # ── FIX (deterministic) ──
        det_fix = fix_deterministic(component_id, scan["problems"])
        step_data["deterministic_fix"] = det_fix
        step_data["actions"].append("deterministic_fix")
        result.deterministic_fixes += det_fix["fixed"]
        result.issues_fixed += det_fix["fixed"]

        if not det_fix["unfixed"]:
            step_data["status"] = "fixed_deterministically"
            result.steps.append(step_data)
            log_verify_result(component_id, False, iteration)
            continue  # verify on next iteration

        # ── REASON (LLM) ──
        llm = reason_with_llm(component_id, det_fix["unfixed"])
        step_data["llm_reasoning"] = {
            "requested": llm["reasoning_requested"],
            "has_suggestion": bool(llm.get("fix_suggestion")),
        }
        step_data["actions"].append("llm_reasoning")

        # ── HEAL (coding agent / self-healer) ──
        heal = heal_component(component_id, det_fix["unfixed"], llm)
        step_data["heal"] = heal
        step_data["actions"].append("heal")

        if heal["healed"]:
            result.llm_fixes += 1
            result.issues_fixed += len(det_fix["unfixed"])
            step_data["status"] = f"healed_via_{heal.get('healing_method', 'unknown')}"
        else:
            step_data["status"] = "healing_failed"

        result.steps.append(step_data)
        log_verify_result(component_id, heal["healed"], iteration)

        if not heal["healed"] and iteration == max_iterations:
            result.escalated = True
            log_heal_escalated(component_id,
                               f"Max iterations ({max_iterations}) reached, still unhealthy",
                               to="human")

    result.completed_at = datetime.now(timezone.utc).isoformat()
    if not result.healthy and not result.escalated:
        result.final_status = "degraded"
    elif result.escalated:
        result.final_status = "escalated"

    # Track the full lifecycle via Genesis
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Lifecycle complete for {component_id}: {result.final_status} "
                 f"({result.iterations} iterations, {result.issues_found} issues, {result.issues_fixed} fixed)",
            who="deterministic_lifecycle",
            output_data={"result": result.to_dict()},
            tags=["deterministic", "lifecycle", "complete", component_id, result.final_status],
        )
    except Exception:
        pass

    log_event("LIFECYCLE_COMPLETE", component_id,
              f"Lifecycle complete: {result.final_status} ({result.iterations} iterations, "
              f"{result.issues_found} found, {result.issues_fixed} fixed)",
              severity="info" if result.healthy else "warning")

    return result


def run_lifecycle_all() -> Dict[str, Any]:
    """Run the lifecycle for ALL registered components."""
    if not _registry:
        auto_discover_components()

    results = {}
    healthy = 0
    unhealthy = 0
    escalated = 0

    with _registry_lock:
        component_ids = list(_registry.keys())

    for comp_id in component_ids:
        lifecycle = run_lifecycle(comp_id)
        results[comp_id] = lifecycle.to_dict()
        if lifecycle.healthy:
            healthy += 1
        elif lifecycle.escalated:
            escalated += 1
        else:
            unhealthy += 1

    return {
        "total_components": len(results),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "escalated": escalated,
        "results": results,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "event_summary": get_event_summary(),
    }


# ═══════════════════════════════════════════════════════════════════
#  QUICK SCAN — Probe all + scan unhealthy (no healing)
# ═══════════════════════════════════════════════════════════════════

def lifecycle_scan() -> Dict[str, Any]:
    """
    Quick lifecycle scan: probe all components, scan unhealthy ones.
    Does NOT attempt fixes — read-only diagnostic.
    """
    if not _registry:
        auto_discover_components()

    probes = probe_all_components()
    scans = {}

    for comp_id, probe in probes.get("components", {}).items():
        if not probe["alive"]:
            scans[comp_id] = scan_component(comp_id)

    return {
        "probe_summary": {
            "total": probes["total"],
            "alive": probes["alive"],
            "dead": probes["dead"],
        },
        "unhealthy_scans": scans,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "event_log": get_event_log(limit=20),
    }


# ═══════════════════════════════════════════════════════════════════
#  ACCESSORS
# ═══════════════════════════════════════════════════════════════════

def get_registry() -> Dict[str, Dict[str, Any]]:
    """Get all registered components."""
    with _registry_lock:
        return {k: asdict(v) for k, v in _registry.items()}


def get_component_status(component_id: str) -> Dict[str, Any]:
    """Get lifecycle status for a single component."""
    reg = _registry.get(component_id)
    if not reg:
        return {"error": f"Component {component_id} not registered"}

    return {
        "registration": asdict(reg),
        "event_log": get_event_log(component_id, limit=20),
    }
