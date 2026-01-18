"""
Knowledge-Driven Code Generator

Generates code using ingested knowledge from GitHub, code repositories, and other sources.
This allows Grace to generate code WITHOUT requiring LLMs by using:
1. RAG retrieval from knowledge base
2. Template pattern matching
3. Code examples from ingested repositories
4. Procedural memory patterns

This makes Grace LLM-independent for common patterns.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import re
import ast

logger = logging.getLogger(__name__)


class KnowledgeDrivenCodeGenerator:
    """
    Generate code using knowledge base instead of LLMs.
    
    This system:
    1. Retrieves relevant code examples from knowledge base
    2. Matches patterns from templates
    3. Uses procedural memory
    4. Synthesizes code from examples
    """
    
    def __init__(
        self,
        retriever=None,
        template_matcher=None,
        procedural_memory=None,
        knowledge_base_path: Optional[Path] = None
    ):
        """
        Initialize knowledge-driven code generator.
        
        Args:
            retriever: RAG retriever for knowledge base
            template_matcher: Template pattern matcher
            procedural_memory: Procedural memory repository
            knowledge_base_path: Path to knowledge base
        """
        self.retriever = retriever
        self.template_matcher = template_matcher
        self.procedural_memory = procedural_memory
        self.knowledge_base_path = knowledge_base_path
        
        # Initialize template matcher if not provided
        if not self.template_matcher:
            try:
                from benchmarking.mbpp_templates import get_template_matcher
                self.template_matcher = get_template_matcher()
            except Exception as e:
                logger.warning(f"[KNOWLEDGE-CODING] Could not load template matcher: {e}")
        
        logger.info("[KNOWLEDGE-CODING] Knowledge-driven code generator initialized")
    
    def generate_code(
        self,
        task_description: str,
        function_name: Optional[str] = None,
        test_cases: List[str] = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate code using knowledge base (no LLM required).
        
        Args:
            task_description: Description of the coding task
            function_name: Expected function name
            test_cases: Test cases (for pattern inference)
            context: Additional context
            
        Returns:
            Dictionary with:
            - code: Generated code
            - method: How code was generated ("template", "rag", "procedural", "synthesized")
            - confidence: Confidence score (0.0-1.0)
            - sources: Sources used
        """
        context = context or {}
        test_cases = test_cases or []
        
        # Method 1: Try template pattern matching (fastest, highest confidence)
        if self.template_matcher:
            template_code = self._try_template_generation(
                task_description, function_name, test_cases
            )
            if template_code:
                return {
                    "code": template_code,
                    "method": "template",
                    "confidence": 0.9,
                    "sources": ["template_library"]
                }
        
        # Method 2: Try RAG retrieval from knowledge base
        if self.retriever:
            rag_code = self._try_rag_generation(
                task_description, function_name, test_cases, context
            )
            if rag_code:
                return rag_code
        
        # Method 3: Try procedural memory
        if self.procedural_memory:
            procedural_code = self._try_procedural_generation(
                task_description, function_name, context
            )
            if procedural_code:
                return procedural_code
        
        # Method 4: Synthesize from multiple sources
        synthesized_code = self._synthesize_code(
            task_description, function_name, test_cases, context
        )
        if synthesized_code:
            return synthesized_code
        
        # No code generated
        return {
            "code": None,
            "method": "none",
            "confidence": 0.0,
            "sources": [],
            "error": "Could not generate code from knowledge base"
        }
    
    def _try_template_generation(
        self,
        task_description: str,
        function_name: Optional[str],
        test_cases: List[str]
    ) -> Optional[str]:
        """Try to generate code using template matching."""
        try:
            if not function_name:
                # Try to extract from description
                func_match = re.search(r'function\s+(\w+)|def\s+(\w+)', task_description, re.IGNORECASE)
                if func_match:
                    function_name = func_match.group(1) or func_match.group(2)
            
            if not function_name:
                function_name = "solve_task"
            
            code = self.template_matcher.generate_from_template(
                problem_text=task_description,
                function_name=function_name,
                test_cases=test_cases
            )
            
            return code
        except Exception as e:
            logger.debug(f"[KNOWLEDGE-CODING] Template generation failed: {e}")
            return None
    
    def _try_rag_generation(
        self,
        task_description: str,
        function_name: Optional[str],
        test_cases: List[str],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Try to generate code using RAG retrieval."""
        try:
            # Build query for retrieval
            query = f"{task_description}"
            if function_name:
                query += f" function {function_name}"
            
            # Retrieve relevant code examples
            results = self.retriever.retrieve(
                query=query,
                limit=5,
                score_threshold=0.5
            )
            
            if not results:
                return None
            
            # Extract code from retrieved examples
            code_examples = []
            for result in results:
                content = result.get("content", "")
                score = result.get("score", 0.0)
                
                # Try to extract Python code from content
                code = self._extract_code_from_text(content)
                if code:
                    code_examples.append({
                        "code": code,
                        "score": score,
                        "source": result.get("id", "unknown")
                    })
            
            if not code_examples:
                return None
            
            # Use best matching example or synthesize
            best_example = max(code_examples, key=lambda x: x["score"])
            
            # Adapt code to match function name if needed
            adapted_code = self._adapt_code_to_function(
                best_example["code"],
                function_name or "solve_task",
                task_description
            )
            
            return {
                "code": adapted_code,
                "method": "rag",
                "confidence": best_example["score"],
                "sources": [best_example["source"]]
            }
            
        except Exception as e:
            logger.debug(f"[KNOWLEDGE-CODING] RAG generation failed: {e}")
            return None
    
    def _try_procedural_generation(
        self,
        task_description: str,
        function_name: Optional[str],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Try to generate code using procedural memory."""
        try:
            # Find matching procedure
            procedure = self.procedural_memory.find_procedure(
                goal=task_description,
                context=context
            )
            
            if not procedure:
                return None
            
            # Extract code from procedure
            # Procedures store action sequences, try to convert to code
            code = self._procedure_to_code(procedure, function_name)
            
            if code:
                return {
                    "code": code,
                    "method": "procedural",
                    "confidence": procedure.success_rate if hasattr(procedure, 'success_rate') else 0.7,
                    "sources": [f"procedure_{procedure.id}"]
                }
            
        except Exception as e:
            logger.debug(f"[KNOWLEDGE-CODING] Procedural generation failed: {e}")
            return None
    
    def _synthesize_code(
        self,
        task_description: str,
        function_name: Optional[str],
        test_cases: List[str],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Synthesize code from multiple knowledge sources."""
        sources = []
        code_parts = []
        
        # Collect from RAG
        if self.retriever:
            try:
                results = self.retriever.retrieve(
                    query=task_description,
                    limit=3,
                    score_threshold=0.4
                )
                for result in results:
                    code = self._extract_code_from_text(result.get("content", ""))
                    if code:
                        code_parts.append(code)
                        sources.append(f"rag_{result.get('id', 'unknown')}")
            except Exception:
                pass
        
        # Collect from templates (even if not exact match)
        if self.template_matcher:
            try:
                # Try to find partial matches
                for template in self.template_matcher.templates:
                    matches, confidence = template.matches(task_description, test_cases)
                    if matches and confidence > 0.3:
                        code = template.generate_code(
                            function_name or "solve_task",
                            task_description,
                            test_cases
                        )
                        if code:
                            code_parts.append(code)
                            sources.append(f"template_{template.name}")
            except Exception:
                pass
        
        if not code_parts:
            return None
        
        # Synthesize from parts
        synthesized = self._combine_code_examples(
            code_parts,
            function_name or "solve_task",
            task_description
        )
        
        if synthesized:
            return {
                "code": synthesized,
                "method": "synthesized",
                "confidence": 0.6,
                "sources": sources
            }
        
        return None
    
    def _extract_code_from_text(self, text: str) -> Optional[str]:
        """Extract Python code from text (markdown, docstrings, etc.)."""
        # Try to find code blocks
        code_block_match = re.search(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1).strip()
            if self._is_valid_python(code):
                return code
        
        # Try to find function definitions
        func_match = re.search(r'def\s+\w+\s*\([^)]*\)\s*:.*?(?=\n\n|\ndef\s|\nclass\s|$)', text, re.DOTALL)
        if func_match:
            code = func_match.group(0).strip()
            if self._is_valid_python(code):
                return code
        
        # Try to find any Python code
        lines = text.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Detect code blocks
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                code_lines.append(line)
            elif stripped.startswith('def ') or stripped.startswith('class '):
                code_lines.append(line)
            elif code_lines and (stripped.startswith(' ') or stripped.startswith('\t')):
                code_lines.append(line)
        
        if code_lines:
            code = '\n'.join(code_lines).strip()
            if self._is_valid_python(code):
                return code
        
        return None
    
    def _is_valid_python(self, code: str) -> bool:
        """Check if code is valid Python."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _adapt_code_to_function(
        self,
        code: str,
        target_function_name: str,
        task_description: str
    ) -> str:
        """Adapt retrieved code to match target function name."""
        # Find function name in code
        func_match = re.search(r'def\s+(\w+)\s*\(', code)
        if func_match:
            original_name = func_match.group(1)
            if original_name != target_function_name:
                # Rename function
                code = re.sub(
                    rf'def\s+{re.escape(original_name)}\s*\(',
                    f'def {target_function_name}(',
                    code,
                    count=1
                )
        
        return code
    
    def _procedure_to_code(
        self,
        procedure,
        function_name: Optional[str]
    ) -> Optional[str]:
        """Convert procedure to Python code."""
        # Procedures store action sequences
        # This is a simplified conversion - in practice, you'd need more sophisticated logic
        try:
            if hasattr(procedure, 'action_sequence'):
                actions = procedure.action_sequence
                if actions:
                    # Try to extract code from actions
                    code_parts = []
                    for action in actions:
                        if isinstance(action, dict):
                            action_type = action.get('type', '')
                            if action_type == 'code':
                                code_parts.append(action.get('code', ''))
                    
                    if code_parts:
                        code = '\n'.join(code_parts)
                        if function_name:
                            code = self._adapt_code_to_function(code, function_name, "")
                        return code
        except Exception as e:
            logger.debug(f"[KNOWLEDGE-CODING] Procedure to code conversion failed: {e}")
        
        return None
    
    def _combine_code_examples(
        self,
        code_examples: List[str],
        function_name: str,
        task_description: str
    ) -> Optional[str]:
        """Combine multiple code examples into one solution."""
        if not code_examples:
            return None
        
        # Use the best example as base
        base_code = code_examples[0]
        
        # Try to extract function from base
        func_match = re.search(r'def\s+\w+\s*\([^)]*\)\s*:.*', base_code, re.DOTALL)
        if func_match:
            function_code = func_match.group(0)
            
            # Adapt function name
            if function_name:
                function_code = self._adapt_code_to_function(function_code, function_name, task_description)
            
            return function_code
        
        return base_code


# Singleton instance
_knowledge_generator = None

def get_knowledge_driven_generator(
    retriever=None,
    template_matcher=None,
    procedural_memory=None,
    knowledge_base_path: Optional[Path] = None
) -> KnowledgeDrivenCodeGenerator:
    """Get singleton knowledge-driven code generator."""
    global _knowledge_generator
    if _knowledge_generator is None:
        _knowledge_generator = KnowledgeDrivenCodeGenerator(
            retriever=retriever,
            template_matcher=template_matcher,
            procedural_memory=procedural_memory,
            knowledge_base_path=knowledge_base_path
        )
    return _knowledge_generator
