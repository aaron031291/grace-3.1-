"""
Qwen Model Pool — Async hot-swappable task-routed pool for 3 local Qwen 3.5 models.

Manages qwen3.5:27b (code/general/reasoning), qwen3.5:9b (fast)
with automatic task-based routing, async execution, health monitoring,
and governance contract enforcement.

Architecture:
  User/Grace query → task classification → pool selects optimal model →
  governance wrapper applied → async execution → Genesis key tracked →
  memory/event bus notified → response returned

Governance coding contract:
  - READ-ONLY by default: Qwen observes, analyzes, suggests
  - WRITE only when user explicitly prompts for code changes
  - All outputs pass through GovernanceAwareLLM (rules, hallucination guard)
  - Every call gets a Genesis key for full provenance
"""

import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class QwenTask(Enum):
    CODE = "code"
    REASON = "reason"
    FAST = "fast"
    GENERAL = "general"
    CHAT = "chat"
    DIAGNOSE = "diagnose"
    HEAL = "heal"
    LEARN = "learn"
    AUDIT = "audit"


class WriteMode(Enum):
    READ_ONLY = "read_only"
    WRITE = "write"


_TASK_TO_MODEL_KEY = {
    QwenTask.CODE: "code",
    QwenTask.REASON: "reason",
    QwenTask.FAST: "fast",
    QwenTask.GENERAL: "code",
    QwenTask.CHAT: "fast",
    QwenTask.DIAGNOSE: "reason",
    QwenTask.HEAL: "reason",
    QwenTask.LEARN: "fast",
    QwenTask.AUDIT: "reason",
}


@dataclass
class ModelSlot:
    key: str
    model_name: str
    tasks: List[QwenTask]
    healthy: bool = True
    total_calls: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass
class PoolStats:
    total_calls: int = 0
    total_errors: int = 0
    active_tasks: int = 0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_task: Dict[str, int] = field(default_factory=dict)
    write_calls: int = 0
    read_only_calls: int = 0


