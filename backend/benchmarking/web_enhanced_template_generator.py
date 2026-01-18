"""
Web-Enhanced Template Generator

Uses web search to find solutions and patterns, then integrates
them into templates automatically.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


class WebEnhancedTemplateGenerator:
    """Generate templates using web knowledge."""
    
    def __init__(self):
        """Initialize web-enhanced generator."""
        self.cache = {}
    
    def search_and_create_template(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        error_message: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search web and create template from results.
        
        This function uses web_search tool (available in context).
        """
        # Build search query
        query = self._build_web_query(problem_text, test_cases, error_message)
        
        # Search web (this will be called with web_search available)
        # For now, return structure - actual search happens in integration
        
        template_suggestion = {
            "query": query,
            "problem": problem_text,
            "test_cases": test_cases,
            "error": error_message,
            "sources": [
                "stackoverflow.com",
                "github.com",
                "geeksforgeeks.org",
                "programiz.com",
                "w3schools.com"
            ]
        }
        
        return template_suggestion
    
    def _build_web_query(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        error_message: str = None
    ) -> str:
        """Build optimized web search query."""
        # Extract function name from test cases
        func_name = None
        if test_cases:
            for test in test_cases:
                match = re.search(r'(\w+)\s*\(', test)
                if match:
                    func_name = match.group(1)
                    break
        
        # Extract keywords
        keywords = []
        text_lower = problem_text.lower()
        
        # Operations
        if "find" in text_lower:
            keywords.append("find")
        if "count" in text_lower:
            keywords.append("count")
        if "sort" in text_lower:
            keywords.append("sort")
        if "remove" in text_lower:
            keywords.append("remove")
        
        # Data types
        if "list" in text_lower:
            keywords.append("list")
        if "string" in text_lower:
            keywords.append("string")
        
        # Build query: "python [function_name] [keywords] example"
        query_parts = ["python"]
        if func_name:
            query_parts.append(func_name)
        query_parts.extend(keywords[:3])
        query_parts.append("example")
        
        query = " ".join(query_parts)
        
        # Add error context if available
        if error_message:
            if "assertion" in error_message.lower():
                query += " assertion error"
            if "typeerror" in error_message.lower():
                query += " type error"
        
        return query
    
    def extract_code_from_web_content(self, web_content: str) -> List[str]:
        """Extract code examples from web content."""
        code_examples = []
        
        # Find Python code blocks
        patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'<code>(.*?)</code>',
            r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, web_content, re.DOTALL)
            for match in matches:
                code = match.strip()
                if "def " in code and len(code) > 20:
                    code_examples.append(code)
        
        return code_examples
    
    def create_template_from_web_code(
        self,
        code: str,
        problem_text: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """Create template structure from web-sourced code."""
        # Extract function signature
        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        if not func_match:
            return None
        
        func_name = func_match.group(1)
        params = func_match.group(2)
        
        # Replace function name with placeholder
        template_code = code.replace(f"def {func_name}(", "def {function_name}(")
        
        # Replace params if needed
        if params and "{params}" not in template_code:
            template_code = template_code.replace(f"({params})", "({params})")
        
        template = {
            "name": f"web_{func_name}",
            "pattern_keywords": keywords,
            "pattern_regex": "|".join(keywords[:3]) + ".*",
            "template_code": template_code,
            "description": f"Web-sourced from online solutions",
            "examples": [problem_text[:100]],
            "source": "web_search"
        }
        
        return template


def search_web_for_solution(
    problem_text: str,
    test_cases: List[str] = None,
    error_message: str = None
) -> Optional[Dict[str, Any]]:
    """
    Search web for solution to problem.
    
    This is the main entry point - should be called with web_search available.
    """
    generator = WebEnhancedTemplateGenerator()
    
    # Build query
    query = generator._build_web_query(problem_text, test_cases, error_message)
    
    # Return query structure (actual search happens in integration layer)
    return {
        "query": query,
        "problem": problem_text,
        "ready_for_search": True
    }
