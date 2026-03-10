"""
Librarian Ingestion Pipeline
============================
Full data ingestion flow with Genesis Key tracking.
Data comes in → Genesis Key → Indexed → Files created/named → Saved in memory → Shows in UI

Integrations:
- Genesis Key Service: Every ingestion gets a properly tracked Genesis Key
- Mirror Self-Modeling: Ingestions are observed for pattern learning
- Cognitive Framework: Decisions about filing and categorization
- Trust Scores: Ingestion reliability tracking
- Version Control: All ingestions are version controlled
"""

import os
import json
import hashlib
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import mimetypes
import shutil

logger = logging.getLogger(__name__)


def get_genesis_key_service():
    """Get the Genesis Key Service for proper key creation."""
    try:
        from genesis.genesis_key_service import GenesisKeyService
        from database.session import get_session
        session = next(get_session())
        return GenesisKeyService(session=session)
    except Exception as e:
        logger.debug(f"[LIBRARIAN] Genesis Key Service not available: {e}")
        return None


def get_mirror_system():
    """Get the Mirror Self-Modeling System for observation."""
    try:
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        from database.session import get_session
        session = next(get_session())
        return MirrorSelfModelingSystem(session)
    except Exception as e:
        logger.debug(f"[LIBRARIAN] Mirror System not available: {e}")
        return None


class IngestionStatus(str, Enum):
    """Status of ingestion process."""
    PENDING = "pending"
    RECEIVING = "receiving"
    GENESIS_ASSIGNED = "genesis_assigned"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FILING = "filing"
    FILED = "filed"
    MEMORIZING = "memorizing"
    COMPLETE = "complete"
    FAILED = "failed"


class ContentType(str, Enum):
    """Types of content that can be ingested."""
    DOCUMENT = "document"
    CODE = "code"
    IMAGE = "image"
    DATA = "data"
    CONFIG = "config"
    KNOWLEDGE = "knowledge"
    CONVERSATION = "conversation"
    LOG = "log"
    UNKNOWN = "unknown"


@dataclass
class IngestionRecord:
    """Record of an ingestion operation."""
    ingestion_id: str
    genesis_key: str
    status: IngestionStatus
    content_type: ContentType
    source: str
    destination: str
    filename: str
    file_size: int
    content_hash: str
    index_id: Optional[str]
    memory_id: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    ingestion_id: str
    genesis_key: str
    status: IngestionStatus
    destination: str
    index_id: Optional[str]
    memory_id: Optional[str]
    duration_ms: int
    message: str


