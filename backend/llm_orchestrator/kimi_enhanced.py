"""
Enhanced Kimi Integration — Full tool-like capacity connected to Magma Memory.

Kimi capabilities now used:
1. Cross-model verification (generate local → verify with Kimi)
2. Continuous learning teacher (idle time knowledge generation)
3. Real-time healing consultant (instant diagnosis on critical alerts)
4. Code review (second opinion on generated code)
5. Document understanding (pre-process governance/agent rules)
6. Long-context project analysis (128K+ token codebase reasoning)
7. Magma memory enrichment (causal inference, semantic linking)
8. Memory consolidation (synthesise scattered knowledge)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class KimiEnhanced:
    """Enhanced Kimi with Magma memory integration and full tool capacity."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from llm_orchestrator.factory import get_raw_client
                self._client = get_raw_client(provider="kimi")
            except Exception:
                pass
        return self._client

    def _call(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 4096) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        try:
            messages = [{"role": "user", "content": prompt}]
            if system:
                messages.insert(0, {"role": "system", "content": system})
            return client.chat(messages=messages, temperature=temperature)
        except Exception as e:
            logger.warning(f"Kimi call failed: {e}")
            return None

    # ── 1. Cross-model verification ────────────────────────────────────

    def verify_output(self, prompt: str, local_output: str) -> Dict[str, Any]:
        """
        Verify locally-generated output with Kimi as second opinion.
        Two independent models agreeing = high confidence.
        """
        verification_prompt = (
            f"A local AI generated this output for the following request. "
            f"Review it for: accuracy, completeness, potential issues, hallucinations.\n\n"
            f"Original request: {prompt[:1000]}\n\n"
            f"Generated output:\n{local_output[:3000]}\n\n"
            f"Provide your assessment as JSON:\n"
            f'{{"agrees": true/false, "confidence": 0.0-1.0, "issues": ["..."], "improvements": ["..."]}}'
        )

        response = self._call(verification_prompt,
                              system="You are a code and content reviewer. Be precise and critical.")

        result = {"verified": False, "kimi_available": response is not None}
        if response:
            try:
                import json
                parsed = json.loads(response.strip().strip('```json').strip('```'))
                result.update(parsed)
                result["verified"] = parsed.get("agrees", False) and parsed.get("confidence", 0) > 0.6
            except Exception:
                result["raw_review"] = response[:500]
                result["verified"] = "no issues" in response.lower() or "looks correct" in response.lower()

        return result

    # ── 2. Continuous learning teacher ─────────────────────────────────

    def teach_topic(self, topic: str, context: str = "") -> Dict[str, Any]:
        """
        Generate structured knowledge on a topic for ingestion into
        learning memory and Magma.
        """
        prompt = (
            f"Teach me comprehensively about: {topic}\n"
            f"{'Context: ' + context if context else ''}\n\n"
            f"Structure your response as:\n"
            f"1. Key concepts (facts Grace should know)\n"
            f"2. Causal relationships (what causes what)\n"
            f"3. Procedures (step-by-step how-to)\n"
            f"4. Common mistakes (what to avoid)\n"
            f"5. Connections to other topics\n"
        )

        response = self._call(prompt,
                              system="You are a teacher creating structured knowledge for an AI learning system.",
                              max_tokens=6000)

        result = {"topic": topic, "generated": bool(response)}
        if response:
            result["knowledge"] = response

            # Ingest into Magma memory
            self._ingest_to_magma(topic, response)

            # Store as learning example
            self._store_learning(topic, response)

        return result

    # ── 3. Real-time healing consultant ────────────────────────────────

    def diagnose_realtime(self, error_events: List[Dict]) -> Dict[str, Any]:
        """
        Instant diagnosis when critical alert fires.
        Connected to genesis realtime engine.
        """
        error_summary = "\n".join(
            f"- [{e.get('error_type', '?')}] {e.get('what', '?')} at {e.get('where', '?')}"
            for e in error_events[:10]
        )

        prompt = (
            f"Grace AI has detected these errors in rapid succession:\n\n"
            f"{error_summary}\n\n"
            f"Diagnose:\n1. Root cause\n2. Severity (1-10)\n3. Immediate fix\n4. Prevention strategy"
        )

        response = self._call(prompt,
                              system="You are a system diagnostician. Be specific and actionable.",
                              temperature=0.2)

        return {"diagnosis": response, "error_count": len(error_events)}

    # ── 4. Code review ─────────────────────────────────────────────────

    def review_code(self, code: str, project_context: str = "", rules: str = "") -> Dict[str, Any]:
        """
        Review generated code before applying.
        Checks: bugs, security, style, compliance with rules.
        """
        prompt = (
            f"Review this code for bugs, security issues, and best practices:\n\n"
            f"```\n{code[:5000]}\n```\n"
        )
        if project_context:
            prompt += f"\nProject context: {project_context[:1000]}"
        if rules:
            prompt += f"\nMust comply with: {rules[:1000]}"

        prompt += (
            f"\n\nProvide:\n1. Issues found (critical/warning/info)\n"
            f"2. Security concerns\n3. Suggested improvements\n4. Overall quality (1-10)"
        )

        response = self._call(prompt, system="You are a senior code reviewer.", temperature=0.2)
        return {"review": response, "reviewed": bool(response)}

    # ── 5. Document understanding ──────────────────────────────────────

    def process_rule_document(self, content: str, doc_name: str) -> Dict[str, Any]:
        """
        Pre-process a governance or agent rule document.
        Extracts structured rules, identifies conflicts, creates summary.
        """
        prompt = (
            f"Analyse this governance/compliance document and extract:\n\n"
            f"Document: {doc_name}\n"
            f"Content:\n{content[:10000]}\n\n"
            f"Extract as JSON:\n"
            f'{{"summary": "...", "rules": [{{"rule": "...", "severity": "must/should/may", "category": "..."}}], '
            f'"conflicts": ["any conflicts with common practices"], "key_obligations": ["..."]}}'
        )

        response = self._call(prompt,
                              system="You are a compliance analyst. Extract precise, actionable rules.",
                              max_tokens=6000, temperature=0.1)

        result = {"document": doc_name, "processed": bool(response)}
        if response:
            try:
                import json
                result["structured"] = json.loads(response.strip().strip('```json').strip('```'))
            except Exception:
                result["raw_analysis"] = response[:2000]

        return result

    # ── 6. Long-context project analysis ───────────────────────────────

    def analyse_project(self, project_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Send entire project to Kimi for holistic analysis.
        Uses Kimi's 128K+ token context for codebase-level reasoning.
        """
        file_contents = ""
        for path, content in list(project_files.items())[:20]:
            file_contents += f"\n--- {path} ---\n{content[:3000]}\n"

        prompt = (
            f"Analyse this entire project holistically:\n\n"
            f"{file_contents[:50000]}\n\n"
            f"Provide:\n1. Architecture overview\n2. Code quality assessment\n"
            f"3. Potential issues\n4. Security concerns\n5. Improvement recommendations\n"
            f"6. Missing components\n7. Technical debt"
        )

        response = self._call(prompt,
                              system="You are a senior architect reviewing a codebase.",
                              max_tokens=8000, temperature=0.3)

        return {"analysis": response, "files_analysed": len(project_files)}

    # ── 7. Magma memory enrichment ─────────────────────────────────────

    def enrich_magma(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Use Kimi to generate causal inferences and semantic links
        for Magma memory graphs.
        """
        prompt = (
            f"For this knowledge:\n\n{query}\n"
            f"{'Context: ' + context if context else ''}\n\n"
            f"Generate:\n"
            f"1. Causal relationships (X causes Y because Z)\n"
            f"2. Semantic connections (X is related to Y via Z)\n"
            f"3. Temporal patterns (X happens before/after Y)\n"
            f"4. Entity relationships (X uses/contains/depends-on Y)\n"
            f"Format as JSON arrays."
        )

        response = self._call(prompt,
                              system="You are a knowledge graph builder. Extract precise relationships.",
                              temperature=0.2)

        result = {"enriched": bool(response)}
        if response:
            result["relationships"] = response[:2000]
            self._ingest_to_magma(query[:100], response)

        return result

    # ── 8. Memory consolidation ────────────────────────────────────────

    def consolidate_memory(self, memories: List[Dict]) -> Dict[str, Any]:
        """
        Synthesise scattered knowledge into consolidated understanding.
        Takes multiple memory fragments and produces a coherent summary.
        """
        memory_text = "\n".join(
            f"- [{m.get('type', '?')}] {m.get('content', '')[:200]}"
            for m in memories[:20]
        )

        prompt = (
            f"These are scattered memory fragments from an AI system:\n\n"
            f"{memory_text}\n\n"
            f"Consolidate into:\n1. Key themes\n2. Unified understanding\n"
            f"3. Contradictions to resolve\n4. Knowledge gaps identified"
        )

        response = self._call(prompt,
                              system="You are consolidating fragmented knowledge into coherent understanding.",
                              max_tokens=4000)

        result = {"consolidated": bool(response), "fragment_count": len(memories)}
        if response:
            result["synthesis"] = response
            self._ingest_to_magma("memory_consolidation", response)

        return result

    # ── Magma integration helpers ──────────────────────────────────────

    def _ingest_to_magma(self, topic: str, content: str):
        """Ingest Kimi-generated knowledge into Magma memory."""
        try:
            from cognitive.magma.grace_magma_system import GraceMagmaSystem
            magma = GraceMagmaSystem()
            if hasattr(magma, 'ingest'):
                magma.ingest(topic, content)
            elif hasattr(magma, 'store'):
                magma.store(topic, content)
        except Exception:
            pass

        # Also store in relation graphs directly
        try:
            from cognitive.magma.relation_graphs import SemanticGraph
            graph = SemanticGraph()
            graph.add_concept(topic, {"content": content[:500], "source": "kimi"})
        except Exception:
            pass

        # Track via genesis
        try:
            from api._genesis_tracker import track
            track(key_type="ai_response",
                  what=f"Kimi → Magma: {topic[:80]}",
                  how="KimiEnhanced → Magma",
                  tags=["kimi", "magma", "enrichment"])
        except Exception:
            pass

    def _store_learning(self, topic: str, knowledge: str):
        """Store Kimi-generated knowledge as learning example."""
        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="",
                prompt=f"Learn: {topic}",
                output=knowledge[:5000],
                outcome="positive",
            )
        except Exception:
            pass


# Singleton
_kimi = None

def get_kimi_enhanced() -> KimiEnhanced:
    global _kimi
    if _kimi is None:
        _kimi = KimiEnhanced()
    return _kimi
