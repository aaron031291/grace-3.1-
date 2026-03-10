"""
Predictive Context Loader - Proactive Knowledge Fetching

Grace doesn't just wait for queries - she thinks ahead!

When Grace encounters a whitelisted trigger (e.g., "REST API design"),
she proactively pre-fetches related topics and brings them into context
BEFORE they're explicitly requested.

This is deterministic preemptive fetching:
1. Detect trigger topic
2. Identify neighboring/related topics
3. Pre-fetch relevant knowledge
4. Cache in active context
5. Ready when needed
"""

from typing import List, Dict, Any, Set, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from collections import defaultdict
import logging

from sqlalchemy.orm import Session
from retrieval.retriever import DocumentRetriever
from cognitive.learning_memory import LearningExample

logger = logging.getLogger(__name__)


@dataclass
class PreFetchedContext:
    """Pre-fetched context ready for use."""
    topic: str
    related_topics: List[str]
    knowledge_chunks: List[Dict[str, Any]]
    trust_score: float
    operational_confidence: float
    fetched_at: datetime
    expires_at: datetime


class TopicRelationshipGraph:
    """
    Maps relationships between topics.

    Examples:
    - "REST API" → ["HTTP methods", "Authentication", "JSON", "CRUD"]
    - "Python functions" → ["parameters", "return values", "decorators", "lambdas"]
    - "Database design" → ["normalization", "indexes", "foreign keys", "transactions"]
    """

    def __init__(self):
        # Topic relationships (manually defined + learned from co-occurrence)
        self.relationships = {
            # API Design
            "REST API": [
                "HTTP methods", "HTTP status codes", "API authentication",
                "JSON", "API versioning", "CRUD operations", "RESTful principles"
            ],
            "API design": [
                "REST API", "GraphQL", "API documentation", "API security",
                "rate limiting", "pagination", "error handling"
            ],
            "API authentication": [
                "JWT", "OAuth", "API keys", "session management",
                "token refresh", "CORS"
            ],

            # Backend Development
            "backend development": [
                "REST API", "databases", "server architecture", "microservices",
                "caching", "message queues", "load balancing"
            ],
            "microservices": [
                "service mesh", "API gateway", "service discovery",
                "distributed systems", "containerization", "Docker"
            ],

            # Databases
            "database design": [
                "normalization", "indexes", "foreign keys", "transactions",
                "SQL", "query optimization", "database schema"
            ],
            "SQL": [
                "SELECT queries", "JOIN operations", "transactions",
                "indexes", "stored procedures", "database normalization"
            ],

            # Python Programming
            "Python": [
                "Python functions", "Python classes", "Python modules",
                "Python decorators", "Python generators", "error handling"
            ],
            "Python functions": [
                "parameters", "return values", "decorators", "lambda functions",
                "closures", "function composition"
            ],

            # Testing
            "testing": [
                "unit testing", "integration testing", "test fixtures",
                "mocking", "test coverage", "TDD"
            ],
            "unit testing": [
                "test fixtures", "assertions", "test isolation",
                "mocking", "pytest", "test coverage"
            ],

            # Architecture
            "software architecture": [
                "design patterns", "SOLID principles", "clean architecture",
                "domain driven design", "microservices", "monolithic architecture"
            ],
            "design patterns": [
                "singleton", "factory", "observer", "strategy",
                "dependency injection", "repository pattern"
            ],

            # DevOps
            "DevOps": [
                "CI/CD", "Docker", "Kubernetes", "infrastructure as code",
                "monitoring", "logging", "deployment strategies"
            ],
            "Docker": [
                "containers", "Dockerfile", "docker-compose", "images",
                "volumes", "networking", "orchestration"
            ],
        }

        # Learned relationships from co-occurrence (populated dynamically)
        self.learned_relationships: Dict[str, Set[str]] = defaultdict(set)

    def get_related_topics(self, topic: str, depth: int = 1) -> List[str]:
        """
        Get topics related to this topic.

        Args:
            topic: Source topic
            depth: How many hops to traverse (1 = immediate neighbors, 2 = neighbors of neighbors)

        Returns:
            List of related topics
        """
        related = set()

        # Get direct relationships
        topic_lower = topic.lower()
        for key, values in self.relationships.items():
            if topic_lower in key.lower():
                related.update(values)

        # Add learned relationships
        if topic_lower in self.learned_relationships:
            related.update(self.learned_relationships[topic_lower])

        # If depth > 1, get neighbors of neighbors
        if depth > 1:
            for related_topic in list(related):
                related.update(self.get_related_topics(related_topic, depth - 1))

        return list(related)

    def learn_relationship(self, topic1: str, topic2: str):
        """
        Learn a relationship between two topics.

        Called when topics frequently appear together.
        """
        self.learned_relationships[topic1.lower()].add(topic2)
        self.learned_relationships[topic2.lower()].add(topic1)


