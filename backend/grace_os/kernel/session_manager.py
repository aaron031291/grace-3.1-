"""
Grace OS — Session Manager

The entry point for starting and managing coding tasks.
Orchestrates the lifecycle of a Grace OS session.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from .message_bus import MessageBus
from .layer_registry import LayerRegistry
from .message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

class SessionState:
    """Tracks the state of a single session."""
    def __init__(self, trace_id: str, prompt: str):
        self.trace_id = trace_id
        self.prompt = prompt
        self.start_time = datetime.utcnow()
        self.status = "initializing"  # initializing | planning | executing | verifying | completed | failed
        self.tasks: List[Dict[str, Any]] = []
        self.current_trust_score = 0.0
        self.error: Optional[str] = None

class SessionManager:
    """
    Manages Grace OS sessions.
    """

    def __init__(self, bus: MessageBus, registry: LayerRegistry):
        self.bus = bus
        self.registry = registry
        self.sessions: Dict[str, SessionState] = {}

    async def start_session(self, prompt: str) -> str:
        """
        Starts a new Grace OS session from a user prompt.
        
        Returns:
            trace_id: The unique ID for this session.
        """
        trace_id = str(uuid.uuid4())
        session = SessionState(trace_id, prompt)
        self.sessions[trace_id] = session
        
        logger.info(f"[SessionManager] Starting session {trace_id}: {prompt[:50]}...")
        
        # 1. Trigger L2 (Planning)
        # We send a broadcast message that L2 will pick up.
        # Once L2 is implemented, it will subscribe to 'DECOMPOSE_TASK'.
        
        planning_msg = LayerMessage(
            from_layer="SessionManager",
            to_layer="L2_Planning",
            message_type="DECOMPOSE_TASK",
            payload={"prompt": prompt},
            trace_id=trace_id
        )
        
        session.status = "planning"
        
        # Note: In a real system, we'd fire and forget or wait depending on UI needs.
        # For the kernel demonstration, we'll await it.
        response = await self.bus.send(planning_msg)
        
        if response.status == "success":
            session.tasks = response.payload.get("tasks", [])
            session.status = "executing"
            logger.info(f"[SessionManager] Planning successful. {len(session.tasks)} tasks identified.")
            
            # 2. Sequential Execution (Simplified DAG handling for Stage 3)
            for task in session.tasks:
                logger.info(f"[SessionManager] Executing task: {task.get('description')}")
                
                # Execute Task (L6)
                exec_msg = LayerMessage(
                    from_layer="SessionManager",
                    to_layer="L6_Codegen",
                    message_type="EXECUTE_TASK",
                    payload=task,
                    trace_id=trace_id
                )
                exec_response = await self.bus.send(exec_msg)
                
                if exec_response.status != "success":
                    session.status = "failed"
                    session.error = f"Task execution failed: {exec_response.payload.get('error')}"
                    break
                    
                # Verify Task (L7)
                verify_msg = LayerMessage(
                    from_layer="SessionManager",
                    to_layer="L7_Testing",
                    message_type="VERIFY_TASK",
                    payload=task,
                    trace_id=trace_id
                )
                verify_response = await self.bus.send(verify_msg)
                
                if verify_response.status == "success":
                    logger.info(f"[SessionManager] Task verified: {task.get('id')}")
                elif verify_response.status == "partial":
                    logger.warning(f"[SessionManager] Task partial success (self-healing triggered): {task.get('id')}")
                    # In a real system, we'd wait for the L7->L6 fix loop to complete or continue.
                else:
                    session.status = "failed"
                    session.error = f"Task verification failed: {verify_response.payload.get('error')}"
                    break
            
            if session.status != "failed":
                session.status = "completed"
                logger.info(f"[SessionManager] Session {trace_id} completed successfully.")
            
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
            "duration_sec": (datetime.utcnow() - session.start_time).total_seconds()
        }
