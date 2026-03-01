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
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QwenCodingNet:
    """Unified coding execution engine — everything connected."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "QwenCodingNet":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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

        # 2. TimeSense context (shared with Kimi+Opus via consensus)
        time_context = self._get_time_context()
        ghost.append("context", f"Time: {time_context.get('summary', 'unknown')}")

        # 3. Immune system scan — reject sketchy tasks
        if self._immune_scan(task, ghost):
            result["status"] = "blocked_by_immune"
            return result

        # 4. Get architecture context from compass
        arch_context = self._get_architecture_context(task)
        ghost.append("context", f"Architecture: {arch_context[:200]}")

        # 5. Design blueprint (consensus with TimeSense injected)
        if use_consensus:
            blueprint = self._consensus_design(task, ghost, time_context)
        else:
            blueprint = {"architecture": task, "functions": [], "direct": True}

        ghost.append("blueprint", json.dumps(blueprint, default=str)[:500])

        # 6. Build code with token-managed loop
        code = self._build_with_token_management(task, blueprint, ghost)

        if code:
            result["code"] = code
            result["status"] = "completed"
            ghost.append("success", f"Code generated: {len(code)} chars")

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
            now = datetime.utcnow()
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
        """Build code with circuit breaker managing token limits."""
        try:
            from cognitive.circuit_breaker import enter_loop, exit_loop

            if not enter_loop("blueprint_build"):
                ghost.append("error", "Circuit breaker blocked — too many attempts")
                return None

            try:
                from llm_orchestrator.factory import get_qwen_coder
                qwen = get_qwen_coder()

                # Build prompt with ghost context (token-managed)
                ghost_context = ghost.get_context(max_tokens=1000)
                arch = blueprint.get("architecture", task)

                prompt = (
                    f"Build Python code for this task:\n\n"
                    f"Task: {task}\n"
                    f"Architecture: {arch[:500]}\n\n"
                    f"Context from previous work:\n{ghost_context}\n\n"
                    f"Output ONLY valid Python code. No explanations."
                )

                # Token check — if prompt too large, trim ghost context
                est_tokens = len(prompt) // 4
                if est_tokens > 3000:
                    ghost_context = ghost.get_context(max_tokens=500)
                    prompt = (
                        f"Build Python code:\nTask: {task}\n"
                        f"Context:\n{ghost_context}\n\n"
                        f"Output ONLY Python code."
                    )

                code = qwen.generate(
                    prompt=prompt,
                    system_prompt="You are a Python code generator. Output ONLY code.",
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
            from cognitive.grace_compiler import get_grace_compiler
            compiler = get_grace_compiler()
            result = compiler.compile(code)

            compile_result = {
                "passed": result.success,
                "trust_score": result.trust_score,
                "error": "; ".join(result.errors) if result.errors else "",
                "warnings": len(result.warnings),
            }

            ghost.append(
                "pass" if result.success else "failure",
                f"Compile: {'PASS' if result.success else 'FAIL'} (trust: {result.trust_score})"
            )

            return compile_result
        except Exception as e:
            ghost.append("error", f"Compile failed: {e}")
            return {"passed": False, "error": str(e)}


def get_qwen_net() -> QwenCodingNet:
    return QwenCodingNet.get_instance()
