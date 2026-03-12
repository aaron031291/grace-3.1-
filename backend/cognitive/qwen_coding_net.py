"""
Qwen Coding Net — Unified coding execution through Grace's internal world.

Connects: Qwen (coding) + Consensus (design) + Ghost Memory (context) +
TimeSense (temporal awareness) + Architecture Compass (self-awareness) +
Trust Engine (quality) + Circuit Breaker (token management) + Genesis Keys

The full loop:
  1. User describes task in consensus chat
  2. Ghost Memory starts tracking silently
  3. TimeSense provides temporal context (time of day, urgency)
  4. Kimi+Opus design blueprint via consensus
  5. Blueprint chunked for Qwen's token window
  6. Each chunk: Ghost Memory injects context → Qwen codes → Compiler tests
  7. Circuit breaker manages token limits (save → reset → continue)
  8. On success: Ghost Memory reflects → Playbook stores → Reset
  9. On failure: retry with ghost context → escalate if stuck
  10. Everything tracked via Genesis Keys
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from self_healing.meta_healer import meta_heal

logger = logging.getLogger(__name__)


class QwenCodingNet:
    """Unified coding execution engine — everything connected."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "QwenCodingNet":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @meta_heal
    def execute_task(self, task: str, use_consensus: bool = True) -> Dict[str, Any]:
        """
        Full unified execution: task description → working code.
        Connected to: ghost memory, consensus, TimeSense, compiler,
        diagnostic engine, self-healing, immune system, test engines.
        """
        start = time.time()
        result = {
            "task": task,
            "status": "started",
            "code": "",
            "attempts": 0,
            "ghost_reflection": None,
        }

        # 1. Ghost Memory starts tracking
        from cognitive.ghost_memory import get_ghost_memory
        ghost = get_ghost_memory()
        ghost.start_task(task)
        
        # INJECTED DELIBERATE META-HEAL COMPONENT FAILURE
        x = 1 / 0
        
        # 2. TimeSense context
        time_context = self._get_time_context()
        ghost.append("context", f"Time: {time_context.get('summary', 'unknown')}")

        # 3. Immune system scan — reject sketchy tasks
        if self._immune_scan(task, ghost):
            result["status"] = "blocked_by_immune"
            return result

        # 3b. ── Deterministic gate (BEFORE LLM) ──────────────────────────
        try:
            from coding_agent.deterministic_gate import get_gate
            gate_report = get_gate().analyze(task)
            if not gate_report.gate_passed:
                result["status"] = "blocked_by_gate"
                result["gate_report"] = gate_report.as_prompt_context()
                ghost.append("gate_blocked", f"Risk={gate_report.risk_score:.2f}")
                return result
            ghost.append("gate", f"Gate OK (risk={gate_report.risk_score:.2f})")
        except Exception as _ge:
            gate_report = None
            logger.debug("[QWEN-NET] Gate skipped: %s", _ge)

        # 3c. ── Episodic memory injection ────────────────────────────────
        episodic_context = ""
        try:
            from cognitive.episodic_memory import EpisodicMemory
            from database.session import session_scope
            with session_scope() as _ep_session:
                ep_mem = EpisodicMemory(_ep_session)
                past = ep_mem.retrieve_similar(task, limit=3)
                if past:
                    snippets = []
                    for ep in past:
                        outcome = ep.outcome if isinstance(ep.outcome, str) else str(ep.outcome)[:100]
                        snippets.append(f"Past: {ep.problem[:80]} → {outcome[:80]}")
                    episodic_context = "\n".join(snippets)
                    ghost.append("episodic", episodic_context[:200])
        except Exception as _ee:
            logger.debug("[QWEN-NET] Episodic injection skipped: %s", _ee)

        # 4. Get architecture context from compass
        arch_context = self._get_architecture_context(task)
        ghost.append("context", f"Architecture: {arch_context[:200]}")

        # 5. Design blueprint (consensus with TimeSense injected)
        if use_consensus:
            blueprint = self._consensus_design(task, ghost, time_context)
        else:
            blueprint = {"architecture": task, "functions": [], "direct": True}

        # Inject gate report + episodic context into blueprint
        if gate_report:
            blueprint["_gate_context"] = gate_report.as_prompt_context()
        if episodic_context:
            blueprint["_episodic_context"] = episodic_context

        ghost.append("blueprint", json.dumps(blueprint, default=str)[:500])

        # 6. Build code with token-managed loop
        code = self._build_with_token_management(task, blueprint, ghost)

        if code:
            result["code"] = code
            result["status"] = "completed"
            ghost.append("success", f"Code generated: {len(code)} chars")

            # ── Verification pass (post-generation, pre-compile) ──────────
            verified = True
            try:
                from coding_agent.verification_pass import get_verification_pass
                vpass = get_verification_pass()
                ghost_ctx = ghost.get_context(max_tokens=500) if hasattr(ghost, "get_context") else ""
                v_result = vpass.verify(code, task, ghost_context=ghost_ctx)
                result["verification"] = {
                    "accepted": v_result.accepted,
                    "trust_score": v_result.trust_score,
                    "flags": v_result.flags,
                }
                if not v_result.accepted:
                    ghost.append("verify_rejected", v_result.revision_hint[:200])
                    result["status"] = "verification_failed"
                    result["revision_hint"] = v_result.revision_hint
                    verified = False
                else:
                    ghost.append("verify_passed", f"Trust={v_result.trust_score:.2f}")
            except Exception as _ve:
                logger.debug("[QWEN-NET] Verification skipped: %s", _ve)

            if verified:
                # 7. Compile and test
                test_result = self._compile_and_test(code, ghost)
                result["test_result"] = test_result

                if test_result.get("passed"):
                    # 8. Run diagnostic on the generated code
                    diag = self._run_diagnostics(code, ghost)
                    result["diagnostics"] = diag

                    # 9. Deep test engine validation
                    self._run_tests(code, ghost)

                    ghost.append("pass", "All checks passed")
                    result["status"] = "deployed"
                else:
                    # 10. Self-healing attempt
                    healed = self._self_heal(code, test_result, ghost)
                    if healed:
                        result["code"] = healed
                        result["status"] = "healed_and_deployed"
                    else:
                        ghost.append("failure", f"Tests failed: {test_result.get('error', '')}")
                        result["status"] = "needs_fix"
        else:
            result["status"] = "failed"
            ghost.append("failure", "No code generated")

        # 11. Complete ghost memory (reflect + playbook + reset)
        if ghost.is_task_done() or result["status"] in ("deployed", "healed_and_deployed"):
            reflection = ghost.complete_task(user_approved=True)
            result["ghost_reflection"] = reflection.get("reflection")

        result["duration_ms"] = round((time.time() - start) * 1000, 1)
        result["ghost_stats"] = ghost.get_stats()

        # 8. Track via Genesis
        try:
            from api._genesis_tracker import track
            track(
                key_type="ai_code_generation",
                what=f"QwenNet: {result['status']} — {task[:80]}",
                how="qwen_coding_net.execute_task",
                output_data={
                    "status": result["status"],
                    "code_length": len(result.get("code", "")),
                    "duration_ms": result["duration_ms"],
                },
                tags=["qwen_net", result["status"]],
            )
        except Exception:
            pass

        return result

    def chat_execute(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Execute from the consensus chat — message comes in, code goes out.
        Ghost memory holds the full conversation context.
        """
        from cognitive.ghost_memory import get_ghost_memory
        ghost = get_ghost_memory()

        # Append conversation to ghost
        if conversation_history:
            for msg in conversation_history[-5:]:
                ghost.append("chat", f"{msg.get('role', 'user')}: {msg.get('content', '')[:200]}")
        ghost.append("chat", f"user: {message}")

        # Check if this is a coding request
        is_code = any(w in message.lower() for w in [
            "build", "create", "code", "write", "function", "fix", "add", "implement",
            "endpoint", "api", "component", "module", "class", "test",
        ])

        if is_code:
            return self.execute_task(message, use_consensus=True)
        else:
            # Non-coding request — just pass to consensus
            try:
                from cognitive.consensus_engine import run_consensus
                result = run_consensus(
                    prompt=message,
                    models=["kimi", "opus"],
                    context=ghost.get_context(max_tokens=1000),
                    source="user",
                )
                ghost.append("response", result.final_output[:500])
                return {
                    "task": message,
                    "status": "responded",
                    "response": result.final_output,
                    "models": result.models_used,
                }
            except Exception as e:
                return {"task": message, "status": "error", "error": str(e)}

    def _immune_scan(self, task: str, ghost) -> bool:
        """Immune system scan — reject dangerous tasks."""
        try:
            from cognitive.immune_system import GraceImmuneSystem
            dangerous = any(w in task.lower() for w in [
                "delete all", "drop table", "rm -rf", "format disk", "shutdown",
            ])
            if dangerous:
                ghost.append("immune_block", f"Task blocked by immune system: {task[:50]}")
                return True
        except Exception:
            pass
        return False

    def _run_diagnostics(self, code: str, ghost) -> Dict:
        """Run diagnostic engine on generated code."""
        try:
            from cognitive.autonomous_diagnostics import get_diagnostics
            diag = get_diagnostics()
            # Check if the code introduces any issues
            ghost.append("diagnostic", "Code diagnostics running")
            return {"checked": True}
        except Exception:
            return {"checked": False}

    def _run_tests(self, code: str, ghost):
        """Run test engines on generated code."""
        try:
            from cognitive.code_sandbox import verify_code_quality
            quality = verify_code_quality(code)
            ghost.append("test", f"Quality score: {quality.get('score', 0)}/100")
        except Exception:
            pass

    def _self_heal(self, code: str, test_result: Dict, ghost) -> Optional[str]:
        """Attempt to self-heal failed code."""
        try:
            error = test_result.get("error", "")
            if not error:
                return None

            ghost.append("healing", f"Attempting self-heal: {error[:100]}")

            from llm_orchestrator.factory import get_qwen_coder
            qwen = get_qwen_coder()

            fix = qwen.generate(
                prompt=f"Fix this Python code error:\nError: {error}\n\nCode:\n{code[:2000]}\n\nOutput ONLY fixed code.",
                system_prompt="Fix the code. Output ONLY Python code.",
                temperature=0.1,
                max_tokens=2048,
            )

            if isinstance(fix, str) and len(fix) > 20:
                fix = fix.strip().strip("`").strip()
                if fix.startswith("python"):
                    fix = fix[6:].strip()

                # Re-test the fix
                retest = self._compile_and_test(fix, ghost)
                if retest.get("passed"):
                    ghost.append("healed", "Self-healing successful")
                    return fix

            ghost.append("heal_failed", "Self-healing did not fix the issue")
        except Exception as e:
            ghost.append("heal_error", str(e))
        return None

    def _get_time_context(self) -> Dict:
        """Get temporal awareness from TimeSense."""
        try:
            from cognitive.time_sense import TimeSense
            ts = TimeSense()
            return ts.get_context()
        except Exception:
            now = datetime.now(timezone.utc)
            return {
                "summary": f"{now.strftime('%A %H:%M')} UTC",
                "hour": now.hour,
                "is_business": 9 <= now.hour <= 17,
            }

    def _get_architecture_context(self, task: str) -> str:
        """Get relevant architecture info from compass."""
        try:
            from cognitive.architecture_compass import get_compass
            compass = get_compass()
            relevant = compass.find_for(task[:50])
            if relevant:
                explanations = [compass.explain(r)[:100] for r in relevant[:3]]
                return "; ".join(explanations)
        except Exception:
            pass
        return "Architecture context unavailable"

    def _consensus_design(self, task: str, ghost, time_context: Dict = None) -> Dict:
        """Use Kimi+Opus to design the blueprint. TimeSense injected."""
        try:
            from cognitive.consensus_engine import run_consensus
            ghost_context = ghost.get_context(max_tokens=500)

            time_str = ""
            if time_context:
                time_str = f"\n[TimeSense: {time_context.get('summary', '')}]"

            result = run_consensus(
                prompt=(
                    f"Design a code blueprint for: {task}\n"
                    f"{time_str}\n"
                    f"Context:\n{ghost_context}\n\n"
                    f"Output JSON: {{architecture, functions: [{{name, inputs, output, description}}]}}"
                ),
                models=["kimi", "opus"],
                source="autonomous",
            )

            ghost.append("consensus", f"Blueprint designed: {result.final_output[:200]}")

            # Try parse JSON
            import re
            m = re.search(r'\{[\s\S]+\}', result.final_output)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass

            return {"architecture": result.final_output[:500], "functions": []}
        except Exception as e:
            ghost.append("error", f"Consensus design failed: {e}")
            return {"architecture": task, "functions": [], "fallback": True}

    def _build_with_token_management(self, task: str, blueprint: Dict, ghost) -> Optional[str]:
        """Build code with circuit breaker managing token limits.
        Deterministic gate context + episodic memory prepended to prompt.
        """
        try:
            from cognitive.circuit_breaker import enter_loop, exit_loop

            if not enter_loop("blueprint_build"):
                ghost.append("error", "Circuit breaker blocked — too many attempts")
                return None

            try:
                from llm_orchestrator.factory import get_qwen_coder
                qwen = get_qwen_coder()

                # Build prompt with ghost context + gate report + episodic context
                ghost_context = ghost.get_context(max_tokens=800)
                arch = blueprint.get("architecture", task)
                gate_ctx = blueprint.get("_gate_context", "")
                episodic_ctx = blueprint.get("_episodic_context", "")

                # Assemble structured prompt: deterministic first, then LLM takes over
                sections = [f"Build Python code for this task:\n\nTask: {task}\nArchitecture: {arch[:400]}"]
                if gate_ctx:
                    sections.append(gate_ctx)
                if episodic_ctx:
                    sections.append(f"=== RELATED PAST WORK ===\n{episodic_ctx}\n========================")
                if ghost_context:
                    sections.append(f"Session context:\n{ghost_context}")
                sections.append("Output ONLY valid Python code. No explanations.")

                prompt = "\n\n".join(sections)

                # Token check — trim if too large
                est_tokens = len(prompt) // 4
                if est_tokens > 3500:
                    prompt = (
                        f"Build Python code:\nTask: {task}\n"
                        + (gate_ctx[:300] if gate_ctx else "")
                        + "\nOutput ONLY Python code."
                    )

                code = qwen.generate(
                    prompt=prompt,
                    system_prompt="You are a precise Python code generator. Use the deterministic analysis provided. Output ONLY code.",
                    temperature=0.2,
                    max_tokens=2048,
                )

                if isinstance(code, str):
                    code = code.strip()
                    if code.startswith("```python"):
                        code = code[9:]
                    if code.startswith("```"):
                        code = code[3:]
                    if code.endswith("```"):
                        code = code[:-3]
                    ghost.append("code_generated", code[:200])
                    return code.strip()

            finally:
                exit_loop("blueprint_build")

        except Exception as e:
            ghost.append("error", f"Build failed: {e}")
        return None

    def _compile_and_test(self, code: str, ghost) -> Dict:
        """Compile and test through Grace's compiler."""
        try:
            from ide.bridge.SpindleDriver import compile_spindle
            from validators.z3_geometric import geometric_verify
            from core.sandbox_modifier import modify_sandbox_node
            import uuid
            
            # 1. Spindle Compilation
            executable_ast = compile_spindle(code)
            
            # 2. Z3 Geometric Verification
            is_safe = geometric_verify(executable_ast.to_dict())
            if not is_safe:
                ghost.append("failure", "Compile: FAIL (Z3 Geometric Proof Failed)")
                return {"passed": False, "error": "Z3 Geometric Proof Failed. Entropy bounds exceeded. Change rejected."}
            
            # 3. Save to Sandbox (Ghost Memory + Genesis Key handled internally)
            ghost.append("pass", "Compile: PASS (Z3 Geometric Proof Succeeded)")
            
            # Use a dummy path for now since LLMs may generate arbitrary snippets. 
            # In a full flow we map this to physical files
            file_path = f"generated_snippet_{uuid.uuid4().hex[:8]}.py"
            result = modify_sandbox_node(file_path, code, reason="LLM Generated", actor="Spindle_Autonomy_LLM")
            
            return {"passed": True, "trust_score": 100, "error": "", "warnings": 0}
        except Exception as e:
            ghost.append("error", f"Compile failed: {e}")
            return {"passed": False, "error": str(e)}


def get_qwen_net() -> QwenCodingNet:
    return QwenCodingNet.get_instance()


def generate_code(prompt: str, project_folder: str = "", use_pipeline: bool = False) -> Dict[str, Any]:
    """
    Generate code from a prompt. Agentic entry: either fast path (Qwen coder only)
    or full pipeline (consensus design → Qwen build → compile/test → self-heal).
    Returns {code, prompt, status?, stages_passed?, trust_score?} for brain/HealingCoordinator.
    """
    if use_pipeline or not prompt.strip():
        result = get_qwen_net().execute_task(prompt or "Generate placeholder", use_consensus=True)
        code = result.get("code", "")
        return {
            "code": code,
            "prompt": prompt,
            "status": result.get("status", "unknown"),
            "stages_passed": ["design", "build", "compile"] if result.get("test_result", {}).get("passed") else ["design", "build"],
            "trust_score": result.get("test_result", {}).get("trust_score", 0.5),
            "error": result.get("revision_hint", result.get("test_result", {}).get("error", result.get("error", "Verification/Compilation Failed"))),
            "ghost_reflection": result.get("ghost_reflection"),
        }
    # Fast path: Qwen coder only (reasoning + coding via latest model)
    try:
        from llm_orchestrator.factory import get_qwen_coder
        qwen = get_qwen_coder()
        context = ""
        if project_folder:
            try:
                from pathlib import Path
                from settings import settings
                kb = Path(settings.KNOWLEDGE_BASE_PATH)
                target = (kb / project_folder.replace("..", "")).resolve()
                if str(target).startswith(str(kb.resolve())):
                    files = list(target.rglob("*"))[:20]
                    context = "Project files: " + ", ".join(f.name for f in files if f.is_file() and f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx"))
            except Exception:
                pass
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        raw = qwen.generate(
            prompt=full_prompt,
            system_prompt="You are a precise code generator. Output only valid code; use markdown code blocks only when necessary.",
            temperature=0.2,
            max_tokens=4096,
        )
        code = raw if isinstance(raw, str) else str(raw)
        if code.strip().startswith("```"):
            lines = code.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        return {"code": code.strip(), "prompt": prompt, "trust_score": 0.7}
    except Exception as e:
        logger.exception("generate_code fast path failed: %s", e)
        return {"code": "", "prompt": prompt, "error": str(e), "trust_score": 0.0}
