import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

MINIMUM_PROPOSAL_SCORE = 70


class EvaluatorLayer(GraceLayer):
    """
    Layer 4: Solution Evaluator & Ranker.
    Scores and ranks proposals from L3, selects the best one.
    """

    @property
    def layer_name(self) -> str:
        return "L4_Evaluator"

    @property
    def capabilities(self) -> List[str]:
        return ["evaluate_proposals", "comparative_scoring", "tradeoff_analysis"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["EVALUATE_PROPOSALS"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "EVALUATE_PROPOSALS":
            return await self._handle_evaluate(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_evaluate(self, message: LayerMessage) -> LayerResponse:
        """Score proposals and select the best one."""
        proposals = message.payload.get("proposals", [])
        task = message.payload.get("task", {})

        if not proposals:
            logger.warning("[L4] No proposals to evaluate.")
            return self.build_response(
                message, "failure",
                {"error": "No proposals received"},
                trust_score=20.0
            )

        logger.info(f"[L4] Evaluating {len(proposals)} proposals...")

        system_prompt = (
            "You are the L4 Evaluator of Grace OS. "
            "Score each proposal on 4 criteria (0-100 each): "
            "correctness, performance, maintainability, risk. "
            "Respond ONLY with a JSON array where each element has: "
            '"proposal_id" (string), "correctness" (int), "performance" (int), '
            '"maintainability" (int), "risk" (int), "total" (int average of the 4). '
            "Then add a final key 'selected' with the proposal_id of the best one."
        )

        proposals_text = json.dumps(proposals, indent=2)
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)

        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}\nProposals:\n{proposals_text}",
            system_prompt=system_prompt
        )

        try:
            evaluation = json.loads(llm_response) if llm_response else None

            if evaluation and isinstance(evaluation, dict):
                scores = evaluation.get("scores", evaluation.get("evaluations", []))
                selected_id = evaluation.get("selected", "")
            elif evaluation and isinstance(evaluation, list):
                scores = evaluation
                selected_id = max(scores, key=lambda s: s.get("total", 0)).get("proposal_id", "")
            else:
                scores = []
                selected_id = ""

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[L4] LLM parse failed, using heuristic scoring: {e}")
            scores = []
            selected_id = ""

        # Fallback: heuristic scoring based on risk_score from proposals
        if not scores or not selected_id:
            scores = []
            for p in proposals:
                risk = p.get("risk_score", 50)
                score = {
                    "proposal_id": p.get("id", "unknown"),
                    "correctness": 80,
                    "performance": 75,
                    "maintainability": 80,
                    "risk": max(0, 100 - risk),
                    "total": int((80 + 75 + 80 + max(0, 100 - risk)) / 4)
                }
                scores.append(score)
            selected_id = max(scores, key=lambda s: s["total"])["proposal_id"]

        # Check threshold — if best score is too low, ask L3 for more
        best_score = next((s for s in scores if s.get("proposal_id") == selected_id), {})
        if best_score.get("total", 0) < MINIMUM_PROPOSAL_SCORE:
            logger.warning(f"[L4] Best score {best_score.get('total')} below threshold {MINIMUM_PROPOSAL_SCORE}. Requesting more proposals.")

            await self.send_message(
                to_layer="L3_Proposer",
                message_type="REQUEST_MORE_PROPOSALS",
                payload={
                    "task": task,
                    "rejection_reasons": [f"All proposals scored below {MINIMUM_PROPOSAL_SCORE}"]
                },
                trace_id=message.trace_id,
                parent_message_id=message.id
            )

            return self.build_response(
                message, "partial",
                {"message": "All proposals below threshold. Requested more from L3.", "scores": scores},
                trust_score=40.0
            )

        # Find the winning proposal object
        selected_proposal = next((p for p in proposals if p.get("id") == selected_id), proposals[0])

        logger.info(f"[L4] Selected proposal: {selected_id} (score: {best_score.get('total', 'N/A')})")

        return self.build_response(
            message, "success",
            {
                "selected_proposal": selected_proposal,
                "scores": scores,
                "selected_id": selected_id,
                "task": task,
            },
            trust_score=85.0
        )
