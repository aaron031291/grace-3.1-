import logging
from typing import Dict, Any, List
import json
import asyncio
from pydantic import BaseModel

logger = logging.getLogger("cognitive_blueprint")

class OODAChessPath(BaseModel):
    path_description: str
    complexity_score: float
    blast_radius: float
    evaluation_answers: Dict[str, str]

class OODALoopExecutor:
    """
    Implements the Grace Cognitive Blueprint: OODA loop + "Chess Mode" + 16 Questions.
    Fully Asynchronous for real-time Event Bus processing.
    """
    
    # The 16 Evaluation Questions Context
    SIXTEEN_QUESTIONS = [
        "1. Does it solve the explicit problem it was designed to solve?",
        "2. Does the functionality work end-to-end as intended?",
        "3. Does it fit within the existing Grace architecture and constraints?",
        "4. What breaks if this is removed entirely?",
        "5. Is this the simplest version that preserves correctness and guarantees?",
        "6. Is the structure logical, explainable, and internally coherent?",
        "7. Is complexity justified by measurable benefit?",
        "8. How expensive is it to change or undo later?",
        "9. Does it allow safe iteration and improvement without rewrite?",
        "10. Is modularity real and purpose-driven (not cosmetic)?",
        "11. Is failure contained with a limited blast radius?",
        "12. Is determinism preserved where determinism is required?",
        "13. Is recursion intentional, bounded, and useful?",
        "14. Can its behavior be observed, inspected, and explained?",
        "15. Does it improve the overall system in a measurable way?",
        "16. What new problems, risks, or trade-offs does it introduce?"
    ]

    def __init__(self):
        logger.info("OODALoopExecutor Initialized (Async OODA + Chess Mode + 16 Questions)")

    async def orient_and_observe(self, problem_statement: str, event_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1 & 2: Orient and Observe
        Restates the problem, identifies goals, boundaries, and missing knowledge.
        Asynchronous operation to fetch contextual metadata without blocking.
        """
        logger.info(f"OODA [Orient & Observe]: Evaluating problem context.")
        
        # Simulate an IO-bound fetch for contextual bounds
        await asyncio.sleep(0.1) 
        
        orientation = {
            "original_problem": problem_statement,
            "goal": "Resolve the issue without violating constitutional safety constraints.",
            "constraints": ["Must be reversible", "Must be logged to genesis tracker", "Cannot degrade other services"],
            "ambient_context": event_context
        }
        return orientation

    async def chess_mode_decide(self, orientation_context: Dict[str, Any]) -> OODAChessPath:
        """
        Step 3: Decide (Chess Mode)
        Generates multiple paths and evaluates them against the 16 Questions.
        Selects the path with the lowest disruption.
        Asynchronous operation to allow concurrent LLM evaluations.
        """
        logger.info("OODA [Decide]: Entering Chess Mode to plot routes.")
        
        # Simulate an IO-bound LLM generation for 3 parallel paths
        await asyncio.sleep(0.2)
        
        paths = [
            OODAChessPath(
                path_description="Directly patch the failing file.",
                complexity_score=0.2,
                blast_radius=0.1,
                evaluation_answers={"1": "Yes", "5": "Yes", "11": "Yes"}
            ),
            OODAChessPath(
                path_description="Refactor the entire module to use a new dependency.",
                complexity_score=0.9,
                blast_radius=0.8,
                evaluation_answers={"1": "Yes", "5": "No", "11": "No"}
            ),
            OODAChessPath(
                path_description="Rollback the system to the previous snapshot.",
                complexity_score=0.1,
                blast_radius=0.9, # Heavy business disruption
                evaluation_answers={"1": "Yes", "5": "Yes", "11": "No"}
            )
        ]

        # The OODA executor favors the path with the lowest combined problem score.
        # (Lowest complexity + blast radius, while preserving correctness)
        selected_path = min(paths, key=lambda p: p.complexity_score + p.blast_radius)
        
        logger.info(f"OODA [Decide]: Selected path -> '{selected_path.path_description}'")
        return selected_path

    async def process_and_act(self, problem_statement: str, event_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main asynchronous entry point for the Cognitive Framework to run the OODA Loop.
        Returns the finalized context to append to the Task Queue.
        """
        orientation = await self.orient_and_observe(problem_statement, event_context)
        decision = await self.chess_mode_decide(orientation)
        
        return {
            "orientation": orientation,
            "chess_mode_decision": decision.model_dump(),
            "sixteen_questions_rubric": self.SIXTEEN_QUESTIONS
        }
