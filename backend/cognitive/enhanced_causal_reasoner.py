"""
Enhanced Causal Reasoner - Advanced Deterministic Causal Analysis

This module provides comprehensive causal reasoning with:
- Temporal ordering analysis
- Directed co-occurrence patterns
- Practice sequence analysis
- Validation chain analysis
- Causal relationship synthesis
- Predictive relationship strength

Maintains 100% determinism while providing rich causal insights.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict
from enum import Enum

from sqlalchemy.orm import Session
from cognitive.learning_memory import LearningExample

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Types of causal relationships."""
    TEMPORAL_SEQUENCE = "temporal_sequence"
    PRACTICE_SEQUENCE = "practice_sequence"
    VALIDATION_CHAIN = "validation_chain"
    CO_OCCURRENCE = "co_occurrence"
    CAUSAL = "causal"  # Strong causal relationship


class EvidenceStrength(Enum):
    """Strength of evidence for causal relationships."""
    WEAK = "weak"  # < 0.5
    MODERATE = "moderate"  # 0.5 - 0.7
    STRONG = "strong"  # 0.7 - 0.85
    VERY_STRONG = "very_strong"  # > 0.85


@dataclass
class TemporalPattern:
    """Represents a temporal ordering pattern."""
    topic: str
    before_topics: List[str]
    after_topics: List[str]
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'topic': self.topic,
            'before_topics': self.before_topics,
            'after_topics': self.after_topics,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class CausalRelationship:
    """Represents a causal relationship between topics."""
    cause: str
    effect: str
    strength: float  # 0-1, how strong the causal relationship is
    confidence: float  # 0-1, how confident we are about this relationship
    relationship_type: RelationshipType
    evidence: List[Dict[str, Any]]  # Evidence supporting this relationship
    evidence_strength: EvidenceStrength
    support_count: int  # Number of times this relationship was observed
    trust_weighted_strength: float  # Strength weighted by trust scores
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cause': self.cause,
            'effect': self.effect,
            'strength': self.strength,
            'confidence': self.confidence,
            'relationship_type': self.relationship_type.value,
            'evidence': self.evidence,
            'evidence_strength': self.evidence_strength.value,
            'support_count': self.support_count,
            'trust_weighted_strength': self.trust_weighted_strength
        }


@dataclass
class CausalAnalysis:
    """
    Comprehensive causal analysis result.
    """
    topic: str
    causal_relationships: List[CausalRelationship]
    confidence: float  # Overall confidence in analysis
    evidence_strength: EvidenceStrength
    temporal_patterns: List[TemporalPattern]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'topic': self.topic,
            'causal_relationships': [r.to_dict() for r in self.causal_relationships],
            'confidence': self.confidence,
            'evidence_strength': self.evidence_strength.value,
            'temporal_patterns': [p.to_dict() for p in self.temporal_patterns],
            'recommendations': self.recommendations
        }


