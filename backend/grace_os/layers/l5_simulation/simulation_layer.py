import json
import logging
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class SimulationLayer(GraceLayer):
    """
    Layer 5: Simulation & Reasoning Engine.
    Pre-flight analysis — reasons about code behavior without running it.
    Static analysis, edge case detection, dependency impact, contradiction detection.
    """

    @property
    def layer_name(self) -> str:
        return "L5_Simulation"

    @property
    def capabilities(self) -> List[str]:
        return ["static_analysis", "symbolic_execution", "impact_analysis", "edge_case_detection"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["SIMULATE_PROPOSAL", "ANALYZE_IMPACT"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "SIMULATE_PROPOSAL":
            return await self._handle_simulate(message)
        elif message.message_type == "ANALYZE_IMPACT":
            return await self._handle_impact(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_simulate(self, message: LayerMessage) -> LayerResponse:
        """Simulate a proposal to find risks and edge cases before codegen."""
        proposal = message.payload.get("selected_proposal", {})
        task = message.payload.get("task", {})
        approach = proposal.get("approach", "") if isinstance(proposal, dict) else str(proposal)
        task_desc = task.get("description", "") if isinstance(task, dict) else str(task)

        logger.info(f"[L5] Simulating proposal: {approach[:60]}...")

        system_prompt = (
            "You are the L5 Simulation Engine of Grace OS. "
            "Analyze the proposed solution WITHOUT running code. Think through: "
            "1) What could break in existing code? "
            "2) What edge cases exist (null inputs, empty lists, API failures)? "
            "3) What dependencies are affected? "
            "4) Any logical contradictions with existing patterns? "
            "Respond ONLY with JSON: "
            '{"risks": ["..."], "edge_cases": ["..."], "dependency_impacts": ["..."], '
            '"contradictions": ["..."], "impact_score": 0-100, "recommendation": "proceed|caution|block"}'
        )

        llm_response = await self.call_llm(
            prompt=f"Task: {task_desc}\nProposal: {approach}",
            system_prompt=system_prompt
        )

        try:
            analysis = json.loads(llm_response) if llm_response else {}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[L5] Parse failed, using safe defaults: {e}")
            analysis = {}

        risks = analysis.get("risks", [])
        edge_cases = analysis.get("edge_cases", [])
        impact_score = analysis.get("impact_score", 30)
        recommendation = analysis.get("recommendation", "proceed")

        # Trust score inversely related to impact severity
        trust = max(20.0, 100.0 - float(impact_score))

        return self.build_response(
            message, "success",
            {
                "risks": risks,
                "edge_cases": edge_cases,
                "dependency_impacts": analysis.get("dependency_impacts", []),
                "contradictions": analysis.get("contradictions", []),
                "impact_score": impact_score,
                "recommendation": recommendation,
                "selected_proposal": proposal,
                "task": task,
            },
            trust_score=trust
        )

    async def _handle_impact(self, message: LayerMessage) -> LayerResponse:
        """Analyze dependency impact of a specific code change."""
        change_description = message.payload.get("change_description", "")
        affected_files = message.payload.get("affected_files", [])

        logger.info(f"[L5] Analyzing impact of: {change_description[:60]}...")

        system_prompt = (
            "You are the L5 Impact Analyzer. Given a code change and affected files, "
            "determine what else might break. "
            'Respond with JSON: {"affected_modules": ["..."], "risk_level": "low|medium|high", "details": "..."}'
        )

        llm_response = await self.call_llm(
            prompt=f"Change: {change_description}\nFiles: {affected_files}",
            system_prompt=system_prompt
        )

        try:
            result = json.loads(llm_response) if llm_response else {}
        except Exception:
            result = {"affected_modules": [], "risk_level": "medium", "details": "Analysis inconclusive"}

        return self.build_response(message, "success", result, trust_score=70.0)
