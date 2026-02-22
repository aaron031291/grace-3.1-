"""
Enterprise Repository Management API.

Endpoints for managing enterprise repositories, tracking ingestion status,
and monitoring repository health.
These endpoints are not exposed to the frontend yet - internal use only.

Classes:
- `RepositoryType`
- `IngestionStatus`
- `RepositoryPriority`
- `RepositoryConfig`
- `RepositoryResponse`
- `IngestionResultResponse`
- `RepositoryStatsResponse`
- `BulkAddRequest`
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session

from database.session import get_session

router = APIRouter(prefix="/repositories", tags=["Enterprise Repository Management"])


# ==================== Enums ====================

class RepositoryType(str, Enum):
    """Types of repositories."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"
    LOCAL = "local"
    ENTERPRISE = "enterprise"


class IngestionStatus(str, Enum):
    """Status of repository ingestion."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    OUTDATED = "outdated"


class RepositoryPriority(str, Enum):
    """Priority level for repository."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==================== Pydantic Models ====================

class RepositoryConfig(BaseModel):
    """Configuration for adding a repository."""
    name: str = Field(..., description="Repository name")
    url: str = Field(..., description="Repository URL")
    repo_type: RepositoryType = Field(RepositoryType.GITHUB, description="Repository type")
    description: Optional[str] = Field(None, description="Repository description")
    language: Optional[str] = Field(None, description="Primary language")
    priority: RepositoryPriority = Field(RepositoryPriority.MEDIUM, description="Ingestion priority")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    branch: str = Field("main", description="Branch to track")
    include_patterns: List[str] = Field(default_factory=list, description="File patterns to include")
    exclude_patterns: List[str] = Field(default_factory=list, description="File patterns to exclude")
    auto_sync: bool = Field(True, description="Enable automatic syncing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RepositoryResponse(BaseModel):
    """Response for a repository."""
    id: str = Field(..., description="Unique repository ID")
    name: str = Field(..., description="Repository name")
    url: str = Field(..., description="Repository URL")
    repo_type: RepositoryType = Field(..., description="Repository type")
    description: Optional[str] = Field(None, description="Description")
    language: Optional[str] = Field(None, description="Primary language")
    priority: RepositoryPriority = Field(..., description="Priority level")
    tags: List[str] = Field(default_factory=list, description="Tags")
    branch: str = Field(..., description="Tracked branch")
    ingestion_status: IngestionStatus = Field(..., description="Current ingestion status")
    files_indexed: int = Field(0, description="Number of files indexed")
    last_commit: Optional[str] = Field(None, description="Last commit hash")
    last_synced: Optional[str] = Field(None, description="Last sync timestamp")
    stars: int = Field(0, description="GitHub stars (if applicable)")
    health_score: float = Field(1.0, description="Repository health score 0-1")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class IngestionResultResponse(BaseModel):
    """Response for ingestion operation."""
    repository_id: str = Field(..., description="Repository ID")
    status: IngestionStatus = Field(..., description="Ingestion status")
    files_processed: int = Field(0, description="Files processed")
    files_indexed: int = Field(0, description="Files indexed")
    files_skipped: int = Field(0, description="Files skipped")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    duration_seconds: float = Field(..., description="Operation duration")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: str = Field(..., description="Completion timestamp")


class RepositoryStatsResponse(BaseModel):
    """Response for repository statistics."""
    total_repositories: int = Field(..., description="Total repositories")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by type")
    by_language: Dict[str, int] = Field(default_factory=dict, description="Count by language")
    total_files_indexed: int = Field(0, description="Total files indexed")
    avg_health_score: float = Field(0.0, description="Average health score")


class BulkAddRequest(BaseModel):
    """Request to add multiple repositories."""
    repositories: List[RepositoryConfig] = Field(..., description="List of repositories to add")


# ==================== In-Memory Storage (for demo) ====================
# In production, these would be stored in the database

_repositories: Dict[str, Dict[str, Any]] = {}
_ingestion_history: List[Dict[str, Any]] = []


def _generate_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())[:8]


