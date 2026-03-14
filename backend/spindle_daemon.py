"""
Spindle Autonomous Daemon — Async Parallel Runtime
Runs as an independent process, fully decoupled from Grace via ZeroMQ.
Sub-agent architecture with async event loop and thread pool for CPU-bound Z3 work.
"""

import sys
import os
import time
import json
import signal
import logging
import asyncio
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

os.environ["IS_SPINDLE_DAEMON"] = "1"
sys.path.insert(0, str(Path(__file__).parent))

import zmq
import zmq.asyncio
from cognitive.deterministic_validator import verify_autonomy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("spindle_daemon")

ZMQ_PUB_ENDPOINT = "tcp://127.0.0.1:5521"
ZMQ_SUB_ENDPOINT = "tcp://127.0.0.1:5520"


@dataclass
class SubAgentTask:
    """A unit of work for a sub-agent."""
    task_id: str
    topic: str
    data: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None


class SubAgentPool:
    """Thread pool for CPU-bound sub-agent work (Z3 solving, healing)."""

    def __init__(self, max_workers: int = 8):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="spindle-agent")
        self._active: Dict[str, Future] = {}
        self._completed: list = []
        self._lock = threading.Lock()
        self._task_counter = 0
        logger.info(f"[POOL] SubAgentPool started with {max_workers} workers")

    def submit(self, fn, *args, task_id: str = None, **kwargs) -> str:
        """Submit work to a sub-agent. Returns task_id."""
        with self._lock:
            self._task_counter += 1
            tid = task_id or f"SA-{self._task_counter:05d}-{int(time.time()*1000) % 100000}"
        future = self._pool.submit(fn, *args, **kwargs)
        with self._lock:
            self._active[tid] = future
        future.add_done_callback(lambda f: self._on_complete(tid, f))
        logger.debug(f"[POOL] Submitted {tid}")
        return tid

    def _on_complete(self, task_id: str, future: Future):
        with self._lock:
            self._active.pop(task_id, None)
            try:
                result = future.result()
                self._completed.append({"task_id": task_id, "success": True, "result": result})
            except Exception as e:
                self._completed.append({"task_id": task_id, "success": False, "error": str(e)})
                logger.error(f"[POOL] {task_id} failed: {e}")
            if len(self._completed) > 500:
                self._completed = self._completed[-500:]

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": len(self._active),
                "completed": len(self._completed),
                "total_submitted": self._task_counter,
            }

    def shutdown(self):
        self._pool.shutdown(wait=False)


