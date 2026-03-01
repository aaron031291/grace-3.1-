"""
Consensus Engine — re-export from cognitive.consensus_engine.

This is the canonical import path going forward.
All consensus logic stays in cognitive/consensus_engine.py (the real implementation).
This module provides the clean import path for the new architecture.
"""

from cognitive.consensus_engine import (
    run_consensus,
    layer1_deliberate,
    layer2_consensus,
    layer3_align,
    layer4_verify,
    get_available_models,
    queue_autonomous_query,
    get_batch_queue,
    run_batch,
    MODEL_REGISTRY,
    ModelResponse,
    ConsensusResult,
    _check_model_available,
    _get_client,
    _build_model_registry,
)

__all__ = [
    "run_consensus",
    "layer1_deliberate",
    "layer2_consensus",
    "layer3_align",
    "layer4_verify",
    "get_available_models",
    "queue_autonomous_query",
    "get_batch_queue",
    "run_batch",
    "MODEL_REGISTRY",
    "ModelResponse",
    "ConsensusResult",
    "_check_model_available",
    "_get_client",
    "_build_model_registry",
]
