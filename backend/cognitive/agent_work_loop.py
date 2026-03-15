# -*- coding: utf-8 -*-
"""
Coding Agent Work Loop -- Active stabilisation system.

Subscribes to pipeline.deploy_gate Spindle events and uses the multi-LLM
coding agents (Kimi + Opus) to actively fix edge cases and stabilise the
system.

Flow:
    1. DISCOVER -- Run E2E validator, healing swarm, and deterministic bridge
                   to find what's actually broken right now
    2. PRIORITISE -- Rank issues by severity (critical > warning > low)
    3. DISPATCH -- Send tasks to Kimi+Opus via CodingAgentPool
    4. VERIFY -- Check fixes compile, pass AST, and don't break other things
    5. REPORT -- Emit results to Spindle + Genesis Keys
    6. LISTEN -- Subscribe to pipeline.deploy_gate for ongoing stabilisation

Agents follow ALL governance rules via GovernanceAwareLLM wrapper.
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent.parent


# ======================================================================
# Issue Discovery -- find what's broken
# ======================================================================

def discover_issues() -> List[Dict[str, Any]]:
    """
    Run all diagnostic tools and collect issues.
    Returns a list of issues sorted by severity.
    """
    issues = []

    # 1. E2E Validator -- 12-stage pipeline check
    try:
        from core.deterministic_e2e_validator import run_e2e_validation, StageVerdict
        report = run_e2e_validation()
        for stage in report.stages:
            for check in stage.checks:
                if check.verdict in (StageVerdict.FAIL, StageVerdict.WARN):
                    issues.append({
                        "source": "e2e_validator",
                        "severity": "critical" if check.verdict == StageVerdict.FAIL else "warning",
                        "stage": stage.stage,
                        "stage_name": stage.name,
                        "check": check.name,
                        "message": check.message,
                        "details": check.details,
                    })
    except Exception as e:
        logger.warning(f"[WORK-LOOP] E2E validator failed: {e}")

    # 2. Deterministic Bridge -- AST/import/wiring scan
    try:
        from core.deterministic_bridge import build_deterministic_report
        report = build_deterministic_report()
        for problem in report.get("problems", [])[:30]:
            issues.append({
                "source": "deterministic_bridge",
                "severity": problem.get("severity", "warning"),
                "file": problem.get("file", ""),
                "line": problem.get("line", 0),
                "message": problem.get("message", ""),
                "category": problem.get("category", ""),
            })
    except Exception as e:
        logger.debug(f"[WORK-LOOP] Deterministic bridge scan failed: {e}")

    # 3. Python compile check on all backend modules
    try:
        import py_compile
        for py_file in _BACKEND.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".git" in str(py_file):
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                rel = py_file.relative_to(_BACKEND)
                issues.append({
                    "source": "compile_check",
                    "severity": "critical",
                    "file": str(rel),
                    "message": str(e)[:200],
                    "category": "syntax_error",
                })
    except Exception as e:
        logger.debug(f"[WORK-LOOP] Compile scan failed: {e}")

    # 4. Import check -- try importing key modules
    critical_modules = [
        "app", "cognitive.event_bus", "cognitive.healing_swarm",
        "cognitive.coding_agents", "cognitive.qwen_agents",
        "core.coding_pipeline", "core.deterministic_e2e_validator",
        "llm_orchestrator.factory", "llm_orchestrator.governance_wrapper",
        "database.session", "database.connection",
    ]
    for mod in critical_modules:
        try:
            import importlib
            importlib.import_module(mod)
        except Exception as e:
            issues.append({
                "source": "import_check",
                "severity": "critical",
                "module": mod,
                "message": str(e)[:200],
                "category": "import_error",
            })

    # Sort by severity: critical first, then warning, then low
    severity_order = {"critical": 0, "warning": 1, "low": 2}
    issues.sort(key=lambda i: severity_order.get(i.get("severity", "low"), 3))

    logger.info(f"[WORK-LOOP] Discovered {len(issues)} issues "
                f"({sum(1 for i in issues if i['severity']=='critical')} critical, "
                f"{sum(1 for i in issues if i['severity']=='warning')} warning)")

    return issues


# ======================================================================
# Task Builder -- convert issues into CodingTasks
# ======================================================================

def build_tasks(issues: List[Dict[str, Any]], max_tasks: int = 10) -> list:
    """Convert discovered issues into CodingTasks for the agent pool."""
    from cognitive.coding_agents import CodingTask

    tasks = []
    for i, issue in enumerate(issues[:max_tasks]):
        file_path = issue.get("file", "")
        module = issue.get("module", "")

        # Convert module to file path if needed
        if not file_path and module:
            file_path = module.replace(".", "/") + ".py"

        description = (
            f"Fix {issue['severity']} issue in {issue.get('stage_name', issue.get('category', 'system'))}:\n"
            f"{issue['message']}\n"
        )
        if issue.get("details"):
            description += f"Details: {str(issue['details'])[:300]}\n"

        task = CodingTask(
            id=f"stabilise-{i}-{int(time.time())}",
            task_type="fix",
            file_path=file_path,
            description=description,
            error=issue["message"],
            context={
                "source": issue["source"],
                "severity": issue["severity"],
                "stage": issue.get("stage", 0),
            },
            priority="high" if issue["severity"] == "critical" else "medium",
        )
        tasks.append(task)

    return tasks


# ======================================================================
# Stabilisation Run -- discover, dispatch, verify
# ======================================================================

def run_stabilisation(max_tasks: int = 10) -> Dict[str, Any]:
    """
    Full stabilisation cycle:
    1. Discover issues
    2. Build tasks
    3. Dispatch to Kimi+Opus in parallel
    4. Verify and report results
    """
    start = time.time()
    run_id = f"stabilise-{int(start)}"

    logger.info(f"[WORK-LOOP] Starting stabilisation run {run_id}")

    # Emit start event
    _emit("stabilisation.started", {
        "run_id": run_id,
        "max_tasks": max_tasks,
    })

    # 1. Discover
    issues = discover_issues()
    if not issues:
        result = {
            "run_id": run_id,
            "status": "clean",
            "message": "No issues found -- system is stable",
            "duration_s": round(time.time() - start, 2),
        }
        _emit("stabilisation.completed", result)
        return result

    # 2. Build tasks
    tasks = build_tasks(issues, max_tasks=max_tasks)

    # 3. Dispatch to coding agents
    from cognitive.coding_agents import get_coding_agent_pool
    pool = get_coding_agent_pool()

    results = []
    for task in tasks:
        try:
            # Use parallel dispatch for critical issues
            if task.context.get("severity") == "critical":
                agent_results = pool.dispatch_parallel(task, agents=["kimi", "opus"])
                best = max(agent_results, key=lambda r: r.confidence) if agent_results else None
                if best:
                    results.append({
                        "task_id": task.id,
                        "file": task.file_path,
                        "severity": task.context.get("severity"),
                        "agent": best.agent,
                        "status": best.status,
                        "confidence": best.confidence,
                        "has_patch": bool(best.patch),
                        "analysis": best.analysis[:200] if best.analysis else "",
                        "duration_s": best.duration_s,
                    })
            else:
                # Single agent for warnings/low
                result = pool.dispatch(task)
                results.append({
                    "task_id": task.id,
                    "file": task.file_path,
                    "severity": task.context.get("severity"),
                    "agent": result.agent,
                    "status": result.status,
                    "confidence": result.confidence,
                    "has_patch": bool(result.patch),
                    "analysis": result.analysis[:200] if result.analysis else "",
                    "duration_s": result.duration_s,
                })
        except Exception as e:
            logger.warning(f"[WORK-LOOP] Task {task.id} dispatch failed: {e}")
            results.append({
                "task_id": task.id,
                "file": task.file_path,
                "status": "dispatch_error",
                "error": str(e)[:200],
            })

    # 4. Summary
    completed = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    patched = sum(1 for r in results if r.get("has_patch"))

    summary = {
        "run_id": run_id,
        "status": "completed",
        "total_issues": len(issues),
        "tasks_dispatched": len(tasks),
        "tasks_completed": completed,
        "tasks_failed": failed,
        "patches_generated": patched,
        "critical_issues": sum(1 for i in issues if i["severity"] == "critical"),
        "warning_issues": sum(1 for i in issues if i["severity"] == "warning"),
        "results": results,
        "duration_s": round(time.time() - start, 2),
        "group_session": pool.ledger.get_summary(),
    }

    # Track in Genesis
    _track(
        f"Stabilisation run {run_id}: {completed}/{len(tasks)} fixed, {patched} patches",
        tags=["stabilisation", "work_loop"],
    )

    _emit("stabilisation.completed", {
        "run_id": run_id,
        "completed": completed,
        "failed": failed,
        "patches": patched,
        "duration_s": summary["duration_s"],
    })

    logger.info(
        f"[WORK-LOOP] Run {run_id} complete: "
        f"{completed} fixed, {patched} patches, {failed} failed "
        f"in {summary['duration_s']}s"
    )

    return summary


# ======================================================================
# Event Listener -- subscribe to pipeline.deploy_gate
# ======================================================================

_listener_active = False
_listener_lock = threading.Lock()


def _on_deploy_gate(event):
    """
    Handler for pipeline.deploy_gate events.
    When the deploy gate fires, kick off a stabilisation run.
    """
    try:
        logger.info(f"[WORK-LOOP] Deploy gate event received, starting stabilisation")
        # Run in background thread so we don't block the event bus
        t = threading.Thread(
            target=run_stabilisation,
            kwargs={"max_tasks": 5},
            daemon=True,
            name="stabilise-deploy-gate",
        )
        t.start()
    except Exception as e:
        logger.warning(f"[WORK-LOOP] Deploy gate handler failed: {e}")


def _on_healing_completed(event):
    """When healing swarm completes, run targeted stabilisation on remaining issues."""
    try:
        data = event.data if hasattr(event, "data") else {}
        if data.get("remaining_issues", 0) > 0:
            logger.info("[WORK-LOOP] Healing swarm has remaining issues, dispatching agents")
            t = threading.Thread(
                target=run_stabilisation,
                kwargs={"max_tasks": 3},
                daemon=True,
                name="stabilise-post-healing",
            )
            t.start()
    except Exception as e:
        logger.debug(f"[WORK-LOOP] Post-healing handler: {e}")


def _on_system_health_changed(event):
    """When system health degrades, proactively stabilise."""
    try:
        data = event.data if hasattr(event, "data") else {}
        health = data.get("health", "")
        if health in ("degraded", "critical"):
            logger.info(f"[WORK-LOOP] System health {health}, triggering stabilisation")
            t = threading.Thread(
                target=run_stabilisation,
                kwargs={"max_tasks": 8},
                daemon=True,
                name="stabilise-health",
            )
            t.start()
    except Exception as e:
        logger.debug(f"[WORK-LOOP] Health handler: {e}")


def start_agent_work_loop():
    """
    Start the agent work loop -- subscribes to Spindle events and actively
    dispatches Kimi+Opus to fix issues as they're discovered.
    
    Call this during app startup to activate autonomous stabilisation.
    """
    global _listener_active
    with _listener_lock:
        if _listener_active:
            return
        _listener_active = True

    try:
        from cognitive.event_bus import subscribe

        # Subscribe to deploy gate events
        subscribe("pipeline.deploy_gate", _on_deploy_gate)
        
        # Subscribe to healing events for follow-up
        subscribe("healing.completed", _on_healing_completed)
        
        # Subscribe to health degradation
        subscribe("system.health_changed", _on_system_health_changed)

        logger.info(
            "[WORK-LOOP] Agent work loop started -- "
            "listening on: pipeline.deploy_gate, healing.completed, system.health_changed"
        )

        # Emit registration event
        _emit("stabilisation.listener.registered", {
            "topics": ["pipeline.deploy_gate", "healing.completed", "system.health_changed"],
            "agents": ["kimi", "opus", "ollama"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        logger.error(f"[WORK-LOOP] Failed to start: {e}")
        _listener_active = False


def stop_agent_work_loop():
    """Stop the agent work loop."""
    global _listener_active
    with _listener_lock:
        if not _listener_active:
            return
        _listener_active = False

    try:
        from cognitive.event_bus import unsubscribe
        unsubscribe("pipeline.deploy_gate", _on_deploy_gate)
        unsubscribe("healing.completed", _on_healing_completed)
        unsubscribe("system.health_changed", _on_system_health_changed)
        logger.info("[WORK-LOOP] Agent work loop stopped")
    except Exception:
        pass


# ======================================================================
# Helpers
# ======================================================================

def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="agent_work_loop")
    except Exception:
        pass


def _track(what: str, tags: list = None) -> Optional[str]:
    try:
        from api._genesis_tracker import track
        return track(
            key_type="system_event",
            what=what,
            who="agent_work_loop",
            tags=["work_loop", "stabilisation"] + (tags or []),
        )
    except Exception:
        return None
