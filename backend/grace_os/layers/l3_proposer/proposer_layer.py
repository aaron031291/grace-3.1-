import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class ProposerLayer(GraceLayer):
    """
    Layer 3: Solution Proposer.
    Generates 3+ diverse solution approaches for each sub-task.
    """

    @property
    def layer_name(self) -> str:
        return "L3_Proposer"

    @property
    def capabilities(self) -> List[str]:
        return ["propose_solutions", "strategy_generation", "diversity_enforcement"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["PROPOSE_SOLUTIONS", "REQUEST_MORE_PROPOSALS"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "PROPOSE_SOLUTIONS":
            return await self._handle_propose(message)
        elif message.message_type == "REQUEST_MORE_PROPOSALS":
            return await self._handle_more_proposals(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_propose(self, message: LayerMessage) -> LayerResponse:
        """Generate 3+ diverse solution proposals for a task."""
        task = message.payload.get("task", {})
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        context = message.payload.get("context", "")

        logger.info(f"[L3] Generating proposals for: {task_desc[:60]}...")

        system_prompt = (
            "You are the L3 Solution Proposer of Grace OS. "
            "Generate EXACTLY 3 distinct solution approaches for the given task. "
            "Proposals MUST differ in fundamental strategy, not cosmetic variations. "
            "Respond ONLY with a JSON array where each element has: "
            '"id" (string), "approach" (string summary), '
            '"tradeoffs" (string), "risk_score" (int 0-100). '
            "Example: "
            '[{"id":"p1","approach":"Refactor existing module","tradeoffs":"Lower risk but more work","risk_score":25}]'
        )

        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}\nContext: {context}",
            system_prompt=system_prompt
        )

        try:
            proposals = json.loads(llm_response) if llm_response else []
            if not isinstance(proposals, list) or len(proposals) < 1:
                proposals = [
                    {"id": "p1", "approach": "Direct implementation", "tradeoffs": "Fast but less flexible", "risk_score": 30},
                    {"id": "p2", "approach": "Modular refactor", "tradeoffs": "More work but extensible", "risk_score": 20},
                    {"id": "p3", "approach": "Minimal patch", "tradeoffs": "Quick fix, may need revisit", "risk_score": 50},
                ]

            return self.build_response(
                message, "success",
                {"proposals": proposals, "task": task},
                trust_score=75.0
            )
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"[L3] Failed to parse proposals: {e}")
            fallback = [
                {"id": "p1", "approach": "Direct implementation", "tradeoffs": "Default fallback", "risk_score": 40},
            ]
            return self.build_response(
                message, "partial",
                {"proposals": fallback, "task": task, "parse_error": str(e)},
                trust_score=50.0
            )

    async def _handle_more_proposals(self, message: LayerMessage) -> LayerResponse:
        """Generate additional proposals when L4 rejects all existing ones."""
        rejected_reasons = message.payload.get("rejection_reasons", [])
        task = message.payload.get("task", {})

        logger.info(f"[L3] Generating more proposals (previous rejected)...")

        system_prompt = (
            "You are the L3 Solution Proposer. Previous proposals were rejected. "
            f"Rejection reasons: {rejected_reasons}. "
            "Generate 3 NEW approaches that address these concerns. "
            "Respond ONLY with a JSON array of proposals."
        )

        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}",
            system_prompt=system_prompt
        )

        try:
            proposals = json.loads(llm_response) if llm_response else []
            return self.build_response(message, "success", {"proposals": proposals, "task": task}, trust_score=70.0)
        except Exception as e:
            logger.error(f"[L3] Failed on retry proposals: {e}")
            return self.build_response(message, "failure", {"error": str(e)}, trust_score=30.0)
