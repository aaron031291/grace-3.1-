"""
Neural-to-Symbolic Rule Generator - Neuro-Symbolic Integration

Converts neural patterns (clusters, embeddings) into symbolic rules
that can be used for explicit reasoning.

Key Features:
- Pattern detection from neural clustering
- Automatic rule generation from patterns
- Trust score assignment based on pattern confidence
- Integration with symbolic knowledge base
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import uuid

from embedding import EmbeddingModel, get_embedding_model

try:
    from cognitive.learning_memory import TrustScorer
except ImportError:
    # Fallback if not available
    TrustScorer = None

logger = logging.getLogger(__name__)


@dataclass
class NeuralPattern:
    """Neural pattern detected from clustering/embedding analysis"""
    pattern_id: str
    cluster_center: np.ndarray  # Embedding center
    members: List[str]  # Text members
    member_indices: List[int]  # Original indices
    confidence: float  # Pattern confidence (0-1)
    support_count: int  # Number of supporting examples
    features: Dict[str, Any]  # Extracted features
    timestamp: datetime


@dataclass
class SymbolicRule:
    """Symbolic rule generated from neural pattern"""
    rule_id: str
    premise: Dict[str, Any]  # Conditions (IF)
    conclusion: Dict[str, Any]  # Outcome (THEN)
    trust_score: float  # Rule trust (0-1)
    confidence: float  # Pattern confidence
    source: str  # "neural_pattern_detection"
    source_pattern_id: str  # Link to neural pattern
    support_count: int  # Number of examples
    validation_count: int = 0
    invalidation_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class NeuralToSymbolicRuleGenerator:
    """
    Converts neural patterns into symbolic rules.
    
    This bridges the neural-symbolic gap by:
    - Detecting patterns in neural embedding space
    - Extracting features from patterns
    - Creating explicit symbolic rules
    - Assigning trust scores based on pattern confidence
    """
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        min_confidence: float = 0.7,
        min_support: int = 3,
        trust_scorer: Optional[TrustScorer] = None,
    ):
        """
        Initialize neural-to-symbolic rule generator.
        
        Args:
            embedding_model: EmbeddingModel for pattern detection
            min_confidence: Minimum pattern confidence to create rule
            min_support: Minimum examples to support a pattern
            trust_scorer: TrustScorer for rule trust calculation
        """
        self.embedding_model = embedding_model or get_embedding_model()
        self.min_confidence = min_confidence
        self.min_support = min_support
        if TrustScorer is not None:
            self.trust_scorer = trust_scorer or TrustScorer()
        else:
            self.trust_scorer = trust_scorer
        
        logger.info(f"[NEURAL→SYMBOLIC] Initialized with min_confidence={min_confidence}, min_support={min_support}")
    
    def detect_patterns(
        self,
        texts: List[str],
        num_clusters: int = 5,
        instruction: Optional[str] = None,
    ) -> List[NeuralPattern]:
        """
        Detect patterns in texts using neural clustering.
        
        Args:
            texts: List of texts to analyze
            num_clusters: Number of clusters to find
            instruction: Optional instruction for embedding
            
        Returns:
            List of detected neural patterns
        """
        if len(texts) < self.min_support:
            logger.warning(f"Not enough texts ({len(texts)}) for pattern detection")
            return []
        
        # Get embeddings
        embeddings = self.embedding_model.embed_text(
            texts,
            instruction=instruction,
            convert_to_numpy=True,
        )
        
        # Cluster
        clusters = self.embedding_model.cluster_texts(
            texts,
            num_clusters=min(num_clusters, len(texts)),
            instruction=instruction,
        )
        
        # Extract patterns from clusters
        patterns = []
        for cluster_idx, member_indices in enumerate(clusters):
            if len(member_indices) < self.min_support:
                continue
            
            # Calculate cluster center
            cluster_embeddings = embeddings[member_indices]
            cluster_center = np.mean(cluster_embeddings, axis=0)
            
            # Calculate confidence (cohesion = how tight the cluster is)
            distances = [
                np.linalg.norm(emb - cluster_center)
                for emb in cluster_embeddings
            ]
            avg_distance = np.mean(distances)
            max_distance = np.max(distances) if len(distances) > 0 else 0.0
            
            # Confidence: inverse of normalized distance
            # Tighter clusters = higher confidence
            confidence = 1.0 / (1.0 + avg_distance * 10.0)  # Normalize to 0-1
            confidence = min(1.0, max(0.0, confidence))
            
            # Extract features
            member_texts = [texts[i] for i in member_indices]
            features = self._extract_features(member_texts, cluster_embeddings)
            
            pattern = NeuralPattern(
                pattern_id=str(uuid.uuid4()),
                cluster_center=cluster_center,
                members=member_texts,
                member_indices=member_indices,
                confidence=confidence,
                support_count=len(member_indices),
                features=features,
                timestamp=datetime.now(),
            )
            
            patterns.append(pattern)
        
        logger.info(f"[NEURAL→SYMBOLIC] Detected {len(patterns)} patterns from {len(texts)} texts")
        return patterns
    
    def _extract_features(
        self,
        texts: List[str],
        embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """Extract features from text cluster."""
        # Basic features
        features = {
            "text_count": len(texts),
            "avg_text_length": np.mean([len(t) for t in texts]),
            "max_text_length": max([len(t) for t in texts]),
            "min_text_length": min([len(t) for t in texts]),
        }
        
        # Common keywords (simple heuristic)
        all_words = []
        for text in texts:
            words = text.lower().split()
            all_words.extend(words)
        
        from collections import Counter
        word_counts = Counter(all_words)
        common_words = [word for word, count in word_counts.most_common(10) if count >= 2]
        features["common_keywords"] = common_words
        
        # Embedding statistics
        if len(embeddings) > 0:
            features["embedding_variance"] = float(np.var(embeddings))
            features["embedding_mean_norm"] = float(np.mean([np.linalg.norm(e) for e in embeddings]))
        
        return features
    
    def pattern_to_rule(
        self,
        pattern: NeuralPattern,
        rule_type: str = "association",
    ) -> Optional[SymbolicRule]:
        """
        Convert a neural pattern to a symbolic rule.
        
        Args:
            pattern: Neural pattern to convert
            rule_type: Type of rule ("association", "implication", "classification")
            
        Returns:
            Symbolic rule or None if pattern doesn't meet criteria
        """
        # Check if pattern meets minimum criteria
        if pattern.confidence < self.min_confidence:
            logger.debug(f"Pattern {pattern.pattern_id} confidence {pattern.confidence} < {self.min_confidence}")
            return None
        
        if pattern.support_count < self.min_support:
            logger.debug(f"Pattern {pattern.pattern_id} support {pattern.support_count} < {self.min_support}")
            return None
        
        # Extract premise and conclusion from pattern
        premise, conclusion = self._extract_rule_structure(pattern, rule_type)
        
        # Calculate trust score
        trust_score = self._calculate_rule_trust(pattern)
        
        rule = SymbolicRule(
            rule_id=str(uuid.uuid4()),
            premise=premise,
            conclusion=conclusion,
            trust_score=trust_score,
            confidence=pattern.confidence,
            source="neural_pattern_detection",
            source_pattern_id=pattern.pattern_id,
            support_count=pattern.support_count,
        )
        
        logger.info(f"[NEURAL→SYMBOLIC] Created rule {rule.rule_id} with trust={trust_score:.2f}")
        return rule
    
    def _extract_rule_structure(
        self,
        pattern: NeuralPattern,
        rule_type: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract rule structure (premise, conclusion) from pattern.
        
        This is a simplified extraction - can be enhanced with NLP.
        """
        features = pattern.features
        
        if rule_type == "association":
            # IF: keywords present, THEN: likely in this cluster
            premise = {
                "keywords": features.get("common_keywords", [])[:5],
                "text_length_range": [
                    features.get("min_text_length", 0),
                    features.get("max_text_length", 1000),
                ],
            }
            conclusion = {
                "cluster_id": pattern.pattern_id,
                "pattern_confidence": pattern.confidence,
                "member_count": pattern.support_count,
            }
        
        elif rule_type == "classification":
            # IF: features, THEN: category
            premise = {
                "features": features,
            }
            conclusion = {
                "category": f"pattern_{pattern.pattern_id[:8]}",
                "confidence": pattern.confidence,
            }
        
        else:  # implication
            # IF: conditions, THEN: outcome
            premise = {
                "keywords": features.get("common_keywords", [])[:3],
            }
            conclusion = {
                "pattern_match": True,
                "confidence": pattern.confidence,
            }
        
        return premise, conclusion
    
    def _calculate_rule_trust(self, pattern: NeuralPattern) -> float:
        """Calculate trust score for rule based on pattern."""
        # Use pattern confidence as base
        base_trust = pattern.confidence
        
        # Adjust based on support count
        # More examples = more trustworthy
        support_factor = min(1.0, pattern.support_count / 10.0)  # Normalize to 10 examples
        
        # Combine: confidence weighted 70%, support weighted 30%
        trust_score = base_trust * 0.7 + support_factor * 0.3
        
        return min(1.0, max(0.0, trust_score))
    
    def generate_rules_from_texts(
        self,
        texts: List[str],
        num_clusters: int = 5,
        instruction: Optional[str] = None,
        rule_type: str = "association",
    ) -> List[SymbolicRule]:
        """
        Complete pipeline: detect patterns → generate rules.
        
        Args:
            texts: Texts to analyze
            num_clusters: Number of clusters
            instruction: Optional embedding instruction
            rule_type: Type of rules to generate
            
        Returns:
            List of generated symbolic rules
        """
        # Step 1: Detect patterns
        patterns = self.detect_patterns(
            texts,
            num_clusters=num_clusters,
            instruction=instruction,
        )
        
        # Step 2: Convert patterns to rules
        rules = []
        for pattern in patterns:
            rule = self.pattern_to_rule(pattern, rule_type=rule_type)
            if rule:
                rules.append(rule)
        
        logger.info(f"[NEURAL→SYMBOLIC] Generated {len(rules)} rules from {len(patterns)} patterns")
        return rules
    
    def validate_rule(
        self,
        rule: SymbolicRule,
        test_cases: List[Dict[str, Any]],
    ) -> Tuple[bool, float]:
        """
        Validate a rule against test cases.
        
        Returns:
            (is_valid, updated_trust_score)
        """
        # Simple validation: check if premise matches and conclusion is correct
        correct = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            # Check if premise matches
            premise_match = self._check_premise_match(rule.premise, test_case)
            
            if premise_match:
                # Check if conclusion matches
                conclusion_match = self._check_conclusion_match(rule.conclusion, test_case)
                if conclusion_match:
                    correct += 1
        
        accuracy = correct / total if total > 0 else 0.0
        
        # Update trust score based on validation
        validation_ratio = accuracy
        updated_trust = (rule.trust_score * 0.7 + validation_ratio * 0.3)
        
        return accuracy >= 0.7, updated_trust
    
    def _check_premise_match(
        self,
        premise: Dict[str, Any],
        test_case: Dict[str, Any],
    ) -> bool:
        """Check if test case matches rule premise (simplified)."""
        # Simplified matching - can be enhanced
        if "keywords" in premise:
            keywords = premise["keywords"]
            test_text = str(test_case.get("text", "")).lower()
            matches = sum(1 for kw in keywords if kw.lower() in test_text)
            return matches >= len(keywords) * 0.5  # 50% keyword match
        
        return True  # Default: match
    
    def _check_conclusion_match(
        self,
        conclusion: Dict[str, Any],
        test_case: Dict[str, Any],
    ) -> bool:
        """Check if test case matches rule conclusion (simplified)."""
        # Simplified matching - can be enhanced
        if "category" in conclusion:
            expected_category = conclusion["category"]
            actual_category = test_case.get("category", "")
            return expected_category == actual_category
        
        return True  # Default: match


def get_neural_to_symbolic_generator(
    embedding_model: Optional[EmbeddingModel] = None,
    min_confidence: float = 0.7,
    min_support: int = 3,
) -> NeuralToSymbolicRuleGenerator:
    """
    Get neural-to-symbolic rule generator instance.
    
    Args:
        embedding_model: EmbeddingModel (uses singleton if None)
        min_confidence: Minimum pattern confidence
        min_support: Minimum examples per pattern
        
    Returns:
        NeuralToSymbolicRuleGenerator instance
    """
    return NeuralToSymbolicRuleGenerator(
        embedding_model=embedding_model,
        min_confidence=min_confidence,
        min_support=min_support,
    )