class QwenModelPool:
    """
    Async hot-swappable pool that manages all 3 Qwen models.

    Key behaviors:
    - Task-based routing: each task type maps to the optimal model
    - Hot-swap: models can be added/removed/replaced at runtime
    - Async: all calls run in a thread pool for non-blocking execution
    - Failover: if the primary model for a task fails, falls back to another
    - Governance: every call is wrapped with governance rules
    - Read-only by default: write mode requires explicit user intent
    - Health tracking: per-model health with auto-degradation
    """

    def __init__(self):
        self._slots: Dict[str, ModelSlot] = {}
        self._clients: Dict[str, BaseLLMClient] = {}
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="qwen-pool")
        self._stats = PoolStats()
        self._lock = threading.Lock()
        self._write_mode = WriteMode.READ_ONLY
        self._initialized = False

    def initialize(self):
        """Load models from settings and create clients."""
        if self._initialized:
            return

        try:
            from settings import settings
        except ImportError:
            logger.warning("[QWEN-POOL] Settings unavailable, using defaults")
            settings = None

        model_configs = {
            "code": {
                "model_name": getattr(settings, "QWEN_CODE_MODEL", None)
                    or getattr(settings, "OLLAMA_MODEL_CODE", None) or "qwen3.5:27b",
                "tasks": [QwenTask.CODE, QwenTask.GENERAL, QwenTask.AUDIT],
            },
            "reason": {
                "model_name": getattr(settings, "QWEN_REASON_MODEL", None)
                    or getattr(settings, "OLLAMA_MODEL_REASON", None) or "qwen3.5:27b",
                "tasks": [QwenTask.REASON, QwenTask.DIAGNOSE, QwenTask.HEAL],
            },
            "fast": {
                "model_name": getattr(settings, "OLLAMA_MODEL_FAST", None) or "qwen3.5:9b",
                "tasks": [QwenTask.FAST, QwenTask.CHAT, QwenTask.LEARN],
            },
        }

        for key, cfg in model_configs.items():
            self._slots[key] = ModelSlot(
                key=key,
                model_name=cfg["model_name"],
                tasks=cfg["tasks"],
            )

        self._build_clients()
        self._initialized = True
        logger.info(
            f"[QWEN-POOL] Initialized with {len(self._slots)} models: "
            + ", ".join(f"{k}={s.model_name}" for k, s in self._slots.items())
        )

    def _build_clients(self):
        """Create governed Qwen clients for each slot."""
        from .qwen_client import QwenLLMClient
        from .governance_wrapper import GovernanceAwareLLM

        try:
            from settings import settings
            api_key = getattr(settings, "QWEN_API_KEY", "")
        except ImportError:
            api_key = ""

        for key, slot in self._slots.items():
            raw_client = QwenLLMClient(api_key=api_key, model=slot.model_name)
            self._clients[key] = GovernanceAwareLLM(raw_client)

    def _select_model(self, task: QwenTask) -> str:
        """Select the best available model for a task."""
        primary_key = _TASK_TO_MODEL_KEY.get(task, "code")

        if primary_key in self._slots and self._slots[primary_key].healthy:
            return primary_key

        for key, slot in self._slots.items():
            if task in slot.tasks and slot.healthy:
                return key

        for key, slot in self._slots.items():
            if slot.healthy:
                logger.warning(f"[QWEN-POOL] Failover: {task.value} → {key}")
                return key

        return primary_key

    def _classify_task(self, prompt: str, explicit_task: Optional[str] = None) -> QwenTask:
        """Classify a prompt into a task type."""
        if explicit_task:
            try:
                return QwenTask(explicit_task)
            except ValueError:
                pass

        p = prompt.lower()

        code_signals = ["write code", "implement", "function", "class ", "def ", "refactor",
                        "fix the code", "generate code", "build a", "create a script"]
        if any(s in p for s in code_signals):
            return QwenTask.CODE

        reason_signals = ["why", "explain", "analyze", "reason", "think through",
                          "what if", "compare", "trade-off", "pros and cons"]
        if any(s in p for s in reason_signals):
            return QwenTask.REASON

        diagnose_signals = ["diagnose", "debug", "error", "broken", "failing", "crash"]
        if any(s in p for s in diagnose_signals):
            return QwenTask.DIAGNOSE

        heal_signals = ["fix", "heal", "repair", "recover", "self-heal"]
        if any(s in p for s in heal_signals):
            return QwenTask.HEAL

        return QwenTask.FAST

    def _check_write_permission(self, task: QwenTask, user_prompted: bool) -> WriteMode:
        """Enforce read-only unless user explicitly requests write."""
        write_tasks = {QwenTask.CODE, QwenTask.HEAL}
        if task in write_tasks and user_prompted:
            return WriteMode.WRITE
        return WriteMode.READ_ONLY

    def _apply_read_only_prefix(self, system_prompt: Optional[str], mode: WriteMode) -> str:
        """Inject read-only governance contract into the system prompt."""
        base = system_prompt or ""
        if mode == WriteMode.READ_ONLY:
            contract = (
                "\n\nGOVERNANCE CONTRACT — READ-ONLY MODE:\n"
                "You are in READ-ONLY mode. You may observe, analyze, explain, and suggest.\n"
                "You MUST NOT generate code that modifies files, databases, or system state.\n"
                "If asked to make changes, explain what you WOULD do and ask the user to confirm.\n"
            )
            return base + contract
        else:
            contract = (
                "\n\nGOVERNANCE CONTRACT — WRITE MODE (user-authorized):\n"
                "The user has explicitly requested changes. You may generate code and modifications.\n"
                "All changes are tracked via Genesis keys. Follow all governance rules.\n"
            )
            return base + contract

    async def generate(
        self,
        prompt: str,
        task: Optional[str] = None,
        user_prompted: bool = False,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Async generate with task routing, governance, and tracking.

        Returns dict with response, model used, task, mode, and latency.
        """
        if not self._initialized:
            self.initialize()

        classified_task = self._classify_task(prompt, task)
        model_key = self._select_model(classified_task)
        mode = self._check_write_permission(classified_task, user_prompted)
        governed_prompt = self._apply_read_only_prefix(system_prompt, mode)

        client = self._clients.get(model_key)
        if not client:
            return {"response": "No Qwen model available", "error": True}

        slot = self._slots[model_key]

        with self._lock:
            self._stats.active_tasks += 1
            self._stats.total_calls += 1
            self._stats.by_task[classified_task.value] = self._stats.by_task.get(classified_task.value, 0) + 1
            if mode == WriteMode.WRITE:
                self._stats.write_calls += 1
            else:
                self._stats.read_only_calls += 1

        start = time.time()
        error_msg = None

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: client.generate(
                    prompt=prompt,
                    system_prompt=governed_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ),
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[QWEN-POOL] {model_key} failed: {e}")
            response = None

            with self._lock:
                slot.total_errors += 1
                slot.last_error = error_msg
                if slot.total_errors > 3 and slot.total_calls > 0:
                    error_rate = slot.total_errors / slot.total_calls
                    if error_rate > 0.5:
                        slot.healthy = False
                        logger.warning(f"[QWEN-POOL] {model_key} marked unhealthy (error rate {error_rate:.0%})")

            if error_msg:
                fallback_key = self._get_fallback(model_key)
                if fallback_key:
                    logger.info(f"[QWEN-POOL] Failover {model_key} → {fallback_key}")
                    try:
                        fallback_client = self._clients[fallback_key]
                        response = await loop.run_in_executor(
                            self._executor,
                            lambda: fallback_client.generate(
                                prompt=prompt,
                                system_prompt=governed_prompt,
                                temperature=temperature,
                                max_tokens=max_tokens,
                                **kwargs,
                            ),
                        )
                        model_key = fallback_key
                        error_msg = None
                    except Exception as e2:
                        error_msg = f"Primary: {error_msg}; Fallback: {e2}"
        finally:
            latency = (time.time() - start) * 1000
            with self._lock:
                self._stats.active_tasks = max(0, self._stats.active_tasks - 1)
                slot.total_calls += 1
                slot.total_latency_ms += latency
                slot.last_used = datetime.now(timezone.utc)

        self._emit_events(classified_task, model_key, mode, latency, error_msg)

        return {
            "response": response if isinstance(response, str) else str(response) if response else "",
            "model": self._slots[model_key].model_name,
            "model_key": model_key,
            "task": classified_task.value,
            "mode": mode.value,
            "latency_ms": round(latency, 1),
            "error": error_msg,
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        task: Optional[str] = None,
        user_prompted: bool = False,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Async chat with task routing."""
        if not self._initialized:
            self.initialize()

        last_msg = messages[-1].get("content", "") if messages else ""
        classified_task = self._classify_task(last_msg, task or "chat")
        model_key = self._select_model(classified_task)
        mode = self._check_write_permission(classified_task, user_prompted)

        governed_messages = list(messages)
        contract = self._apply_read_only_prefix(None, mode)
        if governed_messages and governed_messages[0].get("role") == "system":
            governed_messages[0] = {
                "role": "system",
                "content": governed_messages[0]["content"] + contract,
            }
        else:
            governed_messages.insert(0, {"role": "system", "content": contract.strip()})

        client = self._clients.get(model_key)
        if not client:
            return {"response": "No Qwen model available", "error": True}

        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: client.chat(
                    messages=governed_messages,
                    temperature=temperature,
                    **kwargs,
                ),
            )
            error_msg = None
        except Exception as e:
            response = ""
            error_msg = str(e)

        latency = (time.time() - start) * 1000
        slot = self._slots[model_key]
        with self._lock:
            slot.total_calls += 1
            slot.total_latency_ms += latency
            slot.last_used = datetime.now(timezone.utc)

        return {
            "response": response if isinstance(response, str) else str(response),
            "model": slot.model_name,
            "model_key": model_key,
            "task": classified_task.value,
            "mode": mode.value,
            "latency_ms": round(latency, 1),
            "error": error_msg,
        }

    def _get_fallback(self, failed_key: str) -> Optional[str]:
        """Get a fallback model key when the primary fails."""
        fallback_order = ["fast", "code", "reason"]
        for key in fallback_order:
            if key != failed_key and key in self._slots and self._slots[key].healthy:
                return key
        return None

    def _emit_events(self, task: QwenTask, model_key: str, mode: WriteMode,
                     latency_ms: float, error: Optional[str]):
        """Fire events to cognitive event bus and Layer 1."""
        try:
            from cognitive.event_bus import publish_async
            publish_async("qwen_pool.call_completed", {
                "task": task.value,
                "model": model_key,
                "mode": mode.value,
                "latency_ms": latency_ms,
                "success": error is None,
            }, source="qwen_pool")
        except Exception:
            pass

    # ── Hot-swap API ──

    def swap_model(self, key: str, new_model_name: str):
        """Hot-swap a model at runtime without restarting."""
        if key not in self._slots:
            raise ValueError(f"Unknown slot: {key}")

        old_name = self._slots[key].model_name
        self._slots[key].model_name = new_model_name
        self._slots[key].healthy = True
        self._slots[key].total_errors = 0
        self._slots[key].last_error = None

        from .qwen_client import QwenLLMClient
        from .governance_wrapper import GovernanceAwareLLM
        try:
            from settings import settings
            api_key = getattr(settings, "QWEN_API_KEY", "")
        except ImportError:
            api_key = ""

        raw = QwenLLMClient(api_key=api_key, model=new_model_name)
        self._clients[key] = GovernanceAwareLLM(raw)

        logger.info(f"[QWEN-POOL] Hot-swapped {key}: {old_name} → {new_model_name}")

        try:
            from cognitive.event_bus import publish_async
            publish_async("qwen_pool.model_swapped", {
                "slot": key, "old_model": old_name, "new_model": new_model_name,
            }, source="qwen_pool")
        except Exception:
            pass

    def mark_healthy(self, key: str):
        """Manually mark a model as healthy after recovery."""
        if key in self._slots:
            self._slots[key].healthy = True
            self._slots[key].total_errors = 0
            self._slots[key].last_error = None

    def set_write_mode(self, enabled: bool):
        """Enable/disable global write mode (overrides per-call checks)."""
        self._write_mode = WriteMode.WRITE if enabled else WriteMode.READ_ONLY

    # ── Status API ──

    def get_status(self) -> Dict[str, Any]:
        """Full pool status for monitoring and Ask Grace."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "global_write_mode": self._write_mode.value,
                "stats": {
                    "total_calls": self._stats.total_calls,
                    "total_errors": self._stats.total_errors,
                    "active_tasks": self._stats.active_tasks,
                    "write_calls": self._stats.write_calls,
                    "read_only_calls": self._stats.read_only_calls,
                    "by_task": dict(self._stats.by_task),
                },
                "models": {
                    key: {
                        "model_name": slot.model_name,
                        "healthy": slot.healthy,
                        "total_calls": slot.total_calls,
                        "total_errors": slot.total_errors,
                        "avg_latency_ms": round(slot.total_latency_ms / max(slot.total_calls, 1), 1),
                        "last_used": slot.last_used.isoformat() if slot.last_used else None,
                        "last_error": slot.last_error,
                        "tasks": [t.value for t in slot.tasks],
                    }
                    for key, slot in self._slots.items()
                },
            }

    def get_client_for_task(self, task: str) -> BaseLLMClient:
        """Get the governed client for a specific task (for direct use by factory)."""
        if not self._initialized:
            self.initialize()
        try:
            qt = QwenTask(task)
        except ValueError:
            qt = QwenTask.FAST
        key = self._select_model(qt)
        return self._clients.get(key)


_pool: Optional[QwenModelPool] = None
_pool_lock = threading.Lock()


def get_qwen_pool() -> QwenModelPool:
    """Get or create the global Qwen model pool singleton."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = QwenModelPool()
                _pool.initialize()
    return _pool
