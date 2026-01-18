import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from cognitive.gap_detector import get_gap_detector, KnowledgeGap
from cognitive.reverse_knn_searcher import get_reverse_knn_searcher, SimilarProblem
from cognitive.healing_knowledge_base import get_healing_knowledge_base, IssueType, FixPattern
import re
logger = logging.getLogger(__name__)

class GapFiller:
    """
    Fills knowledge gaps by learning from similar problems.
    
    Process:
    1. Detect gap (error we can't fix)
    2. Use reverse KNN to find K similar problems
    3. Extract solutions from neighbors
    4. Create fix pattern from solutions
    5. Add to knowledge base
    """
    
    def __init__(self, github_token: Optional[str] = None):
        self.gap_detector = get_gap_detector()
        self.knn_searcher = get_reverse_knn_searcher(github_token)
        self.knowledge_base = get_healing_knowledge_base()
        self.filled_gaps: List[Dict] = []
    
    def fill_gap(
        self,
        error_message: str,
        attempted_fixes: List[str] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Fill a knowledge gap by learning from similar problems.
        
        Args:
            error_message: Error that represents a gap
            attempted_fixes: Fixes that were tried and failed
            k: Number of similar problems to find (K in KNN)
        
        Returns:
            Result with new fix pattern if successful
        """
        logger.info(f"[GAP-FILLER] Attempting to fill gap: {error_message[:100]}")
        
        # Step 1: Detect gap
        gap = self.gap_detector.detect_gap(error_message, attempted_fixes)
        if gap is None:
            return {
                "success": False,
                "reason": "Not a knowledge gap - can be handled by existing patterns"
            }
        
        # Step 2: Find similar problems using reverse KNN
        logger.info(f"[GAP-FILLER] Finding {k} similar problems...")
        similar_problems = self.knn_searcher.find_similar_problems(gap, k=k)
        
        if not similar_problems:
            return {
                "success": False,
                "reason": "No similar problems found",
                "gap": gap.error_message
            }
        
        logger.info(f"[GAP-FILLER] Found {len(similar_problems)} similar problems")
        
        # Step 3: Extract common solution pattern
        solution_pattern = self._extract_common_solution(similar_problems)
        
        if not solution_pattern:
            return {
                "success": False,
                "reason": "Could not extract solution pattern",
                "similar_problems": len(similar_problems)
            }
        
        # Step 4: Create fix pattern
        fix_pattern = self._create_fix_pattern(gap, similar_problems, solution_pattern)
        
        if not fix_pattern:
            return {
                "success": False,
                "reason": "Could not create fix pattern"
            }
        
        # Step 5: Add to knowledge base (would need to modify knowledge base to support dynamic addition)
        # For now, return the pattern to be added manually
        result = {
            "success": True,
            "gap": gap.error_message,
            "similar_problems_found": len(similar_problems),
            "fix_pattern": fix_pattern,
            "confidence": self._calculate_confidence(similar_problems),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.filled_gaps.append(result)
        logger.info(f"[GAP-FILLER] Successfully created fix pattern for gap")
        
        return result
    
    def _extract_common_solution(self, similar_problems: List[SimilarProblem]) -> Optional[str]:
        """Extract common solution pattern from similar problems."""
        if not similar_problems:
            return None
        
        # Group solutions by similarity
        solutions = [p.solution for p in similar_problems if p.solution]
        
        if not solutions:
            return None
        
        # Find most common solution (or best solution if only one)
        if len(solutions) == 1:
            return solutions[0]
        
        # For multiple solutions, find common patterns
        # Simple approach: return highest upvoted/accepted solution
        best_problem = max(
            similar_problems,
            key=lambda p: (p.is_accepted, p.upvotes, p.similarity_score)
        )
        
        return best_problem.solution
    
    def _create_fix_pattern(
        self,
        gap: KnowledgeGap,
        similar_problems: List[SimilarProblem],
        solution: str
    ) -> Optional[Dict]:
        """Create a fix pattern from gap and solutions."""
        # Categorize error type
        error_type = self._categorize_error_type(gap.error_message)
        
        # Create pattern regex
        pattern = self._create_pattern_regex(gap.error_message)
        
        # Create fix template from solution
        fix_template = self._create_fix_template(solution, gap.error_message)
        
        # Calculate confidence based on:
        # - Number of similar problems found
        # - Quality of solutions (upvotes, accepted)
        # - Similarity scores
        confidence = self._calculate_confidence(similar_problems)
        
        return {
            "issue_type": error_type,
            "pattern": pattern,
            "fix_template": fix_template,
            "confidence": confidence,
            "description": f"Learned from {len(similar_problems)} similar problems",
            "examples": [p.error_message for p in similar_problems[:3]],
            "sources": list(set(p.source for p in similar_problems))
        }
    
    def _categorize_error_type(self, error_message: str) -> str:
        """Categorize error type from message."""
        error_lower = error_message.lower()
        
        # Try to match existing issue types
        try:
            issue_info = self.knowledge_base.identify_issue_type(error_message)
            if issue_info:
                issue_type, _ = issue_info
                return issue_type.value
        except:
            pass
        
        # Fallback categorization
        if "import" in error_lower and "circular" in error_lower:
            return "circular_import"
        elif "no module named" in error_lower or "modulenotfounderror" in error_lower:
            return "missing_dependency"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "connection_timeout"
        elif "table" in error_lower and "already defined" in error_lower:
            return "sqlalchemy_table_redefinition"
        elif "connection" in error_lower and "failed" in error_lower:
            return "database_connection"
        else:
            # Extract error type from message
            import re
            error_type_match = re.search(r'(\w+Error|\w+Exception)', error_message)
            if error_type_match:
                return error_type_match.group(1).lower().replace("error", "").replace("exception", "")
            return "unknown"
    
    def _create_pattern_regex(self, error_message: str) -> str:
        """Create regex pattern from error message."""
        # Extract key parts
        error_type_match = re.search(r'(\w+Error|\w+Exception)', error_message)
        if error_type_match:
            error_type = error_type_match.group(1)
            return rf"{error_type}.*"
        
        # Fallback: use first few words
        words = error_message.split()[:5]
        pattern = ".*".join(re.escape(w) for w in words)
        return pattern
    
    def _create_fix_template(self, solution: str, error_message: str) -> str:
        """Create fix template from solution code."""
        # If solution is code, format as template
        if "def " in solution or "import " in solution or "=" in solution:
            return f"# Fix learned from similar problems:\n{solution}\n\n# Original error: {error_message[:100]}"
        else:
            return f"# Fix: {solution}\n\n# Original error: {error_message[:100]}"
    
    def _calculate_confidence(self, similar_problems: List[SimilarProblem]) -> float:
        """Calculate confidence based on solution quality."""
        if not similar_problems:
            return 0.0
        
        # Base confidence from number of similar problems
        base_confidence = min(0.7, 0.3 + (len(similar_problems) * 0.1))
        
        # Boost for accepted answers
        accepted_count = sum(1 for p in similar_problems if p.is_accepted)
        if accepted_count > 0:
            base_confidence += 0.1
        
        # Boost for high upvotes
        avg_upvotes = sum(p.upvotes for p in similar_problems) / len(similar_problems)
        if avg_upvotes > 10:
            base_confidence += 0.1
        
        # Boost for high similarity scores
        avg_similarity = sum(p.similarity_score for p in similar_problems) / len(similar_problems)
        base_confidence += avg_similarity * 0.1
        
        return min(1.0, base_confidence)
    
    def get_filled_gaps(self) -> List[Dict]:
        """Get all gaps that were filled."""
        return self.filled_gaps


import re  # Add import at top

# Global instance
_gap_filler: Optional[GapFiller] = None


def get_gap_filler(github_token: Optional[str] = None) -> GapFiller:
    """Get global gap filler instance."""
    global _gap_filler
    if _gap_filler is None:
        _gap_filler = GapFiller(github_token=github_token)
    return _gap_filler
