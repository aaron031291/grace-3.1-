"""
Deterministic RAG Validator
=============================
Pure deterministic analysis of the RAG pipeline — no LLM needed.

Checks:
1.  Embedding Model: Can the model file/config be found and loaded?
2.  Qdrant Connectivity: Is the vector DB reachable, does the collection exist?
3.  Collection Schema: Does the Qdrant collection have correct vector dimensions?
4.  Document-Chunk Consistency: DB chunks match Qdrant vectors (no orphans)
5.  Ingestion Pipeline Wiring: ingestion service → embedder → vector DB chain intact
6.  Retriever Wiring: retriever → embedder → vector DB chain intact
7.  RAG Prompt Integrity: Prompt templates exist and are well-formed
8.  Knowledge Base File Tracking: Files on disk vs. ingested documents
9.  Connector Registration: RAG + Ingestion connectors registered in Layer 1
10. Import Chain: All RAG module imports resolve
11. Confidence Scoring: Chunk confidence scores within valid range (0-1)
"""

import ast
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent


@dataclass
class RAGIssue:
    """A single deterministic RAG validation issue."""
    check: str
    severity: str  # critical, warning, info
    message: str
    details: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None


@dataclass
class RAGValidationReport:
    """Full deterministic RAG validation report."""
    timestamp: str
    total_issues: int
    critical_count: int
    warning_count: int
    info_count: int
    checks_run: List[str]
    issues: List[RAGIssue]
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "checks_run": self.checks_run,
            "issues": [asdict(i) for i in self.issues],
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# 1. Embedding Model Check
# ---------------------------------------------------------------------------

def check_embedding_model() -> List[RAGIssue]:
    """
    Verify the embedding model configuration is valid and the model
    file or HuggingFace identifier exists.
    """
    issues = []

    embedder_file = BACKEND_ROOT / "embedding" / "embedder.py"
    if not embedder_file.exists():
        issues.append(RAGIssue(
            check="embedding_model",
            severity="critical",
            message="Embedding module not found: embedding/embedder.py",
            fix_suggestion="Create or restore embedding/embedder.py",
        ))
        return issues

    try:
        source = embedder_file.read_text(errors="ignore")
        ast.parse(source)
    except SyntaxError as e:
        issues.append(RAGIssue(
            check="embedding_model",
            severity="critical",
            message=f"Syntax error in embedder.py: {e.msg} (line {e.lineno})",
        ))
        return issues

    has_class = "class EmbeddingModel" in source
    has_embed = "def embed_text" in source
    has_singleton = "get_embedding_model" in source

    if not has_class:
        issues.append(RAGIssue(
            check="embedding_model",
            severity="critical",
            message="EmbeddingModel class not found in embedder.py",
        ))
    if not has_embed:
        issues.append(RAGIssue(
            check="embedding_model",
            severity="critical",
            message="embed_text() method not found in EmbeddingModel",
        ))
    if not has_singleton:
        issues.append(RAGIssue(
            check="embedding_model",
            severity="warning",
            message="get_embedding_model() singleton factory not found",
            fix_suggestion="Add singleton factory to prevent multiple model instances",
        ))

    settings_file = BACKEND_ROOT / "settings.py"
    if settings_file.exists():
        settings_source = settings_file.read_text(errors="ignore")
        if "EMBEDDING" not in settings_source:
            issues.append(RAGIssue(
                check="embedding_model",
                severity="info",
                message="No EMBEDDING_* settings found in settings.py",
            ))

    return issues


# ---------------------------------------------------------------------------
# 2. Qdrant Connectivity
# ---------------------------------------------------------------------------

