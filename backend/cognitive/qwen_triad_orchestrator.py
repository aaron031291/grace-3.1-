"""
Qwen Triad Orchestrator — Async parallel processing across 3 Qwen models
with full subsystem context gathering.

Models:
  qwen3.5:27b  (code)     — code generation, structured output
  qwen3.5:27b  (reason)   — deep reasoning, analysis, 262K context
  qwen3.5:9b   (fast)     — quick triage, classification, summaries

Flow:
  1. GATHER  — pull context from ALL subsystems in parallel
  2. TRIAGE  — fast model classifies intent and routes
  3. TRIAD   — all 3 models process in parallel with role-specific prompts
  4. SYNTHESIZE — reasoning model merges outputs with trust weighting
  5. GOVERN  — governance gate (read-only unless user specifies execution)
  6. TRACK   — Genesis key + episodic memory + mirror update

Subsystem context sources:
  - Memory (Magma, episodic, procedural, flash cache)
  - Genesis Keys (provenance, lineage)
  - Diagnostics (system health, recent issues)
  - Self-healing (healing history, current status)
  - Self-learning (learned patterns, knowledge gaps)
  - Self-governance (autonomy tier, rules, persona)
  - Self-mirror (behavioral patterns, self-model)
  - TimeSense (temporal awareness, quiet hours)
  - Trust scores (component and system trust)
  - Brains (cross-brain context via Hebbian mesh)
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="qwen-triad")
_instance = None


@dataclass
class TriadContext:
    """Full subsystem context gathered before model processing."""
    prompt: str
    user_intent: str = ""
    execution_allowed: bool = False

    # Subsystem context
    time_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    genesis_context: Dict[str, Any] = field(default_factory=dict)
    diagnostic_context: Dict[str, Any] = field(default_factory=dict)
    healing_context: Dict[str, Any] = field(default_factory=dict)
    learning_context: Dict[str, Any] = field(default_factory=dict)
    governance_context: Dict[str, Any] = field(default_factory=dict)
    mirror_context: Dict[str, Any] = field(default_factory=dict)
    trust_context: Dict[str, Any] = field(default_factory=dict)
    brain_context: Dict[str, Any] = field(default_factory=dict)
    coding_agents_context: Dict[str, Any] = field(default_factory=dict)

    # Model outputs
    triage: Dict[str, Any] = field(default_factory=dict)
    code_output: str = ""
    reason_output: str = ""
    fast_output: str = ""
    synthesis: str = ""

    # Metadata
    governance_decision: str = "read_only"
    total_time_ms: float = 0
    gather_time_ms: float = 0
    triad_time_ms: float = 0


class QwenTriadOrchestrator:
    """
    Orchestrates all 3 Qwen models with full subsystem awareness.

    Default mode is read-only (analyze/suggest). Execution requires
    explicit user opt-in via execution_allowed=True.
    """

    def __init__(self):
        self._initialized = False

    async def process(
        self,
        prompt: str,
        system_prompt: str = "",
        execution_allowed: bool = False,
        conversation_history: Optional[List[Dict]] = None,
        project_folder: str = "",
    ) -> Dict[str, Any]:
        """
        Main entry point. Runs the full triad pipeline:
        gather → triage → parallel triad → synthesize → govern → track
        """
        start = time.time()
        ctx = TriadContext(prompt=prompt, execution_allowed=execution_allowed)

        # 1. GATHER — pull context from all subsystems in parallel
        gather_start = time.time()
        await self._gather_all_context(ctx)
        ctx.gather_time_ms = round((time.time() - gather_start) * 1000, 1)

        # 2. TRIAGE — fast model classifies intent
        await self._triage(ctx)

        # 2b. CODE OPERATIONS — route through GRACE protocol with contract enforcement
        #     AI-to-AI: structured only, no NLP. NLP generated at human boundary.
        if ctx.triage.get("intent") in ("code", "execute", "debug") and ctx.triage.get("needs_code"):
            code_result = await self._route_code_through_protocol(ctx, project_folder)
            if code_result:
                ctx.total_time_ms = round((time.time() - start) * 1000, 1)
                return code_result

        # 3. TRIAD — all 3 models process in parallel
        triad_start = time.time()
        await self._run_triad(ctx, system_prompt, conversation_history)
        ctx.triad_time_ms = round((time.time() - triad_start) * 1000, 1)

        # 4. SYNTHESIZE — reasoning model merges outputs
        await self._synthesize(ctx, system_prompt)

        # 5. GOVERN — governance gate
        self._apply_governance(ctx)

        # 6. TRACK — genesis key + memory
        self._track(ctx)

        ctx.total_time_ms = round((time.time() - start) * 1000, 1)

        return {
            "response": ctx.synthesis,
            "triage": ctx.triage,
            "governance": ctx.governance_decision,
            "execution_allowed": ctx.execution_allowed,
            "subsystem_context": {
                "time": ctx.time_context,
                "memory": bool(ctx.memory_context),
                "genesis": bool(ctx.genesis_context),
                "diagnostics": bool(ctx.diagnostic_context),
                "healing": bool(ctx.healing_context),
                "learning": bool(ctx.learning_context),
                "governance": bool(ctx.governance_context),
                "mirror": bool(ctx.mirror_context),
                "trust": ctx.trust_context,
                "coding_agents": bool(ctx.coding_agents_context),
            },
            "model_outputs": {
                "code_model": ctx.code_output[:200] if ctx.code_output else None,
                "reason_model": ctx.reason_output[:200] if ctx.reason_output else None,
                "fast_model": ctx.fast_output[:200] if ctx.fast_output else None,
            },
            "coding_agents": ctx.coding_agents_context,
            "timing": {
                "total_ms": ctx.total_time_ms,
                "gather_ms": ctx.gather_time_ms,
                "triad_ms": ctx.triad_time_ms,
            },
        }

    # ── Context Gathering ─────────────────────────────────────────────

    async def _gather_all_context(self, ctx: TriadContext):
        """Pull context from all subsystems in parallel (11 sources)."""
        tasks = [
            self._gather_time(ctx),
            self._gather_memory(ctx),
            self._gather_genesis(ctx),
            self._gather_diagnostics(ctx),
            self._gather_healing(ctx),
            self._gather_learning(ctx),
            self._gather_governance(ctx),
            self._gather_mirror(ctx),
            self._gather_trust(ctx),
            self._gather_brain_mesh(ctx),
            self._gather_coding_agents(ctx),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _gather_time(self, ctx: TriadContext):
        try:
            from cognitive.time_sense import TimeSense
            ts = TimeSense()
            ctx.time_context = ts.get_context()
        except Exception as e:
            logger.debug(f"TimeSense unavailable: {e}")

    async def _gather_memory(self, ctx: TriadContext):
        def _sync():
            result = {}
            try:
                from cognitive.magma_bridge import query_context
                magma = query_context(ctx.prompt[:300])
                if magma:
                    result["magma"] = magma[:500]
            except Exception:
                pass
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                hits = fc.search(ctx.prompt[:200], limit=3, min_trust=0.4)
                if hits:
                    result["flash_cache"] = [
                        {"source": h.get("source_name", ""), "trust": h.get("trust_score", 0)}
                        for h in hits[:3]
                    ]
            except Exception:
                pass
            try:
                from cognitive.unified_memory import get_unified_memory
                um = get_unified_memory()
                episodic = um.recall_episodic(ctx.prompt[:200], limit=2)
                if episodic:
                    result["episodic"] = episodic[:2]
                procedural = um.recall_procedural(ctx.prompt[:100])
                if procedural:
                    result["procedural"] = procedural[:2]
            except Exception:
                pass
            return result
        loop = asyncio.get_event_loop()
        ctx.memory_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_genesis(self, ctx: TriadContext):
        def _sync():
            try:
                from database.session import session_scope
                from models.genesis_key_models import GenesisKey
                with session_scope() as s:
                    recent = s.query(GenesisKey).order_by(
                        GenesisKey.when_timestamp.desc()
                    ).limit(5).all()
                    return {
                        "recent_keys": [
                            {"type": str(k.key_type), "what": k.what_description[:80]}
                            for k in recent
                        ]
                    }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.genesis_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_diagnostics(self, ctx: TriadContext):
        def _sync():
            try:
                from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
                engine = get_diagnostic_engine()
                status = engine.get_status()
                return {
                    "health": status.get("health", "unknown"),
                    "active_issues": status.get("active_issues", 0),
                    "last_cycle": status.get("last_cycle", ""),
                }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.diagnostic_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_healing(self, ctx: TriadContext):
        def _sync():
            try:
                from cognitive.self_healing import SelfHealer
                healer = SelfHealer()
                return {
                    "last_healed": healer.last_healed.isoformat() if hasattr(healer, 'last_healed') and healer.last_healed else None,
                    "status": "active",
                }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.healing_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_learning(self, ctx: TriadContext):
        def _sync():
            try:
                from cognitive.learning_memory import LearningMemoryManager
                lm = LearningMemoryManager()
                patterns = lm.get_patterns(limit=3) if hasattr(lm, 'get_patterns') else []
                return {
                    "learned_patterns": len(patterns),
                    "recent": patterns[:2] if patterns else [],
                }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.learning_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_governance(self, ctx: TriadContext):
        def _sync():
            try:
                from security.governance import GovernanceEngine
                engine = GovernanceEngine()
                tier = engine.current_tier if hasattr(engine, 'current_tier') else "TIER_0_SUPERVISED"
                allowed = engine.get_allowed_actions() if hasattr(engine, 'get_allowed_actions') else {"read", "analyze", "suggest"}
                return {
                    "autonomy_tier": str(tier),
                    "allowed_actions": list(allowed)[:10],
                    "read_only": "execute" not in allowed and not ctx.execution_allowed,
                }
            except Exception:
                return {"autonomy_tier": "TIER_0_SUPERVISED", "read_only": True}
        loop = asyncio.get_event_loop()
        ctx.governance_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_mirror(self, ctx: TriadContext):
        def _sync():
            try:
                from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
                mirror = MirrorSelfModelingSystem()
                observation = mirror.observe() if hasattr(mirror, 'observe') else {}
                return {
                    "behavioral_patterns": observation.get("patterns", [])[:3],
                    "improvement_suggestions": observation.get("suggestions", [])[:2],
                }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.mirror_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_trust(self, ctx: TriadContext):
        def _sync():
            try:
                from ml_intelligence.kpi_tracker import get_kpi_tracker
                tracker = get_kpi_tracker()
                return {
                    "system_trust": tracker.get_system_trust_score(),
                    "health": tracker.get_system_health(),
                }
            except Exception:
                return {"system_trust": 0.5}
        loop = asyncio.get_event_loop()
        ctx.trust_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_brain_mesh(self, ctx: TriadContext):
        def _sync():
            try:
                from core.hebbian import get_hebbian_mesh
                mesh = get_hebbian_mesh()
                return {
                    "strongest_paths": mesh.get_strongest(limit=5) if hasattr(mesh, 'get_strongest') else [],
                }
            except Exception:
                return {}
        loop = asyncio.get_event_loop()
        ctx.brain_context = await loop.run_in_executor(_executor, _sync)

    async def _gather_coding_agents(self, ctx: TriadContext):
        """Gather status from multi-LLM coding agents (Kimi+Opus+Ollama).
        Same pattern as Qwen agent pool context gathering."""
        def _sync():
            try:
                from cognitive.coding_agents import get_coding_agent_pool
                pool = get_coding_agent_pool()
                status = pool.get_status()
                agents = status.get("agents", {})
                return {
                    "agents_available": list(agents.keys()),
                    "agent_count": len(agents),
                    "channel_messages": len(pool.channel.get_history(limit=10)),
                    "group_sessions": pool.ledger.get_summary().get("total_actions", 0),
                    "status": "active",
                }
            except Exception:
                return {"status": "unavailable"}
        loop = asyncio.get_event_loop()
        ctx.coding_agents_context = await loop.run_in_executor(_executor, _sync)

    async def _triage(self, ctx: TriadContext):
        """Fast model classifies intent and urgency."""
        def _sync():
            try:
                from llm_orchestrator.factory import get_llm_for_task
                client = get_llm_for_task("fast")

                triage_prompt = (
                    f"Classify this request in ONE line. Format: INTENT|URGENCY|NEEDS_CODE|NEEDS_REASONING\n"
                    f"INTENT: one of [code, analyze, explain, debug, plan, chat, search, execute]\n"
                    f"URGENCY: one of [low, medium, high, critical]\n"
                    f"NEEDS_CODE: yes/no\n"
                    f"NEEDS_REASONING: yes/no\n\n"
                    f"Request: {ctx.prompt[:500]}"
                )
                response = client.generate(triage_prompt, temperature=0.0, max_tokens=50)
                text = response if isinstance(response, str) else response.get("response", "")
                parts = text.strip().split("|")
                return {
                    "intent": parts[0].strip().lower() if len(parts) > 0 else "chat",
                    "urgency": parts[1].strip().lower() if len(parts) > 1 else "medium",
                    "needs_code": parts[2].strip().lower() == "yes" if len(parts) > 2 else False,
                    "needs_reasoning": parts[3].strip().lower() == "yes" if len(parts) > 3 else True,
                }
            except Exception as e:
                logger.warning(f"Triage failed, using defaults: {e}")
                return {"intent": "chat", "urgency": "medium", "needs_code": True, "needs_reasoning": True}

        loop = asyncio.get_event_loop()
        ctx.triage = await loop.run_in_executor(_executor, _sync)
        ctx.user_intent = ctx.triage.get("intent", "chat")

    # ── Code Protocol Route ─────────────────────────────────────────

    async def _route_code_through_protocol(
        self, ctx: TriadContext, project_folder: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Route code operations through the GRACE protocol.

        AI-to-AI: structured GraceMessage/GraceResponse (no NLP).
        Contract enforcement: deterministic checks on all generated code.
        NLP: generated ONLY at the human-facing boundary.
        """
        def _sync():
            from core.grace_protocol import (
                GraceMessage, OperationType, OutputMode, route_message,
            )

            op_map = {
                "code": OperationType.CODE_GENERATE,
                "execute": OperationType.CODE_GENERATE,
                "debug": OperationType.CODE_FIX,
            }
            operation = op_map.get(ctx.user_intent, OperationType.CODE_GENERATE)

            msg = GraceMessage(
                operation=operation,
                source="qwen_triad_orchestrator",
                target="coding_agent",
                payload={
                    "prompt": ctx.prompt,
                    "project_folder": project_folder,
                    "component": "user_request",
                    "problems": [],
                },
                output_mode=OutputMode.HUMAN,
                contract_type=operation.value,
                execution_allowed=ctx.execution_allowed,
            )

            response = route_message(msg)
            return response

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(_executor, _sync)
        except Exception as e:
            logger.warning(f"Protocol route failed, falling back to triad: {e}")
            return None

        result = {
            "response": response.human_text or response.error or "Code operation completed.",
            "triage": ctx.triage,
            "governance": "contract_enforced",
            "execution_allowed": ctx.execution_allowed,
            "protocol": "grace_structured",
            "contract_result": response.contract_result,
            "code": response.code,
            "subsystem_context": {
                "time": ctx.time_context,
                "memory": bool(ctx.memory_context),
                "genesis": bool(ctx.genesis_context),
                "diagnostics": bool(ctx.diagnostic_context),
                "healing": bool(ctx.healing_context),
                "learning": bool(ctx.learning_context),
                "governance": bool(ctx.governance_context),
                "mirror": bool(ctx.mirror_context),
                "trust": ctx.trust_context,
            },
            "timing": {
                "total_ms": ctx.total_time_ms,
                "gather_ms": ctx.gather_time_ms,
                "protocol_ms": response.duration_ms,
            },
        }

        self._track(ctx)
        return result

    # ── Parallel Triad ────────────────────────────────────────────────

    async def _run_triad(
        self,
        ctx: TriadContext,
        system_prompt: str = "",
        conversation_history: Optional[List[Dict]] = None,
    ):
        """Run all 3 Qwen models in parallel with role-specific prompts."""
        subsystem_summary = self._build_subsystem_summary(ctx)
        governance_note = ""
        if ctx.governance_context.get("read_only", True) and not ctx.execution_allowed:
            governance_note = (
                "\n[GOVERNANCE: Read-only mode. Analyze and suggest only. "
                "Do NOT execute, modify, or write unless the user explicitly requests execution.]"
            )

        base_context = f"{subsystem_summary}{governance_note}"
        history_text = ""
        if conversation_history:
            recent = conversation_history[-6:]
            history_text = "\n".join(
                f"[{m.get('role', 'user')}]: {m.get('content', '')[:200]}"
                for m in recent
            )
            if history_text:
                history_text = f"\n[Conversation context:\n{history_text}]"

        tasks = []

        if ctx.triage.get("needs_code", True):
            tasks.append(self._call_model(
                "code",
                f"You are the CODE specialist. Focus on implementation, code generation, and technical solutions."
                f"{base_context}{history_text}",
                ctx.prompt,
                system_prompt,
            ))
        else:
            async def _empty(): return ""
            tasks.append(_empty())

        if ctx.triage.get("needs_reasoning", True):
            tasks.append(self._call_model(
                "reason",
                f"You are the REASONING specialist. Focus on deep analysis, architecture, trade-offs, and strategic thinking."
                f"{base_context}{history_text}",
                ctx.prompt,
                system_prompt,
            ))
        else:
            async def _empty(): return ""
            tasks.append(_empty())

        tasks.append(self._call_model(
            "fast",
            f"You are the SYNTHESIS specialist. Provide a clear, concise, actionable response."
            f"{base_context}{history_text}",
            ctx.prompt,
            system_prompt,
        ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Triad task {i} failed with exception: {res}")
                import traceback
                traceback.print_exception(type(res), res, res.__traceback__)

        ctx.code_output = results[0] if not isinstance(results[0], Exception) else ""
        ctx.reason_output = results[1] if not isinstance(results[1], Exception) else ""
        ctx.fast_output = results[2] if not isinstance(results[2], Exception) else ""

    async def _call_model(
        self,
        task: str,
        role_prompt: str,
        user_prompt: str,
        base_system_prompt: str = "",
    ) -> str:
        """Call a specific Qwen model via Ollama."""
        def _sync():
            from llm_orchestrator.factory import get_llm_for_task
            client = get_llm_for_task(task)
            full_system = f"{base_system_prompt}\n{role_prompt}" if base_system_prompt else role_prompt
            messages = [
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_prompt},
            ]
            response = client.chat(messages=messages, temperature=0.3)
            if isinstance(response, dict):
                return response.get("message", {}).get("content", "") if "message" in response else response.get("response", str(response))
            return str(response)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _sync)

    # ── Synthesis ─────────────────────────────────────────────────────

    async def _synthesize(self, ctx: TriadContext, system_prompt: str = ""):
        """Reasoning model merges all model outputs into a coherent response."""
        outputs = []
        if ctx.code_output:
            outputs.append(f"[CODE MODEL]: {ctx.code_output}")
        if ctx.reason_output:
            outputs.append(f"[REASONING MODEL]: {ctx.reason_output}")
        if ctx.fast_output:
            outputs.append(f"[FAST MODEL]: {ctx.fast_output}")

        if not outputs:
            ctx.synthesis = "I apologize, but I was unable to generate a response. Please try again."
            return

        if len(outputs) == 1:
            ctx.synthesis = outputs[0].split("]: ", 1)[-1]
            return

        def _sync():
            from llm_orchestrator.factory import get_llm_for_task
            client = get_llm_for_task("reason")

            governance_note = ""
            if ctx.governance_context.get("read_only", True) and not ctx.execution_allowed:
                governance_note = (
                    "\nIMPORTANT: Respond in read-only advisory mode. "
                    "Suggest and analyze but do not instruct execution unless the user explicitly requested it."
                )

            synthesis_prompt = (
                f"You received responses from 3 specialized AI models to the same user question.\n"
                f"Synthesize them into ONE coherent, comprehensive response.\n"
                f"Prefer code from the CODE model, reasoning from the REASONING model, "
                f"and conciseness from the FAST model.\n"
                f"Resolve any conflicts by preferring depth and correctness.{governance_note}\n\n"
                f"User question: {ctx.prompt}\n\n"
                + "\n\n".join(outputs)
            )

            sys_prompt = system_prompt or "You are GRACE, a cognitive AI system. Synthesize the multi-model outputs into one response."
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": synthesis_prompt},
            ]
            response = client.chat(messages=messages, temperature=0.2)
            if isinstance(response, dict):
                return response.get("message", {}).get("content", "") if "message" in response else response.get("response", str(response))
            return str(response)

        loop = asyncio.get_event_loop()
        ctx.synthesis = await loop.run_in_executor(_executor, _sync)

    # ── Governance Gate ───────────────────────────────────────────────

    def _apply_governance(self, ctx: TriadContext):
        """Enforce governance: read-only unless user explicitly allows execution."""
        if ctx.execution_allowed:
            ctx.governance_decision = "execution_allowed"
        elif ctx.governance_context.get("read_only", True):
            ctx.governance_decision = "read_only"
            execution_phrases = [
                "I will now execute", "I'll run this", "executing the following",
                "running the command", "I have applied",
            ]
            for phrase in execution_phrases:
                if phrase.lower() in ctx.synthesis.lower():
                    ctx.synthesis = ctx.synthesis.replace(
                        phrase,
                        f"[GOVERNANCE: Would {phrase.lower()} — but read-only mode is active. "
                        f"Set execution_allowed=True to proceed.]"
                    )
        else:
            ctx.governance_decision = "supervised"

    # ── Tracking ──────────────────────────────────────────────────────

    def _track(self, ctx: TriadContext):
        """Record Genesis key and update episodic memory."""
        try:
            from api._genesis_tracker import track
            track(
                key_type="triad_response",
                what=f"Triad: {ctx.user_intent} ({ctx.triage.get('urgency', 'medium')})",
                who="qwen_triad_orchestrator",
                how="async_parallel",
                tags=["triad", ctx.user_intent, ctx.governance_decision],
            )
        except Exception:
            pass

        try:
            from cognitive.unified_memory import get_unified_memory
            um = get_unified_memory()
            um.store_episodic(
                event=f"triad:{ctx.user_intent}",
                context=ctx.prompt[:200],
                outcome=ctx.synthesis[:200],
                success=bool(ctx.synthesis),
            )
        except Exception:
            pass

    # ── Helpers ────────────────────────────────────────────────────────

    def _build_subsystem_summary(self, ctx: TriadContext) -> str:
        """Build a concise subsystem context string for model prompts."""
        parts = []

        if ctx.time_context:
            period = ctx.time_context.get("period", "")
            if period:
                parts.append(f"Time: {period}")

        if ctx.memory_context.get("magma"):
            parts.append(f"Memory: {ctx.memory_context['magma'][:200]}")

        if ctx.memory_context.get("episodic"):
            eps = ctx.memory_context["episodic"]
            parts.append(f"Past experience: {len(eps)} relevant episodes")

        if ctx.diagnostic_context.get("health"):
            parts.append(f"System health: {ctx.diagnostic_context['health']}")

        if ctx.trust_context.get("system_trust"):
            parts.append(f"Trust score: {ctx.trust_context['system_trust']:.2f}")

        if ctx.learning_context.get("learned_patterns"):
            parts.append(f"Learned patterns: {ctx.learning_context['learned_patterns']}")

        if ctx.mirror_context.get("improvement_suggestions"):
            sug = ctx.mirror_context["improvement_suggestions"]
            parts.append(f"Self-improvement: {len(sug)} suggestions")

        if ctx.governance_context.get("autonomy_tier"):
            parts.append(f"Governance: {ctx.governance_context['autonomy_tier']}")

        if ctx.coding_agents_context.get("status") == "active":
            agents = ctx.coding_agents_context.get("agents_available", [])
            parts.append(f"Coding agents: {', '.join(agents)} ({ctx.coding_agents_context.get('agent_count', 0)} active)")

        if not parts:
            return ""

        return "\n[System context: " + " | ".join(parts) + "]"


def get_triad_orchestrator() -> QwenTriadOrchestrator:
    """Get singleton triad orchestrator instance."""
    global _instance
    if _instance is None:
        _instance = QwenTriadOrchestrator()
    return _instance
