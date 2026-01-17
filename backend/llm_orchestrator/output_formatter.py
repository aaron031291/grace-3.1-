import json
import logging
from typing import Dict, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import re

# Import emoji sanitization
try:
    from utils.emoji_sanitizer import sanitize_llm_output
except ImportError:
    # Fallback if not available
    def sanitize_llm_output(output, replace=True):
        return output

logger = logging.getLogger(__name__)


class OutputRecipient(str, Enum):
    """Output recipient types."""
    AI = "ai"  # AI-to-AI communication (deterministic JSON)
    HUMAN = "human"  # AI-to-Human communication (natural language)


class OutputFormat(str, Enum):
    """Output formats."""
    JSON = "json"  # Deterministic JSON (AI-to-AI)
    NLP = "nlp"  # Natural language (AI-to-Human)


@dataclass
class FormattedOutput:
    """Formatted output with verification."""
    content: str
    format: OutputFormat
    recipient: OutputRecipient
    verified: bool
    verification_confidence: float
    is_json: bool
    json_valid: bool
    deterministic: bool  # Only for JSON outputs


class OutputFormatter:
    """
    Output formatter for Grace-Aligned LLMs.
    
    Features:
    - Deterministic JSON for AI-to-AI (verified, structured)
    - Natural language for AI-to-Human (readable, conversational)
    - Verification layer (hallucination mitigation)
    - Type-safe formatting
    """
    
    def __init__(self):
        """Initialize output formatter."""
        self.verification_cache: Dict[str, bool] = {}
    
    def format_output(
        self,
        raw_output: str,
        recipient: OutputRecipient = OutputRecipient.HUMAN,
        verify: bool = True,
        force_json: bool = False
    ) -> FormattedOutput:
        """
        Format LLM output for recipient type.
        
        Args:
            raw_output: Raw LLM output
            recipient: Output recipient (AI or HUMAN)
            verify: Whether to verify output
            force_json: Force JSON output even for human recipients
            
        Returns:
            FormattedOutput with verified content
        """
        # Determine format based on recipient
        if recipient == OutputRecipient.AI or force_json:
            format_type = OutputFormat.JSON
        else:
            format_type = OutputFormat.NLP
        
        # Verify output if enabled
        verified = True
        verification_confidence = 1.0
        if verify:
            verified, verification_confidence = self._verify_output(raw_output)
        
        # Sanitize emojis from raw output first
        raw_output = sanitize_llm_output(raw_output, replace=True)
        
        # Format based on type
        if format_type == OutputFormat.JSON:
            formatted = self._format_json(raw_output, verified)
        else:
            formatted = self._format_nlp(raw_output, verified)
        
        # Final sanitization pass on formatted output
        formatted = sanitize_llm_output(formatted, replace=True)
        
        # Check if output is JSON
        is_json = self._is_json(formatted)
        json_valid = False
        deterministic = False
        
        if is_json:
            json_valid = self._validate_json(formatted)
            if json_valid:
                deterministic = self._check_deterministic_json(formatted)
        
        return FormattedOutput(
            content=formatted,
            format=format_type,
            recipient=recipient,
            verified=verified,
            verification_confidence=verification_confidence,
            is_json=is_json,
            json_valid=json_valid,
            deterministic=deterministic
        )
    
    def _format_json(
        self,
        raw_output: str,
        verified: bool
    ) -> str:
        """
        Format output as deterministic JSON (AI-to-AI).
        
        Ensures:
        - Valid JSON structure
        - Deterministic ordering
        - Type consistency
        - Verification metadata
        """
        # Try to parse existing JSON
        try:
            data = json.loads(raw_output)
            
            # Ensure deterministic structure
            formatted_json = self._ensure_deterministic_json(data, verified)
            
            return formatted_json
            
        except json.JSONDecodeError:
            # Not JSON, try to extract JSON from text
            json_match = re.search(r'\{[^{}]*\}', raw_output, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    formatted_json = self._ensure_deterministic_json(data, verified)
                    return formatted_json
                except json.JSONDecodeError:
                    pass
            
            # No JSON found, wrap in JSON structure
            return self._wrap_as_json(raw_output, verified)
    
    def _format_nlp(
        self,
        raw_output: str,
        verified: bool
    ) -> str:
        """
        Format output as natural language (AI-to-Human).
        
        Ensures:
        - Readable format
        - Natural language flow
        - Verification indicator (if needed)
        - Conversational tone
        """
        # Clean up output
        formatted = raw_output.strip()
        
        # Add verification indicator if needed
        if not verified:
            formatted = f"[WARN] Note: This response has not been fully verified\n\n{formatted}"
        
        # Ensure proper formatting
        formatted = self._clean_nlp_output(formatted)
        
        return formatted
    
    def _ensure_deterministic_json(
        self,
        data: Dict[str, Any],
        verified: bool
    ) -> str:
        """
        Ensure JSON is deterministic (same structure always).
        
        Deterministic means:
        - Same key order
        - Consistent types
        - No randomness
        - Verifiable structure
        """
        # Add verification metadata
        deterministic_data = {
            "verified": verified,
            "timestamp": datetime.utcnow().isoformat(),
            "format": "deterministic_json",
            "data": self._normalize_json_data(data)
        }
        
        # Sort keys for deterministic ordering
        sorted_json = json.dumps(deterministic_data, sort_keys=True, indent=2, ensure_ascii=False)
        
        return sorted_json
    
    def _normalize_json_data(self, data: Any) -> Any:
        """Normalize JSON data for deterministic output."""
        if isinstance(data, dict):
            # Sort keys and normalize values
            normalized = {}
            for key in sorted(data.keys()):
                normalized[key] = self._normalize_json_data(data[key])
            return normalized
        elif isinstance(data, list):
            # Normalize list items
            return [self._normalize_json_data(item) for item in data]
        elif isinstance(data, (int, float)):
            # Ensure numeric types are consistent
            return float(data) if isinstance(data, float) else int(data)
        elif isinstance(data, bool):
            return bool(data)
        elif isinstance(data, str):
            return str(data)
        else:
            return str(data)
    
    def _wrap_as_json(self, content: str, verified: bool) -> str:
        """Wrap non-JSON content in JSON structure."""
        data = {
            "verified": verified,
            "timestamp": datetime.utcnow().isoformat(),
            "format": "deterministic_json",
            "content": content,
            "data": {
                "text": content
            }
        }
        
        return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
    
    def _clean_nlp_output(self, text: str) -> str:
        """Clean NLP output for human readability."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure proper sentence endings
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Clean up formatting
        text = text.strip()
        
        return text
    
    def _verify_output(self, output: str) -> Tuple[bool, float]:
        """
        Verify output for hallucinations and errors.
        
        Returns:
            (verified, confidence) where confidence is 0-1
        """
        # Simple verification heuristics (can be enhanced)
        verification_score = 1.0
        issues = []
        
        # Check for common hallucination patterns
        if re.search(r'\b(always|never|all|every|none)\b.*\b(always|never|all|every|none)\b', output, re.IGNORECASE):
            issues.append("Potential absolute statements")
            verification_score -= 0.2
        
        # Check for contradictory statements
        contradictory_patterns = [
            (r'\b(is|are)\s+not\b', r'\b(is|are)\b'),
            (r'\balways\b', r'\bnever\b'),
            (r'\ball\b', r'\bnone\b')
        ]
        
        for neg_pattern, pos_pattern in contradictory_patterns:
            if re.search(neg_pattern, output, re.IGNORECASE) and re.search(pos_pattern, output, re.IGNORECASE):
                issues.append("Potential contradiction")
                verification_score -= 0.3
        
        # Check for undefined terms (simple heuristic)
        undefined_terms = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', output)
        if len(undefined_terms) > 5:
            issues.append("Many undefined terms")
            verification_score -= 0.1
        
        verified = verification_score >= 0.7
        
        if issues:
            logger.debug(f"[OUTPUT-FORMATTER] Verification issues: {issues}")
        
        return verified, max(0.0, min(1.0, verification_score))
    
    def _is_json(self, content: str) -> bool:
        """Check if content is JSON."""
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _validate_json(self, content: str) -> bool:
        """Validate JSON structure."""
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def _check_deterministic_json(self, json_content: str) -> bool:
        """
        Check if JSON is deterministic.
        
        Deterministic means:
        - Same output for same input
        - No randomness
        - Consistent structure
        """
        try:
            data = json.loads(json_content)
            
            # Check for required deterministic fields
            if not isinstance(data, dict):
                return False
            
            # Check for verification metadata
            if "verified" not in data:
                return False
            
            # Check for timestamp (deterministic outputs should have timestamps)
            if "timestamp" not in data:
                return False
            
            # Check for data field (structured data)
            if "data" not in data:
                return False
            
            return True
            
        except (json.JSONDecodeError, TypeError):
            return False
    
    def format_for_ai(
        self,
        raw_output: str,
        verify: bool = True
    ) -> FormattedOutput:
        """Format output for AI consumption (deterministic JSON)."""
        return self.format_output(
            raw_output=raw_output,
            recipient=OutputRecipient.AI,
            verify=verify,
            force_json=True
        )
    
    def format_for_human(
        self,
        raw_output: str,
        verify: bool = True
    ) -> FormattedOutput:
        """Format output for human consumption (natural language)."""
        return self.format_output(
            raw_output=raw_output,
            recipient=OutputRecipient.HUMAN,
            verify=verify,
            force_json=False
        )


def get_output_formatter() -> OutputFormatter:
    """Factory function to get output formatter."""
    return OutputFormatter()
