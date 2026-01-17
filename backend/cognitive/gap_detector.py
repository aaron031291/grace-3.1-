import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType
class KnowledgeGap:
    logger = logging.getLogger(__name__)
    """Represents a gap in Grace's knowledge."""
    error_message: str
    error_type: Optional[str] = None
    confidence: float = 0.0  # How confident we are this is a gap
    attempted_fixes: List[str] = None
    failure_reason: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.attempted_fixes is None:
            self.attempted_fixes = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class GapDetector:
    """
    Detects knowledge gaps by identifying errors Grace can't fix.
    
    Uses reverse KNN to find similar problems and solutions.
    """
    
    def __init__(self):
        self.knowledge_base = get_healing_knowledge_base()
        self.detected_gaps: List[KnowledgeGap] = []
    
    def detect_gap(self, error_message: str, attempted_fixes: List[str] = None) -> Optional[KnowledgeGap]:
        """
        Detect if this error represents a knowledge gap.
        
        A gap exists if:
        1. Error can't be categorized by knowledge base
        2. Fix was attempted but failed
        3. No fix pattern matches with high confidence
        """
        # Try to identify issue type
        issue_info = self.knowledge_base.identify_issue_type(error_message)
        
        if issue_info is None:
            # Can't identify - this is a gap
            gap = KnowledgeGap(
                error_message=error_message,
                confidence=0.9,  # High confidence it's a gap
                attempted_fixes=attempted_fixes or [],
                failure_reason="No matching fix pattern found"
            )
            self.detected_gaps.append(gap)
            logger.info(f"[GAP-DETECTOR] Knowledge gap detected: {error_message[:100]}")
            return gap
        
        issue_type, pattern = issue_info
        
        # Check if fix was attempted but failed
        if attempted_fixes and len(attempted_fixes) > 0:
            # Fix was attempted but error persists - gap in fix quality
            gap = KnowledgeGap(
                error_message=error_message,
                error_type=issue_type.value,
                confidence=0.7,  # Medium confidence - pattern exists but fix doesn't work
                attempted_fixes=attempted_fixes,
                failure_reason=f"Fix pattern exists but failed: {pattern.description}"
            )
            self.detected_gaps.append(gap)
            logger.info(f"[GAP-DETECTOR] Fix quality gap: {error_message[:100]}")
            return gap
        
        # Low confidence pattern match - might be a gap
        if pattern.confidence < 0.6:
            gap = KnowledgeGap(
                error_message=error_message,
                error_type=issue_type.value,
                confidence=0.5,  # Low confidence gap
                attempted_fixes=attempted_fixes or [],
                failure_reason=f"Low confidence pattern match: {pattern.confidence}"
            )
            self.detected_gaps.append(gap)
            return gap
        
        # No gap - we can handle this
        return None
    
    def get_all_gaps(self) -> List[KnowledgeGap]:
        """Get all detected knowledge gaps."""
        return self.detected_gaps
    
    def get_gaps_by_type(self, error_type: str) -> List[KnowledgeGap]:
        """Get gaps for a specific error type."""
        return [gap for gap in self.detected_gaps if gap.error_type == error_type]


# Global instance
_gap_detector: Optional[GapDetector] = None


def get_gap_detector() -> GapDetector:
    """Get global gap detector instance."""
    global _gap_detector
    if _gap_detector is None:
        _gap_detector = GapDetector()
    return _gap_detector