class SpindleDaemon:
    def __init__(self):
        self._zmq_ctx = zmq.asyncio.Context()
        self._pub_socket = self._zmq_ctx.socket(zmq.PUB)
        self._pub_socket.connect(ZMQ_PUB_ENDPOINT)

        self._sub_socket = self._zmq_ctx.socket(zmq.SUB)
        self._sub_socket.connect(ZMQ_SUB_ENDPOINT)
        self._sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._pool = SubAgentPool(max_workers=8)
        self._running = False
        self._metrics = {
            'pid': os.getpid(),
            'cap_sys_rawio': 1,
            'oom_kills': 0,
        }
        self._stats = {
            "events_received": 0,
            "events_processed": 0,
            "z3_verified": 0,
            "z3_rejected": 0,
            "errors": 0,
        }

    async def _publish(self, topic: str, data: dict):
        msg = {"topic": topic, "data": data, "source": "spindle_isolated_daemon"}
        await self._pub_socket.send_string(f"{topic} {json.dumps(msg)}")

    # ── Core event loop ─────────────────────────────────────

    async def run(self):
        self._running = True
        logger.info("[SPINDLE] Booting Async Parallel Runtime...")

        is_autonomous, reason = verify_autonomy(self._metrics)
        if not is_autonomous:
            logger.critical(f"[SPINDLE] FAILED Autonomy bounds-check: {reason}")
            sys.exit(1)

        logger.info(f"[SPINDLE] Autonomy Predicate Satisfied: {reason}")
        await self._publish("spindle.status", {"state": "online", "isolated": True, "mode": "async_parallel"})

        # Launch all concurrent tasks
        tasks = [
            asyncio.create_task(self._zmq_listener(), name="zmq-listener"),
            asyncio.create_task(self._event_dispatcher(), name="event-dispatcher"),
            asyncio.create_task(self._projection_updater(), name="projection-updater"),
            asyncio.create_task(self._health_heartbeat(), name="health-heartbeat"),
            asyncio.create_task(self._metrics_reporter(), name="metrics-reporter"),
        ]

        logger.info(f"[SPINDLE] {len(tasks)} background services started")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("[SPINDLE] Shutting down...")
        finally:
            self._pool.shutdown()

    async def _zmq_listener(self):
        """Async ZMQ listener — receives events and queues them."""
        logger.info(f"[SPINDLE] Listening on {ZMQ_SUB_ENDPOINT}...")
        poller = zmq.asyncio.Poller()
        poller.register(self._sub_socket, zmq.POLLIN)

        while self._running:
            events = await poller.poll(timeout=100)  # 100ms poll
            if events:
                raw_msg = await self._sub_socket.recv_string()
                if " " in raw_msg:
                    topic, payload_str = raw_msg.split(" ", 1)
                    try:
                        payload = json.loads(payload_str)
                        if payload.get("source") == "spindle_isolated_daemon":
                            continue
                        self._stats["events_received"] += 1
                        await self._event_queue.put(SubAgentTask(
                            task_id=f"EVT-{self._stats['events_received']:06d}",
                            topic=topic,
                            data=payload.get("data", {}),
                        ))
                    except json.JSONDecodeError:
                        logger.warning(f"[SPINDLE] Bad JSON from ZMQ: {raw_msg[:100]}")

    async def _event_dispatcher(self):
        """Pulls events from queue and dispatches to sub-agent pool."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            is_error = task.data.get("is_error", False)
            if task.topic.startswith("healing") or (task.topic == "genesis.key_created" and is_error):
                # Dispatch to thread pool — Z3 + execution is CPU-bound
                self._pool.submit(
                    self._handle_event_sync,
                    task.topic, task.data,
                    task_id=task.task_id,
                )
                self._stats["events_processed"] += 1
            self._event_queue.task_done()

    def _handle_event_sync(self, topic: str, data: dict) -> Dict[str, Any]:
        """
        Sub-agent worker: runs in thread pool.
        Performs Z3 verification + execution synchronously.
        """
        problem = data.get("error", data.get("message", data.get("description", str(data))))
        logger.info(f"[SUB-AGENT] Processing {topic}: {problem[:80]}")

        # Primary path: Z3-verified execution
        try:
            from cognitive.braille_compiler import NLPCompilerEdge
            from cognitive.spindle_executor import get_spindle_executor

            compiler = NLPCompilerEdge()
            masks, verification_msg = compiler.process_command(
                natural_language=f"repair {problem}",
                privilege="system",
                session_context={"is_emergency": True},
            )

            if masks:
                logger.info(f"[SUB-AGENT] Z3 SAT: {verification_msg}")
                self._stats["z3_verified"] += 1
                executor = get_spindle_executor()
                proof = compiler._last_proof
                result = executor.execute(proof)

                # Fire-and-forget publish (thread-safe via zmq)
                asyncio.run_coroutine_threadsafe(
                    self._publish("audit.spindle", {
                        "action": "z3_verified_execution",
                        "target": topic,
                        "proof_hash": proof.constraint_hash,
                        "execution_success": result.success,
                        "action_taken": result.action_taken,
                    }),
                    asyncio.get_event_loop(),
                )

                # Persist to event store
                try:
                    from cognitive.spindle_event_store import get_event_store
                    get_event_store().append(
                        topic=f"spindle.execution.{topic}",
                        source_type="healing",
                        payload={"problem": problem, "result": result.action_taken, "success": result.success},
                        proof_hash=proof.constraint_hash,
                        result="EXECUTED" if result.success else "FAILED",
                    )
                except Exception as e:
                    logger.warning(f"[SUB-AGENT] Event store write failed: {e}")

                return {"status": "executed", "success": result.success, "action": result.action_taken}
            else:
                self._stats["z3_rejected"] += 1
                logger.warning(f"[SUB-AGENT] Z3 REJECTED: {verification_msg}")
                asyncio.run_coroutine_threadsafe(
                    self._publish("audit.spindle", {"action": "z3_rejected", "target": topic, "reason": verification_msg}),
                    asyncio.get_event_loop(),
                )
                return {"status": "rejected", "reason": verification_msg}

        except Exception as e:
            logger.warning(f"[SUB-AGENT] Z3 pipeline unavailable ({e}), trying legacy path")

        # Fallback: legacy path
        is_autonomous, reason = verify_autonomy(self._metrics)
        if not is_autonomous:
            return {"status": "blocked", "reason": reason}

        try:
            from cognitive.qwen_coding_net import generate_code
            prompt = (
                f"Spindle Autonomous Daemon intercepted:\n"
                f"Topic: {topic}\nDetails: {problem}\n"
                f"Write Python code to self-heal this issue."
            )
            result = generate_code(prompt, use_pipeline=True)
            status = result.get("status")
            self._stats["events_processed"] += 1
            return {"status": status, "legacy": True}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"[SUB-AGENT] Legacy path failed: {e}")
            return {"status": "error", "error": str(e)}

    # ── Background services ─────────────────────────────────

    async def _projection_updater(self):
        """Background: update CQRS projections every 5 seconds."""
        await asyncio.sleep(3)  # Initial delay
        while self._running:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._update_projection)
            except Exception as e:
                logger.debug(f"[BG] Projection update failed: {e}")
            await asyncio.sleep(5)

    def _update_projection(self):
        try:
            from cognitive.spindle_projection import get_spindle_projection
            get_spindle_projection().update()
        except Exception:
            pass

    async def _health_heartbeat(self):
        """Background: publish health heartbeat every 10 seconds."""
        while self._running:
            await asyncio.sleep(10)
            await self._publish("spindle.heartbeat", {
                "state": "alive",
                "pid": os.getpid(),
                "pool": self._pool.stats,
                "queue_size": self._event_queue.qsize(),
            })

    async def _metrics_reporter(self):
        """Background: report metrics every 30 seconds."""
        while self._running:
            await asyncio.sleep(30)
            logger.info(
                f"[METRICS] recv={self._stats['events_received']} "
                f"proc={self._stats['events_processed']} "
                f"z3_ok={self._stats['z3_verified']} "
                f"z3_no={self._stats['z3_rejected']} "
                f"err={self._stats['errors']} "
                f"pool={self._pool.stats} "
                f"queue={self._event_queue.qsize()}"
            )


def main():
    daemon = SpindleDaemon()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig, frame):
        logger.info(f"[SPINDLE] Received signal {sig}, shutting down...")
        daemon._running = False
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(daemon.run())
    except KeyboardInterrupt:
        logger.info("[SPINDLE] Interrupted, shutting down...")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