# Initialize with 50 enterprise repositories (from recent commit)
def _init_enterprise_repos():
    """Initialize with enterprise repositories."""
    enterprise_repos = [
        {"name": "kubernetes", "url": "https://github.com/kubernetes/kubernetes", "language": "Go", "stars": 105000},
        {"name": "tensorflow", "url": "https://github.com/tensorflow/tensorflow", "language": "Python", "stars": 180000},
        {"name": "react", "url": "https://github.com/facebook/react", "language": "JavaScript", "stars": 220000},
        {"name": "vue", "url": "https://github.com/vuejs/vue", "language": "JavaScript", "stars": 206000},
        {"name": "angular", "url": "https://github.com/angular/angular", "language": "TypeScript", "stars": 94000},
        {"name": "django", "url": "https://github.com/django/django", "language": "Python", "stars": 76000},
        {"name": "flask", "url": "https://github.com/pallets/flask", "language": "Python", "stars": 66000},
        {"name": "fastapi", "url": "https://github.com/tiangolo/fastapi", "language": "Python", "stars": 70000},
        {"name": "express", "url": "https://github.com/expressjs/express", "language": "JavaScript", "stars": 63000},
        {"name": "nestjs", "url": "https://github.com/nestjs/nest", "language": "TypeScript", "stars": 63000},
        {"name": "spring-boot", "url": "https://github.com/spring-projects/spring-boot", "language": "Java", "stars": 72000},
        {"name": "rails", "url": "https://github.com/rails/rails", "language": "Ruby", "stars": 55000},
        {"name": "laravel", "url": "https://github.com/laravel/laravel", "language": "PHP", "stars": 76000},
        {"name": "dotnet-runtime", "url": "https://github.com/dotnet/runtime", "language": "C#", "stars": 14000},
        {"name": "rust", "url": "https://github.com/rust-lang/rust", "language": "Rust", "stars": 93000},
        {"name": "go", "url": "https://github.com/golang/go", "language": "Go", "stars": 120000},
        {"name": "typescript", "url": "https://github.com/microsoft/TypeScript", "language": "TypeScript", "stars": 98000},
        {"name": "vscode", "url": "https://github.com/microsoft/vscode", "language": "TypeScript", "stars": 158000},
        {"name": "electron", "url": "https://github.com/electron/electron", "language": "C++", "stars": 112000},
        {"name": "next.js", "url": "https://github.com/vercel/next.js", "language": "JavaScript", "stars": 120000},
        {"name": "svelte", "url": "https://github.com/sveltejs/svelte", "language": "JavaScript", "stars": 76000},
        {"name": "pytorch", "url": "https://github.com/pytorch/pytorch", "language": "Python", "stars": 77000},
        {"name": "scikit-learn", "url": "https://github.com/scikit-learn/scikit-learn", "language": "Python", "stars": 58000},
        {"name": "pandas", "url": "https://github.com/pandas-dev/pandas", "language": "Python", "stars": 42000},
        {"name": "numpy", "url": "https://github.com/numpy/numpy", "language": "Python", "stars": 26000},
        {"name": "grafana", "url": "https://github.com/grafana/grafana", "language": "TypeScript", "stars": 60000},
        {"name": "prometheus", "url": "https://github.com/prometheus/prometheus", "language": "Go", "stars": 53000},
        {"name": "elasticsearch", "url": "https://github.com/elastic/elasticsearch", "language": "Java", "stars": 68000},
        {"name": "kafka", "url": "https://github.com/apache/kafka", "language": "Java", "stars": 27000},
        {"name": "redis", "url": "https://github.com/redis/redis", "language": "C", "stars": 64000},
        {"name": "postgres", "url": "https://github.com/postgres/postgres", "language": "C", "stars": 15000},
        {"name": "mongodb", "url": "https://github.com/mongodb/mongo", "language": "C++", "stars": 25000},
        {"name": "docker", "url": "https://github.com/moby/moby", "language": "Go", "stars": 68000},
        {"name": "terraform", "url": "https://github.com/hashicorp/terraform", "language": "Go", "stars": 41000},
        {"name": "ansible", "url": "https://github.com/ansible/ansible", "language": "Python", "stars": 61000},
        {"name": "jenkins", "url": "https://github.com/jenkinsci/jenkins", "language": "Java", "stars": 22000},
        {"name": "gitlab", "url": "https://gitlab.com/gitlab-org/gitlab", "language": "Ruby", "stars": 8000},
        {"name": "openai-api", "url": "https://github.com/openai/openai-python", "language": "Python", "stars": 20000},
        {"name": "langchain", "url": "https://github.com/langchain-ai/langchain", "language": "Python", "stars": 85000},
        {"name": "llama", "url": "https://github.com/meta-llama/llama", "language": "Python", "stars": 55000},
        {"name": "stable-diffusion", "url": "https://github.com/CompVis/stable-diffusion", "language": "Python", "stars": 66000},
        {"name": "whisper", "url": "https://github.com/openai/whisper", "language": "Python", "stars": 60000},
        {"name": "huggingface-transformers", "url": "https://github.com/huggingface/transformers", "language": "Python", "stars": 125000},
        {"name": "deno", "url": "https://github.com/denoland/deno", "language": "Rust", "stars": 93000},
        {"name": "bun", "url": "https://github.com/oven-sh/bun", "language": "Zig", "stars": 70000},
        {"name": "nginx", "url": "https://github.com/nginx/nginx", "language": "C", "stars": 20000},
        {"name": "traefik", "url": "https://github.com/traefik/traefik", "language": "Go", "stars": 48000},
        {"name": "envoy", "url": "https://github.com/envoyproxy/envoy", "language": "C++", "stars": 24000},
        {"name": "istio", "url": "https://github.com/istio/istio", "language": "Go", "stars": 35000},
        {"name": "helm", "url": "https://github.com/helm/helm", "language": "Go", "stars": 26000},
    ]

    import random
    statuses = [IngestionStatus.COMPLETED, IngestionStatus.COMPLETED, IngestionStatus.COMPLETED,
                IngestionStatus.IN_PROGRESS, IngestionStatus.PENDING, IngestionStatus.PARTIAL]

    for i, repo in enumerate(enterprise_repos):
        repo_id = f"repo_{i:03d}"
        now = datetime.now().isoformat()

        _repositories[repo_id] = {
            "id": repo_id,
            "name": repo["name"],
            "url": repo["url"],
            "repo_type": RepositoryType.GITHUB,
            "description": f"Enterprise repository: {repo['name']}",
            "language": repo["language"],
            "priority": random.choice(list(RepositoryPriority)),
            "tags": [repo["language"].lower(), "enterprise", "open-source"],
            "branch": "main",
            "include_patterns": [],
            "exclude_patterns": ["*.test.*", "*.spec.*", "__tests__/*"],
            "auto_sync": True,
            "ingestion_status": random.choice(statuses),
            "files_indexed": random.randint(100, 5000),
            "last_commit": f"abc{random.randint(1000, 9999)}",
            "last_synced": now if random.random() > 0.3 else None,
            "stars": repo["stars"],
            "health_score": round(random.uniform(0.7, 1.0), 2),
            "created_at": now,
            "updated_at": now,
            "metadata": {}
        }


