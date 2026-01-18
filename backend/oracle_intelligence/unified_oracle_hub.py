"""
Unified Oracle Hub - Central Intelligence Ingestion System

Routes ALL inbound intelligence to the Oracle as the single source of truth:
- AI Research (arXiv, HuggingFace)
- GitHub (pulls, issues, code)
- Stack Overflow solutions
- Sandbox insights and lessons learned
- Coding templates and patterns
- Learning memory training data
- Whitelist approved sources
- Internal updates and self-healing fixes
- Librarian ingestion pipeline
- Pattern discoveries
"""

import logging
import asyncio
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class IntelligenceSource(str, Enum):
    """All sources of intelligence that feed the Oracle."""
    AI_RESEARCH = "ai_research"           # arXiv, HuggingFace papers
    GITHUB_PULLS = "github_pulls"         # GitHub PRs, issues, code
    STACKOVERFLOW = "stackoverflow"       # Stack Overflow Q&A
    SANDBOX_INSIGHTS = "sandbox_insights" # Lessons from sandbox experiments
    TEMPLATES = "templates"               # Coding patterns and templates
    LEARNING_MEMORY = "learning_memory"   # Training data, trust scores
    WHITELIST_SOURCES = "whitelist"       # Approved external sources
    INTERNAL_UPDATES = "internal_updates" # Self-healing fixes
    LIBRARIAN_INGESTION = "librarian"     # Files ingested via Librarian
    PATTERN_DISCOVERY = "pattern"         # New patterns discovered
    WEB_KNOWLEDGE = "web_knowledge"       # General web research
    DOCUMENTATION = "documentation"       # Official docs
    USER_FEEDBACK = "user_feedback"       # User corrections/feedback


@dataclass
class IntelligenceItem:
    """Standardized format for any intelligence entering the Oracle."""
    item_id: str
    source: IntelligenceSource
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    code_examples: List[str] = field(default_factory=list)
    patterns_discovered: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)
    confidence: float = 0.7
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    source_files: List[str] = field(default_factory=list)
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source": self.source.value,
            "title": self.title,
            "content": self.content[:1000],
            "confidence": self.confidence,
            "tags": self.tags,
            "source_url": self.source_url,
            "genesis_key_id": self.genesis_key_id,
            "created_at": self.created_at.isoformat(),
            "processed": self.processed
        }