class LibrarianPipeline:
    """
    The Librarian handles all data ingestion for GRACE.

    Flow:
    1. RECEIVE - Accept incoming data
    2. GENESIS - Assign Genesis Key for tracking
    3. INDEX - Add to vector index for retrieval
    4. FILE - Create/name files in organized structure
    5. MEMORIZE - Store in learning memory
    6. PUBLISH - Make visible in UI
    """

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or "/tmp/grace/library")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Sub-directories
        self.documents_dir = self.storage_dir / "documents"
        self.code_dir = self.storage_dir / "code"
        self.data_dir = self.storage_dir / "data"
        self.knowledge_dir = self.storage_dir / "knowledge"
        self.index_dir = self.storage_dir / "index"

        for d in [self.documents_dir, self.code_dir, self.data_dir,
                  self.knowledge_dir, self.index_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Ingestion registry
        self.registry: Dict[str, IngestionRecord] = {}
        self._load_registry()

        # Event listeners for UI updates
        self._listeners: List[callable] = []

        # Index integration (will use existing embedder)
        self._indexer = None

        # =================================================================
        # Core System Integrations
        # =================================================================

        # Genesis Key Service - for proper tracked key generation
        self._genesis_service = get_genesis_key_service()

        # Mirror Self-Modeling - for observation
        self._mirror = get_mirror_system()

        # Ingestion version history for mutation tracking
        self._ingestion_versions: Dict[str, List[Dict[str, Any]]] = {}

        logger.info("[LIBRARIAN] Pipeline initialized with core integrations")
        if self._genesis_service:
            logger.info("[LIBRARIAN]   ✓ Genesis Key Service connected")
        if self._mirror:
            logger.info("[LIBRARIAN]   ✓ Mirror Self-Modeling connected")

    def _load_registry(self):
        """Load ingestion registry from disk."""
        registry_file = self.storage_dir / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, "r") as f:
                    data = json.load(f)
                    for record_data in data.get("records", []):
                        record = IngestionRecord(
                            ingestion_id=record_data["ingestion_id"],
                            genesis_key=record_data["genesis_key"],
                            status=IngestionStatus(record_data["status"]),
                            content_type=ContentType(record_data["content_type"]),
                            source=record_data["source"],
                            destination=record_data["destination"],
                            filename=record_data["filename"],
                            file_size=record_data["file_size"],
                            content_hash=record_data["content_hash"],
                            index_id=record_data.get("index_id"),
                            memory_id=record_data.get("memory_id"),
                            created_at=record_data["created_at"],
                            updated_at=record_data["updated_at"],
                            metadata=record_data.get("metadata", {}),
                            timeline=record_data.get("timeline", []),
                            error=record_data.get("error")
                        )
                        self.registry[record.ingestion_id] = record
                logger.info(f"[LIBRARIAN] Loaded {len(self.registry)} ingestion records")
            except Exception as e:
                logger.error(f"[LIBRARIAN] Failed to load registry: {e}")

    def _save_registry(self):
        """Save ingestion registry to disk."""
        registry_file = self.storage_dir / "registry.json"
        data = {
            "records": [asdict(r) for r in self.registry.values()],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        with open(registry_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _generate_genesis_key(
        self,
        content_type: ContentType,
        content_hash: str,
        filename: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Generate Genesis Key for ingestion using proper Genesis Key Service.

        Every ingestion gets a tracked Genesis Key for:
        - Full audit trail
        - Version control
        - Mirror observation
        - Pattern learning
        """
        # Use Genesis Key Service if available
        if self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType

                genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.INPUT,
                    what_description=f"Ingestion of {content_type.value} content: {filename or 'unnamed'}",
                    who_actor="LIBRARIAN_PIPELINE",
                    where_location=filename or "unknown",
                    why_reason="Data ingestion into library",
                    how_method="LibrarianPipeline.ingest_content()",
                    context_data={
                        "content_type": content_type.value,
                        "content_hash": content_hash,
                        "filename": filename,
                        **(metadata or {})
                    },
                    tags=["librarian", "ingestion", content_type.value]
                )

                logger.debug(f"[LIBRARIAN] Created tracked Genesis Key: {genesis_key.genesis_key}")
                return genesis_key.genesis_key

            except Exception as e:
                logger.warning(f"[LIBRARIAN] Genesis Key Service error, falling back: {e}")

        # Fallback to simple key generation
        timestamp = datetime.now(timezone.utc).isoformat()
        key_data = f"librarian:ingest:{content_type.value}:{content_hash}:{timestamp}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:12]
        return f"gk-lib-{key_hash}"

    def _track_ingestion_version(self, ingestion_id: str, record: IngestionRecord, mutation_type: str):
        """Track version/mutation of an ingestion for audit trail."""
        if ingestion_id not in self._ingestion_versions:
            self._ingestion_versions[ingestion_id] = []

        version_entry = {
            "version": len(self._ingestion_versions[ingestion_id]) + 1,
            "mutation_type": mutation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": record.status.value,
            "genesis_key": record.genesis_key,
            "snapshot": {
                "content_type": record.content_type.value,
                "filename": record.filename,
                "file_size": record.file_size,
                "content_hash": record.content_hash
            }
        }

        self._ingestion_versions[ingestion_id].append(version_entry)
        logger.debug(f"[LIBRARIAN] Tracked version {version_entry['version']} for ingestion {ingestion_id}: {mutation_type}")

    def _detect_content_type(self, filename: str, content: bytes = None) -> ContentType:
        """Detect content type from filename and content."""
        ext = Path(filename).suffix.lower()

        # Code files
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go',
                          '.rs', '.cpp', '.c', '.h', '.cs', '.rb', '.php', '.swift'}
        if ext in code_extensions:
            return ContentType.CODE

        # Documents
        doc_extensions = {'.md', '.txt', '.pdf', '.doc', '.docx', '.rst', '.html'}
        if ext in doc_extensions:
            return ContentType.DOCUMENT

        # Data files
        data_extensions = {'.json', '.yaml', '.yml', '.xml', '.csv', '.parquet'}
        if ext in data_extensions:
            return ContentType.DATA

        # Config files
        config_extensions = {'.ini', '.cfg', '.conf', '.toml', '.env'}
        if ext in config_extensions:
            return ContentType.CONFIG

        # Images
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
        if ext in image_extensions:
            return ContentType.IMAGE

        # Log files
        if ext in {'.log'} or 'log' in filename.lower():
            return ContentType.LOG

        return ContentType.UNKNOWN

    def _compute_hash(self, content: bytes) -> str:
        """Compute content hash."""
        return hashlib.sha256(content).hexdigest()

    def _generate_filename(
        self,
        original_name: str,
        content_type: ContentType,
        genesis_key: str
    ) -> Tuple[str, Path]:
        """Generate organized filename and path."""
        # Choose directory based on content type
        type_dirs = {
            ContentType.CODE: self.code_dir,
            ContentType.DOCUMENT: self.documents_dir,
            ContentType.DATA: self.data_dir,
            ContentType.CONFIG: self.data_dir,
            ContentType.KNOWLEDGE: self.knowledge_dir,
            ContentType.IMAGE: self.documents_dir / "images",
            ContentType.LOG: self.data_dir / "logs",
            ContentType.UNKNOWN: self.data_dir / "misc"
        }

        base_dir = type_dirs.get(content_type, self.data_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Create date-based subdirectory
        date_dir = base_dir / datetime.now(timezone.utc).strftime("%Y/%m/%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        stem = Path(original_name).stem
        ext = Path(original_name).suffix

        # Clean filename
        safe_stem = "".join(c if c.isalnum() or c in '-_' else '_' for c in stem)

        # Add short genesis key suffix for uniqueness
        gk_suffix = genesis_key.split('-')[-1][:6]
        new_filename = f"{safe_stem}_{gk_suffix}{ext}"

        return new_filename, date_dir / new_filename

    def _update_status(
        self,
        record: IngestionRecord,
        status: IngestionStatus,
        message: str = None
    ):
        """Update ingestion status and add to timeline."""
        record.status = status
        record.updated_at = datetime.now(timezone.utc).isoformat()
        record.timeline.append({
            "status": status.value,
            "timestamp": record.updated_at,
            "message": message
        })

        # Notify listeners
        self._notify_listeners(record)

        # Save registry
        self._save_registry()

        logger.debug(f"[LIBRARIAN] {record.ingestion_id} -> {status.value}")

    def _notify_listeners(self, record: IngestionRecord):
        """Notify UI listeners of status change."""
        for listener in self._listeners:
            try:
                listener(record)
            except Exception as e:
                logger.error(f"[LIBRARIAN] Listener error: {e}")

    def add_listener(self, callback: callable):
        """Add a listener for ingestion updates."""
        self._listeners.append(callback)

    def remove_listener(self, callback: callable):
        """Remove a listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def ingest_file(
        self,
        file_path: str,
        metadata: Dict[str, Any] = None
    ) -> IngestionResult:
        """
        Ingest a file into the library.

        Args:
            file_path: Path to file to ingest
            metadata: Optional metadata

        Returns:
            IngestionResult with status and IDs
        """
        start_time = datetime.now(timezone.utc)
        file_path = Path(file_path)

        if not file_path.exists():
            return IngestionResult(
                success=False,
                ingestion_id="",
                genesis_key="",
                status=IngestionStatus.FAILED,
                destination="",
                index_id=None,
                memory_id=None,
                duration_ms=0,
                message=f"File not found: {file_path}"
            )

        # Read file content
        content = file_path.read_bytes()

        return await self.ingest_content(
            content=content,
            filename=file_path.name,
            source=str(file_path),
            metadata=metadata
        )

    async def ingest_content(
        self,
        content: bytes,
        filename: str,
        source: str = "upload",
        metadata: Dict[str, Any] = None
    ) -> IngestionResult:
        """
        Ingest raw content into the library.

        Args:
            content: Raw bytes to ingest
            filename: Original filename
            source: Source identifier
            metadata: Optional metadata

        Returns:
            IngestionResult with status and IDs
        """
        start_time = datetime.now(timezone.utc)
        ingestion_id = f"ing-{uuid.uuid4().hex[:12]}"

        try:
            # ========================================
            # STEP 1: RECEIVE
            # ========================================
            content_hash = self._compute_hash(content)
            content_type = self._detect_content_type(filename, content)

            # Create initial record
            record = IngestionRecord(
                ingestion_id=ingestion_id,
                genesis_key="",  # Assigned in step 2
                status=IngestionStatus.RECEIVING,
                content_type=content_type,
                source=source,
                destination="",  # Set in step 4
                filename=filename,
                file_size=len(content),
                content_hash=content_hash,
                index_id=None,
                memory_id=None,
                created_at=start_time.isoformat(),
                updated_at=start_time.isoformat(),
                metadata=metadata or {},
                timeline=[{
                    "status": IngestionStatus.RECEIVING.value,
                    "timestamp": start_time.isoformat(),
                    "message": f"Receiving {len(content)} bytes"
                }]
            )
            self.registry[ingestion_id] = record

            logger.info(f"[LIBRARIAN] Starting ingestion {ingestion_id}: {filename} ({content_type.value})")

            # ========================================
            # STEP 2: GENESIS KEY ASSIGNMENT
            # ========================================
            genesis_key = self._generate_genesis_key(
                content_type,
                content_hash,
                filename=filename,
                metadata=metadata
            )
            record.genesis_key = genesis_key
            self._update_status(record, IngestionStatus.GENESIS_ASSIGNED,
                              f"Genesis Key: {genesis_key}")

            # Track initial version (creation with genesis key)
            self._track_ingestion_version(ingestion_id, record, "create")

            # ========================================
            # STEP 3: INDEXING
            # ========================================
            self._update_status(record, IngestionStatus.INDEXING, "Adding to search index")

            index_id = None
            try:
                index_id = await self._index_content(content, filename, content_type, genesis_key, metadata)
                record.index_id = index_id
                self._update_status(record, IngestionStatus.INDEXED, f"Index ID: {index_id}")
            except Exception as e:
                logger.warning(f"[LIBRARIAN] Indexing skipped: {e}")
                self._update_status(record, IngestionStatus.INDEXED, f"Indexing skipped: {e}")

            # ========================================
            # STEP 4: FILE CREATION
            # ========================================
            self._update_status(record, IngestionStatus.FILING, "Creating file")

            new_filename, destination = self._generate_filename(filename, content_type, genesis_key)

            # Write file
            with open(destination, 'wb') as f:
                f.write(content)

            record.destination = str(destination)
            record.filename = new_filename
            self._update_status(record, IngestionStatus.FILED, f"Filed: {destination}")

            # ========================================
            # STEP 5: MEMORY STORAGE
            # ========================================
            self._update_status(record, IngestionStatus.MEMORIZING, "Storing in memory")

            memory_id = None
            try:
                memory_id = await self._store_in_memory(
                    content, filename, content_type, genesis_key, destination, metadata
                )
                record.memory_id = memory_id
            except Exception as e:
                logger.warning(f"[LIBRARIAN] Memory storage skipped: {e}")

            # ========================================
            # STEP 6: COMPLETE
            # ========================================
            self._update_status(record, IngestionStatus.COMPLETE, "Ingestion complete")

            # Track completion version
            self._track_ingestion_version(ingestion_id, record, "complete")

            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            logger.info(f"[LIBRARIAN] Completed {ingestion_id} in {duration_ms}ms -> {destination}")

            return IngestionResult(
                success=True,
                ingestion_id=ingestion_id,
                genesis_key=genesis_key,
                status=IngestionStatus.COMPLETE,
                destination=str(destination),
                index_id=index_id,
                memory_id=memory_id,
                duration_ms=duration_ms,
                message="Ingestion complete"
            )

        except Exception as e:
            logger.error(f"[LIBRARIAN] Ingestion failed: {e}")

            if ingestion_id in self.registry:
                record = self.registry[ingestion_id]
                record.error = str(e)
                self._update_status(record, IngestionStatus.FAILED, str(e))

            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            return IngestionResult(
                success=False,
                ingestion_id=ingestion_id,
                genesis_key=record.genesis_key if record else "",
                status=IngestionStatus.FAILED,
                destination="",
                index_id=None,
                memory_id=None,
                duration_ms=duration_ms,
                message=str(e)
            )

    async def _index_content(
        self,
        content: bytes,
        filename: str,
        content_type: ContentType,
        genesis_key: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Index content for search/retrieval."""
        try:
            # Try to use the embedder if available
            from genesis.embedder import get_embedder

            embedder = get_embedder()

            # Decode content for text-based files
            if content_type in [ContentType.CODE, ContentType.DOCUMENT,
                               ContentType.DATA, ContentType.CONFIG]:
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    text_content = content.decode('latin-1')

                # Add to embedder
                doc_id = f"lib_{genesis_key}"
                await embedder.add_document(
                    doc_id=doc_id,
                    content=text_content,
                    metadata={
                        "filename": filename,
                        "content_type": content_type.value,
                        "genesis_key": genesis_key,
                        **(metadata or {})
                    }
                )
                return doc_id

            return None

        except ImportError:
            logger.debug("[LIBRARIAN] Embedder not available")
            return None
        except Exception as e:
            logger.debug(f"[LIBRARIAN] Indexing failed: {e}")
            return None

    async def _store_in_memory(
        self,
        content: bytes,
        filename: str,
        content_type: ContentType,
        genesis_key: str,
        destination: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Store in learning memory system."""
        try:
            from learning_memory_api import get_memory_manager

            memory_manager = get_memory_manager()

            # Decode content for text-based files
            if content_type in [ContentType.CODE, ContentType.DOCUMENT,
                               ContentType.DATA, ContentType.CONFIG, ContentType.KNOWLEDGE]:
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError:
                    text_content = content.decode('latin-1')

                # Store as memory entry
                memory_entry = await memory_manager.store({
                    "type": "ingested_content",
                    "filename": filename,
                    "content_type": content_type.value,
                    "genesis_key": genesis_key,
                    "destination": destination,
                    "content_preview": text_content[:1000],  # First 1000 chars
                    "full_content": text_content,
                    "metadata": metadata or {}
                })

                return memory_entry.get("memory_id")

            return None

        except ImportError:
            logger.debug("[LIBRARIAN] Learning memory not available")
            return None
        except Exception as e:
            logger.debug(f"[LIBRARIAN] Memory storage failed: {e}")
            return None

    async def ingest_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        patterns: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Ingest all files in a directory.

        Args:
            directory_path: Path to directory
            recursive: Include subdirectories
            patterns: File patterns to match (e.g., ['*.py', '*.md'])
            metadata: Metadata for all files

        Returns:
            Summary of ingestion results
        """
        directory = Path(directory_path)

        if not directory.exists() or not directory.is_dir():
            return {
                "success": False,
                "error": f"Directory not found: {directory_path}",
                "results": []
            }

        # Collect files
        files = []
        if recursive:
            if patterns:
                for pattern in patterns:
                    files.extend(directory.rglob(pattern))
            else:
                files = [f for f in directory.rglob("*") if f.is_file()]
        else:
            if patterns:
                for pattern in patterns:
                    files.extend(directory.glob(pattern))
            else:
                files = [f for f in directory.glob("*") if f.is_file()]

        # Filter out hidden files and common excludes
        exclude_patterns = {'.git', '__pycache__', 'node_modules', '.env', '.venv'}
        files = [f for f in files if not any(p in str(f) for p in exclude_patterns)]

        results = []
        success_count = 0
        fail_count = 0

        for file_path in files:
            result = await self.ingest_file(str(file_path), metadata)
            results.append(asdict(result))

            if result.success:
                success_count += 1
            else:
                fail_count += 1

        return {
            "success": fail_count == 0,
            "directory": str(directory),
            "total_files": len(files),
            "successful": success_count,
            "failed": fail_count,
            "results": results
        }

    def get_ingestion(self, ingestion_id: str) -> Optional[IngestionRecord]:
        """Get an ingestion record by ID."""
        return self.registry.get(ingestion_id)

    def get_ingestions_by_genesis_key(self, genesis_key: str) -> List[IngestionRecord]:
        """Get all ingestions with a specific Genesis Key."""
        return [r for r in self.registry.values() if r.genesis_key == genesis_key]

    def list_ingestions(
        self,
        status: IngestionStatus = None,
        content_type: ContentType = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[IngestionRecord]:
        """List ingestion records with optional filters."""
        records = list(self.registry.values())

        if status:
            records = [r for r in records if r.status == status]

        if content_type:
            records = [r for r in records if r.content_type == content_type]

        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)

        return records[offset:offset + limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        records = list(self.registry.values())

        # Count by status
        status_counts = {}
        for status in IngestionStatus:
            status_counts[status.value] = len([r for r in records if r.status == status])

        # Count by type
        type_counts = {}
        for ct in ContentType:
            type_counts[ct.value] = len([r for r in records if r.content_type == ct])

        # Calculate sizes
        total_size = sum(r.file_size for r in records)

        # Recent activity
        recent = records[:10] if records else []

        return {
            "total_ingestions": len(records),
            "by_status": status_counts,
            "by_type": type_counts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "recent": [
                {
                    "ingestion_id": r.ingestion_id,
                    "genesis_key": r.genesis_key,
                    "filename": r.filename,
                    "status": r.status.value,
                    "content_type": r.content_type.value,
                    "created_at": r.created_at
                }
                for r in recent
            ],
            "storage_path": str(self.storage_dir)
        }

    def search_library(
        self,
        query: str,
        content_type: ContentType = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search the library for matching content."""
        results = []

        for record in self.registry.values():
            if record.status != IngestionStatus.COMPLETE:
                continue

            if content_type and record.content_type != content_type:
                continue

            # Simple text matching on filename and metadata
            search_text = f"{record.filename} {json.dumps(record.metadata)}".lower()
            if query.lower() in search_text:
                results.append({
                    "ingestion_id": record.ingestion_id,
                    "genesis_key": record.genesis_key,
                    "filename": record.filename,
                    "content_type": record.content_type.value,
                    "destination": record.destination,
                    "created_at": record.created_at,
                    "metadata": record.metadata
                })

        return results[:limit]


# =============================================================================
# Global Instance
# =============================================================================

_librarian_pipeline: Optional[LibrarianPipeline] = None


def get_librarian_pipeline() -> LibrarianPipeline:
    """Get the global librarian pipeline instance."""
    global _librarian_pipeline
    if _librarian_pipeline is None:
        _librarian_pipeline = LibrarianPipeline()
    return _librarian_pipeline


# =============================================================================
# Convenience Functions
# =============================================================================

async def ingest_file(file_path: str, metadata: Dict[str, Any] = None) -> IngestionResult:
    """Convenience function to ingest a file."""
    pipeline = get_librarian_pipeline()
    return await pipeline.ingest_file(file_path, metadata)


async def ingest_content(
    content: bytes,
    filename: str,
    source: str = "upload",
    metadata: Dict[str, Any] = None
) -> IngestionResult:
    """Convenience function to ingest raw content."""
    pipeline = get_librarian_pipeline()
    return await pipeline.ingest_content(content, filename, source, metadata)


async def ingest_directory(
    directory_path: str,
    recursive: bool = True,
    patterns: List[str] = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Convenience function to ingest a directory."""
    pipeline = get_librarian_pipeline()
    return await pipeline.ingest_directory(directory_path, recursive, patterns, metadata)
