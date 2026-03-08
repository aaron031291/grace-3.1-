"""
coding_agent/task_queue.py
─────────────────────────────────────────────────────────────────────────────
Persistent DB-backed task queue for the coding agent.

Every error that needs a code fix, every self-healing request, and every
autonomous coding task goes through here. Tasks are:
  - Submitted  (error_pipeline, self_healing, user request)
  - Polled     (coding agent worker thread)
  - Completed  (success or failure recorded + learning event)
  - Retried    (up to MAX_RETRIES, with backoff)
"""
from __future__ import annotations

import json
import logging
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
POLL_INTERVAL = 5  # seconds


# ── In-memory queue (backed by DB on submit) ─────────────────────────────
_queue: List[Dict[str, Any]] = []
_queue_lock = threading.Lock()
_worker_thread: Optional[threading.Thread] = None
_worker_running = False

# Registered handlers: task_type → callable
_handlers: Dict[str, Callable] = {}


def register_handler(task_type: str, handler: Callable) -> None:
    """Register a callable to handle a specific task type."""
    _handlers[task_type] = handler
    logger.info("[CODING-AGENT] Registered handler for task type: %s", task_type)


def submit(
    task_type: str,
    instructions: str,
    context: Dict[str, Any] = None,
    priority: int = 5,
    origin: str = "unknown",
    error_class: str = "",
) -> str:
    """
    Submit a task to the coding agent queue.
    Returns a task_id string.
    """
    task_id = f"task_{int(time.time() * 1000)}_{task_type[:8]}"

    # ── TimeSense: adjust priority based on time of day ──────────────────
    time_ctx = {}
    try:
        from cognitive.time_sense import TimeSense
        time_ctx = TimeSense.now_context()
        period = time_ctx.get("period", "")

        # Defer non-critical tasks during late night / night
        if period in ("late_night", "night") and priority >= 6:
            priority = min(priority + 2, 10)   # push further back
            logger.debug(
                "[CODING-AGENT] %s period — deferring non-critical task (priority now %d)",
                period, priority,
            )
        # Boost urgent tasks during business hours
        elif time_ctx.get("is_business_hours") and priority <= 3:
            priority = max(priority - 1, 1)    # small boost for urgent fixes
    except Exception:
        pass  # TimeSense unavailable — use original priority

    task = {
        "task_id": task_id,
        "task_type": task_type,
        "instructions": instructions,
        "context": context or {},
        "priority": priority,
        "origin": origin,
        "error_class": error_class,
        "status": "pending",
        "attempts": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "time_context": time_ctx,   # available to worker/handler
    }

    with _queue_lock:
        # Insert sorted by priority (lower number = higher priority)
        _queue.append(task)
        _queue.sort(key=lambda t: (t["priority"], t["created_at"]))

    # Persist to DB (fire and forget)
    _persist_task(task)

    logger.info(
        "[CODING-AGENT] Task submitted: %s (type=%s priority=%d origin=%s)",
        task_id, task_type, priority, origin,
    )

    # Record learning event
    _record_submission(task)

    return task_id


