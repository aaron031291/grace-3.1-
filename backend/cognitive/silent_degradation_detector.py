"""
Silent Degradation Detector - Detects silently failing components.

Identifies components that are failing or degrading without proper logging,
monitoring, or alerting - enabling proactive healing before issues escalate.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DegradationType(str, Enum):
    """Types of silent degradation patterns."""
    SWALLOWED_EXCEPTION = "swallowed_exception"  # try/except without logging
    SILENT_RETURN = "silent_return"  # Returns None/empty instead of raising
    FREQUENT_FALLBACK = "frequent_fallback"  # Fallback paths hit frequently
    DEGRADED_COMPONENT = "degraded_component"  # Component in degraded state
    DEFAULT_VALUE_FALLBACK = "default_value_fallback"  # Using defaults due to failure
    MISSING_TELEMETRY = "missing_telemetry"  # Expected metrics/logs missing
    PARTIAL_FAILURE = "partial_failure"  # Component partially working


class SeverityLevel(str, Enum):
    """Severity levels for degradation issues."""
    LOW = "low"  # Minor impact, no immediate action needed
    MEDIUM = "medium"  # Noticeable impact, should address soon
    HIGH = "high"  # Significant impact, address promptly
    CRITICAL = "critical"  # Severe impact, immediate action required


@dataclass
class DegradationIssue:
    """Represents a detected degradation issue."""
    issue_id: str
    issue_type: DegradationType
    severity: SeverityLevel
    component: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    health_impact_score: float = 0.0  # 0-1 scale

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "component": self.component,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_fix": self.suggested_fix,
            "detected_at": self.detected_at.isoformat(),
            "health_impact_score": self.health_impact_score,
        }


class ExceptionSwallowingVisitor(ast.NodeVisitor):
    """AST visitor to detect try/except blocks that swallow exceptions."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: List[DegradationIssue] = []
        self._issue_counter = 0
        self._current_function: Optional[str] = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_func = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old_func
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        old_func = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old_func
    
    def visit_Try(self, node: ast.Try) -> None:
        for handler in node.handlers:
            if self._is_swallowed_exception(handler):
                self._issue_counter += 1
                
                exception_type = "Exception"
                if handler.type:
                    if isinstance(handler.type, ast.Name):
                        exception_type = handler.type.id
                    elif isinstance(handler.type, ast.Attribute):
                        exception_type = handler.type.attr
                
                issue = DegradationIssue(
                    issue_id=f"SWL-{self._issue_counter:04d}",
                    issue_type=DegradationType.SWALLOWED_EXCEPTION,
                    severity=self._estimate_severity(handler),
                    component=self._current_function or "module_level",
                    file_path=self.file_path,
                    line_number=handler.lineno,
                    description=f"Exception ({exception_type}) caught but not logged or re-raised",
                    evidence={
                        "handler_type": exception_type,
                        "function": self._current_function,
                        "body_statements": len(handler.body),
                    },
                    suggested_fix="Add logging with logger.exception() or logger.error() to preserve error context",
                )
                issue.health_impact_score = self._calculate_health_impact(issue)
                self.issues.append(issue)
        
        self.generic_visit(node)
    
    def _is_swallowed_exception(self, handler: ast.ExceptHandler) -> bool:
        """Check if exception handler swallows the exception without logging."""
        has_logging = False
        has_raise = False
        
        for stmt in ast.walk(handler):
            if isinstance(stmt, ast.Raise):
                has_raise = True
                break
            
            if isinstance(stmt, ast.Call):
                func = stmt.func
                if isinstance(func, ast.Attribute):
                    attr_name = func.attr.lower()
                    if attr_name in ("error", "exception", "warning", "critical", "log"):
                        if isinstance(func.value, ast.Name):
                            if func.value.id.lower() in ("logger", "logging", "log"):
                                has_logging = True
                                break
        
        if has_raise or has_logging:
            return False
        
        if len(handler.body) == 1:
            stmt = handler.body[0]
            if isinstance(stmt, ast.Pass):
                return True
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                return True
        
        has_only_pass_or_assign = True
        for stmt in handler.body:
            if isinstance(stmt, (ast.Pass, ast.Assign)):
                continue
            if isinstance(stmt, ast.Return):
                if stmt.value is None:
                    continue
                if isinstance(stmt.value, ast.Constant) and stmt.value.value in (None, False, [], {}, ""):
                    continue
            has_only_pass_or_assign = False
            break
        
        return has_only_pass_or_assign
    
    def _estimate_severity(self, handler: ast.ExceptHandler) -> SeverityLevel:
        """Estimate severity based on exception type and context."""
        if handler.type is None:
            return SeverityLevel.HIGH
        
        exception_name = ""
        if isinstance(handler.type, ast.Name):
            exception_name = handler.type.id
        elif isinstance(handler.type, ast.Attribute):
            exception_name = handler.type.attr
        
        critical_exceptions = {"Exception", "BaseException", "SystemExit", "KeyboardInterrupt"}
        high_exceptions = {"RuntimeError", "IOError", "OSError", "ConnectionError", "TimeoutError"}
        
        if exception_name in critical_exceptions:
            return SeverityLevel.CRITICAL
        if exception_name in high_exceptions:
            return SeverityLevel.HIGH
        
        return SeverityLevel.MEDIUM
    
    def _calculate_health_impact(self, issue: DegradationIssue) -> float:
        """Calculate health impact score (0-1)."""
        base_score = {
            SeverityLevel.LOW: 0.2,
            SeverityLevel.MEDIUM: 0.4,
            SeverityLevel.HIGH: 0.7,
            SeverityLevel.CRITICAL: 0.9,
        }.get(issue.severity, 0.5)
        
        return min(1.0, base_score)


