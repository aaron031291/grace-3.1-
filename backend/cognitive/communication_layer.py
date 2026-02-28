"""
NLP Communication Layer — Adaptive Communication Routing

Grace communicates differently depending on who she's talking to:
  - Human → Natural Language (NLP), conversational, clear
  - System/API → JSON, structured, machine-readable
  - Component → Internal protocol, minimal overhead
  - LLM → Prompt-optimized, context-rich

The system autonomously chooses the best communication format
for each interaction, optimizing for:
  - Least resistance (fastest path to understanding)
  - No loss of intelligence or formulation quality
  - Context-appropriate formatting

Grace can also test different communication strategies in the
sandbox environment and adopt the most effective approach.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class CommunicationTarget:
    HUMAN = "human"
    SYSTEM = "system"
    COMPONENT = "component"
    LLM = "llm"
    API = "api"


def format_for_target(
    data: Any,
    target: str = CommunicationTarget.HUMAN,
    context: str = "",
    detail_level: str = "normal",
) -> Union[str, Dict[str, Any]]:
    """
    Format data for the appropriate target.
    Grace decides the best format automatically.
    """
    if target == CommunicationTarget.HUMAN:
        return _format_human(data, context, detail_level)
    elif target == CommunicationTarget.SYSTEM:
        return _format_system(data)
    elif target == CommunicationTarget.COMPONENT:
        return _format_component(data)
    elif target == CommunicationTarget.LLM:
        return _format_llm(data, context)
    elif target == CommunicationTarget.API:
        return _format_api(data)
    return str(data)


def _format_human(data: Any, context: str = "", detail_level: str = "normal") -> str:
    """Format for human consumption — natural language, clear, conversational."""
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        lines = []

        # Status/health type data
        if "health_score" in data or "status" in data:
            score = data.get("health_score", data.get("trust_score", ""))
            status = data.get("status", "")
            if score:
                lines.append(f"System health is at {score}{'%' if isinstance(score, (int, float)) else ''}.")
            if status:
                lines.append(f"Current status: {status}.")

        # Improvements/problems
        if "improvements" in data:
            if data["improvements"]:
                lines.append("\nWhat's going well:")
                for item in data["improvements"]:
                    lines.append(f"  + {item}")

        if "problems" in data:
            if data["problems"]:
                lines.append("\nAreas needing attention:")
                for item in data["problems"]:
                    lines.append(f"  - {item}")

        # Metrics
        if "metrics" in data and isinstance(data["metrics"], dict):
            lines.append("\nKey numbers:")
            for key, val in data["metrics"].items():
                nice_key = key.replace("_", " ").title()
                lines.append(f"  {nice_key}: {val}")

        # Steps/plan type data
        if "steps" in data and isinstance(data["steps"], list):
            lines.append("\nPlan:")
            for i, step in enumerate(data["steps"], 1):
                desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)
                lines.append(f"  {i}. {desc}")

        # Error handling
        if "error" in data:
            lines.append(f"\nThere was an issue: {data['error']}")

        if lines:
            return "\n".join(lines)

        # Fallback: readable key-value
        return "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in data.items()
                         if not k.startswith("_") and v is not None)

    if isinstance(data, list):
        if not data:
            return "No items found."
        if all(isinstance(item, str) for item in data):
            return "\n".join(f"  - {item}" for item in data)
        return "\n".join(f"  {i+1}. {str(item)[:200]}" for i, item in enumerate(data))

    return str(data)


def _format_system(data: Any) -> Dict[str, Any]:
    """Format for system consumption — JSON, structured."""
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return {"message": data}
    if isinstance(data, list):
        return {"items": data, "count": len(data)}
    return {"value": data}


def _format_component(data: Any) -> Dict[str, Any]:
    """Format for component-to-component — minimal overhead JSON."""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if v is not None}
    return {"data": data}


def _format_llm(data: Any, context: str = "") -> str:
    """Format for LLM consumption — prompt-optimized, context-rich."""
    parts = []
    if context:
        parts.append(f"Context: {context}")

    if isinstance(data, dict):
        parts.append("Data:")
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                parts.append(f"  {k}: {json.dumps(v, default=str)[:500]}")
            else:
                parts.append(f"  {k}: {v}")
    elif isinstance(data, list):
        parts.append("Items:")
        for item in data[:20]:
            parts.append(f"  - {str(item)[:200]}")
    else:
        parts.append(str(data))

    return "\n".join(parts)


def _format_api(data: Any) -> Dict[str, Any]:
    """Format for API response — REST conventions."""
    if isinstance(data, dict):
        return {"success": True, "data": data}
    if isinstance(data, list):
        return {"success": True, "data": data, "count": len(data)}
    if isinstance(data, str):
        return {"success": True, "message": data}
    return {"success": True, "data": data}


def detect_best_target(recipient: str) -> str:
    """Auto-detect the best communication target type."""
    r = recipient.lower()
    if any(w in r for w in ["user", "human", "aaron", "person", "client"]):
        return CommunicationTarget.HUMAN
    if any(w in r for w in ["api", "endpoint", "rest", "http"]):
        return CommunicationTarget.API
    if any(w in r for w in ["llm", "kimi", "opus", "model", "prompt"]):
        return CommunicationTarget.LLM
    if any(w in r for w in ["pipeline", "engine", "module", "cognitive"]):
        return CommunicationTarget.COMPONENT
    return CommunicationTarget.SYSTEM


def smart_format(data: Any, recipient: str = "human", context: str = "") -> Any:
    """
    Smart formatting — auto-detects target and formats appropriately.
    The path of least resistance for communication.
    """
    target = detect_best_target(recipient)
    return format_for_target(data, target, context)
