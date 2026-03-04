import json
import logging
import re
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

MAX_FIX_RETRIES = 3


class CodegenLayer(GraceLayer):
    """
    Layer 6: Code Generation.
    Translates the chosen solution into actual code changes via MCP tools.
    Primary consumer of file_write and edit_block MCP tools.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fix_attempts: Dict[str, int] = {}

    @property
    def layer_name(self) -> str:
        return "L6_Codegen"

    @property
    def capabilities(self) -> List[str]:
        return ["code_generation", "file_editing", "style_enforcement", "multi_file_coordination"]

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
        """Translate a task into code changes using MCP file tools."""
        task = message.payload.get("task", message.payload)
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)
        selected_proposal = message.payload.get("selected_proposal", {})
        approach = selected_proposal.get("approach", "") if isinstance(selected_proposal, dict) else str(selected_proposal)

        logger.info(f"[L6] Generating code for: {task_desc[:60]}...")

        # 1. Read existing relevant files for context
        context_files = task.get("files", []) if isinstance(task, dict) else []
        file_contents = {}
        for fpath in context_files[:5]:  # Limit to 5 files for context
            try:
                read_result = await self.call_tool("read_file", {"path": fpath})
                if read_result.get("success"):
                    file_contents[fpath] = read_result.get("content", "")
            except Exception as e:
                logger.warning(f"[L6] Could not read {fpath}: {e}")

        # 2. Generate code via LLM
        system_prompt = (
            "You are the L6 Codegen Layer of Grace OS. "
            "Generate the code changes required to fulfill the task. "
            "Respond ONLY with a JSON array of file operations. Each element must have:\n"
            '- "operation": "write" (create/overwrite) or "edit" (surgical edit)\n'
            '- "path": file path (relative to project root)\n'
            '- For "write": include "content" with the full file content\n'
            '- For "edit": include "old_string" and "new_string" for search-and-replace\n'
            "Example:\n"
            '[{"operation":"write","path":"src/utils.py","content":"def add(a,b):\\n    return a+b\\n"},'
            '{"operation":"edit","path":"src/main.py","old_string":"import os","new_string":"import os\\nimport utils"}]'
        )

        context_block = ""
        if file_contents:
            context_block = "\n\nExisting file contents:\n"
            for fp, fc in file_contents.items():
                truncated = fc[:2000] if len(fc) > 2000 else fc
                context_block += f"\n--- {fp} ---\n{truncated}\n"

        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}\nApproach: {approach}{context_block}",
            system_prompt=system_prompt
        )

        # 3. Parse file operations from LLM response
        operations = self._parse_operations(llm_response)

        if not operations:
            logger.warning("[L6] No valid file operations parsed from LLM response.")
            return self.build_response(
                message, "partial",
                {"error": "Could not parse file operations from LLM output", "raw_response": llm_response[:500]},
                trust_score=30.0
            )

        # 4. Execute file operations via MCP tools
        results = await self._execute_operations(operations)

        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        if failures and not successes:
            return self.build_response(
                message, "failure",
                {"error": "All file operations failed", "results": results},
                trust_score=20.0
            )

        trust = 90.0 if not failures else 65.0

        return self.build_response(
            message, "success",
            {
                "message": f"Generated {len(successes)} file(s), {len(failures)} failed.",
                "files_changed": [r["path"] for r in successes],
                "results": results,
                "task": task,
            },
            trust_score=trust
        )

    async def _handle_fix(self, message: LayerMessage) -> LayerResponse:
        """Fix code based on test failures from L7 (self-healing loop)."""
        error_trace = message.payload.get("error_trace", "")
        original_task = message.payload.get("original_task", "")
        failed_files = message.payload.get("failed_files", [])
        trace_id = message.trace_id

        # Track fix attempts to prevent infinite loops
        fix_key = f"{trace_id}:{original_task[:50]}"
        self._fix_attempts[fix_key] = self._fix_attempts.get(fix_key, 0) + 1

        if self._fix_attempts[fix_key] > MAX_FIX_RETRIES:
            logger.warning(f"[L6] Max fix retries ({MAX_FIX_RETRIES}) exceeded. Giving up.")
            return self.build_response(
                message, "failure",
                {"error": f"Max fix retries exceeded after {MAX_FIX_RETRIES} attempts", "error_trace": error_trace},
                trust_score=10.0
            )

        logger.info(f"[L6] Fix attempt {self._fix_attempts[fix_key]}/{MAX_FIX_RETRIES} for: {error_trace[:60]}...")

        # 1. Read the failing files for context
        file_contents = {}
        for fpath in failed_files[:3]:
            try:
                read_result = await self.call_tool("read_file", {"path": fpath})
                if read_result.get("success"):
                    file_contents[fpath] = read_result.get("content", "")
            except Exception as e:
                logger.warning(f"[L6] Could not read {fpath}: {e}")

        # 2. Ask LLM to generate fix
        system_prompt = (
            "You are the L6 Codegen Layer performing a CODE FIX. "
            "Analyze the error trace and generate ONLY the necessary edits. "
            "Respond with a JSON array of edit operations:\n"
            '[{"operation":"edit","path":"file.py","old_string":"broken code","new_string":"fixed code"}]'
        )

        context_block = ""
        if file_contents:
            context_block = "\n\nCurrent file contents:\n"
            for fp, fc in file_contents.items():
                truncated = fc[:2000] if len(fc) > 2000 else fc
                context_block += f"\n--- {fp} ---\n{truncated}\n"

        llm_response = await self.call_llm(
            prompt=f"Original task: {original_task}\nError trace:\n{error_trace}{context_block}",
            system_prompt=system_prompt
        )

        # 3. Parse and execute fix operations
        operations = self._parse_operations(llm_response)

        if not operations:
            return self.build_response(
                message, "failure",
                {"error": "Could not parse fix operations", "attempt": self._fix_attempts[fix_key]},
                trust_score=25.0
            )

        results = await self._execute_operations(operations)
        successes = [r for r in results if r["success"]]

        trust = 70.0 if successes else 30.0

        return self.build_response(
            message, "success" if successes else "failure",
            {
                "message": f"Fix attempt {self._fix_attempts[fix_key]}: {len(successes)} edits applied.",
                "files_changed": [r["path"] for r in successes],
                "results": results,
                "attempt": self._fix_attempts[fix_key],
            },
            trust_score=trust
        )

    def _parse_operations(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse file operations from LLM response."""
        if not llm_response:
            return []

        # Try direct JSON parse
        try:
            ops = json.loads(llm_response)
            if isinstance(ops, list):
                return [op for op in ops if isinstance(op, dict) and "operation" in op]
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', llm_response)
        if json_match:
            try:
                ops = json.loads(json_match.group(1))
                if isinstance(ops, list):
                    return [op for op in ops if isinstance(op, dict) and "operation" in op]
            except json.JSONDecodeError:
                pass

        # Try finding a JSON array anywhere in the response
        array_match = re.search(r'\[[\s\S]*\]', llm_response)
        if array_match:
            try:
                ops = json.loads(array_match.group(0))
                if isinstance(ops, list):
                    return [op for op in ops if isinstance(op, dict) and "operation" in op]
            except json.JSONDecodeError:
                pass

        logger.warning("[L6] Could not parse any file operations from LLM response.")
        return []

    async def _execute_operations(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute file operations via MCP tools. Returns results list."""
        results = []

        for op in operations:
            op_type = op.get("operation", "")
            path = op.get("path", "")

            if not path:
                results.append({"path": "unknown", "operation": op_type, "success": False, "error": "No path specified"})
                continue

            try:
                if op_type == "write":
                    content = op.get("content", "")
                    tool_result = await self.call_tool("write_file", {
                        "path": path,
                        "content": content
                    })
                    results.append({
                        "path": path,
                        "operation": "write",
                        "success": tool_result.get("success", False),
                        "error": tool_result.get("error")
                    })

                elif op_type == "edit":
                    old_string = op.get("old_string", "")
                    new_string = op.get("new_string", "")
                    if not old_string:
                        results.append({"path": path, "operation": "edit", "success": False, "error": "No old_string for edit"})
                        continue

                    tool_result = await self.call_tool("edit_block", {
                        "path": path,
                        "old_string": old_string,
                        "new_string": new_string
                    })
                    results.append({
                        "path": path,
                        "operation": "edit",
                        "success": tool_result.get("success", False),
                        "error": tool_result.get("error")
                    })

                else:
                    results.append({"path": path, "operation": op_type, "success": False, "error": f"Unknown operation: {op_type}"})

            except Exception as e:
                logger.error(f"[L6] Tool call failed for {path}: {e}")
                results.append({"path": path, "operation": op_type, "success": False, "error": str(e)})

        return results
