"""
Chat Intelligence Layer

Wires cognitive systems into the chat pipeline:
1. Ambiguity detection - asks clarifying questions when input is vague
2. Episodic memory - learns from every conversation
3. Governance checks - validates outputs against constitutional rules
4. Oracle predictions - routes queries using ML predictions
5. Conversation memory - cross-session context persistence

This is the missing integration bridge between the rich cognitive backend
and the user-facing chat endpoints.

Classes:
- `ChatIntelligence`

Key Methods:
- `ambiguity_engine()`
- `episodic_buffer()`
- `detect_ambiguity()`
- `record_episode()`
- `check_governance()`
- `use_three_layer_reasoning()`
- `predict_query_routing()`
- `enrich_response()`
- `get_chat_intelligence()`

Database Tables:
None (no DB tables)

Connects To:
- `cognitive.engine`
- `cognitive.episodic_memory`
- `diagnostic_machine.interpreters`
- `llm_orchestrator.three_layer_reasoning`
- `security.honesty_integrity_accountability`
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatIntelligence:
    """
    Augments every chat interaction with cognitive capabilities.

    Called from send_prompt and chat endpoints to:
    - Detect ambiguity and generate clarifying questions
    - Store episodes for learning from conversations
    - Check governance rules on outputs
    - Use Oracle ML for query routing predictions
    """

    def __init__(self):
        self._ambiguity_engine = None
        self._episodic_buffer = None
        self._governance = None
        self._oracle = None

    @property
    def ambiguity_engine(self):
        if self._ambiguity_engine is None:
            try:
                from cognitive.engine import CognitiveEngine
                self._ambiguity_engine = CognitiveEngine(enable_strict_mode=False)
            except Exception as e:
                logger.debug(f"[CHAT-INTEL] Ambiguity engine unavailable: {e}")
        return self._ambiguity_engine

    @property
    def episodic_buffer(self):
        if self._episodic_buffer is None:
            try:
                from cognitive.episodic_memory import EpisodicBuffer
                from database.session import SessionLocal
                session = SessionLocal()
                if session:
                    self._episodic_buffer = EpisodicBuffer(session=session)
            except Exception as e:
                logger.debug(f"[CHAT-INTEL] Episodic buffer unavailable: {e}")
        return self._episodic_buffer

    def detect_ambiguity(self, user_query: str, conversation_history: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Detect if a user query is ambiguous and needs clarification.

        Returns None if query is clear, or a dict with:
        - is_ambiguous: bool
        - ambiguity_level: str (low/medium/high)
        - clarifying_questions: list of questions to ask
        - ambiguity_reason: why it's ambiguous
        """
        if not user_query or len(user_query.strip()) < 3:
            return None

        query_lower = user_query.lower().strip()

        ambiguity_signals = []
        score = 0.0

        vague_pronouns = ["it", "this", "that", "they", "them", "those", "these"]
        words = query_lower.split()
        if words and words[0] in vague_pronouns and not conversation_history:
            ambiguity_signals.append("vague_pronoun_without_context")
            score += 0.4

        if len(words) <= 2 and not any(w in query_lower for w in ["hi", "hello", "hey", "bye", "thanks"]):
            ambiguity_signals.append("too_short")
            score += 0.3

        ambiguous_phrases = [
            "how do i", "what about", "can you help", "tell me about",
            "explain", "help me with", "i need help", "show me"
        ]
        matching_phrases = [p for p in ambiguous_phrases if p in query_lower]
        if matching_phrases and len(words) <= 5:
            ambiguity_signals.append("vague_request")
            score += 0.3

        if query_lower.count(" or ") >= 1:
            ambiguity_signals.append("multiple_options")
            score += 0.2

        if score < 0.3:
            return None

        level = "low" if score < 0.5 else ("medium" if score < 0.7 else "high")

        questions = self._generate_clarifying_questions(
            user_query, ambiguity_signals, conversation_history
        )

        return {
            "is_ambiguous": True,
            "ambiguity_level": level,
            "ambiguity_score": round(score, 2),
            "ambiguity_signals": ambiguity_signals,
            "clarifying_questions": questions,
            "ambiguity_reason": f"Query has {len(ambiguity_signals)} ambiguity signal(s)"
        }

    def _generate_clarifying_questions(
        self,
        query: str,
        signals: List[str],
        history: List[Dict] = None
    ) -> List[str]:
        """Generate specific clarifying questions based on ambiguity signals."""
        questions = []

        if "vague_pronoun_without_context" in signals:
            questions.append("Could you clarify what you're referring to? I don't have context from a previous conversation.")

        if "too_short" in signals:
            questions.append("Could you provide more detail about what you need? Your query is quite brief.")

        if "vague_request" in signals:
            questions.append("Could you be more specific about what aspect you'd like me to focus on?")
            questions.append("Are you looking for a general overview or specific technical details?")

        if "multiple_options" in signals:
            questions.append("You mentioned multiple options. Which one would you like me to focus on first?")

        return questions[:3]

    def record_episode(
        self,
        user_query: str,
        response: str,
        sources_used: List[Dict] = None,
        tier_used: str = "unknown",
        confidence: float = 0.5,
        generation_time: float = 0.0,
        chat_id: Optional[int] = None
    ):
        """
        Record this conversation turn as an episode for learning.

        This builds episodic memory from every interaction so Grace
        can learn from patterns in conversations.
        """
        try:
            if not self.episodic_buffer:
                return

            self.episodic_buffer.store_episode(
                problem=user_query,
                action={
                    "type": "chat_response",
                    "tier": tier_used,
                    "sources_count": len(sources_used) if sources_used else 0,
                    "chat_id": chat_id
                },
                outcome={
                    "response_length": len(response),
                    "generation_time": generation_time,
                    "confidence": confidence,
                    "had_sources": bool(sources_used)
                },
                predicted_outcome={"expected_quality": "good"},
                source="chat_interaction",
                trust_score=confidence
            )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Episode recording failed: {e}")

    def check_governance(self, response_text: str, has_sources: bool = False) -> Dict[str, Any]:
        """
        Check response against governance rules + HIA (Honesty, Integrity, Accountability).

        Returns governance check result with any violations.
        """
        result = {
            "passed": True,
            "violations": [],
            "warnings": [],
            "checks_performed": [],
            "hia_score": None
        }

        try:
            checks = [
                ("safety_language", self._check_safety_language),
                ("response_quality", self._check_response_quality),
                ("transparency", self._check_transparency),
            ]

            for check_name, check_fn in checks:
                check_result = check_fn(response_text)
                result["checks_performed"].append(check_name)
                if check_result.get("violation"):
                    result["passed"] = False
                    result["violations"].append(check_result)
                elif check_result.get("warning"):
                    result["warnings"].append(check_result)

            # HIA Verification — Honesty, Integrity, Accountability
            try:
                from security.honesty_integrity_accountability import get_hia_framework
                hia = get_hia_framework()
                hia_result = hia.verify_llm_output(response_text, has_sources=has_sources)
                result["checks_performed"].append("hia_honesty_check")
                result["hia_score"] = {
                    "honesty": hia_result.honesty_score,
                    "integrity": hia_result.integrity_score,
                    "accountability": hia_result.accountability_score,
                    "overall": hia_result.overall_score,
                }
                if not hia_result.passed:
                    result["passed"] = False
                    for v in hia_result.violations:
                        result["violations"].append({
                            "rule": f"HIA_{v.value.value.upper()}",
                            "detail": v.description,
                            "severity": v.severity.value,
                        })
                if hia_result.corrections_applied:
                    result["warnings"].extend([
                        {"rule": "HIA_CORRECTION", "detail": c}
                        for c in hia_result.corrections_applied
                    ])
            except Exception as e:
                logger.debug(f"[CHAT-INTEL] HIA check skipped: {e}")

        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Governance check error: {e}")

        return result

    def _check_safety_language(self, text: str) -> Dict[str, Any]:
        """Check for safety-critical language patterns."""
        dangerous_patterns = [
            "i will delete", "i will remove all", "destroying",
            "i have access to your", "i can control"
        ]
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern in text_lower:
                return {
                    "violation": True,
                    "rule": "SAFETY_FIRST",
                    "detail": f"Response contains safety-critical language: '{pattern}'"
                }
        return {}

    def _check_response_quality(self, text: str) -> Dict[str, Any]:
        """Check response quality indicators."""
        if len(text.strip()) < 10:
            return {
                "warning": True,
                "rule": "RESPONSE_QUALITY",
                "detail": "Response is very short, may not be helpful"
            }
        return {}

    def _check_transparency(self, text: str) -> Dict[str, Any]:
        """Check transparency requirements."""
        fabrication_indicators = [
            "as an ai, i know that",
            "studies have conclusively proven",
        ]
        text_lower = text.lower()
        for indicator in fabrication_indicators:
            if indicator in text_lower:
                return {
                    "warning": True,
                    "rule": "TRANSPARENCY_REQUIRED",
                    "detail": "Response may contain ungrounded claims"
                }
        return {}

    def use_three_layer_reasoning(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Invoke the 3-layer reasoning pipeline for complex queries.

        Returns the verified result or None if unavailable.
        """
        try:
            from llm_orchestrator.three_layer_reasoning import get_three_layer_reasoning
            pipeline = get_three_layer_reasoning()
            result = pipeline.reason(query)
            return {
                "answer": result.answer,
                "confidence": result.confidence,
                "l1_agreement": result.layer1_agreement,
                "l2_agreement": result.layer2_agreement,
                "grounded": result.training_data_grounded,
                "governance_passed": result.governance_passed,
            }
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] 3-layer reasoning unavailable: {e}")
            return None

    def predict_query_routing(self, user_query: str) -> Dict[str, Any]:
        """
        Use Oracle ML predictions to optimize query routing.

        Predicts which tier (VectorDB, Model, Internet) will work best
        for this type of query, improving response time and quality.
        """
        try:
            from diagnostic_machine.interpreters import QueryPatternInterpreter
            interpreter = QueryPatternInterpreter()
            prediction = interpreter.predict_best_tier(user_query)
            return prediction
        except Exception:
            pass

        query_lower = user_query.lower()
        if any(w in query_lower for w in ["code", "function", "class", "api", "bug", "error"]):
            return {"predicted_tier": "VECTORDB", "confidence": 0.7, "reason": "technical_query"}
        elif any(w in query_lower for w in ["latest", "news", "current", "today", "2026"]):
            return {"predicted_tier": "INTERNET", "confidence": 0.6, "reason": "temporal_query"}
        elif any(w in query_lower for w in ["what is", "explain", "how does", "define"]):
            return {"predicted_tier": "MODEL_KNOWLEDGE", "confidence": 0.5, "reason": "general_knowledge"}

        return {"predicted_tier": "VECTORDB", "confidence": 0.4, "reason": "default"}

    def enrich_response(
        self,
        response_text: str,
        ambiguity_result: Optional[Dict] = None,
        governance_result: Optional[Dict] = None
    ) -> str:
        """
        Enrich a response with ambiguity questions or governance warnings.

        If the query was ambiguous, prepend clarifying questions.
        If governance flagged warnings, append transparency notes.
        """
        enriched = response_text

        if ambiguity_result and ambiguity_result.get("is_ambiguous"):
            questions = ambiguity_result.get("clarifying_questions", [])
            if questions and ambiguity_result.get("ambiguity_level") in ("medium", "high"):
                q_text = "\n".join(f"- {q}" for q in questions)
                enriched = (
                    f"I noticed your question might be interpreted in different ways. "
                    f"Before I answer, let me clarify:\n\n{q_text}\n\n"
                    f"Based on my best understanding, here's what I found:\n\n{response_text}"
                )

        if governance_result and governance_result.get("warnings"):
            warnings = governance_result["warnings"]
            if warnings:
                w_text = "; ".join(w.get("detail", "") for w in warnings)
                enriched += f"\n\n_Note: {w_text}_"

        return enriched


_chat_intelligence: Optional[ChatIntelligence] = None


def get_chat_intelligence() -> ChatIntelligence:
    """Get or create the chat intelligence singleton."""
    global _chat_intelligence
    if _chat_intelligence is None:
        _chat_intelligence = ChatIntelligence()
    return _chat_intelligence
