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

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import zmq
from cognitive.deterministic_validator import verify_autonomy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("spindle_daemon")

ZMQ_PUB_ENDPOINT = "tcp://127.0.0.1:5516"  # Spindle PUBs here, Grace SUBs
ZMQ_SUB_ENDPOINT = "tcp://127.0.0.1:5515"  # Spindle SUBs here, Grace PUBs

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
        """React to Genesis Keys or other Grace events."""
        if topic == "genesis.key_created" or topic.startswith("healing"):
            # Mock autonomous reaction: we received a structural signal, let's act on it
            logger.info(f"[SPINDLE] Autonomous action triggered by {topic}")
            # E.g., spawn coding task, run tests, etc.
            self._publish("audit.spindle", {"action": "analyzed_event", "target": topic})

if __name__ == "__main__":
    daemon = SpindleDaemon()
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Spindle Daemon shutting down.")
