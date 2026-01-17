import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from models.genesis_key_models import GenesisKey
from genesis.code_change_analyzer import ChangeAnalysis
class ChangeIntent(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of change intents."""
    BUG_FIX = "bug_fix"
    FEATURE_ADDITION = "feature_addition"
    REFACTORING = "refactoring"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    SECURITY_FIX = "security_fix"
    DOCUMENTATION = "documentation"
    TEST_ADDITION = "test_addition"
    DEPENDENCY_UPDATE = "dependency_update"
    CODE_CLEANUP = "code_cleanup"
    UNKNOWN = "unknown"


@dataclass
class IntentAnalysis:
    """Analysis of change intent."""
    genesis_key_id: str
    primary_intent: ChangeIntent
    confidence: float  # 0.0-1.0
    secondary_intents: List[ChangeIntent] = field(default_factory=list)
    intent_reasoning: str = ""
    related_changes: List[str] = field(default_factory=list)
    suggested_followups: List[str] = field(default_factory=list)
    pattern_match: Optional[str] = None


class SemanticIntentAnalyzer:
    """
    Analyzes the semantic intent behind code changes.
    
    Understands:
    - Why the change was made
    - What problem it solves
    - Related changes that might be needed
    - Patterns in change behavior
    """
    
    def __init__(self):
        self.intent_history: List[IntentAnalysis] = []
        self.intent_patterns: Dict[str, List[str]] = {}
    
    def analyze_intent(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> IntentAnalysis:
        """
        Analyze the intent behind a code change.
        
        Args:
            genesis_key: Genesis Key representing the change
            change_analysis: Semantic analysis of the change
            
        Returns:
            Intent analysis with reasoning
        """
        # Extract intent from Genesis Key metadata
        why_reason = genesis_key.why_reason or ""
        what_description = genesis_key.what_description or ""
        
        # Analyze intent from multiple sources
        primary_intent = self._determine_primary_intent(
            why_reason,
            what_description,
            change_analysis,
            genesis_key
        )
        
        # Find secondary intents
        secondary_intents = self._find_secondary_intents(
            change_analysis,
            genesis_key
        )
        
        # Generate reasoning
        intent_reasoning = self._generate_reasoning(
            primary_intent,
            why_reason,
            change_analysis
        )
        
        # Find related changes
        related_changes = self._find_related_changes(
            primary_intent,
            genesis_key,
            change_analysis
        )
        
        # Suggest followups
        suggested_followups = self._suggest_followups(
            primary_intent,
            change_analysis
        )
        
        # Check for pattern matches
        pattern_match = self._match_intent_pattern(primary_intent, genesis_key)
        
        analysis = IntentAnalysis(
            genesis_key_id=genesis_key.key_id,
            primary_intent=primary_intent,
            confidence=self._calculate_confidence(primary_intent, why_reason, change_analysis),
            secondary_intents=secondary_intents,
            intent_reasoning=intent_reasoning,
            related_changes=related_changes,
            suggested_followups=suggested_followups,
            pattern_match=pattern_match
        )
        
        self.intent_history.append(analysis)
        
        logger.info(
            f"[IntentAnalyzer] Analyzed {genesis_key.key_id}: "
            f"intent={primary_intent.value}, confidence={analysis.confidence:.2f}"
        )
        
        return analysis
    
    def _determine_primary_intent(
        self,
        why_reason: str,
        what_description: str,
        change_analysis: ChangeAnalysis,
        genesis_key: GenesisKey
    ) -> ChangeIntent:
        """Determine primary intent from multiple signals."""
        
        # Check explicit reason
        reason_lower = why_reason.lower()
        description_lower = what_description.lower()
        
        # Security fixes
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['security', 'vulnerability', 'cve', 'exploit', 'hack']):
            return ChangeIntent.SECURITY_FIX
        
        # Bug fixes
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['fix', 'bug', 'error', 'issue', 'problem', 'broken']):
            return ChangeIntent.BUG_FIX
        
        # Performance
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['performance', 'speed', 'optimize', 'faster', 'slow']):
            return ChangeIntent.PERFORMANCE_IMPROVEMENT
        
        # Features
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['add', 'new', 'feature', 'implement', 'support']):
            return ChangeIntent.FEATURE_ADDITION
        
        # Refactoring
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['refactor', 'restructure', 'reorganize', 'cleanup']):
            return ChangeIntent.REFACTORING
        
        # Tests
        if 'test' in genesis_key.file_path.lower():
            return ChangeIntent.TEST_ADDITION
        
        # Documentation
        if any(keyword in reason_lower or keyword in description_lower 
               for keyword in ['doc', 'comment', 'readme', 'documentation']):
            return ChangeIntent.DOCUMENTATION
        
        # Analyze change patterns
        if change_analysis.risk_score < 0.3 and len(change_analysis.changes) > 5:
            return ChangeIntent.CODE_CLEANUP
        
        # Default
        return ChangeIntent.UNKNOWN
    
    def _find_secondary_intents(
        self,
        change_analysis: ChangeAnalysis,
        genesis_key: GenesisKey
    ) -> List[ChangeIntent]:
        """Find secondary intents."""
        intents = []
        
        # If high risk, might also be security-related
        if change_analysis.risk_score > 0.7:
            intents.append(ChangeIntent.SECURITY_FIX)
        
        # If many changes, might be refactoring
        if len(change_analysis.changes) > 10:
            intents.append(ChangeIntent.REFACTORING)
        
        return intents
    
    def _generate_reasoning(
        self,
        intent: ChangeIntent,
        why_reason: str,
        change_analysis: ChangeAnalysis
    ) -> str:
        """Generate human-readable reasoning."""
        
        reasoning_parts = [f"Primary intent: {intent.value}"]
        
        if why_reason:
            reasoning_parts.append(f"Explicit reason: {why_reason[:100]}")
        
        if change_analysis.risk_score > 0.7:
            reasoning_parts.append("High-risk change detected")
        
        if len(change_analysis.affected_functions) > 5:
            reasoning_parts.append("Multiple functions affected")
        
        return ". ".join(reasoning_parts)
    
    def _find_related_changes(
        self,
        intent: ChangeIntent,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> List[str]:
        """Find related changes that might be needed."""
        related = []
        
        # Look for similar intents in history
        for past_analysis in self.intent_history[-50:]:  # Last 50 changes
            if past_analysis.primary_intent == intent:
                # Check if same file or related
                if past_analysis.genesis_key_id != genesis_key.key_id:
                    related.append(past_analysis.genesis_key_id)
        
        return related[:5]  # Top 5 related
        
    def _suggest_followups(
        self,
        intent: ChangeIntent,
        change_analysis: ChangeAnalysis
    ) -> List[str]:
        """Suggest follow-up actions based on intent."""
        suggestions = []
        
        if intent == ChangeIntent.SECURITY_FIX:
            suggestions.append("Run security scan")
            suggestions.append("Update security documentation")
        
        elif intent == ChangeIntent.BUG_FIX:
            suggestions.append("Add regression test")
            suggestions.append("Check for similar bugs")
        
        elif intent == ChangeIntent.FEATURE_ADDITION:
            suggestions.append("Add integration tests")
            suggestions.append("Update API documentation")
        
        elif intent == ChangeIntent.REFACTORING:
            suggestions.append("Verify all tests pass")
            suggestions.append("Check performance impact")
        
        return suggestions
    
    def _match_intent_pattern(
        self,
        intent: ChangeIntent,
        genesis_key: GenesisKey
    ) -> Optional[str]:
        """Match against known intent patterns."""
        # Simple pattern matching
        # In production, would use ML for pattern recognition
        
        # Check if this intent appears frequently
        recent_intents = [a.primary_intent for a in self.intent_history[-20:]]
        intent_count = recent_intents.count(intent)
        
        if intent_count > 3:
            return f"frequent_{intent.value}"
        
        return None
    
    def _calculate_confidence(
        self,
        intent: ChangeIntent,
        why_reason: str,
        change_analysis: ChangeAnalysis
    ) -> float:
        """Calculate confidence in intent analysis."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if explicit reason provided
        if why_reason and len(why_reason) > 10:
            confidence += 0.2
        
        # Higher confidence if change analysis supports intent
        if change_analysis.risk_score > 0.7 and intent == ChangeIntent.SECURITY_FIX:
            confidence += 0.2
        
        # Lower confidence if intent is UNKNOWN
        if intent == ChangeIntent.UNKNOWN:
            confidence -= 0.3
        
        return min(1.0, max(0.0, confidence))


# Global instance
_analyzer: Optional[SemanticIntentAnalyzer] = None


def get_semantic_intent_analyzer() -> SemanticIntentAnalyzer:
    """Get or create global semantic intent analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SemanticIntentAnalyzer()
    return _analyzer
