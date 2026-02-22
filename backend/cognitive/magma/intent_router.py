"""
Magma Memory - Intent-Aware Router

Routes queries to appropriate retrieval strategies based on:
1. Intent Classification - What type of information is being sought
2. Anchor Identification - Key concepts/entities in the query
3. Graph Selection - Which relation graphs to query
4. Retrieval Policy - How to traverse and combine results

This is the entry point for the Magma query process.

Classes:
- `QueryIntent`
- `AnchorType`
- `Anchor`
- `QueryAnalysis`
- `IntentClassifier`
- `AnchorIdentifier`
- `GraphSelector`
- `RetrievalPolicySelector`
- `IntentAwareRouter`

Key Methods:
- `classify()`
- `identify()`
- `select()`
- `select()`
- `analyze_query()`
- `route()`
- `get_anchor_embeddings_needed()`
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Types of query intents."""
    # Factual intents
    FACTUAL_LOOKUP = "factual_lookup"  # "What is X?"
    DEFINITION = "definition"  # "Define X"
    EXPLANATION = "explanation"  # "Explain X" / "How does X work?"

    # Relational intents
    RELATIONSHIP = "relationship"  # "How are X and Y related?"
    COMPARISON = "comparison"  # "Compare X and Y"
    SIMILARITY = "similarity"  # "What is similar to X?"

    # Temporal intents
    TEMPORAL_SEQUENCE = "temporal_sequence"  # "What happened after X?"
    TEMPORAL_RANGE = "temporal_range"  # "What happened between X and Y?"
    HISTORY = "history"  # "What is the history of X?"

    # Causal intents
    CAUSE = "cause"  # "What causes X?"
    EFFECT = "effect"  # "What are the effects of X?"
    REASON = "reason"  # "Why does X happen?"

    # Procedural intents
    HOW_TO = "how_to"  # "How do I do X?"
    STEPS = "steps"  # "What are the steps for X?"
    PROCESS = "process"  # "What is the process for X?"

    # Exploratory intents
    EXPLORE = "explore"  # General exploration
    LIST = "list"  # "List all X"
    FIND = "find"  # "Find X that matches Y"

    # Unknown
    UNKNOWN = "unknown"


class AnchorType(Enum):
    """Types of anchors identified in queries."""
    CONCEPT = "concept"  # Abstract concept
    ENTITY = "entity"  # Named entity (person, place, thing)
    EVENT = "event"  # Something that happened
    TIME = "time"  # Temporal reference
    ACTION = "action"  # Verb/action
    ATTRIBUTE = "attribute"  # Property/attribute


