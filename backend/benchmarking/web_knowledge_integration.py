"""
Web Knowledge Integration

Searches the web for solutions, patterns, and best practices,
then integrates that knowledge into templates and learning memory.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


class WebKnowledgeIntegrator:
    """Integrate web knowledge into templates and learning."""
    
    def __init__(self):
        """Initialize web knowledge integrator."""
        self.web_search_cache = {}
        
    def search_for_solution_pattern(
        self,
        problem_text: str,
        error_message: str = None,
        test_cases: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search web for solution patterns to a problem.
        
        Args:
            problem_text: Problem description
            error_message: Error if this is a failure
            test_cases: Test cases for context
            
        Returns:
            Dictionary with web knowledge
        """
        # Build search query from problem
        query = self._build_search_query(problem_text, error_message, test_cases)
        
        # Search web (using web_search tool)
        # Note: This will be called from context where web_search is available
        web_results = {
            "query": query,
            "results": [],
            "patterns": [],
            "code_examples": []
        }
        
        return web_results
    
    def _build_search_query(
        self,
        problem_text: str,
        error_message: str = None,
        test_cases: List[str] = None
    ) -> str:
        """Build search query from problem context."""
        # Extract key terms
        keywords = self._extract_keywords(problem_text)
        
        # Add error context if available
        if error_message:
            error_keywords = self._extract_error_keywords(error_message)
            keywords.extend(error_keywords)
        
        # Add test case patterns
        if test_cases:
            test_keywords = self._extract_test_keywords(test_cases)
            keywords.extend(test_keywords)
        
        # Build query: "python function [keywords] solution"
        query = f"python function {' '.join(keywords[:5])} solution"
        
        return query
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from problem text."""
        # Common programming keywords
        keywords = []
        text_lower = text.lower()
        
        # Function operations
        if "find" in text_lower:
            keywords.append("find")
        if "count" in text_lower:
            keywords.append("count")
        if "sort" in text_lower:
            keywords.append("sort")
        if "remove" in text_lower:
            keywords.append("remove")
        if "check" in text_lower:
            keywords.append("check")
        
        # Data types
        if "list" in text_lower or "array" in text_lower:
            keywords.append("list")
        if "string" in text_lower or "str" in text_lower:
            keywords.append("string")
        if "dictionary" in text_lower or "dict" in text_lower:
            keywords.append("dictionary")
        
        return keywords
    
    def _extract_error_keywords(self, error: str) -> List[str]:
        """Extract keywords from error message."""
        keywords = []
        error_lower = error.lower()
        
        if "assertion" in error_lower:
            keywords.append("assertion")
        if "typeerror" in error_lower:
            keywords.append("type")
        if "nameerror" in error_lower:
            keywords.append("name")
        
        return keywords
    
    def _extract_test_keywords(self, test_cases: List[str]) -> List[str]:
        """Extract keywords from test cases."""
        keywords = []
        test_text = " ".join(test_cases).lower()
        
        # Look for data structures
        if "[" in test_text and "]" in test_text:
            keywords.append("list")
        if '"' in test_text or "'" in test_text:
            keywords.append("string")
        if "assert" in test_text:
            keywords.append("assertion")
        
        return keywords
    
    def extract_code_from_web_results(
        self,
        web_results: Dict[str, Any]
    ) -> List[str]:
        """Extract code examples from web search results."""
        code_examples = []
        
        # Extract code blocks from results
        for result in web_results.get("results", []):
            content = result.get("content", "")
            
            # Find code blocks
            code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
            code_blocks.extend(re.findall(r'```\n(.*?)\n```', content, re.DOTALL))
            
            for code in code_blocks:
                # Clean and validate code
                code = code.strip()
                if "def " in code and len(code) > 20:
                    code_examples.append(code)
        
        return code_examples
    
    def create_template_from_web_knowledge(
        self,
        problem_text: str,
        web_results: Dict[str, Any],
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create template from web knowledge."""
        code_examples = self.extract_code_from_web_results(web_results)
        
        if not code_examples:
            return None
        
        # Use best code example (most complete)
        best_code = max(code_examples, key=len)
        
        # Extract function signature
        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', best_code)
        if not func_match:
            return None
        
        func_name = func_match.group(1)
        params = func_match.group(2)
        
        # Extract keywords
        keywords = self._extract_keywords(problem_text)
        
        # Create template
        template = {
            "name": f"web_{func_name}",
            "pattern_keywords": keywords,
            "pattern_regex": "|".join(keywords[:3]) + ".*",
            "template_code": best_code.replace(func_name, "{function_name}"),
            "description": f"Web-sourced template from online solutions",
            "examples": [problem_text[:100]],
            "source": "web_search"
        }
        
        return template
    
    def enhance_template_with_web_knowledge(
        self,
        template_code: str,
        problem_text: str,
        web_results: Dict[str, Any]
    ) -> str:
        """Enhance existing template with web knowledge."""
        code_examples = self.extract_code_from_web_results(web_results)
        
        if not code_examples:
            return template_code
        
        # Find similar patterns in web examples
        # Use best matching example to enhance template
        best_example = max(code_examples, key=lambda x: self._similarity_score(x, template_code))
        
        # Merge patterns (simplified - could be more sophisticated)
        enhanced = template_code
        
        # Add imports if found in web examples
        if "import " in best_example and "import " not in enhanced:
            import_line = re.search(r'import\s+[\w\s,]+', best_example)
            if import_line:
                enhanced = import_line.group(0) + "\n" + enhanced
        
        return enhanced


def integrate_web_knowledge_into_templates(
    problem_text: str,
    error_message: str = None,
    test_cases: List[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Search web and integrate knowledge into templates.
    
    This function should be called when:
    - Template matching fails
    - Template generates code that fails tests
    - New problem patterns are encountered
    """
    integrator = WebKnowledgeIntegrator()
    
    # Search web for solution
    web_results = integrator.search_for_solution_pattern(
        problem_text,
        error_message,
        test_cases
    )
    
    # Create template from web knowledge
    template = integrator.create_template_from_web_knowledge(
        problem_text,
        web_results,
        test_cases
    )
    
    return template
