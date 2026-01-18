import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
logger = logging.getLogger(__name__)

class SemanticContradictionDetector:
    """
    Uses NLI (Natural Language Inference) to detect semantic contradictions.
    
    Cross-encoder/nli-deberta-large achieves 96% accuracy on MNLI benchmark
    by understanding if one statement entails, contradicts, or is neutral to another.
    """
    
    def __init__(self, use_gpu: bool = True):
        """
        Initialize the contradiction detector with the DeBERTa cross-encoder model.

        Args:
            use_gpu: Whether to use GPU if available
        """
        _torch = _get_torch()
        if _torch is not None:
            self.use_gpu = use_gpu and _torch.cuda.is_available()
        else:
            self.use_gpu = False
        self.device = "cuda" if self.use_gpu else "cpu"
        
        logger.info(f"Loading NLI model on {self.device.upper()}...")
        
        try:
            from sentence_transformers import CrossEncoder
            
            # Load the cross-encoder model for NLI
            # This model outputs 3 scores: entailment, neutral, contradiction
            self.model = CrossEncoder(
                'cross-encoder/nli-deberta-v3-large',
                device=self.device,
                max_length=512
            )
            logger.info("[OK] NLI DeBERTa model loaded successfully")
            self.model_available = True
            
        except ImportError:
            logger.warning("sentence-transformers not found, installing...")
            import subprocess
            subprocess.check_call([
                "pip", "install", "sentence-transformers", "-q"
            ])
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(
                'cross-encoder/nli-deberta-large',
                device=self.device,
                max_length=512
            )
            self.model_available = True
        except Exception as e:
            logger.error(f"Failed to load NLI model: {e}")
            self.model_available = False
            self.model = None
    
    def detect_contradiction(
        self,
        chunk1: str,
        chunk2: str,
        similarity_score: float = 0.8,
        threshold: float = 0.7,
    ) -> Tuple[bool, float, str]:
        """
        Detect if two semantically similar chunks contradict each other.
        
        Uses the cross-encoder model to determine the relationship:
        - Entailment: chunk1 implies chunk2 is true
        - Neutral: no clear relationship
        - Contradiction: chunk1 implies chunk2 is false
        
        Args:
            chunk1: First chunk text
            chunk2: Second chunk text
            similarity_score: The semantic similarity score (0-1)
            threshold: Minimum score to consider as contradiction (0-1)
            
        Returns:
            Tuple of (is_contradictory, contradiction_confidence, reason)
        """
        if not self.model_available:
            logger.debug("NLI model not available, skipping contradiction detection")
            return False, 0.0, "Model unavailable"
        
        if similarity_score < 0.6:
            # If not very similar semantically, ignore
            return False, 0.0, "Low semantic similarity"
        
        try:
            # The model expects input as [[sentence_a, sentence_b]]
            # and outputs 3 scores for [entailment, neutral, contradiction]
            scores = self.model.predict([[chunk1, chunk2]])

            # Handle different score shapes - ensure we have the right format
            scores_arr = np.atleast_2d(scores)
            if scores_arr.shape[-1] != 3:
                # If scores don't have 3 classes, this model may not be an NLI model
                logger.warning(f"Unexpected scores shape: {scores_arr.shape}, expected 3 classes")
                return False, 0.0, "Model output format unexpected"

            # Get the contradiction score (index 2)
            contradiction_score = float(scores_arr[0][2])  # Contradiction is the 3rd class

            # Check both directions for robustness
            scores_reverse = self.model.predict([[chunk2, chunk1]])
            scores_reverse_arr = np.atleast_2d(scores_reverse)
            contradiction_score_reverse = float(scores_reverse_arr[0][2])

            # Use the maximum contradiction score from both directions
            max_contradiction_score = max(contradiction_score, contradiction_score_reverse)

            logger.debug(
                f"NLI scores - Forward: {scores_arr[0]}, Reverse: {scores_reverse_arr[0]}"
            )

            if max_contradiction_score > threshold:
                return True, float(max_contradiction_score), \
                    f"Semantic contradiction detected (confidence: {max_contradiction_score:.3f})"

            return False, 0.0, "No contradiction detected"

        except Exception as e:
            logger.error(f"Error in contradiction detection: {e}", exc_info=True)
            return False, 0.0, f"Detection error: {str(e)}"
    
    def batch_detect_contradictions(
        self,
        new_chunk: str,
        existing_chunks: List[str],
        similarity_scores: List[float],
        trust_scores: Optional[List[float]] = None,
        threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Detect contradictions between new chunk and multiple existing chunks.
        
        Weighted by trust scores: contradictions with high-confidence knowledge
        have higher impact than contradictions with low-confidence knowledge.
        
        Processes in batch for efficiency.
        
        Args:
            new_chunk: The new chunk being ingested
            existing_chunks: List of existing chunk texts
            similarity_scores: Corresponding similarity scores
            trust_scores: Optional confidence/trust scores for each existing chunk (0-1)
            threshold: Minimum contradiction score threshold
            
        Returns:
            List of contradiction details for matches above threshold
        """
        if not self.model_available or not existing_chunks:
            return []
        
        contradictions = []
        
        # Initialize trust scores if not provided (default to 1.0 for unknown chunks)
        if trust_scores is None:
            trust_scores = [1.0] * len(existing_chunks)
        elif len(trust_scores) != len(existing_chunks):
            # Pad or truncate trust scores to match existing chunks
            trust_scores = trust_scores + [1.0] * (len(existing_chunks) - len(trust_scores))
            trust_scores = trust_scores[:len(existing_chunks)]
        
        try:
            # Prepare pairs for batch processing
            pairs = []
            valid_indices = []
            
            for i, (chunk, sim_score) in enumerate(zip(existing_chunks, similarity_scores)):
                if sim_score >= 0.6:  # Only check semantically similar chunks
                    pairs.append([new_chunk, chunk])
                    valid_indices.append(i)
            
            if not pairs:
                return []
            
            # Batch predict
            scores = self.model.predict(pairs, batch_size=16)
            
            # Process results
            for idx, pred_scores in zip(valid_indices, scores):
                contradiction_score = pred_scores[2]  # Contradiction is index 2
                
                if contradiction_score > threshold:
                    # Weight penalty by trust score of existing chunk
                    # Higher trust = higher impact of contradiction
                    trust_weight = trust_scores[idx]
                    weighted_penalty = float(similarity_scores[idx] * contradiction_score * trust_weight)
                    
                    contradictions.append({
                        "chunk_index": idx,
                        "existing_chunk": existing_chunks[idx][:150],
                        "similarity": float(similarity_scores[idx]),
                        "contradiction_confidence": float(contradiction_score),
                        "entailment_score": float(pred_scores[0]),
                        "neutral_score": float(pred_scores[1]),
                        "trust_score": float(trust_weight),
                        "penalty": weighted_penalty,
                    })
            
            logger.info(
                f"Found {len(contradictions)} contradictions in {len(pairs)} comparisons. "
                f"Weighted by trust scores."
            )
            return contradictions
            
        except Exception as e:
            logger.error(f"Error in batch contradiction detection: {e}", exc_info=True)
            return []
    
    def adjust_consensus_for_contradictions(
        self,
        new_chunk: str,
        existing_chunks_with_scores: List[Tuple[str, float]],
        existing_chunks_trust_scores: Optional[List[float]] = None,
        threshold: float = 0.7,
    ) -> Tuple[float, List[Dict]]:
        """
        Adjust consensus score accounting for semantic contradictions.
        
        If the new chunk contradicts high-confidence existing chunks,
        the consensus score is significantly reduced. Contradictions with
        high-trust existing knowledge have greater impact.
        
        Args:
            new_chunk: The new chunk being ingested
            existing_chunks_with_scores: List of (chunk_text, similarity_score) tuples
            existing_chunks_trust_scores: Optional list of trust/confidence scores (0-1)
            threshold: Minimum contradiction score threshold
            
        Returns:
            Tuple of (adjusted_consensus_score, contradiction_details)
        """
        if not self.model_available:
            # Fallback: use simple mean if model unavailable
            if existing_chunks_with_scores:
                return float(np.mean([score for _, score in existing_chunks_with_scores])), []
            return 0.5, []
        
        if not existing_chunks_with_scores:
            return 0.5, []
        
        # Extract texts and scores
        texts = [chunk for chunk, _ in existing_chunks_with_scores]
        similarity_scores = [score for _, score in existing_chunks_with_scores]
        
        # Initialize trust scores if not provided
        if existing_chunks_trust_scores is None:
            existing_chunks_trust_scores = [1.0] * len(texts)
        
        # Batch detect contradictions with trust scores
        contradiction_details = self.batch_detect_contradictions(
            new_chunk,
            texts,
            similarity_scores,
            existing_chunks_trust_scores,
            threshold
        )
        
        if not contradiction_details:
            # No contradictions found - use average similarity as consensus
            consensus_score = float(np.mean(similarity_scores))
            return consensus_score, []
        
        # Calculate supporting vs conflicting evidence
        supporting_similarities = []
        total_penalty = 0.0
        
        contradiction_indices = {c["chunk_index"] for c in contradiction_details}
        
        for i, sim_score in enumerate(similarity_scores):
            if i not in contradiction_indices:
                supporting_similarities.append(sim_score)
        
        # Calculate penalties
        for contradiction in contradiction_details:
            total_penalty += contradiction["penalty"]
        
        # Adjust consensus based on evidence mix
        if supporting_similarities:
            avg_support = np.mean(supporting_similarities)
            # Reduce supporting evidence by contradiction weight
            # But not below 0.1 (minimum viable confidence)
            consensus_score = max(0.1, avg_support - total_penalty)
        else:
            # Only contradictions found - significantly reduce confidence
            consensus_score = max(0.1, 0.5 - total_penalty)
        
        # Clamp to [0, 1]
        consensus_score = max(0.0, min(1.0, consensus_score))
        
        logger.info(
            f"Consensus adjusted from {np.mean(similarity_scores):.3f} "
            f"to {consensus_score:.3f} due to {len(contradiction_details)} contradictions. "
            f"Weighted by trust scores of existing knowledge."
        )
        
        return consensus_score, contradiction_details
    
    def analyze_claim_agreement(
        self,
        chunks: List[str],
    ) -> Dict[str, any]:
        """
        Analyze agreement/contradiction patterns across multiple chunks.
        
        Useful for understanding knowledge base consistency.
        
        Args:
            chunks: List of chunk texts to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not self.model_available or len(chunks) < 2:
            return {"status": "unavailable"}
        
        try:
            contradictions = []
            agreements = []
            
            # Check all pairs
            for i in range(len(chunks)):
                for j in range(i + 1, len(chunks)):
                    scores = self.model.predict([[chunks[i], chunks[j]]])
                    pred_scores = scores[0]
                    
                    if pred_scores[2] > 0.7:  # Contradiction
                        contradictions.append({
                            "chunk1_index": i,
                            "chunk2_index": j,
                            "confidence": float(pred_scores[2]),
                        })
                    elif pred_scores[0] > 0.7:  # Entailment
                        agreements.append({
                            "chunk1_index": i,
                            "chunk2_index": j,
                            "confidence": float(pred_scores[0]),
                        })
            
            return {
                "status": "complete",
                "total_pairs": len(chunks) * (len(chunks) - 1) // 2,
                "contradictions": contradictions,
                "agreements": agreements,
                "consistency_score": 1.0 - (len(contradictions) / max(1, len(chunks))),
            }
            
        except Exception as e:
            logger.error(f"Error in claim agreement analysis: {e}")
            return {"status": "error", "error": str(e)}