class WhitelistTrigger:
    """
    Defines triggers that activate predictive fetching.

    When Grace encounters these topics, she proactively fetches related content.
    """

    def __init__(self):
        # High-priority topics that trigger aggressive pre-fetching
        self.high_priority_triggers = {
            "REST API", "API design", "backend development",
            "database design", "microservices", "testing",
            "Python", "Docker", "Kubernetes"
        }

        # Medium-priority triggers
        self.medium_priority_triggers = {
            "authentication", "caching", "monitoring",
            "design patterns", "clean architecture"
        }

        # Learning-phase triggers (Grace is actively studying)
        self.learning_triggers = {
            "tutorial", "example", "how to", "guide",
            "introduction", "basics", "fundamentals"
        }

    def should_prefetch(self, query: str, context: Dict[str, Any]) -> bool:
        """
        Determine if we should trigger predictive fetching.

        Args:
            query: User query or current topic
            context: Additional context (task type, complexity, etc.)

        Returns:
            True if predictive fetching should activate
        """
        query_lower = query.lower()

        # High priority triggers - always prefetch
        for trigger in self.high_priority_triggers:
            if trigger.lower() in query_lower:
                return True

        # Medium priority - prefetch if complexity is high
        if context.get('complexity', 0.5) > 0.6:
            for trigger in self.medium_priority_triggers:
                if trigger.lower() in query_lower:
                    return True

        # Learning mode - prefetch when Grace is studying
        if context.get('task_type') == 'learning':
            for trigger in self.learning_triggers:
                if trigger in query_lower:
                    return True

        return False

    def get_prefetch_depth(self, query: str, context: Dict[str, Any]) -> int:
        """
        Determine how many relationship hops to pre-fetch.

        Returns:
            1 = immediate neighbors only
            2 = neighbors + neighbors of neighbors
            3 = deep prefetch (used for complex tasks)
        """
        query_lower = query.lower()

        # High priority + high complexity = deep prefetch
        if any(t.lower() in query_lower for t in self.high_priority_triggers):
            if context.get('complexity', 0.5) > 0.7:
                return 3
            return 2

        # Learning mode = medium depth
        if context.get('task_type') == 'learning':
            return 2

        # Default
        return 1


