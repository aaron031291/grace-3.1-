"""
Rule Storage - Connects Neural-to-Symbolic Rules to Learning Memory

Stores symbolic rules generated from neural patterns into the learning memory system,
making them available for symbolic reasoning.

Classes:
- `RuleStorage`

Key Methods:
- `store_rule()`
- `store_rules()`
- `get_rule_pattern()`
- `get_rules_by_type()`
- `get_rule_storage()`
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ml_intelligence.neural_to_symbolic_rule_generator import SymbolicRule
from cognitive.learning_memory import LearningMemoryManager, LearningPattern

logger = logging.getLogger(__name__)


class RuleStorage:
    """
    Stores symbolic rules in learning memory.
    
    Converts SymbolicRule objects into LearningPattern instances
    that can be used for symbolic reasoning.
    """
    
    def __init__(
        self,
        learning_memory: LearningMemoryManager
    ):
        """
        Initialize rule storage.
        
        Args:
            learning_memory: LearningMemoryManager instance
        """
        self.learning_memory = learning_memory
        self.session = learning_memory.session
        
        logger.info("[RULE-STORAGE] Initialized")
    
    def store_rule(
        self,
        rule: SymbolicRule,
        pattern_type: str = "neural_symbolic",
    ) -> Optional[LearningPattern]:
        """
        Store a symbolic rule as a LearningPattern.
        
        Args:
            rule: SymbolicRule to store
            pattern_type: Type of pattern (default: "neural_symbolic")
            
        Returns:
            Created LearningPattern or None if storage fails
        """
        try:
            # Check if pattern with this ID already exists
            existing = self.session.query(LearningPattern).filter(
                LearningPattern.pattern_name == f"rule_{rule.rule_id[:8]}"
            ).first()
            
            if existing:
                logger.debug(f"Rule {rule.rule_id[:8]} already exists, updating")
                # Update existing pattern
                existing.preconditions = rule.premise
                existing.actions = {"conclusion": rule.conclusion}  # Store conclusion as action
                existing.expected_outcomes = rule.conclusion
                existing.trust_score = rule.trust_score
                existing.sample_size = rule.support_count
                existing.times_applied = rule.validation_count
                existing.times_succeeded = rule.validation_count  # Simplified
                
                self.session.commit()
                return existing
            
            # Create new LearningPattern from SymbolicRule
            pattern = LearningPattern(
                pattern_name=f"rule_{rule.rule_id[:8]}",
                pattern_type=pattern_type,
                preconditions=rule.premise,
                actions={"conclusion": rule.conclusion},  # Store conclusion as action
                expected_outcomes=rule.conclusion,
                trust_score=rule.trust_score,
                success_rate=rule.confidence,
                sample_size=rule.support_count,
                supporting_examples=[],  # Could link to learning examples
                times_applied=rule.validation_count,
                times_succeeded=rule.validation_count,  # Simplified
                times_failed=rule.invalidation_count,
                linked_procedures=None,
            )
            
            self.session.add(pattern)
            self.session.commit()
            
            logger.info(f"[RULE-STORAGE] Stored rule {rule.rule_id[:8]} as pattern {pattern.pattern_name}")
            return pattern
            
        except Exception as e:
            logger.error(f"[RULE-STORAGE] Failed to store rule {rule.rule_id[:8]}: {e}")
            self.session.rollback()
            return None
    
    def store_rules(
        self,
        rules: List[SymbolicRule],
        pattern_type: str = "neural_symbolic",
    ) -> List[LearningPattern]:
        """
        Store multiple symbolic rules.
        
        Args:
            rules: List of SymbolicRule objects
            pattern_type: Type of patterns
            
        Returns:
            List of created LearningPattern instances
        """
        stored_patterns = []
        
        for rule in rules:
            pattern = self.store_rule(rule, pattern_type=pattern_type)
            if pattern:
                stored_patterns.append(pattern)
        
        logger.info(f"[RULE-STORAGE] Stored {len(stored_patterns)}/{len(rules)} rules")
        return stored_patterns
    
    def get_rule_pattern(
        self,
        rule_id: str
    ) -> Optional[LearningPattern]:
        """
        Get a LearningPattern by rule ID.
        
        Args:
            rule_id: SymbolicRule ID
            
        Returns:
            LearningPattern or None if not found
        """
        pattern_name = f"rule_{rule_id[:8]}"
        return self.session.query(LearningPattern).filter(
            LearningPattern.pattern_name == pattern_name
        ).first()
    
    def get_rules_by_type(
        self,
        pattern_type: str = "neural_symbolic",
        min_trust: float = 0.5
    ) -> List[LearningPattern]:
        """
        Get all rules of a specific type above minimum trust.
        
        Args:
            pattern_type: Type of patterns
            min_trust: Minimum trust score
            
        Returns:
            List of LearningPattern instances
        """
        return self.session.query(LearningPattern).filter(
            LearningPattern.pattern_type == pattern_type,
            LearningPattern.trust_score >= min_trust
        ).all()


def get_rule_storage(
    learning_memory: LearningMemoryManager
) -> RuleStorage:
    """
    Get rule storage instance.
    
    Args:
        learning_memory: LearningMemoryManager instance
        
    Returns:
        RuleStorage instance
    """
    return RuleStorage(learning_memory)