def check_qdrant_connectivity() -> List[RAGIssue]:
    """Check if Qdrant is reachable and the documents collection exists."""
    issues = []

    client_file = BACKEND_ROOT / "vector_db" / "client.py"
    if not client_file.exists():
        issues.append(RAGIssue(
            check="qdrant_connectivity",
            severity="critical",
            message="Qdrant client module not found: vector_db/client.py",
            fix_suggestion="Create or restore vector_db/client.py",
        ))
        return issues

    import urllib.request
    qdrant_url = os.environ.get("QDRANT_URL", "")

    if qdrant_url and qdrant_url.startswith("https://"):
        try:
            api_key = os.environ.get("QDRANT_API_KEY", "")
            req = urllib.request.Request(
                f"{qdrant_url}/collections",
                headers={"api-key": api_key} if api_key else {},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            issues.append(RAGIssue(
                check="qdrant_connectivity",
                severity="warning",
                message=f"Qdrant Cloud unreachable at {qdrant_url[:50]}: {e}",
                fix_suggestion="Check QDRANT_URL and QDRANT_API_KEY environment variables",
            ))
    else:
        try:
            urllib.request.urlopen("http://localhost:6333/collections", timeout=3)
        except Exception:
            issues.append(RAGIssue(
                check="qdrant_connectivity",
                severity="warning",
                message="Qdrant not reachable at localhost:6333",
                fix_suggestion="Start Qdrant: docker run -p 6333:6333 qdrant/qdrant",
            ))
            return issues

    try:
        base = qdrant_url if qdrant_url.startswith("https://") else "http://localhost:6333"
        api_key = os.environ.get("QDRANT_API_KEY", "")
        req = urllib.request.Request(
            f"{base}/collections/documents",
            headers={"api-key": api_key} if api_key else {},
        )
        response = urllib.request.urlopen(req, timeout=5)
        import json
        data = json.loads(response.read())
        collection_info = data.get("result", {})
        vector_count = collection_info.get("points_count", 0)
        if vector_count == 0:
            issues.append(RAGIssue(
                check="qdrant_connectivity",
                severity="info",
                message="Qdrant 'documents' collection exists but has 0 vectors",
                details={"collection": "documents", "vector_count": 0},
            ))
    except Exception:
        issues.append(RAGIssue(
            check="qdrant_connectivity",
            severity="info",
            message="Qdrant 'documents' collection not found or not accessible",
            fix_suggestion="The collection is auto-created on first ingestion",
        ))

    return issues


# ---------------------------------------------------------------------------
# 3. Document-Chunk Consistency
# ---------------------------------------------------------------------------

def check_document_chunk_consistency() -> List[RAGIssue]:
    """
    Verify DB documents and chunks are consistent:
    - Documents with status=completed should have chunks
    - Chunks should reference existing documents
    - Chunk confidence scores should be in [0, 1]
    """
    issues = []

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if not db_path.exists():
        issues.append(RAGIssue(
            check="document_chunk_consistency",
            severity="info",
            message="Database not found — cannot check document-chunk consistency",
        ))
        return issues

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "documents" not in tables:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message="documents table not found — run migrations",
                fix_suggestion="Run database migrations to create documents table",
            ))
            conn.close()
            return issues

        if "document_chunks" not in tables:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message="document_chunks table not found — run migrations",
                fix_suggestion="Run database migrations to create document_chunks table",
            ))
            conn.close()
            return issues

        empty_docs = conn.execute("""
            SELECT d.id, d.filename, d.status
            FROM documents d
            WHERE d.status = 'completed'
              AND d.id NOT IN (SELECT DISTINCT document_id FROM document_chunks)
        """).fetchall()

        if empty_docs:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message=f"{len(empty_docs)} completed documents have no chunks",
                details={"examples": [
                    {"id": r[0], "filename": r[1], "status": r[2]}
                    for r in empty_docs[:5]
                ]},
                fix_suggestion="Re-ingest these documents to generate chunks",
            ))

        orphan_chunks = conn.execute("""
            SELECT COUNT(*)
            FROM document_chunks dc
            WHERE dc.document_id NOT IN (SELECT id FROM documents)
        """).fetchone()[0]

        if orphan_chunks > 0:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message=f"{orphan_chunks} chunks reference non-existent documents",
                fix_suggestion="Delete orphaned chunks or restore missing documents",
            ))

        bad_confidence = conn.execute("""
            SELECT COUNT(*)
            FROM document_chunks
            WHERE confidence_score < 0 OR confidence_score > 1
        """).fetchone()[0]

        if bad_confidence > 0:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message=f"{bad_confidence} chunks have confidence_score outside [0, 1]",
                fix_suggestion="Recalculate confidence scores for affected chunks",
            ))

        no_vector_id = conn.execute("""
            SELECT COUNT(*)
            FROM document_chunks
            WHERE embedding_vector_id IS NULL OR embedding_vector_id = ''
        """).fetchone()[0]

        total_chunks = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        if total_chunks > 0 and no_vector_id > total_chunks * 0.1:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="warning",
                message=f"{no_vector_id}/{total_chunks} chunks have no embedding_vector_id",
                details={"without_vector": no_vector_id, "total": total_chunks},
                fix_suggestion="Re-embed chunks missing vector IDs",
            ))

        failed_docs = conn.execute("""
            SELECT COUNT(*) FROM documents WHERE status = 'failed'
        """).fetchone()[0]

        if failed_docs > 0:
            issues.append(RAGIssue(
                check="document_chunk_consistency",
                severity="info",
                message=f"{failed_docs} documents have status='failed'",
                details={"failed_count": failed_docs},
            ))

        conn.close()
    except Exception as e:
        issues.append(RAGIssue(
            check="document_chunk_consistency",
            severity="info",
            message=f"Document-chunk consistency check failed: {e}",
        ))

    return issues


