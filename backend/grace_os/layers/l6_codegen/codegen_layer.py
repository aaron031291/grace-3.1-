import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)

class CodegenLayer(GraceLayer):
    """
    Layer 6: Code Generation.
    Translates task descriptions into actual code using MCP tools.
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
        """
        Main entry point for L6.
        """
        if message.message_type == "EXECUTE_TASK":
            return await self._handle_execute(message)
        elif message.message_type == "FIX_CODE":
            return await self._handle_fix(message)
        
        return self.build_response(
            message, 
            "failure", 
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_execute(self, message: LayerMessage) -> LayerResponse:
        """
        Translates a task into code changes.
        """
        task_desc = message.payload.get("description", "")
        logger.info(f"[L6] Executing task: {task_desc[:50]}...")
        
        # 1. Generate code using LLM
        system_prompt = (
            "You are the L6 Codegen Layer of Grace OS. "
            "Generate the code or diff required to fulfill the task. "
            "Always include the file path and the EXACT content to be written."
        )
        
        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}",
            system_prompt=system_prompt
        )
        
        # 2. Use MCP tools to write/edit file
        # (Simplified: assumes GPT output some parsable structure)
        # In real L6, we'd have a parser to extract path and content.
        
        # Prototype Tool Call:
        # result = await self.call_tool("write_file", {"path": "example.py", "content": llm_response})
        
        return self.build_response(message, "success", {"message": "Code generated (mock tool call)."})

    async def _handle_fix(self, message: LayerMessage) -> LayerResponse:
        """
        Fixes code based on test failures from L7.
        """
        error_trace = message.payload.get("error_trace", "")
        logger.info(f"[L6] Fixing code based on error: {error_trace[:50]}...")
        
        # Logic to analyze error and regenerate code...
        return self.build_response(message, "success", {"message": "Code fix attempted."})
