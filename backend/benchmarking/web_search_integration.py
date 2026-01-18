"""
Web Search Integration for Template Creation

Connects web_search tool to template generation system.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path


class WebSearchTemplateIntegration:
    """Integrate web search into template creation."""
    
    def __init__(self):
        """Initialize integration."""
        self.templates_created = []
    
    def search_and_create_template(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        web_search_func=None  # web_search tool function
    ) -> Optional[Dict[str, Any]]:
        """
        Search web and create template.
        
        Args:
            problem_text: Problem description
            test_cases: Test cases
            web_search_func: Function to call web_search tool
            
        Returns:
            Template dict or None
        """
        # Build query
        query = self._build_query(problem_text, test_cases)
        
        if not web_search_func:
            return None
        
        # Search web
        try:
            search_results = web_search_func(query)
            
            # Extract code from results
            code_examples = self._extract_code(search_results)
            
            if not code_examples:
                return None
            
            # Create template from best code
            template = self._create_template(
                code_examples[0],
                problem_text,
                query
            )
            
            if template:
                self.templates_created.append(template)
            
            return template
            
        except Exception as e:
            print(f"[WEB] Search failed: {e}")
            return None
    
    def _build_query(self, problem_text: str, test_cases: List[str] = None) -> str:
        """Build search query."""
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
        
        for word in ["find", "count", "sort", "remove", "check", "list", "string"]:
            if word in text_lower:
                keywords.append(word)
        
        # Build query
        query_parts = ["python"]
        if func_name:
            query_parts.append(func_name)
        query_parts.extend(keywords[:3])
        query_parts.append("example")
        
        return " ".join(query_parts)
    
    def _extract_code(self, search_results: Dict[str, Any]) -> List[str]:
        """Extract code from web search results."""
        code_blocks = []
        
        # Handle different result formats
        content = search_results.get("content", "") or search_results.get("text", "")
        
        if not content:
            return []
        
        # Find Python code
        patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                code = match.strip()
                if "def " in code and len(code) > 20:
                    code_blocks.append(code)
        
        return code_blocks
    
    def _create_template(
        self,
        code: str,
        problem_text: str,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Create template from code."""
        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        if not func_match:
            return None
        
        func_name = func_match.group(1)
        template_code = code.replace(f"def {func_name}(", "def {function_name}(")
        
        # Extract keywords
        keywords = []
        text_lower = problem_text.lower()
        for word in ["find", "count", "sort", "remove", "check", "list", "string"]:
            if word in text_lower:
                keywords.append(word)
        
        return {
            "name": f"web_{func_name}",
            "pattern_keywords": keywords,
            "pattern_regex": "|".join(keywords[:3]) + ".*" if keywords else ".*",
            "template_code": template_code,
            "description": f"Web-sourced: {query}",
            "examples": [problem_text[:100]],
            "source": "web_search"
        }
