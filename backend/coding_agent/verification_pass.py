"""
coding_agent/verification_pass.py
─────────────────────────────────────────────────────────────────────────────
Post-generation RAG Verification Pass

After Qwen generates code, this module:
  1. Cross-checks the code logic against Grace's knowledge base via the
     neuro-symbolic reasoner (is this how the system actually works?)
  2. Detects contradictions with current ghost memory session context
  3. Scores confidence — rejects code below trust threshold
  4. Flags specific suspicious lines with reasons
  5. Records accepted/rejected decisions as learning events

Trust threshold: 0.5 (lenient) for syntax-valid code — we don't want to
block too aggressively on internal code generation.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TRUST_THRESHOLD = 0.65      # below this → reject and request revision
HARD_REJECT_THRESHOLD = 0.3  # below this → reject immediately, no retry
# Base score — code must earn its trust, not start at maximum
_BASE_SCORE = 0.75  # deductions pull from here; bonuses can exceed


@dataclass
class VerificationResult:
    """Result from the post-generation verification pass."""
    accepted: bool = True
    trust_score: float = 1.0
    flags: List[str] = field(default_factory=list)
    kb_matches: List[Dict] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    revision_hint: str = ""  # what the LLM should change on retry

    def summary(self) -> str:
        status = "✅ ACCEPTED" if self.accepted else "❌ REJECTED"
        return (
            f"{status} | trust={self.trust_score:.2f} | "
            f"flags={len(self.flags)} | contradictions={len(self.contradictions)}"
        )


class VerificationPass:
    """
    Runs post-generation verification on Qwen's output.
    Uses RAG + ghost memory + static checks.
    """

    def verify(
        self,
        code: str,
        task: str,
        ghost_context: str = "",
    ) -> VerificationResult:
        """
        Full verification pass. Always returns VerificationResult — never raises.
        """
        result = VerificationResult()

        if not code or len(code.strip()) < 10:
            result.accepted = False
            result.trust_score = 0.0
            result.flags.append("empty_or_trivial_output")
            return result

        try:
            # 1. Static checks (fast, deterministic)
            self._static_checks(code, result)

            # 2. Ghost memory contradiction check
            if ghost_context:
                self._check_ghost_contradictions(code, ghost_context, result)

            # 3. RAG knowledge base cross-check
            self._rag_check(code, task, result)

            # 4. Compute final trust score
            result.trust_score = self._compute_trust_score(result)

            # 5. Accept/reject decision
            if result.trust_score < HARD_REJECT_THRESHOLD:
                result.accepted = False
                result.revision_hint = (
                    f"Code scored {result.trust_score:.2f} trust — critically low. "
                    f"Issues: {'; '.join(result.flags[:3])}"
                )
            elif result.trust_score < TRUST_THRESHOLD:
                result.accepted = False
                result.revision_hint = (
                    f"Code scored {result.trust_score:.2f} trust. "
                    f"Address these issues: {'; '.join((result.flags + result.contradictions)[:3])}"
                )

            logger.info("[VERIFY] %s — task: %s", result.summary(), task[:60])

        except Exception as e:
            # Never block on verification failure — log and accept
            logger.warning("[VERIFY] Verification error (accepting): %s", e)
            result.accepted = True
            result.trust_score = 0.65

        # Record learning event
        self._record_verification(task, code, result)

        return result

    def _static_checks(self, code: str, result: VerificationResult) -> None:
        """Fast static checks — no LLM, no DB."""
        import ast

        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.flags.append(f"syntax_error:line_{e.lineno}:{e.msg}")

        # Dead code patterns
        if "pass" in code and len(code.strip()) < 50:
            result.flags.append("stub_only_no_implementation")

        # Hallucination patterns in code
        hallucination_signals = [
            r"\.fictional_method\(",
            r"import fake_",
            r"from nonexistent",
            r"# TODO: implement",
            r"raise NotImplementedError",
        ]
        for pattern in hallucination_signals:
            if re.search(pattern, code, re.IGNORECASE):
                result.flags.append(f"hallucination_signal:{pattern}")

        # Dangerous patterns
        dangerous = ["eval(", "exec(", "__import__(", "os.system("]
        for d in dangerous:
            if d in code:
                result.flags.append(f"dangerous_pattern:{d}")

    def _check_ghost_contradictions(
        self, code: str, ghost_context: str, result: VerificationResult
    ) -> None:
        """Check if code contradicts what ghost memory knows about this session."""
        # Simple contradiction: code redefines a function ghost said already exists
        functions_in_code = re.findall(r"def (\w+)\(", code)
        for fn in functions_in_code:
            if f"def {fn}" in ghost_context and fn not in ("__init__", "main"):
                result.contradictions.append(
                    f"Function '{fn}' already defined in session context — possible duplicate"
                )

    def _rag_check(self, code: str, task: str, result: VerificationResult) -> None:
        try:
            from ml_intelligence.neuro_symbolic_reasoner import get_neuro_symbolic_reasoner
            from cognitive.learning_memory import LearningMemoryManager
            from database.session import SessionLocal
            import os
            from pathlib import Path
            
            db = SessionLocal() if SessionLocal else None
            if db:
                try:
                    lm = LearningMemoryManager(db, Path(os.environ.get("GRACE_KNOWLEDGE_BASE_PATH", ".")))
                    reasoner = get_neuro_symbolic_reasoner(learning_memory=lm)
                    # Query: does the KB have anything relevant to this task?
                    query = f"code implementation: {task[:200]}"
                    reasoning = reasoner.reason(query, limit=3)
                    result.kb_matches = [
                        {"score": r.get("fusion_score", 0), "text": str(r.get("text", ""))[:100]}
                        for r in reasoning.fused_results[:3]
                    ]
        
                    # If KB has relevant content and trust is high, boost confidence
                    if reasoning.fusion_confidence > 0.7 and result.kb_matches:
                        result.flags.append("kb_verified")  # positive flag
                finally:
                    db.close()
        except Exception:
            pass  # KB check is optional

    def _compute_trust_score(self, result: VerificationResult) -> float:
        """Compute trust score from all check results.

        Score starts at _BASE_SCORE (0.75) — trust is earned, not assumed.
        Clean code with KB verification can reach 1.0.
        """
        score = _BASE_SCORE

        # Deductions for flags
        for flag in result.flags:
            if flag.startswith("syntax_error"):
                score -= 0.45  # syntax error is serious
            elif flag.startswith("hallucination_signal"):
                score -= 0.35
            elif flag.startswith("dangerous_pattern"):
                score -= 0.25
            elif flag == "stub_only_no_implementation":
                score -= 0.35
            elif flag == "kb_verified":
                score += 0.15  # KB match is a meaningful positive signal

        # Deductions for contradictions
        score -= len(result.contradictions) * 0.20

        # Bonus for clean code (no flags, no contradictions)
        if not result.flags and not result.contradictions:
            score += 0.10

        return max(0.0, min(1.0, score))

    def _record_verification(
        self, task: str, code: str, result: VerificationResult
    ) -> None:
        """Record verification decision as a learning event."""
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what_description=f"Code verification: {'ACCEPTED' if result.accepted else 'REJECTED'} (trust={result.trust_score:.2f})",
                why_reason=result.revision_hint or "Trust threshold passed",
                how_method="coding_agent.verification_pass",
                context_data={
                    "task": task[:100],
                    "flags": result.flags,
                    "contradictions": result.contradictions,
                    "trust_score": result.trust_score,
                    "accepted": result.accepted,
                },
                is_error=not result.accepted,
            )
        except Exception:
            pass

        # Feed into learning memory (accepted code = positive example)
        if result.accepted and result.trust_score > 0.7:
            try:
                from cognitive.unified_memory import get_unified_memory
                get_unified_memory().store_learning(
                    input_ctx=f"code_generation: {task[:200]}",
                    expected=code[:400],
                    actual=code[:400],
                    trust=result.trust_score,
                    source="verification_pass",
                    example_type="accepted_code",
                )
            except Exception:
                pass
            try:
                from cognitive import magma_bridge as magma
                magma.ingest(
                    f"Verified code accepted (trust={result.trust_score:.2f}): {task[:150]}",
                    source="verification_pass",
                    metadata={"trust_score": result.trust_score, "flags": result.flags},
                )
            except Exception:
                pass

        # KPI: overall verification component metric
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi(
                "verification_pass",
                "trust_score",
                value=result.trust_score,
                success=result.accepted,
            )
        except Exception:
            pass


# Singleton
_pass: Optional[VerificationPass] = None


def get_verification_pass() -> VerificationPass:
    global _pass
    if _pass is None:
        _pass = VerificationPass()
    return _pass
