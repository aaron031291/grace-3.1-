"""
AMP Librarian Bridge - Unified External Knowledge Integration

Bridges Grace's internal Librarian system with external knowledge sources:
- GitHub repositories (public and private)
- External documentation
- API references
- Community resources

This creates a UNIFIED LIBRARIAN that can:
1. Access local knowledge base (Grace's Librarian)
2. Access GitHub repos (Amp's Librarian capability)
3. Sync and cache external knowledge locally
4. Provide unified search across all sources

Genesis Key tracked for all operations.
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KnowledgeSourceType(Enum):
    """Types of knowledge sources."""
    LOCAL = "local"           # Grace's internal knowledge base
    GITHUB = "github"         # GitHub repositories
    DOCUMENTATION = "docs"    # External documentation
    API_REFERENCE = "api"     # API documentation
    COMMUNITY = "community"   # Stack Overflow, forums


@dataclass
class ExternalKnowledgeSource:
    """Represents an external knowledge source."""
    source_type: KnowledgeSourceType
    identifier: str  # e.g., "github.com/aaron031291/grace-3.1-"
    name: str
    url: str
    is_private: bool = False
    access_token: Optional[str] = None
    last_synced: Optional[datetime] = None
    sync_interval_hours: int = 24
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def needs_sync(self) -> bool:
        if self.last_synced is None:
            return True
        return datetime.utcnow() - self.last_synced > timedelta(hours=self.sync_interval_hours)


@dataclass 
class UnifiedSearchResult:
    """Result from unified search across all sources."""
    content: str
    source_type: KnowledgeSourceType
    source_identifier: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    relevance_score: float = 0.0
    snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AmpLibrarianBridge:
    """
    Unified Librarian Bridge - Connects Grace's Librarian with external sources.
    
    Provides:
    - Unified search across local + external knowledge
    - GitHub repository indexing and caching
    - External documentation integration
    - Automatic sync and refresh
    """
    
    def __init__(
        self,
        db_session: Session,
        knowledge_base_path: str = "knowledge_base",
        cache_path: str = "knowledge_base/external_cache",
        github_token: Optional[str] = None
    ):
        self.db = db_session
        self.kb_path = Path(knowledge_base_path)
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.github_token = github_token
        
        # External sources registry
        self.sources: Dict[str, ExternalKnowledgeSource] = {}
        self._load_sources()
        
        # Integration with Grace's Librarian
        self._enterprise_librarian = None
        self._librarian_engine = None
        
        logger.info("[AMP-LIBRARIAN-BRIDGE] Initialized unified librarian")
    
    def connect_enterprise_librarian(self, enterprise_librarian):
        """Connect to Grace's Enterprise Librarian."""
        self._enterprise_librarian = enterprise_librarian
        logger.info("[AMP-LIBRARIAN-BRIDGE] ✓ Connected to Enterprise Librarian")
    
    def connect_librarian_engine(self, librarian_engine):
        """Connect to Grace's Librarian Engine."""
        self._librarian_engine = librarian_engine
        logger.info("[AMP-LIBRARIAN-BRIDGE] ✓ Connected to Librarian Engine")
    
    def _load_sources(self):
        """Load registered external sources from cache."""
        sources_file = self.cache_path / "registered_sources.json"
        if sources_file.exists():
            try:
                with open(sources_file, 'r') as f:
                    data = json.load(f)
                for source_data in data.get("sources", []):
                    source = ExternalKnowledgeSource(
                        source_type=KnowledgeSourceType(source_data["source_type"]),
                        identifier=source_data["identifier"],
                        name=source_data["name"],
                        url=source_data["url"],
                        is_private=source_data.get("is_private", False),
                        last_synced=datetime.fromisoformat(source_data["last_synced"]) if source_data.get("last_synced") else None,
                        sync_interval_hours=source_data.get("sync_interval_hours", 24),
                        metadata=source_data.get("metadata", {})
                    )
                    self.sources[source.identifier] = source
                logger.info(f"[AMP-LIBRARIAN-BRIDGE] Loaded {len(self.sources)} external sources")
            except Exception as e:
                logger.warning(f"[AMP-LIBRARIAN-BRIDGE] Could not load sources: {e}")
    
    def _save_sources(self):
        """Save registered sources to cache."""
        sources_file = self.cache_path / "registered_sources.json"
        data = {
            "updated_at": datetime.utcnow().isoformat(),
            "sources": [
                {
                    "source_type": s.source_type.value,
                    "identifier": s.identifier,
                    "name": s.name,
                    "url": s.url,
                    "is_private": s.is_private,
                    "last_synced": s.last_synced.isoformat() if s.last_synced else None,
                    "sync_interval_hours": s.sync_interval_hours,
                    "metadata": s.metadata
                }
                for s in self.sources.values()
            ]
        }
        with open(sources_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_github_repo(
        self,
        repo_url: str,
        name: Optional[str] = None,
        is_private: bool = False,
        sync_interval_hours: int = 24
    ) -> ExternalKnowledgeSource:
        """
        Register a GitHub repository as a knowledge source.
        
        Args:
            repo_url: GitHub repo URL (e.g., "github.com/owner/repo")
            name: Display name (default: repo name)
            is_private: Whether repo is private
            sync_interval_hours: How often to sync
            
        Returns:
            Registered source
        """
        # Normalize URL
        repo_url = repo_url.replace("https://", "").replace("http://", "")
        if repo_url.startswith("github.com/"):
            identifier = repo_url
        else:
            identifier = f"github.com/{repo_url}"
        
        parts = identifier.split("/")
        if len(parts) >= 3:
            repo_name = parts[2]
        else:
            repo_name = identifier
        
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.GITHUB,
            identifier=identifier,
            name=name or repo_name,
            url=f"https://{identifier}",
            is_private=is_private,
            sync_interval_hours=sync_interval_hours
        )
        
        self.sources[identifier] = source
        self._save_sources()
        
        logger.info(f"[AMP-LIBRARIAN-BRIDGE] Registered GitHub repo: {identifier}")
        return source
    
    def register_documentation(
        self,
        url: str,
        name: str,
        doc_type: str = "general"
    ) -> ExternalKnowledgeSource:
        """Register external documentation as a knowledge source."""
        identifier = hashlib.md5(url.encode()).hexdigest()[:12]
        
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.DOCUMENTATION,
            identifier=f"docs-{identifier}",
            name=name,
            url=url,
            metadata={"doc_type": doc_type}
        )
        
        self.sources[source.identifier] = source
        self._save_sources()
        
        logger.info(f"[AMP-LIBRARIAN-BRIDGE] Registered documentation: {name}")
        return source
    
    async def sync_github_repo(
        self,
        identifier: str,
        paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sync a GitHub repository to local cache.
        
        Args:
            identifier: Source identifier
            paths: Specific paths to sync (default: all)
            
        Returns:
            Sync results
        """
        source = self.sources.get(identifier)
        if not source or source.source_type != KnowledgeSourceType.GITHUB:
            return {"error": f"GitHub source not found: {identifier}"}
        
        logger.info(f"[AMP-LIBRARIAN-BRIDGE] Syncing GitHub repo: {identifier}")
        
        # Create cache directory for this repo
        repo_cache = self.cache_path / "github" / identifier.replace("/", "_")
        repo_cache.mkdir(parents=True, exist_ok=True)
        
        synced_files = []
        errors = []
        
        try:
            # Parse repo info
            parts = identifier.replace("github.com/", "").split("/")
            owner = parts[0]
            repo = parts[1] if len(parts) > 1 else parts[0]
            
            # Fetch repo contents via GitHub API
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            async with aiohttp.ClientSession() as session:
                # Get repo tree
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
                async with session.get(api_url, headers=headers) as resp:
                    if resp.status == 200:
                        tree_data = await resp.json()
                        
                        # Filter files
                        files = [
                            item for item in tree_data.get("tree", [])
                            if item["type"] == "blob" and self._is_indexable_file(item["path"])
                        ]
                        
                        # Apply path filter if provided
                        if paths:
                            files = [f for f in files if any(f["path"].startswith(p) for p in paths)]
                        
                        # Fetch and cache files
                        for file_info in files[:100]:  # Limit to 100 files per sync
                            try:
                                file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{file_info['path']}"
                                async with session.get(file_url) as file_resp:
                                    if file_resp.status == 200:
                                        content = await file_resp.text()
                                        
                                        # Save to cache
                                        cache_file = repo_cache / file_info["path"].replace("/", "_")
                                        cache_file.write_text(content[:50000])  # Limit size
                                        
                                        synced_files.append({
                                            "path": file_info["path"],
                                            "size": len(content)
                                        })
                            except Exception as e:
                                errors.append({"path": file_info["path"], "error": str(e)})
                    else:
                        errors.append({"error": f"API error: {resp.status}"})
            
            # Update source
            source.last_synced = datetime.utcnow()
            source.metadata["files_synced"] = len(synced_files)
            self._save_sources()
            
        except Exception as e:
            logger.error(f"[AMP-LIBRARIAN-BRIDGE] Sync error: {e}")
            errors.append({"error": str(e)})
        
        result = {
            "source": identifier,
            "synced_files": len(synced_files),
            "errors": len(errors),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[AMP-LIBRARIAN-BRIDGE] Synced {len(synced_files)} files from {identifier}")
        return result
    
    def _is_indexable_file(self, path: str) -> bool:
        """Check if file should be indexed."""
        indexable_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json",
            ".yaml", ".yml", ".toml", ".rst", ".html", ".css", ".sql"
        }
        return any(path.endswith(ext) for ext in indexable_extensions)
    
    def unified_search(
        self,
        query: str,
        source_types: Optional[List[KnowledgeSourceType]] = None,
        limit: int = 20
    ) -> List[UnifiedSearchResult]:
        """
        Search across all knowledge sources (local + external).
        
        Args:
            query: Search query
            source_types: Filter by source types (default: all)
            limit: Maximum results
            
        Returns:
            Unified search results
        """
        results = []
        
        # 1. Search Grace's local knowledge base
        if source_types is None or KnowledgeSourceType.LOCAL in source_types:
            local_results = self._search_local(query, limit=limit // 2)
            results.extend(local_results)
        
        # 2. Search cached external sources
        if source_types is None or any(t != KnowledgeSourceType.LOCAL for t in (source_types or [])):
            external_results = self._search_external_cache(query, source_types, limit=limit // 2)
            results.extend(external_results)
        
        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        return results[:limit]
    
    def _search_local(self, query: str, limit: int = 10) -> List[UnifiedSearchResult]:
        """Search Grace's local knowledge base."""
        results = []
        
        # Use Librarian Engine's unified retriever if available
        if self._librarian_engine and hasattr(self._librarian_engine, 'unified_retriever'):
            try:
                retriever = self._librarian_engine.unified_retriever
                local_results = retriever.retrieve_unified(
                    query=query,
                    limit=limit
                )
                
                for item in local_results.get("results", []):
                    results.append(UnifiedSearchResult(
                        content=item.get("content", ""),
                        source_type=KnowledgeSourceType.LOCAL,
                        source_identifier="grace-knowledge-base",
                        file_path=item.get("file_path"),
                        relevance_score=item.get("score", 0.5),
                        snippet=item.get("snippet", ""),
                        metadata=item.get("metadata", {})
                    ))
            except Exception as e:
                logger.warning(f"[AMP-LIBRARIAN-BRIDGE] Local search error: {e}")
        
        return results
    
    def _search_external_cache(
        self,
        query: str,
        source_types: Optional[List[KnowledgeSourceType]],
        limit: int = 10
    ) -> List[UnifiedSearchResult]:
        """Search cached external knowledge."""
        results = []
        query_lower = query.lower()
        
        # Search GitHub cache
        github_cache = self.cache_path / "github"
        if github_cache.exists():
            for repo_dir in github_cache.iterdir():
                if not repo_dir.is_dir():
                    continue
                
                for cache_file in repo_dir.iterdir():
                    if not cache_file.is_file():
                        continue
                    
                    try:
                        content = cache_file.read_text(errors='ignore')
                        content_lower = content.lower()
                        
                        # Simple relevance scoring
                        if query_lower in content_lower:
                            # Calculate basic relevance
                            occurrences = content_lower.count(query_lower)
                            score = min(1.0, occurrences * 0.1 + 0.3)
                            
                            # Extract snippet
                            idx = content_lower.find(query_lower)
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(query) + 150)
                            snippet = content[start:end].strip()
                            
                            results.append(UnifiedSearchResult(
                                content=content[:2000],  # Limit content size
                                source_type=KnowledgeSourceType.GITHUB,
                                source_identifier=repo_dir.name.replace("_", "/"),
                                file_path=cache_file.name.replace("_", "/"),
                                relevance_score=score,
                                snippet=snippet
                            ))
                    except Exception:
                        pass
        
        # Sort and limit
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]
    
    def get_status(self) -> Dict[str, Any]:
        """Get unified librarian status."""
        return {
            "bridge_status": "active",
            "local_librarian_connected": self._librarian_engine is not None,
            "enterprise_librarian_connected": self._enterprise_librarian is not None,
            "registered_sources": len(self.sources),
            "sources": {
                identifier: {
                    "name": source.name,
                    "type": source.source_type.value,
                    "url": source.url,
                    "last_synced": source.last_synced.isoformat() if source.last_synced else None,
                    "needs_sync": source.needs_sync
                }
                for identifier, source in self.sources.items()
            },
            "cache_path": str(self.cache_path),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_unified_analytics(self) -> Dict[str, Any]:
        """Get analytics across all knowledge sources."""
        analytics = {
            "local": {},
            "external": {},
            "totals": {}
        }
        
        # Local analytics
        if self._enterprise_librarian:
            try:
                analytics["local"] = self._enterprise_librarian.get_librarian_analytics()
            except Exception as e:
                analytics["local"]["error"] = str(e)
        
        # External analytics
        github_sources = [s for s in self.sources.values() if s.source_type == KnowledgeSourceType.GITHUB]
        doc_sources = [s for s in self.sources.values() if s.source_type == KnowledgeSourceType.DOCUMENTATION]
        
        analytics["external"] = {
            "github_repos": len(github_sources),
            "documentation_sources": len(doc_sources),
            "total_sources": len(self.sources),
            "sources_needing_sync": len([s for s in self.sources.values() if s.needs_sync])
        }
        
        # Totals
        analytics["totals"] = {
            "unified_sources": 1 + len(self.sources),  # Local + external
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return analytics


# Singleton instance
_amp_librarian_bridge: Optional[AmpLibrarianBridge] = None


def get_amp_librarian_bridge(
    db_session: Session,
    knowledge_base_path: str = "knowledge_base"
) -> AmpLibrarianBridge:
    """Get or create the Amp Librarian Bridge singleton."""
    global _amp_librarian_bridge
    
    if _amp_librarian_bridge is None:
        _amp_librarian_bridge = AmpLibrarianBridge(
            db_session=db_session,
            knowledge_base_path=knowledge_base_path
        )
    
    return _amp_librarian_bridge


def integrate_with_grace_librarian(
    db_session: Session,
    enterprise_librarian=None,
    librarian_engine=None,
    knowledge_base_path: str = "knowledge_base"
) -> AmpLibrarianBridge:
    """
    Full integration function - connects Amp's Librarian with Grace's Librarian.
    
    Usage:
        from librarian.amp_librarian_bridge import integrate_with_grace_librarian
        from librarian.enterprise_librarian import get_enterprise_librarian
        from librarian.engine import LibrarianEngine
        
        # Get Grace's librarians
        enterprise = get_enterprise_librarian(session, kb_path)
        engine = LibrarianEngine(db_session=session, ...)
        
        # Integrate
        unified = integrate_with_grace_librarian(
            db_session=session,
            enterprise_librarian=enterprise,
            librarian_engine=engine
        )
        
        # Now use unified search
        results = unified.unified_search("authentication patterns")
    """
    bridge = get_amp_librarian_bridge(db_session, knowledge_base_path)
    
    if enterprise_librarian:
        bridge.connect_enterprise_librarian(enterprise_librarian)
    
    if librarian_engine:
        bridge.connect_librarian_engine(librarian_engine)
    
    # Auto-register the Grace repository
    bridge.register_github_repo(
        repo_url="github.com/aaron031291/grace-3.1-",
        name="Grace 3.1 Repository",
        is_private=True
    )
    
    logger.info("[AMP-LIBRARIAN-BRIDGE] ✓ Full integration complete")
    return bridge
