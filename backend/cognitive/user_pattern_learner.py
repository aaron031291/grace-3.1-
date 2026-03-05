"""
User Thinking Pattern Learner
==============================
Observes how each user communicates, thinks, and works —
then adapts Grace's responses to match their style.

Tracks:
  - Communication style (verbose/concise, technical/casual, tone)
  - Topic preferences (what they ask about most)
  - Problem-solving approach (step-by-step vs big-picture)
  - Response preferences (code-first vs explanation-first)
  - Session patterns (active hours, session lengths)
  - Error patterns (recurring issues, common mistakes)
  - Vocabulary level (beginner/intermediate/expert per domain)

The learner runs after every user interaction, updating the profile
incrementally. Grace uses the profile to customize her responses.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import Counter

from database.session import session_scope
from models.memory_graph_models import UserThinkingPattern, UserInteractionLog

logger = logging.getLogger(__name__)


class UserPatternLearner:
    """
    Learns user thinking patterns from interaction history.
    Each user gets a profile that evolves over time.
    """

    STYLE_PATTERNS = {
        "communication_verbosity": "How verbose vs concise the user communicates",
        "communication_technicality": "How technical vs casual the language is",
        "response_preference": "Prefers code-first, explanation-first, or balanced",
        "problem_solving_style": "Step-by-step methodical vs exploratory jump-around",
        "question_depth": "Surface-level questions vs deep investigation",
        "feedback_style": "How the user gives feedback (explicit, implicit, none)",
    }

    def __init__(self, user_id: str):
        self.user_id = user_id

    def observe_interaction(
        self,
        message: str,
        interaction_type: str = "chat",
        session_id: Optional[str] = None,
        response: Optional[str] = None,
        response_time_ms: float = 0,
        satisfaction_signal: Optional[float] = None,
        topic_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Observe a user interaction and update patterns.
        Called after every user message.
        """
        content_hash = hashlib.sha256(message.encode()).hexdigest()

        with session_scope() as session:
            log = UserInteractionLog(
                user_id=self.user_id,
                session_id=session_id,
                interaction_type=interaction_type,
                content_hash=content_hash,
                content_length=len(message),
                topic_tags=topic_tags or [],
                response_type=self._classify_response_type(response) if response else None,
                response_length=len(response) if response else 0,
                response_time_ms=response_time_ms,
                satisfaction_signal=satisfaction_signal,
                metadata_json={},
            )
            session.add(log)

        patterns_updated = self._extract_patterns(message, response, topic_tags)

        return {
            "user_id": self.user_id,
            "patterns_updated": patterns_updated,
            "interaction_logged": True,
        }

    def _extract_patterns(
        self, message: str, response: Optional[str], topic_tags: Optional[List[str]]
    ) -> int:
        """Extract and update patterns from a single interaction."""
        updated = 0

        verbosity = "verbose" if len(message) > 200 else ("concise" if len(message) < 50 else "moderate")
        updated += self._update_pattern("communication_verbosity", verbosity, 1.0)

        tech_indicators = ["function", "class", "api", "endpoint", "database", "async",
                           "import", "module", "deploy", "docker", "kubernetes", "sql"]
        tech_count = sum(1 for w in tech_indicators if w in message.lower())
        technicality = "technical" if tech_count >= 2 else ("casual" if tech_count == 0 else "mixed")
        updated += self._update_pattern("communication_technicality", technicality, 1.0)

        if any(w in message.lower() for w in ["code", "implement", "write", "build", "create", "function"]):
            updated += self._update_pattern("response_preference", "code_first", 0.8)
        elif any(w in message.lower() for w in ["explain", "why", "how does", "what is", "understand"]):
            updated += self._update_pattern("response_preference", "explanation_first", 0.8)

        if any(w in message.lower() for w in ["step by step", "first", "then", "next", "plan"]):
            updated += self._update_pattern("problem_solving_style", "methodical", 0.7)
        elif any(w in message.lower() for w in ["just", "quick", "fast", "directly", "skip"]):
            updated += self._update_pattern("problem_solving_style", "exploratory", 0.7)

        has_question = "?" in message
        question_words = sum(1 for w in ["why", "how", "what", "when", "where", "which"]
                            if w in message.lower().split())
        if has_question and question_words >= 2:
            updated += self._update_pattern("question_depth", "deep", 0.6)
        elif has_question:
            updated += self._update_pattern("question_depth", "moderate", 0.6)

        if topic_tags:
            for tag in topic_tags:
                updated += self._update_pattern("topic_preference", tag, 0.5)

        return updated

    def _update_pattern(self, pattern_type: str, pattern_value: str, weight: float) -> int:
        """Update or create a pattern record. Returns 1 if updated, 0 if failed."""
        try:
            with session_scope() as session:
                existing = session.query(UserThinkingPattern).filter_by(
                    user_id=self.user_id,
                    pattern_type=pattern_type,
                    pattern_key=pattern_value,
                ).first()

                if existing:
                    existing.observation_count += 1
                    old_conf = existing.confidence
                    existing.confidence = old_conf + (weight - old_conf) * 0.1
                    existing.last_observed = datetime.now(timezone.utc)
                else:
                    record = UserThinkingPattern(
                        user_id=self.user_id,
                        pattern_type=pattern_type,
                        pattern_key=pattern_value,
                        pattern_value=pattern_value,
                        confidence=weight * 0.5,
                        observation_count=1,
                        last_observed=datetime.now(timezone.utc),
                    )
                    session.add(record)
                return 1
        except Exception as e:
            logger.debug(f"[UserPattern] Update failed: {e}")
            return 0

    def get_profile(self) -> Dict[str, Any]:
        """Get the full user thinking profile."""
        with session_scope() as session:
            patterns = session.query(UserThinkingPattern).filter_by(
                user_id=self.user_id
            ).order_by(UserThinkingPattern.confidence.desc()).all()

            profile = {}
            for p in patterns:
                if p.pattern_type not in profile:
                    profile[p.pattern_type] = []
                profile[p.pattern_type].append({
                    "value": p.pattern_key,
                    "confidence": round(p.confidence, 3),
                    "observations": p.observation_count,
                    "last_seen": p.last_observed.isoformat() if p.last_observed else None,
                })

            dominant = {}
            for ptype, values in profile.items():
                if values:
                    dominant[ptype] = values[0]["value"]

            interaction_count = session.query(UserInteractionLog).filter_by(
                user_id=self.user_id
            ).count()

            return {
                "user_id": self.user_id,
                "interaction_count": interaction_count,
                "dominant_patterns": dominant,
                "all_patterns": profile,
            }

    def get_adaptation_hints(self) -> Dict[str, str]:
        """
        Get hints for how Grace should adapt responses for this user.
        Used by the LLM orchestrator to customize system prompts.
        """
        profile = self.get_profile()
        dominant = profile.get("dominant_patterns", {})
        hints = {}

        verbosity = dominant.get("communication_verbosity")
        if verbosity == "concise":
            hints["length"] = "Keep responses short and direct. This user prefers brevity."
        elif verbosity == "verbose":
            hints["length"] = "Provide detailed, thorough responses. This user appreciates depth."

        tech = dominant.get("communication_technicality")
        if tech == "technical":
            hints["style"] = "Use technical language. This user is comfortable with jargon."
        elif tech == "casual":
            hints["style"] = "Use plain, accessible language. Avoid unnecessary jargon."

        pref = dominant.get("response_preference")
        if pref == "code_first":
            hints["format"] = "Lead with code examples, then explain. This user prefers seeing code first."
        elif pref == "explanation_first":
            hints["format"] = "Explain the concept first, then show code. This user prefers understanding before implementation."

        solving = dominant.get("problem_solving_style")
        if solving == "methodical":
            hints["structure"] = "Use numbered steps and clear progression. This user thinks methodically."
        elif solving == "exploratory":
            hints["structure"] = "Get to the point quickly. This user prefers directness over structure."

        return hints

    @staticmethod
    def _classify_response_type(response: str) -> str:
        if "```" in response:
            return "code_heavy"
        elif len(response) > 500:
            return "detailed"
        elif len(response) < 100:
            return "brief"
        return "moderate"


def get_user_learner(user_id: str) -> UserPatternLearner:
    return UserPatternLearner(user_id)