# Initialize repos on module load
_init_enterprise_repos()


# ==================== Endpoints ====================

@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(
    repo_type: Optional[RepositoryType] = None,
    status: Optional[IngestionStatus] = None,
    language: Optional[str] = None,
    priority: Optional[RepositoryPriority] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """
    List all enterprise repositories.

    Supports filtering by type, status, language, priority, and tags.
    """
    try:
        repos = list(_repositories.values())

        if repo_type:
            repos = [r for r in repos if r["repo_type"] == repo_type]

        if status:
            repos = [r for r in repos if r["ingestion_status"] == status]

        if language:
            repos = [r for r in repos if r.get("language", "").lower() == language.lower()]

        if priority:
            repos = [r for r in repos if r["priority"] == priority]

        if tag:
            repos = [r for r in repos if tag.lower() in [t.lower() for t in r.get("tags", [])]]

        # Sort by priority and stars
        repos.sort(key=lambda x: (
            list(RepositoryPriority).index(x["priority"]),
            -x.get("stars", 0)
        ))

        total = len(repos)
        repos = repos[skip:skip + limit]

        return [RepositoryResponse(**r) for r in repos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=RepositoryResponse)
async def add_repository(
    config: RepositoryConfig,
    session: Session = Depends(get_session)
):
    """
    Add a new repository for tracking.
    """
    try:
        repo_id = _generate_id()
        now = datetime.now().isoformat()

        repo = {
            "id": repo_id,
            "name": config.name,
            "url": config.url,
            "repo_type": config.repo_type,
            "description": config.description,
            "language": config.language,
            "priority": config.priority,
            "tags": config.tags,
            "branch": config.branch,
            "include_patterns": config.include_patterns,
            "exclude_patterns": config.exclude_patterns,
            "auto_sync": config.auto_sync,
            "ingestion_status": IngestionStatus.PENDING,
            "files_indexed": 0,
            "last_commit": None,
            "last_synced": None,
            "stars": 0,
            "health_score": 1.0,
            "created_at": now,
            "updated_at": now,
            "metadata": config.metadata
        }

        _repositories[repo_id] = repo

        return RepositoryResponse(**repo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=List[RepositoryResponse])
async def bulk_add_repositories(
    request: BulkAddRequest,
    session: Session = Depends(get_session)
):
    """
    Add multiple repositories at once.
    """
    try:
        added = []
        now = datetime.now().isoformat()

        for config in request.repositories:
            repo_id = _generate_id()

            repo = {
                "id": repo_id,
                "name": config.name,
                "url": config.url,
                "repo_type": config.repo_type,
                "description": config.description,
                "language": config.language,
                "priority": config.priority,
                "tags": config.tags,
                "branch": config.branch,
                "include_patterns": config.include_patterns,
                "exclude_patterns": config.exclude_patterns,
                "auto_sync": config.auto_sync,
                "ingestion_status": IngestionStatus.PENDING,
                "files_indexed": 0,
                "last_commit": None,
                "last_synced": None,
                "stars": 0,
                "health_score": 1.0,
                "created_at": now,
                "updated_at": now,
                "metadata": config.metadata
            }

            _repositories[repo_id] = repo
            added.append(RepositoryResponse(**repo))

        return added
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific repository by ID.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        return RepositoryResponse(**_repositories[repository_id])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: str,
    config: RepositoryConfig,
    session: Session = Depends(get_session)
):
    """
    Update a repository configuration.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        repo = _repositories[repository_id]
        repo.update({
            "name": config.name,
            "url": config.url,
            "repo_type": config.repo_type,
            "description": config.description,
            "language": config.language,
            "priority": config.priority,
            "tags": config.tags,
            "branch": config.branch,
            "include_patterns": config.include_patterns,
            "exclude_patterns": config.exclude_patterns,
            "auto_sync": config.auto_sync,
            "metadata": config.metadata,
            "updated_at": datetime.now().isoformat()
        })

        return RepositoryResponse(**repo)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a repository.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        del _repositories[repository_id]

        return {"status": "deleted", "repository_id": repository_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repository_id}/ingest", response_model=IngestionResultResponse)
async def ingest_repository(
    repository_id: str,
    full_ingest: bool = Query(False, description="Force full re-ingestion"),
    session: Session = Depends(get_session)
):
    """
    Trigger ingestion for a repository.

    Indexes repository files into the knowledge base.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        repo = _repositories[repository_id]
        started_at = datetime.now()

        # Update status
        repo["ingestion_status"] = IngestionStatus.IN_PROGRESS
        repo["updated_at"] = started_at.isoformat()

        # Simulate ingestion
        import random
        import time
        time.sleep(0.1)

        files_processed = random.randint(50, 500)
        files_indexed = int(files_processed * random.uniform(0.8, 0.95))
        files_skipped = files_processed - files_indexed

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Update repository
        repo["ingestion_status"] = IngestionStatus.COMPLETED
        repo["files_indexed"] = repo.get("files_indexed", 0) + files_indexed
        repo["last_synced"] = completed_at.isoformat()
        repo["last_commit"] = f"abc{random.randint(1000, 9999)}"
        repo["updated_at"] = completed_at.isoformat()

        result = IngestionResultResponse(
            repository_id=repository_id,
            status=IngestionStatus.COMPLETED,
            files_processed=files_processed,
            files_indexed=files_indexed,
            files_skipped=files_skipped,
            errors=[],
            duration_seconds=duration,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat()
        )

        _ingestion_history.append(result.dict())

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-all")
async def ingest_all_repositories(
    priority: Optional[RepositoryPriority] = None,
    session: Session = Depends(get_session)
):
    """
    Trigger ingestion for all repositories.

    Optionally filter by priority level.
    """
    try:
        repos = list(_repositories.values())

        if priority:
            repos = [r for r in repos if r["priority"] == priority]

        results = []
        for repo in repos:
            if repo["ingestion_status"] != IngestionStatus.IN_PROGRESS:
                repo["ingestion_status"] = IngestionStatus.PENDING
                results.append({
                    "repository_id": repo["id"],
                    "name": repo["name"],
                    "queued": True
                })

        return {
            "status": "queued",
            "repositories_queued": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repository_id}/files")
