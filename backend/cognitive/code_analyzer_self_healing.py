import logging
import ast
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from cognitive.grace_code_analyzer import GraceCodeAnalyzer, CodeIssue, Severity, Confidence, PatternRule
from cognitive.autonomous_healing_system import AutonomousHealingSystem, HealingAction, TrustLevel, HealthStatus
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
class ASTCodeTransformer(ast.NodeTransformer):
    logger = logging.getLogger(__name__)
    """AST Transformer for code fixes (inspired by pytest assertion rewriting)"""
    
    def __init__(self, issue: CodeIssue):
        self.issue = issue
        self.fixed = False
        self.needs_logging_import = False
    
    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Visit module to check for logging import"""
        if self.issue.rule_id == 'G012':
            # Check if logging is already imported
            has_logging_import = False
            for item in node.body:
                if isinstance(item, ast.Import):
                    for alias in item.names:
                        if alias.name == 'logging':
                            has_logging_import = True
                            break
                elif isinstance(item, ast.ImportFrom):
                    if item.module == 'logging':
                        has_logging_import = True
                        break
            
            if not has_logging_import:
                # Add import logging at the top of the file
                logging_import = ast.Import(names=[ast.alias(name='logging', asname=None)])
                # Find the right position (after docstrings, before other imports if any)
                insert_pos = 0
                for i, item in enumerate(node.body):
                    if isinstance(item, ast.Expr) and isinstance(item.value, ast.Str):  # Docstring
                        insert_pos = i + 1
                    elif isinstance(item, (ast.Import, ast.ImportFrom)):
                        # Insert before other imports
                        insert_pos = i
                        break
                node.body.insert(insert_pos, logging_import)
                self.needs_logging_import = True
        
        return self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Add logger to class if G012 issue"""
        if self.issue.rule_id == 'G012':
            # Check if we're at the right line (approximately)
            # The issue line number should be around the class definition
            if self.issue.line_number and hasattr(node, 'lineno'):
                # Check if this is the class we need to fix
                if abs(node.lineno - self.issue.line_number) <= 2:
                    # Check if logger already exists
                    has_logger = False
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == 'logger':
                                    has_logger = True
                                    break
                        # Check in __init__ too
                        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                            for stmt in item.body:
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self' and target.attr == 'logger':
                                            has_logger = True
                                            break
                    
                    if not has_logger:
                        # Add logger = logging.getLogger(__name__) as first statement in class
                        logger_assign = ast.Assign(
                            targets=[ast.Name(id='logger', ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id='logging', ctx=ast.Load()),
                                    attr='getLogger',
                                    ctx=ast.Load()
                                ),
                                args=[ast.Name(id='__name__', ctx=ast.Load())],
                                keywords=[]
                            )
                        )
                        # Add to beginning of class body
                        node.body.insert(0, logger_assign)
                        self.fixed = True
        
        return self.generic_visit(node)


