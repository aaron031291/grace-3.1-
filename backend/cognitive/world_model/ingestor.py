"""
World Model Ingestor — Neural-Symbolic Situational Awareness

This module serves as Grace's sensory input array. It receives unstructured
or semi-structured external data (e.g., logs, environment sensor readings,
human behavioral data, web events) and uses LLMs to extract actionable
semantic and causal meaning.

It directly wires into Magma Memory's Causal Graph to permanently store
the causal chains defining real-world physics and dependencies.
"""

import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from llm_orchestrator.llm_orchestrator import LLMOrchestrator, TaskType
from cognitive.magma_bridge import get_magma_graphs
from cognitive.magma.causal_inference import LLMCausalInferencer

logger = logging.getLogger(__name__)

class WorldModelIngestor:
    def __init__(self):
        self.orchestrator = LLMOrchestrator()
        try:
            graphs = get_magma_graphs()
            # Wrap the Orchestrator with the Magma Causal Inferencer
            self.causal_engine = LLMCausalInferencer(
                graphs=graphs,
                # Provide a lambda to route prompts to our LLM Engine
                llm_fn=lambda prompt: self._execute_llm_extraction(prompt)
            )
        except Exception as e:
            logger.error(f"[WORLD-MODEL] Failed to initialize Causal Engine: {e}")
            self.causal_engine = None

    def _execute_llm_extraction(self, prompt: str) -> str:
        """Helper to route Magma Causal Prompts through the Orchestrator"""
        result = self.orchestrator.execute_task(
            prompt=prompt,
            task_type=TaskType.REASONING,
            require_consensus=False  # Fast extraction
        )
        if result.success:
            return result.content
        return "Extraction Failed"

    def ingest_event_stream(self, data_payload: str, source: str = "external_sensor") -> Dict[str, Any]:
        """
        Ingest raw external data, extract semantic meaning, and generate Causal Claims
        to persist in Magma's Causal Graph.
        
        Args:
            data_payload: The raw text/JSON of the external event.
            source: Where this data came from.
            
        Returns:
            Dict containing ingestion stats and generated edges.
        """
        logger.info(f"[WORLD-MODEL] Ingesting external sensor data from source: {source}")
        
        if not self.causal_engine:
            return {"status": "error", "message": "Magma Causal Engine offline."}
            
        # 1. Ask the LLM to parse the messy sensor data into causal claims
        try:
            claims = self.causal_engine.infer_causation(text=data_payload, use_llm=True)
            
            if not claims:
                logger.info("[WORLD-MODEL] No actionable causal claims found in event stream.")
                return {"status": "success", "edges_created": 0, "message": "No claims detected."}
                
            # 2. Store the claims permanently in Magma's Causal Graph
            genesis_key = f"sensor_event_{uuid.uuid4().hex[:8]}"
            
            from cognitive.validators.tla_validator import get_tla_validator
            tla_validator = get_tla_validator()
            
            # Format requested edges for TLA
            requested_edges = [(c.cause, c.effect, c.confidence) for c in claims]
            
            # Run formal Model Checking
            tla_validation = tla_validator.validate_causal_graph_update(
                new_edges=requested_edges, 
                full_graph_nodes=self.causal_engine.graphs.causal.nodes
            )
            
            if tla_validation["status"] == "REJECTED":
                logger.error(f"[WORLD-MODEL] TLA+ Validator Rejected Update: {tla_validation['reason']}")
                return {
                    "status": "error",
                    "reason": tla_validation['reason'],
                    "tla_spec": tla_validation["tla_spec"]
                }
            
            # Use original store_claims method from LLMCausalInferencer
            edge_ids = self.causal_engine.store_claims(claims=claims, genesis_key_id=genesis_key)
            edges_created = len(edge_ids)
            
            logger.info(f"[WORLD-MODEL] Extracted and stored {edges_created} causal edges into Magma after TLA+ validation.")
            
            return {
                "status": "success",
                "edges_created": edges_created,
                "claims": [{"cause": c.cause, "effect": c.effect, "confidence": c.confidence} for c in claims],
                "genesis_key": genesis_key
            }
            
        except Exception as e:
            logger.error(f"[WORLD-MODEL] Ingestion failed: {e}")
            return {"status": "error", "message": str(e)}

# Singleton instance
_ingestor = None

def get_world_model_ingestor() -> WorldModelIngestor:
    global _ingestor
    if _ingestor is None:
        _ingestor = WorldModelIngestor()
    return _ingestor