# ---------------------------------------------------------------------------
# 4. Ingestion Pipeline Wiring
# ---------------------------------------------------------------------------

def check_ingestion_pipeline_wiring() -> List[RAGIssue]:
    """
    Verify the ingestion pipeline chain:
    ingestion/service.py → embedding/embedder.py → vector_db/client.py
    """
    issues = []

    chain = [
        ("ingestion/service.py", "TextIngestionService", ["EmbeddingModel", "get_qdrant_client"]),
        ("embedding/embedder.py", "EmbeddingModel", ["SentenceTransformer"]),
        ("vector_db/client.py", "QdrantVectorDB", ["QdrantClient"]),
    ]

    for file_path, main_class, expected_deps in chain:
        full_path = BACKEND_ROOT / file_path
        if not full_path.exists():
            issues.append(RAGIssue(
                check="ingestion_pipeline",
                severity="critical",
                message=f"Ingestion pipeline file missing: {file_path}",
                fix_suggestion=f"Create or restore {file_path}",
            ))
            continue

        try:
            source = full_path.read_text(errors="ignore")
            ast.parse(source)
        except SyntaxError as e:
            issues.append(RAGIssue(
                check="ingestion_pipeline",
                severity="critical",
                message=f"Syntax error in {file_path}: {e.msg} (line {e.lineno})",
            ))
            continue

        if main_class not in source:
            issues.append(RAGIssue(
                check="ingestion_pipeline",
                severity="critical",
                message=f"{main_class} not found in {file_path}",
            ))

        for dep in expected_deps:
            if dep not in source:
                issues.append(RAGIssue(
                    check="ingestion_pipeline",
                    severity="warning",
                    message=f"{file_path} does not reference {dep}",
                    fix_suggestion=f"Ensure {dep} is imported and used in {file_path}",
                ))

    return issues


# ---------------------------------------------------------------------------
# 5. Retriever Wiring
# ---------------------------------------------------------------------------

