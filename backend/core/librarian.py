"""
Librarian — auto-categorization, tagging, versioning of all documents.

Every upload goes through the librarian:
  1. Extract metadata (title, type, language, size)
  2. Auto-categorize into folder structure
  3. Tag with keywords
  4. Version track (every save creates a version)
  5. Index for search
"""

import json
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

CATEGORY_MAP = {
    "code": [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".php"],
    "docs": [".md", ".txt", ".rst", ".doc", ".docx", ".pdf"],
    "data": [".json", ".yaml", ".yml", ".csv", ".xml", ".sql", ".toml"],
    "config": [".env", ".ini", ".cfg", ".conf", ".toml"],
    "media": [".png", ".jpg", ".gif", ".svg", ".mp4", ".mp3"],
    "web": [".html", ".css", ".scss"],
    "tests": [".test.py", ".test.js", ".spec.ts", ".test.ts"],
}

_document_index: List[dict] = []
_version_history: Dict[str, List[dict]] = {}


def ingest_document(file_path: str, content: str, project_id: str = "",
                    source: str = "upload") -> dict:
    """
    Process a document through the librarian pipeline.
    Auto-categorize, tag, version, index.
    """
    name = Path(file_path).name
    ext = Path(file_path).suffix.lower()
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    # 1. Auto-categorize
    category = "other"
    for cat, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            category = cat
            break

    # 2. Auto-tag
    tags = _extract_tags(content, ext)

    # 3. Extract metadata
    metadata = {
        "name": name,
        "extension": ext,
        "category": category,
        "tags": tags,
        "size": len(content),
        "lines": content.count("\n") + 1,
        "hash": content_hash,
        "project_id": project_id,
        "source": source,
        "ingested_at": datetime.utcnow().isoformat(),
    }

    # 4. Version tracking
    if file_path not in _version_history:
        _version_history[file_path] = []
    version = len(_version_history[file_path]) + 1
    _version_history[file_path].append({
        "version": version,
        "hash": content_hash,
        "size": len(content),
        "timestamp": datetime.utcnow().isoformat(),
        "source": source,
    })
    metadata["version"] = version

    # 5. Add to search index
    _document_index.append({
        "path": file_path,
        "name": name,
        "category": category,
        "tags": tags,
        "project_id": project_id,
        "size": len(content),
        "version": version,
        "indexed_at": datetime.utcnow().isoformat(),
        "content_preview": content[:200],
    })

    # Keep index bounded
    if len(_document_index) > 5000:
        _document_index.pop(0)

    # Track via Genesis
    try:
        from core.tracing import light_track
        light_track("file_ingestion", f"Librarian: {name} → {category} ({len(tags)} tags, v{version})",
                     "librarian", ["librarian", category, project_id])
    except Exception:
        pass

    return metadata


def _extract_tags(content: str, ext: str) -> list:
    """Extract keyword tags from content."""
    tags = set()

    if ext in (".py",):
        # Python: extract imports, class names, function names
        for match in re.finditer(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE):
            tags.add(match.group(1).split(".")[0])
        for match in re.finditer(r'^(?:class|def)\s+(\w+)', content, re.MULTILINE):
            tags.add(match.group(1))

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        for match in re.finditer(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", content):
            tags.add(match.group(1).split("/")[-1])
        for match in re.finditer(r"(?:function|class|const)\s+(\w+)", content):
            tags.add(match.group(1))

    elif ext in (".md", ".txt"):
        for match in re.finditer(r'^#+\s+(.+)$', content, re.MULTILINE):
            tags.add(match.group(1).strip()[:30])

    # Common keywords
    keywords = ["api", "database", "auth", "login", "user", "admin", "test",
                "config", "deploy", "build", "error", "fix", "feature"]
    content_lower = content.lower()
    for kw in keywords:
        if kw in content_lower:
            tags.add(kw)

    return list(tags)[:20]


def search_documents(query: str, project_id: str = "", category: str = "",
                     limit: int = 20) -> list:
    """Search across all indexed documents."""
    query_lower = query.lower()
    results = []

    for doc in reversed(_document_index):
        if project_id and doc.get("project_id") != project_id:
            continue
        if category and doc.get("category") != category:
            continue

        score = 0
        if query_lower in doc.get("name", "").lower():
            score += 3
        if query_lower in doc.get("content_preview", "").lower():
            score += 2
        if any(query_lower in tag.lower() for tag in doc.get("tags", [])):
            score += 1

        if score > 0:
            results.append({**doc, "score": score})

        if len(results) >= limit:
            break

    results.sort(key=lambda x: -x["score"])
    return results


def get_versions(file_path: str) -> list:
    """Get version history for a file."""
    return _version_history.get(file_path, [])


def get_document_stats() -> dict:
    """Get librarian statistics."""
    by_category = {}
    for doc in _document_index:
        cat = doc.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "total_indexed": len(_document_index),
        "total_versioned": len(_version_history),
        "by_category": by_category,
    }


def cross_project_search(query: str, limit: int = 30) -> list:
    """Search across ALL projects."""
    return search_documents(query, project_id="", limit=limit)