async def get_repository_files(
    repository_id: str,
    path: str = Query("", description="Path within repository"),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """
    Get indexed files from a repository.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        repo = _repositories[repository_id]

        # Simulate file listing
        files = []
        for i in range(min(limit, repo.get("files_indexed", 0))):
            files.append({
                "path": f"src/file_{i}.{repo.get('language', 'txt').lower()[:2]}",
                "size_bytes": 1000 + i * 100,
                "last_modified": datetime.now().isoformat(),
                "indexed": True
            })

        return {
            "repository_id": repository_id,
            "path": path,
            "total_files": repo.get("files_indexed", 0),
            "files": files
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview", response_model=RepositoryStatsResponse)
async def get_repository_stats(session: Session = Depends(get_session)):
    """
    Get repository statistics overview.
    """
    try:
        repos = list(_repositories.values())

        by_status = {}
        by_type = {}
        by_language = {}
        total_files = 0
        total_health = 0.0

        for repo in repos:
            # By status
            status = repo["ingestion_status"]
            by_status[status] = by_status.get(status, 0) + 1

            # By type
            rtype = repo["repo_type"]
            by_type[rtype] = by_type.get(rtype, 0) + 1

            # By language
            lang = repo.get("language", "Unknown")
            by_language[lang] = by_language.get(lang, 0) + 1

            # Totals
            total_files += repo.get("files_indexed", 0)
            total_health += repo.get("health_score", 0)

        avg_health = total_health / len(repos) if repos else 0.0

        return RepositoryStatsResponse(
            total_repositories=len(repos),
            by_status=by_status,
            by_type=by_type,
            by_language=by_language,
            total_files_indexed=total_files,
            avg_health_score=round(avg_health, 2)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/languages")
async def get_language_stats(session: Session = Depends(get_session)):
    """
    Get statistics by programming language.
    """
    try:
        repos = list(_repositories.values())
        languages = {}

        for repo in repos:
            lang = repo.get("language", "Unknown")
            if lang not in languages:
                languages[lang] = {
                    "count": 0,
                    "files_indexed": 0,
                    "total_stars": 0
                }
            languages[lang]["count"] += 1
            languages[lang]["files_indexed"] += repo.get("files_indexed", 0)
            languages[lang]["total_stars"] += repo.get("stars", 0)

        # Sort by count
        sorted_langs = sorted(languages.items(), key=lambda x: x[1]["count"], reverse=True)

        return {
            "languages": dict(sorted_langs),
            "total_languages": len(languages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/check")
async def check_repositories_health(session: Session = Depends(get_session)):
    """
    Check health of all repositories.
    """
    try:
        repos = list(_repositories.values())

        healthy = []
        unhealthy = []
        outdated = []

        for repo in repos:
            health_info = {
                "id": repo["id"],
                "name": repo["name"],
                "health_score": repo.get("health_score", 0),
                "ingestion_status": repo["ingestion_status"],
                "last_synced": repo.get("last_synced")
            }

            if repo.get("health_score", 0) >= 0.8 and repo["ingestion_status"] == IngestionStatus.COMPLETED:
                healthy.append(health_info)
            elif repo["ingestion_status"] == IngestionStatus.OUTDATED:
                outdated.append(health_info)
            else:
                unhealthy.append(health_info)

        return {
            "total": len(repos),
            "healthy_count": len(healthy),
            "unhealthy_count": len(unhealthy),
            "outdated_count": len(outdated),
            "healthy": healthy[:10],
            "unhealthy": unhealthy[:10],
            "outdated": outdated[:10],
            "checked_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingestion/history")
async def get_ingestion_history(
    repository_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """
    Get ingestion history.
    """
    try:
        history = _ingestion_history

        if repository_id:
            history = [h for h in history if h["repository_id"] == repository_id]

        return {
            "total": len(history),
            "history": history[-limit:][::-1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repository_id}/priority")
async def set_repository_priority(
    repository_id: str,
    priority: RepositoryPriority = Body(..., embed=True),
    session: Session = Depends(get_session)
):
    """
    Set repository priority level.
    """
    try:
        if repository_id not in _repositories:
            raise HTTPException(status_code=404, detail=f"Repository '{repository_id}' not found")

        repo = _repositories[repository_id]
        repo["priority"] = priority
        repo["updated_at"] = datetime.now().isoformat()

        return {
            "repository_id": repository_id,
            "name": repo["name"],
            "priority": priority
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_repositories(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """
    Search repositories by name, description, or tags.
    """
    try:
        repos = list(_repositories.values())
        query_lower = query.lower()

        matches = []
        for repo in repos:
            score = 0
            if query_lower in repo["name"].lower():
                score += 10
            if repo.get("description") and query_lower in repo["description"].lower():
                score += 5
            if any(query_lower in tag.lower() for tag in repo.get("tags", [])):
                score += 3
            if repo.get("language") and query_lower in repo["language"].lower():
                score += 2

            if score > 0:
                matches.append((score, repo))

        # Sort by score
        matches.sort(key=lambda x: x[0], reverse=True)
        results = [RepositoryResponse(**r[1]) for r in matches[:limit]]

        return {
            "query": query,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
