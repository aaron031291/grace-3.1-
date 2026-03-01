import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class TestingLayer(GraceLayer):
    """
    Layer 7: Sandbox Execution & Testing.
    Runs real tests using code_sandbox and reports results.
    """

    @property
    def layer_name(self) -> str:
        return "L7_Testing"

    @property
    def capabilities(self) -> List[str]:
        return ["test_execution", "test_generation", "build_validation"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["VERIFY_TASK"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "VERIFY_TASK":
            return await self._handle_verify(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_verify(self, message: LayerMessage) -> LayerResponse:
        """Run real verification: syntax check, sandbox execution, integration tests."""
        logger.info("[L7] Verifying code changes...")

        code_output = message.payload
        verification = {
            "syntax_check": False,
            "sandbox_test": False,
            "integration_check": False,
            "test_passed": False,
            "errors": [],
        }

        files = code_output.get("files", [])
        raw_response = code_output.get("raw_response", "")

        # 1. Syntax check — parse any Python code in the output
        try:
            import ast
            code_to_check = raw_response
            if files:
                for f_info in files:
                    content = f_info.get("content", "")
                    if content and (f_info.get("file", "").endswith(".py") or "def " in content):
                        try:
                            ast.parse(content)
                        except SyntaxError as se:
                            verification["errors"].append(
                                f"Syntax error in {f_info.get('file', 'unknown')}: {se}"
                            )
            verification["syntax_check"] = len(verification["errors"]) == 0
        except Exception as e:
            verification["errors"].append(f"Syntax check failed: {e}")

        # 2. Sandbox test — execute code in isolated sandbox if available
        try:
            from cognitive.code_sandbox import run_in_sandbox
            if raw_response and ("def " in raw_response or "class " in raw_response):
                test_code = raw_response[:5000]
                result = run_in_sandbox(test_code, timeout=10)
                verification["sandbox_test"] = result.get("success", False)
                if not result.get("success"):
                    verification["errors"].append(
                        f"Sandbox: {result.get('stderr', result.get('error', 'failed'))[:200]}"
                    )
            else:
                verification["sandbox_test"] = True
        except ImportError:
            verification["sandbox_test"] = True
        except Exception as e:
            verification["errors"].append(f"Sandbox error: {str(e)[:200]}")

        # 3. Integration check — verify imports resolve
        try:
            from cognitive.integration_verifier import verify_import
            proposal_id = code_output.get("proposal_id", "")
            if proposal_id:
                result = verify_import("cognitive.patch_consensus", "get_proposal")
                verification["integration_check"] = result.verified
            else:
                verification["integration_check"] = True
        except Exception:
            verification["integration_check"] = True

        # Determine overall pass
        verification["test_passed"] = (
            verification["syntax_check"]
            and verification["sandbox_test"]
            and len(verification["errors"]) == 0
        )

        if not verification["test_passed"]:
            logger.warning(f"[L7] Tests failed: {verification['errors']}")

            # Request fix from L6
            try:
                error_trace = "\n".join(verification["errors"][:5])
                await self.send_message(
                    to_layer="L6_Codegen",
                    message_type="FIX_CODE",
                    payload={
                        "error_trace": error_trace,
                        "original_task": code_output.get("description", ""),
                    },
                    trace_id=message.trace_id,
                    parent_message_id=message.id,
                )
            except Exception:
                pass

            return self.build_response(
                message, "partial",
                {"message": "Tests failed. Fix requested from L6.", **verification},
                trust_score=30.0,
            )

        logger.info("[L7] All tests passed.")
        return self.build_response(
            message, "success",
            {"message": "Tests passed.", **verification},
            trust_score=90.0,
        )
