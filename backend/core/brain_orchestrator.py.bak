"""
Brain Orchestrator Ã¢â‚¬â€ intelligent multi-brain coordination.

Knows when to call which brains simultaneously.
Manages parallel execution across domains.
Self-aware of system state and task requirements.
"""

import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BrainOrchestrator:
    """
    Coordinates multiple brain calls simultaneously.
    Decides which brains a task needs based on task analysis.
    """

    TASK_BRAIN_MAP = {
        # Code & build tasks
        "build":    ["code", "ai", "system", "govern"],
        "fix":      ["ai", "code", "system"],
        "test":     ["ai", "system", "code"],
        "deploy":   ["system", "govern", "code"],
        # Analysis & review
        "analyze":  ["ai", "system", "files"],
        "review":   ["ai", "code", "govern"],
        # Knowledge & learning (wired to actual brains: ai=dl_train/fill_gaps, govern=trigger_learning, data=store)
        "learn":    ["ai", "govern", "data"],
        "remember": ["chat", "ai", "data"],
        "search":   ["files", "code", "data"],
        # Healing & governance
        "heal":     ["system", "ai", "govern"],
        "plan":     ["tasks", "ai", "govern"],
        # Interaction & data
        "chat":     ["chat", "ai"],
        "upload":   ["files", "data", "govern"],
        "filing":   ["files", "data"],
        "document": ["data", "files"],
        # Memory operations (chat=history, ai=consensus/recall, data=store)
        "recall":   ["chat", "ai", "data"],
        "store":    ["data", "chat", "govern"],
    }


    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="orchestrator")

    def orchestrate(self, task_type: str, payload: dict,
                    brains: List[str] = None) -> dict:
        """
        Execute a task across multiple brains simultaneously.
        Auto-detects which brains to call if not specified.
        """
        if not brains:
            brains = self._detect_brains(task_type, payload)

        start = time.time()
        results = {}
        futures = {}

        for brain_name in brains:
            action = self._best_action(brain_name, task_type, payload)
            future = self._executor.submit(
                self._call_brain, brain_name, action, payload
            )
            futures[future] = brain_name

        try:
            for future in as_completed(futures, timeout=30):
                brain_name = futures[future]
                try:
                    results[brain_name] = future.result(timeout=1)
                except Exception as e:
                    results[brain_name] = {"ok": False, "error": str(e)[:100]}
        except TimeoutError:
            # Collect whatever finished; mark the rest as timed out
            for future, brain_name in futures.items():
                if brain_name not in results:
                    if future.done():
                        try:
                            results[brain_name] = future.result(timeout=0)
                        except Exception as e:
                            results[brain_name] = {"ok": False, "error": str(e)[:100]}
                    else:
                        results[brain_name] = {"ok": False, "error": "timeout (30s)"}
                        future.cancel()

        latency = round((time.time() - start) * 1000, 1)

        # Record KPIs (governance + ML tracker)
        try:
            from core.governance_engine import record_kpi
            for brain, result in results.items():
                record_kpi("brain_orchestrator", brain,
                           passed=result.get("ok", False))
        except Exception:
            pass
        try:
            from core.kpi_recorder import record_brain_kpi
            for brain, result in results.items():
                action = payload.get("action") or "orchestrate"
                record_brain_kpi(brain, action, result.get("ok", False))
        except Exception:
            pass

        return {
            "task_type": task_type,
            "brains_called": brains,
            "results": results,
            "successful": sum(1 for r in results.values() if r.get("ok")),
            "failed": sum(1 for r in results.values() if not r.get("ok")),
            "latency_ms": latency,
        }

    def _detect_brains(self, task_type: str, payload: dict) -> list:
        """Auto-detect which brains to involve."""
        detected = self.TASK_BRAIN_MAP.get(task_type, ["ai", "system"])

        text = str(payload).lower()
        if "file" in text or "folder" in text:
            if "files" not in detected:
                detected.append("files")
        if "code" in text or "function" in text:
            if "code" not in detected:
                detected.append("code")
        if "rule" in text or "approve" in text:
            if "govern" not in detected:
                detected.append("govern")
        if "deterministic" in text or "ast" in text or "syntax check" in text or "phase 0" in text:
            if "deterministic" not in detected:
                detected.append("deterministic")

        return detected[:5]

    def _best_action(self, brain: str, task_type: str, payload: dict) -> str:
        """Pick the best action for a brain given the task type."""
        action_map = {
            ("ai", "build"): "pipeline",
            ("ai", "fix"): "deterministic_fix",
            ("ai", "test"): "logic_tests",
            ("ai", "analyze"): "cognitive_report",
            ("ai", "review"): "cognitive_report",
            ("ai", "learn"): "dl_train",
            ("code", "build"): "generate",
            ("code", "fix"): "generate",
            ("code", "review"): "projects",
            ("system", "build"): "runtime",
            ("system", "fix"): "auto_cycle",
            ("system", "heal"): "scan_heal",
            ("system", "test"): "probe",
            ("system", "deploy"): "hot_reload_all",
            ("system", "analyze"): "intelligence",
            ("govern", "build"): "rules",
            ("govern", "deploy"): "approvals",
            ("govern", "review"): "scores",
            ("files", "search"): "search",
            ("files", "analyze"): "stats",
            ("files", "filing"): "filing",
            ("files", "document"): "create_doc",
            ("data", "search"): "api_sources",
            ("data", "filing"): "librarian_organise_file",
            ("data", "document"): "librarian_process",
            ("chat", "chat"): "send",
            ("tasks", "plan"): "submit",
        }
        defaults = {
            "system": "runtime",
            "ai": "fast",
            "files": "stats",
            "data": "stats",
            "govern": "scores",
            "chat": "send",
            "tasks": "submit",
            "code": "projects",
            "deterministic": "scan",
        }
        return action_map.get((brain, task_type)) or defaults.get(brain, "runtime")

    def _call_brain(self, brain: str, action: str, payload: dict) -> dict:
        from api.brain_api_v2 import call_brain
        return call_brain(brain, action, payload)


_orchestrator: Optional[BrainOrchestrator] = None


def get_orchestrator() -> BrainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BrainOrchestrator()
    return _orchestrator
