"""
Fix Function Name Extraction from LLM Code

Extracts correct function name from LLM-generated code and fixes "def to()" issues.
"""

import re
from typing import Optional


def extract_function_name_from_code(code: str) -> Optional[str]:
    """Extract function name from code."""
    if not code:
        return None
    
    # Find first function definition
    match = re.search(r'def\s+(\w+)\s*\(', code)
    if match:
        return match.group(1)
    
    return None


def fix_function_name_in_code(
    code: str,
    correct_function_name: str
) -> str:
    """
    Fix function name in code.
    
    Replaces ANY incorrect function name with correct function name.
    Handles: "def to(", "def solve_task(", or any other wrong name.
    """
    if not code or not correct_function_name:
        return code
    
    # Find the first function definition
    func_match = re.search(r'def\s+(\w+)\s*\(', code)
    if func_match:
        current_name = func_match.group(1)
        # If function name is wrong, replace it
        if current_name != correct_function_name:
            # Replace the function definition
            fixed = re.sub(
                r'def\s+' + re.escape(current_name) + r'\s*\(',
                f'def {correct_function_name}(',
                code,
                count=1  # Only replace first occurrence
            )
            return fixed
    
    # Also handle common wrong names explicitly
    wrong_names = ['to', 'solve_task', 'solution', 'answer', 'function']
    for wrong_name in wrong_names:
        if wrong_name != correct_function_name:
            code = re.sub(
                r'def\s+' + re.escape(wrong_name) + r'\s*\(',
                f'def {correct_function_name}(',
                code,
                count=1
            )
    
    return code


def extract_and_fix_code(
    llm_output: str,
    function_name: str,
    problem_text: str = None
) -> str:
    """
    Extract code from LLM output and fix function name.
    
    Args:
        llm_output: Raw LLM output (may contain markdown, explanations, etc.)
        function_name: Correct function name
        problem_text: Problem description (for context)
        
    Returns:
        Fixed code with correct function name
    """
    if not llm_output:
        return ""
    
    # Extract code block if in markdown
    code = llm_output
    
    # Try to find Python code block
    code_block_match = re.search(r'```python\n(.*?)\n```', code, re.DOTALL)
    if code_block_match:
        code = code_block_match.group(1)
    else:
        # Try without language tag
        code_block_match = re.search(r'```\n(.*?)\n```', code, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1)
    
    # Extract function definition
    func_match = re.search(r'def\s+\w+\s*\([^)]*\):.*', code, re.DOTALL)
    if func_match:
        code = func_match.group(0)
    
    # Fix function name
    code = fix_function_name_in_code(code, function_name)
    
    return code.strip()
