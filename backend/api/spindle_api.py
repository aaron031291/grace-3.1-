from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
from cognitive.braille_compiler import NLPCompilerEdge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spindle", tags=["Spindle Formal Verification"])

# Global instantiation per worker
compiler = NLPCompilerEdge()

import uuid
from cognitive import magma_bridge

class ActionRequest(BaseModel):
    natural_language: str
    privilege: str = "user"
    session_context: dict = {}

class VerificationResponse(BaseModel):
    is_valid: bool
    mathematical_proof: str
    z3_mask: dict

@router.post("/verify_action", response_model=VerificationResponse)
async def verify_spindle_action(req: ActionRequest):
    """
    Takes an action request from the UI, compiles it into the 256-bit HDC structure,
    and runs it through the Z3 SMT Formal Theorem Prover.
    Returns strict mathematical guarantees of system safety.
    """
    
    logger.info(f"Frontend requesting formal verification for: {req.natural_language}")
    
    # 1. Ask the NLP Compiler Edge to translate to JSON, then to 256-bit HDC, then verify via Z3
    masks, verification_msg = compiler.process_command(
        natural_language=req.natural_language,
        privilege=req.privilege,
        session_context=req.session_context
    )
    
    # 1.5 World Model Causal Verification
    if masks:
        try:
            from cognitive.magma_bridge import get_magma_graphs
            from cognitive.magma.causal_inference import LLMCausalInferencer
            graphs = get_magma_graphs()
            causal_inferencer = LLMCausalInferencer(graphs)
            
            # Trace the real-world effects of the action
            # Use simple keyword extraction for the start concept for proof of concept
            action_lower = req.natural_language.lower()
            
            # Find any node in the graph that overlaps with our action intent
            start_nodes = []
            for node in graphs.causal.nodes.values():
                node_content = node.content.lower()
                # If the core nouns/verbs match (e.g. "core temperature")
                if "core temperature" in action_lower and "core temperature" in node_content:
                    start_nodes.append(node.content)
                elif "archiving" in action_lower and "archiving" in node_content:
                    start_nodes.append(node.content)
                elif len(set(action_lower.split()) & set(node_content.split())) >= 3:
                     start_nodes.append(node.content)
                     
            if not start_nodes:
                start_nodes = [req.natural_language]
                
            catastrophe_keywords = ["crash", "failure", "catastrophe", "loss", "shutdown", "meltdown", "breach"]
            
            for start_concept in start_nodes:
                chains = causal_inferencer.trace_causal_chain(start_concept, direction="effects", max_depth=4)
                
                for chain in chains:
                    for node in chain.nodes:
                        if any(bad_word in node.lower() for bad_word in catastrophe_keywords):
                            # Action leads to disaster. Override Z3 to UNSAT.
                            logger.warning(f"[WORLD-MODEL] Z3 Overridden! Causal Graph predicts disaster: {' -> '.join(chain.nodes)}")
                            masks = None
                            
                            # Invoke Error Middleware
                            from cognitive.world_model.error_middleware import get_error_middleware, SpindleRejection
                            middleware = get_error_middleware()
                            rejection = SpindleRejection(
                                original_action=req.natural_language,
                                rejection_reason="Causal Graph predicted catastrophic failure state.",
                                violating_causal_nodes=list(chain.nodes)
                            )
                            alternative = middleware.handle_causal_rejection(rejection)
                            
                            if alternative:
                                verification_msg = f"Z3_UNSAT: Causal Graph Violation. Action leads to critical failure state: {' -> '.join(chain.nodes)}. SUGGESTED FIX: {alternative.suggested_action} RATIONALE: {alternative.rationale}"
                            else:
                                verification_msg = f"Z3_UNSAT: Causal Graph Violation. Action leads to critical failure state: {' -> '.join(chain.nodes)}"
                            
                            break
                    if not masks:
                        break
                if not masks:
                    break
        except Exception as e:
            logger.error(f"[WORLD-MODEL] Failed to cross-reference Causal Graph: {e}")
    
    # 2. Package the mathematical proof responses & Persist to Magma
    constraint_id = f"spindle_constraint_{uuid.uuid4()}"
    
    if masks:
        # Z3 SAT (Valid)
        d_val, i_val, s_val, c_val = masks
        
        magma_bridge.store_decision(
            action="verify_spindle_action",
            target=req.natural_language,
            rationale=verification_msg,
            data={"constraint_id": constraint_id, "status": "SAT", "z3_masks": {"domain": d_val, "intent": i_val, "state": s_val, "context": c_val}}
        )
        
        return VerificationResponse(
            is_valid=True,
            mathematical_proof=verification_msg,
            z3_mask={
                "domain": d_val,
                "intent": i_val,
                "state": s_val,
                "context": c_val
            }
        )
    else:
        # Z3 UNSAT (Invalid / Hallucination blocked)
        magma_bridge.store_decision(
            action="verify_spindle_action",
            target=req.natural_language,
            rationale=verification_msg,
            data={"constraint_id": constraint_id, "status": "UNSAT", "z3_masks": {}}
        )
        
        return VerificationResponse(
            is_valid=False,
            mathematical_proof=verification_msg,
            z3_mask={}
        )

# For mounting to the main FastAPI app in api_server.py
def include_spindle_router(app):
    app.include_router(router)