class UnifiedOracleHub:
    """
    Central hub that routes ALL intelligence to the Oracle.
    
    The Oracle becomes the single source of truth for:
    - All AI research and learnings
    - All patterns discovered
    - All templates and code examples
    - All sandbox insights
    - All external knowledge
    - All internal improvements
    """
    
    def __init__(
        self,
        session=None,
        genesis_service=None,
        oracle_core=None,
        librarian_pipeline=None,
        learning_memory=None,
        sandbox_lab=None,
        knowledge_base_path: Optional[Path] = None
    ):
        self.session = session
        self._genesis_service = genesis_service
        self._oracle_core = oracle_core
        self._librarian = librarian_pipeline
        self._learning_memory = learning_memory
        self._sandbox_lab = sandbox_lab
        
        # Knowledge base export path
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.oracle_export_path = self.knowledge_base_path / "oracle"
        self.oracle_export_path.mkdir(parents=True, exist_ok=True)
        
        # Ingestion queue
        self._queue: List[IntelligenceItem] = []
        self._processing = False
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_running = False
        
        # Statistics per source
        self._stats: Dict[str, Dict[str, Any]] = {
            source.value: {
                "total_ingested": 0,
                "successful": 0,
                "failed": 0,
                "last_ingestion": None
            }
            for source in IntelligenceSource
        }
        
        # Callbacks for hooks
        self._on_ingest_callbacks: List[Callable] = []
        
        # Cache of recent items (for deduplication)
        self._recent_hashes: set = set()
        
        logger.info("[ORACLE-HUB] Unified Oracle Hub initialized")
    
    # =========================================================================
    # MAIN INGESTION ENTRY POINT
    # =========================================================================
    
    async def ingest(self, item: IntelligenceItem) -> Dict[str, Any]:
        """
        Main entry point - ingests any intelligence item into the Oracle.
        
        All other ingest_from_* methods call this.
        """
        try:
            # Deduplication check
            content_hash = self._hash_content(item.content)
            if content_hash in self._recent_hashes:
                logger.debug(f"[ORACLE-HUB] Skipping duplicate: {item.title[:50]}")
                return {"status": "skipped", "reason": "duplicate"}
            
            self._recent_hashes.add(content_hash)
            if len(self._recent_hashes) > 10000:
                self._recent_hashes = set(list(self._recent_hashes)[-5000:])
            
            # Create Genesis key for tracking
            if self._genesis_service and not item.genesis_key_id:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    key = self._genesis_service.create_key(
                        key_type=GenesisKeyType.RESEARCH_STORED,
                        what_description=f"Oracle Ingestion: {item.title[:50]}",
                        who_actor="UnifiedOracleHub",
                        where_location=f"oracle/{item.source.value}",
                        why_reason=f"Intelligence from {item.source.value}",
                        how_method="unified_oracle_hub.ingest",
                        context_data={
                            "item_id": item.item_id,
                            "source": item.source.value,
                            "tags": item.tags
                        },
                        session=self.session
                    )
                    item.genesis_key_id = key.key_id
                except Exception as e:
                    logger.warning(f"[ORACLE-HUB] Genesis key creation failed: {e}")
            
            # Store in Oracle
            if self._oracle_core:
                research_entry = await self._oracle_core.store_research(
                    topic=item.title,
                    findings=item.content,
                    code_examples=item.code_examples,
                    source_files=item.source_files
                )
                item.processed = True
                logger.info(f"[ORACLE-HUB] Stored in Oracle: {item.title[:50]}")
            
            # Export to knowledge base
            await self._export_item(item)
            
            # Update stats
            self._stats[item.source.value]["total_ingested"] += 1
            self._stats[item.source.value]["successful"] += 1
            self._stats[item.source.value]["last_ingestion"] = datetime.utcnow().isoformat()
            
            # Fire callbacks
            for callback in self._on_ingest_callbacks:
                try:
                    callback(item)
                except Exception as e:
                    logger.warning(f"[ORACLE-HUB] Callback error: {e}")
            
            return {
                "status": "success",
                "item_id": item.item_id,
                "genesis_key_id": item.genesis_key_id,
                "source": item.source.value
            }
            
        except Exception as e:
            logger.error(f"[ORACLE-HUB] Ingestion failed: {e}")
            self._stats[item.source.value]["failed"] += 1
            return {"status": "error", "error": str(e)}
    
    # =========================================================================
    # SOURCE-SPECIFIC INGESTION METHODS
    # =========================================================================
    
    async def ingest_from_sandbox(
        self,
        experiment_id: str,
        experiment_name: str,
        results: Dict[str, Any],
        lessons_learned: List[str],
        success: bool = True
    ) -> Dict[str, Any]:
        """Ingest insights from sandbox experiments."""
        content = f"Experiment: {experiment_name}\n\n"
        content += f"Results: {json.dumps(results, indent=2)}\n\n"
        content += "Lessons Learned:\n"
        for lesson in lessons_learned:
            content += f"- {lesson}\n"
        
        item = IntelligenceItem(
            item_id=f"SANDBOX-{experiment_id}",
            source=IntelligenceSource.SANDBOX_INSIGHTS,
            title=f"Sandbox Experiment: {experiment_name}",
            content=content,
            metadata={
                "experiment_id": experiment_id,
                "success": success,
                "results": results
            },
            success_patterns=lessons_learned if success else [],
            failure_patterns=lessons_learned if not success else [],
            confidence=0.8 if success else 0.6,
            tags=["sandbox", "experiment", "self-improvement"]
        )
        
        return await self.ingest(item)
    
    async def ingest_from_learning_memory(
        self,
        training_type: str,
        data: Dict[str, Any],
        trust_score: float = 0.7
    ) -> Dict[str, Any]:
        """Ingest from learning memory training data."""
        content = f"Training Type: {training_type}\n\n"
        content += f"Data:\n{json.dumps(data, indent=2, default=str)}\n"
        content += f"Trust Score: {trust_score}"
        
        item = IntelligenceItem(
            item_id=f"LEARNING-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.LEARNING_MEMORY,
            title=f"Learning Memory: {training_type}",
            content=content,
            metadata={
                "training_type": training_type,
                "trust_score": trust_score,
                "data_keys": list(data.keys()) if isinstance(data, dict) else []
            },
            confidence=trust_score,
            tags=["learning", "training", training_type]
        )
        
        return await self.ingest(item)
    
    async def ingest_from_librarian(
        self,
        ingestion_id: str,
        filename: str,
        content_type: str,
        content_summary: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Hook into Librarian pipeline - ingest every file."""
        item = IntelligenceItem(
            item_id=f"LIBRARIAN-{ingestion_id}",
            source=IntelligenceSource.LIBRARIAN_INGESTION,
            title=f"Ingested: {filename}",
            content=content_summary,
            metadata={
                "ingestion_id": ingestion_id,
                "content_type": content_type,
                "file_path": file_path
            },
            source_files=[file_path],
            confidence=0.9,
            tags=["librarian", "ingestion", content_type]
        )
        
        return await self.ingest(item)
    
    async def ingest_from_github(
        self,
        repo_url: str,
        data_type: str,  # "pull", "issue", "code", "release"
        title: str,
        content: str,
        code_examples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Ingest GitHub data (pulls, issues, code)."""
        item = IntelligenceItem(
            item_id=f"GITHUB-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.GITHUB_PULLS,
            title=f"GitHub {data_type}: {title}",
            content=content,
            metadata={
                "repo_url": repo_url,
                "data_type": data_type
            },
            code_examples=code_examples or [],
            source_url=repo_url,
            confidence=0.8,
            tags=["github", data_type, "external"]
        )
        
        return await self.ingest(item)
    
    async def ingest_from_template(
        self,
        template_name: str,
        pattern_type: str,
        code_example: str,
        description: str,
        category: str
    ) -> Dict[str, Any]:
        """Ingest coding template/pattern."""
        content = f"Pattern: {pattern_type}\n\n"
        content += f"Description: {description}\n\n"
        content += f"Code Example:\n```\n{code_example}\n```"
        
        item = IntelligenceItem(
            item_id=f"TEMPLATE-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.TEMPLATES,
            title=f"Template: {template_name}",
            content=content,
            metadata={
                "pattern_type": pattern_type,
                "category": category
            },
            code_examples=[code_example],
            patterns_discovered=[pattern_type],
            confidence=0.9,
            tags=["template", "pattern", category, pattern_type]
        )
        
        return await self.ingest(item)
    
    async def ingest_from_self_healing(
        self,
        error_type: str,
        error_message: str,
        fix_applied: str,
        success: bool,
        affected_files: List[str]
    ) -> Dict[str, Any]:
        """Ingest self-healing fix results."""
        content = f"Error Type: {error_type}\n"
        content += f"Error Message: {error_message}\n\n"
        content += f"Fix Applied: {fix_applied}\n"
        content += f"Success: {success}"
        
        item = IntelligenceItem(
            item_id=f"HEAL-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.INTERNAL_UPDATES,
            title=f"Self-Healing: {error_type}",
            content=content,
            metadata={
                "error_type": error_type,
                "success": success
            },
            source_files=affected_files,
            success_patterns=[fix_applied] if success else [],
            failure_patterns=[error_type] if not success else [],
            confidence=0.85 if success else 0.5,
            tags=["self-healing", "fix", error_type]
        )
        
        return await self.ingest(item)
    
    async def ingest_whitelist_source(
        self,
        source_name: str,
        source_url: str,
        source_type: str,
        content: str
    ) -> Dict[str, Any]:
        """Ingest from approved whitelist source."""
        item = IntelligenceItem(
            item_id=f"WHITELIST-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.WHITELIST_SOURCES,
            title=f"Whitelist: {source_name}",
            content=content,
            metadata={
                "source_name": source_name,
                "source_type": source_type
            },
            source_url=source_url,
            confidence=0.9,  # Whitelist sources are trusted
            tags=["whitelist", "approved", source_type]
        )
        
        return await self.ingest(item)
    
    async def ingest_pattern_discovery(
        self,
        pattern_name: str,
        pattern_description: str,
        occurrences: int,
        source_files: List[str],
        is_success_pattern: bool = True
    ) -> Dict[str, Any]:
        """Ingest newly discovered pattern."""
        content = f"Pattern: {pattern_name}\n\n"
        content += f"Description: {pattern_description}\n"
        content += f"Occurrences: {occurrences}\n"
        content += f"Source Files: {', '.join(source_files[:5])}"
        
        item = IntelligenceItem(
            item_id=f"PATTERN-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.PATTERN_DISCOVERY,
            title=f"Pattern: {pattern_name}",
            content=content,
            metadata={
                "occurrences": occurrences,
                "is_success": is_success_pattern
            },
            source_files=source_files,
            patterns_discovered=[pattern_name],
            success_patterns=[pattern_name] if is_success_pattern else [],
            failure_patterns=[pattern_name] if not is_success_pattern else [],
            confidence=min(0.95, 0.5 + occurrences * 0.05),
            tags=["pattern", "discovery", "success" if is_success_pattern else "failure"]
        )
        
        return await self.ingest(item)
    
    async def ingest_ai_research(
        self,
        paper_title: str,
        abstract: str,
        key_findings: List[str],
        source_url: str,
        source: str = "arxiv"
    ) -> Dict[str, Any]:
        """Ingest AI research papers."""
        content = f"Abstract:\n{abstract}\n\n"
        content += "Key Findings:\n"
        for finding in key_findings:
            content += f"- {finding}\n"
        
        item = IntelligenceItem(
            item_id=f"RESEARCH-{uuid.uuid4().hex[:12]}",
            source=IntelligenceSource.AI_RESEARCH,
            title=paper_title,
            content=content,
            metadata={
                "paper_source": source,
                "findings_count": len(key_findings)
            },
            source_url=source_url,
            confidence=0.85,
            tags=["research", "ai", source]
        )
        
        return await self.ingest(item)
    
    # =========================================================================
    # EXPORT AND SYNC
    # =========================================================================
    
    async def _export_item(self, item: IntelligenceItem):
        """Export item to knowledge_base/oracle/ folder."""
        try:
            source_dir = self.oracle_export_path / item.source.value
            source_dir.mkdir(parents=True, exist_ok=True)
            
            export_file = source_dir / f"{item.item_id}.json"
            with open(export_file, "w") as f:
                json.dump(item.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Export failed: {e}")
    
    async def export_to_knowledge_base(self) -> Dict[str, Any]:
        """Export all Oracle research to knowledge_base/oracle/."""
        exported = 0
        
        if self._oracle_core and hasattr(self._oracle_core, '_research'):
            for research_id, entry in self._oracle_core._research.items():
                try:
                    export_file = self.oracle_export_path / "research" / f"{research_id}.json"
                    export_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(export_file, "w") as f:
                        json.dump(entry.to_dict(), f, indent=2)
                    exported += 1
                except Exception as e:
                    logger.warning(f"[ORACLE-HUB] Export error: {e}")
        
        # Create index file
        index = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_exported": exported,
            "sources": {s.value: self._stats[s.value] for s in IntelligenceSource}
        }
        
        with open(self.oracle_export_path / "index.json", "w") as f:
            json.dump(index, f, indent=2)
        
        logger.info(f"[ORACLE-HUB] Exported {exported} items to knowledge base")
        
        return {"exported": exported, "path": str(self.oracle_export_path)}
    
    def start_background_sync(self, interval_seconds: int = 300):
        """Start background sync of all sources."""
        if self._sync_running:
            return {"status": "already_running"}
        
        self._sync_running = True
        
        def sync_loop():
            while self._sync_running:
                try:
                    asyncio.run(self._run_sync_cycle())
                except Exception as e:
                    logger.error(f"[ORACLE-HUB] Sync error: {e}")
                
                for _ in range(interval_seconds):
                    if not self._sync_running:
                        break
                    import time
                    time.sleep(1)
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        
        logger.info("[ORACLE-HUB] Background sync started")
        return {"status": "started", "interval": interval_seconds}
    
    def stop_background_sync(self):
        """Stop background sync."""
        self._sync_running = False
        logger.info("[ORACLE-HUB] Background sync stopped")
        return {"status": "stopped"}
    
    async def load_coding_patterns(self) -> Dict[str, Any]:
        """Load coding patterns from knowledge_base/oracle/coding_patterns/."""
        patterns_dir = self.oracle_export_path / "coding_patterns"
        
        if not patterns_dir.exists():
            return {"status": "no_patterns", "loaded": 0}
        
        loaded = 0
        try:
            # Load main library
            main_file = patterns_dir / "coding_patterns_library.json"
            if main_file.exists():
                with open(main_file, 'r', encoding='utf-8') as f:
                    library = json.load(f)
                
                # Ingest each category as a knowledge item
                for category, data in library.get('categories', {}).items():
                    patterns = data.get('mbpp_patterns', []) + data.get('humaneval_patterns', [])
                    
                    if patterns:
                        await self.ingest(IntelligenceItem(
                            item_id=f"coding_patterns_{category}",
                            source=IntelligenceSource.LEARNING_MEMORY,
                            title=f"Coding Patterns: {category}",
                            content=json.dumps(patterns[:50]),  # Top 50 per category
                            tags=["coding_patterns", category, "benchmark"],
                            trust_score=0.95,
                            metadata={
                                "category": category,
                                "pattern_count": len(patterns),
                                "source_benchmarks": ["MBPP", "HumanEval"]
                            }
                        ))
                        loaded += 1
                
                logger.info(f"[ORACLE-HUB] Loaded {loaded} coding pattern categories")
                
        except Exception as e:
            logger.error(f"[ORACLE-HUB] Failed to load coding patterns: {e}")
            return {"status": "error", "error": str(e)}
        
        return {"status": "loaded", "categories": loaded}
    
    async def _run_sync_cycle(self):
        """Run one sync cycle - pull from all sources."""
        logger.info("[ORACLE-HUB] Running sync cycle...")
        
        # Load coding patterns on first sync
        await self.load_coding_patterns()
        
        # Sync from learning memory
        if self._learning_memory:
            try:
                if hasattr(self._learning_memory, 'get_recent_learnings'):
                    learnings = self._learning_memory.get_recent_learnings(limit=10)
                    for learning in learnings:
                        await self.ingest_from_learning_memory(
                            training_type=learning.get("type", "general"),
                            data=learning,
                            trust_score=learning.get("trust_score", 0.7)
                        )
            except Exception as e:
                logger.warning(f"[ORACLE-HUB] Learning memory sync failed: {e}")
        
        # Sync from sandbox
        if self._sandbox_lab:
            try:
                if hasattr(self._sandbox_lab, 'get_recent_experiments'):
                    experiments = self._sandbox_lab.get_recent_experiments(limit=5)
                    for exp in experiments:
                        await self.ingest_from_sandbox(
                            experiment_id=exp.get("id", "unknown"),
                            experiment_name=exp.get("name", "Unknown Experiment"),
                            results=exp.get("results", {}),
                            lessons_learned=exp.get("lessons", []),
                            success=exp.get("success", False)
                        )
            except Exception as e:
                logger.warning(f"[ORACLE-HUB] Sandbox sync failed: {e}")
        
        # Export to knowledge base
        await self.export_to_knowledge_base()
    
    # =========================================================================
    # HOOKS
    # =========================================================================
    
    def add_on_ingest_callback(self, callback: Callable):
        """Add callback to be fired on each ingestion."""
        self._on_ingest_callbacks.append(callback)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _hash_content(self, content: str) -> str:
        """Hash content for deduplication."""
        import hashlib
        return hashlib.md5(content[:500].encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        total = sum(s["total_ingested"] for s in self._stats.values())
        successful = sum(s["successful"] for s in self._stats.values())
        failed = sum(s["failed"] for s in self._stats.values())
        
        return {
            "total_ingested": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "by_source": self._stats,
            "sync_running": self._sync_running
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete hub status."""
        return {
            "status": "active",
            "oracle_connected": self._oracle_core is not None,
            "librarian_connected": self._librarian is not None,
            "learning_memory_connected": self._learning_memory is not None,
            "sandbox_connected": self._sandbox_lab is not None,
            "genesis_service_connected": self._genesis_service is not None,
            "export_path": str(self.oracle_export_path),
            "stats": self.get_stats()
        }
    
    # =========================================================================
    # INTELLIGENCE QUERY METHODS (for Layer 2 Integration)
    # =========================================================================
    
    def search_intelligence(
        self,
        query: str,
        sources: Optional[List[IntelligenceSource]] = None,
        limit: int = 5
    ) -> List[IntelligenceItem]:
        """
        Search Oracle for relevant intelligence items.
        
        Args:
            query: Search query string
            sources: Optional filter by intelligence sources
            limit: Maximum number of results
        
        Returns:
            List of matching IntelligenceItem objects
        """
        results = []
        
        try:
            # Search in Oracle Core if available
            if self._oracle_core:
                try:
                    oracle_results = self._oracle_core.search(query, limit=limit)
                    for r in oracle_results:
                        item = IntelligenceItem(
                            item_id=r.get("id", str(uuid.uuid4())),
                            source=IntelligenceSource.INTERNAL_UPDATES,
                            title=r.get("topic", r.get("title", query)),
                            content=r.get("findings", r.get("content", "")),
                            confidence=r.get("confidence", 0.7),
                            tags=r.get("tags", [])
                        )
                        results.append(item)
                except Exception as e:
                    logger.debug(f"[ORACLE-HUB] Oracle Core search failed: {e}")
            
            # Search exported files in knowledge base
            if not results:
                results = self._search_exported_files(query, sources, limit)
            
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Search failed: {e}")
        
        return results[:limit]
    
    def _search_exported_files(
        self,
        query: str,
        sources: Optional[List[IntelligenceSource]] = None,
        limit: int = 5
    ) -> List[IntelligenceItem]:
        """Search exported JSON files for matching intelligence."""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        try:
            for source_dir in self.oracle_export_path.iterdir():
                if not source_dir.is_dir():
                    continue
                    
                # Filter by source if specified
                if sources:
                    source_values = [s.value for s in sources]
                    if source_dir.name not in source_values:
                        continue
                
                for json_file in source_dir.glob("*.json"):
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        
                        # Score relevance
                        title = data.get("title", "").lower()
                        content = data.get("content", "")[:500].lower()
                        tags = [t.lower() for t in data.get("tags", [])]
                        
                        score = 0
                        for word in query_words:
                            if word in title:
                                score += 3
                            if word in content:
                                score += 1
                            if word in tags:
                                score += 2
                        
                        if score > 0:
                            # Map source string to enum
                            try:
                                source_enum = IntelligenceSource(source_dir.name)
                            except ValueError:
                                source_enum = IntelligenceSource.INTERNAL_UPDATES
                            
                            item = IntelligenceItem(
                                item_id=data.get("item_id", json_file.stem),
                                source=source_enum,
                                title=data.get("title", ""),
                                content=data.get("content", ""),
                                confidence=data.get("confidence", 0.7),
                                tags=data.get("tags", [])
                            )
                            results.append((score, item))
                            
                    except Exception:
                        continue
            
            # Sort by score and return top results
            results.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in results[:limit]]
            
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] File search failed: {e}")
            return []
    
    def get_templates_for_intent(self, intent: str) -> List[Dict[str, Any]]:
        """
        Get coding templates relevant to an intent.
        
        Args:
            intent: The user's intent or goal
        
        Returns:
            List of template dictionaries with name, pattern, confidence
        """
        templates = []
        intent_lower = intent.lower()
        
        try:
            # Search template files
            template_dir = self.oracle_export_path / "templates"
            if template_dir.exists():
                for json_file in template_dir.glob("*.json"):
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        
                        # Check relevance
                        title = data.get("title", "").lower()
                        tags = [t.lower() for t in data.get("tags", [])]
                        
                        if any(word in title or word in " ".join(tags) 
                               for word in intent_lower.split()):
                            templates.append({
                                "name": data.get("title", json_file.stem),
                                "pattern": data.get("content", "")[:500],
                                "confidence": data.get("confidence", 0.7),
                                "tags": data.get("tags", [])
                            })
                    except Exception:
                        continue
            
            # Also check coding patterns
            patterns_dir = self.oracle_export_path / "pattern"
            if patterns_dir.exists():
                for json_file in patterns_dir.glob("*.json"):
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        
                        title = data.get("title", "").lower()
                        if any(word in title for word in intent_lower.split()):
                            templates.append({
                                "name": data.get("title", json_file.stem),
                                "pattern": data.get("content", "")[:500],
                                "confidence": data.get("confidence", 0.7),
                                "tags": data.get("tags", [])
                            })
                    except Exception:
                        continue
            
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Template search failed: {e}")
        
        return templates[:10]
    
    def get_recent_learnings(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent learning entries from the Oracle.
        
        Args:
            limit: Maximum number of learnings to return
        
        Returns:
            List of learning dictionaries with source, insight, timestamp
        """
        learnings = []
        
        try:
            # Check learning memory exports
            learning_dir = self.oracle_export_path / "learning_memory"
            if learning_dir.exists():
                files = sorted(
                    learning_dir.glob("*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True
                )
                
                for json_file in files[:limit]:
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        
                        learnings.append({
                            "source": data.get("source", "learning_memory"),
                            "insight": data.get("content", data.get("title", ""))[:200],
                            "timestamp": data.get("created_at", ""),
                            "confidence": data.get("confidence", 0.7)
                        })
                    except Exception:
                        continue
            
            # Also check internal updates
            internal_dir = self.oracle_export_path / "internal_updates"
            if internal_dir.exists():
                files = sorted(
                    internal_dir.glob("*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True
                )
                
                for json_file in files[:limit]:
                    try:
                        with open(json_file, "r") as f:
                            data = json.load(f)
                        
                        learnings.append({
                            "source": "internal",
                            "insight": data.get("content", data.get("title", ""))[:200],
                            "timestamp": data.get("created_at", ""),
                            "confidence": data.get("confidence", 0.7)
                        })
                    except Exception:
                        continue
            
            # Sort by timestamp and limit
            learnings.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Recent learnings retrieval failed: {e}")
        
        return learnings[:limit]


# =============================================================================
# HOOK FUNCTIONS - Connect other systems to Oracle Hub
# =============================================================================

def hook_librarian_to_oracle(librarian, hub: UnifiedOracleHub):
    """Add callback to Librarian that sends all ingestions to Oracle."""
    if hasattr(librarian, 'add_listener'):
        async def on_ingest(record):
            await hub.ingest_from_librarian(
                ingestion_id=record.get("ingestion_id", "unknown"),
                filename=record.get("filename", "unknown"),
                content_type=record.get("content_type", "unknown"),
                content_summary=record.get("content_summary", ""),
                file_path=record.get("file_path", "")
            )
        librarian.add_listener(on_ingest)
        logger.info("[ORACLE-HUB] Hooked Librarian → Oracle")


def hook_sandbox_to_oracle(sandbox, hub: UnifiedOracleHub):
    """Add callback to Sandbox that sends all experiment results to Oracle."""
    if hasattr(sandbox, 'add_experiment_callback'):
        async def on_experiment(result):
            await hub.ingest_from_sandbox(
                experiment_id=result.get("experiment_id", "unknown"),
                experiment_name=result.get("name", "Unknown"),
                results=result.get("results", {}),
                lessons_learned=result.get("lessons_learned", []),
                success=result.get("success", False)
            )
        sandbox.add_experiment_callback(on_experiment)
        logger.info("[ORACLE-HUB] Hooked Sandbox → Oracle")


def hook_learning_memory_to_oracle(learning_memory, hub: UnifiedOracleHub):
    """Add callback to Learning Memory that syncs training to Oracle."""
    if hasattr(learning_memory, 'add_training_callback'):
        async def on_training(data):
            await hub.ingest_from_learning_memory(
                training_type=data.get("type", "general"),
                data=data,
                trust_score=data.get("trust_score", 0.7)
            )
        learning_memory.add_training_callback(on_training)
        logger.info("[ORACLE-HUB] Hooked Learning Memory → Oracle")


def hook_self_healing_to_oracle(healer, hub: UnifiedOracleHub):
    """Add callback to Self-Healing that sends all fixes to Oracle."""
    if hasattr(healer, 'add_fix_callback'):
        async def on_fix(result):
            await hub.ingest_from_self_healing(
                error_type=result.get("error_type", "unknown"),
                error_message=result.get("error_message", ""),
                fix_applied=result.get("fix_applied", ""),
                success=result.get("success", False),
                affected_files=result.get("affected_files", [])
            )
        healer.add_fix_callback(on_fix)
        logger.info("[ORACLE-HUB] Hooked Self-Healing → Oracle")


# =============================================================================
# SINGLETON
# =============================================================================

_oracle_hub_instance: Optional[UnifiedOracleHub] = None


def get_oracle_hub(
    session=None,
    genesis_service=None,
    oracle_core=None,
    librarian_pipeline=None,
    learning_memory=None,
    sandbox_lab=None
) -> UnifiedOracleHub:
    """Get singleton Oracle Hub instance."""
    global _oracle_hub_instance
    
    if _oracle_hub_instance is None:
        _oracle_hub_instance = UnifiedOracleHub(
            session=session,
            genesis_service=genesis_service,
            oracle_core=oracle_core,
            librarian_pipeline=librarian_pipeline,
            learning_memory=learning_memory,
            sandbox_lab=sandbox_lab
        )
    
    return _oracle_hub_instance


def initialize_oracle_hub_with_hooks() -> UnifiedOracleHub:
    """Initialize Oracle Hub and connect all available systems."""
    from pathlib import Path
    
    # Get dependencies
    session = None
    genesis_service = None
    oracle_core = None
    librarian = None
    learning_memory = None
    sandbox_lab = None
    
    try:
        from database.session import SessionLocal
        session = SessionLocal()
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Session unavailable: {e}")
    
    try:
        from models.genesis_key_models import get_genesis_key_service
        genesis_service = get_genesis_key_service()
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Genesis service unavailable: {e}")
    
    try:
        from oracle_intelligence.oracle_core import OracleCore
        oracle_core = OracleCore(
            session=session,
            genesis_service=genesis_service
        )
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Oracle Core unavailable: {e}")
    
    try:
        from genesis.librarian_pipeline import LibrarianPipeline
        librarian = LibrarianPipeline()
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Librarian unavailable: {e}")
    
    try:
        from cognitive.learning_memory import get_learning_memory
        learning_memory = get_learning_memory()
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Learning Memory unavailable: {e}")
    
    try:
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        sandbox_lab = get_sandbox_lab()
    except Exception as e:
        logger.warning(f"[ORACLE-HUB] Sandbox Lab unavailable: {e}")
    
    # Create hub
    hub = get_oracle_hub(
        session=session,
        genesis_service=genesis_service,
        oracle_core=oracle_core,
        librarian_pipeline=librarian,
        learning_memory=learning_memory,
        sandbox_lab=sandbox_lab
    )
    
    # Hook all systems
    if librarian:
        hook_librarian_to_oracle(librarian, hub)
    if sandbox_lab:
        hook_sandbox_to_oracle(sandbox_lab, hub)
    if learning_memory:
        hook_learning_memory_to_oracle(learning_memory, hub)
    
    logger.info("[ORACLE-HUB] Initialized with all available hooks")
    
    return hub
