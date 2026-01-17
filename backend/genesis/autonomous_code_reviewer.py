import ast
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from models.genesis_key_models import GenesisKey
from genesis.code_change_analyzer import ChangeAnalysis, CodeChange
class ReviewSeverity(str, Enum):
    logger = logging.getLogger(__name__)
    """Severity levels for code review issues."""
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeReviewIssue:
    """A code review issue or suggestion."""
    severity: ReviewSeverity
    category: str  # security, performance, maintainability, etc.
    message: str
    file_path: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    code_example: Optional[str] = None
    confidence: float = 0.5  # 0.0-1.0
    related_functions: List[str] = field(default_factory=list)


@dataclass
class CodeReview:
    """Complete code review result."""
    genesis_key_id: str
    file_path: str
    issues: List[CodeReviewIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    overall_score: float = 1.0  # 0.0-1.0
    review_confidence: float = 0.5
    estimated_improvement_time: float = 0.0  # minutes


class AutonomousCodeReviewer:
    """
    Reviews code changes autonomously.
    
    Analyzes:
    - Security issues
    - Performance problems
    - Maintainability concerns
    - Best practices
    - Pattern violations
    """
    
    def __init__(self):
        self.review_history: List[CodeReview] = []
        self.pattern_knowledge: Dict[str, List[str]] = {}
    
    def review_code_change(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> CodeReview:
        """
        Review a code change autonomously.
        
        Args:
            genesis_key: Genesis Key representing the change
            change_analysis: Semantic analysis of the change
            
        Returns:
            Complete code review with issues and suggestions
        """
        issues = []
        
        # Review each change
        for change in change_analysis.changes:
            change_issues = self._review_change(change, genesis_key, change_analysis)
            issues.extend(change_issues)
        
        # Overall code review
        overall_issues = self._review_overall(genesis_key, change_analysis)
        issues.extend(overall_issues)
        
        # Calculate overall score
        overall_score = self._calculate_score(issues)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(issues, change_analysis)
        
        review = CodeReview(
            genesis_key_id=genesis_key.key_id,
            file_path=genesis_key.file_path,
            issues=issues,
            suggestions=suggestions,
            overall_score=overall_score,
            review_confidence=0.7,  # Base confidence
            estimated_improvement_time=len(issues) * 2.0  # 2 min per issue
        )
        
        self.review_history.append(review)
        
        logger.info(
            f"[CodeReviewer] Reviewed {genesis_key.key_id}: "
            f"{len(issues)} issues, score={overall_score:.2f}"
        )
        
        return review
    
    def _review_change(
        self,
        change: CodeChange,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> List[CodeReviewIssue]:
        """Review a specific code change."""
        issues = []
        
        # Review deletions
        if change.change_type.value.endswith('_deleted'):
            issues.extend(self._review_deletion(change, genesis_key))
        
        # Review additions
        elif change.change_type.value.endswith('_added'):
            issues.extend(self._review_addition(change, genesis_key))
        
        # Review modifications
        elif change.change_type.value.endswith('_modified'):
            issues.extend(self._review_modification(change, genesis_key))
        
        # Review imports
        if change.change_type.value.startswith('import_'):
            issues.extend(self._review_imports(change, genesis_key))
        
        return issues
    
    def _review_deletion(
        self,
        change: CodeChange,
        genesis_key: GenesisKey
    ) -> List[CodeReviewIssue]:
        """Review code deletions."""
        issues = []
        
        if change.entity:
            # Check if deleted function/class is used elsewhere
            if change.entity.dependents:
                issues.append(CodeReviewIssue(
                    severity=ReviewSeverity.ERROR,
                    category="breaking_change",
                    message=f"Deleted {change.entity.entity_type} '{change.entity.name}' is used by {len(change.entity.dependents)} other entities",
                    file_path=genesis_key.file_path,
                    line_number=change.line_numbers[0],
                    suggestion="Check all usages before deletion or provide migration path",
                    confidence=0.9
                ))
        
        return issues
    
    def _review_addition(
        self,
        change: CodeChange,
        genesis_key: GenesisKey
    ) -> List[CodeReviewIssue]:
        """Review code additions."""
        issues = []
        
        if change.after_code:
            # Parse and analyze new code
            try:
                tree = ast.parse(change.after_code)
                issues.extend(self._analyze_code_quality(tree, genesis_key, change))
            except SyntaxError:
                pass
        
        return issues
    
    def _review_modification(
        self,
        change: CodeChange,
        genesis_key: GenesisKey
    ) -> List[CodeReviewIssue]:
        """Review code modifications."""
        issues = []
        
        # Check for breaking changes
        if change.before_code and change.after_code:
            # Simple heuristic: if function signature changed significantly
            before_tree = ast.parse(change.before_code) if change.before_code else None
            after_tree = ast.parse(change.after_code) if change.after_code else None
            
            if before_tree and after_tree:
                issues.extend(self._check_breaking_changes(before_tree, after_tree, genesis_key, change))
        
        return issues
    
    def _analyze_code_quality(
        self,
        tree: ast.AST,
        genesis_key: GenesisKey,
        change: CodeChange
    ) -> List[CodeReviewIssue]:
        """Analyze code quality issues."""
        issues = []
        visitor = CodeQualityVisitor(genesis_key.file_path)
        visitor.visit(tree)
        
        # Check for common issues
        if visitor.has_bare_except:
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.WARNING,
                category="error_handling",
                message="Bare except clause found - catch specific exceptions",
                file_path=genesis_key.file_path,
                line_number=change.line_numbers[0],
                suggestion="Use 'except SpecificError:' instead of 'except:'",
                code_example="except ValueError:\n    # handle error",
                confidence=0.8
            ))
        
        if visitor.has_hardcoded_secrets:
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.CRITICAL,
                category="security",
                message="Potential hardcoded secrets detected",
                file_path=genesis_key.file_path,
                line_number=change.line_numbers[0],
                suggestion="Use environment variables or secrets management",
                confidence=0.7
            ))
        
        if visitor.complexity > 15:
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.SUGGESTION,
                category="maintainability",
                message=f"High cyclomatic complexity ({visitor.complexity})",
                file_path=genesis_key.file_path,
                line_number=change.line_numbers[0],
                suggestion="Consider breaking into smaller functions",
                confidence=0.6
            ))
        
        return issues
    
    def _check_breaking_changes(
        self,
        before_tree: ast.AST,
        after_tree: ast.AST,
        genesis_key: GenesisKey,
        change: CodeChange
    ) -> List[CodeReviewIssue]:
        """Check for breaking changes."""
        issues = []
        
        # Extract function signatures
        before_funcs = self._extract_function_signatures(before_tree)
        after_funcs = self._extract_function_signatures(after_tree)
        
        # Check for signature changes
        for func_name, before_sig in before_funcs.items():
            if func_name in after_funcs:
                after_sig = after_funcs[func_name]
                if before_sig != after_sig:
                    issues.append(CodeReviewIssue(
                        severity=ReviewSeverity.WARNING,
                        category="breaking_change",
                        message=f"Function '{func_name}' signature changed",
                        file_path=genesis_key.file_path,
                        line_number=change.line_numbers[0],
                        suggestion="Update all callers or maintain backward compatibility",
                        confidence=0.9
                    ))
        
        return issues
    
    def _review_imports(
        self,
        change: CodeChange,
        genesis_key: GenesisKey
    ) -> List[CodeReviewIssue]:
        """Review import changes."""
        issues = []
        
        # Check for unused imports (simplified)
        # In production, would do full dependency analysis
        
        return issues
    
    def _review_overall(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> List[CodeReviewIssue]:
        """Review overall code change patterns."""
        issues = []
        
        # High risk changes
        if change_analysis.risk_score > 0.7:
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.WARNING,
                category="risk",
                message=f"High-risk change detected (risk={change_analysis.risk_score:.2f})",
                file_path=genesis_key.file_path,
                suggestion="Consider additional testing and code review",
                confidence=0.8
            ))
        
        # Large changes
        if len(change_analysis.changes) > 10:
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.SUGGESTION,
                category="maintainability",
                message=f"Large change ({len(change_analysis.changes)} modifications)",
                file_path=genesis_key.file_path,
                suggestion="Consider splitting into smaller, focused changes",
                confidence=0.7
            ))
        
        # Security-sensitive files
        if any(keyword in genesis_key.file_path.lower() for keyword in ['auth', 'security', 'password', 'token']):
            issues.append(CodeReviewIssue(
                severity=ReviewSeverity.WARNING,
                category="security",
                message="Security-sensitive file modified",
                file_path=genesis_key.file_path,
                suggestion="Ensure security review and additional testing",
                confidence=0.9
            ))
        
        return issues
    
    def _calculate_score(self, issues: List[CodeReviewIssue]) -> float:
        """Calculate overall review score."""
        if not issues:
            return 1.0
        
        # Weight by severity
        severity_weights = {
            ReviewSeverity.INFO: 0.0,
            ReviewSeverity.SUGGESTION: 0.1,
            ReviewSeverity.WARNING: 0.3,
            ReviewSeverity.ERROR: 0.6,
            ReviewSeverity.CRITICAL: 1.0
        }
        
        total_penalty = sum(severity_weights.get(issue.severity, 0.0) for issue in issues)
        score = max(0.0, 1.0 - (total_penalty / max(1, len(issues))))
        
        return score
    
    def _generate_suggestions(
        self,
        issues: List[CodeReviewIssue],
        change_analysis: ChangeAnalysis
    ) -> List[str]:
        """Generate actionable suggestions."""
        suggestions = []
        
        # Group by category
        by_category = {}
        for issue in issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)
        
        # Generate category-specific suggestions
        if 'security' in by_category:
            suggestions.append("Security review recommended - multiple security-related issues found")
        
        if 'breaking_change' in by_category:
            suggestions.append("Breaking changes detected - ensure backward compatibility or update all callers")
        
        if 'maintainability' in by_category:
            suggestions.append("Consider refactoring for better maintainability")
        
        return suggestions
    
    def _extract_function_signatures(self, tree: ast.AST) -> Dict[str, str]:
        """Extract function signatures from AST."""
        signatures = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Simple signature: name + arg count
                arg_count = len(node.args.args)
                signatures[node.name] = f"{node.name}({arg_count} args)"
        
        return signatures


class CodeQualityVisitor(ast.NodeVisitor):
    """AST visitor to detect code quality issues."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.has_bare_except = False
        self.has_hardcoded_secrets = False
        self.complexity = 0
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.has_bare_except = True
        self.generic_visit(node)
    
    def visit_Str(self, node: ast.Str):
        # Simple heuristic for secrets
        value = node.s.lower()
        if any(keyword in value for keyword in ['password', 'secret', 'api_key', 'token']):
            if len(value) > 10:  # Likely not just a variable name
                self.has_hardcoded_secrets = True
        self.generic_visit(node)
    
    def visit_If(self, node: ast.If):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node: ast.While):
        self.complexity += 1
        self.generic_visit(node)


# Global instance
_reviewer: Optional[AutonomousCodeReviewer] = None


def get_autonomous_code_reviewer() -> AutonomousCodeReviewer:
    """Get or create global autonomous code reviewer instance."""
    global _reviewer
    if _reviewer is None:
        _reviewer = AutonomousCodeReviewer()
    return _reviewer
