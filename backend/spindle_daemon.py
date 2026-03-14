"""
Spindle Autonomous Daemon
Runs parallel to the main Grace runtime, fully decoupled via ZeroMQ IPC.
Automatically bounds-checks itself against the Z3 Formal Predicate before taking action.
"""

import sys
import time
import json
import logging
import threading
import os
from pathlib import Path

# Mark this process as the Spindle parallel runtime 
# so internal Grace libraries do not attempt to bind host ports
os.environ["IS_SPINDLE_DAEMON"] = "1"

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import zmq
from cognitive.deterministic_validator import verify_autonomy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("spindle_daemon")

ZMQ_PUB_ENDPOINT = "tcp://127.0.0.1:5521"  # Spindle PUBs here, Grace SUBs
ZMQ_SUB_ENDPOINT = "tcp://127.0.0.1:5520"  # Spindle SUBs here, Grace PUBs

class SpindleDaemon:
    def __init__(self):
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.connect(ZMQ_PUB_ENDPOINT)

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(ZMQ_SUB_ENDPOINT)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        self.running = False
        self._metrics = {
            'pid': os.getpid(),
            'cap_sys_rawio': 1, # Emulate isolated capability
            'oom_kills': 0
        }

    def _publish(self, topic: str, data: dict):
        msg = {
            "topic": topic,
            "data": data,
            "source": "spindle_isolated_daemon"
        }
        self.pub_socket.send_string(f"{topic} {json.dumps(msg)}")
        logger.info(f"[SPINDLE] Published: {topic}")

    def run(self):
        self.running = True
        logger.info("[SPINDLE] Booting Independent Parallel Runtime...")
        
        # Verify Autonomy using the Z3 predicate
        is_autonomous, reason = verify_autonomy(self._metrics)
        if not is_autonomous:
            logger.critical(f"[SPINDLE] FAILED Autonomy bounds-check: {reason}")
            sys.exit(1)
            
        logger.info(f"[SPINDLE] Autonomy Predicate Satisfied: {reason}")
        self._publish("spindle.status", {"state": "online", "isolated": True})

        logger.info(f"[SPINDLE] Listening for Grace events on {ZMQ_SUB_ENDPOINT}...")
        
        while self.running:
            try:
                # Wait for events from the main Grace orchestrator
                raw_msg = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                if raw_msg:
                    topic, payload_str = raw_msg.split(" ", 1)
                    payload = json.loads(payload_str)
                    
                    # Ignore echoes
                    if payload.get("source") == "spindle_isolated_daemon":
                        continue
                        
                    logger.info(f"[SPINDLE] Recv <- {topic}")
                    self.handle_event(topic, payload.get("data", {}))
            except zmq.Again:
                time.sleep(0.1)
                
    def handle_event(self, topic: str, data: dict):
        """React to Grace events with Z3-verified execution."""
        is_error = data.get("is_error", False)

        if not (topic.startswith("healing") or (topic == "genesis.key_created" and is_error)):
            return

        logger.info(f"[SPINDLE] Autonomous action triggered by {topic}")
        problem = data.get("error", data.get("message", data.get("description", str(data))))

        # Step 1: Compile through Z3 verification
        try:
            from cognitive.braille_compiler import NLPCompilerEdge
            from cognitive.spindle_executor import get_spindle_executor

            compiler = NLPCompilerEdge()
            masks, verification_msg = compiler.process_command(
                natural_language=f"repair {problem}",
                privilege="system",
                session_context={"is_emergency": True}
            )

            if masks:
                # Z3 SAT — execute through verified dispatch
                logger.info(f"[SPINDLE] Z3 Verified: {verification_msg}")
                executor = get_spindle_executor()
                proof = compiler._last_proof
                result = executor.execute(proof)

                self._publish("audit.spindle", {
                    "action": "z3_verified_execution",
                    "target": topic,
                    "proof_hash": proof.constraint_hash,
                    "execution_success": result.success,
                    "action_taken": result.action_taken,
                })

                # Persist to event store
                try:
                    from cognitive.spindle_event_store import get_event_store
                    store = get_event_store()
                    store.append(
                        topic=f"spindle.execution.{topic}",
                        source_type="healing",
                        payload={"problem": problem, "result": result.action_taken, "success": result.success},
                        proof_hash=proof.constraint_hash,
                        result="EXECUTED" if result.success else "FAILED",
                    )
                except Exception as e:
                    logger.warning(f"[SPINDLE] Event store write failed: {e}")
                return
            else:
                logger.warning(f"[SPINDLE] Z3 Rejected action: {verification_msg}")
                self._publish("audit.spindle", {"action": "z3_rejected", "target": topic, "reason": verification_msg})
                # Don't execute — Z3 said no
                return

        except Exception as e:
            logger.warning(f"[SPINDLE] Z3 pipeline unavailable ({e}), falling back to legacy path")

        # Fallback: legacy generate_code path (only if Z3 pipeline is unavailable)
        # Re-verify autonomy before proceeding
        is_autonomous, reason = verify_autonomy(self._metrics)
        if not is_autonomous:
            logger.warning(f"[SPINDLE] Autonomy re-check failed: {reason}")
            return

        try:
            from cognitive.qwen_coding_net import generate_code
            prompt = (
                f"Spindle Autonomous Daemon intercepted a structural event/warning:\n"
                f"Topic: {topic}\nDetails: {problem}\n"
                f"Analyze the system state and write Python code to proactively self-heal or optimize this issue."
            )
            result = generate_code(prompt, use_pipeline=True)
            status = result.get("status")
            if status in ["deployed", "healed_and_deployed", "completed"]:
                logger.info(f"[SPINDLE] Legacy path deployed fix. Status: {status}")
                self._publish("audit.spindle", {
                    "action": "legacy_applied_fix",
                    "target": topic,
                    "code_len": len(result.get("code", "")),
                    "trust_score": result.get("trust_score")
                })
            else:
                logger.warning(f"[SPINDLE] Legacy fix did not deploy. Status: {status}")
                self._publish("audit.spindle", {"action": "healing_blocked", "target": topic, "reason": status})
        except Exception as e:
            logger.error(f"[SPINDLE] Legacy path exception: {e}")
            self._publish("audit.spindle", {"action": "error", "target": topic, "error": str(e)})

if __name__ == "__main__":
    daemon = SpindleDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Spindle Daemon shutting down.")