def _persist_task(task: Dict) -> None:
    """Persist task to DB for durability across restarts."""
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as session:
            session.execute(text("""
                INSERT INTO coding_agent_tasks
                    (task_id, task_type, instructions, context_data, priority,
                     origin, error_class, status, attempts, created_at, updated_at)
                VALUES
                    (:task_id, :task_type, :instructions, :context_data, :priority,
                     :origin, :error_class, :status, :attempts, :created_at, :updated_at)
                ON CONFLICT (task_id) DO NOTHING
            """), {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "instructions": task["instructions"][:2000],
                "context_data": json.dumps(task["context"])[:4000],
                "priority": task["priority"],
                "origin": task["origin"],
                "error_class": task["error_class"],
                "status": task["status"],
                "attempts": task["attempts"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
            })
    except Exception as e:
        logger.error("[CODING-AGENT] Task persistence skipped (table may not exist yet): %s", e)


def poll() -> Optional[Dict]:
    """Get the next pending task. Returns None if queue is empty."""
    with _queue_lock:
        for task in _queue:
            if task["status"] == "pending" and task["attempts"] < MAX_RETRIES:
                task["status"] = "running"
                task["attempts"] += 1
                task["updated_at"] = datetime.utcnow().isoformat()
                return task
    return None


def complete(task_id: str, success: bool, result: Any = None, error: str = "") -> None:
    """Mark a task as completed or failed."""
    with _queue_lock:
        for task in _queue:
            if task["task_id"] == task_id:
                task["status"] = "completed" if success else "failed"
                task["result"] = result
                task["error"] = error
                task["updated_at"] = datetime.utcnow().isoformat()

                if not success and task["attempts"] < MAX_RETRIES:
                    # Re-queue for retry with backoff
                    task["status"] = "pending"
                    logger.info(
                        "[CODING-AGENT] Task %s failed, retrying (attempt %d/%d)",
                        task_id, task["attempts"], MAX_RETRIES,
                    )
                break

    _record_completion(task_id, success, result, error)


def get_status() -> Dict:
    """Get queue statistics."""
    with _queue_lock:
        by_status = {}
        for t in _queue:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    return {"queue_depth": len(_queue), "by_status": by_status}


def get_swarm_status() -> List[Dict]:
    """Get active background tasks for the UI Swarm Swimlane/Task Manager."""
    active = []
    with _queue_lock:
        for t in _queue:
            if t["status"] in ("pending", "running"):
                active.append({
                    "id": t["task_id"],
                    "name": t["instructions"][:40] + "...",
                    "status": t["status"],
                    "progress": 45 if t["status"] == "running" else 0,
                    "layer": 7, # Default display layer
                    "time": t["created_at"]
                })
    return active


# ── Worker thread ─────────────────────────────────────────────────────────

def start_worker() -> None:
    """Start the background worker that processes coding tasks."""
    global _worker_thread, _worker_running
    if _worker_running:
        return
    _worker_running = True
    # We still use a background thread, but inside it we run an asyncio event loop!
    _worker_thread = threading.Thread(
        target=_run_async_worker,
        daemon=True,
        name="grace-coding-agent",
    )
    _worker_thread.start()
    logger.info("[CODING-AGENT] Async Worker started (polling every %ds)", POLL_INTERVAL)


def _run_async_worker() -> None:
    """Entry point for the worker thread to initialize the asyncio loop."""
    asyncio.run(_async_worker_loop())


async def _async_worker_loop() -> None:
    """True asyncio worker loop utilizing ThreadPoolExecutor for concurrent LLM API calls."""
    loop = asyncio.get_running_loop()
    # Execute LLM tasks in parallel!
    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="sub-agent") as pool:
        logger.info("[CODING-AGENT] ThreadPoolExecutor online (10 workers). Swarm is ready.")
        while _worker_running:
            try:
                task = poll()
                if task:
                    # Fire and forget into the thread pool, immediately freeing the loop for the next task!
                    loop.run_in_executor(pool, _dispatch, task)
                else:
                    await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error("[CODING-AGENT] Worker error: %s", e)
                await asyncio.sleep(POLL_INTERVAL)


def _dispatch(task: Dict) -> None:
    """Dispatch a task to its registered handler."""
    handler = _handlers.get(task["task_type"])
    if handler is None:
        # Default: route to QwenCodingNet
        handler = _default_handler

    logger.info(
        "[CODING-AGENT] 🔨 Executing task %s (type=%s attempt=%d)",
        task["task_id"], task["task_type"], task["attempts"],
    )

    try:
        result = handler(task)
        complete(task["task_id"], success=True, result=result)
        logger.info("[CODING-AGENT] ✅ Task %s completed successfully", task["task_id"])
    except Exception as e:
        complete(task["task_id"], success=False, error=str(e))
        logger.error("[CODING-AGENT] ❌ Task %s failed: %s", task["task_id"], e)


