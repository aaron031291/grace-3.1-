"""
Synaptic Core — The Central Orchestration Bus & Living Memory Thread.

Allows Grace to dynamically invoke specific models, pass intermediate thoughts
between them (cross-model critique), and log the final synthesized
conclusion directly into UnifiedMemory, creating a continuous thread of learning.
"""
import logging
import json
from typing import List, Dict, Any, Optional

from llm_orchestrator.factory import get_llm_client, get_llm_for_task
from cognitive.unified_memory import get_unified_memory

logger = logging.getLogger(__name__)

class SynapticCore:
    """
    Orchestration Bus for Grace's Multi-Model architecture.
    """
    
    def __init__(self):
        # Attach to the unified memory singleton directly
        self.memory = get_unified_memory()

    def dispatch(self, model_id: str, prompt: str, system_prompt: str = "") -> str:
        """
        Send a one-off prompt to a specific model.
        
        Args:
            model_id: 'opus', 'kimi', 'qwen', 'reasoning', etc.
            prompt: The text prompt.
            system_prompt: Optional system persona setup.
        """
        logger.info(f"[SynapticCore] Dispatching prompt to {model_id}...")
        
        # Route colloquial model names to strict backend providers/tasks
        if model_id in ["qwen", "reasoning", "fast", "code", "ollama"]:
            provider = "ollama"
        else:
            provider = model_id
            
        try:
            if provider == "ollama":
                from llm_orchestrator.factory import _ollama_with_model
                client = _ollama_with_model("qwen3:14b")
            elif provider == "runpod":
                client = get_llm_client(provider="runpod")
            else:
                client = get_llm_client(provider=provider)
        except Exception as e:
            logger.error(f"[SynapticCore] Failed to load provider {provider}: {e}")
            return f"Error: Provider {provider} failed to load."
        
        try:
            response = client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=4096
            )
            return response if isinstance(response, str) else str(response)
        except Exception as e:
            logger.error(f"[SynapticCore] Generation failed for {model_id}: {e}")
            return f"Error: Model {model_id} failed to generate."

    def orchestrate_chain(self, chain_definition: List[Dict[str, str]], initial_state: str = "") -> Dict[str, Any]:
        """
        Run a multi-model critique loop. Output of step N is prepended/injected into step N+1.
        
        Args:
            chain_definition: list of steps, e.g. [{"model": "opus", "instruction": "Draft the plan", "system_prompt": "..."}]
            initial_state: The starting context or problem statement.
        """
        logger.info(f"[SynapticCore] Starting orchestration chain with {len(chain_definition)} steps.")
        
        history = []
        current_state = initial_state
        
        for step_idx, step in enumerate(chain_definition):
            model = step.get("model", "qwen")
            instruction = step.get("instruction", "")
            system_prompt = step.get("system_prompt", "You are an expert autonomous component of Grace.")
            
            logger.info(f"[SynapticCore] Executing Chain Step {step_idx + 1}/{len(chain_definition)} with {model}.")
            
            # Construct the prompt by merging the instruction and the current state context
            merged_prompt = f"{instruction}\n\nCONTEXT FROM PREVIOUS STEP:\n{current_state}"
            
            response = self.dispatch(model_id=model, prompt=merged_prompt, system_prompt=system_prompt)
            current_state = response
            
            history.append({
                "step": step_idx + 1,
                "model": model,
                "instruction": instruction,
                "output": response
            })
            
        logger.info("[SynapticCore] Orchestration chain complete.")
        return {
            "final_output": current_state,
            "history": history
        }

    def log_to_memory(self, problem: str, action: str, outcome: str, trust: float = 0.8) -> bool:
        """
        Persist an episodic result into UnifiedMemory.
        
        Args:
            problem: The initial trigger or question.
            action: The chain of actions taken (e.g. models queried).
            outcome: The final result text.
            trust: The confidence level of this outcome.
        """
        logger.info("[SynapticCore] Attempting to log result to UnifiedMemory.")
        
        try:
            success = self.memory.store_episode(
                problem=problem,
                action={"orchestration_chain": action},
                outcome={"aligned_output": outcome},
                trust=trust,
                source="synaptic_core_orchestration",
                trust_coin="VVT_PLATINUM_COIN"  # Pass the Trust Gate requirements for system updates
            )
            if success:
                logger.info("[SynapticCore] Successfully logged to UnifiedMemory.")
            else:
                logger.warning("[SynapticCore] Failed to log episodic data to UnifiedMemory.")
            return success
        except Exception as e:
            logger.exception(f"[SynapticCore] Error logging to memory: {e}")
            return False

def get_synaptic_core() -> SynapticCore:
    return SynapticCore()