class PredictiveContextLoader:
    """
    Proactive knowledge fetching system.

    Grace thinks ahead and pre-fetches related knowledge
    before it's explicitly requested.
    """

    def __init__(
        self,
        session: Session,
        retriever: DocumentRetriever,
        cache_ttl_minutes: int = 30
    ):
        self.session = session
        self.retriever = retriever
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)

        # Components
        self.topic_graph = TopicRelationshipGraph()
        self.whitelist = WhitelistTrigger()

        # Context cache
        self.prefetched_cache: Dict[str, PreFetchedContext] = {}

        # Statistics
        self.prefetch_hits = 0  # How many times cached context was used
        self.prefetch_misses = 0  # How many times we needed to fetch on-demand

    def process_query(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a query with predictive fetching.

        1. Check if query triggers prefetch
        2. If yes, identify related topics
        3. Pre-fetch knowledge for all related topics
        4. Cache for future use
        5. Return main query result + prefetched context

        Args:
            query: Current query/topic
            context: Task context

        Returns:
            Enhanced result with prefetched context ready
        """
        logger.info(f"Processing query with predictive fetching: {query}")

        # Check if we should trigger predictive fetching
        should_prefetch = self.whitelist.should_prefetch(query, context)

        if not should_prefetch:
            logger.debug(f"No prefetch trigger for: {query}")
            return {"main_result": self._fetch_main_query(query), "prefetched": []}

        # PREDICTIVE FETCHING ACTIVATED
        logger.info(f"🔮 Predictive fetching activated for: {query}")

        # Determine prefetch depth
        depth = self.whitelist.get_prefetch_depth(query, context)

        # Identify related topics
        related_topics = self.topic_graph.get_related_topics(query, depth=depth)
        logger.info(f"📊 Identified {len(related_topics)} related topics (depth={depth})")

        # Pre-fetch knowledge for each related topic
        prefetched_contexts = []
        for topic in related_topics:
            # Check cache first
            if topic in self.prefetched_cache:
                cached = self.prefetched_cache[topic]
                if datetime.now(timezone.utc) < cached.expires_at:
                    logger.debug(f"[OK] Cache hit: {topic}")
                    self.prefetch_hits += 1
                    prefetched_contexts.append(cached)
                    continue

            # Not in cache or expired - fetch now
            logger.debug(f"→ Pre-fetching: {topic}")
            prefetched = self._prefetch_topic(topic)
            if prefetched:
                self.prefetched_cache[topic] = prefetched
                prefetched_contexts.append(prefetched)

        # Learn relationships from co-occurrence
        for topic in related_topics:
            self.topic_graph.learn_relationship(query, topic)

        # Get main query result
        main_result = self._fetch_main_query(query)

        logger.info(f"[OK] Pre-fetched {len(prefetched_contexts)} contexts ready")

        return {
            "main_result": main_result,
            "prefetched_contexts": prefetched_contexts,
            "ready_topics": [ctx.topic for ctx in prefetched_contexts],
            "statistics": {
                "prefetch_hits": self.prefetch_hits,
                "prefetch_misses": self.prefetch_misses,
                "cache_size": len(self.prefetched_cache)
            }
        }

    def _fetch_main_query(self, query: str) -> Dict[str, Any]:
        """Fetch main query result."""
        results = self.retriever.retrieve(
            query=query,
            limit=10,
            score_threshold=0.4
        )
        return results

    def _prefetch_topic(self, topic: str) -> Optional[PreFetchedContext]:
        """
        Pre-fetch knowledge for a topic.

        Retrieves relevant chunks and calculates trust scores.
        """
        try:
            # Retrieve knowledge chunks
            results = self.retriever.retrieve(
                query=topic,
                limit=15,  # More than main query (preparing for future)
                score_threshold=0.3  # Lower threshold for prefetch
            )

            chunks = results.get('chunks', [])
            if not chunks:
                return None

            # Calculate average trust score from learning examples
            trust_score, operational_confidence = self._calculate_topic_confidence(topic)

            # Create prefetched context
            context = PreFetchedContext(
                topic=topic,
                related_topics=self.topic_graph.get_related_topics(topic, depth=1),
                knowledge_chunks=chunks,
                trust_score=trust_score,
                operational_confidence=operational_confidence,
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + self.cache_ttl
            )

            return context

        except Exception as e:
            logger.error(f"Failed to prefetch topic {topic}: {e}")
            return None

    def _calculate_topic_confidence(self, topic: str) -> tuple[float, float]:
        """
        Calculate trust score and operational confidence for a topic.

        Queries learning_examples to see what Grace knows about this topic.
        """
        # Query learning examples for this topic
        examples = self.session.query(LearningExample).filter(
            LearningExample.input_context.contains({"topic": topic})
        ).all()

        if not examples:
            return 0.5, 0.3  # No knowledge yet

        # Calculate average trust and operational confidence
        avg_trust = sum(ex.trust_score for ex in examples) / len(examples)

        operational_confidences = []
        for ex in examples:
            if ex.example_metadata and 'operational_confidence' in ex.example_metadata:
                operational_confidences.append(ex.example_metadata['operational_confidence'])

        avg_operational = sum(operational_confidences) / len(operational_confidences) if operational_confidences else 0.3

        return avg_trust, avg_operational

    def get_cached_context(self, topic: str) -> Optional[PreFetchedContext]:
        """
        Get pre-fetched context if available.

        This is called when Grace actually needs the topic.
        If it's already cached, instant access!
        """
        if topic in self.prefetched_cache:
            context = self.prefetched_cache[topic]
            if datetime.now(timezone.utc) < context.expires_at:
                self.prefetch_hits += 1
                logger.info(f"🎯 CACHE HIT: {topic} was already prefetched!")
                return context
            else:
                # Expired - remove from cache
                del self.prefetched_cache[topic]

        self.prefetch_misses += 1
        logger.debug(f"Cache miss: {topic} not prefetched")
        return None

    def warmup_topics(self, topics: List[str]):
        """
        Warm up cache with specific topics.

        Useful when Grace starts a training session or begins a complex task.
        """
        logger.info(f"🔥 Warming up cache for {len(topics)} topics")
        for topic in topics:
            if topic not in self.prefetched_cache:
                prefetched = self._prefetch_topic(topic)
                if prefetched:
                    self.prefetched_cache[topic] = prefetched

    def clear_expired_cache(self):
        """Clear expired entries from cache."""
        now = datetime.now(timezone.utc)
        expired = [topic for topic, ctx in self.prefetched_cache.items() if now >= ctx.expires_at]
        for topic in expired:
            del self.prefetched_cache[topic]

        if expired:
            logger.info(f"Cleared {len(expired)} expired cache entries")

    def get_statistics(self) -> Dict[str, Any]:
        """Get prefetch statistics."""
        total_requests = self.prefetch_hits + self.prefetch_misses
        hit_rate = (self.prefetch_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_size": len(self.prefetched_cache),
            "total_hits": self.prefetch_hits,
            "total_misses": self.prefetch_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_topics": list(self.prefetched_cache.keys())
        }
