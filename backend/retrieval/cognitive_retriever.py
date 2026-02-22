"""
Cognitive Retrieval Service - Integration Layer

Connects Cognitive Engine → RAG → Learning Memory
Every retrieval goes through OODA loop with decision logging and trust scoring.

Classes:
- `CognitiveRetriever`

Key Methods:
- `retrieve_with_cognition()`
- `provide_feedback()`
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from cognitive.engine import CognitiveEngine, DecisionContext
from cognitive.learning_memory import LearningMemoryManager, TrustScorer
from retrieval.retriever import DocumentRetriever
from database.session import get_session
from pathlib import Path
from settings import KNOWLEDGE_BASE_PATH

logger = logging.getLogger(__name__)
def _track_op(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event('cognitive_retriever', desc, **kw)
    except Exception:
        pass



class CognitiveRetriever:
    """
    Retrieval system integrated with Cognitive Engine.

    Every query:
    1. Starts OODA loop (Observe → Orient → Decide → Act)
    2. Tracks ambiguity and decision quality
    3. Feeds outcomes to Learning Memory
    4. Updates trust scores based on results
    """

    def __init__(
        self,
        retriever: DocumentRetriever,
        enable_cognitive: bool = True,
        enable_learning: bool = True
    ):
        """
        Initialize cognitive retriever.

        Args:
            retriever: Base document retriever
            enable_cognitive: Enable cognitive engine integration
            enable_learning: Enable learning memory integration
        """
        self.retriever = retriever
        self.enable_cognitive = enable_cognitive
        self.enable_learning = enable_learning

        # Initialize cognitive engine
        if self.enable_cognitive:
            self.cognitive_engine = CognitiveEngine(enable_strict_mode=False)
        else:
            self.cognitive_engine = None

        # Initialize learning memory
        if self.enable_learning:
            session = next(get_session())
            self.learning_manager = LearningMemoryManager(
                session=session,
                knowledge_base_path=Path(KNOWLEDGE_BASE_PATH)
            )
        else:
            self.learning_manager = None

    def retrieve_with_cognition(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        keyword_weight: float = 0.3,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve documents using cognitive decision-making.

        Implements OODA loop:
        - Observe: Analyze query, check ambiguity
        - Orient: Determine retrieval strategy
        - Decide: Choose semantic vs hybrid vs reranking
        - Act: Execute retrieval, track outcome

        Args:
            query: User query
            limit: Max chunks to retrieve
            score_threshold: Minimum score
            keyword_weight: Weight for keyword matching
            user_id: Genesis ID of user
            genesis_key_id: Genesis Key for this query

        Returns:
            Dict with chunks, context, and cognitive metadata
        """
        start_time = datetime.now()

        # If cognitive engine disabled, use basic retrieval
        if not self.enable_cognitive:
            return self._basic_retrieve(query, limit, score_threshold, keyword_weight)

        # ========== OODA: OBSERVE ==========
        context = self.cognitive_engine.begin_decision(
            problem_statement=f"Retrieve relevant documents for query: {query}",
            goal="Find most relevant document chunks with high confidence",
            success_criteria=[
                "Chunks have relevance score > threshold",
                "Chunks provide useful context",
                "No contradictory information"
            ],
            is_reversible=True,  # Can always adjust retrieval
            impact_scope="local"  # Only affects this query
        )

        # Analyze query characteristics
        query_analysis = self._analyze_query(query)

        self.cognitive_engine.observe(context, {
            "query": query,
            "query_length": len(query.split()),
            "query_type": query_analysis["type"],
            "has_keywords": query_analysis["has_keywords"],
            "ambiguity_level": query_analysis["ambiguity"],
            "requested_limit": limit,
            "threshold": score_threshold
        })

        # ========== OODA: ORIENT ==========
        # Determine constraints and strategy
        constraints = {
            "safety_critical": False,  # Retrieval is not safety-critical
            "impact_scope": "local",
            "requires_high_confidence": score_threshold > 0.5
        }

        context_info = {
            "available_strategies": ["semantic", "hybrid", "reranked"],
            "query_characteristics": query_analysis,
            "performance_history": self._get_performance_history()
        }

        self.cognitive_engine.orient(context, constraints, context_info)

        # ========== OODA: DECIDE ==========
        # Generate alternative retrieval strategies
        def generate_alternatives() -> List[Dict[str, Any]]:
            alternatives = []

            # Alternative 1: Pure semantic search
            alternatives.append({
                "strategy": "semantic",
                "immediate_value": 0.7,
                "future_options": 0.9,  # Can always add keywords later
                "simplicity": 1.0,  # Simplest approach
                "reversibility": 1.0,
                "complexity": 0.1
            })

            # Alternative 2: Hybrid search (semantic + keyword)
            alternatives.append({
                "strategy": "hybrid",
                "immediate_value": 0.85,  # Better for most queries
                "future_options": 0.8,
                "simplicity": 0.8,
                "reversibility": 1.0,
                "complexity": 0.3
            })

            # Alternative 3: Hybrid + Reranking
            alternatives.append({
                "strategy": "reranked",
                "immediate_value": 0.9,  # Best quality
                "future_options": 0.7,  # More committed
                "simplicity": 0.6,  # More complex
                "reversibility": 1.0,
                "complexity": 0.5
            })

            return alternatives

        selected_strategy = self.cognitive_engine.decide(
            context,
            generate_alternatives,
            max_alternatives=3
        )

        logger.info(f"[COGNITIVE RETRIEVAL] Selected strategy: {selected_strategy['strategy']}")

        # ========== OODA: ACT ==========
        # Execute retrieval with selected strategy
        def execute_retrieval() -> Dict[str, Any]:
            strategy = selected_strategy["strategy"]

            if strategy == "semantic":
                chunks = self.retriever.retrieve(
                    query=query,
                    limit=limit,
                    score_threshold=score_threshold,
                    include_metadata=True
                )
            elif strategy == "hybrid":
                chunks = self.retriever.retrieve_hybrid(
                    query=query,
                    limit=limit,
                    score_threshold=score_threshold,
                    keyword_weight=keyword_weight,
                    include_metadata=True
                )
            else:  # reranked
                chunks = self.retriever.retrieve_and_rank(
                    query=query,
                    limit=limit,
                    score_threshold=score_threshold,
                    rerank=True
                )

            # Build context
            context_str = self.retriever.build_context(chunks, include_sources=True)

            return {
                "chunks": chunks,
                "context": context_str,
                "strategy_used": strategy
            }

        result = self.cognitive_engine.act(context, execute_retrieval)

        # Calculate retrieval quality
        retrieval_quality = self._assess_retrieval_quality(
            query=query,
            chunks=result["chunks"],
            query_analysis=query_analysis
        )

        # Finalize decision
        self.cognitive_engine.finalize_decision(context)

        end_time = datetime.now()
        elapsed_ms = (end_time - start_time).total_seconds() * 1000

        # ========== LEARNING MEMORY INTEGRATION ==========
        if self.enable_learning and self.learning_manager:
            # Feed outcome to learning memory
            self._record_learning_example(
                query=query,
                strategy=selected_strategy["strategy"],
                chunks=result["chunks"],
                quality_score=retrieval_quality,
                decision_context=context,
                user_id=user_id,
                genesis_key_id=genesis_key_id
            )

        # Return enriched result
        return {
            **result,
            "cognitive_metadata": {
                "decision_id": context.decision_id,
                "strategy_selected": selected_strategy["strategy"],
                "ambiguity_level": query_analysis["ambiguity"],
                "quality_score": retrieval_quality,
                "elapsed_ms": elapsed_ms,
                "ooda_phases_completed": ["observe", "orient", "decide", "act"]
            },
            "total": len(result["chunks"]),
            "query": query
        }

    def _basic_retrieve(
        self,
        query: str,
        limit: int,
        score_threshold: float,
        keyword_weight: float
    ) -> Dict[str, Any]:
        """Fallback to basic retrieval without cognitive engine."""
        chunks = self.retriever.retrieve_hybrid(
            query=query,
            limit=limit,
            score_threshold=score_threshold,
            keyword_weight=keyword_weight,
            include_metadata=True
        )

        context = self.retriever.build_context(chunks, include_sources=True)

        return {
            "chunks": chunks,
            "context": context,
            "strategy_used": "hybrid",
            "total": len(chunks),
            "query": query
        }

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query characteristics to inform strategy.

        Returns:
            Dict with query analysis
        """
        words = query.split()
        word_count = len(words)

        # Detect query type
        question_words = ["what", "why", "how", "when", "where", "who", "which"]
        is_question = any(query.lower().startswith(qw) for qw in question_words)

        # Check for specific keywords
        has_keywords = any(word.isupper() or word.startswith("$") for word in words)

        # Estimate ambiguity
        vague_words = ["thing", "stuff", "some", "any", "about", "like"]
        ambiguity_count = sum(1 for word in words if word.lower() in vague_words)

        if ambiguity_count > 2:
            ambiguity = "high"
        elif ambiguity_count > 0:
            ambiguity = "medium"
        else:
            ambiguity = "low"

        # Determine type
        if is_question:
            query_type = "question"
        elif word_count <= 3:
            query_type = "keyword"
        else:
            query_type = "descriptive"

        return {
            "type": query_type,
            "word_count": word_count,
            "has_keywords": has_keywords,
            "ambiguity": ambiguity,
            "is_question": is_question
        }

    def _get_performance_history(self) -> Dict[str, Any]:
        """
        Get historical performance data for strategy selection.

        Queries learning memory for past retrieval performance.
        """
        # Default baseline performance
        performance = {
            "semantic_avg_quality": 0.7,
            "hybrid_avg_quality": 0.8,
            "reranked_avg_quality": 0.85
        }

        # Try to get actual performance from learning memory
        if self.enable_learning and hasattr(self, 'learning_manager'):
            try:
                # Get recent retrieval experiences
                stats = self.learning_manager.get_training_data_stats()
                if stats and "total_examples" in stats and stats["total_examples"] > 0:
                    # Calculate average quality from recent examples
                    avg_trust = stats.get("average_trust_score", 0.75)
                    # Adjust performance based on learning data
                    performance["semantic_avg_quality"] = avg_trust * 0.9
                    performance["hybrid_avg_quality"] = avg_trust * 0.95
                    performance["reranked_avg_quality"] = min(1.0, avg_trust * 1.05)
            except Exception as e:
                logger.debug(f"Could not load performance history: {e}")

        return performance

    def _assess_retrieval_quality(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_analysis: Dict[str, Any]
    ) -> float:
        """
        Assess quality of retrieval results.

        Factors:
        - Number of chunks returned
        - Average confidence scores
        - Score distribution
        - Relevance to query type

        Returns:
            Quality score (0-1)
        """
        if not chunks:
            return 0.0

        # Factor 1: Coverage (did we get enough chunks?)
        coverage_score = min(1.0, len(chunks) / 5)  # Ideal is 5 chunks

        # Factor 2: Average confidence
        confidences = [c.get("confidence_score", 0.5) for c in chunks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Factor 3: Score distribution (prefer varied but high scores)
        scores = [c.get("score", 0) for c in chunks]
        if scores:
            score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            distribution_score = 1.0 - min(1.0, score_variance)
        else:
            distribution_score = 0.5

        # Factor 4: Minimum score (worst chunk quality)
        min_score = min(scores) if scores else 0.0

        # Weighted combination
        quality = (
            coverage_score * 0.2 +
            avg_confidence * 0.4 +
            distribution_score * 0.2 +
            min_score * 0.2
        )

        return quality

    def _record_learning_example(
        self,
        query: str,
        strategy: str,
        chunks: List[Dict[str, Any]],
        quality_score: float,
        decision_context: DecisionContext,
        user_id: Optional[str],
        genesis_key_id: Optional[str]
    ):
        """
        Record this retrieval as a learning example.

        Feeds to learning memory for future improvement.
        """
        try:
            learning_data = {
                "context": {
                    "query": query,
                    "query_type": decision_context.metadata.get("observations", {}).get("query_type"),
                    "ambiguity_level": decision_context.metadata.get("observations", {}).get("ambiguity_level")
                },
                "expected": {
                    "strategy": strategy,
                    "quality_threshold": 0.7
                },
                "actual": {
                    "strategy": strategy,
                    "quality_achieved": quality_score,
                    "chunks_returned": len(chunks),
                    "avg_confidence": sum(c.get("confidence_score", 0) for c in chunks) / len(chunks) if chunks else 0
                }
            }

            # Determine source based on quality
            if quality_score > 0.8:
                source = "system_observation_success"
            elif quality_score < 0.3:
                source = "system_observation_failure"
            else:
                source = "system_observation_success"

            self.learning_manager.ingest_learning_data(
                learning_type="retrieval_outcome",
                learning_data=learning_data,
                source=source,
                user_id=user_id,
                genesis_key_id=genesis_key_id
            )

            logger.info(f"[LEARNING] Recorded retrieval example with quality {quality_score:.2f}")

        except Exception as e:
            logger.error(f"Failed to record learning example: {e}")

    def provide_feedback(
        self,
        query: str,
        chunks_used: List[int],
        was_helpful: bool,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ):
        """
        Record user feedback on retrieval quality.

        This creates high-trust learning examples from direct user feedback.

        Args:
            query: Original query
            chunks_used: List of chunk IDs that were used
            was_helpful: Whether the results were helpful
            user_id: Genesis ID of user
            genesis_key_id: Genesis Key for this feedback
        """
        if not self.enable_learning or not self.learning_manager:
            return

        try:
            learning_data = {
                "context": {
                    "query": query,
                    "chunks_used": chunks_used
                },
                "expected": {
                    "helpful": True
                },
                "actual": {
                    "helpful": was_helpful
                }
            }

            source = "user_feedback_positive" if was_helpful else "user_feedback_negative"

            self.learning_manager.ingest_learning_data(
                learning_type="user_feedback",
                learning_data=learning_data,
                source=source,
                user_id=user_id,
                genesis_key_id=genesis_key_id
            )

            logger.info(f"[LEARNING] Recorded user feedback: {'helpful' if was_helpful else 'not helpful'}")

        except Exception as e:
            logger.error(f"Failed to record user feedback: {e}")