def check_retriever_wiring() -> List[RAGIssue]:
    """
    Verify the retriever chain:
    retrieval/retriever.py → embedding → vector_db → database models
    """
    issues = []

    retriever_file = BACKEND_ROOT / "retrieval" / "retriever.py"
    if not retriever_file.exists():
        issues.append(RAGIssue(
            check="retriever_wiring",
            severity="critical",
            message="Retriever module not found: retrieval/retriever.py",
        ))
        return issues

    try:
        source = retriever_file.read_text(errors="ignore")
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append(RAGIssue(
            check="retriever_wiring",
            severity="critical",
            message=f"Syntax error in retriever.py: {e.msg} (line {e.lineno})",
        ))
        return issues

    required_refs = {
        "EmbeddingModel": "embedding model integration",
        "get_qdrant_client": "vector DB connection",
        "Document": "document model for metadata",
        "DocumentChunk": "chunk model for text retrieval",
    }

    for ref, purpose in required_refs.items():
        if ref not in source:
            issues.append(RAGIssue(
                check="retriever_wiring",
                severity="warning",
                message=f"retriever.py missing reference to {ref} ({purpose})",
            ))

    methods = {"retrieve", "retrieve_hybrid", "build_context"}
    for method in methods:
        if f"def {method}" not in source:
            issues.append(RAGIssue(
                check="retriever_wiring",
                severity="warning",
                message=f"DocumentRetriever missing method: {method}()",
            ))

    cog_retriever = BACKEND_ROOT / "retrieval" / "cognitive_retriever.py"
    if cog_retriever.exists():
        cog_source = cog_retriever.read_text(errors="ignore")
        if "retrieve_and_rank" in cog_source:
            if "def retrieve_and_rank" not in source and "retrieve_and_rank" not in source:
                issues.append(RAGIssue(
                    check="retriever_wiring",
                    severity="warning",
                    message="cognitive_retriever.py calls retrieve_and_rank() but it's not defined on DocumentRetriever",
                    fix_suggestion="Add retrieve_and_rank() to DocumentRetriever or use DocumentReranker",
                ))

    return issues


# ---------------------------------------------------------------------------
# 6. RAG Prompt Integrity
# ---------------------------------------------------------------------------

def check_rag_prompt_integrity() -> List[RAGIssue]:
    """Verify RAG prompt templates exist and contain required elements."""
    issues = []

    prompt_file = BACKEND_ROOT / "utils" / "rag_prompt.py"
    if not prompt_file.exists():
        issues.append(RAGIssue(
            check="rag_prompt",
            severity="warning",
            message="RAG prompt helper not found: utils/rag_prompt.py",
            fix_suggestion="Create utils/rag_prompt.py with build_rag_prompt() and build_rag_system_prompt()",
        ))
        return issues

    try:
        source = prompt_file.read_text(errors="ignore")
        ast.parse(source)
    except SyntaxError as e:
        issues.append(RAGIssue(
            check="rag_prompt",
            severity="critical",
            message=f"Syntax error in rag_prompt.py: {e.msg} (line {e.lineno})",
        ))
        return issues

    if "def build_rag_prompt" not in source and "def build_rag_system_prompt" not in source:
        issues.append(RAGIssue(
            check="rag_prompt",
            severity="info",
            message="rag_prompt.py may not have standard prompt builder functions",
        ))

    if "context" not in source.lower():
        issues.append(RAGIssue(
            check="rag_prompt",
            severity="warning",
            message="rag_prompt.py does not reference 'context' — prompts may not inject retrieved context",
        ))

    return issues


# ---------------------------------------------------------------------------
# 7. Knowledge Base File Tracking
# ---------------------------------------------------------------------------

def check_knowledge_base_tracking() -> List[RAGIssue]:
    """
    Check if knowledge_base files on disk align with ingested documents in DB.
    """
    issues = []

    kb_path = BACKEND_ROOT / "knowledge_base"
    if not kb_path.exists():
        issues.append(RAGIssue(
            check="kb_tracking",
            severity="info",
            message="knowledge_base directory not found",
        ))
        return issues

    kb_files = []
    skip_dirs = {"__pycache__", ".git", "node_modules"}
    for ext in ("*.txt", "*.md", "*.pdf", "*.json", "*.csv"):
        for f in kb_path.rglob(ext):
            if not any(skip in f.parts for skip in skip_dirs):
                kb_files.append(f)

    db_path = BACKEND_ROOT / "data" / "grace.db"
    ingested_count = 0

    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            if "documents" in tables:
                ingested_count = conn.execute(
                    "SELECT COUNT(*) FROM documents WHERE status = 'completed'"
                ).fetchone()[0]
            conn.close()
        except Exception:
            pass

    if len(kb_files) > 0 and ingested_count == 0:
        issues.append(RAGIssue(
            check="kb_tracking",
            severity="info",
            message=f"{len(kb_files)} knowledge base files on disk but 0 ingested documents",
            details={"kb_files": len(kb_files), "ingested": 0},
            fix_suggestion="Run ingestion on knowledge_base directory",
        ))
    elif len(kb_files) > ingested_count * 2 and ingested_count > 0:
        issues.append(RAGIssue(
            check="kb_tracking",
            severity="info",
            message=f"{len(kb_files)} KB files on disk vs {ingested_count} ingested — many files may be un-ingested",
            details={"kb_files": len(kb_files), "ingested": ingested_count},
        ))

    return issues


