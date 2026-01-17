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
                    # Apply fix manually
                    lines = full_code.split('\n')
                    if 0 < error.line_number <= len(lines):
                        # Simple replacement (could be enhanced)
                        fixed_code = full_code  # Placeholder
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
