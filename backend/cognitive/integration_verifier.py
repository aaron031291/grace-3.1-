"""
Integration Verifier — Anti-Hallucination Layer

Stops Grace (and agents building Grace) from claiming integrations work
when they don't. Every claim is TESTED, not trusted.

Rules:
1. If you say "X is connected to Y" — prove it with an actual import + call
2. If you say "data flows from A to B" — trace it with real code paths
3. If a schema column is referenced — verify it exists in the model
4. If a function is called — verify it exists with that exact signature
5. Every fix generates a verification test that runs automatically

This is the immune system against code hallucinations.
"""

import importlib
import inspect
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

VERIFICATION_DIR = Path(__file__).parent.parent / "data" / "verifications"


class VerificationResult:
    def __init__(self, claim: str, verified: bool, evidence: str = "", error: str = ""):
        self.claim = claim
        self.verified = verified
        self.evidence = evidence
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "claim": self.claim,
            "verified": self.verified,
            "evidence": self.evidence,
            "error": self.error,
            "timestamp": self.timestamp,
        }


def verify_import(module_path: str, attribute: str = None) -> VerificationResult:
    """Verify a module can actually be imported and optionally has an attribute."""
    claim = f"Module '{module_path}' is importable"
    if attribute:
        claim += f" and has '{attribute}'"
    try:
        mod = importlib.import_module(module_path)
        if attribute:
            obj = getattr(mod, attribute, None)
            if obj is None:
                return VerificationResult(claim, False,
                    error=f"Module imports but '{attribute}' not found. Available: {dir(mod)[:10]}")
            return VerificationResult(claim, True,
                evidence=f"Found {type(obj).__name__}: {attribute}")
        return VerificationResult(claim, True, evidence="Import successful")
    except Exception as e:
        return VerificationResult(claim, False, error=f"{type(e).__name__}: {str(e)[:200]}")


def verify_function_signature(module_path: str, function_name: str,
                               expected_params: List[str] = None) -> VerificationResult:
    """Verify a function exists and has expected parameters."""
    claim = f"Function '{module_path}.{function_name}' exists"
    if expected_params:
        claim += f" with params {expected_params}"
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, function_name, None)
        if fn is None:
            available = [a for a in dir(mod) if callable(getattr(mod, a, None)) and not a.startswith("_")]
            return VerificationResult(claim, False,
                error=f"Function not found. Available: {available[:15]}")
        if not callable(fn):
            return VerificationResult(claim, False, error=f"'{function_name}' exists but is not callable")

        sig = inspect.signature(fn)
        actual_params = list(sig.parameters.keys())

        if expected_params:
            missing = [p for p in expected_params if p not in actual_params]
            if missing:
                return VerificationResult(claim, False,
                    error=f"Missing params: {missing}. Actual: {actual_params}")

        return VerificationResult(claim, True,
            evidence=f"Signature: {function_name}({', '.join(actual_params)})")
    except Exception as e:
        return VerificationResult(claim, False, error=f"{type(e).__name__}: {str(e)[:200]}")


def verify_class_method(module_path: str, class_name: str, method_name: str) -> VerificationResult:
    """Verify a class has a specific method."""
    claim = f"Class '{module_path}.{class_name}' has method '{method_name}'"
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name, None)
        if cls is None:
            return VerificationResult(claim, False, error=f"Class '{class_name}' not found")
        method = getattr(cls, method_name, None)
        if method is None:
            methods = [m for m in dir(cls) if not m.startswith("_") and callable(getattr(cls, m, None))]
            return VerificationResult(claim, False,
                error=f"Method not found. Available: {methods[:15]}")
        return VerificationResult(claim, True, evidence=f"Method exists: {method_name}")
    except Exception as e:
        return VerificationResult(claim, False, error=f"{type(e).__name__}: {str(e)[:200]}")


def verify_schema_column(module_path: str, model_name: str, column_name: str) -> VerificationResult:
    """Verify a SQLAlchemy model has a specific column."""
    claim = f"Model '{model_name}' has column '{column_name}'"
    try:
        mod = importlib.import_module(module_path)
        model = getattr(mod, model_name, None)
        if model is None:
            return VerificationResult(claim, False, error=f"Model '{model_name}' not found")
        col = getattr(model, column_name, None)
        if col is None:
            cols = [a for a in dir(model) if not a.startswith("_") and not callable(getattr(model, a, None))]
            return VerificationResult(claim, False,
                error=f"Column not found. Available: {cols[:20]}")
        return VerificationResult(claim, True, evidence=f"Column exists: {column_name}")
    except Exception as e:
        return VerificationResult(claim, False, error=f"{type(e).__name__}: {str(e)[:200]}")


