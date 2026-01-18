"""
Reverse KNN Proactive Learning API

Endpoints for the proactive learning system that uses KNN in reverse
to find knowledge gaps and expand from original sources.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/proactive-learning", tags=["proactive-learning"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze knowledge landscape."""
    force_refresh: bool = Field(default=False, description="Force refresh embeddings cache")


class ExpansionConfig(BaseModel):
    """Configuration for expansion queries."""
    max_queries: int = Field(default=10, description="Maximum queries to generate")
    use_llm_optimization: bool = Field(default=True, description="Use LLM to optimize queries")
    sources: Optional[List[str]] = Field(default=None, description="Limit to specific sources")


class LearningConfig(BaseModel):
    """Configuration for continuous learning."""
    interval_seconds: int = Field(default=600, description="Interval between cycles (default 10 min)")
    max_expansions_per_cycle: int = Field(default=5, description="Max expansions per cycle")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_proactive_learning_status() -> Dict[str, Any]:
    """
    **Get Proactive Learning Status**
    
    Returns current state of the Reverse KNN learning system:
    - Cluster analysis
    - Pending expansions
    - Learning statistics
    
    ```bash
    curl http://localhost:8000/proactive-learning/status
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        return {
            "system": "Reverse KNN Proactive Learning",
            "stats": rknn.get_stats(),
            "clusters": len(rknn._clusters),
            "running": rknn._running
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/analyze")
async def analyze_knowledge_landscape(request: AnalyzeRequest = None) -> Dict[str, Any]:
    """
    **Analyze Knowledge Landscape**
    
    Uses Reverse KNN to:
    1. Embed all Oracle knowledge
    2. Cluster to find dense/sparse areas  
    3. Identify gaps (sparse regions, frontier edges)
    4. Compute expansion priorities
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/analyze
    ```
    
    **Response:**
    ```json
    {
        "total_knowledge_items": 150,
        "clusters": 12,
        "sparse_clusters": 3,
        "frontier_clusters": 2,
        "clusters_data": [...]
    }
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.oracle_core import OracleCore
        
        hub = get_oracle_hub()
        oracle = OracleCore()
        
        rknn = get_reverse_knn_learning(
            oracle_hub=hub,
            oracle_core=oracle
        )
        
        if request and request.force_refresh:
            rknn._embeddings_cache.clear()
        
        result = await rknn.analyze_knowledge_landscape()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/generate-queries")
async def generate_expansion_queries(config: ExpansionConfig = None) -> Dict[str, Any]:
    """
    **Generate Expansion Queries**
    
    Based on gap analysis, generates queries to expand knowledge
    from the original sources (GitHub, StackOverflow, etc.)
    
    Optionally uses LLM to optimize queries.
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/generate-queries \\
      -H "Content-Type: application/json" \\
      -d '{"max_queries": 10, "use_llm_optimization": true}'
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        
        max_queries = config.max_queries if config else 10
        use_llm = config.use_llm_optimization if config else True
        
        # Generate queries
        queries = await rknn.generate_expansion_queries(max_queries=max_queries)
        
        # Optionally optimize with LLM
        if use_llm:
            queries = await rknn.llm_optimize_expansion(queries)
        
        return {
            "queries_generated": len(queries),
            "llm_optimized": len([q for q in queries if q.llm_optimized]),
            "queries": [
                {
                    "id": q.query_id,
                    "source": q.source,
                    "query": q.query_text,
                    "strategy": q.strategy.value,
                    "priority": q.priority,
                    "llm_optimized": q.llm_optimized
                }
                for q in queries
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query generation failed: {str(e)}")


@router.post("/execute-expansions")
async def execute_expansions(max_per_source: int = 5) -> Dict[str, Any]:
    """
    **Execute Expansion Queries**
    
    Fetches knowledge from original sources using generated queries
    and ingests into the Oracle.
    
    ```bash
    curl -X POST "http://localhost:8000/proactive-learning/execute-expansions?max_per_source=5"
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        rknn = get_reverse_knn_learning(oracle_hub=hub)
        
        results = await rknn.execute_expansions(max_per_source=max_per_source)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Expansion failed: {str(e)}")


@router.post("/discover-connections")
async def discover_connections() -> Dict[str, Any]:
    """
    **Discover Hidden Connections (LLM)**
    
    Uses LLM to analyze clusters and discover:
    - Hidden connections between clusters
    - Knowledge gaps spanning multiple topics
    - Cross-pollination opportunities
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/discover-connections
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        insights = await rknn.llm_discover_connections()
        
        return {
            "insights_discovered": len(insights),
            "insights": [
                {
                    "id": i.insight_id,
                    "type": i.insight_type,
                    "content": i.content,
                    "confidence": i.confidence,
                    "suggested_queries": i.actionable_queries
                }
                for i in insights
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.post("/run-cycle")
async def run_learning_cycle() -> Dict[str, Any]:
    """
    **Run Complete Learning Cycle**
    
    Executes one full proactive learning cycle:
    1. Analyze knowledge landscape
    2. Generate expansion queries
    3. LLM optimize queries
    4. Discover connections
    5. Execute expansions
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/run-cycle
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.oracle_core import OracleCore
        
        hub = get_oracle_hub()
        oracle = OracleCore()
        rknn = get_reverse_knn_learning(oracle_hub=hub, oracle_core=oracle)
        
        await rknn._run_learning_cycle()
        
        return {
            "status": "cycle_complete",
            "stats": rknn.get_stats()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learning cycle failed: {str(e)}")


@router.post("/start")
async def start_proactive_learning(config: LearningConfig = None) -> Dict[str, Any]:
    """
    **Start Continuous Proactive Learning**
    
    Starts background thread that continuously:
    - Analyzes knowledge gaps using Reverse KNN
    - Generates and optimizes expansion queries
    - Fetches from original sources
    - Ingests new knowledge
    
    Default interval: 10 minutes
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/start \\
      -H "Content-Type: application/json" \\
      -d '{"interval_seconds": 600}'
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.oracle_core import OracleCore
        
        hub = get_oracle_hub()
        oracle = OracleCore()
        rknn = get_reverse_knn_learning(oracle_hub=hub, oracle_core=oracle)
        
        if config:
            rknn.expansion_interval = config.interval_seconds
        
        result = rknn.start_proactive_learning()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start failed: {str(e)}")


@router.post("/stop")
async def stop_proactive_learning() -> Dict[str, Any]:
    """
    **Stop Continuous Proactive Learning**
    
    ```bash
    curl -X POST http://localhost:8000/proactive-learning/stop
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        result = rknn.stop_proactive_learning()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop failed: {str(e)}")


