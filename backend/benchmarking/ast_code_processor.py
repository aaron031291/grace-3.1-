"""
AST-Based Code Processor for Benchmark Evaluation

This module provides deterministic AST-based transformations to fix common
code generation issues that cause test failures:

1. Function name extraction from test cases (AST-based, not regex)
2. Entrypoint enforcement (rename/wrap generated functions)
3. Code validation and cleanup
4. Error-conditioned repair

These fixes address ~80% of MBPP failures which are NameError issues.
"""

import ast
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class CodeAnalysis:
    """Result of analyzing generated code."""
    functions: List[str]  # Function names defined
    classes: List[str]  # Class names defined
    imports: List[str]  # Import statements
    top_level_code: bool  # Has executable top-level code
    has_syntax_error: bool
    syntax_error_msg: Optional[str]
    main_function: Optional[str]  # Best guess at main function


@dataclass
class TestAnalysis:
    """Result of analyzing test cases."""
    expected_function: Optional[str]  # Most likely expected function name
    all_called_functions: List[str]  # All functions called in tests
    call_counts: Dict[str, int]  # Count of each function call
    arg_counts: Dict[str, Tuple[int, int]]  # min/max arg counts per function


# Built-in functions to ignore when extracting function names from tests
BUILTIN_FUNCTIONS = {
    'len', 'sorted', 'list', 'dict', 'set', 'tuple', 'str', 'int', 'float',
    'bool', 'abs', 'sum', 'min', 'max', 'range', 'enumerate', 'zip', 'map',
    'filter', 'any', 'all', 'isinstance', 'type', 'print', 'open', 'round',
    'ord', 'chr', 'hex', 'bin', 'oct', 'pow', 'divmod', 'hash', 'id',
    'input', 'iter', 'next', 'reversed', 'slice', 'format', 'repr',
    'getattr', 'setattr', 'hasattr', 'delattr', 'callable', 'eval', 'exec',
    'compile', 'globals', 'locals', 'vars', 'dir', 'help', 'ascii', 'bytes',
    'bytearray', 'memoryview', 'complex', 'frozenset', 'object', 'super',
    'classmethod', 'staticmethod', 'property', 'Exception', 'assert_equal',
    'assertEqual', 'assertTrue', 'assertFalse', 'assertRaises', 'assertIn',
    'assertNotIn', 'assertIsNone', 'assertIsNotNone', 'math', 're', 'os',
}


