import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class CodegenLayer(GraceLayer):
    """
    Layer 6: Code Generation.
    Translates task descriptions into actual code using LLM + patch consensus.
    """

    @property
    def layer_name(self) -> str:
        return "L6_Codegen"

    @property
    def capabilities(self) -> List[str]:
        return ["code_generation", "file_editing", "style_enforcement"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["EXECUTE_TASK", "FIX_CODE"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "EXECUTE_TASK":
            return await self._handle_execute(message)
        elif message.message_type == "FIX_CODE":
            return await self._handle_fix(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_execute(self, message: LayerMessage) -> LayerResponse:
        """Generate code via LLM, produce structured patch instructions."""
        task_desc = message.payload.get("description", "")
        project_folder = message.payload.get("project_folder", "")
        logger.info(f"[L6] Executing task: {task_desc[:80]}...")

        system_prompt = (
            "You are the L6 Codegen Layer. Generate code to fulfill the task.\n"
            "Output ONLY a JSON object with:\n"
            '{"file": "path/to/file.py", "content": "full file content", "reason": "why"}\n'
            "For multiple files, output a JSON array of such objects.\n"
            "Be precise with file paths relative to the project root."
        )

        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}\nProject: {project_folder}",
            system_prompt=system_prompt,
        )

        code_output = {"raw_response": llm_response[:3000]}

        try:
            text = llm_response.strip()
            if "```" in text:
                text = text.split("```")[1] if len(text.split("```")) > 1 else text
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip().rstrip("`")

            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parsed = [parsed]

            code_output["files"] = []
            for item in parsed:
                file_path = item.get("file", "")
                content = item.get("content", "")
                reason = item.get("reason", "")

                if file_path and content:
                    code_output["files"].append({
                        "file": file_path,
                        "content_length": len(content),
                        "reason": reason,
                    })

                    try:
                        from cognitive.patch_consensus import (
                            PatchInstruction, create_patch_proposal, run_consensus_vote,
                        )
                        instruction = PatchInstruction(
                            file=file_path, diff=content,
                            reason=reason, action="modify",
                        )
                        proposal = create_patch_proposal([instruction], ["L6_Codegen"])
                        proposal = run_consensus_vote(proposal)
                        code_output["proposal_id"] = proposal.proposal_id
                        code_output["proposal_status"] = proposal.status
                    except Exception as e:
                        code_output["consensus_error"] = str(e)[:200]

            code_output["files_generated"] = len(code_output.get("files", []))
            return self.build_response(message, "success", code_output)

        except (json.JSONDecodeError, KeyError) as e:
            code_output["parse_error"] = str(e)
            code_output["files_generated"] = 0
            return self.build_response(message, "partial", code_output, trust_score=50.0)

    async def _handle_fix(self, message: LayerMessage) -> LayerResponse:
        """Fix code based on test failures from L7."""
        error_trace = message.payload.get("error_trace", "")
        original_task = message.payload.get("original_task", "")
        failed_file = message.payload.get("failed_file", "")
        logger.info(f"[L6] Fixing code for: {error_trace[:80]}...")

        system_prompt = (
            "You are the L6 Codegen Layer fixing a test failure.\n"
            "Analyze the error trace and produce a JSON fix:\n"
            '{"file": "path/to/file.py", "content": "corrected content", "reason": "what was wrong"}\n'
        )

        prompt = f"Error:\n{error_trace}\n\nOriginal task: {original_task}"
        if failed_file:
            prompt += f"\nFailing file: {failed_file}"

        llm_response = await self.call_llm(prompt=prompt, system_prompt=system_prompt)

        fix_output = {"raw_response": llm_response[:2000], "error_analyzed": error_trace[:200]}

        try:
            text = llm_response.strip()
            if "```" in text:
                text = text.split("```")[1] if len(text.split("```")) > 1 else text
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip().rstrip("`")

            parsed = json.loads(text)
            fix_output["fix_file"] = parsed.get("file", "")
            fix_output["fix_reason"] = parsed.get("reason", "")
            fix_output["fix_applied"] = True

            return self.build_response(message, "success", fix_output)

        except Exception as e:
            fix_output["parse_error"] = str(e)
            return self.build_response(message, "partial", fix_output, trust_score=40.0)
