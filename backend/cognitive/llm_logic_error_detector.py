"""
LLM-Powered Logic Error Detection and Fixing System

Uses LLM reasoning to detect and fix logic errors in code that static analysis
and pattern matching might miss.

Features:
- Semantic analysis of code logic
- Detection of logical inconsistencies
- Off-by-one errors, incorrect conditionals
- Variable misuse, type logic errors
- Integration with self-healing system
"""

import logging
import ast
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LogicError:
    """Represents a detected logic error."""
    error_type: str  # e.g., "off_by_one", "incorrect_conditional", "variable_misuse"
    severity: str  # "critical", "high", "medium", "low"
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    reasoning: str  # LLM's reasoning about the error
    suggested_fix: str
    confidence: float  # 0.0-1.0
    context_lines: List[str]  # Surrounding code context


class LLMLogicErrorDetector:
    """
    Uses LLM reasoning to detect logic errors in code.
    
    Analyzes code semantically to find:
    - Incorrect conditional logic
    - Off-by-one errors
    - Variable misuse
    - Type logic errors
    - Missing edge cases
    - Logical contradictions
    """

    def __init__(self, llm_service=None):
        """
        Initialize LLM Logic Error Detector.
        
        Args:
            llm_service: Optional LLM service instance
        """
        self.llm_service = llm_service
        if not self.llm_service:
            try:
                from llm_orchestrator.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning(f"Could not initialize LLM service: {e}")

    def detect_logic_errors(
        self,
        file_path: str,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[LogicError]:
        """
        Detect logic errors in a file using LLM reasoning.
        
        Args:
            file_path: Path to file to analyze
            code: Optional code content (if not provided, reads from file)
            context: Optional context (errors, recent changes, etc.)
            
        Returns:
            List of detected LogicError objects
        """
        if not code:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return []

        if not code or not self.llm_service:
            return []

        # Analyze code using LLM
        errors = []
        
        try:
            # Use LLM to analyze code for logic errors
            analysis = self._llm_analyze_logic(code, file_path, context)
            
            # Parse LLM response into LogicError objects
            errors = self._parse_llm_analysis(analysis, file_path, code)
            
            logger.info(
                f"[LOGIC-DETECTOR] Detected {len(errors)} logic errors in {file_path}"
            )
            
        except Exception as e:
            logger.error(f"[LOGIC-DETECTOR] Error analyzing {file_path}: {e}")
            
        return errors

    def _llm_analyze_logic(
        self,
        code: str,
        file_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Use LLM to analyze code for logic errors.
        
        Args:
            code: Code to analyze
            file_path: Path to file
            context: Optional context
            
        Returns:
            LLM analysis response
        """
        # Build prompt for logic error detection
        prompt = self._build_analysis_prompt(code, file_path, context)
        
        try:
            # Use LLM service to analyze
            response = self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more deterministic analysis
                system_prompt=self._get_system_prompt()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"[LOGIC-DETECTOR] LLM analysis failed: {e}")
            return ""

    def _build_analysis_prompt(
        self,
        code: str,
        file_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for LLM logic analysis."""
        
        context_str = ""
        if context:
            if "errors" in context:
                context_str += f"\nRecent errors: {context['errors']}\n"
            if "related_files" in context:
                context_str += f"\nRelated files: {context['related_files']}\n"
        
        prompt = f"""Analyze the following Python code for logic errors. Look for:

1. **Off-by-one errors**: Array indexing, loop boundaries, range issues
2. **Incorrect conditionals**: Wrong boolean logic, missing/incorrect operators
3. **Variable misuse**: Using wrong variable, uninitialized variables, scope issues
4. **Type logic errors**: Incorrect type assumptions, type-related logic bugs
5. **Missing edge cases**: Null checks, empty collections, boundary conditions
6. **Logical contradictions**: Code that contradicts itself or comments
7. **Control flow issues**: Infinite loops, unreachable code, missing returns
8. **State inconsistencies**: Variables that should be updated but aren't

File: {file_path}
{context_str}

Code to analyze:
```python
{code}
```

Provide your analysis in this JSON format:
{{
  "errors": [
    {{
      "error_type": "off_by_one|incorrect_conditional|variable_misuse|type_logic|missing_edge_case|logical_contradiction|control_flow|state_inconsistency",
      "severity": "critical|high|medium|low",
      "line_number": <int>,
      "description": "Clear description of the logic error",
      "code_snippet": "Relevant code snippet",
      "reasoning": "Your reasoning about why this is a logic error",
      "suggested_fix": "Corrected code",
      "confidence": 0.0-1.0
    }}
  ]
}}

Focus on actual logic errors, not style issues. Be specific and provide actionable fixes.
"""
        
        return prompt

    def _get_system_prompt(self) -> str:
        """Get system prompt for logic error detection."""
        return """You are an expert code reviewer specializing in logic error detection. 
You have deep understanding of common programming logic errors including off-by-one errors, 
incorrect conditionals, variable misuse, and edge cases. You analyze code carefully and 
provide specific, actionable fixes with clear reasoning."""
    
    def _parse_llm_analysis(
        self,
        analysis: str,
        file_path: str,
        code: str
    ) -> List[LogicError]:
        """
        Parse LLM analysis response into LogicError objects.
        
        Args:
            analysis: LLM response text
            file_path: File path
            code: Original code
            
        Returns:
            List of LogicError objects
        """
        errors = []
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', analysis, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group(0))
                
                for error_data in data.get("errors", []):
                    line_num = error_data.get("line_number", 0)
                    code_lines = code.split('\n')
                    context_lines = []
                    
                    # Get context around the error
                    start = max(0, line_num - 3)
                    end = min(len(code_lines), line_num + 2)
                    context_lines = code_lines[start:end]
                    
                    error = LogicError(
                        error_type=error_data.get("error_type", "unknown"),
                        severity=error_data.get("severity", "medium"),
                        file_path=file_path,
                        line_number=line_num,
                        description=error_data.get("description", ""),
                        code_snippet=error_data.get("code_snippet", ""),
                        reasoning=error_data.get("reasoning", ""),
                        suggested_fix=error_data.get("suggested_fix", ""),
                        confidence=error_data.get("confidence", 0.5),
                        context_lines=context_lines
                    )
                    errors.append(error)
                    
        except Exception as e:
            logger.warning(f"[LOGIC-DETECTOR] Failed to parse LLM response: {e}")
            # Fallback: Try to extract errors from natural language response
            errors = self._fallback_parse(analysis, file_path, code)
            
        return errors
    
    def _fallback_parse(
        self,
        analysis: str,
        file_path: str,
        code: str
    ) -> List[LogicError]:
        """Fallback parsing if JSON parsing fails."""
        errors = []
        
        # Simple pattern matching for common error mentions
        # This is a basic fallback - LLM should ideally return JSON
        error_patterns = [
            (r'off.?by.?one', 'off_by_one'),
            (r'conditional', 'incorrect_conditional'),
            (r'variable.*misuse', 'variable_misuse'),
            (r'edge.?case', 'missing_edge_case'),
        ]
        
        for pattern, error_type in error_patterns:
            if re.search(pattern, analysis, re.IGNORECASE):
                # Create a generic error entry
                error = LogicError(
                    error_type=error_type,
                    severity="medium",
                    file_path=file_path,
                    line_number=0,
                    description=f"Potential {error_type} detected by LLM analysis",
                    code_snippet="",
                    reasoning=analysis[:500],  # First 500 chars of analysis
                    suggested_fix="",
                    confidence=0.5,
                    context_lines=[]
                )
                errors.append(error)
                
        return errors

    def _apply_ast_based_fix(
        self,
        full_code: str,
        error: LogicError
    ) -> Tuple[str, bool]:
        """
        Apply AST-based fix for detected logic errors.
        
        Args:
            full_code: Full source code
            error: LogicError containing fix information
            
        Returns:
            Tuple of (fixed_code, success)
        """
        try:
            tree = ast.parse(full_code)
        except SyntaxError:
            return full_code, False
            
        lines = full_code.split('\n')
        line_idx = error.line_number - 1
        
        if not (0 <= line_idx < len(lines)):
            return full_code, False
            
        original_line = lines[line_idx]
        fixed_line = original_line
        error_type = error.error_type.lower()
        suggested = error.suggested_fix.lower()
        
        try:
            if error_type == "off_by_one" or "off-by-one" in suggested:
                fixed_line = self._fix_off_by_one(original_line)
                
            elif error_type == "incorrect_conditional" or "comparison" in suggested:
                fixed_line = self._fix_comparison(original_line, suggested)
                
            elif error_type == "boolean_logic" or any(x in suggested for x in ["and", "or", "not"]):
                fixed_line = self._fix_boolean_logic(original_line, suggested)
                
            elif error_type == "null_check" or "none" in suggested:
                fixed_line = self._fix_null_check(original_line)
                
            elif error_type == "type_error" or "type" in suggested:
                fixed_line = self._fix_type_error(original_line, suggested)
                
            else:
                fixed_line = self._apply_suggested_fix_heuristic(original_line, error.suggested_fix)
            
            if fixed_line != original_line:
                lines[line_idx] = fixed_line
                new_code = '\n'.join(lines)
                try:
                    ast.parse(new_code)
                    return new_code, True
                except SyntaxError:
                    return full_code, False
                    
        except Exception as e:
            logger.debug(f"[LOGIC-DETECTOR] AST fix failed: {e}")
            
        return full_code, False
    
    def _fix_off_by_one(self, line: str) -> str:
        """Fix off-by-one errors in loop bounds."""
        patterns = [
            (r'range\((\w+)\)', r'range(\1 + 1)'),
            (r'range\((\w+)\s*-\s*1\)', r'range(\1)'),
            (r'range\((\w+),\s*(\w+)\)', r'range(\1, \2 + 1)'),
            (r'<\s*len\(', r'<= len('),
            (r'<=\s*len\((\w+)\)\s*-\s*1', r'< len(\1)'),
            (r'\[\s*(\w+)\s*-\s*1\s*\]', r'[\1]'),
        ]
        result = line
        for pattern, replacement in patterns:
            new_result = re.sub(pattern, replacement, result)
            if new_result != result:
                return new_result
        return line
    
    def _fix_comparison(self, line: str, suggested: str) -> str:
        """Fix comparison operator errors."""
        operator_swaps = {
            '<': '<=',
            '<=': '<',
            '>': '>=',
            '>=': '>',
            '==': '!=',
            '!=': '==',
        }
        for op, swap in operator_swaps.items():
            if op in suggested and swap not in suggested:
                if f' {op} ' in line and f' {swap} ' not in line:
                    return line.replace(f' {op} ', f' {swap} ', 1)
        if '<' in suggested and '>' in line:
            return line.replace('>', '<', 1)
        elif '>' in suggested and '<' in line:
            return line.replace('<', '>', 1)
        return line
    
    def _fix_boolean_logic(self, line: str, suggested: str) -> str:
        """Fix boolean logic errors (and/or/not)."""
        if "and" in suggested and " or " in line.lower():
            return re.sub(r'\bor\b', 'and', line, flags=re.IGNORECASE)
        elif "or" in suggested and " and " in line.lower():
            return re.sub(r'\band\b', 'or', line, flags=re.IGNORECASE)
        if "not" in suggested:
            if " not " in line:
                return line.replace(" not ", " ", 1)
            else:
                match = re.search(r'if\s+(.+?):', line)
                if match:
                    condition = match.group(1)
                    return line.replace(condition, f"not ({condition})", 1)
        return line
    
    def _fix_null_check(self, line: str) -> str:
        """Add None checks."""
        match = re.search(r'(\w+)\.(\w+)', line)
        if match:
            var_name = match.group(0)
            indent = len(line) - len(line.lstrip())
            return ' ' * indent + f"if {match.group(1)} is not None:\n" + ' ' * (indent + 4) + line.lstrip()
        match = re.search(r'if\s+(.+?):', line)
        if match and 'None' not in line:
            condition = match.group(1)
            var_match = re.search(r'^(\w+)', condition)
            if var_match:
                var = var_match.group(1)
                new_condition = f"{var} is not None and {condition}"
                return line.replace(condition, new_condition, 1)
        return line
    
    def _fix_type_error(self, line: str, suggested: str) -> str:
        """Add type conversions."""
        type_patterns = [
            (r'int', r'(\w+)', r'int(\1)'),
            (r'str', r'(\w+)', r'str(\1)'),
            (r'float', r'(\w+)', r'float(\1)'),
            (r'list', r'(\w+)', r'list(\1)'),
        ]
        for type_name, var_pattern, replacement in type_patterns:
            if type_name in suggested.lower():
                match = re.search(r'=\s*(\w+)\s*$', line)
                if match:
                    var = match.group(1)
                    return line.replace(f'= {var}', f'= {type_name}({var})')
        return line
    
    def _apply_suggested_fix_heuristic(self, line: str, suggested_fix: str) -> str:
        """Apply suggested fix using heuristics when specific patterns don't match."""
        code_match = re.search(r'`([^`]+)`', suggested_fix)
        if code_match:
            suggested_code = code_match.group(1)
            if '->' in suggested_fix or 'to' in suggested_fix.lower():
                parts = re.split(r'\s*(?:->|to)\s*', suggested_fix, flags=re.IGNORECASE)
                if len(parts) >= 2:
                    old_match = re.search(r'`([^`]+)`', parts[0])
                    new_match = re.search(r'`([^`]+)`', parts[1])
                    if old_match and new_match:
                        old_code = old_match.group(1)
                        new_code = new_match.group(1)
                        if old_code in line:
                            return line.replace(old_code, new_code, 1)
        return line

    def generate_fix(
        self,
        error: LogicError,
        full_code: str
    ) -> Tuple[str, str]:
        """
        Generate a fix for a logic error using LLM.
        
        Args:
            error: LogicError to fix
            full_code: Full file code
            
        Returns:
            Tuple of (fixed_code, explanation)
        """
        if not self.llm_service:
            return full_code, "LLM service not available"
            
        prompt = f"""Fix the following logic error in the code:

Error Type: {error.error_type}
Severity: {error.severity}
Line: {error.line_number}
Description: {error.description}
Reasoning: {error.reasoning}

Current Code:
```python
{full_code}
```

Error Location (around line {error.line_number}):
```python
{chr(10).join(error.context_lines)}
```

Please provide:
1. The corrected code (full file with the fix applied)
2. A brief explanation of the fix

Format your response as:
FIXED_CODE:
```python
[corrected code here]
```

EXPLANATION:
[explanation here]
"""
        
        try:
            response = self.llm_service.generate(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.2,
                system_prompt="You are an expert at fixing logic errors in code. Provide clear, correct fixes with explanations."
            )
            
            # Extract fixed code
            fixed_code_match = re.search(
                r'FIXED_CODE:\s*```python\s*(.*?)```',
                response,
                re.DOTALL
            )
            explanation_match = re.search(
                r'EXPLANATION:\s*(.*?)(?:\n\n|\Z)',
                response,
                re.DOTALL
            )
            
            if fixed_code_match:
                fixed_code = fixed_code_match.group(1).strip()
                explanation = explanation_match.group(1).strip() if explanation_match else "Fix applied"
                return fixed_code, explanation
            else:
                # Fallback: try to use suggested_fix from error
                if error.suggested_fix:
                    fixed_code, success = self._apply_ast_based_fix(
                        full_code, error
                    )
                    if success:
                        explanation = f"Applied fix: {error.suggested_fix}"
                        return fixed_code, explanation
                        
        except Exception as e:
            logger.error(f"[LOGIC-DETECTOR] Error generating fix: {e}")
            
        return full_code, "Could not generate fix"

    def batch_detect(
        self,
        file_paths: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[LogicError]]:
        """
        Detect logic errors in multiple files.
        
        Args:
            file_paths: List of file paths to analyze
            context: Optional shared context
            
        Returns:
            Dictionary mapping file paths to lists of LogicError objects
        """
        results = {}
        
        for file_path in file_paths:
            try:
                errors = self.detect_logic_errors(file_path, context=context)
                results[file_path] = errors
            except Exception as e:
                logger.error(f"[LOGIC-DETECTOR] Error analyzing {file_path}: {e}")
                results[file_path] = []
                
        return results


def get_logic_error_detector(llm_service=None) -> LLMLogicErrorDetector:
    """Get or create LLM Logic Error Detector instance."""
    global _detector_instance
    
    if '_detector_instance' not in globals():
        _detector_instance = None
        
    if _detector_instance is None:
        _detector_instance = LLMLogicErrorDetector(llm_service=llm_service)
        
    return _detector_instance
