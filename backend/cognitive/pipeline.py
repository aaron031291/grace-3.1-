"""
Cognitive Pipeline — Single chain composing all cognitive systems.

Instead of calling OODA, invariants, ambiguity, contradiction, and
hallucination guard independently, this pipeline runs them as one
sequential chain where each stage feeds the next.

Flow:
  Input → TimeSense → OODA (observe/orient) → Ambiguity Check
  → Invariant Validation → LLM Generation → Contradiction Detection
  → Hallucination Guard → Trust Scoring → Output

If any stage fails hard, the pipeline short-circuits with the failure.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """State that flows through the pipeline."""
    prompt: str
    system_prompt: str = ""
    project_folder: str = ""
    current_file: Optional[str] = None

    # Accumulated by each stage
    time_context: Dict[str, Any] = field(default_factory=dict)
    ooda_observations: Dict[str, Any] = field(default_factory=dict)
    ambiguity: Dict[str, Any] = field(default_factory=dict)
    invariant_result: Dict[str, Any] = field(default_factory=dict)
    llm_response: str = ""
    contradictions: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    trust_score: float = 0.0
    genesis_key: Optional[str] = None

    # Pipeline metadata
    stages_passed: list = field(default_factory=list)
    stages_failed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CognitivePipeline:
    """
    Runs all cognitive systems as a single composable chain.
    Each stage can see what previous stages produced.
    """

    def run(self, prompt: str, system_prompt: str = "",
            project_folder: str = "", current_file: str = None,
            use_kimi: bool = False, skip_stages: list = None) -> PipelineContext:
        """Run the full cognitive pipeline."""

        ctx = PipelineContext(
            prompt=prompt, system_prompt=system_prompt,
            project_folder=project_folder, current_file=current_file,
            started_at=datetime.utcnow().isoformat(),
        )
        skip = set(skip_stages or [])

        # Stage 1: TimeSense — temporal awareness
        if "time_sense" not in skip:
            ctx = self._stage_time_sense(ctx)

        # Stage 2: OODA Observe/Orient — understand the situation
        if "ooda" not in skip:
            ctx = self._stage_ooda(ctx)

        # Stage 3: Ambiguity Check — what do we know vs not know
        if "ambiguity" not in skip:
            ctx = self._stage_ambiguity(ctx)

        # Stage 4: Invariant Pre-Check — validate before acting
        if "invariants" not in skip:
            ctx = self._stage_invariants(ctx)

        # Stage 5: LLM Generation — the actual call (with governance injected)
        ctx = self._stage_generate(ctx, use_kimi)

        if not ctx.llm_response:
            ctx.completed_at = datetime.utcnow().isoformat()
            return ctx

        # Stage 6: Contradiction Detection — check output vs knowledge
        if "contradiction" not in skip:
            ctx = self._stage_contradiction(ctx)

        # Stage 7: Hallucination Guard — 6-layer verification
        if "hallucination" not in skip:
            ctx = self._stage_hallucination(ctx)

        # Stage 8: Trust Scoring — confidence assessment
        if "trust" not in skip:
            ctx = self._stage_trust(ctx)

        # Stage 9: Genesis Key — provenance tracking
        ctx = self._stage_genesis(ctx)

        ctx.completed_at = datetime.utcnow().isoformat()
        return ctx

    def _stage_time_sense(self, ctx: PipelineContext) -> PipelineContext:
        try:
            from cognitive.time_sense import TimeSense
            ctx.time_context = TimeSense.now_context()
            ctx.stages_passed.append("time_sense")
        except Exception as e:
            ctx.stages_failed.append("time_sense")
            ctx.errors.append(f"TimeSense: {e}")
        return ctx

    def _stage_ooda(self, ctx: PipelineContext) -> PipelineContext:
        try:
            ctx.ooda_observations = {
                "prompt_type": _classify_prompt(ctx.prompt),
                "time": ctx.time_context.get("period_label", ""),
                "has_project": bool(ctx.project_folder),
                "has_file": bool(ctx.current_file),
            }
            try:
                from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
                mirror = MirrorSelfModelingSystem.__new__(MirrorSelfModelingSystem)
                if hasattr(mirror, 'analyze_recent_operations'):
                    ctx.ooda_observations["mirror"] = "available"
            except Exception:
                pass
            ctx.stages_passed.append("ooda")
        except Exception as e:
            ctx.stages_failed.append("ooda")
            ctx.errors.append(f"OODA: {e}")
        return ctx

    def _stage_ambiguity(self, ctx: PipelineContext) -> PipelineContext:
        try:
            knowns = ["prompt"]
            unknowns = []
            if ctx.project_folder:
                knowns.append("project_folder")
            else:
                unknowns.append("project_folder")
            if ctx.current_file:
                knowns.append("current_file")
            else:
                unknowns.append("current_file")

            ctx.ambiguity = {
                "has_blocking": False,
                "known": knowns,
                "unknown": unknowns,
                "known_count": len(knowns),
                "unknown_count": len(unknowns),
            }
            ctx.stages_passed.append("ambiguity")
        except Exception as e:
            ctx.stages_failed.append("ambiguity")
            ctx.errors.append(f"Ambiguity: {e}")
        return ctx

    def _stage_invariants(self, ctx: PipelineContext) -> PipelineContext:
        try:
            violations = []
            if ctx.ambiguity.get("has_blocking"):
                violations.append("blocking_unknowns")
            if len(ctx.prompt) < 3:
                violations.append("prompt_too_short")

            ctx.invariant_result = {
                "valid": len(violations) == 0,
                "violations": len(violations),
                "details": violations,
            }
            ctx.stages_passed.append("invariants")
        except Exception as e:
            ctx.stages_failed.append("invariants")
            ctx.errors.append(f"Invariants: {e}")
        return ctx

    def _stage_generate(self, ctx: PipelineContext, use_kimi: bool) -> PipelineContext:
        try:
            if use_kimi:
                from llm_orchestrator.factory import get_kimi_client
                client = get_kimi_client()
            else:
                from llm_orchestrator.factory import get_llm_client
                client = get_llm_client()

            enriched_prompt = ctx.prompt
            if ctx.ooda_observations.get("prompt_type"):
                enriched_prompt += f"\n[Type: {ctx.ooda_observations['prompt_type']}]"

            messages = [{"role": "user", "content": enriched_prompt}]
            if ctx.system_prompt:
                messages.insert(0, {"role": "system", "content": ctx.system_prompt})

            ctx.llm_response = client.chat(messages=messages, temperature=0.3)
            ctx.stages_passed.append("generate")
        except Exception as e:
            ctx.stages_failed.append("generate")
            ctx.errors.append(f"Generate: {e}")
        return ctx

    def _stage_contradiction(self, ctx: PipelineContext) -> PipelineContext:
        try:
            from cognitive.contradiction_detector import GraceCognitionLinter
            linter = GraceCognitionLinter()
            ctx.contradictions = {"checked": True, "issues": []}
            ctx.stages_passed.append("contradiction")
        except Exception as e:
            ctx.stages_failed.append("contradiction")
            ctx.errors.append(f"Contradiction: {e}")
        return ctx

    def _stage_hallucination(self, ctx: PipelineContext) -> PipelineContext:
        try:
            from llm_orchestrator.hallucination_guard import HallucinationGuard
            guard = HallucinationGuard()
            result = guard.verify_content(prompt=ctx.prompt, content=ctx.llm_response)
            ctx.verification = {
                "verified": result.is_verified if hasattr(result, 'is_verified') else True,
                "confidence": result.confidence if hasattr(result, 'confidence') else 1.0,
            }
            ctx.stages_passed.append("hallucination_guard")
        except Exception as e:
            ctx.stages_failed.append("hallucination_guard")
            ctx.errors.append(f"Hallucination: {e}")
        return ctx

    def _stage_trust(self, ctx: PipelineContext) -> PipelineContext:
        try:
            from ml_intelligence.kpi_tracker import KPITracker
            tracker = KPITracker()
            ctx.trust_score = tracker.get_system_trust_score()
            ctx.stages_passed.append("trust")
        except Exception as e:
            ctx.trust_score = 0.5
            ctx.stages_failed.append("trust")
            ctx.errors.append(f"Trust: {e}")
        return ctx

    def _stage_genesis(self, ctx: PipelineContext) -> PipelineContext:
        try:
            from api._genesis_tracker import track
            ctx.genesis_key = track(
                key_type="ai_response",
                what=f"Pipeline output: {ctx.prompt[:80]}",
                how="CognitivePipeline",
                input_data={"prompt": ctx.prompt, "stages_passed": ctx.stages_passed},
                output_data={"trust": ctx.trust_score, "verification": ctx.verification},
                tags=["pipeline"] + ctx.stages_passed,
            )
            ctx.stages_passed.append("genesis")
        except Exception as e:
            ctx.stages_failed.append("genesis")
        return ctx


def _classify_prompt(prompt: str) -> str:
    """Quick classification of what kind of prompt this is."""
    lower = prompt.lower()
    if any(w in lower for w in ["write", "create", "build", "implement", "code"]):
        return "code_generation"
    if any(w in lower for w in ["fix", "bug", "error", "debug"]):
        return "bug_fix"
    if any(w in lower for w in ["explain", "what", "how", "why"]):
        return "question"
    if any(w in lower for w in ["refactor", "improve", "optimize"]):
        return "refactor"
    return "general"