class CausalReasoner:
    """
    Advanced causal reasoning for deterministic relationship analysis.
    
    Analyzes temporal patterns, practice sequences, and validation chains
    to identify causal relationships between topics.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize causal reasoner.
        
        Args:
            session: Database session for querying learning examples
        """
        self.session = session
        self.min_support_count = 3  # Minimum observations for relationship
        self.min_confidence = 0.6  # Minimum confidence threshold
    
    def analyze_causal_relationships(
        self,
        topic: str,
        learning_examples: Optional[List[LearningExample]] = None,
        min_strength: float = 0.5
    ) -> CausalAnalysis:
        """
        Analyze causal relationships for a topic.
        
        Args:
            topic: Topic to analyze
            learning_examples: Optional list of examples (if None, queries from DB)
            min_strength: Minimum relationship strength to include
            
        Returns:
            CausalAnalysis with all detected relationships
        """
        # Load examples if not provided
        if learning_examples is None:
            if not self.session:
                raise ValueError("Session required if learning_examples not provided")
            learning_examples = self._load_examples_for_topic(topic)
        
        # 1. Temporal Ordering Analysis
        temporal_patterns = self._analyze_temporal_ordering(
            topic,
            learning_examples
        )
        
        # 2. Directed Co-occurrence Analysis
        directed_cooccurrence = self._analyze_directed_cooccurrence(
            topic,
            learning_examples
        )
        
        # 3. Practice Sequence Analysis
        practice_sequences = self._analyze_practice_sequences(
            topic,
            learning_examples
        )
        
        # 4. Validation Chain Analysis
        validation_chains = self._analyze_validation_chains(
            topic,
            learning_examples
        )
        
        # 5. Synthesize Causal Relationships
        causal_relationships = self._synthesize_causal_relationships(
            temporal_patterns,
            directed_cooccurrence,
            practice_sequences,
            validation_chains,
            learning_examples,
            min_strength,
            topic  # Pass topic parameter
        )
        
        # Calculate overall confidence
        confidence = self._calculate_causal_confidence(causal_relationships)
        
        # Determine evidence strength
        evidence_strength = self._calculate_evidence_strength(causal_relationships)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            causal_relationships,
            confidence,
            evidence_strength
        )
        
        return CausalAnalysis(
            topic=topic,
            causal_relationships=causal_relationships,
            confidence=confidence,
            evidence_strength=evidence_strength,
            temporal_patterns=temporal_patterns,
            recommendations=recommendations
        )
    
    def _load_examples_for_topic(
        self,
        topic: str,
        limit: int = 1000
    ) -> List[LearningExample]:
        """Load learning examples for a topic."""
        if not self.session:
            return []
        
        # Query examples that mention this topic
        examples = self.session.query(LearningExample).filter(
            LearningExample.input_context.contains({'topic': topic})
        ).order_by(LearningExample.created_at).limit(limit).all()
        
        return examples
    
    def _analyze_temporal_ordering(
        self,
        topic: str,
        examples: List[LearningExample]
    ) -> List[TemporalPattern]:
        """
        Analyze temporal ordering of topics in learning examples.
        
        Identifies what topics come before and after the target topic.
        """
        patterns = []
        
        # Group examples by session/study sequence
        sessions = self._group_by_session(examples)
        
        for session_id, session_examples in sessions.items():
            # Sort by timestamp
            sorted_examples = sorted(
                session_examples,
                key=lambda e: e.created_at if hasattr(e, 'created_at') else datetime.utcnow()
            )
            
            # Find topic position
            topic_indices = [
                i for i, ex in enumerate(sorted_examples)
                if self._extract_topic(ex) == topic
            ]
            
            for topic_idx in topic_indices:
                # Get topics before and after
                before_topics = [
                    self._extract_topic(sorted_examples[i])
                    for i in range(topic_idx)
                    if i < len(sorted_examples)
                ]
                
                after_topics = [
                    self._extract_topic(sorted_examples[i])
                    for i in range(topic_idx + 1, len(sorted_examples))
                ]
                
                # Get timestamp
                timestamp = None
                if hasattr(sorted_examples[topic_idx], 'created_at'):
                    timestamp = sorted_examples[topic_idx].created_at
                
                patterns.append(TemporalPattern(
                    topic=topic,
                    before_topics=before_topics,
                    after_topics=after_topics,
                    session_id=session_id,
                    timestamp=timestamp
                ))
        
        return patterns
    
    def _analyze_directed_cooccurrence(
        self,
        topic: str,
        examples: List[LearningExample]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze directed co-occurrence patterns.
        
        Tracks which topics appear together with the target topic,
        and in what order.
        """
        cooccurrence = defaultdict(lambda: {
            'before_count': 0,
            'after_count': 0,
            'together_count': 0,
            'trust_scores': []
        })
        
        # Group by session
        sessions = self._group_by_session(examples)
        
        for session_id, session_examples in sessions.items():
            sorted_examples = sorted(
                session_examples,
                key=lambda e: e.created_at if hasattr(e, 'created_at') else datetime.utcnow()
            )
            
            topic_indices = [
                i for i, ex in enumerate(sorted_examples)
                if self._extract_topic(ex) == topic
            ]
            
            for topic_idx in topic_indices:
                # Check topics before
                for i in range(topic_idx):
                    other_topic = self._extract_topic(sorted_examples[i])
                    if other_topic and other_topic != topic:
                        cooccurrence[other_topic]['before_count'] += 1
                        if hasattr(sorted_examples[i], 'trust_score'):
                            cooccurrence[other_topic]['trust_scores'].append(
                                sorted_examples[i].trust_score
                            )
                
                # Check topics after
                for i in range(topic_idx + 1, len(sorted_examples)):
                    other_topic = self._extract_topic(sorted_examples[i])
                    if other_topic and other_topic != topic:
                        cooccurrence[other_topic]['after_count'] += 1
                        if hasattr(sorted_examples[i], 'trust_score'):
                            cooccurrence[other_topic]['trust_scores'].append(
                                sorted_examples[i].trust_score
                            )
        
        return dict(cooccurrence)
    
    def _analyze_practice_sequences(
        self,
        topic: str,
        examples: List[LearningExample]
    ) -> List[Dict[str, Any]]:
        """
        Analyze practice sequences (when topics are practiced together).
        """
        sequences = []
        
        # Filter to practice examples
        practice_examples = [
            ex for ex in examples
            if hasattr(ex, 'example_type') and 'practice' in str(ex.example_type).lower()
        ]
        
        # Group by practice session
        practice_sessions = self._group_by_session(practice_examples)
        
        for session_id, session_examples in practice_sessions.items():
            sorted_examples = sorted(
                session_examples,
                key=lambda e: e.created_at if hasattr(e, 'created_at') else datetime.utcnow()
            )
            
            topics = [self._extract_topic(ex) for ex in sorted_examples]
            
            if topic in topics:
                topic_idx = topics.index(topic)
                sequences.append({
                    'session_id': session_id,
                    'sequence': topics,
                    'topic_position': topic_idx,
                    'before_topics': topics[:topic_idx],
                    'after_topics': topics[topic_idx + 1:],
                    'success_rate': self._calculate_practice_success_rate(session_examples)
                })
        
        return sequences
    
    def _analyze_validation_chains(
        self,
        topic: str,
        examples: List[LearningExample]
    ) -> List[Dict[str, Any]]:
        """
        Analyze validation chains (when validation of one topic leads to another).
        """
        chains = []
        
        # Find examples with validation history
        validated_examples = [
            ex for ex in examples
            if hasattr(ex, 'times_validated') and ex.times_validated > 0
        ]
        
        # Group by validation session
        validation_sessions = self._group_by_session(validated_examples)
        
        for session_id, session_examples in validation_sessions.items():
            sorted_examples = sorted(
                session_examples,
                key=lambda e: e.created_at if hasattr(e, 'created_at') else datetime.utcnow()
            )
            
            topics = [self._extract_topic(ex) for ex in sorted_examples]
            
            if topic in topics:
                topic_idx = topics.index(topic)
                chains.append({
                    'session_id': session_id,
                    'chain': topics,
                    'topic_position': topic_idx,
                    'validation_counts': [
                        ex.times_validated if hasattr(ex, 'times_validated') else 0
                        for ex in sorted_examples
                    ]
                })
        
        return chains
    
    def _synthesize_causal_relationships(
        self,
        temporal_patterns: List[TemporalPattern],
        directed_cooccurrence: Dict[str, Dict[str, Any]],
        practice_sequences: List[Dict[str, Any]],
        validation_chains: List[Dict[str, Any]],
        examples: List[LearningExample],
        min_strength: float,
        topic: str  # Add topic parameter
    ) -> List[CausalRelationship]:
        """
        Synthesize causal relationships from multiple evidence sources.
        """
        relationships = defaultdict(lambda: {
            'evidence': [],
            'support_count': 0,
            'trust_scores': []
        })
        
        # 1. From temporal patterns (topic A often comes before topic B)
        for pattern in temporal_patterns:
            for after_topic in pattern.after_topics:
                if after_topic:
                    relationships[(pattern.topic, after_topic)]['evidence'].append({
                        'type': 'temporal_ordering',
                        'strength': 0.7,
                        'pattern': pattern.to_dict()
                    })
                    relationships[(pattern.topic, after_topic)]['support_count'] += 1
        
        # 2. From directed co-occurrence (strong directional patterns)
        for other_topic, data in directed_cooccurrence.items():
            if data['after_count'] > data['before_count'] * 2:
                # Strong directional pattern: topic → other_topic
                strength = min(0.9, data['after_count'] / (data['before_count'] + 1))
                relationships[(topic, other_topic)]['evidence'].append({
                    'type': 'directed_cooccurrence',
                    'strength': strength,
                    'after_count': data['after_count'],
                    'before_count': data['before_count']
                })
                relationships[(topic, other_topic)]['support_count'] += data['after_count']
                if data['trust_scores']:
                    relationships[(topic, other_topic)]['trust_scores'].extend(data['trust_scores'])
        
        # 3. From practice sequences (practice A often leads to practice B)
        for sequence in practice_sequences:
            if sequence['after_topics']:
                for after_topic in sequence['after_topics']:
                    relationships[(topic, after_topic)]['evidence'].append({
                        'type': 'practice_sequence',
                        'strength': 0.8,
                        'success_rate': sequence.get('success_rate', 0.5)
                    })
                    relationships[(topic, after_topic)]['support_count'] += 1
        
        # 4. From validation chains (validating A often leads to validating B)
        for chain in validation_chains:
            chain_topics = chain['chain']
            topic_idx = chain['topic_position']
            if topic_idx < len(chain_topics) - 1:
                next_topic = chain_topics[topic_idx + 1]
                relationships[(topic, next_topic)]['evidence'].append({
                    'type': 'validation_chain',
                    'strength': 0.75,
                    'validation_count': chain['validation_counts'][topic_idx] if topic_idx < len(chain['validation_counts']) else 0
                })
                relationships[(topic, next_topic)]['support_count'] += 1
        
        # Convert to CausalRelationship objects
        causal_relationships = []
        for (cause, effect), data in relationships.items():
            if data['support_count'] < self.min_support_count:
                continue  # Not enough evidence
            
            # Calculate strength from evidence
            strength = self._calculate_relationship_strength(data['evidence'])
            
            if strength < min_strength:
                continue  # Below minimum threshold
            
            # Calculate confidence
            confidence = self._calculate_relationship_confidence(
                data['support_count'],
                data['evidence'],
                len(examples)
            )
            
            if confidence < self.min_confidence:
                continue  # Below minimum confidence
            
            # Calculate trust-weighted strength
            trust_weighted_strength = strength
            if data['trust_scores']:
                avg_trust = sum(data['trust_scores']) / len(data['trust_scores'])
                trust_weighted_strength = strength * avg_trust
            
            # Determine relationship type
            relationship_type = self._determine_relationship_type(data['evidence'])
            
            # Determine evidence strength
            evidence_strength = self._determine_evidence_strength(strength, confidence, data['support_count'])
            
            causal_relationships.append(CausalRelationship(
                cause=cause,
                effect=effect,
                strength=strength,
                confidence=confidence,
                relationship_type=relationship_type,
                evidence=data['evidence'],
                evidence_strength=evidence_strength,
                support_count=data['support_count'],
                trust_weighted_strength=trust_weighted_strength
            ))
        
        # Sort by trust-weighted strength
        causal_relationships.sort(key=lambda r: r.trust_weighted_strength, reverse=True)
        
        return causal_relationships
    
    def _calculate_relationship_strength(self, evidence: List[Dict[str, Any]]) -> float:
        """Calculate relationship strength from evidence."""
        if not evidence:
            return 0.0
        
        # Weighted average of evidence strengths
        total_weight = 0.0
        weighted_sum = 0.0
        
        for ev in evidence:
            ev_strength = ev.get('strength', 0.5)
            # Weight by evidence type
            if ev['type'] == 'practice_sequence':
                weight = 1.2  # Practice sequences are strong evidence
            elif ev['type'] == 'validation_chain':
                weight = 1.1  # Validation chains are good evidence
            elif ev['type'] == 'directed_cooccurrence':
                weight = 1.0
            else:
                weight = 0.9
            
            weighted_sum += ev_strength * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_relationship_confidence(
        self,
        support_count: int,
        evidence: List[Dict[str, Any]],
        total_examples: int
    ) -> float:
        """Calculate confidence in relationship."""
        # Base confidence from support count
        if total_examples == 0:
            return 0.0
        
        support_ratio = support_count / total_examples
        
        # Boost confidence with more evidence types
        evidence_diversity = len(set(ev['type'] for ev in evidence))
        diversity_boost = min(0.2, evidence_diversity * 0.05)
        
        # Combine
        confidence = min(1.0, support_ratio * 0.7 + diversity_boost)
        
        return confidence
    
    def _determine_relationship_type(self, evidence: List[Dict[str, Any]]) -> RelationshipType:
        """Determine the type of relationship based on evidence."""
        evidence_types = [ev['type'] for ev in evidence]
        
        if 'practice_sequence' in evidence_types:
            return RelationshipType.PRACTICE_SEQUENCE
        elif 'validation_chain' in evidence_types:
            return RelationshipType.VALIDATION_CHAIN
        elif 'temporal_ordering' in evidence_types:
            return RelationshipType.TEMPORAL_SEQUENCE
        elif 'directed_cooccurrence' in evidence_types:
            return RelationshipType.CO_OCCURRENCE
        else:
            return RelationshipType.CAUSAL
    
    def _determine_evidence_strength(
        self,
        strength: float,
        confidence: float,
        support_count: int
    ) -> EvidenceStrength:
        """Determine evidence strength category."""
        combined_score = (strength + confidence) / 2
        
        if combined_score >= 0.85 and support_count >= 10:
            return EvidenceStrength.VERY_STRONG
        elif combined_score >= 0.7 and support_count >= 5:
            return EvidenceStrength.STRONG
        elif combined_score >= 0.5:
            return EvidenceStrength.MODERATE
        else:
            return EvidenceStrength.WEAK
    
    def _calculate_causal_confidence(self, relationships: List[CausalRelationship]) -> float:
        """Calculate overall confidence in causal analysis."""
        if not relationships:
            return 0.0
        
        # Average confidence weighted by strength
        total_weight = sum(r.strength for r in relationships)
        if total_weight == 0:
            return 0.0
        
        weighted_confidence = sum(r.confidence * r.strength for r in relationships)
        return weighted_confidence / total_weight
    
    def _calculate_evidence_strength(self, relationships: List[CausalRelationship]) -> EvidenceStrength:
        """Calculate overall evidence strength."""
        if not relationships:
            return EvidenceStrength.WEAK
        
        # Use the strongest relationship's evidence strength
        strongest = max(relationships, key=lambda r: r.strength)
        return strongest.evidence_strength
    
    def _generate_recommendations(
        self,
        relationships: List[CausalRelationship],
        confidence: float,
        evidence_strength: EvidenceStrength
    ) -> List[str]:
        """Generate recommendations based on causal analysis."""
        recommendations = []
        
        if not relationships:
            recommendations.append("No causal relationships found. More data needed.")
            return recommendations
        
        if evidence_strength == EvidenceStrength.VERY_STRONG:
            recommendations.append("Very strong evidence for causal relationships. High confidence predictions possible.")
        elif evidence_strength == EvidenceStrength.STRONG:
            recommendations.append("Strong evidence for causal relationships. Good confidence in predictions.")
        elif evidence_strength == EvidenceStrength.MODERATE:
            recommendations.append("Moderate evidence. Consider additional validation.")
        else:
            recommendations.append("Weak evidence. More observations needed for reliable predictions.")
        
        # Top relationships
        top_relationships = relationships[:3]
        if top_relationships:
            recommendations.append(f"Top causal relationships:")
            for i, rel in enumerate(top_relationships, 1):
                recommendations.append(
                    f"  {i}. {rel.cause} → {rel.effect} "
                    f"(strength: {rel.strength:.2f}, confidence: {rel.confidence:.2f})"
                )
        
        return recommendations
    
    # Helper methods
    
    def _group_by_session(self, examples: List[LearningExample]) -> Dict[str, List[LearningExample]]:
        """Group examples by session."""
        sessions = defaultdict(list)
        
        for example in examples:
            session_id = None
            if hasattr(example, 'session_id'):
                session_id = example.session_id
            elif hasattr(example, 'input_context'):
                if isinstance(example.input_context, dict):
                    session_id = example.input_context.get('session_id')
            
            session_id = session_id or 'default'
            sessions[session_id].append(example)
        
        return dict(sessions)
    
    def _extract_topic(self, example: LearningExample) -> str:
        """Extract topic from learning example."""
        if hasattr(example, 'input_context'):
            if isinstance(example.input_context, dict):
                return example.input_context.get('topic', '')
            return str(example.input_context)
        return ''
    
    def _calculate_practice_success_rate(self, examples: List[LearningExample]) -> float:
        """Calculate success rate for practice examples."""
        if not examples:
            return 0.0
        
        success_count = 0
        for ex in examples:
            if hasattr(ex, 'actual_output'):
                if isinstance(ex.actual_output, dict):
                    if ex.actual_output.get('success', False):
                        success_count += 1
        
        return success_count / len(examples) if examples else 0.0


# Global instance
_causal_reasoner: Optional[CausalReasoner] = None


def get_causal_reasoner(session: Optional[Session] = None) -> CausalReasoner:
    """Get or create global causal reasoner instance."""
    global _causal_reasoner
    if _causal_reasoner is None or session is not None:
        _causal_reasoner = CausalReasoner(session=session)
    return _causal_reasoner
