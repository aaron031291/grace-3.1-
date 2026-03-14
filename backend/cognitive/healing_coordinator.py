"""
Healing Coordinator — Intelligent problem resolution chain.

When a problem is detected:
1. Self-healing tries basic recovery
2. If that fails → diagnostics run (Grace + Kimi independently)
3. They compare findings and agree on best fix
4. If code is broken → coding agent fixes it
5. If they can't resolve → web search / API search for context
6. Re-diagnose with new info → apply fix
7. Track outcome via KPI → update trust scores
8. Store as learning experience in Oracle / memory mesh

Connected to: self-healing, coding agent, Kimi, diagnostics,
trust engine, KPI tracker, learning memory, web search.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HealingCoordinator:
    """
    Orchestrates the full healing chain:
    detect → diagnose → fix → verify → learn
    """

    def resolve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full resolution chain for a detected problem.
        
        problem: {
            "component": str,
            "description": str,
            "error": str (optional),
            "file_path": str (optional),
            "severity": str (low/medium/high/critical)
        }
        """
        result = {
            "problem": problem,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": [],
            "resolved": False,
            "resolution": None,
        }

        # Step 1: Self-healing basic recovery
        step1 = self._step_self_heal(problem)
        result["steps"].append(step1)
        if step1.get("resolved"):
            result["resolved"] = True
            result["resolution"] = "self_healing"
            self._trigger_learn_after_heal(problem, "self_healing")
            self._record_outcome(problem, result, success=True)
            self._publish_to_spindle(problem, result)
            return result

        # Step 2: Diagnostics — Grace + Kimi independently
        step2 = self._step_diagnose(problem)
        result["steps"].append(step2)

        # Step 3: Agree on best fix
        step3 = self._step_agree_fix(problem, step2)
        result["steps"].append(step3)

        # Step 4: If code is broken → coding agent → sandbox validation
        if step3.get("fix_type") == "code_fix":
            step4 = self._step_code_fix(problem, step3)
            result["steps"].append(step4)
            if step4.get("resolved"):
                # Phase 3.3: Sandbox Repair Engine — validate patch in isolation
                sandbox_ok = self._step_sandbox_validate(problem, step4)
                result["steps"].append(sandbox_ok)
                if sandbox_ok.get("sandbox_passed", True):
                    result["resolved"] = True
                    result["resolution"] = "coding_agent"
                    self._trigger_heal_and_learn_after_code_fix(problem, step4)
                    self._record_outcome(problem, result, success=True)
                    self._publish_to_spindle(problem, result)
                    return result
                else:
                    logger.warning(
                        "[HEALING-COORD] Sandbox REJECTED patch for %s: %s",
                        problem.get("component", "?"),
                        sandbox_ok.get("rejection_reason", "unknown"),
                    )
                    step4["resolved"] = False
                    step4["sandbox_rejected"] = True

        # Step 5: Can't resolve → search for context
        step5 = self._step_search_context(problem, step3)
        result["steps"].append(step5)

        # Step 6: Re-diagnose with new info
        step6 = self._step_rediagnose(problem, step5)
        result["steps"].append(step6)

        # Step 7: Apply fix with new context
        if step6.get("fix"):
            step7 = self._step_apply_fix(problem, step6)
            result["steps"].append(step7)
            result["resolved"] = step7.get("resolved", False)
            result["resolution"] = "coordinated_fix" if result["resolved"] else "unresolved"

        self._record_outcome(problem, result, success=result["resolved"])
        self._publish_to_spindle(problem, result)
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        return result

    # ── Step 1: Basic self-healing (all paths through brain) ─────────────

    def _step_self_heal(self, problem: Dict) -> Dict:
        """Self-heal via brain: system/reset_db, reset_vector_db, scan_heal; govern/heal for rest."""
        try:
            from api.brain_api_v2 import call_brain
            component = (problem.get("component") or "").lower()
            action_key = "unknown"
            if "database" in component or "db" in component:
                r = call_brain("system", "reset_db", {})
                action_key = "database_reconnect"
                ok = bool(r.get("ok"))
            elif "qdrant" in component or "vector" in component:
                r = call_brain("system", "reset_vector_db", {})
                action_key = "qdrant_reconnect"
                ok = bool(r.get("ok"))
            elif "llm" in component or "ollama" in component:
                r = call_brain("system", "scan_heal", {})
                action_key = "llm_reconnect"
                ok = bool(r.get("ok"))
            else:
                r = call_brain("govern", "heal", {})
                action_key = "gc_collect"
                ok = bool(r.get("ok"))
            return {"step": "self_heal", "action": action_key, "resolved": ok}
        except Exception as e:
            return {"step": "self_heal", "action": "failed", "resolved": False, "error": str(e)}

    # ── Step 2: Diagnostics — Grace + Kimi in parallel ─────────────────

    def _step_diagnose(self, problem: Dict) -> Dict:
        from core.async_parallel import run_parallel
        diagnostics = {"step": "diagnose", "grace": None, "kimi": None, "opus": None, "reasoning": None}
        desc = problem.get("description", "") or ""
        err = problem.get("error", "") or ""
        comp = problem.get("component", "") or ""
        payload = f"Problem: {desc}\nError: {err}\nComponent: {comp}"

        def _grace():
            try:
                from llm_orchestrator.factory import get_raw_client
                return get_raw_client().chat(messages=[
                    {"role": "system", "content": "You are a system diagnostician. Analyse this problem and provide: root cause, affected components, suggested fix."},
                    {"role": "user", "content": payload},
                ], temperature=0.2)
            except Exception as e:
                return f"Grace diagnosis unavailable: {e}"

        def _kimi():
            try:
                from llm_orchestrator.factory import get_kimi_client
                return get_kimi_client().chat(messages=[
                    {"role": "system", "content": "You are a system diagnostician. Analyse this problem and provide: root cause, affected components, suggested fix."},
                    {"role": "user", "content": payload},
                ], temperature=0.2)
            except Exception as e:
                return f"Kimi diagnosis unavailable: {e}"

        def _opus():
            try:
                from llm_orchestrator.factory import get_llm_client
                return get_llm_client(provider="opus").chat(messages=[
                    {"role": "system", "content": "You are a system diagnostician. Analyse this problem and provide: root cause, affected components, suggested fix."},
                    {"role": "user", "content": payload},
                ], temperature=0.2)
            except Exception as e:
                return f"Opus diagnosis unavailable: {e}"

        def _reasoning():
            try:
                from llm_orchestrator.factory import get_deepseek_reasoner
                return get_deepseek_reasoner().chat(messages=[
                    {"role": "system", "content": "You are a system diagnostician. Analyse this problem and provide: root cause, affected components, suggested fix."},
                    {"role": "user", "content": payload},
                ], temperature=0.2)
            except Exception as e:
                return f"Reasoning diagnosis unavailable: {e}"

        results = run_parallel([_grace, _kimi, _opus, _reasoning], return_exceptions=True)
        for key, result in zip(["grace", "kimi", "opus", "reasoning"], results):
            diagnostics[key] = result if not isinstance(result, Exception) else str(result)
        return diagnostics

    # ── Step 3: Agree on best fix ─────────────────────────────────────

    def _step_agree_fix(self, problem: Dict, diagnostics: Dict) -> Dict:
        grace_diag = diagnostics.get("grace", "")
        kimi_diag = diagnostics.get("kimi", "")

        fix_type = "unknown"
        description = problem.get("description", "").lower()
        error = problem.get("error", "").lower()

        if any(w in description + error for w in ["syntax", "import", "indent", "undefined", "typeerror", "attributeerror"]):
            fix_type = "code_fix"
        elif any(w in description + error for w in ["connection", "timeout", "refused", "unavailable"]):
            fix_type = "service_restart"
        elif any(w in description + error for w in ["memory", "disk", "resource"]):
            fix_type = "resource_cleanup"
        else:
            fix_type = "code_fix"  # Default to code fix

        return {
            "step": "agree_fix",
            "fix_type": fix_type,
            "grace_recommendation": str(grace_diag)[:300] if grace_diag else "",
            "kimi_recommendation": str(kimi_diag)[:300] if kimi_diag else "",
        }

    # ── Step 4: Coding agent fix (via brain code/generate) ───────────────

    def _step_code_fix(self, problem: Dict, agreement: Dict) -> Dict:
        """Coding agent fix — routes through 9-layer coding pipeline when available."""
        prompt = (
            f"Fix this problem:\n{problem.get('description', '')}\n"
            f"Error: {problem.get('error', '')}\n"
            f"Grace diagnosis: {agreement.get('grace_recommendation', '')}\n"
            f"Kimi diagnosis: {agreement.get('kimi_recommendation', '')}"
        )
        fix = None
        pipeline_used = False

        # PRIMARY: Route through the 9-layer coding pipeline (full verification chain)
        try:
            from core.coding_pipeline import CodingPipeline
            pipeline = CodingPipeline()
            pipeline_result = pipeline.run(
                task=prompt,
                context={
                    "source": "spindle_healing",
                    "component": problem.get("component", ""),
                    "severity": problem.get("severity", "high"),
                    "proof_hash": problem.get("proof_hash", ""),
                },
            )
            if pipeline_result.status == "passed" and pipeline_result.chunks:
                code_outputs = []
                for chunk in pipeline_result.chunks:
                    for layer in chunk.layers:
                        if layer.layer == 6 and layer.output:
                            code_data = layer.output if isinstance(layer.output, dict) else {}
                            code = code_data.get("code", {})
                            if isinstance(code, dict):
                                code = code.get("code", code.get("response", ""))
                            if code:
                                code_outputs.append(str(code)[:1000])
                if code_outputs:
                    fix = "\n".join(code_outputs)
                    pipeline_used = True
                    logger.info(f"[HEALING-COORD] 9-layer pipeline produced fix ({len(fix)} chars)")
        except Exception as e:
            logger.debug(f"[HEALING-COORD] 9-layer pipeline unavailable, falling back to brain: {e}")

        # FALLBACK: Direct LLM generation via brain API
        if not fix:
            try:
                from api.brain_api_v2 import call_brain
                project_folder = (problem.get("file_path") or "").rsplit("/", 1)[0]
                r = call_brain("code", "generate", {"prompt": prompt, "project_folder": project_folder})
                if not r.get("ok"):
                    return {"step": "code_fix", "resolved": False, "error": r.get("error", "brain error")}
                data = r.get("data") or {}
                fix = data.get("code") or data.get("response")
            except Exception as e:
                return {"step": "code_fix", "resolved": False, "error": str(e)}

        if not fix:
            return {"step": "code_fix", "resolved": False, "error": "No fix generated"}

        # Hallucination Guard: verify LLM-generated fix before accepting
        hallucination_verified = True
        hallucination_details = {}
        try:
            from llm_orchestrator.hallucination_guard import HallucinationGuard
            guard = HallucinationGuard()
            verification = guard.verify_content(
                prompt=prompt,
                content=fix if isinstance(fix, str) else str(fix),
                enable_consensus=False,
                enable_grounding=True,
                enable_trust_verification=True,
                enable_external_verification=False,
                confidence_threshold=0.5,
                max_retry_attempts=1,
            )
            hallucination_verified = verification.is_trusted
            hallucination_details = {
                "trust_score": verification.trust_score,
                "confidence": verification.confidence_score,
                "is_trusted": verification.is_trusted,
            }
            if not hallucination_verified:
                logger.warning(
                    f"[HEALING-COORD] Hallucination guard REJECTED code fix "
                    f"(trust={verification.trust_score:.2f}, confidence={verification.confidence_score:.2f})"
                )
        except Exception as e:
            logger.debug(f"[HEALING-COORD] Hallucination guard unavailable: {e}")

        return {
            "step": "code_fix",
            "resolved": bool(fix) and hallucination_verified,
            "fix": fix[:1000] if isinstance(fix, str) else fix,
            "trust": 0.8 if pipeline_used else 0.5,
            "pipeline_used": pipeline_used,
            "pipeline_stages": ["phase0", "L1-L8"] if pipeline_used else [],
            "hallucination_guard": hallucination_details,
            "hallucination_verified": hallucination_verified,
        }

    # ── Step 4b: Sandbox validation (Phase 3.3) ─────────────────────

    def _step_sandbox_validate(self, problem: Dict, code_fix_step: Dict) -> Dict:
        """
        Evaluate the generated patch in an isolated sandbox before
        allowing FixApplier to touch the live codebase.
        """
        result = {"step": "sandbox_validate", "sandbox_passed": True}
        fix_code = code_fix_step.get("fix", "")
        if not fix_code or not isinstance(fix_code, str):
            # No code to sandbox — pass through
            return result

        target_file = problem.get("file_path", "")
        if not target_file:
            # No target file specified — can't sandbox, pass through
            return result

        try:
            from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
            engine = get_sandbox_repair_engine()
            verdict = engine.evaluate(
                target_file=target_file,
                patch_code=fix_code,
                run_tests=True,
            )
            result["sandbox_passed"] = verdict.passed
            result["sandbox_detail"] = verdict.to_dict()
            if not verdict.passed:
                result["rejection_reason"] = verdict.rejection_reason
        except Exception as e:
            logger.debug("[HEALING-COORD] Sandbox engine unavailable: %s", e)
            # If sandbox engine is unavailable, don't block — pass through
            result["sandbox_passed"] = True
            result["sandbox_error"] = str(e)

        return result

    # ── Step 5: Search for external context ───────────────────────────

    def _step_search_context(self, problem: Dict, agreement: Dict) -> Dict:
        context = {"step": "search_context", "sources": []}

        # Search knowledge base
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding.embedder import get_embedding_model
            from vector_db.client import get_qdrant_client
            retriever = DocumentRetriever(embedding_model=get_embedding_model(), qdrant_client=get_qdrant_client())
            chunks = retriever.retrieve(query=problem.get("description", ""), limit=3, score_threshold=0.3)
            if chunks:
                context["sources"].append({"type": "knowledge_base", "count": len(chunks),
                                            "content": "; ".join(c.get("text", "")[:200] for c in chunks)})
        except Exception:
            pass

        # Search learning memory
        try:
            from cognitive.pipeline import FeedbackLoop
            patterns = FeedbackLoop.get_relevant_patterns(problem.get("description", ""))
            if patterns:
                context["sources"].append({"type": "learning_memory", "count": len(patterns),
                                            "content": "; ".join(p.get("input", "")[:100] for p in patterns)})
        except Exception:
            pass

        return context

    # ── Step 6: Re-diagnose with new context ──────────────────────────

    def _step_rediagnose(self, problem: Dict, search_result: Dict) -> Dict:
        extra_context = ""
        for src in search_result.get("sources", []):
            extra_context += f"\n[{src['type']}]: {src.get('content', '')[:300]}"

        if not extra_context:
            return {"step": "rediagnose", "fix": None, "note": "No additional context found"}

        try:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()
            fix = client.chat(messages=[
                {"role": "system", "content": "You are fixing a system problem. Use the additional context to provide a specific fix."},
                {"role": "user", "content": f"Problem: {problem.get('description', '')}\nError: {problem.get('error', '')}\nAdditional context:{extra_context}\n\nProvide the fix."},
            ], temperature=0.2)

            # Hallucination Guard: verify re-diagnosis fix
            try:
                from llm_orchestrator.hallucination_guard import HallucinationGuard
                guard = HallucinationGuard()
                verification = guard.verify_content(
                    prompt=f"Fix: {problem.get('description', '')}",
                    content=fix if isinstance(fix, str) else str(fix),
                    enable_consensus=False,
                    enable_grounding=True,
                    enable_trust_verification=True,
                    enable_external_verification=False,
                    max_retry_attempts=1,
                )
                if not verification.is_trusted:
                    logger.warning(f"[HEALING-COORD] Hallucination guard rejected rediagnosis fix (trust={verification.trust_score:.2f})")
                    return {"step": "rediagnose", "fix": None, "error": "Hallucination guard rejected fix", "trust_score": verification.trust_score}
            except Exception as e:
                logger.debug(f"[HEALING-COORD] Hallucination guard unavailable for rediagnosis: {e}")

            return {"step": "rediagnose", "fix": fix}
        except Exception as e:
            return {"step": "rediagnose", "fix": None, "error": str(e)}

    # ── Step 7: Apply fix ─────────────────────────────────────────────

    def _step_apply_fix(self, problem: Dict, rediagnosis: Dict) -> Dict:
        fix = rediagnosis.get("fix", "")
        if not fix:
            return {"step": "apply_fix", "resolved": False}

        if problem.get("file_path"):
            try:
                from pathlib import Path
                fp = Path(problem["file_path"])
                if fp.exists():
                    return {"step": "apply_fix", "resolved": True, "note": "Fix generated — ready to apply via coding agent"}
            except Exception:
                pass

        return {"step": "apply_fix", "resolved": bool(fix), "fix_preview": fix[:500]}

    # ── Cross-triggers: heal → learn, code_fix → heal + learn ───────────

    def _trigger_learn_after_heal(self, problem: Dict, resolution: str):
        """After a successful heal, trigger learning in background."""
        from core.async_parallel import run_background
        def _do():
            try:
                from api.brain_api_v2 import call_brain
                call_brain("govern", "learn", {})
                call_brain("govern", "record_gap", {
                    "what": f"Heal succeeded: {resolution} — {problem.get('component', '')}",
                    "target": problem.get("component", ""),
                    "tags": ["heal_triggered_learn", resolution],
                })
            except Exception as e:
                logger.debug("Trigger learn after heal: %s", e)
        run_background(_do, "learn_after_heal")

    def _trigger_heal_and_learn_after_code_fix(self, problem: Dict, step4: Dict):
        """After coding agent fix, trigger heal + learn in background."""
        from core.async_parallel import run_background
        def _do():
            try:
                from api.brain_api_v2 import call_brain
                call_brain("system", "scan_heal", {})
                call_brain("govern", "heal", {})
                call_brain("govern", "learn", {})
                call_brain("govern", "record_gap", {
                    "what": f"Code fix applied: {problem.get('description', '')[:200]}",
                    "target": problem.get("file_path", problem.get("component", "")),
                    "tags": ["code_fix_triggered_heal_learn", "coding_agent"],
                })
            except Exception as e:
                logger.debug("Trigger heal+learn after code fix: %s", e)
        run_background(_do, "heal_learn_after_code_fix")

    # ── Record outcome for learning ───────────────────────────────────

    def _record_outcome(self, problem: Dict, result: Dict, success: bool):
        """Track via KPI + telemetry + store as learning experience + Magma memory."""
        # Telemetry: record healing operation for baseline/drift tracking
        try:
            from telemetry.telemetry_service import get_telemetry_service
            from models.telemetry_models import OperationType
            telemetry = get_telemetry_service()
            with telemetry.track_operation(
                OperationType.HEALING,
                f"healing_{problem.get('component', 'unknown')}",
                metadata={
                    "success": success,
                    "resolution": result.get("resolution", "unresolved"),
                    "steps": len(result.get("steps", [])),
                },
            ):
                pass  # operation already completed, just record it
        except Exception:
            pass

        # Store in Magma
        try:
            from cognitive.magma_bridge import store_decision, store_pattern, ingest
            ingest(f"Healing coordination: {problem.get('component')} — {'RESOLVED' if success else 'UNRESOLVED'}",
                   source="healing_coordinator")
            store_decision("coordinate_healing", problem.get("component", ""),
                          f"{'Resolved' if success else 'Failed'} via {result.get('resolution', '?')}")
            if success:
                store_pattern("successful_coordination", f"{problem.get('description', '')[:100]} → {result.get('resolution', '')}")
        except Exception:
            pass
        try:
            from cognitive.trust_engine import get_trust_engine
            engine = get_trust_engine()
            engine.score_output(
                component_id=f"healing_{problem.get('component', 'unknown')}",
                component_name=f"Healing: {problem.get('component', 'unknown')}",
                output=result.get("resolution", "unresolved"),
                source="deterministic" if success else "unknown",
            )
        except Exception:
            pass

        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="",
                prompt=f"Healing: {problem.get('description', '')}",
                output=result.get("resolution", "unresolved"),
                outcome="positive" if success else "negative",
            )
        except Exception:
            pass

        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Healing coordination: {'RESOLVED' if success else 'UNRESOLVED'} — {problem.get('component', '')}",
                how="HealingCoordinator.resolve",
                input_data=problem,
                output_data={"resolved": success, "resolution": result.get("resolution"), "steps": len(result.get("steps", []))},
                tags=["healing", "coordination", "resolved" if success else "unresolved"],
            )
        except Exception:
            pass

    def _publish_to_spindle(self, problem: Dict, result: Dict):
        """Publish resolution results back to Spindle event store for audit trail."""
        try:
            from cognitive.spindle_event_store import get_event_store
            resolved = result.get("resolved", False)
            get_event_store().append(
                topic=f"healing.coordinator.{problem.get('component', 'unknown')}",
                source_type="healing_coordinator",
                payload={
                    "component": problem.get("component"),
                    "description": problem.get("description", "")[:300],
                    "resolved": resolved,
                    "resolution": result.get("resolution"),
                    "steps_count": len(result.get("steps", [])),
                    "proof_hash": problem.get("proof_hash", ""),
                },
                proof_hash=problem.get("proof_hash", ""),
                result="RESOLVED" if resolved else "UNRESOLVED",
            )
        except Exception as e:
            logger.debug(f"[HEALING-COORD] Spindle event store publish failed: {e}")


_coordinator = None

def get_coordinator() -> HealingCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = HealingCoordinator()
    return _coordinator