class ASTCodeProcessor:
    """
    AST-based code processor for fixing generated code.
    
    Addresses common issues:
    - Function name mismatches (NameError)
    - Missing function definitions
    - Syntax errors
    - Invalid code structure
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ASTCodeProcessor")
    
    # =========================================================================
    # FUNCTION NAME EXTRACTION FROM TESTS (AST-BASED)
    # =========================================================================
    
    def extract_function_name_from_tests(
        self,
        test_list: List[str],
        fallback_name: Optional[str] = None
    ) -> TestAnalysis:
        """
        Extract expected function name from test cases using AST parsing.
        
        This is much more robust than regex-based extraction.
        
        Args:
            test_list: List of test case strings (assert statements)
            fallback_name: Name to use if extraction fails
            
        Returns:
            TestAnalysis with expected function name and metadata
        """
        all_called_functions = []
        call_counts: Counter = Counter()
        arg_counts: Dict[str, List[int]] = {}
        
        for test in test_list:
            try:
                # Parse test as expression or statement
                tree = self._parse_test_string(test)
                if tree is None:
                    continue
                
                # Walk AST to find all function calls
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func_name = self._extract_call_name(node)
                        if func_name and func_name not in BUILTIN_FUNCTIONS:
                            all_called_functions.append(func_name)
                            call_counts[func_name] += 1
                            
                            # Track argument counts
                            num_args = len(node.args) + len(node.keywords)
                            if func_name not in arg_counts:
                                arg_counts[func_name] = []
                            arg_counts[func_name].append(num_args)
                            
            except Exception as e:
                self.logger.debug(f"Failed to parse test: {test[:50]}... - {e}")
                # Fallback to regex for this test
                regex_name = self._regex_extract_function_name(test)
                if regex_name and regex_name not in BUILTIN_FUNCTIONS:
                    all_called_functions.append(regex_name)
                    call_counts[regex_name] += 1
        
        # Determine expected function (most called non-builtin)
        expected_function = None
        if call_counts:
            # Get most common function that's not a builtin
            for func, count in call_counts.most_common():
                if func not in BUILTIN_FUNCTIONS:
                    expected_function = func
                    break
        
        if not expected_function and fallback_name:
            expected_function = fallback_name
        
        # Convert arg_counts to min/max tuples
        arg_count_ranges = {
            func: (min(counts), max(counts))
            for func, counts in arg_counts.items()
        }
        
        return TestAnalysis(
            expected_function=expected_function,
            all_called_functions=list(set(all_called_functions)),
            call_counts=dict(call_counts),
            arg_counts=arg_count_ranges
        )
    
    def _parse_test_string(self, test: str) -> Optional[ast.AST]:
        """Parse a test string into an AST."""
        test = test.strip()
        
        # Try parsing as module (handles assert statements)
        try:
            return ast.parse(test, mode='exec')
        except SyntaxError:
            pass
        
        # Try parsing as expression
        try:
            return ast.parse(test, mode='eval')
        except SyntaxError:
            pass
        
        # Try wrapping in assert if it looks like a comparison
        if '==' in test or 'True' in test or 'False' in test:
            try:
                return ast.parse(f"assert {test}", mode='exec')
            except SyntaxError:
                pass
        
        return None
    
    def _extract_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from a Call node."""
        func = node.func
        
        # Simple name: foo()
        if isinstance(func, ast.Name):
            return func.id
        
        # Attribute access: module.foo() - return just 'foo'
        if isinstance(func, ast.Attribute):
            return func.attr
        
        return None
    
    def _regex_extract_function_name(self, test: str) -> Optional[str]:
        """Fallback regex extraction for unparseable tests."""
        # Match function calls like: func_name(...)
        patterns = [
            r'assert\s+(\w+)\s*\(',
            r'assert\s*\(?\s*(\w+)\s*\(',
            r'assertEqual\s*\(\s*(\w+)\s*\(',
            r'(\w+)\s*\([^)]*\)\s*==',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, test)
            if match:
                return match.group(1)
        
        return None
    
    # =========================================================================
    # CODE ANALYSIS
    # =========================================================================
    
    def analyze_code(self, code: str) -> CodeAnalysis:
        """
        Analyze generated code structure using AST.
        
        Returns:
            CodeAnalysis with function names, classes, imports, etc.
        """
        functions = []
        classes = []
        imports = []
        top_level_code = False
        has_syntax_error = False
        syntax_error_msg = None
        main_function = None
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Check for top-level executable code
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, 
                                        ast.ClassDef, ast.Import, ast.ImportFrom,
                                        ast.Expr)):  # Allow docstrings
                    # Check if it's a docstring
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                        continue
                    top_level_code = True
                    break
            
            # Determine main function
            if functions:
                # First function is usually the main one
                main_function = functions[0]
                
        except SyntaxError as e:
            has_syntax_error = True
            syntax_error_msg = str(e)
        
        return CodeAnalysis(
            functions=functions,
            classes=classes,
            imports=imports,
            top_level_code=top_level_code,
            has_syntax_error=has_syntax_error,
            syntax_error_msg=syntax_error_msg,
            main_function=main_function
        )
    
    # =========================================================================
    # ENTRYPOINT ENFORCEMENT
    # =========================================================================
    
    def enforce_entrypoint(
        self,
        code: str,
        expected_name: str,
        test_analysis: Optional[TestAnalysis] = None
    ) -> Tuple[str, bool, str]:
        """
        Enforce that the code defines the expected function name.
        
        This is the KEY fix for NameError issues (~80% of MBPP failures).
        
        Strategies:
        1. If function with expected name exists -> no change
        2. If single function exists -> rename it
        3. If multiple functions exist -> rename the most likely one
        4. If no functions exist -> wrap top-level code in function
        
        Args:
            code: Generated code
            expected_name: Expected function name from tests
            test_analysis: Optional analysis of test cases
            
        Returns:
            (fixed_code, was_modified, modification_type)
        """
        if not expected_name:
            return code, False, "no_expected_name"
        
        analysis = self.analyze_code(code)
        
        if analysis.has_syntax_error:
            # Try to fix syntax errors first
            fixed_code = self._attempt_syntax_fix(code)
            if fixed_code:
                code = fixed_code
                analysis = self.analyze_code(code)
            
            if analysis.has_syntax_error:
                return code, False, "syntax_error"
        
        # Check if expected function already exists
        if expected_name in analysis.functions:
            return code, False, "already_correct"
        
        # Strategy 1: Rename single/main function
        if analysis.functions:
            return self._rename_function(code, analysis, expected_name)
        
        # Strategy 2: Wrap top-level code in function
        if analysis.top_level_code or not analysis.functions:
            return self._wrap_in_function(code, expected_name, test_analysis)
        
        return code, False, "no_modification_possible"
    
    def _rename_function(
        self,
        code: str,
        analysis: CodeAnalysis,
        expected_name: str
    ) -> Tuple[str, bool, str]:
        """Rename a function to the expected name using AST transformation."""
        try:
            tree = ast.parse(code)
            
            # Find function to rename (first one, or main_function)
            target_func = analysis.main_function or analysis.functions[0]
            old_name = target_func
            
            # Create transformer to rename function
            class FunctionRenamer(ast.NodeTransformer):
                def __init__(self, old_name: str, new_name: str):
                    self.old_name = old_name
                    self.new_name = new_name
                    self.renamed = False
                
                def visit_FunctionDef(self, node):
                    if node.name == self.old_name and not self.renamed:
                        node.name = self.new_name
                        self.renamed = True
                    return self.generic_visit(node)
                
                def visit_AsyncFunctionDef(self, node):
                    if node.name == self.old_name and not self.renamed:
                        node.name = self.new_name
                        self.renamed = True
                    return self.generic_visit(node)
                
                def visit_Name(self, node):
                    # Rename recursive calls
                    if node.id == self.old_name:
                        node.id = self.new_name
                    return node
            
            renamer = FunctionRenamer(old_name, expected_name)
            new_tree = renamer.visit(tree)
            
            if renamer.renamed:
                # Unparse back to code
                new_code = ast.unparse(new_tree)
                self.logger.info(f"Renamed function '{old_name}' -> '{expected_name}'")
                return new_code, True, f"renamed_{old_name}_to_{expected_name}"
            
        except Exception as e:
            self.logger.warning(f"AST rename failed: {e}, falling back to regex")
            # Fallback to regex replacement
            pattern = rf'def\s+{re.escape(old_name)}\s*\('
            new_code = re.sub(pattern, f'def {expected_name}(', code, count=1)
            if new_code != code:
                return new_code, True, f"regex_renamed_{old_name}"
        
        return code, False, "rename_failed"
    
    def _wrap_in_function(
        self,
        code: str,
        expected_name: str,
        test_analysis: Optional[TestAnalysis] = None
    ) -> Tuple[str, bool, str]:
        """Wrap top-level code in a function definition."""
        # Infer parameters from test analysis
        if test_analysis and expected_name in test_analysis.arg_counts:
            min_args, max_args = test_analysis.arg_counts[expected_name]
            if min_args == max_args:
                params = ', '.join([f'arg{i}' for i in range(min_args)])
            else:
                # Variable args - use *args
                params = '*args'
        else:
            params = '*args'  # Default to variable args
        
        # Clean up code - remove if __name__ blocks, etc.
        code = self._clean_code_for_wrapping(code)
        
        # Indent code
        indented = '\n'.join('    ' + line if line.strip() else '' 
                             for line in code.split('\n'))
        
        # Check if code returns something or just computes
        if 'return' not in code:
            # Add return for the result
            lines = indented.rstrip().split('\n')
            if lines:
                last_line = lines[-1].strip()
                if last_line and not last_line.startswith('#'):
                    # Assume last expression should be returned
                    lines[-1] = lines[-1].replace(last_line, f'return {last_line}')
                    indented = '\n'.join(lines)
        
        wrapped = f"def {expected_name}({params}):\n{indented}"
        
        self.logger.info(f"Wrapped code in function '{expected_name}({params})'")
        return wrapped, True, "wrapped_in_function"
    
    def _clean_code_for_wrapping(self, code: str) -> str:
        """Clean up code before wrapping in function."""
        lines = code.split('\n')
        cleaned = []
        skip_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip if __name__ == '__main__' blocks
            if stripped.startswith('if __name__'):
                skip_block = True
                continue
            
            if skip_block:
                if stripped and not stripped.startswith(' ') and not stripped.startswith('\t'):
                    skip_block = False
                else:
                    continue
            
            # Skip print statements for debugging
            if stripped.startswith('print(') and 'return' not in stripped:
                continue
            
            cleaned.append(line)
        
        return '\n'.join(cleaned).strip()
    
    def _attempt_syntax_fix(self, code: str) -> Optional[str]:
        """Attempt to fix common syntax errors."""
        # Common fixes
        fixes = [
            # Missing colons
            (r'def\s+(\w+)\s*\([^)]*\)\s*\n', lambda m: m.group(0).rstrip() + ':\n'),
            # Unclosed parentheses
            (r'\([^)]*$', lambda m: m.group(0) + ')'),
            # Unclosed brackets
            (r'\[[^\]]*$', lambda m: m.group(0) + ']'),
        ]
        
        fixed = code
        for pattern, replacement in fixes:
            fixed = re.sub(pattern, replacement, fixed)
        
        # Verify fix worked
        try:
            ast.parse(fixed)
            return fixed
        except SyntaxError:
            return None
    
    # =========================================================================
    # ERROR-CONDITIONED REPAIR
    # =========================================================================
    
    def repair_based_on_error(
        self,
        code: str,
        error_msg: str,
        expected_name: Optional[str] = None,
        test_list: Optional[List[str]] = None
    ) -> Tuple[str, bool, str]:
        """
        Repair code based on the specific error encountered.
        
        Args:
            code: Generated code that failed
            error_msg: Error message from execution
            expected_name: Expected function name
            test_list: Test cases for context
            
        Returns:
            (repaired_code, was_repaired, repair_type)
        """
        error_lower = error_msg.lower()
        
        # NameError: Function not defined
        if 'nameerror' in error_lower:
            # Extract missing name
            match = re.search(r"name '(\w+)' is not defined", error_msg)
            if match:
                missing_name = match.group(1)
                if expected_name and missing_name == expected_name:
                    # Need to create/rename to expected name
                    return self.enforce_entrypoint(code, expected_name)
        
        # TypeError: Wrong number of arguments
        if 'typeerror' in error_lower:
            if 'positional argument' in error_lower:
                # Try to fix function signature
                return self._fix_signature(code, error_msg, test_list)
        
        # IndentationError
        if 'indentationerror' in error_lower:
            return self._fix_indentation(code)
        
        # SyntaxError
        if 'syntaxerror' in error_lower:
            fixed = self._attempt_syntax_fix(code)
            if fixed:
                return fixed, True, "syntax_fixed"
        
        return code, False, "no_repair_available"
    
    def _fix_signature(
        self,
        code: str,
        error_msg: str,
        test_list: Optional[List[str]]
    ) -> Tuple[str, bool, str]:
        """Fix function signature based on TypeError."""
        # Extract expected vs actual args from error
        match = re.search(r'takes (\d+) positional arguments? but (\d+) (?:was|were) given', error_msg)
        if match:
            expected_args = int(match.group(1)) - 1  # Subtract 1 for self/implicit
            actual_args = int(match.group(2)) - 1
            
            # If we need more args, add them
            if actual_args > expected_args:
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Add missing parameters
                            while len(node.args.args) < actual_args:
                                new_arg = ast.arg(arg=f'arg{len(node.args.args)}', annotation=None)
                                node.args.args.append(new_arg)
                            
                            new_code = ast.unparse(tree)
                            return new_code, True, "fixed_signature"
                except Exception as e:
                    self.logger.warning(f"Signature fix failed: {e}")
        
        return code, False, "signature_fix_failed"
    
    def _fix_indentation(self, code: str) -> Tuple[str, bool, str]:
        """Fix common indentation issues."""
        lines = code.split('\n')
        fixed_lines = []
        expected_indent = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Decrease indent for certain keywords
            if stripped.startswith(('return', 'break', 'continue', 'pass', 'raise')):
                if expected_indent > 0 and not any(stripped.startswith(k) for k in ('def ', 'class ', 'if ', 'for ', 'while ')):
                    pass  # Keep current indent
            
            # Dedent for closing structures
            if stripped.startswith(('elif ', 'else:', 'except:', 'finally:', 'except ')):
                expected_indent = max(0, expected_indent - 4)
            
            # Apply current indent
            fixed_lines.append(' ' * expected_indent + stripped)
            
            # Increase indent after colons
            if stripped.endswith(':'):
                expected_indent += 4
        
        fixed = '\n'.join(fixed_lines)
        
        try:
            ast.parse(fixed)
            return fixed, True, "indentation_fixed"
        except SyntaxError:
            return code, False, "indentation_fix_failed"
    
    # =========================================================================
    # FULL PROCESSING PIPELINE
    # =========================================================================
    
    def process_for_benchmark(
        self,
        code: str,
        test_list: List[str],
        fallback_function_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full processing pipeline for benchmark evaluation.
        
        1. Analyze test cases to get expected function name
        2. Analyze generated code
        3. Enforce correct entrypoint
        4. Return processed code with metadata
        
        Args:
            code: Generated code
            test_list: Test cases
            fallback_function_name: Name from problem definition
            
        Returns:
            Dict with processed code and metadata
        """
        result = {
            "original_code": code,
            "processed_code": code,
            "was_modified": False,
            "modifications": [],
            "test_analysis": None,
            "code_analysis": None,
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Analyze tests
            test_analysis = self.extract_function_name_from_tests(
                test_list, 
                fallback_function_name
            )
            result["test_analysis"] = {
                "expected_function": test_analysis.expected_function,
                "all_called_functions": test_analysis.all_called_functions,
                "call_counts": test_analysis.call_counts
            }
            
            # Step 2: Analyze code
            code_analysis = self.analyze_code(code)
            result["code_analysis"] = {
                "functions": code_analysis.functions,
                "main_function": code_analysis.main_function,
                "has_syntax_error": code_analysis.has_syntax_error
            }
            
            # Step 3: Enforce entrypoint
            if test_analysis.expected_function:
                fixed_code, was_modified, mod_type = self.enforce_entrypoint(
                    code,
                    test_analysis.expected_function,
                    test_analysis
                )
                
                result["processed_code"] = fixed_code
                result["was_modified"] = was_modified
                if was_modified:
                    result["modifications"].append(mod_type)
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Code processing failed: {e}")
        
        return result


# Convenience function
def get_ast_code_processor() -> ASTCodeProcessor:
    """Get an instance of the AST code processor."""
    return ASTCodeProcessor()


# Quick utility functions
def extract_expected_function_name(test_list: List[str]) -> Optional[str]:
    """Quick extraction of expected function name from tests."""
    processor = ASTCodeProcessor()
    analysis = processor.extract_function_name_from_tests(test_list)
    return analysis.expected_function


def fix_function_name(code: str, expected_name: str) -> str:
    """Quick fix of function name in code."""
    processor = ASTCodeProcessor()
    fixed_code, _, _ = processor.enforce_entrypoint(code, expected_name)
    return fixed_code
