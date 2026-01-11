"""
Cognitive Engine API endpoints.

Provides REST endpoints for viewing OODA decisions, ambiguity tracking,
and invariant validation.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from cognitive.engine import CognitiveEngine
from cognitive.decision_log import DecisionLogger

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/cognitive", tags=["Cognitive Engine"])

# Global decision logger (shared across the app)
_decision_logger: Optional[DecisionLogger] = None


def get_decision_logger() -> DecisionLogger:
    """Get or create decision logger instance."""
    global _decision_logger

    if _decision_logger is None:
        # In production, this would use database storage
        # For now, use in-memory storage
        _decision_logger = DecisionLogger()

    return _decision_logger


@router.get("/decisions/recent", summary="Get recent decisions")
async def get_recent_decisions(
    limit: int = Query(20, ge=1, le=100, description="Maximum decisions to return"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
) -> Dict[str, Any]:
    """
    Get recent OODA loop decisions.

    Returns decisions made in the last N hours, useful for monitoring
    and understanding Grace's decision-making process.

    Args:
        limit: Maximum number of decisions
        hours: Hours to look back

    Returns:
        List of recent decisions with metadata
    """
    try:
        logger_instance = get_decision_logger()

        # Get decisions from the last N hours
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        all_decisions = logger_instance.get_recent_decisions(limit * 2)  # Get more to filter

        # Filter by time and convert to response format
        recent = []
        for decision in all_decisions:
            if decision.created_at >= cutoff_time:
                recent.append({
                    "decision_id": decision.decision_id,
                    "problem_statement": decision.problem_statement,
                    "goal": decision.goal,
                    "status": decision.metadata.get("action_status", "completed"),
                    "strategy": decision.selected_path.get("strategy") if decision.selected_path else None,
                    "created_at": decision.created_at.isoformat(),
                    "elapsed_ms": decision.metadata.get("elapsed_ms", 0)
                })

            if len(recent) >= limit:
                break

        return {
            "decisions": recent,
            "total": len(recent),
            "time_range_hours": hours
        }

    except Exception as e:
        logger.error(f"Failed to get recent decisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent decisions")


@router.get("/decisions/{decision_id}", summary="Get decision details")
async def get_decision_details(decision_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific decision.

    Includes:
    - All OODA phases (Observe, Orient, Decide, Act)
    - Ambiguity ledger
    - Invariant validation results
    - Alternative paths considered
    - Execution outcome

    Args:
        decision_id: Decision ID

    Returns:
        Complete decision details
    """
    try:
        logger_instance = get_decision_logger()
        decision = logger_instance.get_decision(decision_id)

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        # Extract observations
        observations = decision.metadata.get("observations", {})

        # Extract context and constraints
        context_info = decision.metadata.get("context_info", {})
        constraints = decision.metadata.get("constraints", {})

        # Extract ambiguity ledger
        ambiguity_ledger = {
            "known": [
                {"key": k, "value": v}
                for k, v in decision.ambiguity_ledger.known.items()
            ],
            "unknowns": [
                {"key": unk.key, "blocking": unk.blocking}
                for unk in decision.ambiguity_ledger.unknowns
            ],
            "inferred": [
                {
                    "key": inf.key,
                    "value": inf.value,
                    "confidence": inf.confidence
                }
                for inf in decision.ambiguity_ledger.inferred
            ]
        }

        # Build invariant validation results (mock for now)
        invariant_validation = _build_invariant_validation(decision)

        return {
            "decision_id": decision.decision_id,
            "problem_statement": decision.problem_statement,
            "goal": decision.goal,
            "success_criteria": decision.success_criteria,
            "status": decision.metadata.get("action_status", "completed"),
            "created_at": decision.created_at.isoformat(),
            # OODA phases
            "observations": observations,
            "context_info": context_info,
            "constraints": constraints,
            "alternative_paths": decision.alternative_paths,
            "strategy_selected": decision.selected_path.get("strategy") if decision.selected_path else None,
            "action_status": decision.metadata.get("action_status"),
            # Quality metrics
            "quality_score": decision.metadata.get("quality_score", 0),
            "elapsed_ms": decision.metadata.get("elapsed_ms", 0),
            "chunks_returned": decision.metadata.get("chunks_returned", 0),
            # Ambiguity and validation
            "ambiguity_ledger": ambiguity_ledger,
            "invariant_validation": invariant_validation,
            # Metadata
            "is_reversible": decision.is_reversible,
            "impact_scope": decision.impact_scope,
            "complexity_score": decision.complexity_score
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get decision details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch decision details")


@router.get("/stats/summary", summary="Get cognitive engine statistics")
async def get_cognitive_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze")
) -> Dict[str, Any]:
    """
    Get summary statistics for cognitive engine.

    Includes:
    - Total decisions made
    - Success rate
    - Average quality score
    - Strategy distribution
    - Ambiguity trends

    Args:
        hours: Hours to analyze

    Returns:
        Statistical summary
    """
    try:
        logger_instance = get_decision_logger()
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        all_decisions = logger_instance.get_recent_decisions(1000)

        # Filter by time
        recent_decisions = [
            d for d in all_decisions
            if d.created_at >= cutoff_time
        ]

        if not recent_decisions:
            return {
                "total_decisions": 0,
                "success_rate": 0,
                "avg_quality_score": 0,
                "strategy_distribution": {},
                "avg_ambiguity_level": "none",
                "time_range_hours": hours
            }

        # Calculate stats
        total = len(recent_decisions)
        successful = sum(
            1 for d in recent_decisions
            if d.metadata.get("action_status") == "success"
        )
        success_rate = successful / total if total > 0 else 0

        quality_scores = [
            d.metadata.get("quality_score", 0)
            for d in recent_decisions
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Strategy distribution
        strategies = {}
        for d in recent_decisions:
            if d.selected_path and "strategy" in d.selected_path:
                strategy = d.selected_path["strategy"]
                strategies[strategy] = strategies.get(strategy, 0) + 1

        # Ambiguity levels
        ambiguity_counts = {"low": 0, "medium": 0, "high": 0}
        for d in recent_decisions:
            level = d.metadata.get("observations", {}).get("ambiguity_level", "low")
            ambiguity_counts[level] = ambiguity_counts.get(level, 0) + 1

        most_common_ambiguity = max(ambiguity_counts, key=ambiguity_counts.get)

        return {
            "total_decisions": total,
            "success_rate": success_rate,
            "avg_quality_score": avg_quality,
            "strategy_distribution": strategies,
            "ambiguity_distribution": ambiguity_counts,
            "avg_ambiguity_level": most_common_ambiguity,
            "time_range_hours": hours
        }

    except Exception as e:
        logger.error(f"Failed to get cognitive stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


def _build_invariant_validation(decision) -> List[Dict[str, Any]]:
    """
    Build invariant validation results for display.

    In production, these would come from the InvariantValidator.
    For now, we'll generate based on decision properties.
    """
    validations = []

    # Invariant 1: OODA as Primary Control Loop
    validations.append({
        "number": 1,
        "name": "OODA as Primary Control Loop",
        "description": "All decisions must go through Observe → Orient → Decide → Act",
        "passed": True,
        "message": "OODA loop completed successfully"
    })

    # Invariant 2: Ambiguity Accounting
    unknown_count = len(decision.ambiguity_ledger.unknowns)
    blocking_unknowns = len([u for u in decision.ambiguity_ledger.unknowns if u.blocking])

    validations.append({
        "number": 2,
        "name": "Ambiguity Accounting",
        "description": "All unknowns must be tracked and blocking unknowns resolved",
        "passed": blocking_unknowns == 0 or decision.is_reversible,
        "message": f"Tracked {unknown_count} unknowns, {blocking_unknowns} blocking"
    })

    # Invariant 3: Reversibility by Default
    validations.append({
        "number": 3,
        "name": "Reversibility by Default",
        "description": "All actions should be reversible unless justified otherwise",
        "passed": decision.is_reversible or decision.reversibility_justification is not None,
        "message": "Action is reversible" if decision.is_reversible else decision.reversibility_justification
    })

    # Invariant 5: Blast Radius Awareness
    validations.append({
        "number": 5,
        "name": "Blast Radius Awareness",
        "description": "Impact scope must be explicitly defined",
        "passed": decision.impact_scope is not None,
        "message": f"Impact scope: {decision.impact_scope}"
    })

    # Invariant 7: Simplicity > Elegance
    complexity_acceptable = decision.complexity_score <= 0.5 or decision.benefit_score > decision.complexity_score * 2

    validations.append({
        "number": 7,
        "name": "Simplicity Over Elegance",
        "description": "Complexity must be justified by proportional benefit",
        "passed": complexity_acceptable,
        "message": f"Complexity: {decision.complexity_score:.2f}, Benefit: {decision.benefit_score:.2f}"
    })

    # Invariant 9: Bounded Recursion
    validations.append({
        "number": 9,
        "name": "Bounded Recursion",
        "description": "Recursion depth and iterations must be bounded",
        "passed": decision.recursion_depth < decision.max_recursion_depth,
        "message": f"Depth: {decision.recursion_depth}/{decision.max_recursion_depth}"
    })

    # Invariant 10: Optionality > Optimization
    validations.append({
        "number": 10,
        "name": "Optionality Over Optimization",
        "description": "Preserve future options over immediate optimization",
        "passed": decision.preserves_future_options or decision.future_flexibility_metric > 0.7,
        "message": f"Future flexibility: {decision.future_flexibility_metric:.2f}"
    })

    # Invariant 12: Forward Simulation
    alternatives_considered = len(decision.alternative_paths) if decision.alternative_paths else 0

    validations.append({
        "number": 12,
        "name": "Forward Simulation",
        "description": "Multiple alternatives must be considered before deciding",
        "passed": alternatives_considered >= 2,
        "message": f"Considered {alternatives_considered} alternatives"
    })

    return validations