class SilentReturnVisitor(ast.NodeVisitor):
    """AST visitor to detect functions that silently return None/empty on errors."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: List[DegradationIssue] = []
        self._issue_counter = 0
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)
    
    def _check_function(self, node) -> None:
        """Check if function has silent return patterns."""
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                for handler in child.handlers:
                    for stmt in handler.body:
                        if isinstance(stmt, ast.Return):
                            if self._is_silent_return(stmt):
                                self._issue_counter += 1
                                issue = DegradationIssue(
                                    issue_id=f"SRT-{self._issue_counter:04d}",
                                    issue_type=DegradationType.SILENT_RETURN,
                                    severity=SeverityLevel.MEDIUM,
                                    component=node.name,
                                    file_path=self.file_path,
                                    line_number=stmt.lineno,
                                    description=f"Function '{node.name}' silently returns None/empty on exception",
                                    evidence={
                                        "function": node.name,
                                        "return_type": self._get_return_type(stmt),
                                    },
                                    suggested_fix="Consider logging the error or raising a custom exception",
                                )
                                issue.health_impact_score = 0.4
                                self.issues.append(issue)
    
    def _is_silent_return(self, stmt: ast.Return) -> bool:
        """Check if return is a silent failure pattern."""
        if stmt.value is None:
            return True
        
        if isinstance(stmt.value, ast.Constant):
            if stmt.value.value in (None, False, "", 0):
                return True
        
        if isinstance(stmt.value, (ast.List, ast.Dict, ast.Tuple)):
            if len(stmt.value.elts if hasattr(stmt.value, 'elts') else stmt.value.keys) == 0:
                return True
        
        return False
    
    def _get_return_type(self, stmt: ast.Return) -> str:
        """Get string description of return value."""
        if stmt.value is None:
            return "None (implicit)"
        if isinstance(stmt.value, ast.Constant):
            return f"Constant({repr(stmt.value.value)})"
        if isinstance(stmt.value, ast.List):
            return "Empty list"
        if isinstance(stmt.value, ast.Dict):
            return "Empty dict"
        return "unknown"


class SilentDegradationDetector:
    """
    Detects silently failing components in the codebase.
    
    Scans for:
    - Exception swallowing (try/except without logging)
    - Silent returns (None/empty on error)
    - Frequent fallback usage
    - Degraded component tracking
    - Missing telemetry
    """
    
    def __init__(
        self,
        repo_path: Optional[Path] = None,
        degraded_components: Optional[List[Dict[str, Any]]] = None,
        fallback_counters: Optional[Dict[str, int]] = None,
    ):
        self.repo_path = repo_path or Path.cwd()
        self.degraded_components = degraded_components or []
        self.fallback_counters = fallback_counters or {}
        
        self._issues: List[DegradationIssue] = []
        self._scan_cache: Dict[str, datetime] = {}
        self._issue_counter = 0
        
        logger.info(f"[DEGRADATION-DETECTOR] Initialized with repo_path={self.repo_path}")
    
    def scan_for_silent_failures(
        self,
        directory: Optional[str] = None,
        files: Optional[List[str]] = None,
        max_files: int = 100,
    ) -> List[DegradationIssue]:
        """
        Detect silently failing patterns in code.
        
        Scans for:
        - try/except blocks that swallow exceptions without logging
        - Functions returning None/empty on error instead of raising
        - Fallback paths being hit frequently
        - Components in degraded_components list
        - Features using default values due to failures
        
        Args:
            directory: Optional directory to scan (relative to repo_path)
            files: Optional list of files to scan (otherwise scans repo)
            max_files: Maximum files to scan (to avoid long scans)
            
        Returns:
            List of detected DegradationIssue objects
        """
        issues = []
        
        if files:
            py_files = [Path(f) for f in files if f.endswith(".py")]
        elif directory:
            scan_path = self.repo_path / directory
            if scan_path.exists():
                py_files = list(scan_path.rglob("*.py"))[:max_files]
            else:
                logger.warning(f"[DEGRADATION-DETECTOR] Directory not found: {scan_path}")
                py_files = []
        else:
            py_files = list(self.repo_path.rglob("*.py"))[:max_files]
        
        for file_path in py_files:
            try:
                file_issues = self._scan_file(file_path)
                issues.extend(file_issues)
            except Exception as e:
                logger.debug(f"[DEGRADATION-DETECTOR] Error scanning {file_path}: {e}")
        
        degraded_issues = self._check_degraded_components()
        issues.extend(degraded_issues)
        
        fallback_issues = self._check_fallback_patterns()
        issues.extend(fallback_issues)
        
        self._issues = issues
        logger.info(f"[DEGRADATION-DETECTOR] Found {len(issues)} silent failure patterns")
        
        return issues
    
    def scan_telemetry_gaps(self) -> List[DegradationIssue]:
        """
        Detect missing metrics/logs that indicate telemetry gaps.
        
        Returns:
            List of detected telemetry gap issues
        """
        issues = []
        
        critical_modules = [
            "autonomous_healing_system",
            "code_analyzer_self_healing",
            "enterprise_coding_agent",
            "learning_memory",
            "genesis_key_service",
        ]
        
        for module in critical_modules:
            module_path = self.repo_path / "cognitive" / f"{module}.py"
            if not module_path.exists():
                module_path = self.repo_path / "genesis" / f"{module}.py"
            
            if module_path.exists():
                try:
                    content = module_path.read_text(encoding="utf-8")
                    has_logger = "logger = " in content or "logger=" in content
                    has_metrics = "metrics" in content.lower() or "telemetry" in content.lower()
                    
                    if not has_logger:
                        self._issue_counter += 1
                        issues.append(DegradationIssue(
                            issue_id=f"TEL-{self._issue_counter:04d}",
                            issue_type=DegradationType.MISSING_TELEMETRY,
                            severity=SeverityLevel.HIGH,
                            component=module,
                            file_path=str(module_path),
                            description=f"Critical module '{module}' has no logger configured",
                            suggested_fix="Add logger = logging.getLogger(__name__) at module level",
                            health_impact_score=0.6,
                        ))
                except Exception as e:
                    logger.debug(f"[DEGRADATION-DETECTOR] Error checking telemetry for {module}: {e}")
        
        return issues
    
    def get_degradation_report(self) -> Dict[str, Any]:
        """
        Generate summary of all silent degradation issues.
        
        Returns:
            Dict with summary statistics and issue details
        """
        if not self._issues:
            self.scan_for_silent_failures()
        
        by_type = {}
        by_severity = {}
        by_component = {}
        
        for issue in self._issues:
            by_type[issue.issue_type.value] = by_type.get(issue.issue_type.value, 0) + 1
            by_severity[issue.severity.value] = by_severity.get(issue.severity.value, 0) + 1
            by_component[issue.component] = by_component.get(issue.component, 0) + 1
        
        total_impact = sum(i.health_impact_score for i in self._issues)
        avg_impact = total_impact / len(self._issues) if self._issues else 0
        
        return {
            "summary": {
                "total_issues": len(self._issues),
                "by_type": by_type,
                "by_severity": by_severity,
                "by_component": by_component,
                "average_health_impact": round(avg_impact, 3),
                "total_health_impact": round(total_impact, 3),
            },
            "critical_issues": [
                i.to_dict() for i in self._issues
                if i.severity == SeverityLevel.CRITICAL
            ],
            "high_issues": [
                i.to_dict() for i in self._issues
                if i.severity == SeverityLevel.HIGH
            ],
            "all_issues": [i.to_dict() for i in self._issues],
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def estimate_health_impact(self, issue: DegradationIssue) -> float:
        """
        Rate the severity/health impact of an issue.
        
        Args:
            issue: The degradation issue to rate
            
        Returns:
            Health impact score (0-1, where 1 is most severe)
        """
        base_scores = {
            DegradationType.SWALLOWED_EXCEPTION: 0.6,
            DegradationType.SILENT_RETURN: 0.4,
            DegradationType.FREQUENT_FALLBACK: 0.5,
            DegradationType.DEGRADED_COMPONENT: 0.7,
            DegradationType.DEFAULT_VALUE_FALLBACK: 0.3,
            DegradationType.MISSING_TELEMETRY: 0.5,
            DegradationType.PARTIAL_FAILURE: 0.6,
        }
        
        base = base_scores.get(issue.issue_type, 0.5)
        
        severity_multiplier = {
            SeverityLevel.LOW: 0.5,
            SeverityLevel.MEDIUM: 1.0,
            SeverityLevel.HIGH: 1.5,
            SeverityLevel.CRITICAL: 2.0,
        }.get(issue.severity, 1.0)
        
        score = base * severity_multiplier
        
        critical_components = {
            "autonomous_healing_system", "genesis_key_service",
            "learning_memory", "code_analyzer_self_healing",
        }
        if any(c in issue.component.lower() for c in critical_components):
            score *= 1.3
        
        return min(1.0, score)
    
    def register_degraded_component(
        self,
        component: str,
        reason: str,
        impact: str,
    ) -> None:
        """Register a component as degraded."""
        self.degraded_components.append({
            "component": component,
            "reason": reason,
            "impact": impact,
            "registered_at": datetime.utcnow().isoformat(),
        })
        logger.info(f"[DEGRADATION-DETECTOR] Registered degraded component: {component}")
    
    def increment_fallback_counter(self, fallback_path: str) -> int:
        """Increment counter for a fallback path being hit."""
        self.fallback_counters[fallback_path] = self.fallback_counters.get(fallback_path, 0) + 1
        count = self.fallback_counters[fallback_path]
        
        if count % 10 == 0:
            logger.warning(f"[DEGRADATION-DETECTOR] Fallback '{fallback_path}' hit {count} times")
        
        return count
    
    def _scan_file(self, file_path: Path) -> List[DegradationIssue]:
        """Scan a single file for degradation patterns."""
        issues = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            swallow_visitor = ExceptionSwallowingVisitor(str(file_path))
            swallow_visitor.visit(tree)
            issues.extend(swallow_visitor.issues)
            
            silent_return_visitor = SilentReturnVisitor(str(file_path))
            silent_return_visitor.visit(tree)
            issues.extend(silent_return_visitor.issues)
            
        except SyntaxError as e:
            logger.debug(f"[DEGRADATION-DETECTOR] Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.debug(f"[DEGRADATION-DETECTOR] Error parsing {file_path}: {e}")
        
        return issues
    
    def _check_degraded_components(self) -> List[DegradationIssue]:
        """Check registered degraded components and create issues."""
        issues = []
        
        for component_info in self.degraded_components:
            self._issue_counter += 1
            issue = DegradationIssue(
                issue_id=f"DEG-{self._issue_counter:04d}",
                issue_type=DegradationType.DEGRADED_COMPONENT,
                severity=SeverityLevel.HIGH,
                component=component_info["component"],
                description=f"Component '{component_info['component']}' is in degraded mode",
                evidence={
                    "reason": component_info.get("reason", "Unknown"),
                    "impact": component_info.get("impact", "Unknown"),
                },
                suggested_fix="Investigate and restore full functionality",
            )
            issue.health_impact_score = self.estimate_health_impact(issue)
            issues.append(issue)
        
        return issues
    
    def _check_fallback_patterns(self) -> List[DegradationIssue]:
        """Check for frequently hit fallback paths."""
        issues = []
        
        FALLBACK_THRESHOLD = 5
        
        for path, count in self.fallback_counters.items():
            if count >= FALLBACK_THRESHOLD:
                self._issue_counter += 1
                severity = SeverityLevel.CRITICAL if count >= 20 else (
                    SeverityLevel.HIGH if count >= 10 else SeverityLevel.MEDIUM
                )
                
                issue = DegradationIssue(
                    issue_id=f"FBK-{self._issue_counter:04d}",
                    issue_type=DegradationType.FREQUENT_FALLBACK,
                    severity=severity,
                    component=path,
                    description=f"Fallback path '{path}' hit {count} times",
                    evidence={"hit_count": count, "threshold": FALLBACK_THRESHOLD},
                    suggested_fix="Investigate why primary path is failing",
                )
                issue.health_impact_score = self.estimate_health_impact(issue)
                issues.append(issue)
        
        return issues


_degradation_detector: Optional[SilentDegradationDetector] = None


def get_degradation_detector(
    repo_path: Optional[Path] = None,
    degraded_components: Optional[List[Dict[str, Any]]] = None,
) -> SilentDegradationDetector:
    """Get or create global degradation detector instance."""
    global _degradation_detector
    if _degradation_detector is None or repo_path is not None:
        _degradation_detector = SilentDegradationDetector(
            repo_path=repo_path,
            degraded_components=degraded_components,
        )
    return _degradation_detector
