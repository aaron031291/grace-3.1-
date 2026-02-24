import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

class PlanningLayer(GraceLayer):
    """
    Layer 2: Task Decomposition & Planning.
    Breaks down user intents into actionable task graphs.
    """

    @property
    def layer_name(self) -> str:
        return "L2_Planning"

    @property
    def capabilities(self) -> List[str]:
        return ["task_decomposition", "planning", "intent_parsing"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["DECOMPOSE_TASK", "REPLAN_TASK"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        """
        Main entry point for L2.
        """
        if message.message_type == "DECOMPOSE_TASK":
            return await self._handle_decompose(message)
        elif message.message_type == "REPLAN_TASK":
            return await self._handle_replan(message)
        
        return self.build_response(
            message, 
            "failure", 
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_decompose(self, message: LayerMessage) -> LayerResponse:
        """
        Logic for decomposing a prompt into a task list.
        """
        prompt = message.payload.get("prompt", "")
        logger.info(f"[L2] Decomposing prompt: {prompt[:50]}...")
        
        # 1. Intent Parsing & Task Graph Generation (simplified for now)
        # In a real implementation, we'd call sub-components or the LLM.
        
        system_prompt = (
            "You are the L2 Planning Layer of Grace OS. "
            "Your job is to break down a user's coding request into a DAG of atomic tasks. "
            "Respond ONLY with a JSON list of tasks, where each task has: "
            "id, description, dependency_ids, and type (e.g., 'codegen', 'test')."
        )
        
        llm_response = await self.call_llm(
            prompt=f"Decompose this request: {prompt}",
            system_prompt=system_prompt
        )
        
        try:
            # We'd use a robust JSON parser here.
            import json
            tasks = json.loads(llm_response)
            return self.build_response(message, "success", {"tasks": tasks})
        except Exception as e:
            logger.error(f"[L2] Failed to parse LLM response: {e}")
            return self.build_response(message, "failure", {"error": "Malformed planning response from LLM."})

    async def _handle_replan(self, message: LayerMessage) -> LayerResponse:
        """
        Logic for re-planning based on downstream failures.
        """
        # TODO: Implement re-planning logic
        return self.build_response(message, "success", {"message": "Re-plan not yet implemented."})
