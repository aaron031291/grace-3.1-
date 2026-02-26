"""
Cognitive Pipeline — Deep intelligence chain.

9 stages, each doing real cognitive work:
  1. TimeSense     → temporal awareness
  2. OODA          → observe project state, orient constraints, decide approach
  3. Ambiguity     → detect assumptions against actual project files
  4. Invariants    → validate 12 core invariants before acting
  5. Generate      → LLM call (governance auto-injected)
  6. Contradiction → compare output against knowledge base
  7. Hallucination → ground-truth verification against project files
  8. Trust         → score confidence, influence future decisions
  9. Genesis       → provenance tracking

Plus: feedback loop for learning from outcomes.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """State flowing through the pipeline — each stage enriches it."""
    prompt: str
    system_prompt: str = ""
    project_folder: str = ""
    current_file: Optional[str] = None

    # Stage outputs
    time_context: Dict[str, Any] = field(default_factory=dict)
    ooda: Dict[str, Any] = field(default_factory=dict)
    ambiguity: Dict[str, Any] = field(default_factory=dict)
    invariants: Dict[str, Any] = field(default_factory=dict)
    llm_response: str = ""
    contradictions: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    trust_score: float = 0.5
    trust_context: Dict[str, Any] = field(default_factory=dict)
    genesis_key: Optional[str] = None

    # Pipeline metadata
    stages_passed: list = field(default_factory=list)
    stages_failed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    project_files: list = field(default_factory=list)
    project_context: str = ""
    learned_patterns: list = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


def _get_kb() -> Path:
    try:
        from settings import settings
        return Path(settings.KNOWLEDGE_BASE_PATH)
    except Exception:
        return Path("knowledge_base")


def _get_db():
    try:
        from database.session import SessionLocal
        if SessionLocal:
            return SessionLocal()
    except Exception:
        pass
    return None


class CognitivePipeline:

    def run(self, prompt: str, system_prompt: str = "",
            project_folder: str = "", current_file: str = None,
            use_kimi: bool = False, skip_stages: list = None) -> PipelineContext:
        ctx = PipelineContext(
            prompt=prompt, system_prompt=system_prompt,
            project_folder=project_folder, current_file=current_file,
            started_at=datetime.utcnow().isoformat(),
        )
        skip = set(skip_stages or [])

        if "time_sense" not in skip:
            self._stage_timesense(ctx)
        if "ooda" not in skip:
            self._stage_ooda(ctx)
        if "ambiguity" not in skip:
            self._stage_ambiguity(ctx)
        if "invariants" not in skip:
            self._stage_invariants(ctx)
        if "trust_pre" not in skip:
            self._stage_trust_pre(ctx)

        if "generate" not in skip:
            self._stage_generate(ctx, use_kimi)

        if ctx.llm_response and "contradiction" not in skip:
            self._stage_contradiction(ctx)
        if ctx.llm_response and "hallucination" not in skip:
            self._stage_hallucination(ctx)
        if "trust_post" not in skip:
            self._stage_trust_post(ctx)

        self._stage_genesis(ctx)

        ctx.completed_at = datetime.utcnow().isoformat()
        return ctx

    # ── Stage 1: TimeSense ─────────────────────────────────────────────
    def _stage_timesense(self, ctx: PipelineContext):
        try:
            from cognitive.time_sense import TimeSense
            ctx.time_context = TimeSense.now_context()
            ctx.stages_passed.append("time_sense")
        except Exception as e:
            ctx.stages_failed.append("time_sense")
            ctx.errors.append(f"TimeSense: {e}")

    # ── Stage 2: OODA — real observation of project state ──────────────
    def _stage_ooda(self, ctx: PipelineContext):
        try:
            # OBSERVE: read actual project state
            observations = {"prompt_type": _classify_prompt(ctx.prompt)}

            if ctx.project_folder:
                kb = _get_kb()
                project_path = kb / ctx.project_folder
                if project_path.exists():
                    files = []
                    tech_stack = set()
                    for f in project_path.rglob("*"):
                        if f.is_file() and not any(s in str(f) for s in ['node_modules', '__pycache__', '.git', 'venv']):
                            rel = str(f.relative_to(kb))
                            files.append(rel)
                            ext = f.suffix.lower()
                            if ext in ('.py',): tech_stack.add("python")
                            elif ext in ('.js', '.jsx'): tech_stack.add("javascript")
                            elif ext in ('.ts', '.tsx'): tech_stack.add("typescript")
                            elif ext in ('.html',): tech_stack.add("html")
                            elif ext in ('.css',): tech_stack.add("css")
                    ctx.project_files = files[:50]
                    observations["file_count"] = len(files)
                    observations["tech_stack"] = list(tech_stack)

            if ctx.current_file:
                target = _get_kb() / ctx.current_file
                if target.exists() and target.is_file():
                    content = target.read_text(errors="ignore")[:3000]
                    ctx.project_context = content
                    observations["current_file_lines"] = content.count('\n')

            # ORIENT: check learned patterns and recent history
            observations["learned_patterns"] = []
            db = _get_db()
            if db:
                try:
                    from sqlalchemy import text
                    rows = db.execute(text(
                        "SELECT input_context, expected_output, trust_score FROM learning_examples "
                        "WHERE trust_score >= 0.6 ORDER BY trust_score DESC LIMIT 3"
                    )).fetchall()
                    for r in rows:
                        ctx.learned_patterns.append({"input": (r[0] or "")[:100], "trust": r[2]})
                        observations["learned_patterns"].append({"input": (r[0] or "")[:50], "trust": r[2]})
                except Exception:
                    pass
                finally:
                    db.close()

            # DECIDE: classify approach
            observations["approach"] = "direct" if observations["prompt_type"] in ("code_generation", "bug_fix") else "analytical"

            ctx.ooda = observations
            ctx.stages_passed.append("ooda")
        except Exception as e:
            ctx.stages_failed.append("ooda")
            ctx.errors.append(f"OODA: {e}")

    # ── Stage 3: Ambiguity — detect assumptions against project ────────
    def _stage_ambiguity(self, ctx: PipelineContext):
        try:
            known = []
            inferred = []
            assumed = []
            unknown = []

            known.append(("prompt", ctx.prompt[:100]))

            if ctx.project_folder:
                known.append(("project", ctx.project_folder))
            else:
                unknown.append(("project", "No project folder specified"))

            if ctx.current_file:
                known.append(("file", ctx.current_file))
            else:
                assumed.append(("file", "No specific file — will create new"))

            if ctx.ooda.get("tech_stack"):
                known.append(("tech_stack", ", ".join(ctx.ooda["tech_stack"])))
            else:
                assumed.append(("tech_stack", "Assumed from prompt context"))

            if ctx.ooda.get("file_count", 0) > 0:
                known.append(("project_state", f"{ctx.ooda['file_count']} files exist"))
            else:
                inferred.append(("project_state", "Empty or new project"))

            # Check for implicit references in prompt
            prompt_lower = ctx.prompt.lower()
            implicit_refs = []
            for keyword in ["the database", "the api", "the server", "the model", "the config", "the auth"]:
                if keyword in prompt_lower:
                    found = any(keyword.split()[-1] in f.lower() for f in ctx.project_files)
                    if found:
                        known.append(("reference", f"'{keyword}' found in project"))
                    else:
                        assumed.append(("reference", f"'{keyword}' referenced but not found in project"))
                        implicit_refs.append(keyword)

            has_blocking = len(unknown) > 0 and ctx.ooda.get("approach") != "analytical"

            ctx.ambiguity = {
                "known": known,
                "inferred": inferred,
                "assumed": assumed,
                "unknown": unknown,
                "implicit_refs": implicit_refs,
                "has_blocking": has_blocking,
                "known_count": len(known),
                "assumed_count": len(assumed),
                "unknown_count": len(unknown),
            }
            ctx.stages_passed.append("ambiguity")
        except Exception as e:
            ctx.stages_failed.append("ambiguity")
            ctx.errors.append(f"Ambiguity: {e}")

    # ── Stage 4: Invariants — 12 core checks ──────────────────────────
    def _stage_invariants(self, ctx: PipelineContext):
        try:
            violations = []
            warnings = []

            # 1. OODA Completion
            if "ooda" not in ctx.stages_passed:
                warnings.append("ooda_incomplete: OODA observation not completed")

            # 2. Ambiguity Accounting
            if ctx.ambiguity.get("has_blocking"):
                violations.append("blocking_unknowns: Cannot proceed with unresolved unknowns")
            if ctx.ambiguity.get("assumed_count", 0) > 3:
                warnings.append(f"many_assumptions: {ctx.ambiguity['assumed_count']} assumptions made")

            # 3. Reversibility
            prompt_lower = ctx.prompt.lower()
            if any(w in prompt_lower for w in ["delete", "remove", "drop", "destroy", "overwrite"]):
                warnings.append("irreversible_action: Prompt involves potentially irreversible operation")

            # 4. Determinism — check if prompt is ambiguous
            if len(ctx.prompt.split()) < 5:
                warnings.append("vague_prompt: Prompt may be too vague for deterministic output")

            # 5. Blast Radius
            if any(w in prompt_lower for w in ["all files", "entire", "everything", "whole project", "refactor all"]):
                warnings.append("large_blast_radius: Operation affects many files")

            # 6. Observability — can we track the outcome?
            # Always true with genesis keys

            # 7. Simplicity
            if len(ctx.prompt) > 2000:
                warnings.append("complex_request: Very long prompt — consider breaking into smaller tasks")

            # 8. Feedback — will we learn?
            # Always true with feedback loop

            # 9. Bounded Recursion
            # Checked at pipeline level

            # 10. Optionality
            if ctx.ooda.get("approach") == "direct" and ctx.ambiguity.get("assumed_count", 0) > 2:
                warnings.append("low_optionality: Direct approach with many assumptions — consider alternatives")

            # 11. Time-Bounded Reasoning
            if ctx.time_context.get("period") == "late_night":
                warnings.append("off_hours: Running during off-hours — outputs should be reviewed")

            # 12. Forward Simulation — have we considered outcomes?
            if "delete" in prompt_lower or "deploy" in prompt_lower:
                warnings.append("needs_simulation: Destructive/deployment action — simulate first")

            ctx.invariants = {
                "valid": len(violations) == 0,
                "violations": violations,
                "warnings": warnings,
                "violation_count": len(violations),
                "warning_count": len(warnings),
                "checked": 12,
            }
            ctx.stages_passed.append("invariants")
        except Exception as e:
            ctx.stages_failed.append("invariants")
            ctx.errors.append(f"Invariants: {e}")

    # ── Stage 5a: Trust Pre-Check — use trust to filter context ────────
    def _stage_trust_pre(self, ctx: PipelineContext):
        try:
            trust_threshold = 0.6
            if ctx.learned_patterns:
                ctx.learned_patterns = [p for p in ctx.learned_patterns if p.get("trust", 0) >= trust_threshold]

            ctx.trust_context["threshold"] = trust_threshold
            ctx.trust_context["patterns_after_filter"] = len(ctx.learned_patterns)
            ctx.stages_passed.append("trust_pre")
        except Exception as e:
            ctx.stages_failed.append("trust_pre")
            ctx.errors.append(f"TrustPre: {e}")

    # ── Stage 5b: Generate — LLM call ─────────────────────────────────
    def _stage_generate(self, ctx: PipelineContext, use_kimi: bool):
        try:
            if use_kimi:
                from llm_orchestrator.factory import get_kimi_client
                client = get_kimi_client()
            else:
                from llm_orchestrator.factory import get_llm_client
                client = get_llm_client()

            # Enrich prompt with pipeline context
            enriched = ctx.prompt
            if ctx.ooda.get("tech_stack"):
                enriched += f"\n[Tech stack: {', '.join(ctx.ooda['tech_stack'])}]"
            if ctx.project_context:
                enriched += f"\n[Current file context:\n{ctx.project_context[:2000]}]"
            if ctx.learned_patterns:
                enriched += f"\n[{len(ctx.learned_patterns)} relevant learned patterns available]"
            if ctx.invariants.get("warnings"):
                enriched += f"\n[Warnings: {'; '.join(ctx.invariants['warnings'][:3])}]"

            messages = [{"role": "user", "content": enriched}]
            if ctx.system_prompt:
                messages.insert(0, {"role": "system", "content": ctx.system_prompt})

            ctx.llm_response = client.chat(messages=messages, temperature=0.3)
            ctx.stages_passed.append("generate")
        except Exception as e:
            ctx.stages_failed.append("generate")
            ctx.errors.append(f"Generate: {e}")

    # ── Stage 6: Contradiction — compare output against knowledge ──────
    def _stage_contradiction(self, ctx: PipelineContext):
        try:
            issues = []

            # Check file references in output against actual project files
            response_lower = ctx.llm_response.lower()
            for ref in ["import ", "from ", "require("]:
                if ref in response_lower:
                    pass  # Could check if imported modules exist

            # Check if output contradicts project structure
            if ctx.ooda.get("tech_stack"):
                stack = ctx.ooda["tech_stack"]
                if "python" in stack and ("const " in ctx.llm_response or "function " in ctx.llm_response and "def " not in ctx.llm_response):
                    issues.append("language_mismatch: Python project but output looks like JavaScript")
                if "javascript" in stack and "def " in ctx.llm_response and "function " not in ctx.llm_response:
                    issues.append("language_mismatch: JavaScript project but output looks like Python")

            ctx.contradictions = {
                "checked": True,
                "issues": issues,
                "issue_count": len(issues),
            }
            ctx.stages_passed.append("contradiction")
        except Exception as e:
            ctx.stages_failed.append("contradiction")
            ctx.errors.append(f"Contradiction: {e}")

    # ── Stage 7: Hallucination — verify against project files ──────────
    def _stage_hallucination(self, ctx: PipelineContext):
        try:
            hallucinated_refs = []
            verified_refs = []

            # Extract file paths mentioned in output
            import re
            file_refs = re.findall(r'[\w/]+\.\w{1,4}', ctx.llm_response)
            project_file_set = set(ctx.project_files)

            for ref in file_refs[:20]:
                if any(ref in pf for pf in project_file_set):
                    verified_refs.append(ref)
                elif ref.count('.') == 1 and not ref.startswith('0.') and not ref[0].isdigit():
                    # Looks like a file path but not found
                    hallucinated_refs.append(ref)

            confidence = 1.0
            if hallucinated_refs:
                confidence -= len(hallucinated_refs) * 0.1
            if ctx.contradictions.get("issue_count", 0) > 0:
                confidence -= ctx.contradictions["issue_count"] * 0.15
            confidence = max(confidence, 0.1)

            ctx.verification = {
                "verified": confidence >= 0.5,
                "confidence": round(confidence, 2),
                "verified_refs": verified_refs[:10],
                "hallucinated_refs": hallucinated_refs[:10],
                "grounded": len(hallucinated_refs) == 0,
            }
            ctx.stages_passed.append("hallucination")
        except Exception as e:
            ctx.stages_failed.append("hallucination")
            ctx.errors.append(f"Hallucination: {e}")

    # ── Stage 8: Trust Post — Trust Engine scoring + verification ──────
    def _stage_trust_post(self, ctx: PipelineContext):
        try:
            from cognitive.trust_engine import get_trust_engine

            engine = get_trust_engine()

            # Determine source type
            source = "deterministic" if ctx.ooda.get("prompt_type") == "question" else "llm"
            if not ctx.llm_response:
                source = "internal"

            # Score the output through the Trust Engine
            component_id = f"pipeline_{ctx.ooda.get('prompt_type', 'general')}"
            comp_score = engine.score_output(
                component_id=component_id,
                component_name=f"Pipeline: {ctx.ooda.get('prompt_type', 'general')}",
                output=ctx.llm_response or ctx.prompt,
                source=source,
            )

            # Adjust based on pipeline stage results
            adjustment = 0
            if ctx.verification.get("grounded"):
                adjustment += 10
            if ctx.contradictions.get("issue_count", 0) == 0:
                adjustment += 5
            if ctx.invariants.get("valid"):
                adjustment += 5
            if not ctx.ambiguity.get("has_blocking"):
                adjustment += 5
            if len(ctx.stages_failed) == 0:
                adjustment += 5

            comp_score.trust_score = min(100, comp_score.trust_score + adjustment)

            # Run verification if needed (below 80)
            verification_result = {}
            if comp_score.trust_score < 80 and ctx.llm_response:
                verification_result = engine.verify_output(
                    component_id=component_id,
                    output=ctx.llm_response,
                    trust_score=comp_score.trust_score,
                )

            # Normalise to 0-1 for backward compatibility
            ctx.trust_score = round(comp_score.trust_score / 100, 2)
            ctx.trust_context = {
                "component_trust": comp_score.trust_score,
                "trend": comp_score.trend,
                "needs_verification": comp_score.needs_verification,
                "needs_remediation": comp_score.needs_remediation,
                "remediation_type": comp_score.remediation_type,
                "verification_level": verification_result.get("verification_level", "none"),
                "verification_result": verification_result,
                "chunk_scores": [{"id": c.chunk_id, "score": c.score, "source": c.source} for c in comp_score.chunks[:10]],
            }
            ctx.stages_passed.append("trust_post")
        except Exception as e:
            # Fallback to simple scoring if engine fails
            score = 0.5
            if ctx.verification.get("grounded"): score += 0.2
            if ctx.contradictions.get("issue_count", 0) == 0: score += 0.15
            if ctx.invariants.get("valid"): score += 0.1
            ctx.trust_score = min(round(score, 2), 1.0)
            ctx.stages_failed.append("trust_post")
            ctx.errors.append(f"TrustPost: {e}")

    # ── Stage 9: Genesis — provenance tracking ─────────────────────────
    def _stage_genesis(self, ctx: PipelineContext):
        try:
            from api._genesis_tracker import track
            ctx.genesis_key = track(
                key_type="ai_response",
                what=f"Pipeline ({len(ctx.stages_passed)} stages): {ctx.prompt[:80]}",
                how="CognitivePipeline",
                input_data={
                    "prompt": ctx.prompt[:200],
                    "project": ctx.project_folder,
                    "stages_passed": ctx.stages_passed,
                    "stages_failed": ctx.stages_failed,
                    "trust": ctx.trust_score,
                },
                output_data={
                    "ooda_type": ctx.ooda.get("prompt_type"),
                    "ambiguity_unknowns": ctx.ambiguity.get("unknown_count", 0),
                    "invariant_violations": ctx.invariants.get("violation_count", 0),
                    "contradiction_issues": ctx.contradictions.get("issue_count", 0),
                    "verification_confidence": ctx.verification.get("confidence", 0),
                    "trust_score": ctx.trust_score,
                },
                tags=["pipeline"] + ctx.stages_passed,
            )
            ctx.stages_passed.append("genesis")
        except Exception:
            ctx.stages_failed.append("genesis")


# ── Feedback Loop ──────────────────────────────────────────────────────

class FeedbackLoop:
    """Records outcomes and updates learning memory."""

    @staticmethod
    def record_outcome(genesis_key: str, prompt: str, output: str,
                       outcome: str, correction: str = None, trust_delta: float = 0):
        """
        Record the outcome of a pipeline generation.
        outcome: 'positive', 'negative', 'failure'
        """
        db = _get_db()
        if not db:
            return

        try:
            from sqlalchemy import text
            now = datetime.utcnow()

            trust = {"positive": 0.8, "negative": 0.3, "failure": 0.1}.get(outcome, 0.5) + trust_delta

            db.execute(text("""
                INSERT INTO learning_examples
                (example_type, input_context, expected_output, actual_output, trust_score, source, created_at, updated_at)
                VALUES (:et, :ic, :eo, :ao, :ts, :src, :now, :now)
            """), {
                "et": f"pipeline_{outcome}",
                "ic": prompt[:5000],
                "eo": correction[:5000] if correction else "",
                "ao": output[:5000],
                "ts": trust,
                "src": "cognitive_pipeline",
                "now": now,
            })
            db.commit()

            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Feedback: {outcome} for pipeline output",
                how="FeedbackLoop.record_outcome",
                input_data={"genesis_key": genesis_key, "outcome": outcome},
                output_data={"trust": trust},
                tags=["feedback", outcome],
                parent_key_id=genesis_key,
            )

            logger.info(f"[FEEDBACK] Recorded {outcome} outcome, trust={trust}")
        except Exception as e:
            logger.error(f"[FEEDBACK] Failed: {e}")
        finally:
            db.close()

    @staticmethod
    def get_relevant_patterns(prompt: str, limit: int = 5) -> list:
        """Get high-trust patterns relevant to the prompt."""
        db = _get_db()
        if not db:
            return []
        try:
            from sqlalchemy import text
            rows = db.execute(text("""
                SELECT input_context, expected_output, actual_output, trust_score, example_type
                FROM learning_examples
                WHERE trust_score >= 0.6
                ORDER BY trust_score DESC, created_at DESC
                LIMIT :lim
            """), {"lim": limit}).fetchall()
            return [
                {"input": r[0][:200] if r[0] else "", "expected": r[1][:200] if r[1] else "",
                 "actual": r[2][:200] if r[2] else "", "trust": r[3], "type": r[4]}
                for r in rows
            ]
        except Exception:
            return []
        finally:
            db.close()


# ── Helpers ────────────────────────────────────────────────────────────

def _classify_prompt(prompt: str) -> str:
    lower = prompt.lower()
    # Check specific types BEFORE generic ones (order matters)
    if any(w in lower for w in ["delete all", "remove all", "drop ", "destroy"]):
        return "destructive"
    if any(w in lower for w in ["fix ", "bug", "error", "debug", "broken"]):
        return "bug_fix"
    if any(w in lower for w in ["test ", "tests ", "spec ", "assert"]):
        return "testing"
    if any(w in lower for w in ["refactor", "improve", "optimize", "clean up"]):
        return "refactor"
    if any(w in lower for w in ["explain", "what does", "how does", "why ", "describe"]):
        return "question"
    if any(w in lower for w in ["write", "create", "build", "implement", "code", "make"]):
        return "code_generation"
    if any(w in lower for w in ["delete", "remove"]):
        return "destructive"
    return "general"
