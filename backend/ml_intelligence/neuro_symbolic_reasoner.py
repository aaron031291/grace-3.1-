"""
Unified Neuro-Symbolic Reasoner - True Neuro-Symbolic Integration

Combines neural (fuzzy, pattern-based) and symbolic (precise, rule-based)
reasoning into a unified system where both inform each other.

Key Features:
- Bidirectional integration (neural ↔ symbolic)
- Joint inference combining both approaches
- Trust-weighted fusion
- Context-aware reasoning
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from embedding import EmbeddingModel, get_embedding_model
from retrieval.retriever import DocumentRetriever
from ml_intelligence.trust_aware_embedding import TrustAwareEmbeddingModel, TrustContext
from ml_intelligence.neural_to_symbolic_rule_generator import NeuralToSymbolicRuleGenerator, SymbolicRule

try:
    from cognitive.learning_memory import LearningMemoryManager
except ImportError:
    LearningMemoryManager = None

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """Unified reasoning result combining neural and symbolic"""
    query: str
    neural_results: List[Dict[str, Any]]
    symbolic_results: List[Dict[str, Any]]
    fused_results: List[Dict[str, Any]]
    neural_confidence: float
    symbolic_confidence: float
    fusion_confidence: float
    reasoning_trace: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    @property
    def confidence(self) -> float:
        """Single confidence score for decision-making (fusion-weighted)."""
        return self.fusion_confidence


class NeuroSymbolicReasoner:
    """
    Unified neuro-symbolic reasoning system.
    
    This implements true bidirectional integration:
    - Neural finds similar concepts (fuzzy search)
    - Symbolic provides trusted facts (precise knowledge)
    - Both inform each other in joint inference
    """
    
    def __init__(
        self,
        retriever: Optional[DocumentRetriever] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        trust_aware_model: Optional[TrustAwareEmbeddingModel] = None,
        learning_memory: Optional[LearningMemoryManager] = None,
        rule_generator: Optional[NeuralToSymbolicRuleGenerator] = None,
        neural_weight: float = 0.5,
        symbolic_weight: float = 0.5,
        trust_threshold: float = 0.5,
    ):
        """
        Initialize neuro-symbolic reasoner.
        
        Args:
            retriever: DocumentRetriever for neural search
            embedding_model: EmbeddingModel for neural component
            trust_aware_model: TrustAwareEmbeddingModel for trust-enhanced search
            learning_memory: LearningMemoryManager for symbolic knowledge
            rule_generator: NeuralToSymbolicRuleGenerator for rule creation
            neural_weight: Weight of neural component (0-1)
            symbolic_weight: Weight of symbolic component (0-1)
            trust_threshold: Minimum trust for symbolic results
        """
        self.retriever = retriever
        self.embedding_model = embedding_model or get_embedding_model()
        self.trust_aware_model = trust_aware_model
        self.learning_memory = learning_memory
        self.rule_generator = rule_generator
        
        # Normalize weights
        total_weight = neural_weight + symbolic_weight
        self.neural_weight = neural_weight / total_weight if total_weight > 0 else 0.5
        self.symbolic_weight = symbolic_weight / total_weight if total_weight > 0 else 0.5
        self.trust_threshold = trust_threshold
        
        logger.info(f"[NEURO-SYMBOLIC] Initialized with neural_weight={self.neural_weight:.2f}, symbolic_weight={self.symbolic_weight:.2f}")
    
    def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        include_trace: bool = True,
    ) -> ReasoningResult:
        """
        Perform unified neuro-symbolic reasoning.
        
        Process:
        1. Neural search: Find similar concepts (fuzzy)
        2. Symbolic query: Get trusted facts (precise)
        3. Cross-inform: Each informs the other
        4. Fusion: Combine both with joint inference
        
        Args:
            query: Query text
            context: Optional context for reasoning
            limit: Maximum results to return
            include_trace: Include reasoning trace
            
        Returns:
            ReasoningResult with fused neural-symbolic results
        """
        context = context or {}
        start_time = datetime.now(timezone.utc)
        reasoning_trace = {}
        
        # ========== STEP 1: Neural Search (Fuzzy) ==========
        neural_results, neural_confidence = self._neural_search(query, limit=limit)
        reasoning_trace["neural_search"] = {
            "results_count": len(neural_results),
            "confidence": neural_confidence,
        }
        
        # ========== STEP 2: Symbolic Query (Precise) ==========
        symbolic_results, symbolic_confidence = self._symbolic_query(query, limit=limit)
        reasoning_trace["symbolic_query"] = {
            "results_count": len(symbolic_results),
            "confidence": symbolic_confidence,
        }
        
        # ========== STEP 3: Cross-Inform ==========
        # Neural informs symbolic (similarity ranking)
        symbolic_results = self._neural_rank_symbolic(symbolic_results, query)
        
        # Symbolic informs neural (trust weighting)
        neural_results = self._symbolic_weight_neural(neural_results)
        
        reasoning_trace["cross_inform"] = {
            "neural_ranked_symbolic": len(symbolic_results),
            "symbolic_weighted_neural": len(neural_results),
        }
        
        # ========== STEP 4: Fusion ==========
        fused_results, fusion_confidence = self._fuse_results(
            neural_results,
            symbolic_results,
            query,
        )
        
        reasoning_trace["fusion"] = {
            "fused_count": len(fused_results),
            "confidence": fusion_confidence,
        }
        
        # ========== Build Result ==========
        result = ReasoningResult(
            query=query,
            neural_results=neural_results[:limit],
            symbolic_results=symbolic_results[:limit],
            fused_results=fused_results[:limit],
            neural_confidence=neural_confidence,
            symbolic_confidence=symbolic_confidence,
            fusion_confidence=fusion_confidence,
            reasoning_trace=reasoning_trace if include_trace else {},
        )
        
        elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.info(f"[NEURO-SYMBOLIC] Reasoning completed in {elapsed_ms:.1f}ms, {len(fused_results)} fused results")
        
        return result
    
    def _neural_search(
        self,
        query: str,
        limit: int = 10,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Perform neural (fuzzy) search."""
        if self.retriever is None:
            logger.warning("No retriever available, returning empty neural results")
            return [], 0.0
        
        try:
            chunks = self.retriever.retrieve(
                query=query,
                limit=limit * 2,  # Get more for filtering
                score_threshold=0.3,
                include_metadata=True,
            )
            
            # Calculate confidence from average similarity
            if chunks:
                scores = [chunk.get("score", 0.0) for chunk in chunks]
                confidence = np.mean(scores) if scores else 0.0
            else:
                confidence = 0.0
            
            return chunks[:limit], confidence
            
        except Exception as e:
            logger.error(f"Neural search failed: {e}")
            return [], 0.0
    
    def _symbolic_query(
        self,
        query: str,
        limit: int = 10,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Perform symbolic (precise) query."""
        if self.learning_memory is None:
            logger.warning(
                "[NEURO-SYMBOLIC] No learning memory (symbolic results empty). "
                "Wire LearningMemoryManager in Layer4 or disable neuro-symbolic to silence."
            )
            return [], 0.0
        
        try:
            from cognitive.learning_memory import LearningExample
            from cognitive.learning_memory import LearningPattern
            
            results = []
            
            # Query high-trust learning examples
            try:
                # Get high-trust examples (if get_training_data method exists)
                if hasattr(self.learning_memory, 'get_training_data'):
                    examples = self.learning_memory.get_training_data(
                        min_trust_score=self.trust_threshold,
                        limit=limit * 2  # Get more for filtering
                    )
                    
                    # Convert to result format
                    for example in examples:
                        import json

                        def _safe_parse(val):
                            if isinstance(val, dict): return val
                            if isinstance(val, str):
                                try: return json.loads(val)
                                except Exception: return {"text": val}
                            return {}

                        ctx = _safe_parse(example.input_context)
                        out = _safe_parse(example.expected_output)
                        context_text = str(ctx.get('text', '') or str(ctx)[:200])
                        output_text = str(out.get('text', '') or str(out)[:200])
                        text = f"{context_text} {output_text}".strip()
                        
                        if text:
                            results.append({
                                "id": example.id,
                                "text": text,
                                "content": text,
                                "trust_score": example.trust_score,
                                "source": example.source,
                                "example_type": example.example_type,
                            })
                else:
                    # Fallback: Direct DB query
                    examples = self.learning_memory.session.query(LearningExample).filter(
                        LearningExample.trust_score >= self.trust_threshold
                    ).order_by(
                        LearningExample.trust_score.desc()
                    ).limit(limit * 2).all()
                    
                    for example in examples:
                        import json

                        def _safe_parse(val):
                            if isinstance(val, dict): return val
                            if isinstance(val, str):
                                try: return json.loads(val)
                                except Exception: return {"text": val}
                            return {}

                        ctx = _safe_parse(example.input_context)
                        out = _safe_parse(example.expected_output)
                        context_text = str(ctx.get('text', '') or str(ctx)[:200])
                        output_text = str(out.get('text', '') or str(out)[:200])
                        text = f"{context_text} {output_text}".strip()
                        
                        if text:
                            results.append({
                                "id": example.id,
                                "text": text,
                                "content": text,
                                "trust_score": example.trust_score,
                                "source": example.source,
                                "example_type": example.example_type,
                            })
            except Exception as e:
                logger.warning(f"Failed to query learning examples: {e}")
            
            # Also query stored rules (if rule_storage available and we have access to it)
            # Note: This would require passing rule_storage to the reasoner
            # For now, we rely on learning examples above
            
            # Calculate confidence from average trust
            if results:
                trust_scores = [r.get("trust_score", 0.5) for r in results]
                confidence = float(np.mean(trust_scores))
            else:
                confidence = 0.0
            
            # Sort by trust score and limit
            results.sort(key=lambda x: x.get("trust_score", 0.0), reverse=True)
            
            return results[:limit], confidence
            
        except Exception as e:
            logger.error(f"Symbolic query failed: {e}", exc_info=True)
            return [], 0.0
    
    def _neural_rank_symbolic(
        self,
        symbolic_results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Use neural similarity to rank symbolic results.
        
        Neural informs symbolic: Similarity scores help prioritize
        which symbolic facts are most relevant.
        """
        if not symbolic_results:
            return []
        
        # Get query embedding
        query_embedding = self.embedding_model.embed_text(query)
        
        # Calculate similarity for each symbolic result
        for result in symbolic_results:
            # Extract text from result
            result_text = result.get("text", "") or result.get("content", "")
            
            if result_text:
                result_embedding = self.embedding_model.embed_text(result_text)
                
                # Cosine similarity
                from sklearn.metrics.pairwise import cosine_similarity
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    result_embedding.reshape(1, -1)
                )[0][0]
                
                result["neural_similarity"] = float(similarity)
            else:
                result["neural_similarity"] = 0.0
        
        # Sort by neural similarity
        symbolic_results.sort(key=lambda x: x.get("neural_similarity", 0.0), reverse=True)
        
        return symbolic_results
    
    def _symbolic_weight_neural(
        self,
        neural_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Use symbolic trust to weight neural results.
        
        Symbolic informs neural: Trust scores adjust neural
        similarity scores.
        """
        if not neural_results:
            return []
        
        # Get trust scores for neural results
        for result in neural_results:
            trust_score = result.get("confidence_score", 0.5) or result.get("trust_score", 0.5)
            
            # Combine neural similarity with symbolic trust
            neural_score = result.get("score", 0.0)
            combined_score = (
                self.neural_weight * neural_score +
                self.symbolic_weight * trust_score
            )
            
            result["trust_weighted_score"] = float(combined_score)
            result["trust_score"] = float(trust_score)
        
        # Filter by trust threshold
        filtered = [
            r for r in neural_results
            if r.get("trust_score", 0.0) >= self.trust_threshold
        ]
        
        # Sort by trust-weighted score
        filtered.sort(key=lambda x: x.get("trust_weighted_score", 0.0), reverse=True)
        
        return filtered
    
    def _fuse_results(
        self,
        neural_results: List[Dict[str, Any]],
        symbolic_results: List[Dict[str, Any]],
        query: str,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Fuse neural and symbolic results with joint inference.
        
        Creates a unified result set where:
        - Results appear once (deduplication)
        - Scores combine neural similarity + symbolic trust
        - High trust boosts, low trust reduces
        """
        # Build unified result map
        result_map: Dict[str, Dict[str, Any]] = {}
        
        # Add neural results
        for i, result in enumerate(neural_results):
            result_id = result.get("id") or f"neural_{i}"
            result_map[result_id] = {
                **result,
                "source": "neural",
                "fusion_score": result.get("trust_weighted_score", result.get("score", 0.0)),
            }
        
        # Add symbolic results (merge if same ID)
        for i, result in enumerate(symbolic_results):
            result_id = result.get("id") or f"symbolic_{i}"
            
            if result_id in result_map:
                # Merge: combine scores
                existing = result_map[result_id]
                neural_score = existing.get("fusion_score", 0.0)
                symbolic_score = result.get("trust_score", 0.0)
                
                # Combined score: weighted average
                combined = (
                    self.neural_weight * neural_score +
                    self.symbolic_weight * symbolic_score
                )
                
                result_map[result_id] = {
                    **existing,
                    **result,
                    "source": "both",
                    "fusion_score": combined,
                }
            else:
                result_map[result_id] = {
                    **result,
                    "source": "symbolic",
                    "fusion_score": result.get("trust_score", 0.0) * self.symbolic_weight,
                }
        
        # Convert to list and sort
        fused_results = list(result_map.values())
        fused_results.sort(key=lambda x: x.get("fusion_score", 0.0), reverse=True)
        
        # Calculate fusion confidence
        if fused_results:
            fusion_scores = [r.get("fusion_score", 0.0) for r in fused_results]
            fusion_confidence = np.mean(fusion_scores)
        else:
            fusion_confidence = 0.0
        
        return fused_results, fusion_confidence
    
    def explain_reasoning(
        self,
        result: ReasoningResult,
    ) -> str:
        """Generate human-readable explanation of reasoning process."""
        lines = [
            f"Neuro-Symbolic Reasoning for: {result.query}",
            "",
            f"Neural Search: {len(result.neural_results)} results (confidence: {result.neural_confidence:.2f})",
            f"Symbolic Query: {len(result.symbolic_results)} results (confidence: {result.symbolic_confidence:.2f})",
            f"Fused Results: {len(result.fused_results)} results (confidence: {result.fusion_confidence:.2f})",
            "",
            "Top Fused Results:",
        ]
        
        for i, result_item in enumerate(result.fused_results[:5], 1):
            source = result_item.get("source", "unknown")
            score = result_item.get("fusion_score", 0.0)
            text_preview = str(result_item.get("text", "") or result_item.get("content", ""))[:100]
            lines.append(f"  {i}. [{source}] (score: {score:.3f}) {text_preview}...")
        
        return "\n".join(lines)


def get_neuro_symbolic_reasoner(
    retriever: Optional[DocumentRetriever] = None,
    learning_memory: Optional[LearningMemoryManager] = None,
    neural_weight: float = 0.5,
    symbolic_weight: float = 0.5,
) -> NeuroSymbolicReasoner:
    """
    Get neuro-symbolic reasoner instance.
    
    Args:
        retriever: DocumentRetriever for neural search
        learning_memory: LearningMemoryManager for symbolic knowledge
        neural_weight: Weight of neural component
        symbolic_weight: Weight of symbolic component
        
    Returns:
        NeuroSymbolicReasoner instance
    """
    return NeuroSymbolicReasoner(
        retriever=retriever,
        learning_memory=learning_memory,
        neural_weight=neural_weight,
        symbolic_weight=symbolic_weight,
    )
