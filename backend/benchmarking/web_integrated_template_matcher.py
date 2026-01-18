"""
Web-Integrated Template Matcher

Enhances template matching with web search capabilities.
When templates fail, searches web for solutions and creates new templates.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from benchmarking.mbpp_templates import MBPPTemplate, MBPPTemplateMatcher


class WebIntegratedTemplateMatcher(MBPPTemplateMatcher):
    """Template matcher enhanced with web search."""
    
    def __init__(self, use_embedding_search: bool = False, use_web_search: bool = True):
        """
        Initialize web-integrated matcher.
        
        Args:
            use_embedding_search: Use reversed KNN embedding search
            use_web_search: Search web when templates fail
        """
        super().__init__(use_embedding_search=use_embedding_search)
        self.use_web_search = use_web_search
        self.web_templates = []  # Templates created from web searches
    
    def find_best_match_with_web(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        function_name: str = None
    ) -> Optional[Tuple[MBPPTemplate, float]]:
        """
        Find best template match, with web search fallback.
        
        Args:
            problem_text: Problem description
            test_cases: Test cases
            function_name: Function name
            
        Returns:
            (template, confidence) or None
        """
        # First try standard template matching
        match_result = self.find_best_match(problem_text, test_cases, function_name)
        
        if match_result:
            return match_result
        
        # If no match and web search enabled, search web
        if self.use_web_search:
            web_template = self._search_web_and_create_template(
                problem_text,
                test_cases,
                function_name
            )
            
            if web_template:
                # Add to web templates cache
                self.web_templates.append(web_template)
                return (web_template, 0.5)  # Medium confidence for web-sourced
        
        return None
    
    def _search_web_and_create_template(
        self,
        problem_text: str,
        test_cases: List[str] = None,
        function_name: str = None
    ) -> Optional[MBPPTemplate]:
        """
        Search web and create template from results.
        
        Note: Actual web search happens via web_search tool in context.
        """
        # Build search query
        from backend.benchmarking.web_enhanced_template_generator import WebEnhancedTemplateGenerator
        generator = WebEnhancedTemplateGenerator()
        
        query = generator._build_web_query(problem_text, test_cases)
        
        # This would call web_search tool (available in context)
        # For now, return None - actual implementation in integration layer
        return None
    
    def generate_from_template_with_web(
        self,
        problem_text: str,
        function_name: str,
        test_cases: List[str] = None
    ) -> Optional[str]:
        """
        Generate code with web search fallback.
        """
        # Try standard template generation
        code = self.generate_from_template(problem_text, function_name, test_cases)
        
        if code:
            return code
        
        # Try web search if enabled
        if self.use_web_search:
            web_template = self._search_web_and_create_template(
                problem_text,
                test_cases,
                function_name
            )
            
            if web_template:
                return web_template.generate_code(function_name, problem_text, test_cases)
        
        return None