@dataclass
class Anchor:
    """An identified anchor in a query."""
    text: str
    anchor_type: AnchorType
    start_pos: int
    end_pos: int
    confidence: float = 0.5
    normalized_form: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryAnalysis:
    """Complete analysis of a query."""
    original_query: str
    normalized_query: str
    primary_intent: QueryIntent
    secondary_intents: List[QueryIntent]
    anchors: List[Anchor]
    target_graphs: List[str]  # semantic, temporal, causal, entity
    retrieval_policy: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentClassifier:
    """
    Classifies query intent using pattern matching and heuristics.

    For production, this would be replaced with an ML model.
    """

    def __init__(self):
        # Intent patterns (regex -> intent mapping)
        self.intent_patterns = {
            # Factual
            QueryIntent.DEFINITION: [
                r"(?:what is|define|meaning of|definition of)\s+",
                r"^what\s+(?:does|is)\s+\w+\s+mean",
            ],
            QueryIntent.EXPLANATION: [
                r"(?:explain|how does|how do|describe how)\s+",
                r"(?:tell me about|explain to me)\s+",
            ],

            # Relational
            QueryIntent.RELATIONSHIP: [
                r"(?:how (?:is|are)|what is the (?:relationship|connection|link) between)\s+",
                r"(?:related to|connected to|linked to)\s+",
            ],
            QueryIntent.COMPARISON: [
                r"(?:compare|difference between|contrast|versus|vs\.?)\s+",
                r"(?:better|worse|similar|different)\s+(?:than|from)\s+",
            ],
            QueryIntent.SIMILARITY: [
                r"(?:similar to|like|resembles|related concepts)\s+",
                r"(?:alternatives? to|other options? for)\s+",
            ],

            # Temporal
            QueryIntent.TEMPORAL_SEQUENCE: [
                r"(?:what happened|what occurs?) (?:after|before|next|then)\s+",
                r"(?:following|preceding|subsequent to)\s+",
            ],
            QueryIntent.TEMPORAL_RANGE: [
                r"(?:between|from .* to|during)\s+",
                r"(?:in the period|timeframe|timeline)\s+",
            ],
            QueryIntent.HISTORY: [
                r"(?:history of|historical|past|evolution of)\s+",
                r"(?:origins? of|how did .* develop)\s+",
            ],

            # Causal
            QueryIntent.CAUSE: [
                r"(?:what causes?|cause of|reason for|why does)\s+",
                r"(?:leads? to|results? in|triggers?)\s+",
            ],
            QueryIntent.EFFECT: [
                r"(?:effect of|effects? of|impact of|consequence of)\s+",
                r"(?:what happens when|result of)\s+",
            ],
            QueryIntent.REASON: [
                r"(?:why|reason|because of|due to)\s+",
                r"(?:what makes?|what causes?)\s+",
            ],

            # Procedural
            QueryIntent.HOW_TO: [
                r"(?:how (?:to|do|can) I|how should I)\s+",
                r"(?:way to|method for|approach to)\s+",
            ],
            QueryIntent.STEPS: [
                r"(?:steps? (?:to|for)|procedure for)\s+",
                r"(?:instructions? for|guide to)\s+",
            ],
            QueryIntent.PROCESS: [
                r"(?:process of|workflow for|pipeline)\s+",
                r"(?:how does .* work|mechanism)\s+",
            ],

            # Exploratory
            QueryIntent.LIST: [
                r"(?:list|enumerate|show all|all the)\s+",
                r"(?:what are the|give me all)\s+",
            ],
            QueryIntent.FIND: [
                r"(?:find|search|look for|locate)\s+",
                r"(?:where (?:is|are|can I find))\s+",
            ],
        }

    def classify(self, query: str) -> Tuple[QueryIntent, List[QueryIntent], float]:
        """
        Classify query intent.

        Returns:
            Tuple of (primary_intent, secondary_intents, confidence)
        """
        query_lower = query.lower().strip()
        intent_scores: Dict[QueryIntent, float] = {}

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    intent_scores[intent] = intent_scores.get(intent, 0) + 1.0

        if not intent_scores:
            # Default to exploration
            return QueryIntent.EXPLORE, [], 0.3

        # Sort by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

        primary_intent = sorted_intents[0][0]
        primary_score = sorted_intents[0][1]

        # Get secondary intents (score > 0.5 * primary)
        secondary_intents = [
            intent for intent, score in sorted_intents[1:]
            if score >= 0.5 * primary_score
        ]

        # Calculate confidence based on clarity of match
        total_score = sum(intent_scores.values())
        confidence = primary_score / total_score if total_score > 0 else 0.5

        return primary_intent, secondary_intents, confidence


