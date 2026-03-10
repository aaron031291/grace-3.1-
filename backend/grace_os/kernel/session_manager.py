"""
Grace OS — Session Manager

The entry point for starting and managing coding tasks.
Orchestrates the lifecycle of a Grace OS session.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .message_bus import MessageBus
from .layer_registry import LayerRegistry
from .message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

class SessionState:
    """Tracks the state of a single session."""
    def __init__(self, trace_id: str, prompt: str):
        self.trace_id = trace_id
        self.prompt = prompt
        self.start_time = datetime.now(timezone.utc)
        self.status = "initializing"  # initializing | planning | executing | verifying | completed | failed
        self.tasks: List[Dict[str, Any]] = []
        self.current_trust_score = 0.0
        self.error: Optional[str] = None

class SessionManager:
    """
    Manages Grace OS sessions.
    """

    def __init__(self, bus: MessageBus, registry: LayerRegistry, trust_threshold: float = 85.0):
        self.bus = bus
        self.registry = registry
        self.sessions: Dict[str, SessionState] = {}
        self.trust_threshold = trust_threshold

    async def start_session(self, prompt: str) -> str:
        """
        Starts a new Grace OS session from a user prompt.
        Routes through the full 9-layer pipeline:
        L1 (setup) → L2 (plan) → L3 (propose) → L4 (evaluate) → L5 (simulate)
        → L6 (codegen) → L7 (test) → L8 (verify) → L9 (deploy gate)
        
        Returns:
            trace_id: The unique ID for this session.
        """
        trace_id = str(uuid.uuid4())
        session = SessionState(trace_id, prompt)
        self.sessions[trace_id] = session
        layer_scores: Dict[str, float] = {}

        logger.info(f"[SessionManager] Starting session {trace_id}: {prompt[:50]}...")

        # ── L1: Setup Environment ──
        session.status = "setting_up"
        setup_msg = LayerMessage(
            from_layer="SessionManager", to_layer="L1_Runtime",
            message_type="SETUP_ENVIRONMENT",
            payload={"project_path": ".", "task": {"description": prompt}},
            trace_id=trace_id
        )
        setup_resp = await self.bus.send(setup_msg)
        layer_scores["L1"] = setup_resp.trust_score
        env_id = setup_resp.payload.get("environment_id", "")

        # ── L2: Decompose into tasks ──
        session.status = "planning"
        planning_msg = LayerMessage(
            from_layer="SessionManager", to_layer="L2_Planning",
            message_type="DECOMPOSE_TASK",
            payload={"prompt": prompt},
            trace_id=trace_id
        )
        plan_resp = await self.bus.send(planning_msg)
        layer_scores["L2"] = plan_resp.trust_score

        if plan_resp.status != "success":
            session.status = "failed"
            session.error = "Planning failed"
            return trace_id

        session.tasks = plan_resp.payload.get("tasks", [])
        logger.info(f"[SessionManager] Planning done. {len(session.tasks)} tasks.")

        # ── Per-task pipeline: L3 → L4 → L5 → L6 → L7 → L8 ──
        session.status = "executing"
        for task in session.tasks:
            task_desc = task.get("description", str(task))
            logger.info(f"[SessionManager] Processing task: {task_desc[:50]}")

            # L3: Propose solutions
            propose_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L3_Proposer",
                message_type="PROPOSE_SOLUTIONS",
                payload={"task": task, "context": prompt},
                trace_id=trace_id
            ))
            layer_scores["L3"] = propose_resp.trust_score
            proposals = propose_resp.payload.get("proposals", [])

            # L4: Evaluate & select
            eval_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L4_Evaluator",
                message_type="EVALUATE_PROPOSALS",
                payload={"proposals": proposals, "task": task},
                trace_id=trace_id
            ))
            layer_scores["L4"] = eval_resp.trust_score
            selected = eval_resp.payload.get("selected_proposal", proposals[0] if proposals else {})

            # L5: Simulate selected proposal
            sim_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L5_Simulation",
                message_type="SIMULATE_PROPOSAL",
                payload={"selected_proposal": selected, "task": task},
                trace_id=trace_id
            ))
            layer_scores["L5"] = sim_resp.trust_score

            # L6: Generate code
            exec_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L6_Codegen",
                message_type="EXECUTE_TASK",
                payload={**task, "selected_proposal": selected},
                trace_id=trace_id
            ))
            layer_scores["L6"] = exec_resp.trust_score

            if exec_resp.status != "success":
                session.status = "failed"
                session.error = f"Codegen failed: {exec_resp.payload.get('error')}"
                break

            # L7: Test
            test_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L7_Testing",
                message_type="VERIFY_TASK",
                payload=task,
                trace_id=trace_id
            ))
            layer_scores["L7"] = test_resp.trust_score

            # L8: Verify output
            verify_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L8_Verification",
                message_type="VERIFY_OUTPUT",
                payload={
                    "task": task,
                    "codegen_result": exec_resp.payload,
                    "test_result": {"status": test_resp.status},
                },
                trace_id=trace_id
            ))
            layer_scores["L8"] = verify_resp.trust_score

            if test_resp.status == "failure":
                session.status = "failed"
                session.error = f"Tests failed for task: {task.get('id')}"
                break

        # ── L9: Deployment Gate ──
        if session.status != "failed":
            session.status = "deploying"
            gate_resp = await self.bus.send(LayerMessage(
                from_layer="SessionManager", to_layer="L9_Deployment",
                message_type="DEPLOYMENT_CHECK",
                payload={
                    "task": {"description": prompt},
                    "layer_scores": layer_scores,
                    "verification_result": verify_resp.payload if 'verify_resp' in dir() else {},
                    "test_result": {"status": test_resp.status if 'test_resp' in dir() else "unknown"},
                    "trust_threshold": self.trust_threshold,
                },
                trace_id=trace_id
            ))
            layer_scores["L9"] = gate_resp.trust_score

            if gate_resp.payload.get("approved"):
                session.status = "completed"
                session.current_trust_score = gate_resp.payload.get("aggregate_trust", 0)
                logger.info(f"[SessionManager] Session {trace_id} COMPLETED. Trust: {session.current_trust_score:.1f}")
            else:
                session.status = "rejected"
                session.error = f"Deployment rejected: {gate_resp.payload.get('policy_violations')}"
                logger.warning(f"[SessionManager] Session {trace_id} REJECTED at gate.")

        return trace_id

    def get_session_status(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current state of a session."""
        session = self.sessions.get(trace_id)
        if not session:
            return None
            
        return {
            "trace_id": session.trace_id,
            "status": session.status,
            "tasks_count": len(session.tasks),
            "trust_score": session.current_trust_score,
            "error": session.error,
            "duration_sec": (datetime.now(timezone.utc) - session.start_time).total_seconds()
        }