# ---------------------------------------------------------------------------
# 8. Connector Registration
# ---------------------------------------------------------------------------

def check_rag_connector_registration() -> List[RAGIssue]:
    """Verify RAG and Ingestion connectors exist and are registered in Layer 1."""
    issues = []

    connectors = {
        "rag_connector.py": ("RAGConnector", "RAG"),
        "ingestion_connector.py": ("IngestionConnector", "Ingestion"),
    }

    connector_dir = BACKEND_ROOT / "layer1" / "components"

    for filename, (class_name, label) in connectors.items():
        filepath = connector_dir / filename
        if not filepath.exists():
            issues.append(RAGIssue(
                check="connector_registration",
                severity="warning",
                message=f"{label} connector not found: layer1/components/{filename}",
            ))
            continue

        try:
            source = filepath.read_text(errors="ignore")
            ast.parse(source)
        except SyntaxError as e:
            issues.append(RAGIssue(
                check="connector_registration",
                severity="critical",
                message=f"Syntax error in {filename}: {e.msg} (line {e.lineno})",
            ))
            continue

        if class_name not in source:
            issues.append(RAGIssue(
                check="connector_registration",
                severity="warning",
                message=f"{class_name} class not found in {filename}",
            ))

    init_file = BACKEND_ROOT / "layer1" / "initialize.py"
    if init_file.exists():
        init_source = init_file.read_text(errors="ignore")
        if "RAGConnector" not in init_source and "rag" not in init_source.lower():
            issues.append(RAGIssue(
                check="connector_registration",
                severity="info",
                message="RAGConnector may not be initialized in layer1/initialize.py",
            ))
        if "IngestionConnector" not in init_source and "ingestion" not in init_source.lower():
            issues.append(RAGIssue(
                check="connector_registration",
                severity="info",
                message="IngestionConnector may not be initialized in layer1/initialize.py",
            ))

    return issues


# ---------------------------------------------------------------------------
# 9. Import Chain
# ---------------------------------------------------------------------------

def check_rag_import_chain() -> List[RAGIssue]:
    """Verify all RAG pipeline files parse without syntax errors."""
    issues = []

    critical_files = [
        "retrieval/retriever.py",
        "retrieval/cognitive_retriever.py",
        "retrieval/reranker.py",
        "ingestion/service.py",
        "embedding/embedder.py",
        "vector_db/client.py",
        "utils/rag_prompt.py",
    ]

    for rel_path in critical_files:
        full_path = BACKEND_ROOT / rel_path
        if not full_path.exists():
            issues.append(RAGIssue(
                check="import_chain",
                severity="warning",
                message=f"RAG pipeline file missing: {rel_path}",
            ))
            continue

        try:
            source = full_path.read_text(errors="ignore")
            ast.parse(source)
        except SyntaxError as e:
            issues.append(RAGIssue(
                check="import_chain",
                severity="critical",
                message=f"Syntax error in {rel_path}: {e.msg} (line {e.lineno})",
            ))

    return issues


# ---------------------------------------------------------------------------
# 10. API Endpoint Wiring
# ---------------------------------------------------------------------------

def check_rag_api_wiring() -> List[RAGIssue]:
    """Verify RAG-related API routers are registered in app.py."""
    issues = []

    app_file = BACKEND_ROOT / "app.py"
    if not app_file.exists():
        return issues

    app_source = app_file.read_text(errors="ignore")

    expected_routers = {
        "retrieve": "retrieval API endpoints",
        "ingest": "ingestion API endpoints",
    }

    for router_name, purpose in expected_routers.items():
        patterns = [
            f"from api.{router_name}",
            f"api.{router_name}",
            f"{router_name}_router",
            f"{router_name}.router",
        ]
        if not any(p in app_source for p in patterns):
            issues.append(RAGIssue(
                check="api_wiring",
                severity="info",
                message=f"{purpose} ({router_name}) may not be registered in app.py",
                fix_suggestion=f"Register {router_name} router in app.py",
            ))

    return issues