class AnchorIdentifier:
    """
    Identifies anchors (key concepts/entities) in queries.

    Uses pattern matching and heuristics for anchor extraction.
    For production, would use NER and entity linking.
    """

    def __init__(self):
        # Common stop words to skip
        self.stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some",
            "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "just", "and", "but", "if", "or",
            "because", "until", "while", "about", "against", "between",
            "into", "through", "during", "before", "after", "above",
            "below", "what", "which", "who", "whom", "this", "that",
            "these", "those", "am", "it", "its", "their", "my", "your"
        }

        # Time patterns
        self.time_patterns = [
            r"\b\d{4}\b",  # Years
            r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
            r"\b(?:yesterday|today|tomorrow|last week|next week|last month|this year)\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # Dates
        ]

        # Action verb patterns
        self.action_patterns = [
            r"\b(?:create|build|make|develop|implement|design)\b",
            r"\b(?:fix|solve|resolve|debug|repair)\b",
            r"\b(?:learn|study|understand|analyze|research)\b",
            r"\b(?:run|execute|deploy|start|stop)\b",
        ]

    def identify(self, query: str) -> List[Anchor]:
        """
        Identify anchors in a query.

        Returns:
            List of identified Anchor objects
        """
        anchors = []
        query_lower = query.lower()

        # Extract time references
        for pattern in self.time_patterns:
            for match in re.finditer(pattern, query_lower, re.IGNORECASE):
                anchors.append(Anchor(
                    text=match.group(),
                    anchor_type=AnchorType.TIME,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9
                ))

        # Extract action verbs
        for pattern in self.action_patterns:
            for match in re.finditer(pattern, query_lower):
                anchors.append(Anchor(
                    text=match.group(),
                    anchor_type=AnchorType.ACTION,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7
                ))

        # Extract noun phrases (simplified - would use NLP in production)
        # Look for capitalized words (potential entities)
        for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query):
            text = match.group()
            if text.lower() not in self.stop_words:
                anchors.append(Anchor(
                    text=text,
                    anchor_type=AnchorType.ENTITY,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8
                ))

        # Extract quoted phrases
        for match in re.finditer(r'"([^"]+)"', query):
            anchors.append(Anchor(
                text=match.group(1),
                anchor_type=AnchorType.CONCEPT,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))

        # Extract remaining significant words
        words = query_lower.split()
        for i, word in enumerate(words):
            # Clean punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word and clean_word not in self.stop_words and len(clean_word) > 2:
                # Check if already captured
                already_captured = any(
                    clean_word in a.text.lower() for a in anchors
                )
                if not already_captured:
                    # Find position in original query
                    start = query_lower.find(clean_word)
                    if start >= 0:
                        anchors.append(Anchor(
                            text=clean_word,
                            anchor_type=AnchorType.CONCEPT,
                            start_pos=start,
                            end_pos=start + len(clean_word),
                            confidence=0.5
                        ))

        # Sort by position
        anchors.sort(key=lambda a: a.start_pos)

        # Remove duplicates (keep higher confidence)
        seen_texts = {}
        unique_anchors = []
        for anchor in anchors:
            key = anchor.text.lower()
            if key not in seen_texts or anchor.confidence > seen_texts[key].confidence:
                seen_texts[key] = anchor
                unique_anchors.append(anchor)

        return unique_anchors


class GraphSelector:
    """
    Selects which relation graphs to query based on intent and anchors.
    """

    def __init__(self):
        # Intent to graph mapping
        self.intent_graph_map = {
            # Semantic graph for conceptual queries
            QueryIntent.DEFINITION: ["semantic"],
            QueryIntent.EXPLANATION: ["semantic", "causal"],
            QueryIntent.SIMILARITY: ["semantic"],

            # Entity graph for relational queries
            QueryIntent.RELATIONSHIP: ["entity", "semantic"],
            QueryIntent.COMPARISON: ["semantic", "entity"],

            # Temporal graph for time-based queries
            QueryIntent.TEMPORAL_SEQUENCE: ["temporal"],
            QueryIntent.TEMPORAL_RANGE: ["temporal"],
            QueryIntent.HISTORY: ["temporal", "causal"],

            # Causal graph for cause-effect queries
            QueryIntent.CAUSE: ["causal"],
            QueryIntent.EFFECT: ["causal"],
            QueryIntent.REASON: ["causal", "semantic"],

            # Procedural uses causal + semantic
            QueryIntent.HOW_TO: ["causal", "semantic"],
            QueryIntent.STEPS: ["causal", "temporal"],
            QueryIntent.PROCESS: ["causal", "temporal", "semantic"],

            # Exploratory uses all
            QueryIntent.EXPLORE: ["semantic", "entity", "temporal", "causal"],
            QueryIntent.LIST: ["entity", "semantic"],
            QueryIntent.FIND: ["semantic", "entity"],

            # Unknown uses all
            QueryIntent.UNKNOWN: ["semantic", "entity", "temporal", "causal"],
        }

    def select(
        self,
        intent: QueryIntent,
        anchors: List[Anchor]
    ) -> List[str]:
        """
        Select graphs to query.

        Returns:
            List of graph names to query
        """
        # Start with intent-based selection
        graphs = self.intent_graph_map.get(intent, ["semantic"])[:] # Copy

        # Adjust based on anchor types
        anchor_types = {a.anchor_type for a in anchors}

        if AnchorType.TIME in anchor_types:
            if "temporal" not in graphs:
                graphs.insert(0, "temporal")

        if AnchorType.ENTITY in anchor_types:
            if "entity" not in graphs:
                graphs.insert(0, "entity")

        if AnchorType.ACTION in anchor_types:
            if "causal" not in graphs:
                graphs.append("causal")

        return graphs


