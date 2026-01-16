"""
Automated Validation Pipeline - Layer 1 Knowledge Validation

This module provides automated validation for Layer 1 knowledge:
- Validation rule system
- Automated validation cycles
- Auto-correction of low-severity issues
- Validation reporting

Maintains 100% determinism while automating validation processes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from sqlalchemy.orm import Session
from cognitive.learning_memory import LearningExample
from cognitive.enhanced_trust_scorer import TrustScoreResult
from cognitive.enhanced_consistency_checker import ConsistencyResult

logger = logging.getLogger(__name__)


class ValidationRuleType(Enum):
    """Types of validation rules."""
    TRUST_SCORE = "trust_score"
    CONSISTENCY = "consistency"
    TEMPORAL = "temporal"
    SOURCE = "source"
    COMPLETENESS = "completeness"
    LOGICAL = "logical"


class IssueSeverity(Enum):
    """Severity levels for validation issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationRuleResult:
    """Result of a validation rule check."""
    passed: bool
    issue_type: Optional[str] = None
    severity: Optional[IssueSeverity] = None
    description: Optional[str] = None
    suggested_correction: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationIssue:
    """Represents a validation issue found."""
    example_id: int
    rule_name: str
    issue_type: str
    severity: IssueSeverity
    description: str
    suggested_correction: Optional[str] = None
    detected_at: datetime = None
    
    def __post_init__(self):
        """Set default timestamp."""
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'example_id': self.example_id,
            'rule_name': self.rule_name,
            'issue_type': self.issue_type,
            'severity': self.severity.value,
            'description': self.description,
            'suggested_correction': self.suggested_correction,
            'detected_at': self.detected_at.isoformat()
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    timestamp: datetime
    validations_run: int
    issues_found: List[ValidationIssue]
    corrections_applied: int
    rules_executed: List[str]
    processing_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'validations_run': self.validations_run,
            'issues_found': [issue.to_dict() for issue in self.issues_found],
            'corrections_applied': self.corrections_applied,
            'rules_executed': self.rules_executed,
            'processing_time_seconds': self.processing_time_seconds,
            'issues_by_severity': self._count_by_severity()
        }
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity."""
        counts = defaultdict(int)
        for issue in self.issues_found:
            counts[issue.severity.value] += 1
        return dict(counts)


class ValidationRule:
    """
    Base class for validation rules.
    
    Each rule validates a specific aspect of learning examples.
    """
    
    def __init__(
        self,
        name: str,
        rule_type: ValidationRuleType,
        description: str,
        enabled: bool = True
    ):
        """
        Initialize validation rule.
        
        Args:
            name: Rule name
            rule_type: Type of rule
            description: Rule description
            enabled: Whether rule is enabled
        """
        self.name = name
        self.rule_type = rule_type
        self.description = description
        self.enabled = enabled
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """
        Validate a learning example.
        
        Args:
            example: Learning example to validate
            session: Database session
            
        Returns:
            ValidationRuleResult
        """
        raise NotImplementedError("Subclasses must implement validate()")


class TrustScoreValidationRule(ValidationRule):
    """Validates trust scores are within acceptable ranges."""
    
    def __init__(self):
        super().__init__(
            name="trust_score_validation",
            rule_type=ValidationRuleType.TRUST_SCORE,
            description="Validates trust scores are reasonable and consistent"
        )
        self.min_trust = 0.0
        self.max_trust = 1.0
        self.suspicious_low = 0.2
        self.suspicious_high = 0.98
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """Validate trust score."""
        if not hasattr(example, 'trust_score'):
            return ValidationRuleResult(
                passed=False,
                issue_type="missing_trust_score",
                severity=IssueSeverity.HIGH,
                description="Learning example missing trust score",
                suggested_correction="Calculate and assign trust score"
            )
        
        trust_score = example.trust_score
        
        # Check bounds
        if trust_score < self.min_trust or trust_score > self.max_trust:
            return ValidationRuleResult(
                passed=False,
                issue_type="trust_score_out_of_bounds",
                severity=IssueSeverity.CRITICAL,
                description=f"Trust score {trust_score} is outside valid range [0, 1]",
                suggested_correction="Recalculate trust score"
            )
        
        # Check for suspicious values
        if trust_score < self.suspicious_low:
            return ValidationRuleResult(
                passed=False,
                issue_type="trust_score_suspiciously_low",
                severity=IssueSeverity.MEDIUM,
                description=f"Trust score {trust_score} is suspiciously low",
                suggested_correction="Review source and validation history"
            )
        
        if trust_score > self.suspicious_high:
            return ValidationRuleResult(
                passed=False,
                issue_type="trust_score_suspiciously_high",
                severity=IssueSeverity.LOW,
                description=f"Trust score {trust_score} is suspiciously high",
                suggested_correction="Verify trust score calculation"
            )
        
        return ValidationRuleResult(passed=True)


class ConsistencyValidationRule(ValidationRule):
    """Validates consistency with existing knowledge."""
    
    def __init__(self):
        super().__init__(
            name="consistency_validation",
            rule_type=ValidationRuleType.CONSISTENCY,
            description="Validates consistency with existing knowledge"
        )
        self.min_consistency = 0.3
        self.critical_consistency = 0.2
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """Validate consistency."""
        if not hasattr(example, 'consistency_score'):
            return ValidationRuleResult(
                passed=False,
                issue_type="missing_consistency_score",
                severity=IssueSeverity.MEDIUM,
                description="Learning example missing consistency score",
                suggested_correction="Calculate consistency score"
            )
        
        consistency_score = example.consistency_score
        
        if consistency_score < self.critical_consistency:
            return ValidationRuleResult(
                passed=False,
                issue_type="critical_consistency_issue",
                severity=IssueSeverity.CRITICAL,
                description=f"Consistency score {consistency_score} is critically low",
                suggested_correction="Review for contradictions and conflicts"
            )
        
        if consistency_score < self.min_consistency:
            return ValidationRuleResult(
                passed=False,
                issue_type="low_consistency",
                severity=IssueSeverity.MEDIUM,
                description=f"Consistency score {consistency_score} is below threshold",
                suggested_correction="Check for conflicts with existing knowledge"
            )
        
        return ValidationRuleResult(passed=True)


class TemporalValidationRule(ValidationRule):
    """Validates temporal aspects (age, recency)."""
    
    def __init__(self):
        super().__init__(
            name="temporal_validation",
            rule_type=ValidationRuleType.TEMPORAL,
            description="Validates temporal aspects of learning examples"
        )
        self.max_age_days = 365  # Flag examples older than 1 year
        self.stale_age_days = 730  # Critical if older than 2 years
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """Validate temporal aspects."""
        if not hasattr(example, 'created_at'):
            return ValidationRuleResult(
                passed=False,
                issue_type="missing_timestamp",
                severity=IssueSeverity.LOW,
                description="Learning example missing creation timestamp",
                suggested_correction="Assign creation timestamp"
            )
        
        age_days = (datetime.utcnow() - example.created_at).days
        
        if age_days > self.stale_age_days:
            return ValidationRuleResult(
                passed=False,
                issue_type="stale_knowledge",
                severity=IssueSeverity.HIGH,
                description=f"Knowledge is {age_days} days old (stale)",
                suggested_correction="Review and update or mark as deprecated"
            )
        
        if age_days > self.max_age_days:
            return ValidationRuleResult(
                passed=False,
                issue_type="old_knowledge",
                severity=IssueSeverity.MEDIUM,
                description=f"Knowledge is {age_days} days old",
                suggested_correction="Consider reviewing for updates"
            )
        
        return ValidationRuleResult(passed=True)


class SourceValidationRule(ValidationRule):
    """Validates source information."""
    
    def __init__(self):
        super().__init__(
            name="source_validation",
            rule_type=ValidationRuleType.SOURCE,
            description="Validates source information is present and valid"
        )
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """Validate source."""
        if not hasattr(example, 'source') or not example.source:
            return ValidationRuleResult(
                passed=False,
                issue_type="missing_source",
                severity=IssueSeverity.MEDIUM,
                description="Learning example missing source information",
                suggested_correction="Assign source"
            )
        
        # Check for unknown sources
        if str(example.source).lower() in ['unknown', 'none', '']:
            return ValidationRuleResult(
                passed=False,
                issue_type="unknown_source",
                severity=IssueSeverity.LOW,
                description="Source is marked as unknown",
                suggested_correction="Identify and assign proper source"
            )
        
        return ValidationRuleResult(passed=True)


class CompletenessValidationRule(ValidationRule):
    """Validates example completeness."""
    
    def __init__(self):
        super().__init__(
            name="completeness_validation",
            rule_type=ValidationRuleType.COMPLETENESS,
            description="Validates learning example has required fields"
        )
    
    def validate(
        self,
        example: LearningExample,
        session: Session
    ) -> ValidationRuleResult:
        """Validate completeness."""
        issues = []
        
        # Check required fields
        if not hasattr(example, 'input_context') or not example.input_context:
            issues.append("Missing input_context")
        
        if not hasattr(example, 'expected_output') or not example.expected_output:
            issues.append("Missing expected_output")
        
        if not hasattr(example, 'example_type') or not example.example_type:
            issues.append("Missing example_type")
        
        if issues:
            return ValidationRuleResult(
                passed=False,
                issue_type="incomplete_example",
                severity=IssueSeverity.MEDIUM,
                description=f"Missing required fields: {', '.join(issues)}",
                suggested_correction="Complete missing fields"
            )
        
        return ValidationRuleResult(passed=True)


class AutomatedValidationPipeline:
    """
    Automated validation pipeline for Layer 1 knowledge.
    
    Runs validation cycles, detects issues, and optionally auto-corrects.
    """
    
    def __init__(self, session: Session):
        """
        Initialize validation pipeline.
        
        Args:
            session: Database session
        """
        self.session = session
        
        # Default validation rules
        self.validation_rules: List[ValidationRule] = [
            TrustScoreValidationRule(),
            ConsistencyValidationRule(),
            TemporalValidationRule(),
            SourceValidationRule(),
            CompletenessValidationRule()
        ]
    
    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule."""
        self.validation_rules.append(rule)
    
    def run_validation_cycle(
        self,
        limit: int = 1000,
        auto_correct: bool = False,
        min_severity_for_auto_correct: IssueSeverity = IssueSeverity.LOW
    ) -> ValidationReport:
        """
        Run automated validation cycle.
        
        Args:
            limit: Maximum number of examples to validate
            auto_correct: If True, auto-correct low-severity issues
            min_severity_for_auto_correct: Minimum severity for auto-correction
            
        Returns:
            ValidationReport with all findings
        """
        import time
        start_time = time.time()
        
        # Get examples to validate
        examples = self._get_examples_for_validation(limit)
        
        issues_found = []
        corrections_applied = 0
        rules_executed = [rule.name for rule in self.validation_rules if rule.enabled]
        
        # Run validation rules
        for example in examples:
            for rule in self.validation_rules:
                if not rule.enabled:
                    continue
                
                try:
                    result = rule.validate(example, self.session)
                    
                    if not result.passed:
                        issue = ValidationIssue(
                            example_id=example.id,
                            rule_name=rule.name,
                            issue_type=result.issue_type or "unknown",
                            severity=result.severity or IssueSeverity.MEDIUM,
                            description=result.description or "Validation failed",
                            suggested_correction=result.suggested_correction
                        )
                        issues_found.append(issue)
                        
                        # Auto-correct if enabled
                        if auto_correct and result.severity:
                            if self._should_auto_correct(result.severity, min_severity_for_auto_correct):
                                if self._apply_correction(issue, example, result):
                                    corrections_applied += 1
                
                except Exception as e:
                    logger.error(f"Error running rule {rule.name} on example {example.id}: {e}")
        
        processing_time = time.time() - start_time
        
        # Commit corrections
        if corrections_applied > 0:
            self.session.commit()
        
        return ValidationReport(
            timestamp=datetime.utcnow(),
            validations_run=len(examples),
            issues_found=issues_found,
            corrections_applied=corrections_applied,
            rules_executed=rules_executed,
            processing_time_seconds=processing_time
        )
    
    def _get_examples_for_validation(
        self,
        limit: int
    ) -> List[LearningExample]:
        """
        Get examples that need validation.
        
        Priority:
        1. Low trust scores
        2. Old examples (not validated recently)
        3. High uncertainty
        4. Missing required fields
        """
        from sqlalchemy import or_
        
        # Priority examples
        priority_examples = self.session.query(LearningExample).filter(
            or_(
                LearningExample.trust_score < 0.6,
                LearningExample.consistency_score < 0.5,
                LearningExample.created_at < datetime.utcnow() - timedelta(days=90)
            )
        ).limit(limit // 2).all()
        
        # Random sample for general validation
        remaining = limit - len(priority_examples)
        if remaining > 0:
            general_examples = self.session.query(LearningExample).filter(
                LearningExample.id.notin_([ex.id for ex in priority_examples])
            ).limit(remaining).all()
        else:
            general_examples = []
        
        return priority_examples + general_examples
    
    def _should_auto_correct(
        self,
        severity: IssueSeverity,
        min_severity: IssueSeverity
    ) -> bool:
        """Determine if issue should be auto-corrected."""
        severity_order = [
            IssueSeverity.LOW,
            IssueSeverity.MEDIUM,
            IssueSeverity.HIGH,
            IssueSeverity.CRITICAL
        ]
        
        return severity_order.index(severity) <= severity_order.index(min_severity)
    
    def _apply_correction(
        self,
        issue: ValidationIssue,
        example: LearningExample,
        result: ValidationRuleResult
    ) -> bool:
        """
        Apply auto-correction for an issue.
        
        Returns:
            True if correction was applied, False otherwise
        """
        try:
            if issue.issue_type == "missing_trust_score":
                # Calculate trust score
                from cognitive.enhanced_trust_scorer import get_adaptive_trust_scorer
                scorer = get_adaptive_trust_scorer()
                
                validation_history = {
                    'validated': example.times_validated if hasattr(example, 'times_validated') else 0,
                    'invalidated': example.times_invalidated if hasattr(example, 'times_invalidated') else 0
                }
                
                age_days = (datetime.utcnow() - example.created_at).days if hasattr(example, 'created_at') else 0
                
                trust_result = scorer.calculate_trust_score(
                    source=example.source if hasattr(example, 'source') else 'unknown',
                    outcome_quality=example.outcome_quality if hasattr(example, 'outcome_quality') else 0.5,
                    consistency_score=example.consistency_score if hasattr(example, 'consistency_score') else 0.5,
                    validation_history=validation_history,
                    age_days=age_days
                )
                
                example.trust_score = trust_result.trust_score
                return True
            
            elif issue.issue_type == "missing_consistency_score":
                # Calculate consistency score
                from cognitive.enhanced_consistency_checker import get_consistency_checker
                checker = get_consistency_checker()
                
                existing_examples = self.session.query(LearningExample).filter(
                    LearningExample.id != example.id
                ).limit(100).all()
                
                consistency_result = checker.check_consistency(
                    new_example=example,
                    existing_examples=existing_examples
                )
                
                example.consistency_score = consistency_result.consistency_score
                return True
            
            elif issue.issue_type == "missing_timestamp":
                # Assign current timestamp
                example.created_at = datetime.utcnow()
                return True
            
            elif issue.issue_type == "unknown_source":
                # Try to infer source from context
                if hasattr(example, 'input_context') and isinstance(example.input_context, dict):
                    inferred_source = example.input_context.get('source', 'inferred')
                    example.source = inferred_source
                    return True
            
            # Other corrections would go here
            
            return False
        
        except Exception as e:
            logger.error(f"Error applying correction for {issue.issue_id}: {e}")
            return False
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation pipeline status."""
        total_examples = self.session.query(LearningExample).count()
        
        # Count examples by trust score ranges
        low_trust = self.session.query(LearningExample).filter(
            LearningExample.trust_score < 0.6
        ).count()
        
        medium_trust = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.6,
            LearningExample.trust_score < 0.8
        ).count()
        
        high_trust = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.8
        ).count()
        
        return {
            'total_examples': total_examples,
            'trust_score_distribution': {
                'low': low_trust,
                'medium': medium_trust,
                'high': high_trust
            },
            'validation_rules': len(self.validation_rules),
            'enabled_rules': len([r for r in self.validation_rules if r.enabled])
        }