@router.get("/clusters")
async def get_clusters() -> Dict[str, Any]:
    """
    **Get Knowledge Clusters**
    
    Returns all identified knowledge clusters with their metadata:
    - Type (dense, sparse, frontier, isolated)
    - Gap score
    - Expansion priority
    - Source origins
    
    ```bash
    curl http://localhost:8000/proactive-learning/clusters
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        
        clusters = sorted(
            rknn._clusters.values(),
            key=lambda c: c.expansion_priority,
            reverse=True
        )
        
        return {
            "total_clusters": len(clusters),
            "by_type": {
                "dense": len([c for c in clusters if c.cluster_type.value == "dense"]),
                "sparse": len([c for c in clusters if c.cluster_type.value == "sparse"]),
                "frontier": len([c for c in clusters if c.cluster_type.value == "frontier"]),
                "isolated": len([c for c in clusters if c.cluster_type.value == "isolated"])
            },
            "clusters": [c.to_dict() for c in clusters]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster fetch failed: {str(e)}")


@router.get("/pending-queries")
async def get_pending_queries() -> Dict[str, Any]:
    """
    **Get Pending Expansion Queries**
    
    Returns queries that have been generated but not yet executed.
    
    ```bash
    curl http://localhost:8000/proactive-learning/pending-queries
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        
        pending = [q for q in rknn._expansion_queue if not q.executed]
        
        return {
            "pending_count": len(pending),
            "by_source": {
                source: len([q for q in pending if q.source == source])
                for source in set(q.source for q in pending)
            },
            "queries": [
                {
                    "id": q.query_id,
                    "source": q.source,
                    "query": q.query_text,
                    "priority": q.priority,
                    "strategy": q.strategy.value
                }
                for q in sorted(pending, key=lambda x: x.priority, reverse=True)[:20]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query fetch failed: {str(e)}")


@router.get("/stats")
async def get_detailed_stats() -> Dict[str, Any]:
    """
    **Get Detailed Learning Statistics**
    
    Returns comprehensive statistics about the proactive learning system.
    
    ```bash
    curl http://localhost:8000/proactive-learning/stats
    ```
    """
    try:
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        rknn = get_reverse_knn_learning()
        stats = rknn.get_stats()
        
        # Add computed metrics
        total_queries = len(rknn._expansion_queue)
        executed_queries = len([q for q in rknn._expansion_queue if q.executed])
        
        stats["queries"] = {
            "total": total_queries,
            "executed": executed_queries,
            "pending": total_queries - executed_queries,
            "execution_rate": executed_queries / total_queries if total_queries > 0 else 0
        }
        
        stats["llm_optimization_rate"] = (
            stats["llm_optimizations"] / stats["expansions_executed"]
            if stats["expansions_executed"] > 0 else 0
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats fetch failed: {str(e)}")
