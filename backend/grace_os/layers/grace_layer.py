"""
Grace OS — Grace Layer (Integration Base)

Extends BaseLayer to provide standardized access to Shared Services:
- LLM Orchestrator (Thinking)
- MCP Client (Acting)
"""

import logging
from typing import Any, Dict, List, Optional

from .base_layer import BaseLayer
from ..kernel.message_bus import MessageBus
from ..kernel.layer_registry import LayerRegistry
from ..kernel.message_protocol import LayerMessage, LayerResponse

# These will be imported once we have the singleton/factory pattern established
# For now, we assume they are passed or available via well-known getters
from llm_orchestrator.llm_orchestrator import LLMOrchestrator, TaskType
from grace_mcp.client import MCPClient

logger = logging.getLogger(__name__)

class GraceLayer(BaseLayer):
    """
    Subclass this for any layer that needs to 'think' (LLM) or 'act' (MCP).
    """

    def __init__(
        self, 
        bus: MessageBus, 
        registry: LayerRegistry,
        llm: LLMOrchestrator,
        mcp: MCPClient
    ):
        super().__init__(bus, registry)
        self.llm = llm
        self.mcp = mcp

    async def call_llm(
        self, 
        prompt: str, 
        task_type: TaskType = TaskType.GENERAL,
        system_prompt: Optional[str] = None
    ) -> str:
        """Standardized LLM call for all Grace layers."""
        logger.info(f"[{self.layer_name}] Prompting LLM...")
        result = self.llm.execute_task(
            prompt=prompt,
            task_type=task_type,
            system_prompt=system_prompt
        )
        if not result.success:
            logger.error(f"[{self.layer_name}] LLM Task Failed: {result.audit_trail[-1].get('error')}")
            return ""
        return result.content

    async def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Standardized MCP tool call for all Grace layers."""
        logger.info(f"[{self.layer_name}] Calling tool: {tool_name}")
        return await self.mcp.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            calling_layer=self.layer_name
        )

    def build_response(
        self, 
        message: LayerMessage, 
        status: str, 
        payload: Dict[str, Any], 
        trust_score: float = 80.0
    ) -> LayerResponse:
        """Helper to build a standardized response."""
        return LayerResponse(
            message_id=message.id,
            from_layer=self.layer_name,
            status=status,
            payload=payload,
            trust_score=trust_score
        )