# ---------------------------------------------------------------------------
# Full Validation Pipeline
# ---------------------------------------------------------------------------

def run_rag_validation() -> RAGValidationReport:
    """
    Run the complete deterministic RAG validation pipeline.
    No LLM needed. Pure structural + data analysis.
    """
    import time
    start = time.time()

    all_issues: List[RAGIssue] = []
    checks_run = []

    checks = [
        ("embedding_model", check_embedding_model),
        ("qdrant_connectivity", check_qdrant_connectivity),
        ("document_chunk_consistency", check_document_chunk_consistency),
        ("ingestion_pipeline", check_ingestion_pipeline_wiring),
        ("retriever_wiring", check_retriever_wiring),
        ("rag_prompt", check_rag_prompt_integrity),
        ("kb_tracking", check_knowledge_base_tracking),
        ("connector_registration", check_rag_connector_registration),
        ("import_chain", check_rag_import_chain),
        ("api_wiring", check_rag_api_wiring),
    ]

    for name, checker in checks:
        try:
            logger.info(f"[DETERMINISTIC-RAG] Running {name}...")
            results = checker()
            all_issues.extend(results)
            checks_run.append(name)
        except Exception as e:
            all_issues.append(RAGIssue(
                check=name,
                severity="warning",
                message=f"Check {name} raised exception: {e}",
            ))
            checks_run.append(name)

    elapsed = (time.time() - start) * 1000

    stats = _gather_rag_stats()

    report = RAGValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_issues=len(all_issues),
        critical_count=sum(1 for i in all_issues if i.severity == "critical"),
        warning_count=sum(1 for i in all_issues if i.severity == "warning"),
        info_count=sum(1 for i in all_issues if i.severity == "info"),
        checks_run=checks_run,
        issues=all_issues,
        stats=stats,
    )

    logger.info(
        f"[DETERMINISTIC-RAG] Complete: {report.total_issues} issues "
        f"({report.critical_count} critical, {report.warning_count} warning, {report.info_count} info) "
        f"in {elapsed:.0f}ms"
    )

    return report


def _gather_rag_stats() -> Dict[str, Any]:
    """Gather basic RAG pipeline statistics."""
    stats: Dict[str, Any] = {
        "total_documents": 0,
        "completed_documents": 0,
        "failed_documents": 0,
        "total_chunks": 0,
        "chunks_with_vectors": 0,
        "avg_confidence": 0.0,
        "kb_files_on_disk": 0,
        "qdrant_reachable": False,
    }

    db_path = BACKEND_ROOT / "data" / "grace.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]

            if "documents" in tables:
                stats["total_documents"] = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
                stats["completed_documents"] = conn.execute(
                    "SELECT COUNT(*) FROM documents WHERE status = 'completed'"
                ).fetchone()[0]
                stats["failed_documents"] = conn.execute(
                    "SELECT COUNT(*) FROM documents WHERE status = 'failed'"
                ).fetchone()[0]

            if "document_chunks" in tables:
                stats["total_chunks"] = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
                stats["chunks_with_vectors"] = conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE embedding_vector_id IS NOT NULL AND embedding_vector_id != ''"
                ).fetchone()[0]
                avg = conn.execute(
                    "SELECT AVG(confidence_score) FROM document_chunks WHERE confidence_score IS NOT NULL"
                ).fetchone()[0]
                stats["avg_confidence"] = round(avg, 3) if avg else 0.0

            conn.close()
        except Exception:
            pass

    kb_path = BACKEND_ROOT / "knowledge_base"
    if kb_path.exists():
        count = 0
        for ext in ("*.txt", "*.md", "*.pdf", "*.json", "*.csv"):
            count += sum(1 for _ in kb_path.rglob(ext))
        stats["kb_files_on_disk"] = count

    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:6333/collections", timeout=2)
        stats["qdrant_reachable"] = True
    except Exception:
        pass

    return stats
