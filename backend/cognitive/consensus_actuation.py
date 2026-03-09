"""
Consensus Actuation Framework

Provides strict, audited actuation primitives to the Consensus Engine.
Allows models (Opus, Kimi, Qwen) to execute actions based on their consensus decisions,
bridging the gap between deliberation and actual system fluidity.
"""

import logging
import json
import subprocess
from typing import Dict, Any, Optional

from settings import settings
from api._genesis_tracker import track
from cognitive.autonomous_healing_system import HealingAction

logger = logging.getLogger(__name__)

class ConsensusActuation:
    """
    Exposes actuation endpoints for the Consensus Engine.
    Requires minimum trust scores and logs every action via Genesis Keys.
    """

    def __init__(self, min_trust_required: float = 0.7):
        self.min_trust_required = min_trust_required

    def execute_action(self, action_payload: Dict[str, Any], decision_context: str, trust_score: float) -> Dict[str, Any]:
        """
        Main routing gateway for executing a consensus-driven action.
        """
        if trust_score < self.min_trust_required:
            logger.warning(
                f"[CONSENSUS-ACTUATION] Blocked action due to low trust score ({trust_score} < {self.min_trust_required})"
            )
            return {"status": "blocked", "reason": "insufficient_trust_score"}

        action_type = action_payload.get("action_type")
        params = action_payload.get("params", {})
        rationale = action_payload.get("rationale", "No rationale provided by consensus")
        
        # Guardian Action Gate (NEW)
        try:
            from guardian.action_gate import get_action_gate
            gate = get_action_gate()
            auth = gate.authorize(action_payload, trust_score)
            if not auth["authorized"]:
                logger.warning(f"[CONSENSUS-ACTUATION] Guardian Blocked: {auth['reason']}")
                return {"status": "blocked", "reason": auth['reason']}
        except Exception as e:
            logger.error(f"[CONSENSUS-ACTUATION] Guardian Gate crash, default deny: {e}")
            return {"status": "blocked", "reason": f"Guardian Gate Error: {e}"}

        logger.info(f"[CONSENSUS-ACTUATION] Authorized command: {action_type} (trust={trust_score:.2f})")

        # 1. Audit Log via Genesis Tracker (Intent phase)
        try:
            track(
                key_type="consensus_actuation_intent",
                what=f"Consensus engine intent: {action_type}",
                why=rationale,
                how="consensus_actuation.execute_action",
                output_data={"action_payload": action_payload, "trust_score": trust_score, "decision": decision_context},
            )
        except Exception as e:
            logger.error(f"[CONSENSUS-ACTUATION] Failed to log intent via Genesis Tracker: {e}")

        # 2. Route to specific primitive
        result = {}
        try:
            if action_type == "execute_shell_command":
                result = self._execute_shell_command(params)
            elif action_type == "submit_coding_task":
                result = self._submit_coding_task(params)
            elif action_type == "restart_service":
                result = self._restart_service(params)
            elif action_type == "update_knowledge_base":
                result = self._update_knowledge_base(params)
            else:
                result = {"status": "error", "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}

        # 3. Audit Log via Genesis Tracker (Outcome phase)
        try:
            track(
                key_type="consensus_actuation_outcome",
                what=f"Consensus engine outcome: {action_type} -> {result.get('status')}",
                why=rationale,
                how="consensus_actuation.execute_action",
                output_data={"result": result, "trust_score": trust_score},
                is_error=result.get("status") == "error",
            )
        except Exception as e:
            logger.error(f"[CONSENSUS-ACTUATION] Failed to log outcome via Genesis Tracker: {e}")

        return result

    def _execute_shell_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a shell command safely (read-only / safe commands mainly, mapped by governance)."""
        command = params.get("command")
        if not command:
            return {"status": "error", "error": "Missing 'command' parameter"}
        
        # Basic safety blocklist for shell commands
        blocked_keywords = ["rm -rf", "mkfs", "dd", "> /dev/sda", "shutdown", "reboot"]
        for kw in blocked_keywords:
            if kw in command:
                return {"status": "blocked", "reason": f"Command contains blocked keyword: {kw}"}

        logger.info(f"[CONSENSUS-ACTUATION] Executing shell command: {command}")
        try:
            process = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "status": "success" if process.returncode == 0 else "failed",
                "returncode": process.returncode,
                "stdout": process.stdout[:2000],  # Truncate
                "stderr": process.stderr[:2000]
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command execution timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _submit_coding_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an autonomous coding task directly to the agent queue."""
        from coding_agent.task_queue import submit
        
        instructions = params.get("instructions")
        target_file = params.get("target_file")
        error_class = params.get("error_class", "")
        is_dry_run = str(params.get("dry_run", "false")).lower() == "true"
        
        if not instructions:
            return {"status": "error", "error": "Missing 'instructions' parameter"}

        if is_dry_run:
            logger.info(f"[CONSENSUS-ACTUATION] DRY-RUN coding task: {instructions[:50]}...")
            return {
                "status": "success", 
                "task_id": "dry_run_simulation", 
                "message": "Guardian Sandboxed Dry-Run successful. The task queue would have handled this."
            }

        logger.info(f"[CONSENSUS-ACTUATION] Submitting coding task: {instructions[:50]}...")
        task_id = submit(
            task_type="consensus_fix",
            instructions=instructions,
            context={"target_file": target_file} if target_file else {},
            priority=2, # High priority for consensus fixes
            origin="consensus_engine",
            error_class=error_class
        )
        return {"status": "success", "task_id": task_id}

    def _restart_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a process or service restart via the AutonomousHealingSystem."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem

        # Since we just need the system logic for the restart mapping, we mock the DB session
        # In a full run, we would inject the real DB session.
        try:
            healer = AutonomousHealingSystem(session=None, simulation_mode=False)
            target = params.get("target", "backend")
            
            # Map target to AVN healing action
            action_map = {
                "database": HealingAction.CONNECTION_RESET,
                "backend": HealingAction.SERVICE_RESTART,
                "worker": HealingAction.PROCESS_RESTART,
                "cache": HealingAction.CACHE_FLUSH
            }
            
            action = action_map.get(target, HealingAction.PROCESS_RESTART)
            
            is_dry_run = str(params.get("dry_run", "false")).lower() == "true"
            if is_dry_run:
                logger.info(f"[CONSENSUS-ACTUATION] DRY-RUN restart for: {target}")
                return {"status": "success", "message": f"Dry-run simulation of {target} restart complete."}

            logger.info(f"[CONSENSUS-ACTUATION] Triggering restart for: {target}")
            result = healer._execute_action(
                action_name=action.value,
                anomaly={"type": "consensus_directed_restart", "severity": "warning"},
                user_id="consensus_engine"
            )
            return result
        except Exception as e:
            return {"status": "error", "error": f"Failed to restart service: {e}"}

    def _update_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Inject a discovered rule or solution directly into Unified Memory or Magma."""
        content = params.get("content")
        pattern_type = params.get("pattern_type", "consensus_learning")
        
        if not content:
            return {"status": "error", "error": "Missing 'content' parameter"}

        logger.info(f"[CONSENSUS-ACTUATION] Pushing knowledge to memory: {pattern_type}")
        
        try:
            from cognitive.unified_memory import get_unified_memory
            get_unified_memory().store_episode(
                problem="Consensus discovery",
                action=pattern_type,
                outcome=content,
                trust=0.9,
                source="consensus_engine"
            )
            return {"status": "success", "message": "Knowledge recorded in Unified Memory"}
        except Exception as e:
            return {"status": "error", "error": f"Memory store failed: {e}"}

# Global singleton instance
_actuation_gateway = None

def get_actuation_gateway() -> ConsensusActuation:
    global _actuation_gateway
    if not _actuation_gateway:
        _actuation_gateway = ConsensusActuation()
    return _actuation_gateway