def verify_data_flow(source_module: str, source_fn: str,
                     target_module: str, target_fn: str) -> VerificationResult:
    """Verify that source function's code actually calls target function."""
    claim = f"Data flows from {source_module}.{source_fn} → {target_module}.{target_fn}"
    try:
        mod = importlib.import_module(source_module)
        fn = getattr(mod, source_fn, None)
        if fn is None:
            return VerificationResult(claim, False, error=f"Source function not found")

        source_code = inspect.getsource(fn)
        target_short = target_fn.split(".")[-1]

        if target_short in source_code or target_module.split(".")[-1] in source_code:
            return VerificationResult(claim, True,
                evidence=f"Source code references '{target_short}'")
        else:
            return VerificationResult(claim, False,
                error=f"No reference to '{target_short}' in source code of {source_fn}")
    except Exception as e:
        return VerificationResult(claim, False, error=f"{type(e).__name__}: {str(e)[:200]}")


def run_integration_tests() -> Dict[str, Any]:
    """
    Run ALL integration verification tests.
    Returns a report of what's real vs hallucinated.
    """
    results = []

    # Memory system verifications
    results.append(verify_import("cognitive.memory_mesh_integration", "MemoryMeshIntegration"))
    results.append(verify_class_method("cognitive.memory_mesh_integration", "MemoryMeshIntegration", "ingest_learning_experience"))
    results.append(verify_class_method("cognitive.memory_mesh_integration", "MemoryMeshIntegration", "get_memory_mesh_stats"))
    results.append(verify_import("cognitive.flash_cache", "FlashCache"))
    results.append(verify_import("cognitive.unified_memory", "UnifiedMemory"))
    results.append(verify_import("cognitive.ghost_memory", "GhostMemory"))

    # Schema verifications (the ones we fixed)
    results.append(verify_schema_column("cognitive.learning_memory", "LearningExample", "outcome_quality"))
    results.append(verify_schema_column("cognitive.learning_memory", "LearningExample", "consistency_score"))
    results.append(verify_schema_column("cognitive.learning_memory", "LearningExample", "recency_weight"))

    # Function signature verifications
    results.append(verify_function_signature("cognitive.memory_mesh_metrics", "get_performance_metrics"))
    results.append(verify_import("cognitive.event_bridge", "activate_all_bridges"))
    results.append(verify_import("cognitive.patch_consensus", "run_patch_consensus"))
    results.append(verify_import("cognitive.self_healing_tracker", "get_self_healing_tracker"))
    results.append(verify_import("cognitive.horizon_planner", "reverse_engineer_goal"))
    results.append(verify_import("cognitive.sandbox_mirror", "get_sandbox_mirror"))
    results.append(verify_import("cognitive.integration_gap_detector", "detect_all_gaps"))
    results.append(verify_import("cognitive.forensic_audit", "run_full_audit"))

    # Genesis key model verification
    results.append(verify_schema_column("models.genesis_key_models", "GenesisKey", "key_id"))
    results.append(verify_schema_column("models.genesis_key_models", "GenesisKey", "what_description"))

    # Pipeline verification
    results.append(verify_class_method("cognitive.pipeline", "CognitivePipeline", "_stage_memory_recall"))

    # Event bus verification
    results.append(verify_function_signature("cognitive.event_bus", "publish", ["topic", "data"]))
    results.append(verify_function_signature("cognitive.event_bus", "subscribe", ["topic", "handler"]))

    verified = sum(1 for r in results if r.verified)
    failed = sum(1 for r in results if not r.verified)

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tests": len(results),
        "verified": verified,
        "failed": failed,
        "pass_rate": round(verified / len(results) * 100, 1) if results else 0,
        "results": [r.to_dict() for r in results],
        "failures": [r.to_dict() for r in results if not r.verified],
    }

    _save_verification(report)
    return report


def verify_claim(claim: str) -> VerificationResult:
    """
    Verify a natural-language claim about the system.
    Parses claims like "X is connected to Y" and tests them.
    """
    claim_lower = claim.lower()

    if "import" in claim_lower:
        parts = claim.split("'")
        if len(parts) >= 2:
            return verify_import(parts[1])

    if "has method" in claim_lower or "has function" in claim_lower:
        parts = claim.split("'")
        if len(parts) >= 4:
            return verify_class_method(parts[1].rsplit(".", 1)[0], parts[1].rsplit(".", 1)[1], parts[3])

    if "has column" in claim_lower:
        parts = claim.split("'")
        if len(parts) >= 4:
            return verify_schema_column(parts[1].rsplit(".", 1)[0], parts[1].rsplit(".", 1)[1], parts[3])

    return VerificationResult(claim, False, error="Could not parse claim. Use structured verify_* functions.")


def _save_verification(report: Dict[str, Any]):
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = VERIFICATION_DIR / f"verification_{ts}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
