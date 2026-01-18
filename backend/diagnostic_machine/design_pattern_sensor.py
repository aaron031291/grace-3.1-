import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
logger = logging.getLogger(__name__)

class DesignPatternIssue:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """A design pattern issue detected by the sensor."""
    pattern_type: str  # 'missing_cache_invalidation', 'missing_error_handling', etc.
    severity: str  # 'low', 'medium', 'high'
    file_path: str
    line_number: Optional[int] = None
    component: str
    message: str
    fix_suggestion: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DesignPatternSensorData:
    """Design pattern detection sensor data."""
    issues: List[DesignPatternIssue] = field(default_factory=list)
    total_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    patterns_checked: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class DesignPatternSensor:
    """
    Sensor that detects design pattern issues and incomplete implementations.
    
    Detects:
    - Missing cache invalidation
    - Missing error handling
    - Incomplete singleton patterns
    - Missing type hints in critical functions
    - Missing validation
    """
    
    def __init__(self, backend_dir: Optional[Path] = None):
        """Initialize design pattern sensor."""
        if backend_dir is None:
            backend_dir = Path(__file__).parent.parent
        self.backend_dir = backend_dir
        
    def detect_all(self) -> DesignPatternSensorData:
        """Run all design pattern checks."""
        data = DesignPatternSensorData()
        
        # Check for missing cache invalidation
        cache_issues = self._check_cache_invalidation()
        data.issues.extend(cache_issues)
        data.patterns_checked.append("cache_invalidation")
        
        # Check for missing error handling
        error_handling_issues = self._check_error_handling()
        data.issues.extend(error_handling_issues)
        data.patterns_checked.append("error_handling")
        
        # Check singleton patterns
        singleton_issues = self._check_singleton_patterns()
        data.issues.extend(singleton_issues)
        data.patterns_checked.append("singleton_patterns")
        
        # Calculate totals
        data.total_issues = len(data.issues)
        data.high_issues = sum(1 for i in data.issues if i.severity == 'high')
        data.medium_issues = sum(1 for i in data.issues if i.severity == 'medium')
        data.low_issues = sum(1 for i in data.issues if i.severity == 'low')
        
        return data
    
    def _check_cache_invalidation(self) -> List[DesignPatternIssue]:
        """Check for missing cache invalidation mechanisms."""
        issues = []
        
        # Check embedding model cache
        embedder_file = self.backend_dir / "embedding" / "embedder.py"
        if embedder_file.exists():
            content = embedder_file.read_text(encoding='utf-8')
            
            # Check if cache invalidation function exists
            has_cache = '_cache' in content or '_instance' in content or 'singleton' in content.lower()
            has_invalidation = 'invalidate' in content.lower() or 'clear_cache' in content.lower() or 'reset' in content.lower()
            
            if has_cache and not has_invalidation:
                issues.append(DesignPatternIssue(
                    pattern_type='missing_cache_invalidation',
                    severity='medium',
                    file_path=str(embedder_file.relative_to(self.backend_dir.parent)),
                    component='embedding',
                    message="Cache/singleton pattern detected but no invalidation mechanism found",
                    fix_suggestion="Add cache invalidation function (e.g., invalidate_embedding_cache())"
                ))
        
        # Check Qdrant client cache
        qdrant_file = self.backend_dir / "vector_db" / "client.py"
        if qdrant_file.exists():
            content = qdrant_file.read_text(encoding='utf-8')
            
            has_singleton = '_qdrant_client' in content or 'singleton' in content.lower()
            has_invalidation = 'invalidate' in content.lower() or 'force_new' in content.lower()
            
            if has_singleton and not has_invalidation:
                issues.append(DesignPatternIssue(
                    pattern_type='missing_cache_invalidation',
                    severity='low',
                    file_path=str(qdrant_file.relative_to(self.backend_dir.parent)),
                    component='vector_db',
                    message="Singleton pattern detected but no cache invalidation mechanism",
                    fix_suggestion="Add cache invalidation or force_new parameter support"
                ))
        
        return issues
    
    def _check_error_handling(self) -> List[DesignPatternIssue]:
        """Check for missing error handling in critical functions."""
        issues = []
        
        # Check API endpoints for error handling
        api_dir = self.backend_dir / "api"
        if api_dir.exists():
            for api_file in api_dir.glob("*.py"):
                try:
                    content = api_file.read_text(encoding='utf-8')
                    
                    # Check for router endpoints
                    if '@router.' in content:
                        # Parse file to find functions
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    # Check if it's an endpoint (has decorator)
                                    has_decorator = any(
                                        isinstance(d, ast.Name) and d.id in ['router', 'app']
                                        or (isinstance(d, ast.Attribute) and d.attr in ['post', 'get', 'put', 'delete'])
                                        for d in node.decorator_list
                                    )
                                    
                                    if has_decorator:
                                        # Check for try/except
                                        has_try_except = any(
                                            isinstance(stmt, ast.Try)
                                            for stmt in ast.walk(node)
                                        )
                                        
                                        if not has_try_except:
                                            issues.append(DesignPatternIssue(
                                                pattern_type='missing_error_handling',
                                                severity='medium',
                                                file_path=str(api_file.relative_to(self.backend_dir.parent)),
                                                line_number=node.lineno,
                                                component='api',
                                                message=f"API endpoint '{node.name}' missing error handling",
                                                fix_suggestion=f"Add try/except block to handle errors in {node.name}"
                                            ))
                        except SyntaxError:
                            pass
                            
                except Exception as e:
                    logger.debug(f"Could not check {api_file}: {e}")
        
        return issues[:20]  # Limit to 20 issues
    
    def _check_singleton_patterns(self) -> List[DesignPatternIssue]:
        """Check for incomplete singleton patterns."""
        issues = []
        
        # Check for singleton patterns without proper initialization
        python_files = list(self.backend_dir.rglob("*.py"))
        
        for py_file in python_files[:30]:  # Limit to first 30 files
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for singleton pattern indicators
                has_singleton = '_instance' in content or 'singleton' in content.lower()
                has_getter = 'get_' in content and ('_instance' in content or 'singleton' in content.lower())
                
                if has_singleton and not has_getter:
                    # Check if it's a module-level singleton
                    if '_instance' in content and 'def get_' not in content:
                        issues.append(DesignPatternIssue(
                            pattern_type='incomplete_singleton',
                            severity='low',
                            file_path=str(py_file.relative_to(self.backend_dir.parent)),
                            component='singleton',
                            message="Singleton pattern detected but no getter function found",
                            fix_suggestion="Add get_*() function to access singleton instance"
                        ))
                        
            except Exception:
                pass
        
        return issues[:10]  # Limit to 10 issues
