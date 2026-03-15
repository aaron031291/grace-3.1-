import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class VerificationLayer(GraceLayer):
    """
    Layer 8: Verification & Fact-Checking.
    Post-generation QA — validates requirements, security, consistency, and correctness.
    """

    @property
    def layer_name(self) -> str:
        return "L8_Verification"

    @property
    def capabilities(self) -> List[str]:
        return ["requirement_verification", "fact_checking", "security_scanning", "consistency_checking"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["VERIFY_OUTPUT", "FACT_CHECK"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "VERIFY_OUTPUT":
            return await self._handle_verify(message)
        elif message.message_type == "FACT_CHECK":
            return await self._handle_fact_check(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_verify(self, message: LayerMessage) -> LayerResponse:
        """Post-flight verification: requirements met? Security OK? Consistent?"""
        task = message.payload.get("task", {})
        codegen_result = message.payload.get("codegen_result", {})
        test_result = message.payload.get("test_result", {})
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)

        logger.info(f"[L8] Verifying output for: {task_desc[:60]}...")

        system_prompt = (
            "You are the L8 Verification Layer of Grace OS. "
            "Verify the generated output against the original requirements. Check: "
            "1) Are ALL requirements from the task addressed? "
            "2) Any security issues (injection, hardcoded secrets, unsafe deps)? "
            "3) Is the code consistent with existing project patterns? "
            "4) Is it readable and maintainable? "
            "Respond ONLY with JSON: "
            '{"verified": true/false, "requirements_met": ["..."], "requirements_missed": ["..."], '
            '"security_flags": ["..."], "consistency_issues": ["..."], '
            '"readability_score": 0-100, "overall_trust": 0-100}'
        )

        llm_response = await self.call_llm(
            prompt=(
                f"Original Task: {task_desc}\n"
                f"Codegen Result: {json.dumps(codegen_result)}\n"
                f"Test Result: {json.dumps(test_result)}"
            ),
            system_prompt=system_prompt
        )

        parse_failed = False
        try:
            verification = json.loads(llm_response) if llm_response else {}
            if not llm_response:
                parse_failed = True
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[L8] Parse failed, failing closed: {e}")
            verification = {}
            parse_failed = True

        verified = verification.get("verified", False)
        security_flags = verification.get("security_flags", [])
        overall_trust = verification.get("overall_trust", 25 if parse_failed else 75)

        if parse_failed:
            verified = False

        # If there are security flags, drop trust significantly
        if security_flags:
            overall_trust = min(overall_trust, 50)
            verified = False

        # If tests failed, mark as not verified
        if test_result.get("status") == "failure":
            verified = False
            overall_trust = min(overall_trust, 30)

        result_payload = {
            "verified": verified,
            "requirements_met": verification.get("requirements_met", []),
            "requirements_missed": verification.get("requirements_missed", []),
            "security_flags": security_flags,
            "consistency_issues": verification.get("consistency_issues", []),
            "readability_score": verification.get("readability_score", 75),
            "overall_trust": overall_trust,
            "task": task,
        }

        return self.build_response(
            message,
            "success" if verified else "partial",
            result_payload,
            trust_score=float(overall_trust)
        )

    async def _handle_fact_check(self, message: LayerMessage) -> LayerResponse:
        """Verify technical claims — API usage, library versions, syntax."""
        claim = message.payload.get("claim", "")
        context = message.payload.get("context", "")

        logger.info(f"[L8] Fact-checking: {claim[:60]}...")

        system_prompt = (
            "You are the L8 Fact-Checker. Verify the technical claim is accurate. "
            "Check API signatures, library versions, and syntax correctness. "
            'Respond with JSON: {"accurate": true/false, "corrections": ["..."], "confidence": 0-100}'
        )

        llm_response = await self.call_llm(
            prompt=f"Claim: {claim}\nContext: {context}",
            system_prompt=system_prompt
        )

        try:
            result = json.loads(llm_response) if llm_response else {}
        except Exception as e:
            logger.warning(f"[L8] Fact-check parse failed, failing closed: {e}")
            result = {"accurate": False, "corrections": ["Verification response unparseable"], "confidence": 0}

        return self.build_response(
            message, "success", result,
            trust_score=float(result.get("confidence", 60))
        )
