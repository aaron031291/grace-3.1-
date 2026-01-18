"""
Enhanced Web Integration with Learning Memory & AI Research

Searches multiple knowledge sources:
1. Learning Memory (stored patterns/examples)
2. AI Research folder (code examples)
3. Web search (Stack Overflow, GitHub)
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


class EnhancedWebTemplateIntegration:
    """Enhanced integration using ALL knowledge sources."""
    
    def __init__(
        self,
        web_knowledge_service=None,
        document_retriever=None,
        learning_memory_manager=None,
        ai_research_path: Optional[str] = None
    ):
        """
        Initialize with all knowledge sources.
        
        Args:
            web_knowledge_service: WebKnowledgeIntegration instance
            document_retriever: DocumentRetriever for knowledge base search
            learning_memory_manager: LearningMemoryManager instance
            ai_research_path: Path to AI research folder
        """
        self.web_knowledge = web_knowledge_service
        self.retriever = document_retriever
        self.learning_memory = learning_memory_manager
        self.ai_research_path = Path(ai_research_path) if ai_research_path else None
        
        # Try to find AI research path if not provided
        if not self.ai_research_path:
            possible_paths = [
                project_root / "knowledge_base" / "learning memory" / "ai research",
                project_root / "backend" / "knowledge_base" / "learning memory" / "ai research",
                project_root / "knowledge_base" / "ai research",
            project_root / "knowledge_base" / "coding_patterns",
            ]
            for path in possible_paths:
                if path.exists():
                    self.ai_research_path = path
                    break
        
        self.templates_created = []
    
    async def search_all_sources_async(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search ALL knowledge sources and create template.
        
        Priority:
        1. Learning Memory (fastest, most trusted)
        2. AI Research folder (local knowledge)
        3. Web search (external knowledge)
        
        Args:
            problem_text: Problem description
            test_cases: Test cases
            
        Returns:
            Template dict or None
        """
        code_examples = []
        sources_used = []
        
        # 1. Search Learning Memory first
        if self.learning_memory:
            try:
                learning_code = await self._search_learning_memory(problem_text, test_cases)
                if learning_code:
                    code_examples.extend(learning_code)
                    sources_used.append("learning_memory")
                    print(f"  [LEARNING MEMORY] Found {len(learning_code)} code examples")
            except Exception as e:
                print(f"  [LEARNING MEMORY] Search failed: {e}")
        
        # 2. Search AI Research folder
        if self.ai_research_path and self.ai_research_path.exists():
            try:
                research_code = await self._search_ai_research(problem_text, test_cases)
                if research_code:
                    code_examples.extend(research_code)
                    sources_used.append("ai_research")
                    print(f"  [AI RESEARCH] Found {len(research_code)} code examples")
            except Exception as e:
                print(f"  [AI RESEARCH] Search failed: {e}")
        
        # 3. Search Knowledge Base via DocumentRetriever
        if self.retriever:
            try:
                kb_code = await self._search_knowledge_base(problem_text, test_cases)
                if kb_code:
                    code_examples.extend(kb_code)
                    sources_used.append("knowledge_base")
                    print(f"  [KNOWLEDGE BASE] Found {len(kb_code)} code examples")
            except Exception as e:
                print(f"  [KNOWLEDGE BASE] Search failed: {e}")
        
        # 4. Search Web (if no local results or as fallback)
        if not code_examples and self.web_knowledge:
            try:
                web_code = await self._search_web(problem_text, test_cases)
                if web_code:
                    code_examples.extend(web_code)
                    sources_used.append("web_search")
                    print(f"  [WEB SEARCH] Found {len(web_code)} code examples")
            except Exception as e:
                print(f"  [WEB SEARCH] Failed: {e}")
        
        if not code_examples:
            return None
        
        # Select best code from all sources
        best_code = self._select_best_code(code_examples, problem_text)
        if not best_code:
            return None
        
        # Create template
        query = self._build_query(problem_text, test_cases)
        template = self._create_template(best_code, problem_text, query)
        
        if template:
            template["sources_used"] = sources_used
            self.templates_created.append(template)
        
        return template
    
    def search_all_sources_sync(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.search_all_sources_async(problem_text, test_cases)
                    )
                    return future.result(timeout=15)
            else:
                return loop.run_until_complete(
                    self.search_all_sources_async(problem_text, test_cases)
                )
        except Exception as e:
            print(f"[ENHANCED WEB] Sync wrapper failed: {e}")
            return None
    
    async def _search_learning_memory(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> List[str]:
        """Search learning memory for code examples."""
        code_examples = []
        
        try:
            # Search for relevant learning examples
            # This is a simplified version - adjust based on actual LearningMemoryManager API
            if hasattr(self.learning_memory, 'search_examples'):
                results = self.learning_memory.search_examples(
                    query=problem_text,
                    limit=5
                )
                
                for result in results:
                    # Extract code from learning examples
                    if hasattr(result, 'actual_output'):
                        code = result.actual_output
                        if isinstance(code, dict):
                            code = code.get('code', '')
                        if code and "def " in code:
                            code_examples.append(code)
            
        except Exception as e:
            print(f"  [LEARNING MEMORY] Error: {e}")
        
        return code_examples
    
    async def _search_ai_research(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> List[str]:
        """Search AI research folder for code examples."""
        code_examples = []
        
        if not self.ai_research_path or not self.ai_research_path.exists():
            return code_examples
        
        try:
            # Build search query
            keywords = self._extract_keywords(problem_text)
            query_terms = " ".join(keywords[:3])
            
            # Search Python files in AI research folder
            python_files = list(self.ai_research_path.rglob("*.py"))
            
            for py_file in python_files[:20]:  # Limit to first 20 files
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    
                    # Check if file contains relevant keywords
                    content_lower = content.lower()
                    problem_lower = problem_text.lower()
                    
                    if any(keyword in content_lower for keyword in keywords):
                        # Extract function definitions
                        func_pattern = r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
                        matches = re.findall(func_pattern, content, re.DOTALL)
                        
                        for match in matches:
                            code = match.strip()
                            if len(code) > 20 and "return " in code:
                                code_examples.append(code)
                                
                except Exception as e:
                    continue  # Skip files that can't be read
        
        except Exception as e:
            print(f"  [AI RESEARCH] Error: {e}")
        
        return code_examples
    
    async def _search_knowledge_base(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> List[str]:
        """Search knowledge base via DocumentRetriever."""
        code_examples = []
        
        try:
            if hasattr(self.retriever, 'search'):
                results = self.retriever.search(
                    query=problem_text,
                    top_k=5
                )
                
                for result in results:
                    content = result.get('content', '') or result.get('text', '')
                    if content:
                        # Extract code blocks
                        code_blocks = self._extract_code_from_text(content)
                        code_examples.extend(code_blocks)
        
        except Exception as e:
            print(f"  [KNOWLEDGE BASE] Error: {e}")
        
        return code_examples
    
    async def _search_web(
        self,
        problem_text: str,
        test_cases: List[str] = None
    ) -> List[str]:
        """Search web using WebKnowledgeIntegration."""
        code_examples = []
        
        if not self.web_knowledge:
            return code_examples
        
        try:
            from backend.oracle_intelligence.web_knowledge import KnowledgeSource
            
            query = self._build_query(problem_text, test_cases)
            results = await self.web_knowledge.search(
                query=query,
                sources=[KnowledgeSource.STACKOVERFLOW, KnowledgeSource.GITHUB],
                limit=3
            )
            
            for result in results:
                code_examples.extend(result.code_examples)
                code_examples.extend(self._extract_code_from_text(result.content))
        
        except Exception as e:
            print(f"  [WEB] Error: {e}")
        
        return code_examples
    
    def _build_query(self, problem_text: str, test_cases: List[str] = None) -> str:
        """Build search query."""
        func_name = None
        if test_cases:
            for test in test_cases:
                match = re.search(r'(\w+)\s*\(', test)
                if match:
                    func_name = match.group(1)
                    break
        
        keywords = self._extract_keywords(problem_text)
        
        query_parts = ["python"]
        if func_name:
            query_parts.append(func_name)
        query_parts.extend(keywords[:3])
        query_parts.append("example")
        
        return " ".join(query_parts)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from problem text."""
        keywords = []
        text_lower = text.lower()
        
        for word in ["find", "count", "sort", "remove", "check", "list", "string", 
                     "maximum", "minimum", "sum", "average", "filter", "map"]:
            if word in text_lower:
                keywords.append(word)
        
        return keywords
    
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
            score = len(code) / 100
            
            code_lower = code.lower()
            if "def " in code:
                score += 10
            if "return " in code:
                score += 3
            
            # Match keywords
            keywords = self._extract_keywords(problem_text)
            for word in keywords:
                if word in code_lower:
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
        
        keywords = self._extract_keywords(problem_text)
        
        return {
            "name": f"enhanced_{func_name}",
            "pattern_keywords": keywords,
            "pattern_regex": "|".join(keywords[:3]) + ".*" if keywords else ".*",
            "template_code": template_code,
            "description": f"Multi-source: {query}",
            "examples": [problem_text[:100]],
            "source": "enhanced_search"
        }
