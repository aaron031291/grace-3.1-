"""
Unified Knowledge Ingestion API - All knowledge pathways into Grace.

Endpoints for all ingestion sources:
- LLM knowledge on request
- Simulation scenarios
- Replay learning
- Self-distillation
- Multi-agent debate
- Benchmark mining
- Manual knowledge items

All operations tracked with Genesis Keys.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from cognitive.unified_knowledge_ingestion import (
    UnifiedKnowledgeIngestion,
    KnowledgeItem,
    IngestionSource,
    KnowledgeType,
    create_unified_ingestion
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingestion", tags=["Knowledge Ingestion"])

# Global instance
_ingestion_system: Optional[UnifiedKnowledgeIngestion] = None


def get_ingestion_system() -> UnifiedKnowledgeIngestion:
    """Get or create ingestion system."""
    global _ingestion_system
    if _ingestion_system is None:
        _ingestion_system = create_unified_ingestion()
    return _ingestion_system


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class LLMKnowledgeRequest(BaseModel):
    """Request knowledge from LLM."""
    topic: str = Field(..., description="Topic to learn about")
    template: str = Field("explain_concept", description="Request template")
    domain: Optional[str] = Field(None, description="Knowledge domain")
    language: Optional[str] = Field(None, description="Programming language (for code patterns)")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class SimulationRequest(BaseModel):
    """Generate simulation scenarios."""
    scenario_type: str = Field(..., description="Type of scenario")
    domain: str = Field("general", description="Domain context")
    difficulty: str = Field("medium", description="Difficulty level")
    count: int = Field(5, description="Number of scenarios")


class FailureRecordRequest(BaseModel):
    """Record a failure for replay learning."""
    task: Dict[str, Any] = Field(..., description="Task that failed")
    attempt: Dict[str, Any] = Field(..., description="Attempt details")
    error: str = Field(..., description="Error message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ReplayRequest(BaseModel):
    """Replay past failures."""
    count: int = Field(10, description="Number to replay")
    strategy: str = Field("random", description="Selection strategy")


class DistillRequest(BaseModel):
    """Distill knowledge."""
    domain: Optional[str] = Field(None, description="Domain to distill")
    min_sample_size: int = Field(5, description="Minimum patterns to merge")
    similarity_threshold: float = Field(0.8, description="Similarity threshold")


class DebateRequest(BaseModel):
    """Run multi-agent debate."""
    topic: str = Field(..., description="Topic to debate")
    domain: Optional[str] = Field(None, description="Knowledge domain")
    initial_positions: Optional[List[str]] = Field(None, description="Starting positions")


class BenchmarkMineRequest(BaseModel):
    """Mine patterns from benchmarks."""
    benchmark_name: str = Field(..., description="Benchmark name")
    results: List[Dict[str, Any]] = Field(..., description="Benchmark results")


class ManualKnowledgeRequest(BaseModel):
    """Manually add knowledge."""
    content: str = Field(..., description="Knowledge content")
    knowledge_type: str = Field("fact", description="Type of knowledge")
    domain: Optional[str] = Field(None, description="Domain")
    tags: List[str] = Field(default_factory=list, description="Tags")
    confidence: float = Field(0.7, description="Confidence level")


# =============================================================================
# STATUS AND INFO
# =============================================================================

@router.get("/status")
async def get_ingestion_status():
    """Get status of all ingestion systems."""
    system = get_ingestion_system()
    return {
        "active": True,
        "stats": system.get_stats(),
        "sources": [s.value for s in IngestionSource],
        "knowledge_types": [k.value for k in KnowledgeType]
    }


@router.get("/sources")
async def get_available_sources():
    """Get all available ingestion sources."""
    return {
        "current_sources": [
            {"value": "sandbox_practice", "description": "Self-generated learning from sandbox"},
            {"value": "oracle_llm", "description": "Oracle/LLM integration"},
            {"value": "federated_learning", "description": "Cross-domain pattern transfer"},
            {"value": "file_ingestion", "description": "Documents and code files"},
            {"value": "github_extractor", "description": "GitHub patterns and fixes"},
            {"value": "self_healing", "description": "Self-healing cycle learnings"},
            {"value": "user_feedback", "description": "User corrections and ratings"},
            {"value": "external_knowledge", "description": "External sources (arXiv, etc.)"}
        ],
        "new_sources": [
            {"value": "simulation_engine", "description": "Synthetic scenario generation"},
            {"value": "replay_learning", "description": "Learn from past failures"},
            {"value": "self_distillation", "description": "Compress and refine knowledge"},
            {"value": "multi_agent_debate", "description": "Consensus through debate"},
            {"value": "benchmark_mining", "description": "Extract from coding benchmarks"},
            {"value": "llm_on_request", "description": "LLM knowledge on demand"}
        ]
    }


@router.get("/templates")
async def get_llm_templates():
    """Get available LLM request templates."""
    system = get_ingestion_system()
    return {
        "templates": system.llm_requester.request_templates,
        "usage": "Use template name with /llm-request endpoint"
    }


@router.get("/scenario-types")
async def get_scenario_types():
    """Get available simulation scenario types."""
    system = get_ingestion_system()
    return {
        "scenario_types": list(system.simulation_engine.scenario_types.keys()),
        "difficulties": ["easy", "medium", "hard", "extreme"]
    }


# =============================================================================
# LLM KNOWLEDGE ON REQUEST
# =============================================================================

@router.post("/llm-request")
async def request_llm_knowledge(request: LLMKnowledgeRequest):
    """
    Request knowledge from LLM on a specific topic.
    
    Templates:
    - explain_concept: Explain a concept
    - code_pattern: Get code patterns
    - fix_strategy: Get fix strategies
    - best_practices: Get best practices
    - compare: Compare options
    - debug_help: Get debugging help
    - architecture: Get architecture advice
    - security: Get security considerations
    """
    system = get_ingestion_system()
    
    try:
        results = await system.request_llm_knowledge(
            topic=request.topic,
            template=request.template,
            domain=request.domain,
            language=request.language,
            context=request.context or {}
        )
        
        return {
            "success": True,
            "topic": request.topic,
            "template": request.template,
            "items_created": len(results),
            "results": [
                {
                    "item_id": r.item_id,
                    "genesis_key_id": r.genesis_key_id,
                    "stored_as": r.stored_as,
                    "trust_score": r.trust_score
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"LLM knowledge request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm-request/batch")
async def batch_llm_requests(requests: List[LLMKnowledgeRequest]):
    """Request multiple topics from LLM."""
    system = get_ingestion_system()
    all_results = []
    
    for req in requests:
        try:
            results = await system.request_llm_knowledge(
                topic=req.topic,
                template=req.template,
                domain=req.domain
            )
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Failed request for {req.topic}: {e}")
    
    return {
        "success": True,
        "total_items": len(all_results),
        "topics_processed": len(requests)
    }


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

@router.post("/simulate")
async def generate_simulations(request: SimulationRequest):
    """
    Generate synthetic training scenarios.
    
    Scenario types:
    - edge_case: Edge cases and boundary conditions
    - failure_scenario: Failure scenarios
    - performance_stress: Performance stress tests
    - security_attack: Security attack patterns
    - concurrency_issue: Concurrency problems
    - data_corruption: Data corruption scenarios
    - integration_failure: Integration failures
    - resource_exhaustion: Resource exhaustion
    """
    system = get_ingestion_system()
    
    if request.scenario_type not in system.simulation_engine.scenario_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown scenario type. Available: {list(system.simulation_engine.scenario_types.keys())}"
        )
    
    results = system.generate_simulations(
        scenario_type=request.scenario_type,
        domain=request.domain,
        difficulty=request.difficulty,
        count=request.count
    )
    
    return {
        "success": True,
        "scenario_type": request.scenario_type,
        "generated": len(results),
        "results": [
            {
                "item_id": r.item_id,
                "genesis_key_id": r.genesis_key_id,
                "stored_as": r.stored_as
            }
            for r in results
        ]
    }


@router.post("/simulate/batch")
async def batch_simulations(background_tasks: BackgroundTasks):
    """Generate a batch of all scenario types."""
    system = get_ingestion_system()
    
    def generate_all():
        for scenario_type in system.simulation_engine.scenario_types.keys():
            system.generate_simulations(scenario_type, count=3)
    
    background_tasks.add_task(generate_all)
    
    return {
        "success": True,
        "message": "Generating all scenario types in background",
        "scenario_types": list(system.simulation_engine.scenario_types.keys())
    }


# =============================================================================
# REPLAY LEARNING
# =============================================================================

@router.post("/replay/record")
async def record_failure(request: FailureRecordRequest):
    """Record a failure for replay learning."""
    system = get_ingestion_system()
    
    system.record_failure(
        task=request.task,
        attempt=request.attempt,
        error=request.error,
        context=request.context
    )
    
    return {
        "success": True,
        "message": "Failure recorded for replay learning",
        "buffer_size": len(system.replay_learner.failure_buffer)
    }


@router.post("/replay/learn")
async def replay_and_learn(request: ReplayRequest):
    """
    Replay past failures and extract learnings.
    
    Strategies:
    - random: Random selection
    - oldest: Oldest failures first
    - most_recent: Most recent first
    - least_replayed: Least replayed first
    """
    system = get_ingestion_system()
    
    results = system.replay_and_learn(count=request.count)
    
    return {
        "success": True,
        "replayed": request.count,
        "learnings_extracted": len(results),
        "remaining_failures": len(system.replay_learner.failure_buffer),
        "results": [
            {
                "item_id": r.item_id,
                "genesis_key_id": r.genesis_key_id
            }
            for r in results
        ]
    }


@router.get("/replay/buffer")
async def get_failure_buffer():
    """Get current failure buffer status."""
    system = get_ingestion_system()
    
    return {
        "buffer_size": len(system.replay_learner.failure_buffer),
        "max_size": system.replay_learner.buffer_max_size,
        "stats": system.replay_learner.stats
    }


# =============================================================================
# SELF-DISTILLATION
# =============================================================================

@router.post("/distill")
async def distill_knowledge(request: DistillRequest):
    """
    Distill and compress existing knowledge.
    
    Merges similar patterns into refined versions.
    """
    system = get_ingestion_system()
    
    results = system.distill_knowledge(domain=request.domain)
    
    return {
        "success": True,
        "domain": request.domain or "all",
        "distilled_items": len(results),
        "stats": system.self_distiller.stats,
        "results": [
            {
                "item_id": r.item_id,
                "genesis_key_id": r.genesis_key_id
            }
            for r in results
        ]
    }


# =============================================================================
# MULTI-AGENT DEBATE
# =============================================================================

@router.post("/debate")
async def run_debate(request: DebateRequest):
    """
    Run multi-agent debate on a topic.
    
    Multiple Grace instances debate to reach better conclusions.
    """
    system = get_ingestion_system()
    
    results = await system.debate_and_learn(
        topic=request.topic,
        domain=request.domain
    )
    
    return {
        "success": True,
        "topic": request.topic,
        "conclusions": len(results),
        "stats": system.multi_agent_debater.stats,
        "results": [
            {
                "item_id": r.item_id,
                "genesis_key_id": r.genesis_key_id,
                "trust_score": r.trust_score
            }
            for r in results
        ]
    }


# =============================================================================
# BENCHMARK MINING
# =============================================================================

@router.post("/mine-benchmarks")
async def mine_benchmarks(request: BenchmarkMineRequest):
    """
    Extract patterns from benchmark results.
    
    Mines successful solutions for reusable patterns.
    """
    system = get_ingestion_system()
    
    results = system.mine_benchmarks(
        benchmark_name=request.benchmark_name,
        results=request.results
    )
    
    return {
        "success": True,
        "benchmark": request.benchmark_name,
        "patterns_extracted": len(results),
        "stats": system.benchmark_miner.stats,
        "results": [
            {
                "item_id": r.item_id,
                "genesis_key_id": r.genesis_key_id,
                "stored_as": r.stored_as
            }
            for r in results
        ]
    }


# =============================================================================
# MANUAL KNOWLEDGE INGESTION
# =============================================================================

@router.post("/manual")
async def add_manual_knowledge(request: ManualKnowledgeRequest):
    """
    Manually add a knowledge item.
    
    For adding specific facts, patterns, or procedures.
    """
    system = get_ingestion_system()
    
    try:
        knowledge_type = KnowledgeType(request.knowledge_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid knowledge type. Available: {[k.value for k in KnowledgeType]}"
        )
    
    item = KnowledgeItem.create(
        source=IngestionSource.USER_FEEDBACK,
        knowledge_type=knowledge_type,
        content=request.content,
        domain=request.domain,
        tags=request.tags,
        confidence=request.confidence
    )
    
    result = await system.ingest(item)
    
    return {
        "success": result.success,
        "item_id": result.item_id,
        "genesis_key_id": result.genesis_key_id,
        "stored_as": result.stored_as,
        "trust_score": result.trust_score
    }


# =============================================================================
# COMPREHENSIVE STATISTICS
# =============================================================================

@router.get("/stats")
async def get_comprehensive_stats():
    """Get comprehensive ingestion statistics."""
    system = get_ingestion_system()
    return system.get_stats()


@router.get("/stats/by-source")
async def get_stats_by_source():
    """Get ingestion counts by source."""
    system = get_ingestion_system()
    return {
        "by_source": system.stats["by_source"],
        "total": system.stats["total_ingested"]
    }


@router.get("/stats/by-type")
async def get_stats_by_type():
    """Get ingestion counts by knowledge type."""
    system = get_ingestion_system()
    return {
        "by_type": system.stats["by_type"],
        "total": system.stats["total_ingested"]
    }
