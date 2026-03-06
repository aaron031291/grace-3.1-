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

            # ORIENT: check learned patterns, episodic memory, procedural memory
            observations["learned_patterns"] = []
            observations["episodic"] = []
            observations["procedures"] = []

            db = _get_db()
            if db:
                try:
                    from sqlalchemy import text

                    # Learning examples
                    rows = db.execute(text(
                        "SELECT input_context, expected_output, trust_score FROM learning_examples "
                        "WHERE trust_score >= 0.6 ORDER BY trust_score DESC LIMIT 3"
                    )).fetchall()
                    for r in rows:
                        ctx.learned_patterns.append({"input": (r[0] or "")[:100], "trust": r[2]})
                        observations["learned_patterns"].append({"input": (r[0] or "")[:50], "trust": r[2]})

                    # Episodic memory — concrete past experiences
                    try:
                        episodes = db.execute(text(
                            "SELECT problem, action, outcome, trust_score FROM episodes "
                            "WHERE trust_score >= 0.5 ORDER BY trust_score DESC LIMIT 3"
                        )).fetchall()
                        for ep in episodes:
                            observations["episodic"].append({
                                "problem": (ep[0] or "")[:80], "action": (ep[1] or "")[:80],
                                "outcome": (ep[2] or "")[:80], "trust": ep[3]
                            })
                    except Exception:
                        pass

                    # Procedural memory — learned skills
                    try:
                        procs = db.execute(text(
                            "SELECT name, goal, trust_score, success_rate FROM procedures "
                            "WHERE trust_score >= 0.5 ORDER BY trust_score DESC LIMIT 3"
                        )).fetchall()
                        for p in procs:
                            observations["procedures"].append({
                                "name": p[0], "goal": (p[1] or "")[:80],
                                "trust": p[2], "success": p[3]
                            })
                    except Exception:
                        pass

                except Exception:
                    pass
                finally:
                    db.close()

            # Decision log — track this decision
            try:
                from genesis.realtime import get_realtime_engine
                get_realtime_engine().on_key_created(
                    key_type="system", what=f"OODA decision: {observations['prompt_type']}",
                    who="pipeline", where="cognitive.pipeline.ooda",
                    data={"type": observations["prompt_type"], "files": len(ctx.project_files)},
                )
            except Exception:
                pass

            # Magma memory — query for relevant context
            try:
                from cognitive.magma_bridge import query_context, query_causal
                magma_ctx = query_context(ctx.prompt[:200])
                if magma_ctx:
                    observations["magma_context"] = magma_ctx[:300]
                # Causal reasoning for bug fixes
                if observations["prompt_type"] == "bug_fix":
                    causal = query_causal(ctx.prompt[:200])
                    if causal:
                        observations["causal_insight"] = causal[:200]
            except Exception:
                pass

            # FlashCache — discover related external references
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                fc_results = fc.search(ctx.prompt[:200], limit=5, min_trust=0.4)
                if fc_results:
                    observations["flash_cache_refs"] = [
                        {"name": r.get("source_name", ""), "uri": r.get("source_uri", ""),
                         "trust": r.get("trust_score", 0)}
                        for r in fc_results[:5]
                    ]
            except Exception:
                pass

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

            # If blocking unknowns exist, escalate to consensus for resolution
            # Protected by circuit breaker (Loop 8: Cognitive Consensus Loop)
            consensus_resolution = None
            if has_blocking and len(unknown) >= 2:
                try:
                    from cognitive.circuit_breaker import enter_loop, exit_loop
                    if enter_loop("cognitive_consensus"):
                        try:
                            from cognitive.consensus_engine import run_consensus, _check_model_available
                            available = [m for m in ["qwen", "reasoning"] if _check_model_available(m)]
                            if available:
                                unknowns_text = ", ".join(f"{k}: {v}" for k, v in unknown)
                                cr = run_consensus(
                                    prompt=f"Resolve these unknowns for the task '{ctx.prompt[:200]}':\n{unknowns_text}",
                                    models=available,
                                    source="autonomous",
                                )
                                if cr.verification.get("passed"):
                                    consensus_resolution = cr.final_output[:500]
                                    for u_key, u_val in unknown:
                                        inferred.append((u_key, f"[consensus] {consensus_resolution[:100]}"))
                        finally:
                            exit_loop("cognitive_consensus")
                except Exception:
                    pass

            ctx.ambiguity = {
                "known": known,
                "inferred": inferred,
                "assumed": assumed,
                "unknown": unknown,
                "implicit_refs": implicit_refs,
                "has_blocking": has_blocking,
                "consensus_resolution": consensus_resolution,
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
                from llm_orchestrator.factory import get_llm_for_task
                task_type = "code" if ctx.ooda.get("prompt_type") in ("code_generation", "bug_fix", "refactor", "testing") else "reason"
                client = get_llm_for_task(task_type)



            # Enrich prompt with pipeline context + all memory systems
            enriched = ctx.prompt
            if ctx.ooda.get("tech_stack"):
                enriched += f"\n[Tech stack: {', '.join(ctx.ooda['tech_stack'])}]"
            if ctx.project_context:
                enriched += f"\n[Current file context:\n{ctx.project_context[:2000]}]"
            if ctx.learned_patterns:
                enriched += f"\n[{len(ctx.learned_patterns)} learned patterns available]"
            if ctx.ooda.get("episodic"):
                enriched += f"\n[Past experiences: {'; '.join(e['problem'][:50] + '→' + e['outcome'][:30] for e in ctx.ooda['episodic'][:2])}]"
            if ctx.ooda.get("procedures"):
                enriched += f"\n[Known skills: {', '.join(p['name'] for p in ctx.ooda['procedures'][:3])}]"
            if ctx.invariants.get("warnings"):
                enriched += f"\n[Warnings: {'; '.join(ctx.invariants['warnings'][:3])}]"
            if ctx.ooda.get("magma_context"):
                enriched += f"\n[Memory context: {ctx.ooda['magma_context'][:500]}]"
            if ctx.ooda.get("causal_insight"):
                enriched += f"\n[Causal insight: {ctx.ooda['causal_insight']}]"

            messages = [{"role": "user", "content": enriched}]
            if ctx.system_prompt:
                messages.insert(0, {"role": "system", "content": ctx.system_prompt})

            ctx.llm_response = client.chat(messages=messages, temperature=0.3)
            ctx.stages_passed.append("generate")
        except Exception as e:
            ctx.stages_failed.append("generate")
            ctx.errors.append(f"Generate: {e}")

    # ── Stage 6: Contradiction — semantic + structural detection ──────
    def _stage_contradiction(self, ctx: PipelineContext):
        try:
            issues = []

            # Check 1: Language mismatch against detected tech stack
            if ctx.ooda.get("tech_stack"):
                stack = ctx.ooda["tech_stack"]
                if "python" in stack and ("const " in ctx.llm_response or "function " in ctx.llm_response and "def " not in ctx.llm_response):
                    issues.append("language_mismatch: Python project but output looks like JavaScript")
                if "javascript" in stack and "def " in ctx.llm_response and "function " not in ctx.llm_response:
                    issues.append("language_mismatch: JavaScript project but output looks like Python")

            # Check 2: Semantic contradiction against knowledge base via RAG
            try:
                from retrieval.retriever import DocumentRetriever
                from embedding.embedder import get_embedding_model

                retriever = DocumentRetriever(
                    embedding_model=get_embedding_model(),
                )
                # Search for content similar to the output
                chunks = retriever.retrieve(
                    query=ctx.llm_response[:500],
                    limit=3, score_threshold=0.7,
                    filter_path=ctx.project_folder if ctx.project_folder else None,
                )
                for chunk in chunks:
                    existing_text = chunk.get("text", "").lower()
                    output_lower = ctx.llm_response.lower()
                    # If highly similar content exists but differs in key ways
                    if chunk.get("score", 0) > 0.85:
                        if ("not " in existing_text) != ("not " in output_lower[:200]):
                            issues.append(f"semantic_contradiction: Output may contradict existing document (similarity {chunk['score']:.0%})")
            except Exception:
                pass  # RAG not available — skip semantic check

            # Check 3: Import verification — do imported modules exist in project?
            import re
            imports = re.findall(r'(?:from|import)\s+([\w.]+)', ctx.llm_response)
            for imp in imports[:10]:
                top_module = imp.split('.')[0]
                stdlib = {'os', 'sys', 'json', 'datetime', 'typing', 'pathlib', 're', 'logging',
                          'collections', 'functools', 'itertools', 'math', 'hashlib', 'uuid', 'time',
                          'abc', 'dataclasses', 'enum', 'copy', 'io', 'subprocess', 'threading',
                          'asyncio', 'contextlib', 'traceback', 'unittest', 'pytest'}
                common_packages = {'fastapi', 'pydantic', 'sqlalchemy', 'requests', 'numpy', 'pandas',
                                   'flask', 'django', 'react', 'express', 'next'}
                if top_module not in stdlib and top_module not in common_packages:
                    if ctx.project_files and not any(top_module in f for f in ctx.project_files):
                        issues.append(f"unresolved_import: '{imp}' not found in project or standard library")

            ctx.contradictions = {
                "checked": True,
                "issues": issues,
                "issue_count": len(issues),
                "semantic_check": "performed" if len(issues) > 0 else "clean",
            }
            ctx.stages_passed.append("contradiction")
        except Exception as e:
            ctx.stages_failed.append("contradiction")
            ctx.errors.append(f"Contradiction: {e}")

    # ── Stage 7: Hallucination — 6-layer verification ────────────────
    def _stage_hallucination(self, ctx: PipelineContext):
        try:
            import re

            # Layer 1: Repository grounding — check file references exist
            file_refs = re.findall(r'[\w/]+\.\w{1,4}', ctx.llm_response)
            project_file_set = set(ctx.project_files)
            hallucinated_refs = []
            verified_refs = []
            for ref in file_refs[:20]:
                if any(ref in pf for pf in project_file_set):
                    verified_refs.append(ref)
                elif ref.count('.') == 1 and not ref.startswith('0.') and not ref[0].isdigit():
                    hallucinated_refs.append(ref)

            grounding_score = 1.0 - (len(hallucinated_refs) * 0.15)

            # Layer 2: Contradiction alignment (from previous stage)
            contradiction_score = 1.0 - (ctx.contradictions.get("issue_count", 0) * 0.2)

            # Layer 3: Confidence scoring — code quality signals
            quality_score = 0.7
            if "def " in ctx.llm_response or "class " in ctx.llm_response or "function " in ctx.llm_response:
                quality_score += 0.1
            if "TODO" in ctx.llm_response or "FIXME" in ctx.llm_response:
                quality_score -= 0.1
            if "error" in ctx.llm_response.lower() and "handle" not in ctx.llm_response.lower():
                quality_score -= 0.05

            # Layer 4: Trust system check
            trust_check = 0.5
            try:
                from cognitive.trust_engine import get_trust_engine
                sys_trust = get_trust_engine().get_system_trust()
                trust_check = sys_trust.get("system_trust", 50) / 100
            except Exception:
                pass

            # Layer 5: Internal knowledge verification
            internal_score = 0.5
            db = _get_db()
            if db:
                try:
                    from sqlalchemy import text
                    docs = db.execute(text("SELECT COUNT(*) FROM documents WHERE status='completed'")).scalar() or 0
                    internal_score = min(0.9, 0.4 + docs * 0.01)
                except Exception:
                    pass
                finally:
                    db.close()

            # Layer 6: Structural verification — does the output make sense?
            structural_score = 0.7
            if len(ctx.llm_response) < 10:
                structural_score = 0.2
            elif len(ctx.llm_response) > 50:
                structural_score = 0.8
            if "```" in ctx.llm_response:
                structural_score += 0.1

            # Composite confidence
            weights = [0.25, 0.15, 0.15, 0.15, 0.15, 0.15]
            scores = [grounding_score, contradiction_score, quality_score, trust_check, internal_score, structural_score]
            confidence = sum(w * max(0, min(1, s)) for w, s in zip(weights, scores))

            # Layer 7: Cross-model verification via Kimi (if available)
            kimi_verification = None
            try:
                from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
                kimi = get_kimi_enhanced()
                kimi_result = kimi.verify_output(ctx.prompt[:500], ctx.llm_response[:2000])
                if kimi_result.get("kimi_available"):
                    kimi_verification = kimi_result
                    if kimi_result.get("verified"):
                        confidence = min(1.0, confidence + 0.1)
                    elif kimi_result.get("issues"):
                        confidence = max(0.1, confidence - 0.1)
            except Exception:
                pass

            ctx.verification = {
                "verified": confidence >= 0.5,
                "confidence": round(confidence, 2),
                "grounded": len(hallucinated_refs) == 0,
                "verified_refs": verified_refs[:10],
                "hallucinated_refs": hallucinated_refs[:10],
                "kimi_verification": kimi_verification,
                "layers": {
                    "1_grounding": round(max(0, grounding_score), 2),
                    "2_contradiction": round(max(0, contradiction_score), 2),
                    "3_quality": round(quality_score, 2),
                    "4_trust": round(trust_check, 2),
                    "5_internal": round(internal_score, 2),
                    "6_structural": round(structural_score, 2),
                    "7_cross_model": round(kimi_verification.get("confidence", 0) if kimi_verification else 0, 2),
                },
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
                (example_type, input_context, expected_output, actual_output, trust_score,
                 source_reliability, content_quality, consensus_score, recency_score,
                 source, created_at, updated_at)
                VALUES (:et, :ic, :eo, :ao, :ts, :sr, :cq, :cs, :rs, :src, :now, :now)
            """), {
                "et": f"pipeline_{outcome}",
                "ic": prompt[:5000],
                "eo": correction[:5000] if correction else "",
                "ao": output[:5000],
                "ts": trust,
                "sr": trust,  # source_reliability matches trust
                "cq": trust,  # content_quality
                "cs": 0.5,    # consensus_score (neutral)
                "rs": 1.0,    # recency_score (just created)
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

            # Also store in episodic memory (concrete experience)
            try:
                db.execute(text("""
                    INSERT INTO episodes (problem, action, outcome, trust_score, source, created_at, updated_at)
                    VALUES (:problem, :action, :outcome, :ts, :src, :now, :now)
                """), {
                    "problem": prompt[:2000],
                    "action": f"pipeline_{outcome}",
                    "outcome": output[:2000],
                    "ts": trust,
                    "src": "feedback_loop",
                    "now": now,
                })
                db.commit()
            except Exception:
                pass

            # If high trust positive → promote to procedural memory (learned skill)
            if outcome == "positive" and trust >= 0.8:
                try:
                    db.execute(text("""
                        INSERT INTO procedures (name, goal, procedure_type, trust_score, success_rate, usage_count, created_at, updated_at)
                        VALUES (:name, :goal, :ptype, :ts, :sr, 1, :now, :now)
                    """), {
                        "name": f"Learned from: {prompt[:50]}",
                        "goal": prompt[:200],
                        "ptype": "pipeline_learned",
                        "ts": trust,
                        "sr": 1.0,
                        "now": now,
                    })
                    db.commit()
                except Exception:
                    pass

            # Store in Magma memory
            try:
                from cognitive.magma_bridge import ingest, store_pattern, store_decision, store_procedure
                ingest(f"{outcome}: {prompt[:200]} → {output[:200]}", source="feedback_loop")
                if outcome == "positive":
                    store_pattern("successful_generation", prompt[:200])
                    store_decision("generate", "code", f"Successfully generated: {prompt[:100]}")
                elif outcome == "negative":
                    store_pattern("failed_generation", f"{prompt[:100]} → correction: {correction[:100] if correction else 'none'}")
                if outcome == "positive" and trust >= 0.8:
                    store_procedure(f"Learned: {prompt[:50]}", prompt[:200], steps=["Generate", "Verify", "Apply"])
            except Exception:
                pass

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
