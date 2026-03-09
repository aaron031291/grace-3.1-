"""
consensus_pipeline.py
The Trust-Driven Feedback Loop (Maker-Checker) for Grace.
"""
import logging
from typing import Dict, Any, Optional

from cognitive.synaptic_core import get_synaptic_core

logger = logging.getLogger(__name__)

class ConsensusPipeline:
    """
    Manages iterative, trust-driven feedback loops between models.
    """
    def __init__(self):
        self.synaptic = get_synaptic_core()

    def run_maker_checker(
        self, 
        instruction: str, 
        maker_model: str = "qwen", 
        checker_model: str = "opus",
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Runs a Maker-Checker loop.
        - Maker (e.g., Qwen) generates an initial response.
        - Checker (e.g., Opus) critiques the response.
        - If Checker approves (outputs 'APPROVED'), the loop ends.
        - Else, Maker refines based on the critique.
        """
        logger.info(f"[ConsensusPipeline] Starting Maker-Checker loop ({maker_model} -> {checker_model}) for {max_iterations} iterations max.")
        
        current_draft = ""
        history = []
        
        # Step 1: Initial Draft
        logger.info(f"[ConsensusPipeline] Maker ({maker_model}) drafting initial response...")
        maker_prompt = f"INSTRUCTION:\n{instruction}"
        current_draft = self.synaptic.dispatch(model_id=maker_model, prompt=maker_prompt)
        
        history.append({
            "iteration": 0,
            "role": "maker",
            "model": maker_model,
            "output": current_draft
        })

        for i in range(1, max_iterations + 1):
            logger.info(f"[ConsensusPipeline] Iteration {i}: Checker ({checker_model}) critiquing...")
            
            checker_prompt = (
                f"You are the Checker. Review the following draft for the given instruction.\n"
                f"INSTRUCTION:\n{instruction}\n\n"
                f"DRAFT TO REVIEW:\n{current_draft}\n\n"
                f"If the draft is excellent and requires no changes, reply with exactly the word 'APPROVED' and nothing else.\n"
                f"If it needs improvement, provide a detailed critique on what needs to be fixed. Do not rewrite the draft, just provide the critique."
            )
            critique = self.synaptic.dispatch(model_id=checker_model, prompt=checker_prompt)
            
            history.append({
                "iteration": i,
                "role": "checker",
                "model": checker_model,
                "output": critique
            })

            # Check if the checker approved it
            if "APPROVED" in critique.strip().upper() and len(critique.strip()) < 20:
                logger.info("[ConsensusPipeline] Draft APPROVED by checker.")
                break
                
            logger.info(f"[ConsensusPipeline] Iteration {i}: Maker ({maker_model}) refining draft based on critique...")
            
            refine_prompt = (
                f"INSTRUCTION:\n{instruction}\n\n"
                f"YOUR PREVIOUS DRAFT:\n{current_draft}\n\n"
                f"CRITIQUE FROM EXPERT:\n{critique}\n\n"
                f"Please provide a revised draft that fully addresses the critique."
            )
            current_draft = self.synaptic.dispatch(model_id=maker_model, prompt=refine_prompt)
            
            history.append({
                "iteration": i,
                "role": "maker",
                "model": maker_model,
                "output": current_draft
            })
            
        logger.info("[ConsensusPipeline] Maker-Checker loop complete.")
        
        # Persist the final trusted outcome in the living memory thread
        try:
            self.synaptic.log_to_memory(
                problem=f"Maker-Checker Task: {instruction[:100]}...",
                action=f"Consensus Loop: {maker_model} drafted, {checker_model} critiqued (Iterations: {history[-1]['iteration']})",
                outcome=current_draft,
                trust=0.9 # High trust because it passed the critique loop
            )
        except Exception as e:
            logger.error(f"[ConsensusPipeline] Failed to log outcome to memory: {e}")

        return {
            "final_output": current_draft,
            "history": history,
            "iterations": history[-1]["iteration"] if history else 0
        }

def get_consensus_pipeline() -> ConsensusPipeline:
    return ConsensusPipeline()
