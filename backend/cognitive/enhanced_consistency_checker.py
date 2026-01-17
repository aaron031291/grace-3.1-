import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
class ContradictionType(Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of contradictions detected."""
    DIRECT_NEGATION = "direct_negation"
    SEMANTIC_CONTRADICTION = "semantic_contradiction"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    TEMPORAL_CONFLICT = "temporal_conflict"
    SOURCE_CONFLICT = "source_conflict"


class Severity(Enum):
    """Severity levels for consistency issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Contradiction:
    """Represents a detected contradiction."""
    type: ContradictionType
    new_concept: str
    existing_concept: str
    new_trust: float
    existing_trust: float
    severity: Severity
    confidence: float  # How confident we are about this contradiction (0-1)
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type.value,
            'new_concept': self.new_concept,
            'existing_concept': self.existing_concept,
            'new_trust': self.new_trust,
            'existing_trust': self.existing_trust,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'details': self.details
        }


@dataclass
class LogicalIssue:
    """Represents a logical inconsistency."""
    type: str
    new_relationship: Dict[str, Any]
    existing_relationship: Dict[str, Any]
    severity: Severity
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type,
            'new_relationship': self.new_relationship,
            'existing_relationship': self.existing_relationship,
            'severity': self.severity.value,
            'description': self.description
        }


@dataclass
class ConsistencyResult:
    """
    Comprehensive consistency check result.
    """
    consistency_score: float  # Overall consistency (0-1)
    direct_contradictions: List[Contradiction]
    logical_inconsistencies: List[LogicalIssue]
    semantic_conflicts: List[Contradiction]
    temporal_conflicts: List[Dict[str, Any]]
    source_conflicts: List[Dict[str, Any]]
    total_issues: int
    highest_severity: Optional[Severity]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'consistency_score': self.consistency_score,
            'direct_contradictions': [c.to_dict() for c in self.direct_contradictions],
            'logical_inconsistencies': [l.to_dict() for l in self.logical_inconsistencies],
            'semantic_conflicts': [c.to_dict() for c in self.semantic_conflicts],
            'temporal_conflicts': self.temporal_conflicts,
            'source_conflicts': self.source_conflicts,
            'total_issues': self.total_issues,
            'highest_severity': self.highest_severity.value if self.highest_severity else None,
            'recommendations': self.recommendations
        }


