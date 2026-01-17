"""
NLP Error Processor for Launcher

Converts technical launcher errors into natural language explanations
using LLM orchestrator for better user understanding.
"""

import logging
import traceback
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NLPErrorProcessor:
    """
    Processes launcher errors through NLP to provide natural language explanations.
    
    Features:
    - Converts technical errors to user-friendly messages
    - Provides actionable solutions
    - Uses LLM orchestrator for intelligent error analysis
    - Maintains original error for debugging
    """
    
    def __init__(self, use_llm: bool = True, backend_url: Optional[str] = None):
        """
        Initialize NLP error processor.
        
        Args:
            use_llm: Whether to use LLM for error processing (default: True)
            backend_url: Backend API URL (e.g., "http://localhost:8000") if available
        """
        self.use_llm = use_llm
        self.backend_url = backend_url or "http://localhost:8000"
        self.llm_orchestrator = None
        
        # Try to use direct import if backend is in same process (unlikely for launcher)
        if use_llm:
            try:
                # Try direct import (only works if backend is in same process)
                import sys
                from pathlib import Path
                backend_path = Path(__file__).parent.parent / "backend"
                if backend_path.exists():
                    sys.path.insert(0, str(backend_path.parent))
                    from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                    self.llm_orchestrator = get_llm_orchestrator()
                    logger.info("LLM orchestrator available for error processing")
            except Exception as e:
                logger.debug(f"Direct LLM orchestrator not available (expected for launcher): {e}")
                # Will use HTTP API instead if backend is running
    
    def process_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process error through NLP to get natural language explanation.
        
        Args:
            error: The exception/error that occurred
            context: Additional context (command, process info, etc.)
        
        Returns:
            Dict with:
            - original_error: Original error message
            - nlp_explanation: Natural language explanation
            - suggested_solutions: List of suggested fixes
            - severity: Error severity (low/medium/high/critical)
            - technical_details: Technical error details
        """
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Build context string
        context_str = ""
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        
        # Try LLM processing if available
        nlp_explanation = None
        suggested_solutions = []
        severity = "medium"
        
        # Try LLM processing if available
        if self.use_llm:
            nlp_result = None
            last_error = None
            
            # Try direct orchestrator first (if in same process)
            if self.llm_orchestrator:
                try:
                    nlp_result = self._process_with_llm_direct(
                        error_type=error_type,
                        error_message=error_message,
                        error_traceback=error_traceback,
                        context=context_str
                    )
                except Exception as e:
                    last_error = str(e)
                    logger.debug(f"Direct LLM processing failed: {e}")
            
            # Try HTTP API if direct orchestrator not available or failed
            if not nlp_result:
                try:
                    nlp_result = self._process_with_llm_api(
                        error_type=error_type,
                        error_message=error_message,
                        error_traceback=error_traceback,
                        context=context_str
                    )
                except Exception as e:
                    last_error = str(e)
                    logger.debug(f"LLM API processing failed (backend may not be running): {e}")
            
            # Use LLM result if available
            if nlp_result and nlp_result.get("explanation"):
                nlp_explanation = nlp_result.get("explanation")
                suggested_solutions = nlp_result.get("solutions", [])
                severity = nlp_result.get("severity", "medium")
            else:
                # Fall back to rule-based processing
                if last_error:
                    logger.debug(f"Falling back to rule-based processing (last error: {last_error})")
                nlp_explanation, suggested_solutions, severity = self._process_with_rules(
                    error_type, error_message, context_str
                )
        else:
            # Use rule-based processing
            nlp_explanation, suggested_solutions, severity = self._process_with_rules(
                error_type, error_message, context_str
            )
        
        return {
            "original_error": error_message,
            "error_type": error_type,
            "nlp_explanation": nlp_explanation,
            "suggested_solutions": suggested_solutions,
            "severity": severity,
            "technical_details": {
                "traceback": error_traceback,
                "context": context
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _process_with_llm_direct(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str,
        context: str
    ) -> Dict[str, Any]:
        """Process error using direct LLM orchestrator (if in same process)."""
        from llm_orchestrator.multi_llm_client import TaskType
        
        prompt = f"""Analyze this launcher error and provide a user-friendly explanation.

Error Type: {error_type}
Error Message: {error_message}
Context: {context}

Traceback (first 500 chars):
{error_traceback[:500]}

Please provide:
1. A clear, non-technical explanation of what went wrong
2. 2-3 suggested solutions to fix the problem
3. Severity assessment (low/medium/high/critical)

Format your response as:
EXPLANATION: [clear explanation]
SOLUTIONS:
1. [solution 1]
2. [solution 2]
3. [solution 3]
SEVERITY: [low/medium/high/critical]"""

        result = self.llm_orchestrator.execute_task(
            prompt=prompt,
            task_type=TaskType.GENERAL,
            require_verification=False,  # Faster for error processing
            require_consensus=False,
            enable_learning=False  # Don't learn from errors
        )
        
        # result is LLMTaskResult object, access .content attribute
        content = result.content if hasattr(result, 'content') else str(result)
        return self._parse_llm_response(content, error_message)
    
    def _process_with_llm_api(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str,
        context: str
    ) -> Dict[str, Any]:
        """Process error using HTTP API to backend LLM orchestrator."""
        import requests
        
        prompt = f"""Analyze this launcher error and provide a user-friendly explanation.

Error Type: {error_type}
Error Message: {error_message}
Context: {context}

Traceback (first 500 chars):
{error_traceback[:500]}