def _build_memory_context(instructions: str, error_class: str = "") -> str:
    """
    Pull context from all 3 memory layers before calling Qwen.
    Returns a formatted string prepended to the coding instructions.
    """
    sections = []

    # 1. Magma — graph-based, causal, semantic memory
    try:
        from cognitive import magma_bridge as magma
        magma_ctx = magma.query_context(instructions, limit=4)
        if magma_ctx:
            sections.append(f"[MAGMA CONTEXT — causal/semantic graph memory]\n{magma_ctx[:800]}")
        # If this is a healing task, ask Magma WHY the error occurs
        if error_class:
            causal = magma.query_causal(f"Why does {error_class} error occur in Python?")
            if causal:
                sections.append(f"[MAGMA CAUSAL — why {error_class} errors happen]\n{str(causal)[:400]}")
    except Exception:
        pass

    # 2. UnifiedMemory — episodic + learning + procedural (search_all)
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        results = mem.search_all(instructions, limit=6, min_trust=0.4)
        if results:
            lines = []
            for r in results[:4]:
                src = r.get("source", "?")
                content = r.get("content", r.get("description", ""))[:150]
                trust = r.get("trust", 0)
                lines.append(f"  [{src}|trust={trust:.2f}] {content}")
            sections.append("[UNIFIED MEMORY — past episodes/learnings/procedures]\n" + "\n".join(lines))
    except Exception:
        pass

    # 3. GhostMemory — current session contextual cache
    try:
        from cognitive.ghost_memory import get_ghost_memory
        ghost_ctx = get_ghost_memory().get_context(max_tokens=600)
        if ghost_ctx:
            sections.append(f"[GHOST MEMORY — current session context]\n{ghost_ctx[:600]}")
    except Exception:
        pass

    if not sections:
        return ""

    instruction = (
        "═══════════════════════════════════════════════════════════\n"
        "MEMORY CONTEXT — READ THIS BEFORE GENERATING ANY CODE\n"
        "═══════════════════════════════════════════════════════════\n"
        "You have been given context from Grace's memory systems above:\n"
        "  • MAGMA CONTEXT  — semantic + causal graph memory (WHY errors occur)\n"
        "  • UNIFIED MEMORY — past episodes, learning examples, proven procedures\n"
        "  • GHOST MEMORY   — current session history (avoid repeating mistakes)\n"
        "\n"
        "RULES:\n"
        "  1. If a past fix is relevant, build upon it — do NOT start from scratch\n"
        "  2. If MAGMA CAUSAL explains why an error occurs, address that root cause\n"
        "  3. If UNIFIED MEMORY shows a similar problem was solved before, use that solution\n"
        "  4. Your fix must be more targeted and correct than random generation\n"
        "═══════════════════════════════════════════════════════════\n\n"
    )
    return "\n\n".join(sections) + "\n\n" + instruction + "[TASK]\n"


def _store_memory_outcome(
    instructions: str,
    error_class: str,
    success: bool,
    result: dict,
    task_id: str,
) -> None:
    """Store task outcome into all 3 memory layers. Non-blocking."""
    outcome_label = "success" if success else "failure"
    apply_result = result.get("apply_result", {})
    fix_info = (
        f"Applied to {apply_result.get('file', 'unknown')}, "
        f"{apply_result.get('lines', 0)} lines"
        if apply_result.get("success") else "not applied to disk"
    )

    # 1. UnifiedMemory
    try:
        from cognitive.unified_memory import get_unified_memory
        get_unified_memory().store_episode(
            problem=instructions[:200],
            action=f"coding_agent.{error_class or 'general'}",
            outcome=f"{outcome_label}: {fix_info}",
            trust=0.85 if success else 0.2,
            source="coding_agent",
        )
    except Exception:
        pass

    # 2. Magma — store as pattern (if fix applied) or decision (always)
    try:
        from cognitive import magma_bridge as magma
        if success and apply_result.get("success"):
            magma.store_pattern(
                pattern_type="coding_fix",
                description=f"{error_class} fix: {instructions[:100]}",
                data={"task_id": task_id, "fix_info": fix_info},
            )
        magma.store_decision(
            action="coding_agent_task",
            target=apply_result.get("file", "unknown"),
            rationale=instructions[:150],
            data={"outcome": outcome_label, "task_id": task_id},
        )
        # Ingest full context for future retrieval
        magma.ingest(
            f"Coding task ({outcome_label}): {instructions[:200]}. Result: {fix_info}",
            source="coding_agent",
            metadata={"task_id": task_id, "error_class": error_class},
        )
    except Exception:
        pass

    # 3. GhostMemory — append event to session cache
    try:
        from cognitive.ghost_memory import get_ghost_memory
        get_ghost_memory().append(
            event_type="success" if success else "failure",
            content=f"[{task_id}] {error_class}: {fix_info}",
            metadata={"task_id": task_id},
        )
    except Exception:
        pass


