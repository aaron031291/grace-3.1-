"""
External Knowledge API - Endpoints for knowledge extraction

Provides API endpoints to:
- Extract knowledge from external sources
- View extraction statistics
- Trigger extraction jobs
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.session import get_session

from cognitive.external_knowledge_extractor import get_external_knowledge_extractor
from cognitive.memory_mesh_integration import get_memory_mesh_integration
from llm_orchestrator.llm_orchestrator import get_llm_orchestrator

router = APIRouter(prefix="/external-knowledge", tags=["external-knowledge"])


class ExtractionRequest(BaseModel):
    """Request for knowledge extraction."""
    sources: List[str] = ["github", "arxiv", "huggingface", "stackoverflow"]
    github_repos: Optional[List[Dict[str, str]]] = None
    github_queries: Optional[List[str]] = None
    arxiv_queries: Optional[List[str]] = None
    stackoverflow_queries: Optional[List[str]] = None
    max_results_per_source: int = 20


@router.post("/extract")
async def extract_knowledge(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Extract knowledge from external sources.
    
    Runs extraction in background and returns job ID.
    """
    try:
        session = next(get_session())
        
        # Initialize extractor
        memory_mesh = get_memory_mesh_integration(session=session)
        llm_orchestrator = get_llm_orchestrator(session=session)
        
        extractor = get_external_knowledge_extractor(
            session=session,
            memory_mesh=memory_mesh,
            llm_orchestrator=llm_orchestrator
        )
        
        # Run extraction in background
        background_tasks.add_task(
            _run_extraction,
            extractor,
            request
        )
        
        return {
            "success": True,
            "message": "Extraction started in background",
            "sources": request.sources
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_extraction_stats() -> Dict[str, Any]:
    """Get extraction statistics."""
    try:
        session = next(get_session())
        
        extractor = get_external_knowledge_extractor(
            session=session,
            memory_mesh=None,
            llm_orchestrator=None
        )
        
        stats = extractor.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_extraction(extractor, request: ExtractionRequest):
    """Run extraction in background."""
    all_sources = []
    
    # GitHub extraction
    if "github" in request.sources:
        if request.github_repos:
            for repo in request.github_repos:
                sources = extractor.extract_from_github_repo(
                    owner=repo.get("owner"),
                    repo=repo.get("repo"),
                    max_files=request.max_results_per_source
                )
                all_sources.extend(sources)
        
        if request.github_queries:
            for query in request.github_queries:
                sources = extractor.extract_from_github_code_search(
                    query=query,
                    max_results=request.max_results_per_source
                )
                all_sources.extend(sources)
    
    # arXiv extraction
    if "arxiv" in request.sources:
        if request.arxiv_queries:
            for query in request.arxiv_queries:
                sources = extractor.extract_from_arxiv(
                    query=query,
                    max_results=request.max_results_per_source
                )
                all_sources.extend(sources)
    
    # Stack Overflow extraction
    if "stackoverflow" in request.sources:
        if request.stackoverflow_queries:
            for query in request.stackoverflow_queries:
                sources = extractor.extract_from_stackoverflow(
                    query=query,
                    max_results=request.max_results_per_source
                )
                all_sources.extend(sources)
    
    # Extract patterns and store
    patterns = extractor.extract_patterns(all_sources)
    extractor.store_in_memory_mesh(patterns)
