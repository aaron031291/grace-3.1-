"""
Cognitive Router — Pilar 1 of the Qwen Manifesto
Dynamically routes tasks based on deterministic trust scores and risk levels.
- High-trust/High-complexity tasks -> Opus (High trust cognitive reasoning)
- Low-trust/Low-complexity tasks -> Qwen (Fast, parallelizable execution)
"""

import logging
from typing import Dict, Any, Optional

from cognitive.trust_engine import TrustEngine
from llm_orchestrator.factory import get_llm_client, get_llm_for_task
from llm_orchestrator.multi_llm_client import TaskType

logger = logging.getLogger(__name__)

# Constants for Thresholds
HIGH_TRUST_THRESHOLD = 80.0
MEDIUM_TRUST_THRESHOLD = 60.0

class CognitiveRouter:
    """
    Dynamically routes workloads between models based on:
    a) The complexity/risk of the task.
    b) The established deterministic Trust Score of the component/model.
    """
    
    def __init__(self, trust_engine: Optional[TrustEngine] = None):
        if trust_engine is None:
            # Import here to avoid circular dependencies if necessary
            from cognitive.trust_engine import TrustEngine as TE
            self.trust_engine = TE()
        else:
            self.trust_engine = trust_engine

    def delegate_task(self, prompt: str, task_type: TaskType, component_id: str = "general_orchestrator") -> Dict[str, Any]:
        """
        Routes the task to the most appropriate model based on trust and complexity.
        """
        logger.info(f"[CognitiveRouter] Delegating task for component '{component_id}'. Type: {task_type}")

        # 1. Fetch current trust score for the component triggering the task
        component_score = self.trust_engine._component_scores.get(component_id)
        
        current_trust = 50.0  # Default if unknown
        if component_score:
            current_trust = component_score.trust_score
            
        logger.info(f"[CognitiveRouter] Component '{component_id}' has Deterministic Trust Score: {current_trust:.2f}")

        # 2. Determine required model based on Risk/Complexity (TaskType) and Trust
        if self._is_high_risk_task(task_type) or current_trust < MEDIUM_TRUST_THRESHOLD:
            # If the task is heavily cognitive (fixing code, resolving system errors) 
            # OR the component has a bad trust score, escalate to the smartest, high-trust model (Opus)
            model_provider = "opus"
            logger.info("[CognitiveRouter] Routing to High-Trust Model (Opus) due to high complexity or low component trust.")
        else:
            # If the task is parallelizable/low-risk (data summarization, standard code generation) 
            # AND the component is trusted, delegate to the fast/low-trust model (Qwen).
            model_provider = "ollama" # Assuming Qwen is hosted on ollama
            logger.info("[CognitiveRouter] Routing to Fast/Low-Trust Model (Qwen) for parallelizable execution.")
            
        # 3. Execute
        try:
            if model_provider == "ollama":
                from llm_orchestrator.factory import _ollama_with_model
                client = _ollama_with_model("qwen3:14b")
            else:
                client = get_llm_client(provider=model_provider)
                
            response = client.generate(
                prompt=prompt,
                task_type=task_type,
                temperature=0.2 if self._is_high_risk_task(task_type) else 0.7
            )
            
            # 4. Cross-Model Validation Pipeline (Opus validates Qwen if it was a standard task)
            if model_provider == "ollama" and self._should_cross_validate(task_type):
                response = self._cross_validate_with_opus(prompt, response, task_type)
                
            return {
                "success": True,
                "model_used": model_provider,
                "output": response,
                "routed_trust_score": current_trust
            }
            
        except Exception as e:
            logger.error(f"[CognitiveRouter] Failed to delegate task: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_used": model_provider
            }

    def _is_high_risk_task(self, task_type: TaskType) -> bool:
        """Determines if a task requires deep cognitive reasoning and high safety."""
        high_risk_types = [
            TaskType.CODE_DEBUGGING, 
            TaskType.CODE_REVIEW,
            TaskType.VALIDATION,
            TaskType.REASONING
        ]
        return task_type in high_risk_types
        
    def _should_cross_validate(self, task_type: TaskType) -> bool:
        """Determines if a fast model's output should be validated by the heavyweight model."""
        # For example, even if standard code generation is routed to Qwen, Opus should double check it.
        return task_type == TaskType.CODE_GENERATION
        
    def _cross_validate_with_opus(self, original_prompt: str, qwen_output: str, task_type: TaskType) -> str:
        """
        Pipes Qwen's output to Opus for a deterministic/logical check.
        """
        logger.info("[CognitiveRouter] Initiating Cross-Model Validation Pipeline (Opus validating Qwen).")
        try:
            opus_client = get_llm_client(provider="opus")
            validation_prompt = (
                f"You are the senior validation node. A lighter model generated the following response "
                f"to this prompt: '{original_prompt}'.\n\n"
                f"OUTPUT TO VALIDATE:\n{qwen_output}\n\n"
                f"Identify any logical flaws, hallucinations, or unsafe syntax. If it is correct, return the original text. "
                f"If flawed, return the corrected text."
            )
            
            validated_response = opus_client.generate(
                prompt=validation_prompt,
                task_type=TaskType.CODE_REVIEW,
                temperature=0.1
            )
            return validated_response
        except Exception as e:
            logger.warning(f"[CognitiveRouter] Cross-reference validation failed: {e}. Returning original output.")
            return qwen_output

def get_cognitive_router() -> CognitiveRouter:
    return CognitiveRouter()
