"""
Template-LLM Collaboration System

Templates and LLM work together:
1. Template provides structure/skeleton
2. LLM fills in details/adapts to problem
3. Best of both worlds: structure + intelligence
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


class TemplateLLMCollaborator:
    """Collaborative system where templates and LLM work together."""
    
    def __init__(self, coding_agent=None):
        """
        Initialize collaborator.
        
        Args:
            coding_agent: EnterpriseCodingAgent instance
        """
        self.coding_agent = coding_agent
    
    def generate_with_template_guidance(
        self,
        problem_text: str,
        function_name: str,
        test_cases: List[str] = None,
        template=None
    ) -> Optional[str]:
        """
        Generate code using template as guidance for LLM.
        
        Args:
            problem_text: Problem description
            function_name: Function name
            test_cases: Test cases
            template: MBPPTemplate instance (optional)
            
        Returns:
            Generated code or None
        """
        # Step 1: Find matching template
        if not template:
            from backend.benchmarking.mbpp_templates import get_template_matcher
            matcher = get_template_matcher()
            match_result = matcher.find_best_match(problem_text, test_cases, function_name)
            if match_result:
                template, confidence = match_result
            else:
                return None
        
        # Step 2: Extract template structure
        template_code = template.template_code
        
        # Step 3: Create enhanced prompt with template guidance
        enhanced_prompt = self._create_collaborative_prompt(
            problem_text=problem_text,
            function_name=function_name,
            test_cases=test_cases,
            template_code=template_code,
            template_name=template.name
        )
        
        # Step 4: Use LLM to complete/adapt template
        if not self.coding_agent:
            return None
        
        try:
            from backend.cognitive.enterprise_coding_agent import CodingTaskType
            
            task = self.coding_agent.create_task(
                task_type=CodingTaskType.CODE_GENERATION,
                description=enhanced_prompt
            )
            
            execution_result = self.coding_agent.execute_task(task.task_id)
            
            if execution_result.get("success"):
                generation = execution_result.get("result", {}).get("generation")
                if generation:
                    if hasattr(generation, 'code_after'):
                        code = generation.code_after
                    elif hasattr(generation, 'code'):
                        code = generation.code
                    elif isinstance(generation, dict):
                        code = generation.get('code', '') or generation.get('code_after', '')
                    else:
                        code = str(generation)
                    
                    # Step 5: Merge template structure with LLM output
                    final_code = self._merge_template_and_llm(template_code, code, function_name)
                    return final_code
        except Exception as e:
            print(f"[COLLAB] LLM collaboration failed: {e}")
            return None
        
        return None
    
    def _create_collaborative_prompt(
        self,
        problem_text: str,
        function_name: str,
        test_cases: List[str] = None,
        template_code: str = None,
        template_name: str = None
    ) -> str:
        """Create prompt that guides LLM using template."""
        prompt_parts = []
        
        prompt_parts.append("You are a Python code generation assistant.")
        prompt_parts.append("A template has been found that matches this problem pattern.")
        prompt_parts.append("Use the template as a GUIDE, but adapt it to solve the specific problem.")
        prompt_parts.append("")
        
        prompt_parts.append("PROBLEM:")
        prompt_parts.append(problem_text)
        prompt_parts.append("")
        
        if test_cases:
            prompt_parts.append("TEST CASES:")
            for test in test_cases[:3]:  # First 3 test cases
                prompt_parts.append(f"  {test}")
            prompt_parts.append("")
        
        prompt_parts.append("TEMPLATE PATTERN (use as guidance):")
        prompt_parts.append("```python")
        prompt_parts.append(template_code)
        prompt_parts.append("```")
        prompt_parts.append("")
        
        prompt_parts.append("INSTRUCTIONS:")
        prompt_parts.append("1. Use the template structure as a starting point")
        prompt_parts.append("2. Replace {function_name} with the actual function name")
        prompt_parts.append("3. Replace {params} with the correct parameters")
        prompt_parts.append("4. Adapt the logic to match the problem requirements")
        prompt_parts.append("5. Ensure the code passes all test cases")
        prompt_parts.append("6. Keep the template's general approach but customize details")
        prompt_parts.append("")
        
        prompt_parts.append("Generate the complete Python function:")
        
        return "\n".join(prompt_parts)
    
    def _merge_template_and_llm(
        self,
        template_code: str,
        llm_code: str,
        function_name: str
    ) -> str:
        """Merge template structure with LLM output."""
        # Extract function from LLM output
        func_match = re.search(r'def\s+(\w+)\s*\([^)]*\):.*', llm_code, re.DOTALL)
        if func_match:
            llm_function = func_match.group(0)
            
            # Replace placeholders in template if LLM didn't handle them
            merged = template_code.replace("{function_name}", function_name)
            # Also replace "def to(" which is used as placeholder in templates
            merged = re.sub(r'def\s+to\s*\(', f'def {function_name}(', merged)
            
            # If LLM generated complete function, prefer it but keep template structure hints
            # Check if LLM code is more complete
            if len(llm_function) > len(merged) * 0.8:  # LLM generated substantial code
                # Fix function name in LLM output too
                fixed_llm = re.sub(
                    r'def\s+(\w+)\s*\(',
                    f'def {function_name}(',
                    llm_function,
                    count=1
                )
                return fixed_llm
            else:
                # Use template structure, fill with LLM details
                return merged
        
        # Fallback: use template with placeholders replaced
        result = template_code.replace("{function_name}", function_name)
        # Also replace "def to(" placeholder
        result = re.sub(r'def\s+to\s*\(', f'def {function_name}(', result)
        return result
    
    def generate_hybrid(
        self,
        problem_text: str,
        function_name: str,
        test_cases: List[str] = None
    ) -> Optional[str]:
        """
        Hybrid approach: Try template first, enhance with LLM.
        
        Returns:
            Generated code or None
        """
        from backend.benchmarking.mbpp_templates import get_template_matcher
        
        matcher = get_template_matcher()
        
        # Step 1: Try pure template generation
        template_code = matcher.generate_from_template(
            problem_text=problem_text,
            function_name=function_name,
            test_cases=test_cases
        )
        
        if template_code and "{function_name}" not in template_code and "{params}" not in template_code:
            # Template generated complete code, use it
            # But fix "def to(" placeholder if present
            if function_name:
                template_code = re.sub(r'def\s+to\s*\(', f'def {function_name}(', template_code)
            return template_code
        
        # Step 2: Template has placeholders or incomplete, use LLM to complete
        match_result = matcher.find_best_match(problem_text, test_cases, function_name)
        if match_result:
            template, confidence = match_result
            return self.generate_with_template_guidance(
                problem_text=problem_text,
                function_name=function_name,
                test_cases=test_cases,
                template=template
            )
        
        # Step 3: No template match, use pure LLM
        if self.coding_agent:
            try:
                from backend.cognitive.enterprise_coding_agent import CodingTaskType
                
                task = self.coding_agent.create_task(
                    task_type=CodingTaskType.CODE_GENERATION,
                    description=problem_text
                )
                
                execution_result = self.coding_agent.execute_task(task.task_id)
                
                if execution_result.get("success"):
                    generation = execution_result.get("result", {}).get("generation")
                    if generation:
                        if hasattr(generation, 'code_after'):
                            return generation.code_after
                        elif hasattr(generation, 'code'):
                            return generation.code
                        elif isinstance(generation, dict):
                            return generation.get('code', '') or generation.get('code_after', '')
                        else:
                            return str(generation)
            except Exception as e:
                print(f"[COLLAB] Pure LLM fallback failed: {e}")
        
        return None