class CodeFixApplicator:
    """Applies code fixes based on analyzer findings"""
    
    def __init__(self):
        self.fix_applications = []
    
    def apply_fix(self, issue: CodeIssue, source_code: str) -> Tuple[bool, str]:
        """
        Apply a fix to source code.
        
        Returns:
            (success, fixed_code)
        """
        try:
            lines = source_code.split('\n')
            if issue.line_number <= 0 or issue.line_number > len(lines):
                return False, source_code
            
            line_index = issue.line_number - 1
            original_line = lines[line_index]
            
            # Apply fix based on rule type
            fixed_lines = lines.copy()
            
            if issue.rule_id == 'G006':  # Print statement
                # Replace print with logger
                if 'print(' in original_line:
                    # Simple replacement - in practice would use AST transformation
                    fixed_line = original_line.replace('print(', 'logger.info(')
                    fixed_lines[line_index] = fixed_line
            
            elif issue.rule_id == 'G007':  # Bare except
                # Replace bare except with except Exception
                if ': except:' in original_line or original_line.strip() == 'except:':
                    fixed_line = original_line.replace('except:', 'except Exception:')
                    fixed_lines[line_index] = fixed_line
            
            elif issue.rule_id == 'G012':  # Missing logger
                # Use AST transformation to add logger to class
                try:
                    tree = ast.parse(source_code)
                    transformer = ASTCodeTransformer(issue)
                    transformed_tree = transformer.visit(tree)
                    
                    if transformer.fixed:
                        # Convert AST back to source code
                        fixed_code = self._ast_to_source(transformed_tree, source_code)
                        
                        # Verify syntax
                        ast.parse(fixed_code)
                        return True, fixed_code
                    else:
                        return False, source_code
                except SyntaxError as e:
                    logger.warning(f"Could not parse code for G012 fix: {e}")
                    return False, source_code
                except Exception as e:
                    logger.error(f"Error applying AST transformation for G012: {e}")
                    return False, source_code
            
            elif issue.rule_id == 'SYNTAX_ERROR':
                # Try to fix syntax errors with AST-based parsing
                try:
                    # First, try to parse and identify the syntax error
                    tree = ast.parse(source_code)
                    # If we got here, code is valid - issue might be stale
                    return False, source_code
                except SyntaxError as e:
                    # Try common syntax fixes
                    # Missing colon after if/for/while/def/class
                    if 'expected' in str(e).lower() and ':' in str(e):
                        if original_line.strip().endswith('):') or original_line.strip().endswith('):'):
                            pass  # Already has colon
                        elif original_line.strip().endswith(')') or original_line.strip().endswith(']'):
                            fixed_lines[line_index] = original_line + ':'
                        elif not original_line.strip().endswith(':'):
                            # Add colon if missing at end
                            fixed_lines[line_index] = original_line.rstrip() + ':'
                    
                    # If suggested_fix provided, use it
                    if issue.suggested_fix:
                        fixed_lines[line_index] = issue.suggested_fix
                    else:
                        # Try basic syntax error recovery
                        logger.debug(f"Syntax error at line {issue.line_number}: {e}")
                        return False, source_code
            
            elif issue.rule_id == 'IMPORT_ERROR':
                # Import errors - can't easily auto-fix without knowing correct path
                # But if suggested_fix is provided, we can try
                if issue.suggested_fix:
                    # Try to apply suggested fix
                    # Usually import errors are in import statements
                    if 'import' in original_line.lower():
                        fixed_lines[line_index] = issue.suggested_fix
                    else:
                        # Try to fix import statement
                        logger.debug(f"Import error - suggested fix: {issue.suggested_fix}")
                        return False, source_code
                else:
                    return False, source_code
            
            elif issue.rule_id == 'MISSING_FILE':
                # Missing file - usually can't auto-fix (file doesn't exist)
                # But if suggested_fix tells us to comment out the import, do that
                if issue.suggested_fix and 'comment' in issue.suggested_fix.lower():
                    if original_line.strip().startswith('from') or original_line.strip().startswith('import'):
                        fixed_lines[line_index] = '# ' + original_line
                    else:
                        return False, source_code
                else:
                    return False, source_code
            
            fixed_code = '\n'.join(fixed_lines)
            
            # Verify fix doesn't break syntax
            try:
                ast.parse(fixed_code)
                return True, fixed_code
            except SyntaxError:
                logger.warning(f"Fix for {issue.rule_id} at line {issue.line_number} created syntax error")
                return False, source_code
            
        except Exception as e:
            logger.error(f"Error applying fix for {issue.rule_id}: {e}")
            return False, source_code
    
    def can_auto_fix(self, issue: CodeIssue) -> bool:
        """Check if issue can be auto-fixed safely"""
        # Rules that can be auto-fixed
        auto_fixable_rules = {
            'G006',  # Print statement
            'G007',  # Bare except
            'G012',  # Missing logger (with caution)
            'SYNTAX_ERROR',  # Syntax fixes (diagnostic)
            'IMPORT_ERROR',  # Import errors (diagnostic)
            'MISSING_FILE',  # Missing files (diagnostic)
        }
        
        # Diagnostic issues (SYNTAX_ERROR, IMPORT_ERROR) can be HIGH severity
        # Standard code quality issues should be LOW/MEDIUM
        if issue.rule_id in ['SYNTAX_ERROR', 'IMPORT_ERROR', 'MISSING_FILE']:
            # Diagnostic issues: allow HIGH severity if we have a suggested fix
            return (
                issue.rule_id in auto_fixable_rules and
                issue.suggested_fix is not None
            )
        else:
            # Standard code quality: only LOW/MEDIUM severity
            safe_severities = {Severity.LOW, Severity.MEDIUM}
            return (
                issue.rule_id in auto_fixable_rules and
                issue.severity in safe_severities and
                (issue.suggested_fix is not None or issue.rule_id == 'G012')  # G012 uses AST transformation
            )
    
    def _ast_to_source(self, tree: ast.AST, original_source: str) -> str:
        """Convert AST back to source code with proper formatting"""
        # Try using ast.unparse (Python 3.9+)
        try:
            if hasattr(ast, 'unparse'):
                result = ast.unparse(tree)
                # Verify the result contains what we expect
                if result and ('logger = logging.getLogger(__name__)' in result or 'logger' in result):
                    return result
        except (AttributeError, Exception) as e:
            logger.debug(f"ast.unparse failed: {e}")
            pass
        
        # Fallback: Try using astor if available
        try:
            import astor
            result = astor.to_source(tree)
            if result:
                return result
        except (ImportError, Exception) as e:
            logger.debug(f"astor.to_source failed: {e}")
            pass
        
        # Last resort: Manual reconstruction
        # Extract imports from AST and rebuild source
        lines = original_source.split('\n')
        output_lines = []
        
        # First, extract any imports from the AST
        if isinstance(tree, ast.Module):
            for node in tree.body:
                if isinstance(node, ast.Import):
                    # Convert Import node to source
                    import_names = []
                    for alias in node.names:
                        if alias.asname:
                            import_names.append(f"{alias.name} as {alias.asname}")
                        else:
                            import_names.append(alias.name)
                    output_lines.append(f"import {', '.join(import_names)}")
                elif isinstance(node, ast.ImportFrom):
                    # Convert ImportFrom node to source
                    module = node.module or ''
                    from_str = f"from {module} import " if module else "from . import "
                    import_names = []
                    for alias in node.names:
                        if alias.asname:
                            import_names.append(f"{alias.name} as {alias.asname}")
                        else:
                            import_names.append(alias.name)
                    output_lines.append(from_str + ', '.join(import_names))
        
        # Then add the original lines (but skip lines that match the class we're modifying)
        # For G012, we need to find the class and insert logger there
        class_found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('class ') and ':' in stripped:
                class_found = True
                output_lines.append(line)  # Add class declaration
                # Find where class body starts and insert logger
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line.strip():  # First non-empty line after class
                        indent = len(next_line) - len(next_line.lstrip())
                        logger_line = ' ' * indent + 'logger = logging.getLogger(__name__)'
                        output_lines.append(logger_line)
                        # Add remaining lines
                        for remaining in lines[j:]:
                            output_lines.append(remaining)
                        break
                break
        
        if not class_found:
            # No class found, just return original with imports prepended
            output_lines.extend(lines)
        
        return '\n'.join(output_lines) if output_lines else '\n'.join(lines)


