"""
User Preference Model

Learns and remembers user preferences across sessions:
- Preferred programming language
- Technical level (beginner/intermediate/expert)
- Response style (concise/detailed)
- Topics of interest
- Common question patterns

Built from Genesis ID session tracking and conversation history.
Feeds into chat intelligence to personalize responses.

Classes:
- `UserPreference`
- `UserPreferenceEngine`

Key Methods:
- `observe_interaction()`
- `get_preferences()`
- `get_system_prompt_additions()`

Database Tables:
- `user_preferences`

Connects To:
Self-contained
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)


class UserPreference(BaseModel):
    """User preference record — persists across sessions."""
    __tablename__ = "user_preferences"

    genesis_id = Column(String(100), nullable=False, index=True)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(Text, nullable=True)
    confidence = Column(Float, default=0.5)
    observation_count = Column(Integer, default=1)
    last_observed = Column(DateTime, default=datetime.now)
    pref_metadata = Column(JSON, nullable=True)


class UserPreferenceEngine:
    """
    Learns user preferences from conversation patterns.

    Observes:
    - What languages they ask about (Python, JS, etc.)
    - How detailed their questions are (infers technical level)
    - What topics they return to repeatedly
    - Whether they prefer code examples or explanations
    """

    def __init__(self, session: Session):
        self.session = session

    def observe_interaction(
        self,
        genesis_id: str,
        query: str,
        response_length: int = 0,
    ):
        """Observe a user interaction and update preferences."""
        if not genesis_id or genesis_id == "anonymous":
            return

        query_lower = query.lower()

        # Detect programming language preference
        lang_signals = {
            "python": ["python", ".py", "pip", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "node", "react", "vue", "npm"],
            "typescript": ["typescript", "ts", "angular", "tsx"],
            "rust": ["rust", "cargo", "rustc"],
            "go": ["golang", " go ", "goroutine"],
        }
        for lang, keywords in lang_signals.items():
            if any(k in query_lower for k in keywords):
                self._update_preference(genesis_id, "preferred_language", lang)

        # Detect technical level from query complexity
        word_count = len(query.split())
        if word_count > 30:
            self._update_preference(genesis_id, "detail_preference", "detailed")
        elif word_count < 8:
            self._update_preference(genesis_id, "detail_preference", "concise")

        # Detect topic interest
        topic_signals = {
            "api_design": ["api", "rest", "endpoint", "route"],
            "database": ["database", "sql", "query", "table", "schema"],
            "ml_ai": ["machine learning", "neural", "model", "training", "ai"],
            "devops": ["docker", "deploy", "ci/cd", "kubernetes", "pipeline"],
            "security": ["security", "auth", "encrypt", "token", "csrf"],
        }
        for topic, keywords in topic_signals.items():
            if any(k in query_lower for k in keywords):
                self._update_preference(genesis_id, f"interest_{topic}", "true")

    def _update_preference(self, genesis_id: str, key: str, value: str):
        """Update or create a preference entry."""
        existing = self.session.query(UserPreference).filter(
            UserPreference.genesis_id == genesis_id,
            UserPreference.preference_key == key,
        ).first()

        if existing:
            if existing.preference_value == value:
                existing.observation_count += 1
                existing.confidence = min(0.99, existing.confidence + 0.02)
            else:
                if existing.observation_count > 3:
                    existing.confidence -= 0.05
                else:
                    existing.preference_value = value
                    existing.confidence = 0.5
            existing.last_observed = datetime.now()
        else:
            entry = UserPreference(
                genesis_id=genesis_id,
                preference_key=key,
                preference_value=value,
                confidence=0.5,
            )
            self.session.add(entry)

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()

    def get_preferences(self, genesis_id: str) -> Dict[str, Any]:
        """Get all preferences for a user."""
        prefs = self.session.query(UserPreference).filter(
            UserPreference.genesis_id == genesis_id,
            UserPreference.confidence >= 0.4,
        ).all()

        return {
            p.preference_key: {
                "value": p.preference_value,
                "confidence": p.confidence,
                "observations": p.observation_count,
            }
            for p in prefs
        }

    def get_system_prompt_additions(self, genesis_id: str) -> str:
        """Get personalization additions for the system prompt."""
        prefs = self.get_preferences(genesis_id)
        if not prefs:
            return ""

        additions = []
        lang = prefs.get("preferred_language")
        if lang and lang["confidence"] >= 0.6:
            additions.append(f"The user prefers {lang['value']}.")

        detail = prefs.get("detail_preference")
        if detail and detail["confidence"] >= 0.6:
            additions.append(f"The user prefers {detail['value']} responses.")

        interests = [k.replace("interest_", "") for k, v in prefs.items()
                     if k.startswith("interest_") and v["confidence"] >= 0.5]
        if interests:
            additions.append(f"The user is interested in: {', '.join(interests)}.")

        return " ".join(additions)