Please provide:
1. A clear, non-technical explanation of what went wrong
2. 2-3 suggested solutions to fix the problem
3. Severity assessment (low/medium/high/critical)

Format your response as:
EXPLANATION: [clear explanation]
SOLUTIONS:
1. [solution 1]
2. [solution 2]
3. [solution 3]
SEVERITY: [low/medium/high/critical]"""
        
        # Call backend API
        try:
            response = requests.post(
                f"{self.backend_url}/llm/task",
                json={
                    "prompt": prompt,
                    "task_type": "general",
                    "require_verification": False,
                    "require_consensus": False,
                    "enable_learning": False,
                    "requires_determinism": False,
                    "is_safety_critical": False,
                    "impact_scope": "local"
                },
                timeout=5.0  # Quick timeout for error processing
            )
            
            if response.status_code == 200:
                result = response.json()
                # API returns LLMTaskResponse with 'content' field
                content = result.get("content", result.get("response", ""))
                if not content:
                    # If no content, try to extract from response structure
                    raise Exception("No content in API response")
                return self._parse_llm_response(content, error_message)
            else:
                error_detail = response.text[:200] if hasattr(response, 'text') else f"Status {response.status_code}"
                raise Exception(f"API returned {response.status_code}: {error_detail}")
                
        except requests.exceptions.RequestException as e:
            # Backend not available - expected during launcher startup
            raise Exception(f"Backend API not available: {str(e)}")
    
    def _parse_llm_response(self, content: str, fallback_error: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        # Parse response
        explanation = self._extract_section(content, "EXPLANATION:")
        solutions = self._extract_list(content, "SOLUTIONS:")
        severity_str = self._extract_section(content, "SEVERITY:")
        severity = severity_str.lower().strip() if severity_str else "medium"
        
        if not explanation:
            explanation = f"The launcher encountered an error: {fallback_error}"
        
        if not solutions:
            solutions = ["Check the error message above for details", "Review launcher logs"]
        
        if severity not in ["low", "medium", "high", "critical"]:
            severity = "medium"
        
        return {
            "explanation": explanation,
            "solutions": solutions,
            "severity": severity
        }
    
    def _process_with_rules(
        self,
        error_type: str,
        error_message: str,
        context: str
    ) -> tuple:
        """Process error using rule-based patterns."""
        
        # Common error patterns
        error_lower = error_message.lower()
        
        # Port already in use
        if "port" in error_lower and ("already" in error_lower or "in use" in error_lower):
            return (
                "The port is already being used by another application.",
                [
                    "Stop the application using the port",
                    "Change the port in launcher configuration",
                    "Check if another instance of GRACE is running"
                ],
                "medium"
            )
        
        # File not found
        if "not found" in error_lower or "file" in error_lower and "missing" in error_lower:
            return (
                "A required file or directory is missing.",
                [
                    "Check that all GRACE files are present",
                    "Verify the installation is complete",
                    "Re-run the setup script if needed"
                ],
                "high"
            )
        
        # Permission denied
        if "permission" in error_lower or "denied" in error_lower:
            return (
                "Permission was denied when trying to access a file or directory.",
                [
                    "Check file/folder permissions",
                    "Run with appropriate user permissions",
                    "Verify write access to required directories"
                ],
                "medium"
            )
        
        # Connection error
        if "connection" in error_lower or "connect" in error_lower:
            return (
                "Could not connect to a required service.",
                [
                    "Check if the service is running",
                    "Verify network connectivity",
                    "Check firewall settings"
                ],
                "high"
            )
        
        # Process died
        if "process" in error_lower and ("died" in error_lower or "exited" in error_lower):
            return (
                "A required process stopped unexpectedly.",
                [
                    "Check process logs for details",
                    "Verify system resources are available",
                    "Check for conflicting processes"
                ],
                "critical"
            )
        
        # Version mismatch
        if "version" in error_lower and "mismatch" in error_lower:
            return (
                "Version mismatch detected between components.",
                [
                    "Update all components to the same version",
                    "Check version compatibility",
                    "Re-run setup to ensure versions match"
                ],
                "high"
            )
        
        # Default
        return (
            f"The launcher encountered an error: {error_message}",
            [
                "Check the error message for details",
                "Review launcher logs",
                "Verify system requirements are met"
            ],
            "medium"
        )
    
    def _extract_section(self, text: str, marker: str) -> str:
        """Extract section from LLM response."""
        if marker not in text:
            return ""
        
        start = text.find(marker) + len(marker)
        end = text.find("\n", start)
        if end == -1:
            end = len(text)
        
        return text[start:end].strip()
    
    def _extract_list(self, text: str, marker: str) -> list:
        """Extract numbered list from LLM response."""
        if marker not in text:
            return []
        
        start = text.find(marker)
        end = text.find("\n\n", start)
        if end == -1:
            end = len(text)
        
        list_text = text[start:end]
        solutions = []
        
        for line in list_text.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering/bullet
                solution = line.split(".", 1)[-1].strip()
                solution = solution.lstrip("- ").strip()
                if solution:
                    solutions.append(solution)
        
        return solutions


# Global instance
_nlp_processor: Optional[NLPErrorProcessor] = None


def get_nlp_error_processor(use_llm: bool = True, backend_url: Optional[str] = None) -> NLPErrorProcessor:
    """Get or create global NLP error processor instance."""
    global _nlp_processor
    if _nlp_processor is None:
        _nlp_processor = NLPErrorProcessor(use_llm=use_llm, backend_url=backend_url)
    return _nlp_processor