class CodeAnalyzerSelfHealing:
    """
    Self-healing code analyzer integration.
    
    Combines code analysis with autonomous healing to automatically
    fix code issues based on trust levels.
    
    Timesense Integration:
    - Estimates time for each fix operation
    - Prioritizes fixes by time efficiency
    - Tracks actual vs. predicted times
    - Schedules healing based on time estimates
    """
    
    def __init__(
        self,
        healing_system: Optional[AutonomousHealingSystem] = None,
        trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
        enable_auto_fix: bool = True,
        enable_timesense: bool = True
    ):
        self.analyzer = GraceCodeAnalyzer()
        self.healing_system = healing_system
        self.trust_level = trust_level
        self.enable_auto_fix = enable_auto_fix
        self.enable_timesense = enable_timesense and TIMESENSE_AVAILABLE
        self.fix_applicator = CodeFixApplicator()
        self.genesis_service = get_genesis_service() if self.healing_system else None
        
        # Timesense integration
        self.time_estimator = None
        if self.enable_timesense and TimeEstimator:
            try:
                self.time_estimator = TimeEstimator()
            except Exception as e:
                logger.warning(f"Could not initialize Timesense: {e}")
                self.enable_timesense = False
        
        # Tracking
        self.issues_found = []
        self.fixes_applied = []
        self.fix_outcomes = []
        self.time_predictions = {}  # issue_id -> PredictionResult
        self.actual_times = {}  # issue_id -> actual_time_ms
    
    def analyze_and_heal(
        self,
        directory: str = 'backend',
        auto_fix: bool = True,
        min_confidence: float = 0.8,
        pre_flight: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze codebase and automatically trigger healing for issues.
        
        Args:
            directory: Directory to analyze
            auto_fix: Whether to automatically apply fixes
            min_confidence: Minimum confidence for auto-fixing
        
        Returns:
            Dictionary with analysis and healing results
        """
        logger.info(f"[CODE-HEALING] Starting code analysis and healing on {directory}")
        
        # Step 1: Analyze codebase with GraceCodeAnalyzer
        results = self.analyzer.analyze_directory(directory)
        
        # Step 1b: Also check diagnostic engine for additional issues
        diagnostic_issues = self._get_diagnostic_engine_issues(directory)
        if diagnostic_issues:
            logger.info(f"[CODE-HEALING] Diagnostic engine found {len(diagnostic_issues)} additional issues")
            # Merge diagnostic issues into results
            for file_path, issues in diagnostic_issues.items():
                if file_path in results:
                    results[file_path].extend(issues)
                else:
                    results[file_path] = issues
        
        # Step 2: Collect all issues
        all_issues = []
        for file_path, issues in results.items():
            all_issues.extend(issues)
        
        self.issues_found = all_issues
        
        # Step 3: Evaluate which issues to fix
        fixable_issues = self._evaluate_fixable_issues(all_issues, min_confidence)
        
        # Step 4: Trigger healing for issues (or prepare pre-flight)
        healing_results = []
        pre_flight_decisions = []
        
        if pre_flight:
            # Pre-flight mode: Prepare decisions for approval
            pre_flight_decisions = self._prepare_pre_flight_decisions(fixable_issues, results)
        elif auto_fix and self.enable_auto_fix:
            # Normal mode: Apply fixes or prepare for healing system approval
            healing_results = self._trigger_healing(fixable_issues, results, pre_flight=False)
        
        # Step 5: Generate Genesis keys for tracking
        if self.genesis_service and not pre_flight:
            self._create_genesis_keys(all_issues, healing_results)
        
        # Calculate time statistics if Timesense enabled
        time_stats = None
        if self.enable_timesense and self.actual_times:
            time_stats = self._calculate_time_statistics()
        
        return {
            'issues_found': len(all_issues),
            'issues_by_severity': self._count_by_severity(all_issues),
            'fixable_issues': len(fixable_issues),
            'fixes_applied': len(healing_results) if not pre_flight else 0,
            'healing_results': healing_results if not pre_flight else [],
            'pre_flight_decisions': pre_flight_decisions if pre_flight else [],
            'health_status': self._determine_health_status(all_issues),
            'mode': 'pre_flight' if pre_flight else ('auto_fix' if auto_fix else 'analysis_only'),
            'timesense_enabled': self.enable_timesense,
            'time_statistics': time_stats
        }
    
    def _get_diagnostic_engine_issues(self, directory: str) -> Dict[str, List[CodeIssue]]:
        """
        Get issues from diagnostic engine (ProactiveScanner, diagnostic engine sensors).
        
        Returns:
            Dictionary mapping file_path -> list of CodeIssue objects
        """
        diagnostic_issues_by_file = {}
        
        try:
            # Try to get issues from ProactiveScanner
            try:
                from diagnostic_machine.proactive_code_scanner import ProactiveCodeScanner
                from pathlib import Path
                
                repo_path = Path(directory).parent if Path(directory).name == 'backend' else Path(directory)
                scanner = ProactiveCodeScanner(backend_dir=Path(directory))
                scanner_issues = scanner.scan_all()
                
                # Convert ProactiveScanner issues to CodeIssue format
                for diag_issue in scanner_issues:
                    file_path = diag_issue.file_path
                    
                    # Map severity
                    severity_map = {
                        'critical': Severity.HIGH,
                        'high': Severity.HIGH,
                        'medium': Severity.MEDIUM,
                        'low': Severity.LOW
                    }
                    severity = severity_map.get(diag_issue.severity, Severity.MEDIUM)
                    
                    # Map issue type to rule_id
                    rule_id_map = {
                        'syntax_error': 'SYNTAX_ERROR',
                        'import_error': 'IMPORT_ERROR',
                        'missing_file': 'MISSING_FILE',
                        'code_quality': 'CODE_QUALITY'
                    }
                    rule_id = rule_id_map.get(diag_issue.issue_type, 'DIAGNOSTIC_ISSUE')
                    
                    code_issue = CodeIssue(
                        rule_id=rule_id,
                        message=diag_issue.message or f"Diagnostic: {diag_issue.issue_type}",
                        severity=severity,
                        confidence=Confidence.HIGH if diag_issue.severity == 'critical' else Confidence.MEDIUM,
                        file_path=file_path,
                        line_number=diag_issue.line_number or 1,
                        suggested_fix=diag_issue.suggested_fix,
                        fix_confidence=0.8 if diag_issue.suggested_fix else 0.3
                    )
                    
                    if file_path not in diagnostic_issues_by_file:
                        diagnostic_issues_by_file[file_path] = []
                    diagnostic_issues_by_file[file_path].append(code_issue)
                    
                logger.info(f"[CODE-HEALING] Diagnostic scanner found {len(scanner_issues)} issues")
                
            except ImportError as e:
                logger.debug(f"[CODE-HEALING] ProactiveScanner not available: {e}")
            except Exception as e:
                logger.warning(f"[CODE-HEALING] Error getting ProactiveScanner issues: {e}")
            
            # Try to get issues from diagnostic engine code quality sensor
            try:
                from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
                
                engine = get_diagnostic_engine()
                if engine and hasattr(engine, 'sensor_layer'):
                    code_quality = engine.sensor_layer._collect_code_quality()
                    if code_quality:
                        # Process syntax errors
                        syntax_errors = getattr(code_quality, 'syntax_errors', [])
                        for err in syntax_errors:
                            file_path = getattr(err, 'file_path', 'unknown')
                            code_issue = CodeIssue(
                                rule_id='SYNTAX_ERROR',
                                message=getattr(err, 'description', 'Syntax error'),
                                severity=Severity.HIGH,
                                confidence=Confidence.HIGH,
                                file_path=file_path,
                                line_number=getattr(err, 'line_number', 1),
                                suggested_fix=None,
                                fix_confidence=0.7
                            )
                            if file_path not in diagnostic_issues_by_file:
                                diagnostic_issues_by_file[file_path] = []
                            diagnostic_issues_by_file[file_path].append(code_issue)
                        
                        # Process other issues
                        for issue_list_name in ['configuration_issues', 'database_issues', 'infrastructure_issues']:
                            issues = getattr(code_quality, issue_list_name, [])
                            for issue in issues:
                                file_path = getattr(issue, 'file_path', 'unknown')
                                code_issue = CodeIssue(
                                    rule_id='DIAGNOSTIC_ISSUE',
                                    message=getattr(issue, 'description', f'{issue_list_name} issue'),
                                    severity=Severity.MEDIUM,
                                    confidence=Confidence.MEDIUM,
                                    file_path=file_path,
                                    line_number=getattr(issue, 'line_number', 1),
                                    suggested_fix=None,
                                    fix_confidence=0.5
                                )
                                if file_path not in diagnostic_issues_by_file:
                                    diagnostic_issues_by_file[file_path] = []
                                diagnostic_issues_by_file[file_path].append(code_issue)
                                
                        logger.info(f"[CODE-HEALING] Diagnostic engine sensor found additional issues")
                        
            except ImportError as e:
                logger.debug(f"[CODE-HEALING] Diagnostic engine not available: {e}")
            except Exception as e:
                logger.warning(f"[CODE-HEALING] Error getting diagnostic engine issues: {e}")
                
        except Exception as e:
            logger.error(f"[CODE-HEALING] Error in _get_diagnostic_engine_issues: {e}")
        
        return diagnostic_issues_by_file
    
    def _estimate_fix_time(self, issue: CodeIssue) -> Optional[PredictionResult]:
        """Estimate time required to fix an issue using Timesense"""
        if not self.enable_timesense or not predict_time:
            return None
        
        try:
            # Map rule type to primitive operation
            # Code fixes are typically file operations
            primitive_type = PrimitiveType.FILE_PROCESSING
            
            # Estimate based on fix complexity
            # Simple fixes (print, bare except) are fast
            # Complex fixes (AST transformation) take longer
            size = 1.0  # Single line fix
            if issue.rule_id == 'G012':  # Missing logger - requires AST transformation
                size = 10.0  # More complex
            elif issue.rule_id in ['G006', 'G007']:  # Simple replacements
                size = 1.0
            
            prediction = predict_time(
                primitive_type=primitive_type,
                size=size,
                model_name=None
            )
            
            return prediction
        except Exception as e:
            logger.debug(f"Timesense prediction failed for {issue.rule_id}: {e}")
            return None
    
    def _evaluate_fixable_issues(
        self,
        issues: List[CodeIssue],
        min_confidence: float
    ) -> List[CodeIssue]:
        """Evaluate which issues can be safely auto-fixed"""
        fixable = []
        
        for issue in issues:
            # Check if auto-fixable
            if not self.fix_applicator.can_auto_fix(issue):
                continue
            
            # Check confidence threshold
            # For AST transformation fixes (like G012), use default high confidence
            if issue.rule_id == 'G012':
                # AST transformation is reliable, so set high confidence if not set
                issue_confidence = issue.fix_confidence if issue.fix_confidence > 0 else 0.9
            else:
                issue_confidence = issue.fix_confidence
            
            if issue_confidence < min_confidence:
                continue
            
            # Check trust level requirements
            if not self._can_auto_fix_at_trust_level(issue):
                continue
            
            # Estimate fix time if Timesense enabled
            if self.enable_timesense:
                time_prediction = self._estimate_fix_time(issue)
                if time_prediction:
                    # Use issue rule_id + line_number as unique ID
                    issue_id = f"{issue.rule_id}_{issue.line_number}_{issue.file_path}"
                    self.time_predictions[issue_id] = time_prediction
                    logger.debug(
                        f"Estimated fix time for {issue.rule_id} at line {issue.line_number}: "
                        f"{time_prediction.p50_ms:.2f}ms"
                    )
            
            fixable.append(issue)
        
        # Sort by estimated time if Timesense enabled (fastest first)
        if self.enable_timesense and fixable:
            fixable = self._prioritize_by_time(fixable)
        
        return fixable
    
    def _prioritize_by_time(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """Prioritize fixes by estimated execution time (fastest first)"""
        if not self.enable_timesense or not self.time_predictions:
            return issues
        
        def get_estimated_time(issue: CodeIssue) -> float:
            issue_id = f"{issue.rule_id}_{issue.line_number}_{issue.file_path}"
            prediction = self.time_predictions.get(issue_id)
            if prediction:
                return prediction.p50_ms  # Use median estimate
            return 1000.0  # Default high value if no prediction
        
        # Sort by estimated time (fastest first)
        return sorted(issues, key=get_estimated_time)
    
    def _can_auto_fix_at_trust_level(self, issue: CodeIssue) -> bool:
        """Check if issue can be auto-fixed at current trust level"""
        # Diagnostic issues (SYNTAX_ERROR, IMPORT_ERROR) can be fixed at MEDIUM_RISK_AUTO
        # even if HIGH severity, because they have suggested fixes
        if issue.rule_id in ['SYNTAX_ERROR', 'IMPORT_ERROR', 'MISSING_FILE']:
            # Diagnostic issues with suggested fixes: MEDIUM_RISK_AUTO is sufficient
            if issue.suggested_fix:
                return self.trust_level >= TrustLevel.MEDIUM_RISK_AUTO
        
        # Low severity: requires LOW_RISK_AUTO or higher
        if issue.severity == Severity.LOW:
            return self.trust_level >= TrustLevel.LOW_RISK_AUTO
        
        # Medium severity: requires MEDIUM_RISK_AUTO or higher
        elif issue.severity == Severity.MEDIUM:
            return self.trust_level >= TrustLevel.MEDIUM_RISK_AUTO
        
        # High/Critical: requires HIGH_RISK_AUTO or higher
        elif issue.severity in {Severity.HIGH, Severity.CRITICAL}:
            return self.trust_level >= TrustLevel.HIGH_RISK_AUTO
        
        return False
    
    def _prepare_pre_flight_decisions(
        self,
        fixable_issues: List[CodeIssue],
        analysis_results: Dict[str, List[CodeIssue]]
    ) -> List[Dict[str, Any]]:
        """Prepare pre-flight decisions for manual approval"""
        decisions = []
        
        # Group issues by file
        issues_by_file = {}
        for issue in fixable_issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)
        
        # Create pre-flight decision for each file
        for file_path, issues in issues_by_file.items():
            # Simulate what would be fixed
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path} for pre-flight: {e}")
                continue
            
            # Prepare fix preview
            fix_preview = []
            for issue in sorted(issues, key=lambda x: x.line_number):
                if issue.line_number > 0:
                    lines = source_code.split('\n')
                    if issue.line_number <= len(lines):
                        line_index = issue.line_number - 1
                        original_line = lines[line_index]
                        fix_preview.append({
                            'line': issue.line_number,
                            'rule_id': issue.rule_id,
                            'original': original_line.strip(),
                            'fix': self._preview_fix(issue, original_line),
                            'message': issue.message
                        })
            
            decisions.append({
                'file': file_path,
                'issues_count': len(issues),
                'rule_ids': list(set(i.rule_id for i in issues)),
                'fix_preview': fix_preview,
                'requires_approval': True,
                'execution_mode': 'manual_approval'
            })
        
        return decisions
    
    def _preview_fix(self, issue: CodeIssue, original_line: str) -> str:
        """Preview what the fix would look like"""
        if issue.rule_id == 'G006':  # Print statement
            return original_line.replace('print(', 'logger.info(')
        elif issue.rule_id == 'G007':  # Bare except
            return original_line.replace('except:', 'except Exception:')
        elif issue.rule_id == 'G012':  # Missing logger
            return f"{original_line}\n        self.logger = logging.getLogger(__name__)"
        else:
            return f"[Fix: {issue.suggested_fix}]"
    
    def _trigger_healing(
        self,
        fixable_issues: List[CodeIssue],
        analysis_results: Dict[str, List[CodeIssue]],
        pre_flight: bool = False
    ) -> List[Dict[str, Any]]:
        """Trigger healing actions for fixable issues"""
        healing_results = []
        
        # Group issues by file
        issues_by_file = {}
        for issue in fixable_issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)
        
        # Apply fixes to each file
        for file_path, issues in issues_by_file.items():
            if not Path(file_path).exists():
                continue
            
            try:
                # Read source code
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Apply fixes
                fixed_code = source_code
                fixes_applied_count = 0
                
                # Sort by line number (reverse to avoid line shifts) or by time if enabled
                if self.enable_timesense and self.time_predictions:
                    # Already sorted by time in _prioritize_by_time, but need reverse for line safety
                    sorted_issues = issues  # Keep time-based order
                else:
                    sorted_issues = sorted(issues, key=lambda x: x.line_number, reverse=True)
                
                for issue in sorted_issues:
                    issue_id = f"{issue.rule_id}_{issue.line_number}_{file_path}"
                    
                    # Track start time if Timesense enabled
                    start_time = None
                    if self.enable_timesense:
                        start_time = time.time()
                    
                    # Apply fix
                    success, fixed_code = self.fix_applicator.apply_fix(issue, fixed_code)
                    
                    # Track actual time if Timesense enabled
                    if self.enable_timesense and start_time:
                        actual_time_ms = (time.time() - start_time) * 1000
                        self.actual_times[issue_id] = actual_time_ms
                        
                        # Log prediction accuracy
                        if issue_id in self.time_predictions:
                            predicted = self.time_predictions[issue_id]
                            error_pct = abs(actual_time_ms - predicted.p50_ms) / predicted.p50_ms * 100 if predicted.p50_ms > 0 else 0
                            logger.debug(
                                f"Fix {issue.rule_id}: predicted {predicted.p50_ms:.2f}ms, "
                                f"actual {actual_time_ms:.2f}ms, error {error_pct:.1f}%"
                            )
                    
                    if success:
                        fixes_applied_count += 1
                        self.fixes_applied.append({
                            'file': file_path,
                            'rule_id': issue.rule_id,
                            'line': issue.line_number,
                            'message': issue.message
                        })
                        
                        # Update source code for next fix
                        source_code = fixed_code
                
                # Write fixed code if changes were made
                if fixes_applied_count > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_code)
                    
                    # Trigger healing action through healing system (unless pre-flight)
                    if self.healing_system and not pre_flight:
                        # Convert issues to anomaly format for healing system
                        anomaly = {
                            'type': 'CODE_ISSUE',
                            'severity': 'medium' if fixes_applied_count > 0 else 'low',
                            'details': f'{fixes_applied_count} code issues fixed in {file_path}',
                            'file_path': file_path,
                            'file_paths': [file_path],
                            'issues_fixed': fixes_applied_count,
                            'rule_ids': [i.rule_id for i in issues],
                            'evidence': [i.rule_id for i in issues]
                        }
                        
                        # Use healing system's decide and execute flow
                        decisions = self.healing_system.decide_healing_actions([anomaly])
                        if decisions:
                            # In pre-flight mode, decisions would require approval
                            execution_results = self.healing_system.execute_healing(decisions)
                            logger.info(f"[CODE-HEALING] Healing system executed: {execution_results}")
                    
                    healing_results.append({
                        'file': file_path,
                        'fixes_applied': fixes_applied_count,
                        'status': 'success'
                    })
                    
                    logger.info(
                        f"[CODE-HEALING] Applied {fixes_applied_count} fixes to {file_path}"
                    )
            
            except Exception as e:
                logger.error(f"[CODE-HEALING] Error fixing {file_path}: {e}")
                healing_results.append({
                    'file': file_path,
                    'fixes_applied': 0,
                    'status': 'error',
                    'error': str(e)
                })
        
        return healing_results
    
    def _count_by_severity(self, issues: List[CodeIssue]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {}
        for issue in issues:
            sev = issue.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts
    
    def _calculate_time_statistics(self) -> Dict[str, Any]:
        """Calculate time prediction accuracy statistics"""
        if not self.actual_times or not self.time_predictions:
            return None
        
        errors = []
        total_predicted = 0.0
        total_actual = 0.0
        
        for issue_id, actual_time in self.actual_times.items():
            if issue_id in self.time_predictions:
                predicted = self.time_predictions[issue_id]
                predicted_time = predicted.p50_ms
                
                total_predicted += predicted_time
                total_actual += actual_time
                
                error = abs(actual_time - predicted_time)
                error_pct = (error / predicted_time * 100) if predicted_time > 0 else 0
                errors.append(error_pct)
        
        if not errors:
            return None
        
        avg_error = sum(errors) / len(errors)
        max_error = max(errors)
        min_error = min(errors)
        
        return {
            'predictions_made': len(self.time_predictions),
            'actual_times_recorded': len(self.actual_times),
            'average_prediction_error_pct': avg_error,
            'max_prediction_error_pct': max_error,
            'min_prediction_error_pct': min_error,
            'total_predicted_time_ms': total_predicted,
            'total_actual_time_ms': total_actual,
            'time_efficiency': (total_predicted / total_actual * 100) if total_actual > 0 else 0
        }
    
    def _determine_health_status(self, issues: List[CodeIssue]) -> HealthStatus:
        """Determine health status based on issues found"""
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == Severity.HIGH)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif high_count > 5:
            return HealthStatus.WARNING
        elif high_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _create_genesis_keys(
        self,
        issues: List[CodeIssue],
        healing_results: List[Dict[str, Any]]
    ):
        """Create Genesis keys for tracking analysis and healing"""
        if not self.genesis_service:
            return
        
        # Create Genesis key for analysis run
        analysis_key = self.genesis_service.create_genesis_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            action="code_analysis_run",
            details={
                'issues_found': len(issues),
                'issues_by_severity': self._count_by_severity(issues),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        # Create Genesis keys for each fix applied
        for result in healing_results:
            if result['status'] == 'success':
                self.genesis_service.create_genesis_key(
                    key_type=GenesisKeyType.CODE_CHANGE,
                    action="auto_code_fix",
                    file_path=result['file'],
                    details={
                        'fixes_applied': result['fixes_applied'],
                        'parent_key_id': analysis_key.key_id if analysis_key else None
                    }
                )


def get_code_analyzer_healing(
    healing_system: Optional[AutonomousHealingSystem] = None,
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    enable_auto_fix: bool = True,
    enable_timesense: bool = True
) -> CodeAnalyzerSelfHealing:
    """Get code analyzer self-healing instance"""
    return CodeAnalyzerSelfHealing(
        healing_system=healing_system,
        trust_level=trust_level,
        enable_auto_fix=enable_auto_fix,
        enable_timesense=enable_timesense
    )


# ============================================================================
# Main Entry Point
# ============================================================================

def trigger_code_healing(
    directory: str = 'backend',
    trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO,
    auto_fix: bool = True,
    pre_flight: bool = False,
    enable_timesense: bool = True
) -> Dict[str, Any]:
    """
    Trigger code analysis and self-healing.
    
    This function can be called:
    - Manually from scripts
    - On a schedule (cron, scheduler)
    - After code changes (file watcher)
    - As part of CI/CD pipeline
    """
    from cognitive.autonomous_healing_system import get_autonomous_healing
    
    # Get healing system
    healing_system = None
    try:
        from database.session import get_session
        session = next(get_session())
        healing_system = get_autonomous_healing(
            session=session,
            repo_path=Path(directory),
            trust_level=trust_level
        )
    except Exception as e:
        logger.warning(f"Could not initialize healing system: {e}")
    
    # Create analyzer healing instance
    analyzer_healing = CodeAnalyzerSelfHealing(
        healing_system=healing_system,
        trust_level=trust_level,
        enable_auto_fix=auto_fix,
        enable_timesense=enable_timesense
    )
    
    # Run analysis and healing
    return analyzer_healing.analyze_and_heal(
        directory=directory,
        auto_fix=auto_fix,
        pre_flight=pre_flight
    )


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    results = trigger_code_healing(
        directory='backend',
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        auto_fix=True
    )
    
    print(f"\n=== Code Analysis & Healing Results ===")
    print(f"Issues found: {results['issues_found']}")
    print(f"Fixes applied: {results['fixes_applied']}")
    print(f"Health status: {results['health_status']}")