class RetrievalPolicySelector:
    """
    Selects the retrieval policy based on query analysis.

    Policies determine how to traverse graphs and combine results.
    """

    POLICIES = {
        "single_graph": "Query single most relevant graph",
        "multi_graph_union": "Query multiple graphs, union results",
        "multi_graph_intersection": "Query multiple graphs, intersect results",
        "graph_traversal": "Start from anchor, traverse relationships",
        "temporal_window": "Retrieve within temporal window",
        "causal_chain": "Follow causal chains from anchor",
        "hybrid": "Combine vector similarity with graph traversal",
    }

    def select(
        self,
        intent: QueryIntent,
        anchors: List[Anchor],
        graphs: List[str]
    ) -> str:
        """
        Select retrieval policy.

        Returns:
            Policy name
        """
        # Temporal intents use temporal window
        if intent in [QueryIntent.TEMPORAL_SEQUENCE, QueryIntent.TEMPORAL_RANGE, QueryIntent.HISTORY]:
            return "temporal_window"

        # Causal intents use causal chain traversal
        if intent in [QueryIntent.CAUSE, QueryIntent.EFFECT, QueryIntent.REASON]:
            return "causal_chain"

        # Relational intents use graph traversal
        if intent in [QueryIntent.RELATIONSHIP, QueryIntent.SIMILARITY]:
            return "graph_traversal"

        # Procedural intents use hybrid
        if intent in [QueryIntent.HOW_TO, QueryIntent.STEPS, QueryIntent.PROCESS]:
            return "hybrid"

        # Multiple graphs use union
        if len(graphs) > 1:
            return "multi_graph_union"

        # Single graph with clear anchors uses traversal
        if len(anchors) >= 2:
            return "graph_traversal"

        # Default to hybrid
        return "hybrid"


class IntentAwareRouter:
    """
    Main router that analyzes queries and determines retrieval strategy.

    This is the entry point for Magma query processing.
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.anchor_identifier = AnchorIdentifier()
        self.graph_selector = GraphSelector()
        self.policy_selector = RetrievalPolicySelector()

        logger.info("[MAGMA-ROUTER] Intent-Aware Router initialized")

    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze a query to determine retrieval strategy.

        Args:
            query: User query string

        Returns:
            QueryAnalysis with complete routing information
        """
        # Normalize query
        normalized = self._normalize_query(query)

        # Classify intent
        primary_intent, secondary_intents, intent_confidence = self.intent_classifier.classify(normalized)

        # Identify anchors
        anchors = self.anchor_identifier.identify(query)

        # Select target graphs
        target_graphs = self.graph_selector.select(primary_intent, anchors)

        # Select retrieval policy
        retrieval_policy = self.policy_selector.select(primary_intent, anchors, target_graphs)

        # Calculate overall confidence
        anchor_confidence = sum(a.confidence for a in anchors) / max(len(anchors), 1)
        overall_confidence = (intent_confidence + anchor_confidence) / 2

        analysis = QueryAnalysis(
            original_query=query,
            normalized_query=normalized,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            anchors=anchors,
            target_graphs=target_graphs,
            retrieval_policy=retrieval_policy,
            confidence=overall_confidence,
            metadata={
                "intent_confidence": intent_confidence,
                "anchor_count": len(anchors),
                "anchor_types": list({a.anchor_type.value for a in anchors})
            }
        )

        logger.info(
            f"[MAGMA-ROUTER] Query analyzed: intent={primary_intent.value}, "
            f"anchors={len(anchors)}, graphs={target_graphs}, policy={retrieval_policy}"
        )

        return analysis

    def _normalize_query(self, query: str) -> str:
        """Normalize query for processing."""
        # Basic normalization
        normalized = query.strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        return normalized

    def route(self, query: str) -> Dict[str, Any]:
        """
        Route a query and return routing decision.

        Args:
            query: User query string

        Returns:
            Dict with routing information
        """
        analysis = self.analyze_query(query)

        return {
            "query": analysis.original_query,
            "intent": analysis.primary_intent.value,
            "secondary_intents": [i.value for i in analysis.secondary_intents],
            "anchors": [
                {
                    "text": a.text,
                    "type": a.anchor_type.value,
                    "confidence": a.confidence
                }
                for a in analysis.anchors
            ],
            "target_graphs": analysis.target_graphs,
            "retrieval_policy": analysis.retrieval_policy,
            "confidence": analysis.confidence
        }

    def get_anchor_embeddings_needed(self, analysis: QueryAnalysis) -> List[str]:
        """
        Get list of anchor texts that need embeddings for similarity search.

        Returns:
            List of anchor texts requiring embedding
        """
        return [
            a.text for a in analysis.anchors
            if a.anchor_type in [AnchorType.CONCEPT, AnchorType.ENTITY]
        ]
