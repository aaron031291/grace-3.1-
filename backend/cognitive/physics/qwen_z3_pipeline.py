import os
import json
import logging
from typing import Dict, Any, Optional

from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
from llm_orchestrator.multi_llm_client import TaskType

logger = logging.getLogger(__name__)

class QwenZ3Pipeline:
    """
    Translates Natural Language constraints into Formal Z3 SMT logic.
    Provides strict template scaffolding to prevent LLM hallucinations.
    """
    
    def __init__(self):
        self.orchestrator = get_llm_orchestrator()

    def generate_z3_constraint(self, natural_language_rule: str) -> Optional[str]:
        """
        Takes a natural language rule (e.g., "Standard users cannot delete active databases")
        and returns a formal Python Z3 AST string.
        """
        prompt = f"""
        You are a formal verification engineer. Translate the following English constraint into a precise Z3 SMT assertion.
        
        Available BitVec boolean masks (Assume they are already defined variables):
        - self.domain_mask
        - self.intent_mask
        - self.state_mask
        - self.ctx_mask
        
        Available Constants:
        Domains: DOMAIN_DATABASE, DOMAIN_API, DOMAIN_MEMORY, DOMAIN_NETWORK, DOMAIN_SYS_CONF
        Intents: INTENT_START, INTENT_STOP, INTENT_DELETE, INTENT_QUERY, INTENT_GRANT, INTENT_REPAIR
        States: STATE_FAILED, STATE_IMMUTABLE, STATE_ACTIVE, STATE_UNKNOWN, STATE_STOPPED
        Contexts: PRIV_ADMIN, PRIV_USER, PRIV_SYSTEM, CTX_MAINTENANCE, CTX_EMERGENCY, CTX_ELEVATED
        
        Rule to Translate: "{natural_language_rule}"
        
        You MUST output ONLY valid Python code using the `z3` library. 
        Use `self.solver.add(...)` and `Implies(..., ...)`.
        Do not include markdown blocks, just the raw code string.
        
        Example Output for "Cannot delete immutable":
        self.solver.add(
            Implies(
                And((self.intent_mask & INTENT_DELETE) != 0, (self.state_mask & STATE_IMMUTABLE) != 0),
                False
            )
        )
        """
        
        try:
            # We use Qwen (which handles TaskType.GENERAL by default) to generate the code
            result = self.orchestrator.execute_task(
                prompt=prompt,
                task_type=TaskType.GENERAL,
                require_consensus=False,  
                require_verification=False, 
                require_grounding=False
            )
            
            if result.success:
                code_snippet = result.content.strip()
                # Clean up if the LLM hallucinated markdown code blocks
                if code_snippet.startswith("```python"):
                    code_snippet = code_snippet[9:]
                if code_snippet.startswith("```"):
                    code_snippet = code_snippet[3:]
                if code_snippet.endswith("```"):
                    code_snippet = code_snippet[:-3]
                    
                return code_snippet.strip()
            else:
                logger.error(f"Qwen failed to generate Z3 constraint: {result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Z3 Generation Pipeline crashed: {e}")
            return None