class ConsistencyChecker:
    """
    Advanced consistency checker with multiple validation methods.
    
    Maintains 100% determinism while providing comprehensive consistency analysis.
    """
    
    def __init__(self, use_semantic_detection: bool = True):
        """
        Initialize consistency checker.
        
        Args:
            use_semantic_detection: If True, use semantic contradiction detector
        """
        self.use_semantic_detection = use_semantic_detection
        self.semantic_detector = None
        
        if use_semantic_detection:
            try:
                from confidence_scorer.contradiction_detector import SemanticContradictionDetector
                self.semantic_detector = SemanticContradictionDetector(use_gpu=True)
                logger.info("[CONSISTENCY] Semantic contradiction detector loaded")
            except ImportError:
                logger.warning("[CONSISTENCY] Semantic detector not available, using rule-based only")
                self.use_semantic_detection = False
        
        # Negation patterns for direct contradiction detection
        self.negation_patterns = [
            ('is', 'is not'),
            ('is not', 'is'),
            ('should', 'should not'),
            ('should not', 'should'),
            ('must', 'must not'),
            ('must not', 'must'),
            ('always', 'never'),
            ('never', 'always'),
            ('true', 'false'),
            ('false', 'true'),
            ('correct', 'incorrect'),
            ('incorrect', 'correct'),
            ('valid', 'invalid'),
            ('invalid', 'valid'),
        ]
    
    def check_consistency(
        self,
        new_example: Any,  # LearningExample or dict-like
        existing_examples: List[Any],
        topic: Optional[str] = None
    ) -> ConsistencyResult:
        """
        Comprehensive consistency check with contradiction detection.
        
        Args:
            new_example: New learning example to check
            existing_examples: List of existing learning examples
            topic: Optional topic to filter examples
            
        Returns:
            ConsistencyResult with all detected issues
        """
        # Extract concept and topic from new example
        new_concept = self._extract_concept(new_example)
        new_topic = topic or self._extract_topic(new_example)
        new_trust = self._extract_trust_score(new_example)
        
        # Filter existing examples by topic if provided
        if topic:
            existing_examples = [
                ex for ex in existing_examples
                if self._extract_topic(ex) == topic
            ]
        
        results = {
            'direct_contradictions': [],
            'logical_inconsistencies': [],
            'semantic_conflicts': [],
            'temporal_conflicts': [],
            'source_conflicts': []
        }
        
        # 1. Direct Contradiction Detection
        contradictions = self._detect_direct_contradictions(
            new_example,
            existing_examples
        )
        results['direct_contradictions'] = contradictions
        
        # 2. Semantic Conflict Detection (if available)
        if self.use_semantic_detection and self.semantic_detector:
            semantic_conflicts = self._detect_semantic_conflicts(
                new_example,
                existing_examples
            )
            results['semantic_conflicts'] = semantic_conflicts
        
        # 3. Logical Consistency Check
        logical_issues = self._check_logical_consistency(
            new_example,
            existing_examples
        )
        results['logical_inconsistencies'] = logical_issues
        
        # 4. Temporal Conflict Detection
        temporal_conflicts = self._detect_temporal_conflicts(
            new_example,
            existing_examples
        )
        results['temporal_conflicts'] = temporal_conflicts
        
        # 5. Source Conflict Detection
        source_conflicts = self._detect_source_conflicts(
            new_example,
            existing_examples
        )
        results['source_conflicts'] = source_conflicts
        
        # Calculate overall consistency score
        total_issues = (
            len(contradictions) +
            len(results['semantic_conflicts']) +
            len(logical_issues) +
            len(temporal_conflicts) +
            len(source_conflicts)
        )
        
        # Calculate consistency score (penalty based on issues)
        consistency_score = self._calculate_consistency_score(
            total_issues,
            contradictions,
            results['semantic_conflicts'],
            logical_issues,
            new_trust
        )
        
        # Determine highest severity
        all_issues = (
            contradictions +
            results['semantic_conflicts'] +
            logical_issues
        )
        highest_severity = self._get_highest_severity(all_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            consistency_score,
            contradictions,
            results['semantic_conflicts'],
            logical_issues,
            temporal_conflicts,
            source_conflicts
        )
        
        return ConsistencyResult(
            consistency_score=consistency_score,
            direct_contradictions=contradictions,
            logical_inconsistencies=logical_issues,
            semantic_conflicts=results['semantic_conflicts'],
            temporal_conflicts=temporal_conflicts,
            source_conflicts=source_conflicts,
            total_issues=total_issues,
            highest_severity=highest_severity,
            recommendations=recommendations
        )
    
    def _detect_direct_contradictions(
        self,
        new_example: Any,
        existing_examples: List[Any]
    ) -> List[Contradiction]:
        """
        Detect direct contradictions using negation patterns.
        """
        contradictions = []
        
        new_concept = self._extract_concept(new_example)
        new_topic = self._extract_topic(new_example)
        new_trust = self._extract_trust_score(new_example)
        
        for existing_example in existing_examples:
            existing_topic = self._extract_topic(existing_example)
            
            # Only check same topic
            if existing_topic != new_topic:
                continue
            
            existing_concept = self._extract_concept(existing_example)
            existing_trust = self._extract_trust_score(existing_example)
            
            # Check for explicit negation patterns
            if self._is_negation(new_concept, existing_concept):
                # Determine severity based on trust scores
                if new_trust >= 0.8 and existing_trust >= 0.8:
                    severity = Severity.CRITICAL
                elif new_trust >= 0.7 or existing_trust >= 0.7:
                    severity = Severity.HIGH
                else:
                    severity = Severity.MEDIUM
                
                contradictions.append(Contradiction(
                    type=ContradictionType.DIRECT_NEGATION,
                    new_concept=new_concept,
                    existing_concept=existing_concept,
                    new_trust=new_trust,
                    existing_trust=existing_trust,
                    severity=severity,
                    confidence=0.9,  # High confidence for explicit negation
                    details={
                        'new_topic': new_topic,
                        'existing_topic': existing_topic,
                        'negation_pattern': self._find_negation_pattern(new_concept, existing_concept)
                    }
                ))
        
        return contradictions
    
    def _detect_semantic_conflicts(
        self,
        new_example: Any,
        existing_examples: List[Any]
    ) -> List[Contradiction]:
        """
        Detect semantic contradictions using NLI model.
        """
        if not self.semantic_detector:
            return []
        
        conflicts = []
        new_concept = self._extract_concept(new_example)
        new_topic = self._extract_topic(new_example)
        new_trust = self._extract_trust_score(new_example)
        
        for existing_example in existing_examples:
            existing_topic = self._extract_topic(existing_example)
            
            # Only check same topic
            if existing_topic != new_topic:
                continue
            
            existing_concept = self._extract_concept(existing_example)
            existing_trust = self._extract_trust_score(existing_example)
            
            # Use semantic detector
            is_contradictory, contradiction_score, reason = self.semantic_detector.detect_contradiction(
                new_concept,
                existing_concept,
                similarity_score=0.8,  # Assume high similarity for same topic
                threshold=0.7
            )
            
            if is_contradictory:
                # Determine severity
                if contradiction_score >= 0.9:
                    severity = Severity.HIGH
                elif contradiction_score >= 0.8:
                    severity = Severity.MEDIUM
                else:
                    severity = Severity.LOW
                
                conflicts.append(Contradiction(
                    type=ContradictionType.SEMANTIC_CONTRADICTION,
                    new_concept=new_concept,
                    existing_concept=existing_concept,
                    new_trust=new_trust,
                    existing_trust=existing_trust,
                    severity=severity,
                    confidence=contradiction_score,
                    details={
                        'reason': reason,
                        'contradiction_score': contradiction_score,
                        'new_topic': new_topic,
                        'existing_topic': existing_topic
                    }
                ))
        
        return conflicts
    
    def _check_logical_consistency(
        self,
        new_example: Any,
        existing_examples: List[Any]
    ) -> List[LogicalIssue]:
        """
        Check for logical inconsistencies (A implies B, but B contradicts C).
        """
        issues = []
        
        # Extract logical relationships
        new_relationships = self._extract_logical_relationships(new_example)
        
        for existing_example in existing_examples:
            existing_relationships = self._extract_logical_relationships(existing_example)
            
            # Check for logical conflicts
            for new_rel in new_relationships:
                for existing_rel in existing_relationships:
                    if self._are_logically_inconsistent(new_rel, existing_rel):
                        issues.append(LogicalIssue(
                            type='logical_inconsistency',
                            new_relationship=new_rel,
                            existing_relationship=existing_rel,
                            severity=Severity.HIGH,
                            description=f"Logical conflict: {new_rel.get('description', '')} contradicts {existing_rel.get('description', '')}"
                        ))
        
        return issues
    
    def _detect_temporal_conflicts(
        self,
        new_example: Any,
        existing_examples: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect temporal conflicts (e.g., version conflicts, outdated information).
        """
        conflicts = []
        
        new_topic = self._extract_topic(new_example)
        new_timestamp = self._extract_timestamp(new_example)
        new_concept = self._extract_concept(new_example)
        
        for existing_example in existing_examples:
            existing_topic = self._extract_topic(existing_example)
            
            if existing_topic != new_topic:
                continue
            
            existing_timestamp = self._extract_timestamp(existing_example)
            existing_concept = self._extract_concept(existing_example)
            
            # Check if concepts are similar but timestamps suggest version conflict
            if self._are_similar_concepts(new_concept, existing_concept):
                time_diff = abs((new_timestamp - existing_timestamp).total_seconds())
                
                # If very similar but different timestamps, might be version conflict
                if time_diff > 86400:  # More than 1 day difference
                    conflicts.append({
                        'type': 'temporal_conflict',
                        'new_timestamp': new_timestamp.isoformat(),
                        'existing_timestamp': existing_timestamp.isoformat(),
                        'time_difference_days': time_diff / 86400,
                        'topic': new_topic,
                        'severity': Severity.LOW if time_diff < 7 * 86400 else Severity.MEDIUM
                    })
        
        return conflicts
    
    def _detect_source_conflicts(
        self,
        new_example: Any,
        existing_examples: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between different sources on the same topic.
        """
        conflicts = []
        
        new_topic = self._extract_topic(new_example)
        new_source = self._extract_source(new_example)
        new_concept = self._extract_concept(new_example)
        new_trust = self._extract_trust_score(new_example)
        
        # Group existing examples by source
        source_groups = {}
        for existing_example in existing_examples:
            existing_topic = self._extract_topic(existing_example)
            if existing_topic != new_topic:
                continue
            
            existing_source = self._extract_source(existing_example)
            if existing_source not in source_groups:
                source_groups[existing_source] = []
            source_groups[existing_source].append(existing_example)
        
        # Check if new source conflicts with existing sources
        for source, examples in source_groups.items():
            if source == new_source:
                continue  # Same source, not a conflict
            
            # Check if concepts differ significantly
            for existing_example in examples:
                existing_concept = self._extract_concept(existing_example)
                existing_trust = self._extract_trust_score(existing_example)
                
                # If concepts are different and both have high trust, it's a conflict
                if not self._are_similar_concepts(new_concept, existing_concept):
                    if new_trust >= 0.7 and existing_trust >= 0.7:
                        conflicts.append({
                            'type': 'source_conflict',
                            'new_source': new_source,
                            'existing_source': source,
                            'topic': new_topic,
                            'new_trust': new_trust,
                            'existing_trust': existing_trust,
                            'severity': Severity.MEDIUM if (new_trust + existing_trust) / 2 >= 0.8 else Severity.LOW
                        })
        
        return conflicts
    
    def _calculate_consistency_score(
        self,
        total_issues: int,
        contradictions: List[Contradiction],
        semantic_conflicts: List[Contradiction],
        logical_issues: List[LogicalIssue],
        new_trust: float
    ) -> float:
        """
        Calculate overall consistency score based on detected issues.
        """
        # Start with perfect consistency
        score = 1.0
        
        # Penalty for direct contradictions (high impact)
        for contradiction in contradictions:
            if contradiction.severity == Severity.CRITICAL:
                score -= 0.3
            elif contradiction.severity == Severity.HIGH:
                score -= 0.2
            elif contradiction.severity == Severity.MEDIUM:
                score -= 0.1
            else:
                score -= 0.05
        
        # Penalty for semantic conflicts
        for conflict in semantic_conflicts:
            # Weight by confidence
            penalty = conflict.confidence * 0.15
            score -= penalty
        
        # Penalty for logical issues
        for issue in logical_issues:
            if issue.severity == Severity.HIGH:
                score -= 0.15
            else:
                score -= 0.05
        
        # Ensure score stays in [0, 1]
        score = max(0.0, min(1.0, score))
        
        # Adjust based on new trust score (higher trust = more weight on consistency)
        if new_trust >= 0.8:
            # High trust knowledge needs high consistency
            if score < 0.7:
                score *= 0.8  # Additional penalty
        elif new_trust < 0.5:
            # Low trust knowledge can have lower consistency
            score = max(score, 0.3)  # Minimum floor
        
        return max(0.0, min(1.0, score))
    
    def _generate_recommendations(
        self,
        consistency_score: float,
        contradictions: List[Contradiction],
        semantic_conflicts: List[Contradiction],
        logical_issues: List[LogicalIssue],
        temporal_conflicts: List[Dict],
        source_conflicts: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on detected issues."""
        recommendations = []
        
        if consistency_score < 0.5:
            recommendations.append("CRITICAL: Very low consistency score. Review all contradictions before accepting.")
        
        if contradictions:
            recommendations.append(f"Found {len(contradictions)} direct contradictions. Verify which source is correct.")
        
        if semantic_conflicts:
            recommendations.append(f"Found {len(semantic_conflicts)} semantic conflicts. Consider additional validation.")
        
        if logical_issues:
            recommendations.append(f"Found {len(logical_issues)} logical inconsistencies. Review relationship chains.")
        
        if temporal_conflicts:
            recommendations.append(f"Found {len(temporal_conflicts)} temporal conflicts. Check if information is outdated.")
        
        if source_conflicts:
            recommendations.append(f"Found {len(source_conflicts)} source conflicts. Multiple sources disagree on this topic.")
        
        if consistency_score >= 0.8:
            recommendations.append("Consistency is good. Proceed with confidence.")
        
        return recommendations
    
    # Helper methods for extracting data from examples
    
    def _extract_concept(self, example: Any) -> str:
        """Extract concept from learning example."""
        if hasattr(example, 'expected_output'):
            if isinstance(example.expected_output, dict):
                return example.expected_output.get('concept', '')
            return str(example.expected_output)
        elif isinstance(example, dict):
            return example.get('expected_output', {}).get('concept', '')
        return ''
    
    def _extract_topic(self, example: Any) -> str:
        """Extract topic from learning example."""
        if hasattr(example, 'input_context'):
            if isinstance(example.input_context, dict):
                return example.input_context.get('topic', '')
            return str(example.input_context)
        elif isinstance(example, dict):
            return example.get('input_context', {}).get('topic', '')
        return ''
    
    def _extract_trust_score(self, example: Any) -> float:
        """Extract trust score from learning example."""
        if hasattr(example, 'trust_score'):
            return float(example.trust_score)
        elif isinstance(example, dict):
            return float(example.get('trust_score', 0.5))
        return 0.5
    
    def _extract_timestamp(self, example: Any) -> datetime:
        """Extract timestamp from learning example."""
        if hasattr(example, 'created_at'):
            return example.created_at
        elif isinstance(example, dict):
            ts = example.get('created_at')
            if isinstance(ts, str):
                return datetime.fromisoformat(ts)
            return ts or datetime.utcnow()
        return datetime.utcnow()
    
    def _extract_source(self, example: Any) -> str:
        """Extract source from learning example."""
        if hasattr(example, 'source'):
            return str(example.source)
        elif isinstance(example, dict):
            return str(example.get('source', 'unknown'))
        return 'unknown'
    
    def _is_negation(self, concept1: str, concept2: str) -> bool:
        """Check if two concepts are negations of each other."""
        concept1_lower = concept1.lower()
        concept2_lower = concept2.lower()
        
        for pattern1, pattern2 in self.negation_patterns:
            if pattern1 in concept1_lower and pattern2 in concept2_lower:
                return True
            if pattern2 in concept1_lower and pattern1 in concept2_lower:
                return True
        
        return False
    
    def _find_negation_pattern(self, concept1: str, concept2: str) -> Optional[Tuple[str, str]]:
        """Find the negation pattern between two concepts."""
        concept1_lower = concept1.lower()
        concept2_lower = concept2.lower()
        
        for pattern1, pattern2 in self.negation_patterns:
            if pattern1 in concept1_lower and pattern2 in concept2_lower:
                return (pattern1, pattern2)
            if pattern2 in concept1_lower and pattern1 in concept2_lower:
                return (pattern2, pattern1)
        
        return None
    
    def _are_similar_concepts(self, concept1: str, concept2: str, threshold: float = 0.7) -> bool:
        """Check if two concepts are similar (simple word overlap)."""
        words1 = set(concept1.lower().split())
        words2 = set(concept2.lower().split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2) / len(words1 | words2)
        return overlap >= threshold
    
    def _extract_logical_relationships(self, example: Any) -> List[Dict[str, Any]]:
        """Extract logical relationships from example (placeholder for future enhancement)."""
        # TODO: Implement logical relationship extraction
        # For now, return empty list
        return []
    
    def _are_logically_inconsistent(self, rel1: Dict, rel2: Dict) -> bool:
        """Check if two relationships are logically inconsistent (placeholder)."""
        # TODO: Implement logical inconsistency checking
        return False
    
    def _get_highest_severity(self, issues: List) -> Optional[Severity]:
        """Get the highest severity from a list of issues."""
        if not issues:
            return None
        
        severities = []
        for issue in issues:
            if hasattr(issue, 'severity'):
                severities.append(issue.severity)
            elif isinstance(issue, dict):
                sev_str = issue.get('severity')
                if sev_str:
                    try:
                        severities.append(Severity(sev_str))
                    except ValueError:
                        pass
        
        if not severities:
            return None
        
        # Order: CRITICAL > HIGH > MEDIUM > LOW
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
        for sev in severity_order:
            if sev in severities:
                return sev
        
        return severities[0]


# Global instance
_consistency_checker: Optional[ConsistencyChecker] = None


def get_consistency_checker(use_semantic_detection: bool = True) -> ConsistencyChecker:
    """Get or create global consistency checker instance."""
    global _consistency_checker
    if _consistency_checker is None:
        _consistency_checker = ConsistencyChecker(use_semantic_detection=use_semantic_detection)
    return _consistency_checker
