"""
coding_agent/deterministic_gate.py
─────────────────────────────────────────────────────────────────────────────
Deterministic Pre-LLM Gate

Philosophy: "Deterministic checks up — LLM takes over"

Before Qwen ever sees a coding task, this gate:
  1. AST-parses any existing code in context (finds syntax errors, imports,
     function signatures, complexity)
  2. Identifies risky patterns (DB writes, network calls, file deletions)
  3. Checks if similar work already exists in the knowledge base
  4. Produces a structured GateReport passed as context INTO the LLM prompt

This means Qwen starts reasoning from a factual foundation, not from scratch.
It knows: what's already there, what imports are available, what the risk
surface is, and what similar code looked like.
"""
from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Risk signals — deterministic, no LLM needed
_HIGH_RISK_PATTERNS = [
    "os.remove", "shutil.rmtree", "DROP TABLE", "DELETE FROM", "TRUNCATE",
    "subprocess.call", "os.system", "eval(", "__import__(",
    "socket.connect", "requests.post", "urllib.request",
]

_MEDIUM_RISK_PATTERNS = [
    "open(", "write(", "session.commit", "session.delete",
    "time.sleep", "threading.Thread",
]


@dataclass
class GateReport:
    """Structured output from the deterministic gate — fed into LLM prompt."""
    syntax_valid: bool = True
    syntax_errors: List[str] = field(default_factory=list)
    imports_found: List[str] = field(default_factory=list)
    functions_found: List[str] = field(default_factory=list)
    classes_found: List[str] = field(default_factory=list)
    high_risk_patterns: List[str] = field(default_factory=list)
    medium_risk_patterns: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    similar_knowledge: List[str] = field(default_factory=list)
    complexity_score: int = 0  # AST node count
    recommendations: List[str] = field(default_factory=list)
    gate_passed: bool = True  # False only for catastrophic risk

    def as_prompt_context(self) -> str:
        """Format as a compact LLM-readable context block."""
        lines = ["=== DETERMINISTIC PRE-ANALYSIS ==="]

        if not self.syntax_valid:
            lines.append(f"⚠️ SYNTAX ERRORS: {'; '.join(self.syntax_errors[:3])}")

        if self.imports_found:
            lines.append(f"Available imports: {', '.join(self.imports_found[:10])}")

        if self.functions_found:
            lines.append(f"Existing functions: {', '.join(self.functions_found[:10])}")

        if self.high_risk_patterns:
            lines.append(f"⛔ HIGH RISK patterns detected: {', '.join(self.high_risk_patterns)}")
            lines.append("  → Wrap in try/except, add governance approval, log to Genesis")

        if self.medium_risk_patterns:
            lines.append(f"⚠️ Medium risk patterns: {', '.join(self.medium_risk_patterns)}")

        if self.similar_knowledge:
            lines.append(f"📚 Similar code in KB: {self.similar_knowledge[0][:150]}...")

        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations[:3]:
                lines.append(f"  • {r}")

        lines.append(f"Risk score: {self.risk_score:.2f} | Complexity: {self.complexity_score} nodes")
        lines.append("=================================")
        return "\n".join(lines)


class DeterministicGate:
    """
    Runs fast, deterministic checks before any LLM call.
    Produces a GateReport that enriches the Qwen prompt.
    """

    def analyze(
        self,
        task: str,
        existing_code: str = "",
        file_context: str = "",
    ) -> GateReport:
        """
        Full deterministic analysis.
        Always returns a GateReport — never raises.
        """
        report = GateReport()

        try:
            # 1. Parse existing code if provided
            if existing_code.strip():
                self._parse_code(existing_code, report)

            # 2. Parse file context code if provided
            if file_context.strip():
                self._parse_code(file_context, report)

            # 3. Risk pattern scan (task description + code)
            combined = f"{task}\n{existing_code}\n{file_context}"
            self._scan_risk_patterns(combined, report)

            # 4. Compute risk score
            report.risk_score = min(1.0, (
                len(report.high_risk_patterns) * 0.3 +
                len(report.medium_risk_patterns) * 0.1 +
                (0.2 if not report.syntax_valid else 0.0)
            ))

            # 5. Gate: block only catastrophic risk (>= 0.9)
            if report.risk_score >= 0.9:
                report.gate_passed = False
                report.recommendations.append(
                    "BLOCKED: Risk score too high. Requires governance approval."
                )

            # 6. Add recommendations based on findings
            self._add_recommendations(report)

            # 7. Search knowledge base for similar code
            report.similar_knowledge = self._search_kb(task)

            logger.debug(
                "[GATE] Analysis complete — risk=%.2f, syntax=%s, gate=%s",
                report.risk_score, report.syntax_valid, report.gate_passed,
            )

        except Exception as e:
            logger.warning("[GATE] Analysis error (non-fatal): %s", e)

        return report

    def _parse_code(self, code: str, report: GateReport) -> None:
        """AST parse code to extract structure."""
        try:
            tree = ast.parse(code)
            report.complexity_score += sum(1 for _ in ast.walk(tree))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in report.imports_found:
                            report.imports_found.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod not in report.imports_found:
                        report.imports_found.append(mod)
                elif isinstance(node, ast.FunctionDef):
                    sig = f"{node.name}({', '.join(a.arg for a in node.args.args)})"
                    if sig not in report.functions_found:
                        report.functions_found.append(sig)
                elif isinstance(node, ast.ClassDef):
                    if node.name not in report.classes_found:
                        report.classes_found.append(node.name)

        except SyntaxError as e:
            report.syntax_valid = False
            report.syntax_errors.append(f"Line {e.lineno}: {e.msg}")

    def _scan_risk_patterns(self, text: str, report: GateReport) -> None:
        """Scan for risky code patterns."""
        for pattern in _HIGH_RISK_PATTERNS:
            if pattern in text and pattern not in report.high_risk_patterns:
                report.high_risk_patterns.append(pattern)
        for pattern in _MEDIUM_RISK_PATTERNS:
            if pattern in text and pattern not in report.medium_risk_patterns:
                report.medium_risk_patterns.append(pattern)

    def _add_recommendations(self, report: GateReport) -> None:
        """Add targeted recommendations based on findings."""
        if not report.syntax_valid:
            report.recommendations.append("Fix syntax errors before adding new logic")
        if "os.remove" in report.high_risk_patterns or "shutil.rmtree" in report.high_risk_patterns:
            report.recommendations.append("Add dry_run=True parameter for destructive file ops")
        if any("session" in p for p in report.medium_risk_patterns):
            report.recommendations.append("Use session_scope() context manager, not bare sessions")
        if report.complexity_score > 500:
            report.recommendations.append("High complexity — consider splitting into smaller functions")

    def _search_kb(self, task: str) -> List[str]:
        """Search knowledge base for similar existing code."""
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            if not client or not client.is_connected():
                return []
            # Quick semantic search
            from embedding import get_embedding_model
            model = get_embedding_model()
            vec = model.embed_text(task[:200])
            results = client.search(
                collection_name="documents",
                query_vector=vec.tolist(),
                limit=2,
                score_threshold=0.7,
            )
            return [r.payload.get("text", "")[:200] for r in results if r.payload]
        except Exception:
            return []


# Singleton
_gate: Optional[DeterministicGate] = None


def get_gate() -> DeterministicGate:
    global _gate
    if _gate is None:
        _gate = DeterministicGate()
    return _gate
