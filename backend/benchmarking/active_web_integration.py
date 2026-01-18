"""
Active Web Integration for Templates

Uses existing WebKnowledgeIntegration to search web and create templates.
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


class ActiveWebTemplateIntegration:
    """Active web search integration using WebKnowledgeIntegration."""
    
    def __init__(self, web_knowledge_service=None):
        """
        Initialize with web knowledge service.
        
        Args:
            web_knowledge_service: WebKnowledgeIntegration instance
        """
        self.web_knowledge = web_knowledge_service
        self.templates_created = []
    
    async def search_and_create_template_async(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search web and create template (async).
        
        Args:
            problem_text: Problem description
            test_cases: Test cases
            
        Returns:
            Template dict or None
        """
        if not self.web_knowledge:
            return None
        
        # Build query
        query = self._build_query(problem_text, test_cases)
        
        try:
            # Search web using existing service
            from backend.oracle_intelligence.web_knowledge import KnowledgeSource
            
            results = await self.web_knowledge.search(
                query=query,
                sources=[KnowledgeSource.STACKOVERFLOW, KnowledgeSource.GITHUB],
                limit=3
            )
            
            if not results:
                return None
            
            # Extract code from results
            code_examples = []
            for result in results:
                code_examples.extend(result.code_examples)
                # Also extract from content
                code_examples.extend(self._extract_code_from_text(result.content))
            
            if not code_examples:
                return None
            
            # Create template from best code
            best_code = self._select_best_code(code_examples, problem_text)
            if not best_code:
                return None
            
            template = self._create_template(best_code, problem_text, query)
            
            if template:
                self.templates_created.append(template)
            
            return template
            
        except Exception as e:
            print(f"[WEB] Search failed: {e}")
            return None
    
    def search_and_create_template_sync(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Synchronous wrapper for async search.
        
        Args:
            problem_text: Problem description
            test_cases: Test cases
            
        Returns:
            Template dict or None
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.search_and_create_template_async(problem_text, test_cases)
                    )
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(
                    self.search_and_create_template_async(problem_text, test_cases)
                )
        except Exception as e:
            print(f"[WEB] Sync wrapper failed: {e}")
            return None
    
    def _build_query(self, problem_text: str, test_cases: List[str] = None) -> str:
        """Build search query."""
        func_name = None
        if test_cases:
            for test in test_cases:
                match = re.search(r'(\w+)\s*\(', test)
                if match:
                    func_name = match.group(1)
                    break
        
        keywords = []
        text_lower = problem_text.lower()
        for word in ["find", "count", "sort", "remove", "check", "list", "string", "maximum", "minimum"]:
            if word in text_lower:
                keywords.append(word)
        
        query_parts = ["python"]
        if func_name:
            query_parts.append(func_name)
        query_parts.extend(keywords[:3])
        query_parts.append("example")
        
        return " ".join(query_parts)
    
    def _extract_code_from_text(self, text: str) -> List[str]:
        """Extract code from text content."""
        code_blocks = []
        
        patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                code = match.strip()
                if "def " in code and len(code) > 20:
                    code_blocks.append(code)
        
        return code_blocks
    
    def _select_best_code(self, code_examples: List[str], problem_text: str) -> Optional[str]:
        """Select best code example."""
        if not code_examples:
            return None
        
        scored = []
        problem_lower = problem_text.lower()
        
        for code in code_examples:
            score = len(code) / 100  # Prefer longer code
            
            code_lower = code.lower()
            if "def " in code:
                score += 10
            if "return " in code:
                score += 3
            
            # Match keywords
            for word in ["find", "count", "sort", "list", "string"]:
                if word in problem_lower and word in code_lower:
                    score += 5
            
            scored.append((score, code))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None
    
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