def _default_handler(task: Dict) -> Dict:
    """Default: send to QwenCodingNet for code generation / fixing, then apply to disk."""
    from cognitive.qwen_coding_net import get_qwen_net
    net = get_qwen_net()
    instructions = task["instructions"]
    ctx = task.get("context", {})
    error_class = task.get("error_class", "")

    # ── 1. Deterministic Gate — AST/risk analysis BEFORE Qwen ──────────
    gate_context = ""
    try:
        from coding_agent.deterministic_gate import get_gate
        gate_report = get_gate().analyze(
            task=instructions,
            existing_code=ctx.get("existing_code", ""),
            file_context=ctx.get("target_file", ""),
        )
        # Block high-risk tasks (score > 0.7) — governance contract
        if gate_report.risk_score > 0.7:
            logger.warning(
                "[CODING-AGENT] ⛔ Task blocked by governance gate (risk=%.2f): %s",
                gate_report.risk_score, instructions[:60],
            )
            try:
                from api._genesis_tracker import track
                track(
                    key_type="governance_block",
                    what_description=f"High-risk coding task blocked (risk={gate_report.risk_score:.2f})",
                    why_reason=instructions[:200],
                    how_method="deterministic_gate.risk_score",
                    context_data={"task_id": task["task_id"], "risk": gate_report.risk_score},
                    is_error=False,
                )
            except Exception:
                pass
            return {
                "blocked": True,
                "reason": f"Risk score {gate_report.risk_score:.2f} exceeds governance threshold 0.7",
                "gate_report": gate_report.as_prompt_context(),
            }
        gate_context = gate_report.as_prompt_context()
        logger.debug("[CODING-AGENT] Gate passed (risk=%.2f)", gate_report.risk_score)
    except Exception as gate_err:
        logger.debug("[CODING-AGENT] Deterministic gate skipped: %s", gate_err)

    # ── 2. 3-Layer Memory Context — Magma + Unified + Ghost ────────────
    memory_prefix = _build_memory_context(instructions, error_class)

    # ── 3. Build enriched instructions for Qwen ─────────────────────────
    enriched_instructions = ""
    if memory_prefix:
        enriched_instructions += memory_prefix
    if gate_context:
        enriched_instructions += f"[DETERMINISTIC ANALYSIS]\n{gate_context}\n\n"

    # Prepend error context if this is a fix_error task
    if error_class:
        enriched_instructions += (
            f"[Self-healing task — {error_class} error "
            f"from {ctx.get('location', ctx.get('file', 'unknown'))}]\n"
            f"Error: {ctx.get('sql_error', ctx.get('error', ''))}\n"
        )
        if ctx.get("existing_code"):
            enriched_instructions += f"\n[EXISTING SOURCE CODE OF {ctx.get('file', 'target_file')}]\n```python\n{ctx.get('existing_code')}\n```\n\n"
        else:
            enriched_instructions += "\n"
    enriched_instructions += instructions

    # ── 4. Ghost Memory — start tracking this task ──────────────────────
    try:
        from cognitive.ghost_memory import get_ghost_memory
        get_ghost_memory().start_task(instructions[:200])
    except Exception:
        pass

    # ── 5. Call Qwen ─────────────────────────────────────────────────────
    code_result = net.execute_task(enriched_instructions, use_consensus=False)
    generated_code = code_result.get("code", "")

    # ── 5b. Verification Pass — trust gate before anything touches disk ──
    verification_result = None
    if generated_code:
        try:
            from coding_agent.verification_pass import get_verification_pass
            from cognitive.ghost_memory import get_ghost_memory
            ghost_ctx = get_ghost_memory().get_context(max_tokens=800)
            verification_result = get_verification_pass().verify(
                code=generated_code,
                task=instructions,
                ghost_context=ghost_ctx,
            )
            code_result["verification"] = {
                "accepted": verification_result.accepted,
                "trust_score": round(verification_result.trust_score, 3),
                "flags": verification_result.flags,
                "contradictions": verification_result.contradictions,
                "revision_hint": verification_result.revision_hint,
            }
            # KPI: record verification outcome
            from core.kpi_recorder import record_component_kpi
            record_component_kpi(
                "coding_agent.verification",
                "accepted" if verification_result.accepted else "rejected",
                value=verification_result.trust_score,
                success=verification_result.accepted,
            )
            if not verification_result.accepted:
                logger.warning(
                    "[CODING-AGENT] ❌ Verification REJECTED (trust=%.2f): %s — %s",
                    verification_result.trust_score,
                    task.get("task_id", "?"),
                    verification_result.revision_hint[:80],
                )
                # Store rejection in memory so future tasks avoid same mistake
                try:
                    from cognitive.unified_memory import get_unified_memory
                    get_unified_memory().store_episode(
                        problem=instructions[:200],
                        action=f"coding_agent.verification.rejected",
                        outcome=f"Rejected trust={verification_result.trust_score:.2f}: {verification_result.revision_hint[:100]}",
                        trust=0.1,
                        source="verification_pass",
                    )
                except Exception:
                    pass
                code_result["apply_result"] = {
                    "success": False,
                    "reason": f"Verification rejected: trust={verification_result.trust_score:.2f}. {verification_result.revision_hint}",
                }
                _store_memory_outcome(
                    instructions=instructions, error_class=error_class,
                    success=False, result=code_result, task_id=task["task_id"],
                )
                return code_result
        except Exception as ve:
            logger.debug("[CODING-AGENT] Verification pass skipped: %s", ve)

    # ── 6. Quarantine and Verify (Context Shadowing) ───────────────────────
    target_file = ctx.get("target_file") or ctx.get("file") or ctx.get("location")
    if generated_code and target_file and target_file.endswith(".py"):
        try:
            from verification.context_shadower import shadower
            
            # Use the shadower to write to __grACE_shadow, verify via VVT, and atomic swap if perfect
            shadow_result = shadower.propose_module_update(
                target_file_path=target_file,
                new_code_content=generated_code,
                module_name_to_test=target_file.split("/")[-1].replace(".py", "") # Simple heuristic
            )
            
            code_result["apply_result"] = {
                "success": shadow_result.get("success", False),
                "file": target_file,
                "lines": len(generated_code.splitlines()) if shadow_result.get("success") else 0,
                "status": shadow_result.get("status", "UNKNOWN_SHADOW_ERROR"),
                "trust_coin": shadow_result.get("trust_coin", "DENIED"),
                "error": shadow_result.get("error", "")[:150]
            }
            
            if shadow_result.get("success"):
                logger.info(
                    "[CODING-AGENT] ✅ Code verified in quarantine and HOT-SWAPPED: %s (%s)",
                    target_file, shadow_result.get("trust_coin")
                )
            else:
                logger.warning(
                    "[CODING-AGENT] ⚠️ Context Shadowing blocked mutation on VVT Failure: %s",
                    target_file
                )
        except Exception as e:
            logger.error("[CODING-AGENT] Context shadower error: %s", e)
            code_result["apply_result"] = {"success": False, "error": str(e)[:200]}
    else:
        code_result["apply_result"] = {
            "success": False,
            "reason": "no valid python target_file in task context — manual review needed",
            "code_preview": generated_code[:200] if generated_code else "",
        }

    # ── 7. Store outcome into all 3 memory layers ───────────────────────
    apply_ok = code_result["apply_result"].get("success", False)
    trust_coin = code_result.get("apply_result", {}).get("trust_coin")

    # Only pass trust_coin downstream if the shadower minted one
    if apply_ok and trust_coin:
        from cognitive.unified_memory import get_unified_memory
        # By passing the trust coin, we prove to the TrustGate we belong in episodic/procedural memory
        _store_memory_outcome(
            instructions=instructions,
            error_class=error_class,
            success=True,
            result=code_result,
            task_id=task["task_id"],
        )
        get_unified_memory().store_episode(
            problem=instructions[:200],
            action=f"coding_agent.{error_class or 'general'}",
            outcome=f"success: Hot-swapped {target_file}",
            trust=0.9,
            source="context_shadower",
            trust_coin=trust_coin
        )
    else:
        _store_memory_outcome(
            instructions=instructions,
            error_class=error_class,
            success=False,
            result=code_result,
            task_id=task["task_id"],
        )

    return code_result



# ── Learning recorder ─────────────────────────────────────────────────────

def _record_submission(task: Dict) -> None:
    try:
        from api._genesis_tracker import track
        track(
            key_type="agent_action",
            what_description=f"Coding agent task submitted: {task['task_type']}",
            why_reason=task["instructions"][:200],
            how_method="coding_agent.task_queue.submit",
            context_data={"task_id": task["task_id"], "priority": task["priority"]},
        )
    except Exception:
        pass


def _record_completion(task_id: str, success: bool, result: Any, error: str) -> None:
    try:
        from api._genesis_tracker import track
        track(
            key_type="fix_applied" if success else "error",
            what_description=f"Coding agent task {'completed' if success else 'failed'}: {task_id}",
            how_method="coding_agent.task_queue.complete",
            context_data={"task_id": task_id, "success": success, "error": error[:200] if error else ""},
            is_error=not success,
        )
    except Exception:
        pass
