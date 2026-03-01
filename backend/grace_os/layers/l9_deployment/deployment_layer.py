import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

DEFAULT_TRUST_THRESHOLD = 85


class DeploymentLayer(GraceLayer):
    """
    Layer 9: Deployment Gate.
    Final approval checkpoint — aggregates trust scores, enforces policies,
    plans commits, and gates deployment.
    """

    @property
    def layer_name(self) -> str:
        return "L9_Deployment"

    @property
    def capabilities(self) -> List[str]:
        return ["trust_aggregation", "policy_enforcement", "commit_planning", "rollback_planning"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["DEPLOYMENT_CHECK"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "DEPLOYMENT_CHECK":
            return await self._handle_deployment_check(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_deployment_check(self, message: LayerMessage) -> LayerResponse:
        """Aggregate trust scores, enforce policies, decide approve/reject."""
        task = message.payload.get("task", {})
        layer_scores = message.payload.get("layer_scores", {})
        verification_result = message.payload.get("verification_result", {})
        test_result = message.payload.get("test_result", {})
        threshold = message.payload.get("trust_threshold", DEFAULT_TRUST_THRESHOLD)

        logger.info(f"[L9] Running deployment gate check...")

        # 1. Aggregate trust scores
        score_values = [v for v in layer_scores.values() if isinstance(v, (int, float))]
        aggregate_trust = sum(score_values) / len(score_values) if score_values else 50.0

        # 2. Policy checks
        policy_violations = []

        # Tests must pass
        if test_result.get("status") == "failure":
            policy_violations.append("Tests did not pass")

        # Verification must be clean
        if verification_result.get("verified") is False:
            policy_violations.append("Verification failed")

        # Security flags block deployment
        security_flags = verification_result.get("security_flags", [])
        if security_flags:
            policy_violations.append(f"Security flags: {', '.join(security_flags)}")

        # Trust threshold
        if aggregate_trust < threshold:
            policy_violations.append(f"Trust score {aggregate_trust:.1f} below threshold {threshold}")

        approved = len(policy_violations) == 0

        # 3. If rejected, trigger re-plan
        if not approved:
            logger.warning(f"[L9] Deployment REJECTED. Violations: {policy_violations}")

            await self.send_message(
                to_layer="L2_Planning",
                message_type="REPLAN_TASK",
                payload={
                    "task": task,
                    "rejection_reasons": policy_violations,
                    "aggregate_trust": aggregate_trust,
                },
                trace_id=message.trace_id,
                parent_message_id=message.id
            )

            return self.build_response(
                message, "failure",
                {
                    "approved": False,
                    "aggregate_trust": aggregate_trust,
                    "policy_violations": policy_violations,
                    "message": "Deployment rejected. Re-plan requested.",
                },
                trust_score=aggregate_trust
            )

        # 4. Approved — plan commit
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        commit_plan = {
            "message": f"feat: {task_desc[:72]}",
            "files_changed": message.payload.get("files_changed", []),
            "rollback_steps": ["git revert HEAD"],
        }

        logger.info(f"[L9] Deployment APPROVED (trust: {aggregate_trust:.1f})")

        return self.build_response(
            message, "success",
            {
                "approved": True,
                "aggregate_trust": aggregate_trust,
                "commit_plan": commit_plan,
                "policy_violations": [],
            },
            trust_score=aggregate_trust
        )
