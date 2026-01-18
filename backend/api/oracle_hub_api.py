"""
Oracle Hub API - Unified Intelligence Ingestion Endpoints

Exposes the Unified Oracle Hub through REST API for:
- Manual intelligence ingestion
- Source-specific ingestion
- Export and sync operations
- Status and statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

router = APIRouter(prefix="/oracle-hub", tags=["oracle-hub"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class IngestRequest(BaseModel):
    """Generic intelligence ingestion request."""
    source: str = Field(..., description="Source type: ai_research, github_pulls, sandbox_insights, etc.")
    title: str = Field(..., description="Title of the intelligence item")
    content: str = Field(..., description="Main content/findings")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    code_examples: Optional[List[str]] = Field(default=[], description="Code examples if any")
    tags: Optional[List[str]] = Field(default=[], description="Tags for categorization")
    confidence: Optional[float] = Field(default=0.7, description="Confidence score 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "ai_research",
                "title": "New Pattern Recognition Approach",
                "content": "Research findings about improved pattern matching...",
                "tags": ["research", "patterns"],
                "confidence": 0.85
            }
        }


class GithubIngestRequest(BaseModel):
    """GitHub data ingestion request."""
    repo_url: str = Field(..., description="GitHub repository URL")
    data_type: str = Field(..., description="Type: pull, issue, code, release")
    title: str = Field(..., description="PR/Issue/Code title")
    content: str = Field(..., description="Description or code content")
    code_examples: Optional[List[str]] = Field(default=[], description="Code snippets")
    
    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/example/repo",
                "data_type": "pull",
                "title": "Fix authentication bug",
                "content": "This PR fixes the JWT validation issue..."
            }
        }


class SandboxIngestRequest(BaseModel):
    """Sandbox experiment ingestion request."""
    experiment_id: str = Field(..., description="Unique experiment identifier")
    experiment_name: str = Field(..., description="Name of the experiment")
    results: Dict[str, Any] = Field(..., description="Experiment results")
    lessons_learned: List[str] = Field(..., description="Key lessons from experiment")
    success: bool = Field(default=True, description="Was experiment successful?")
    
    class Config:
        json_schema_extra = {
            "example": {
                "experiment_id": "EXP-001",
                "experiment_name": "Test new caching strategy",
                "results": {"latency_improvement": "35%", "memory_usage": "-20%"},
                "lessons_learned": ["Cache invalidation critical", "TTL should be dynamic"],
                "success": True
            }
        }


class TemplateIngestRequest(BaseModel):
    """Coding template ingestion request."""
    template_name: str = Field(..., description="Name of the template")
    pattern_type: str = Field(..., description="Type of pattern: api_handler, data_processor, etc.")
    code_example: str = Field(..., description="The template code")
    description: str = Field(..., description="What this template does")
    category: str = Field(..., description="Category: backend, frontend, testing, etc.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_name": "FastAPI CRUD Handler",
                "pattern_type": "api_handler",
                "code_example": "@router.post('/items')\nasync def create_item(item: Item):\n    ...",
                "description": "Standard CRUD endpoint pattern for FastAPI",
                "category": "backend"
            }
        }


class LearningIngestRequest(BaseModel):
    """Learning memory ingestion request."""
    training_type: str = Field(..., description="Type: code_generation, error_fix, pattern_match")
    data: Dict[str, Any] = Field(..., description="Training data")
    trust_score: float = Field(default=0.7, description="Trust score 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "training_type": "error_fix",
                "data": {"error": "NullPointerException", "fix": "Add null check"},
                "trust_score": 0.85
            }
        }


class SelfHealingIngestRequest(BaseModel):
    """Self-healing fix ingestion request."""
    error_type: str = Field(..., description="Type of error that was fixed")
    error_message: str = Field(..., description="Original error message")
    fix_applied: str = Field(..., description="Description of fix applied")
    success: bool = Field(..., description="Was fix successful?")
    affected_files: List[str] = Field(default=[], description="Files that were modified")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "ImportError",
                "error_message": "ModuleNotFoundError: No module named 'xyz'",
                "fix_applied": "Added missing dependency to requirements.txt",
                "success": True,
                "affected_files": ["requirements.txt"]
            }
        }


class WhitelistIngestRequest(BaseModel):
    """Whitelist source ingestion request."""
    source_name: str = Field(..., description="Name of the approved source")
    source_url: str = Field(..., description="URL of the source")
    source_type: str = Field(..., description="Type: documentation, tutorial, reference")
    content: str = Field(..., description="Content from the source")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_name": "Python Official Docs",
                "source_url": "https://docs.python.org/3/library/asyncio.html",
                "source_type": "documentation",
                "content": "asyncio is a library to write concurrent code..."
            }
        }


class PatternIngestRequest(BaseModel):
    """Pattern discovery ingestion request."""
    pattern_name: str = Field(..., description="Name of the pattern")
    pattern_description: str = Field(..., description="Description of what pattern does")
    occurrences: int = Field(..., description="How many times pattern was seen")
    source_files: List[str] = Field(..., description="Files where pattern was found")
    is_success_pattern: bool = Field(default=True, description="Is this a success or failure pattern?")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pattern_name": "try-except-finally cleanup",
                "pattern_description": "Always use finally block for resource cleanup",
                "occurrences": 47,
                "source_files": ["db.py", "cache.py", "file_handler.py"],
                "is_success_pattern": True
            }
        }


class ResearchIngestRequest(BaseModel):
    """AI research paper ingestion request."""
    paper_title: str = Field(..., description="Title of the research paper")
    abstract: str = Field(..., description="Paper abstract")
    key_findings: List[str] = Field(..., description="List of key findings")
    source_url: str = Field(..., description="URL to the paper")
    source: str = Field(default="arxiv", description="Source: arxiv, huggingface, openai")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/ingest")
async def ingest_intelligence(request: IngestRequest) -> Dict[str, Any]:
    """
    **Ingest Any Intelligence into Oracle**
    
    Universal endpoint to ingest any type of intelligence.
    The source field determines how it's categorized.
    
    **Sources:**
    - `ai_research` - AI/ML research papers
    - `github_pulls` - GitHub PRs, issues, code
    - `stackoverflow` - Stack Overflow Q&A
    - `sandbox_insights` - Sandbox experiment results
    - `templates` - Coding templates/patterns
    - `learning_memory` - Training data
    - `whitelist` - Approved external sources
    - `internal_updates` - Self-healing fixes
    - `pattern` - Discovered patterns
    """
    try:
        from oracle_intelligence.unified_oracle_hub import (
            get_oracle_hub, IntelligenceSource, IntelligenceItem
        )
        import uuid
        
        hub = get_oracle_hub()
        
        # Map source string to enum
        try:
            source_enum = IntelligenceSource(request.source)
        except ValueError:
            source_enum = IntelligenceSource.WEB_KNOWLEDGE
        
        item = IntelligenceItem(
            item_id=f"API-{uuid.uuid4().hex[:12]}",
            source=source_enum,
            title=request.title,
            content=request.content,
            metadata=request.metadata or {},
            code_examples=request.code_examples or [],
            confidence=request.confidence or 0.7,
            tags=request.tags or []
        )
        
        result = await hub.ingest(item)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/github")
async def ingest_from_github(request: GithubIngestRequest) -> Dict[str, Any]:
    """
    **Ingest GitHub Data**
    
    Ingest GitHub pull requests, issues, code snippets, or releases.
    
    ```bash
    curl -X POST http://localhost:8000/oracle-hub/ingest/github \\
      -H "Content-Type: application/json" \\
      -d '{
        "repo_url": "https://github.com/example/repo",
        "data_type": "pull",
        "title": "Fix auth bug",
        "content": "This PR fixes..."
      }'
    ```
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_from_github(
            repo_url=request.repo_url,
            data_type=request.data_type,
            title=request.title,
            content=request.content,
            code_examples=request.code_examples
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub ingestion failed: {str(e)}")


@router.post("/ingest/sandbox")
async def ingest_sandbox_insight(request: SandboxIngestRequest) -> Dict[str, Any]:
    """
    **Ingest Sandbox Experiment Results**
    
    Store lessons learned from sandbox experiments.
    
    ```bash
    curl -X POST http://localhost:8000/oracle-hub/ingest/sandbox \\
      -H "Content-Type: application/json" \\
      -d '{
        "experiment_id": "EXP-001",
        "experiment_name": "Cache optimization",
        "results": {"improvement": "40%"},
        "lessons_learned": ["Use LRU cache", "Set proper TTL"],
        "success": true
      }'
    ```
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_from_sandbox(
            experiment_id=request.experiment_id,
            experiment_name=request.experiment_name,
            results=request.results,
            lessons_learned=request.lessons_learned,
            success=request.success
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sandbox ingestion failed: {str(e)}")


@router.post("/ingest/template")
async def ingest_template(request: TemplateIngestRequest) -> Dict[str, Any]:
    """
    **Ingest Coding Template/Pattern**
    
    Store reusable coding templates for the coding agent.
    
    ```bash
    curl -X POST http://localhost:8000/oracle-hub/ingest/template \\
      -H "Content-Type: application/json" \\
      -d '{
        "template_name": "FastAPI CRUD",
        "pattern_type": "api_handler",
        "code_example": "@router.post...",
        "description": "Standard CRUD pattern",
        "category": "backend"
      }'
    ```
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_from_template(
            template_name=request.template_name,
            pattern_type=request.pattern_type,
            code_example=request.code_example,
            description=request.description,
            category=request.category
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template ingestion failed: {str(e)}")


@router.post("/ingest/learning")
async def ingest_learning(request: LearningIngestRequest) -> Dict[str, Any]:
    """
    **Ingest Learning Memory Data**
    
    Sync training data from learning memory to Oracle.
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_from_learning_memory(
            training_type=request.training_type,
            data=request.data,
            trust_score=request.trust_score
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learning ingestion failed: {str(e)}")


@router.post("/ingest/self-healing")
async def ingest_self_healing(request: SelfHealingIngestRequest) -> Dict[str, Any]:
    """
    **Ingest Self-Healing Fix Results**
    
    Store successful (and failed) self-healing fixes for learning.
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_from_self_healing(
            error_type=request.error_type,
            error_message=request.error_message,
            fix_applied=request.fix_applied,
            success=request.success,
            affected_files=request.affected_files
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing ingestion failed: {str(e)}")


@router.post("/ingest/whitelist")
async def ingest_whitelist_source(request: WhitelistIngestRequest) -> Dict[str, Any]:
    """
    **Ingest from Whitelist Source**
    
    Ingest content from pre-approved external sources.
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_whitelist_source(
            source_name=request.source_name,
            source_url=request.source_url,
            source_type=request.source_type,
            content=request.content
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whitelist ingestion failed: {str(e)}")


@router.post("/ingest/pattern")
async def ingest_pattern_discovery(request: PatternIngestRequest) -> Dict[str, Any]:
    """
    **Ingest Discovered Pattern**
    
    Store newly discovered code patterns (success or failure).
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_pattern_discovery(
            pattern_name=request.pattern_name,
            pattern_description=request.pattern_description,
            occurrences=request.occurrences,
            source_files=request.source_files,
            is_success_pattern=request.is_success_pattern
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern ingestion failed: {str(e)}")


@router.post("/ingest/research")
async def ingest_ai_research(request: ResearchIngestRequest) -> Dict[str, Any]:
    """
    **Ingest AI Research Paper**
    
    Store AI/ML research papers and findings.
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.ingest_ai_research(
            paper_title=request.paper_title,
            abstract=request.abstract,
            key_findings=request.key_findings,
            source_url=request.source_url,
            source=request.source
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research ingestion failed: {str(e)}")


# =============================================================================
# EXPORT AND SYNC ENDPOINTS
# =============================================================================

@router.post("/export")
async def export_to_knowledge_base() -> Dict[str, Any]:
    """
    **Export Oracle Research to Knowledge Base**
    
    Exports all Oracle research to `knowledge_base/oracle/` folder.
    Creates organized JSON files by source type.
    
    ```bash
    curl -X POST http://localhost:8000/oracle-hub/export
    ```
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = await hub.export_to_knowledge_base()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/sync/start")
async def start_background_sync(interval_seconds: int = 300) -> Dict[str, Any]:
    """
    **Start Background Sync**
    
    Starts continuous background sync that:
    - Pulls from learning memory
    - Pulls from sandbox experiments
    - Exports to knowledge base
    
    Default interval: 5 minutes (300 seconds)
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = hub.start_background_sync(interval_seconds=interval_seconds)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync start failed: {str(e)}")


@router.post("/sync/stop")
async def stop_background_sync() -> Dict[str, Any]:
    """
    **Stop Background Sync**
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        result = hub.stop_background_sync()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync stop failed: {str(e)}")


# =============================================================================
# STATUS ENDPOINTS
# =============================================================================

@router.get("/stats")
async def get_ingestion_stats() -> Dict[str, Any]:
    """
    **Get Ingestion Statistics**
    
    Returns counts by source, success rates, and last ingestion times.
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        return hub.get_stats()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/status")
async def get_hub_status() -> Dict[str, Any]:
    """
    **Get Complete Oracle Hub Status**
    
    Returns connection status for all integrated systems:
    - Oracle Core
    - Librarian Pipeline
    - Learning Memory
    - Sandbox Lab
    - Genesis Service
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        return hub.get_status()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/research")
async def search_research(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    **Search Oracle Research**
    
    Semantic search through all ingested research.
    
    ```bash
    curl "http://localhost:8000/oracle-hub/research?query=caching%20patterns&limit=5"
    ```
    """
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        hub = get_oracle_hub()
        
        if hub._oracle_core:
            results = await hub._oracle_core.search_research(query, limit)
            return {
                "query": query,
                "count": len(results),
                "results": [r.to_dict() for r in results]
            }
        else:
            return {"query": query, "count": 0, "results": [], "note": "Oracle not connected"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/sources")
async def list_intelligence_sources() -> Dict[str, Any]:
    """
    **List All Intelligence Sources**
    
    Returns all available source types that can be ingested.
    """
    from oracle_intelligence.unified_oracle_hub import IntelligenceSource
    
    return {
        "sources": [
            {
                "value": source.value,
                "name": source.name,
                "description": _get_source_description(source)
            }
            for source in IntelligenceSource
        ]
    }


def _get_source_description(source) -> str:
    """Get description for a source type."""
    from oracle_intelligence.unified_oracle_hub import IntelligenceSource
    
    descriptions = {
        IntelligenceSource.AI_RESEARCH: "AI/ML research papers from arXiv, HuggingFace",
        IntelligenceSource.GITHUB_PULLS: "GitHub pull requests, issues, code snippets",
        IntelligenceSource.STACKOVERFLOW: "Stack Overflow questions and answers",
        IntelligenceSource.SANDBOX_INSIGHTS: "Lessons learned from sandbox experiments",
        IntelligenceSource.TEMPLATES: "Reusable coding templates and patterns",
        IntelligenceSource.LEARNING_MEMORY: "Training data and trust scores",
        IntelligenceSource.WHITELIST_SOURCES: "Approved external documentation sources",
        IntelligenceSource.INTERNAL_UPDATES: "Self-healing fixes and internal improvements",
        IntelligenceSource.LIBRARIAN_INGESTION: "Files ingested via Librarian pipeline",
        IntelligenceSource.PATTERN_DISCOVERY: "Newly discovered code patterns",
        IntelligenceSource.WEB_KNOWLEDGE: "General web research and documentation",
        IntelligenceSource.DOCUMENTATION: "Official documentation",
        IntelligenceSource.USER_FEEDBACK: "User corrections and feedback"
    }
    return descriptions.get(source, "Unknown source type")
