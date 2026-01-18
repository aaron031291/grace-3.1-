import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from cognitive.compiler_governed_agency import CodeIntent, IntentType, CompilerGovernedAgency, get_compiler_governed_agency
logger = logging.getLogger(__name__)

class IntentValidationError(Exception):
    """Intent validation failed"""
    pass


class IntentProposalSystem:
    """
    System for LLM to propose code modifications via intents.
    
    LLM workflow:
    1. Analyze code issue
    2. Generate intent object (not code!)
    3. Submit intent to proposal system
    4. Intent validated and matched to rule
    5. AST transformer executes rule
    6. Diff + Genesis key created
    """
    
    def __init__(self, compiler_agency: Optional[CompilerGovernedAgency] = None):
        self.agency = compiler_agency or get_compiler_governed_agency()
        self.pending_proposals: List[CodeIntent] = []
        self.approved_proposals: List[CodeIntent] = []
        self.rejected_proposals: List[CodeIntent] = []
    
    def propose_intent(
        self,
        intent_type: IntentType,
        target_file: str,
        criteria: Dict[str, Any],
        justification: str,
        llm_model: str = "unknown",
        llm_confidence: float = 0.0,
        **kwargs
    ) -> CodeIntent:
        """
        Create intent proposal from LLM.
        
        This is the ONLY way LLM can propose changes.
        No code strings. Only intent objects.
        """
        intent = CodeIntent(
            intent_type=intent_type,
            target_file=target_file,
            target_line=kwargs.get('target_line'),
            target_function=kwargs.get('target_function'),
            target_class=kwargs.get('target_class'),
            criteria=criteria,
            justification=justification,
            llm_model=llm_model,
            llm_confidence=llm_confidence,
            llm_tokens_used=kwargs.get('tokens_used')
        )
        
        # Validate intent structure (anti-hallucination)
        self._validate_intent_structure(intent)
        
        self.pending_proposals.append(intent)
        
        return intent
    
    def _validate_intent_structure(self, intent: CodeIntent):
        """
        Validate intent is properly structured (not code-shaped).
        
        Raises IntentValidationError if invalid.
        """
        # Check 1: Intent type is valid
        if not isinstance(intent.intent_type, IntentType):
            raise IntentValidationError(f"Invalid intent type: {intent.intent_type}")
        
        # Check 2: No code syntax in any field
        forbidden_code_patterns = [
            'def ', 'class ', 'import ', '=', '(', ')', '{', '}',
            'return ', 'if ', 'for ', 'while ', 'try:', 'except:'
        ]
        
        check_fields = {
            'justification': intent.justification,
            'criteria': str(intent.criteria),
        }
        
        for field_name, field_value in check_fields.items():
            if field_value:
                value_str = str(field_value)
                for pattern in forbidden_code_patterns:
                    if pattern in value_str:
                        # Allow references like "function foo" but not "def foo()"
                        if not self._is_safe_reference(pattern, value_str):
                            raise IntentValidationError(
                                f"Intent {field_name} contains code syntax: {pattern}"
                            )
        
        # Check 3: Criteria is properly structured
        if not isinstance(intent.criteria, dict):
            raise IntentValidationError("Intent criteria must be a dictionary")
        
        # Check 4: Confidence is in valid range
        if not 0.0 <= intent.llm_confidence <= 1.0:
            raise IntentValidationError(f"Invalid LLM confidence: {intent.llm_confidence}")
    
    def _is_safe_reference(self, pattern: str, text: str) -> bool:
        """Check if pattern is safe reference (not code execution)"""
        # Allow references like "function foo" but not "def foo():"
        if pattern == 'def ':
            # Check if followed by function definition syntax
            idx = text.find(pattern)
            if idx != -1:
                # Check if next part looks like code
                next_part = text[idx + len(pattern):idx + len(pattern) + 20]
                if '(' in next_part and ':' in next_part:
                    return False  # Looks like code definition
                return True  # Might be reference
        
        return True  # Conservative - allow if not clearly code
    
    def process_pending_intents(self, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Process all pending intents through compiler-governed pipeline.
        
        Returns:
            Summary of processed intents
        """
        results = {
            'processed': 0,
            'approved': 0,
            'rejected': 0,
            'transformed': 0,
            'errors': []
        }
        
        for intent in self.pending_proposals:
            try:
                # Read source code
                from pathlib import Path
                source_file = Path(intent.target_file)
                if not source_file.exists():
                    results['errors'].append(f"File not found: {intent.target_file}")
                    self.rejected_proposals.append(intent)
                    results['rejected'] += 1
                    continue
                
                source_code = source_file.read_text(encoding='utf-8')
                
                # Process intent through compiler-governed agency
                success, proposal, metadata = self.agency.process_intent(
                    intent, source_code, str(intent.target_file)
                )
                
                results['processed'] += 1
                
                if success:
                    # Intent successfully transformed
                    results['transformed'] += 1
                    
                    if auto_approve:
                        # Apply transformation
                        source_file.write_text(proposal.after_code, encoding='utf-8')
                        self.approved_proposals.append(intent)
                        results['approved'] += 1
                    else:
                        # Keep pending for human approval
                        pass
                else:
                    # Transformation failed
                    results['errors'].append(metadata.get('validation_error', 'Unknown error'))
                    self.rejected_proposals.append(intent)
                    results['rejected'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing intent {intent.intent_type}: {e}")
                results['errors'].append(str(e))
                results['rejected'] += 1
                self.rejected_proposals.append(intent)
        
        # Clear pending after processing
        self.pending_proposals.clear()
        
        return results


def create_intent_from_llm_output(
    llm_response: Dict[str, Any],
    target_file: str
) -> CodeIntent:
    """
    Convert LLM response to CodeIntent (constrained parsing).
    
    LLM should output JSON like:
    {
        "intent_type": "add_logging",
        "target_class": "MyClass",
        "criteria": {"target": "class"},
        "justification": "Class needs logging for debugging",
        "confidence": 0.9
    }
    
    Raises IntentValidationError if response contains code syntax.
    """
    proposal_system = IntentProposalSystem()
    
    # Validate no code syntax in LLM response
    response_str = json.dumps(llm_response)
    forbidden_patterns = ['def ', 'class ', 'import ', '=', '(', ')']
    for pattern in forbidden_patterns:
        if pattern in response_str and not proposal_system._is_safe_reference(pattern, response_str):
            raise IntentValidationError(f"LLM response contains code syntax: {pattern}")
    
    # Parse intent
    intent_type = IntentType(llm_response.get('intent_type'))
    
    intent = proposal_system.propose_intent(
        intent_type=intent_type,
        target_file=target_file,
        criteria=llm_response.get('criteria', {}),
        justification=llm_response.get('justification', ''),
        llm_model=llm_response.get('model', 'unknown'),
        llm_confidence=llm_response.get('confidence', 0.0),
        target_line=llm_response.get('target_line'),
        target_function=llm_response.get('target_function'),
        target_class=llm_response.get('target_class'),
        tokens_used=llm_response.get('tokens_used')
    )
    
    return intent
