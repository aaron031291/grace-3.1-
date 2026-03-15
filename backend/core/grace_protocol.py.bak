"""
GRACE Communication Protocol
================================
Defines the rules for how AI components communicate:

  - AI-to-AI:   Structured dicts only. No NLP. No prose.
  - AI-to-Human: NLP (natural language) responses.

This is ENFORCED, not suggested. Every cross-component call uses
structured GraceMessage / GraceResponse, never free-text strings.
NLP generation happens ONLY at the final human-facing boundary.

Protocol Rules:
  1. All internal messages are GraceMessage dicts (structured, typed)
  2. All internal responses are GraceResponse dicts (structured, typed)
  3. Code generation requests carry a contract_type for enforcement
  4. NLP is generated ONLY when output_mode == "human"
  5. AI-to-AI calls NEVER interpret NLP — they read structured fields
  6. The governance contract is attached to every code operation
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OutputMode(str, Enum):
    """Who receives the output — determines whether NLP is generated."""
    HUMAN = "human"
    AI = "ai"


class OperationType(str, Enum):
    """Type of operation for contract routing."""
    CODE_GENERATE = "code_generate"
    CODE_FIX = "code_fix"
    CODE_REVIEW = "code_review"
    COMPONENT_CREATE = "component_create"
    HEALING = "healing"
    ANALYZE = "analyze"
    QUERY = "query"
    DIAGNOSE = "diagnose"
    PLAN = "plan"


@dataclass
class GraceMessage:
    """
    Structured message for AI-to-AI communication.
    No NLP. Just typed fields.
    """
    operation: OperationType
    source: str
    target: str
    payload: Dict[str, Any] = field(default_factory=dict)
    output_mode: OutputMode = OutputMode.AI
    contract_type: Optional[str] = None
    execution_allowed: bool = False
    trace_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["operation"] = self.operation.value
        d["output_mode"] = self.output_mode.value
        return d


@dataclass
class GraceResponse:
    """
    Structured response for AI-to-AI communication.
    Contains structured data. NLP text generated only when output_mode == HUMAN.
    """
    success: bool
    source: str
    operation: str
    data: Dict[str, Any] = field(default_factory=dict)
    code: Optional[str] = None
    contract_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    human_text: Optional[str] = None
    trust_score: float = 0.5
    duration_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def route_message(msg: GraceMessage) -> GraceResponse:
    """
    Central message router. All AI-to-AI communication goes through here.
    Enforces structured protocol — no NLP between components.
    """
    start = time.time()

    try:
        if msg.operation in (
            OperationType.CODE_GENERATE,
            OperationType.CODE_FIX,
            OperationType.COMPONENT_CREATE,
            OperationType.HEALING,
        ):
            response = _handle_code_operation(msg)
        elif msg.operation == OperationType.ANALYZE:
            response = _handle_analysis(msg)
        elif msg.operation == OperationType.DIAGNOSE:
            response = _handle_diagnose(msg)
        elif msg.operation == OperationType.QUERY:
            response = _handle_query(msg)
        elif msg.operation == OperationType.PLAN:
            response = _handle_plan(msg)
        elif msg.operation == OperationType.CODE_REVIEW:
            response = _handle_code_review(msg)
        else:
            response = GraceResponse(
                success=False, source="protocol_router",
                operation=msg.operation.value,
                error=f"Unknown operation: {msg.operation.value}",
            )
    except Exception as e:
        response = GraceResponse(
            success=False, source="protocol_router",
            operation=msg.operation.value,
            error=str(e)[:300],
        )

    response.duration_ms = round((time.time() - start) * 1000, 1)

    if msg.output_mode == OutputMode.HUMAN and response.success:
        response.human_text = _generate_human_text(msg, response)

    return response


def _handle_code_operation(msg: GraceMessage) -> GraceResponse:
    """
    Handle code generation/fix/creation/healing with governance contract enforcement.
    The Qwen coding agent generates code, then the contract validates it.
    """
    from llm_orchestrator.factory import get_ai_mode_client
    from core.deterministic_coding_contracts import (
        execute_code_generation_contract,
        execute_code_fix_contract,
        execute_component_creation_contract,
        execute_healing_contract,
    )

    prompt = msg.payload.get("prompt", "")
    file_path = msg.payload.get("file_path", "")
    component = msg.payload.get("component", msg.source)
    project_folder = msg.payload.get("project_folder", "")

    if not msg.execution_allowed:
        return GraceResponse(
            success=True, source="coding_agent",
            operation=msg.operation.value,
            data={
                "mode": "read_only",
                "suggestion": prompt,
                "note": "Execution not allowed. Set execution_allowed=True to generate code.",
            },
        )

    client = get_ai_mode_client("code")

    system_prompt = (
        "You are the GRACE coding agent (Qwen). Output ONLY code. "
        "No explanations, no markdown fences, no commentary. "
        "Pure Python code with a module docstring."
    )

    project_context = ""
    if project_folder:
        try:
            from core.services.code_service import _get_project_context
            project_context = _get_project_context(project_folder)
        except Exception:
            pass

    if project_context:
        system_prompt += f"\n[Project context:\n{project_context[:2000]}]"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    raw_code = client.chat(messages=messages, temperature=0.2)

    if isinstance(raw_code, dict):
        raw_code = raw_code.get("message", {}).get("content", "") if "message" in raw_code else raw_code.get("response", str(raw_code))

    raw_code = _strip_markdown_fences(raw_code)

    if msg.operation == OperationType.CODE_GENERATE:
        contract = execute_code_generation_contract(component, raw_code, file_path)
    elif msg.operation == OperationType.CODE_FIX:
        problems = msg.payload.get("problems", [])
        contract = execute_code_fix_contract(component, file_path, raw_code, problems)
    elif msg.operation == OperationType.COMPONENT_CREATE:
        contract = execute_component_creation_contract(component, raw_code, file_path)
    elif msg.operation == OperationType.HEALING:
        method = msg.payload.get("healing_method", "unknown")
        contract = execute_healing_contract(component, raw_code, method)
    else:
        contract = execute_code_generation_contract(component, raw_code, file_path)

    return GraceResponse(
        success=contract.code_accepted,
        source="coding_agent",
        operation=msg.operation.value,
        code=raw_code if contract.code_accepted else None,
        contract_result=contract.to_dict(),
        trust_score=_extract_trust(contract),
        data={
            "verdict": contract.verdict.value,
            "violations": contract.violations,
            "file_path": file_path,
            "component": component,
        },
        error=f"Contract violated: {'; '.join(contract.violations)}" if not contract.code_accepted else None,
    )


def _handle_analysis(msg: GraceMessage) -> GraceResponse:
    """Handle analysis requests — structured output, no NLP between components."""
    from llm_orchestrator.factory import get_ai_mode_client
    client = get_ai_mode_client("reason")
    prompt = msg.payload.get("prompt", "")

    system = (
        "Analyze the following and respond with a JSON object containing: "
        "findings (list of strings), severity (low/medium/high/critical), "
        "recommendations (list of strings), confidence (0-1 float)."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    response = client.chat(messages=messages, temperature=0.2)
    text = response if isinstance(response, str) else response.get("message", {}).get("content", str(response))

    import json
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = {"raw_analysis": text, "format": "unstructured"}

    return GraceResponse(
        success=True, source="analysis_agent",
        operation=msg.operation.value, data=data,
    )


def _handle_diagnose(msg: GraceMessage) -> GraceResponse:
    """Diagnostic — structured dict output."""
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        engine = get_diagnostic_engine()
        status = engine.get_status()
        return GraceResponse(
            success=True, source="diagnostic_engine",
            operation=msg.operation.value, data=status,
        )
    except Exception as e:
        return GraceResponse(
            success=False, source="diagnostic_engine",
            operation=msg.operation.value, error=str(e),
        )


def _handle_query(msg: GraceMessage) -> GraceResponse:
    """Query — use RAG retrieval, structured output."""
    try:
        from retrieval.retriever import DocumentRetriever
        from embedding.embedder import get_embedding_model
        retriever = DocumentRetriever(embedding_model=get_embedding_model())
        query = msg.payload.get("query", msg.payload.get("prompt", ""))
        chunks = retriever.retrieve(query=query, limit=5)
        return GraceResponse(
            success=True, source="retrieval",
            operation=msg.operation.value,
            data={"chunks": chunks, "count": len(chunks)},
        )
    except Exception as e:
        return GraceResponse(
            success=False, source="retrieval",
            operation=msg.operation.value, error=str(e),
        )


def _handle_plan(msg: GraceMessage) -> GraceResponse:
    """Planning — structured task breakdown, no NLP."""
    from llm_orchestrator.factory import get_ai_mode_client
    client = get_ai_mode_client("reason")
    prompt = msg.payload.get("prompt", "")

    system = (
        "Break the following task into steps. Respond ONLY with a JSON object: "
        "{\"steps\": [{\"id\": 1, \"description\": \"...\", \"dependencies\": [], \"estimated_minutes\": N}], "
        "\"total_steps\": N, \"estimated_total_minutes\": N}"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    response = client.chat(messages=messages, temperature=0.2)
    text = response if isinstance(response, str) else response.get("message", {}).get("content", str(response))

    import json
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = {"raw_plan": text, "format": "unstructured"}

    return GraceResponse(
        success=True, source="planner",
        operation=msg.operation.value, data=data,
    )


def _handle_code_review(msg: GraceMessage) -> GraceResponse:
    """Code review — deterministic checks + LLM analysis, structured output."""
    code = msg.payload.get("code", "")
    component = msg.payload.get("component", "unknown")

    from core.deterministic_coding_contracts import (
        check_syntax, check_imports_resolve,
        check_no_dangerous_patterns, check_has_docstring,
    )

    steps = [
        check_syntax(code),
        check_imports_resolve(code),
        check_no_dangerous_patterns(code),
        check_has_docstring(code),
    ]

    return GraceResponse(
        success=all(s.verdict.value != "fail" for s in steps),
        source="code_reviewer",
        operation=msg.operation.value,
        data={
            "component": component,
            "checks": [asdict(s) for s in steps],
            "passed": sum(1 for s in steps if s.verdict.value == "pass"),
            "failed": sum(1 for s in steps if s.verdict.value == "fail"),
            "warnings": sum(1 for s in steps if s.verdict.value == "warn"),
        },
    )


def _generate_human_text(msg: GraceMessage, response: GraceResponse) -> str:
    """
    Generate NLP text ONLY for human-facing output.
    This is the ONLY place NLP is created from structured data.
    """
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("fast")

        import json
        data_str = json.dumps(response.data, indent=2, default=str)[:2000]

        system = (
            "Convert the following structured AI result into a clear, "
            "concise human-readable response. Be direct and informative."
        )
        prompt = (
            f"Operation: {response.operation}\n"
            f"Success: {response.success}\n"
            f"Data: {data_str}\n"
        )
        if response.code:
            prompt += f"\nGenerated code (first 500 chars):\n{response.code[:500]}"
        if response.error:
            prompt += f"\nError: {response.error}"

        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        text = client.chat(messages=messages, temperature=0.3)
        if isinstance(text, dict):
            text = text.get("message", {}).get("content", "") if "message" in text else text.get("response", str(text))
        return text
    except Exception:
        if response.error:
            return f"Operation failed: {response.error}"
        return f"Operation {response.operation} completed successfully."


def _strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences from LLM output."""
    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code


def _extract_trust(contract) -> float:
    """Extract trust score from contract result."""
    for step in contract.steps:
        if step.name == "trust_gate" and step.details:
            return step.details.get("trust_score", 0.5)
    return 0.5
