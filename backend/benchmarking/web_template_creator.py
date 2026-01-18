"""
Web Template Creator

Uses web search to find solutions and automatically create templates.
Integrates with existing web_knowledge system.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


class WebTemplateCreator:
    """Create templates from web search results."""
    
    def __init__(self):
        """Initialize web template creator."""
        self.created_templates = []
    
    def create_template_from_web_search(
        self,
        problem_text: str,
        search_query: str,
        web_results: List[Dict[str, Any]],
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create template from web search results.
        
        Args:
            problem_text: Problem description
            search_query: Query used for search
            web_results: Results from web_search tool
            test_cases: Test cases for context
            
        Returns:
            Template dictionary or None
        """
        # Extract code examples from web results
        code_examples = self._extract_code_from_results(web_results)
        
        if not code_examples:
            return None
        
        # Find best code example
        best_code = self._select_best_code(code_examples, problem_text, test_cases)
        
        if not best_code:
            return None
        
        # Extract function signature
        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', best_code)
        if not func_match:
            return None
        
        func_name = func_match.group(1)
        params = func_match.group(2)
        
        # Extract keywords from problem
        keywords = self._extract_keywords(problem_text)
        
        # Create template code with placeholder
        template_code = best_code.replace(f"def {func_name}(", "def {function_name}(")
        
        # Create template
        template = {
            "name": f"web_{func_name}",
            "pattern_keywords": keywords,
            "pattern_regex": "|".join(keywords[:3]) + ".*" if keywords else ".*",
            "template_code": template_code,
            "description": f"Web-sourced template from search: {search_query}",
            "examples": [problem_text[:100]],
            "source": "web_search",
            "search_query": search_query
        }
        
        self.created_templates.append(template)
        return template
    
    def _extract_code_from_results(self, web_results: List[Dict[str, Any]]) -> List[str]:
        """Extract code examples from web search results."""
        code_examples = []
        
        for result in web_results:
            # Extract content (format depends on web_search tool)
            content = result.get("content", "") or result.get("text", "") or result.get("snippet", "")
            
            if not content:
                continue
            
            # Find Python code blocks
            code_patterns = [
                r'```python\n(.*?)\n```',
                r'```\n(.*?)\n```',
                r'<code>(.*?)</code>',
                r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    code = match.strip()
                    if "def " in code and len(code) > 20:
                        code_examples.append(code)
        
        return code_examples
    
    def _select_best_code(
        self,
        code_examples: List[str],
        problem_text: str,
        test_cases: List[str] = None
    ) -> Optional[str]:
        """Select best code example based on problem context."""
        if not code_examples:
            return None
        
        # Score each example
        scored = []
        for code in code_examples:
            score = 0
            
            # Prefer longer, more complete code
            score += len(code) / 100
            
            # Prefer code with function definitions
            if "def " in code:
                score += 10
            
            # Prefer code that matches problem keywords
            problem_lower = problem_text.lower()
            code_lower = code.lower()
            
            if "list" in problem_lower and ("[" in code or "list" in code_lower):
                score += 5
            if "string" in problem_lower and ('"' in code or "'" in code):
                score += 5
            if "find" in problem_lower and "find" in code_lower:
                score += 5
            if "count" in problem_lower and "count" in code_lower:
                score += 5
            
            # Prefer code with return statements
            if "return " in code:
                score += 3
            
            scored.append((score, code))
        
        # Return highest scoring
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from problem text."""
        keywords = []
        text_lower = text.lower()
        
        # Operations
        ops = ["find", "count", "sort", "remove", "check", "get", "create", "generate"]
        for op in ops:
            if op in text_lower:
                keywords.append(op)
        
        # Data types
        types = ["list", "array", "string", "dict", "dictionary", "tuple", "set"]
        for t in types:
            if t in text_lower:
                keywords.append(t)
        
        return keywords[:10]  # Limit to top 10


def create_templates_from_web_search_results(
    problem_text: str,
    search_query: str,
    web_results: List[Dict[str, Any]],
    test_cases: List[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Main function to create template from web search.
    
    This should be called with web_search results.
    """
    creator = WebTemplateCreator()
    return creator.create_template_from_web_search(
        problem_text,
        search_query,
        web_results,
        test_cases
    )
