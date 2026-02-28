"""
Idle Learner — Kimi teaches the coding agent during idle time.

When Grace has no active user requests, Kimi proactively:
1. Identifies knowledge gaps from failed code generations
2. Teaches coding patterns, best practices, frameworks
3. Reviews past outputs and suggests improvements
4. Builds up procedural memory (learned skills)
5. Enriches Magma with causal relationships about code

Controlled by TimeSense — only runs during off-hours or
when no user activity for 5+ minutes.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Topics Kimi will teach when idle
CODING_CURRICULUM = [
    # Fundamentals
    {"topic": "Python error handling best practices", "category": "python"},
    {"topic": "REST API design patterns and conventions", "category": "api"},
    {"topic": "SQL injection prevention techniques", "category": "security"},
    {"topic": "Git branching strategies for teams", "category": "devops"},
    {"topic": "Unit testing patterns and anti-patterns", "category": "testing"},

    # Architecture
    {"topic": "Clean architecture principles with code examples", "category": "architecture"},
    {"topic": "Microservices vs monolith trade-offs", "category": "architecture"},
    {"topic": "Event-driven architecture patterns", "category": "architecture"},
    {"topic": "Database schema design best practices", "category": "database"},
    {"topic": "Caching strategies and cache invalidation", "category": "performance"},

    # Frontend
    {"topic": "React component patterns and hooks best practices", "category": "frontend"},
    {"topic": "CSS layout techniques: flexbox and grid", "category": "frontend"},
    {"topic": "Frontend state management patterns", "category": "frontend"},
    {"topic": "Accessibility (a11y) in web applications", "category": "frontend"},

    # DevOps
    {"topic": "Docker containerization best practices", "category": "devops"},
    {"topic": "CI/CD pipeline design patterns", "category": "devops"},
    {"topic": "Environment variable management and secrets", "category": "devops"},

    # Security
    {"topic": "Authentication and authorization patterns (JWT, OAuth)", "category": "security"},
    {"topic": "Input validation and sanitization", "category": "security"},
    {"topic": "CORS configuration and security headers", "category": "security"},

    # Performance
    {"topic": "Database query optimization techniques", "category": "performance"},
    {"topic": "Async programming patterns in Python", "category": "performance"},
    {"topic": "Memory management and garbage collection", "category": "performance"},

    # AI/ML
    {"topic": "Prompt engineering best practices", "category": "ai"},
    {"topic": "RAG system optimization techniques", "category": "ai"},
    {"topic": "LLM output validation and hallucination detection", "category": "ai"},
]


class IdleLearner:
    """
    Proactive learning system that runs during idle time.
    Kimi teaches Grace coding skills autonomously.
    """

    def __init__(self):
        self._topics_taught: List[str] = []
        self._current_index: int = 0
        self._last_activity: float = time.time()
        self._learning_log: List[Dict] = []
        self._is_learning: bool = False

    def mark_activity(self):
        """Call this on any user request to reset idle timer."""
        self._last_activity = time.time()

    def is_idle(self, idle_threshold_seconds: int = 300) -> bool:
        """Check if the system has been idle long enough to learn."""
        return (time.time() - self._last_activity) > idle_threshold_seconds

    def should_learn(self) -> bool:
        """Check if conditions are right for idle learning."""
        if self._is_learning:
            return False

        if not self.is_idle():
            return False

        # Check TimeSense — prefer off-hours
        try:
            from cognitive.time_sense import TimeSense
            ctx = TimeSense.now_context()
            # Always learn during off-hours, only learn during business hours if idle 10+ min
            if ctx.get("is_business_hours") and not self.is_idle(600):
                return False
        except Exception:
            pass

        return True

    def learn_next(self) -> Optional[Dict[str, Any]]:
        """
        Teach the next topic from the curriculum.
        Returns the learning result or None if not ready.
        """
        if not self.should_learn():
            return None

        if self._current_index >= len(CODING_CURRICULUM):
            # Cycle back and learn from gaps
            gaps = self._identify_gaps()
            if gaps:
                return self._learn_from_gap(gaps[0])
            self._current_index = 0  # Restart curriculum

        topic_data = CODING_CURRICULUM[self._current_index]
        topic = topic_data["topic"]

        # Skip if already taught recently
        if topic in self._topics_taught[-20:]:
            self._current_index += 1
            return self.learn_next()

        result = self._teach(topic, topic_data.get("category", "general"))
        self._current_index += 1
        return result

    def _teach(self, topic: str, category: str) -> Dict[str, Any]:
        """Have Kimi teach a specific topic."""
        self._is_learning = True
        result = {"topic": topic, "category": category, "timestamp": datetime.utcnow().isoformat()}

        try:
            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()

            teaching = kimi.teach_topic(
                topic=topic,
                context=f"Category: {category}. Teach with concrete code examples. "
                        f"Focus on patterns the coding agent can apply directly."
            )

            if teaching.get("knowledge"):
                result["success"] = True
                result["knowledge_length"] = len(teaching["knowledge"])
                self._topics_taught.append(topic)

                # Store as procedural memory (skill)
                try:
                    from cognitive.magma_bridge import store_procedure
                    store_procedure(
                        name=f"Skill: {topic[:50]}",
                        description=topic,
                        steps=["Apply learned pattern", "Verify output", "Adapt to context"],
                    )
                except Exception:
                    pass

                # Track via genesis
                try:
                    from api._genesis_tracker import track
                    track(
                        key_type="system",
                        what=f"Idle learning: {topic}",
                        how="IdleLearner → Kimi → Magma",
                        output_data={"category": category, "length": len(teaching["knowledge"])},
                        tags=["idle_learning", category],
                    )
                except Exception:
                    pass

                # Route research output to Librarian for organisation
                try:
                    from cognitive.librarian_autonomous import AutonomousLibrarian
                    librarian = AutonomousLibrarian()
                    from pathlib import Path
                    from settings import settings
                    kb = Path(settings.KNOWLEDGE_BASE_PATH)
                    research_dir = kb / "research" / category.replace(" ", "_")
                    research_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = topic.replace(" ", "_").replace("/", "_")[:40]
                    research_file = research_dir / f"{safe_name}.md"
                    research_file.write_text(f"# {topic}\n\n{teaching['knowledge']}")
                    librarian.organise_file(str(research_file))
                except Exception:
                    pass

                logger.info(f"[IDLE LEARNER] Taught: {topic} ({len(teaching['knowledge'])} chars)")
            else:
                result["success"] = False
                result["reason"] = "Kimi returned no knowledge"

        except Exception as e:
            result["success"] = False
            result["reason"] = str(e)

        self._is_learning = False
        self._learning_log.append(result)
        return result

    def _identify_gaps(self) -> List[str]:
        """Find knowledge gaps from failed generations."""
        gaps = []
        try:
            db = _get_db()
            if db:
                from sqlalchemy import text
                rows = db.execute(text("""
                    SELECT input_context FROM learning_examples
                    WHERE example_type LIKE '%negative%' AND trust_score < 0.5
                    ORDER BY created_at DESC LIMIT 5
                """)).fetchall()
                for r in rows:
                    if r[0]:
                        gaps.append(r[0][:200])
                db.close()
        except Exception:
            pass
        return gaps

    def _learn_from_gap(self, gap_description: str) -> Dict[str, Any]:
        """Learn specifically about a knowledge gap."""
        return self._teach(
            f"How to handle: {gap_description[:100]}",
            "gap_fill"
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "topics_taught": len(self._topics_taught),
            "curriculum_progress": f"{self._current_index}/{len(CODING_CURRICULUM)}",
            "is_learning": self._is_learning,
            "is_idle": self.is_idle(),
            "last_activity_seconds_ago": int(time.time() - self._last_activity),
            "recent_topics": self._topics_taught[-5:],
            "total_sessions": len(self._learning_log),
        }

    def get_log(self) -> List[Dict]:
        return self._learning_log[-20:]


def _get_db():
    try:
        from database.session import SessionLocal
        if SessionLocal:
            return SessionLocal()
    except Exception:
        pass
    return None


_learner = None

def get_idle_learner() -> IdleLearner:
    global _learner
    if _learner is None:
        _learner = IdleLearner()
    return _learner
