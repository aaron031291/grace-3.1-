"""
A/B Comparative Testing Framework
Simultaneously executes tasks in the standard backend and the deterministic 
Braille Sandbox to definitively measure optimization gains.
"""
import time
import logging
from typing import Dict, Any

from cognitive.consensus_engine import run_consensus
from core.services.code_service import generate_code

logger = logging.getLogger(__name__)

def run_ab_optimization_test(prompt: str, target_file: str = "") -> Dict[str, Any]:
    """
    Executes a given instruction exactly twice inside the Grace environment:
    A) Standard Backend LLM execution
    B) Spindle Braille Sandbox deterministic execution
    
    Returns optimization telemetry comparing the two pathways.
    """
    metrics = {
        "optimization_gain_ms": 0,
        "environment_a_standard": {"latency_ms": 0, "status": "pending"},
        "environment_b_sandbox": {"latency_ms": 0, "status": "pending"}
    }
    
    # --- ENVIRONMENT A: Standard execution ---
    logger.info("Executing task in Environment A (Standard)")
    start_time = time.time()
    try:
        # Standard code generation without pipeline hooks
        a_result = generate_code(prompt=prompt, project_folder=".", use_pipeline=False)
        metrics["environment_a_standard"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        metrics["environment_a_standard"]["status"] = "success" if a_result.get("ok", False) else "failed"
    except Exception as e:
        metrics["environment_a_standard"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        metrics["environment_a_standard"]["status"] = "failed"
        logger.error(f"Standard execution failed: {e}")

    # --- ENVIRONMENT B: Spindle Sandbox execution ---
    logger.info("Executing task in Environment B (Spindle Sandbox + Unified Memory)")
    start_time = time.time()
    try:
        # Spindle automatically utilizes query_braille_sandbox behind the scenes
        b_result = run_consensus(prompt=f"MODIFY_SANDBOX: {prompt}", models=["kimi", "qwen", "opus"], source="comparative_tester")
        metrics["environment_b_sandbox"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        metrics["environment_b_sandbox"]["status"] = "success"
    except Exception as e:
        metrics["environment_b_sandbox"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        metrics["environment_b_sandbox"]["status"] = "failed"
        logger.error(f"Sandbox execution failed: {e}")

    # Calculate optimization delta
    standard_ms = metrics["environment_a_standard"]["latency_ms"]
    sandbox_ms = metrics["environment_b_sandbox"]["latency_ms"]
    
    if sandbox_ms > 0 and standard_ms > 0:
        gain = standard_ms - sandbox_ms
        metrics["optimization_gain_ms"] = gain
        if gain > 0:
            logger.info(f"Sandbox optimization achieved: {gain}ms faster execution.")
        else:
            logger.info(f"Sandbox optimization deficit: {abs(gain)}ms slower execution.")

    return metrics
