"""
Proactive Learning System for Grace
=====================================

Learns in real-time from all code interactions, user inputs,
and system events to continuously improve predictions.

Key Capabilities:
1. Real-time pattern extraction from code
2. User intent learning
3. Failure pattern learning
4. Success pattern reinforcement
5. Research storage and retrieval
6. Continuous model improvement
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class LearningEvent(str, Enum):
    """Types of events to learn from."""
    CODE_GENERATED = "code_generated"
    CODE_EDITED = "code_edited"
    ERROR_OCCURRED = "error_occurred"
    ERROR_FIXED = "error_fixed"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    USER_FEEDBACK = "user_feedback"
    PREDICTION_VERIFIED = "prediction_verified"
    PATTERN_DISCOVERED = "pattern_discovered"
    RESEARCH_ADDED = "research_added"


class LearningPriority(str, Enum):
    """Priority levels for learning."""
    CRITICAL = "critical"   # Learn immediately
    HIGH = "high"           # Learn soon
    NORMAL = "normal"       # Queue for batch learning
    LOW = "low"             # Learn when idle


@dataclass
class LearningItem:
    """An item to learn from."""
    item_id: str
    event_type: LearningEvent
    priority: LearningPriority
    content: str
    context: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[str] = None
    user_input: Optional[str] = None
    learned: bool = False
    patterns_extracted: List[str] = field(default_factory=list)
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    learned_at: Optional[datetime] = None


@dataclass
class LearnedPattern:
    """A pattern learned from events."""
    pattern_id: str
    pattern_type: str  # code, error, success, user_intent
    pattern_hash: str
    description: str
    occurrences: int = 1
    success_rate: float = 0.5
    associated_files: List[str] = field(default_factory=list)
    associated_errors: List[str] = field(default_factory=list)
    associated_fixes: List[str] = field(default_factory=list)
    confidence: float = 0.5
    last_seen: datetime = field(default_factory=datetime.utcnow)
    genesis_key_id: Optional[str] = None

    def reinforce(self, success: bool):
        """Reinforce pattern based on outcome."""
        self.occurrences += 1
        if success:
            self.success_rate = (self.success_rate * (self.occurrences - 1) + 1.0) / self.occurrences
            self.confidence = min(0.99, self.confidence + 0.02)
        else:
            self.success_rate = (self.success_rate * (self.occurrences - 1)) / self.occurrences
            self.confidence = max(0.1, self.confidence - 0.05)
        self.last_seen = datetime.utcnow()


@dataclass
class UserIntentModel:
    """Model of user intent patterns."""
    intent_id: str
    intent_keywords: List[str]
    common_actions: List[str]
    predicted_next_actions: List[str]
    context_patterns: Dict[str, int] = field(default_factory=dict)
    occurrence_count: int = 1
    accuracy: float = 0.5


class ProactiveLearningSystem:
    """
    Real-time proactive learning from all interactions.

    Continuously learns from:
    - Code generation results
    - Error patterns and fixes
    - User feedback and corrections
    - Prediction accuracy
    - System events
    """

    def __init__(
        self,
        session=None,
        genesis_service=None,
        oracle_core=None,
        vector_db=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self._genesis_service = genesis_service
        self._oracle = oracle_core
        self._vector_db = vector_db
        self.repo_path = repo_path or Path.cwd()

        # Learning storage
        self.research_path = self.repo_path / "ai_research" / "learnings"
        self.research_path.mkdir(parents=True, exist_ok=True)

        # Learning queue
        self._learning_queue: List[LearningItem] = []
        self._is_processing = False

        # Learned patterns
        self._patterns: Dict[str, LearnedPattern] = {}
        self._user_intents: Dict[str, UserIntentModel] = {}

        # Real-time learning stats
        self._session_learnings = defaultdict(list)

        # Pattern extractors
        self._extractors: Dict[str, Callable] = {
            "code": self._extract_code_patterns,
            "error": self._extract_error_patterns,
            "intent": self._extract_intent_patterns
        }

        # Metrics
        self.metrics = {
            "items_processed": 0,
            "patterns_learned": 0,
            "patterns_reinforced": 0,
            "research_stored": 0,
            "predictions_improved": 0
        }

        # Learning configuration
        self.config = {
            "batch_size": 10,
            "auto_persist_interval": 300,  # 5 minutes
            "min_pattern_occurrences": 3,
            "pattern_decay_days": 30
        }

        logger.info("[PROACTIVE-LEARNING] System initialized")

    async def learn(
        self,
        event_type: LearningEvent,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        priority: LearningPriority = LearningPriority.NORMAL,
        source_file: Optional[str] = None,
        user_input: Optional[str] = None
    ) -> LearningItem:
        """
        Submit an event for learning.

        This is the main entry point for the learning system.
        """
        item = LearningItem(
            item_id=f"LEARN-{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            priority=priority,
            content=content,
            context=context or {},
            source_file=source_file,
            user_input=user_input
        )

        # Create Genesis key for learning event
        if self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType
                key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.LEARNING_EVENT,
                    what_description=f"Learning: {event_type.value}",
                    who_actor="ProactiveLearning",
                    where_location=source_file or "system",
                    why_reason="Continuous improvement",
                    how_method="Real-time pattern extraction",
                    context_data={
                        "item_id": item.item_id,
                        "event_type": event_type.value
                    },
                    session=self.session
                )
                item.genesis_key_id = key.key_id
            except Exception as e:
                logger.debug(f"[PROACTIVE-LEARNING] Genesis key creation skipped: {e}")

        # Process based on priority
        if priority == LearningPriority.CRITICAL:
            await self._process_item(item)
        else:
            self._learning_queue.append(item)

            # Process queue if enough items
            if len(self._learning_queue) >= self.config["batch_size"]:
                await self._process_queue()

        logger.debug(f"[PROACTIVE-LEARNING] Queued {event_type.value} for learning")

        return item

    async def _process_queue(self):
        """Process queued learning items."""
        if self._is_processing or not self._learning_queue:
            return

        self._is_processing = True

        try:
            # Sort by priority
            queue = sorted(
                self._learning_queue,
                key=lambda x: [
                    LearningPriority.CRITICAL,
                    LearningPriority.HIGH,
                    LearningPriority.NORMAL,
                    LearningPriority.LOW
                ].index(x.priority)
            )

            # Process batch
            batch = queue[:self.config["batch_size"]]
            for item in batch:
                await self._process_item(item)

            # Remove processed items
            processed_ids = {item.item_id for item in batch}
            self._learning_queue = [
                item for item in self._learning_queue
                if item.item_id not in processed_ids
            ]

        finally:
            self._is_processing = False

    async def _process_item(self, item: LearningItem):
        """Process a single learning item."""
        try:
            # Extract patterns based on event type
            if item.event_type in [LearningEvent.CODE_GENERATED, LearningEvent.CODE_EDITED]:
                patterns = await self._extract_code_patterns(item)
            elif item.event_type in [LearningEvent.ERROR_OCCURRED, LearningEvent.ERROR_FIXED]:
                patterns = await self._extract_error_patterns(item)
            elif item.event_type == LearningEvent.USER_FEEDBACK:
                patterns = await self._extract_intent_patterns(item)
            elif item.event_type == LearningEvent.PREDICTION_VERIFIED:
                await self._process_prediction_feedback(item)
                patterns = []
            else:
                patterns = await self._extract_general_patterns(item)

            item.patterns_extracted = patterns
            item.learned = True
            item.learned_at = datetime.utcnow()

            # Store patterns
            for pattern in patterns:
                await self._store_pattern(pattern, item)

            # Store research if significant
            if len(patterns) >= 2 or item.priority == LearningPriority.CRITICAL:
                await self._store_research(item)

            self.metrics["items_processed"] += 1

        except Exception as e:
            logger.error(f"[PROACTIVE-LEARNING] Item processing failed: {e}")

    async def _extract_code_patterns(self, item: LearningItem) -> List[str]:
        """Extract patterns from code."""
        patterns = []
        content = item.content

        # Structural patterns
        if "class " in content:
            classes = len([l for l in content.split("\n") if l.strip().startswith("class ")])
            patterns.append(f"class_count:{classes}")

        if "def " in content:
            functions = len([l for l in content.split("\n") if "def " in l])
            patterns.append(f"function_count:{functions}")

        # Error handling patterns
        if "try:" in content:
            patterns.append("uses_try_except")
        if "raise " in content:
            patterns.append("raises_exceptions")

        # Async patterns
        if "async def" in content:
            patterns.append("uses_async")
        if "await " in content:
            patterns.append("uses_await")

        # Import patterns
        import_count = len([l for l in content.split("\n") if l.strip().startswith(("import ", "from "))])
        if import_count > 10:
            patterns.append("many_imports")

        # Documentation patterns
        if '"""' in content or "'''" in content:
            patterns.append("has_docstrings")

        # Type hint patterns
        if "-> " in content or ": " in content:
            patterns.append("uses_type_hints")

        return patterns

    async def _extract_error_patterns(self, item: LearningItem) -> List[str]:
        """Extract patterns from errors."""
        patterns = []
        content = item.content.lower()

        # Error type patterns
        error_types = [
            "typeerror", "valueerror", "keyerror", "indexerror",
            "attributeerror", "importerror", "syntaxerror", "nameerror",
            "filenotfounderror", "connectionerror", "timeout"
        ]

        for error_type in error_types:
            if error_type in content:
                patterns.append(f"error:{error_type}")

        # Context patterns
        if item.source_file:
            file_type = Path(item.source_file).suffix
            patterns.append(f"error_in:{file_type}")

        # Fix patterns (if this is error_fixed event)
        if item.event_type == LearningEvent.ERROR_FIXED:
            if item.context.get("fix_method"):
                patterns.append(f"fix_method:{item.context['fix_method']}")

            # Extract fix from context
            if item.context.get("fix_code"):
                fix_patterns = await self._extract_code_patterns(
                    LearningItem(
                        item_id="temp",
                        event_type=LearningEvent.CODE_GENERATED,
                        priority=LearningPriority.LOW,
                        content=item.context["fix_code"]
                    )
                )
                patterns.extend([f"fix_{p}" for p in fix_patterns])

        return patterns

    async def _extract_intent_patterns(self, item: LearningItem) -> List[str]:
        """Extract patterns from user intent/feedback."""
        patterns = []
        user_input = item.user_input or item.content

        if not user_input:
            return patterns

        user_lower = user_input.lower()

        # Action intent patterns
        action_keywords = {
            "create": ["create", "add", "new", "generate", "make"],
            "modify": ["change", "update", "modify", "edit", "fix"],
            "delete": ["remove", "delete", "drop", "clear"],
            "read": ["show", "display", "get", "find", "search"],
            "test": ["test", "verify", "check", "validate"],
            "deploy": ["deploy", "release", "publish", "ship"]
        }

        for action, keywords in action_keywords.items():
            if any(kw in user_lower for kw in keywords):
                patterns.append(f"intent:{action}")

        # Target patterns
        target_keywords = {
            "function": ["function", "method", "def"],
            "class": ["class", "object", "model"],
            "api": ["api", "endpoint", "route"],
            "database": ["database", "db", "query", "table"],
            "test": ["test", "spec", "unittest"]
        }

        for target, keywords in target_keywords.items():
            if any(kw in user_lower for kw in keywords):
                patterns.append(f"target:{target}")

        # Complexity patterns
        if len(user_input) > 200:
            patterns.append("complex_request")
        if "?" in user_input:
            patterns.append("question")

        return patterns

    async def _extract_general_patterns(self, item: LearningItem) -> List[str]:
        """Extract general patterns from any event."""
        patterns = []

        # Time-based patterns
        hour = item.created_at.hour
        if 9 <= hour < 17:
            patterns.append("business_hours")
        else:
            patterns.append("off_hours")

        # Source patterns
        if item.source_file:
            patterns.append(f"source:{Path(item.source_file).suffix}")

        return patterns

    async def _process_prediction_feedback(self, item: LearningItem):
        """Process feedback on a prediction's accuracy."""
        context = item.context

        was_accurate = context.get("was_accurate", False)
        prediction_id = context.get("prediction_id")
        pattern_ids = context.get("pattern_ids", [])

        # Reinforce or weaken patterns
        for pattern_id in pattern_ids:
            if pattern_id in self._patterns:
                self._patterns[pattern_id].reinforce(was_accurate)
                self.metrics["patterns_reinforced"] += 1

        # Notify Oracle for learning
        if self._oracle and prediction_id:
            await self._oracle.learn_from_outcome(
                insight_id=prediction_id,
                was_accurate=was_accurate,
                actual_outcome=context.get("actual_outcome")
            )

        self.metrics["predictions_improved"] += 1

    async def _store_pattern(self, pattern_str: str, item: LearningItem):
        """Store or reinforce a pattern."""
        pattern_hash = hashlib.md5(pattern_str.encode()).hexdigest()[:12]

        if pattern_hash in self._patterns:
            # Reinforce existing pattern
            existing = self._patterns[pattern_hash]
            existing.occurrences += 1
            existing.last_seen = datetime.utcnow()

            if item.source_file:
                if item.source_file not in existing.associated_files:
                    existing.associated_files.append(item.source_file)

            self.metrics["patterns_reinforced"] += 1

        else:
            # Create new pattern
            pattern = LearnedPattern(
                pattern_id=f"PAT-{pattern_hash}",
                pattern_type=self._get_pattern_type(item.event_type),
                pattern_hash=pattern_hash,
                description=pattern_str,
                associated_files=[item.source_file] if item.source_file else [],
                genesis_key_id=item.genesis_key_id
            )

            self._patterns[pattern_hash] = pattern
            self.metrics["patterns_learned"] += 1

            logger.debug(f"[PROACTIVE-LEARNING] New pattern: {pattern_str}")

    def _get_pattern_type(self, event_type: LearningEvent) -> str:
        """Get pattern type from event type."""
        if event_type in [LearningEvent.CODE_GENERATED, LearningEvent.CODE_EDITED]:
            return "code"
        elif event_type in [LearningEvent.ERROR_OCCURRED, LearningEvent.ERROR_FIXED]:
            return "error"
        elif event_type == LearningEvent.USER_FEEDBACK:
            return "intent"
        else:
            return "general"

    async def _store_research(self, item: LearningItem):
        """Store learning as research entry."""
        if not self._oracle:
            return

        try:
            await self._oracle.store_research(
                topic=f"Learning from {item.event_type.value}",
                findings=f"Patterns discovered: {', '.join(item.patterns_extracted)}",
                code_examples=[item.content[:500]] if item.content else [],
                source_files=[item.source_file] if item.source_file else []
            )
            self.metrics["research_stored"] += 1
        except Exception as e:
            logger.warning(f"[PROACTIVE-LEARNING] Research storage failed: {e}")

    async def learn_from_user_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Learn from user input in real-time.

        Extracts intent, predicts needs, and stores learnings.
        """
        # Extract intent patterns
        item = await self.learn(
            event_type=LearningEvent.USER_FEEDBACK,
            content=user_input,
            context=context,
            priority=LearningPriority.HIGH,
            user_input=user_input
        )

        # Predict what user might need
        predictions = self._predict_user_needs(user_input)

        # Update user intent model
        self._update_user_intent(user_input, context or {})

        return {
            "learning_id": item.item_id,
            "patterns_found": item.patterns_extracted,
            "predictions": predictions
        }

    def _predict_user_needs(self, user_input: str) -> List[str]:
        """Predict what the user might need next."""
        predictions = []
        user_lower = user_input.lower()

        # Based on learned intent patterns
        for intent_id, intent in self._user_intents.items():
            if any(kw in user_lower for kw in intent.intent_keywords):
                predictions.extend(intent.predicted_next_actions)

        # Common patterns
        if "create" in user_lower or "add" in user_lower:
            predictions.append("User may want to test the new code")
            predictions.append("User may need to update imports")

        if "error" in user_lower or "bug" in user_lower:
            predictions.append("User may need stack trace analysis")
            predictions.append("User may want to add error handling")

        if "test" in user_lower:
            predictions.append("User may need test fixtures")
            predictions.append("User may want to run all tests")

        return list(set(predictions))[:5]

    def _update_user_intent(self, user_input: str, context: Dict[str, Any]):
        """Update user intent model."""
        # Extract keywords
        words = set(user_input.lower().split())
        action_words = words & {"create", "add", "fix", "update", "delete", "show", "test"}

        if not action_words:
            return

        intent_key = "_".join(sorted(action_words))

        if intent_key in self._user_intents:
            self._user_intents[intent_key].occurrence_count += 1
            for word in words:
                self._user_intents[intent_key].context_patterns[word] = \
                    self._user_intents[intent_key].context_patterns.get(word, 0) + 1
        else:
            self._user_intents[intent_key] = UserIntentModel(
                intent_id=f"INTENT-{uuid.uuid4().hex[:8]}",
                intent_keywords=list(action_words),
                common_actions=[intent_key],
                predicted_next_actions=[],
                context_patterns={w: 1 for w in words}
            )

    async def get_relevant_patterns(
        self,
        code: Optional[str] = None,
        error: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> List[LearnedPattern]:
        """Get patterns relevant to the current context."""
        relevant = []

        for pattern in self._patterns.values():
            relevance_score = 0.0

            # Check file association
            if file_path and file_path in pattern.associated_files:
                relevance_score += 0.3

            # Check error association
            if error and pattern.pattern_type == "error":
                if any(e in error.lower() for e in pattern.associated_errors):
                    relevance_score += 0.4

            # Check code patterns
            if code and pattern.pattern_type == "code":
                if pattern.description.split(":")[0] in code:
                    relevance_score += 0.2

            # Factor in confidence and recency
            relevance_score += pattern.confidence * 0.2

            days_ago = (datetime.utcnow() - pattern.last_seen).days
            if days_ago < 7:
                relevance_score += 0.1

            if relevance_score > 0.3:
                pattern.relevance_score = relevance_score
                relevant.append(pattern)

        # Sort by relevance
        relevant.sort(key=lambda p: getattr(p, 'relevance_score', 0), reverse=True)

        return relevant[:10]

    async def suggest_based_on_learning(
        self,
        current_code: str,
        current_file: Optional[str] = None
    ) -> List[str]:
        """Suggest improvements based on learned patterns."""
        suggestions = []

        # Get relevant patterns
        patterns = await self.get_relevant_patterns(code=current_code, file_path=current_file)

        for pattern in patterns:
            if pattern.pattern_type == "error" and pattern.success_rate > 0.7:
                # This error pattern has successful fixes
                for fix in pattern.associated_fixes[:2]:
                    suggestions.append(f"Consider: {fix}")

            elif pattern.pattern_type == "code" and pattern.occurrences >= 3:
                # Common code pattern
                if "error:" in pattern.description.lower() and pattern.success_rate < 0.5:
                    suggestions.append(f"Avoid pattern: {pattern.description}")

        return suggestions

    def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning status."""
        return {
            "metrics": self.metrics,
            "queue_size": len(self._learning_queue),
            "patterns_known": len(self._patterns),
            "intent_models": len(self._user_intents),
            "is_processing": self._is_processing,
            "recent_patterns": [
                {
                    "description": p.description,
                    "occurrences": p.occurrences,
                    "success_rate": p.success_rate
                }
                for p in sorted(
                    self._patterns.values(),
                    key=lambda x: x.last_seen,
                    reverse=True
                )[:5]
            ]
        }

    async def flush(self):
        """Process all remaining queue items."""
        while self._learning_queue:
            await self._process_queue()

    async def persist_learnings(self):
        """Persist all learnings to disk."""
        try:
            # Save patterns
            patterns_file = self.research_path / "patterns.json"
            with open(patterns_file, "w") as f:
                json.dump(
                    {
                        pid: {
                            "pattern_id": p.pattern_id,
                            "pattern_type": p.pattern_type,
                            "description": p.description,
                            "occurrences": p.occurrences,
                            "success_rate": p.success_rate,
                            "confidence": p.confidence,
                            "last_seen": p.last_seen.isoformat()
                        }
                        for pid, p in self._patterns.items()
                    },
                    f,
                    indent=2
                )

            # Save intents
            intents_file = self.research_path / "intents.json"
            with open(intents_file, "w") as f:
                json.dump(
                    {
                        iid: {
                            "intent_id": i.intent_id,
                            "keywords": i.intent_keywords,
                            "actions": i.common_actions,
                            "occurrence_count": i.occurrence_count
                        }
                        for iid, i in self._user_intents.items()
                    },
                    f,
                    indent=2
                )

            logger.info("[PROACTIVE-LEARNING] Learnings persisted to disk")

        except Exception as e:
            logger.error(f"[PROACTIVE-LEARNING] Persistence failed: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get learning metrics."""
        return {
            **self.metrics,
            "patterns_count": len(self._patterns),
            "intent_models": len(self._user_intents),
            "queue_size": len(self._learning_queue),
            "avg_pattern_confidence": (
                sum(p.confidence for p in self._patterns.values()) / len(self._patterns)
                if self._patterns else 0.0
            )
        }
