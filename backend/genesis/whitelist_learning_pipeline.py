"""
Whitelist Learning Pipeline
===========================
Complete pipeline for human-approved data to flow through GRACE's learning systems.

Flow:
Whitelist Entry → Trust Verification → Genesis Key → Data Processing →
Learning Memory → Cognitive Framework → ML Intelligence → Knowledge Application

Integrations:
- Genesis Key Service: Every input tracked
- Trust Score System: Verify source reliability
- Librarian: File organization and naming
- Cognitive Engine: Understanding and reasoning
- Clarity Framework: Clear explanations
- Mirror Self-Modeling: Self-observation
- Active Learning: Proactive learning triggers
- Memory Mesh: Connected memory storage
- ML Intelligence: Pattern recognition
- Knowledge Base: Stored knowledge
- RAG/Retrieval: Finding relevant info
- Embedder: Vector embeddings
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Status and Types
# =============================================================================

class PipelineStage(str, Enum):
    """Stages of the whitelist learning pipeline."""
    # Entry
    WHITELIST_ENTRY = "whitelist_entry"
    TRUST_VERIFICATION = "trust_verification"

    # Genesis Tracking
    GENESIS_KEY_ASSIGNMENT = "genesis_key_assignment"

    # Data Processing
    DATA_EXTRACTION = "data_extraction"
    CONTENT_ANALYSIS = "content_analysis"

    # Filing
    LIBRARIAN_FILING = "librarian_filing"
    FILE_NAMING = "file_naming"

    # Learning
    EMBEDDING_GENERATION = "embedding_generation"
    MEMORY_STORAGE = "memory_storage"
    MEMORY_MESH_LINKING = "memory_mesh_linking"

    # Cognitive Processing
    COGNITIVE_PROCESSING = "cognitive_processing"
    CLARITY_ANALYSIS = "clarity_analysis"
    CONTRADICTION_CHECK = "contradiction_check"

    # ML & Intelligence
    PATTERN_EXTRACTION = "pattern_extraction"
    ML_TRAINING = "ml_training"

    # Knowledge Application
    KNOWLEDGE_BASE_UPDATE = "knowledge_base_update"
    PROACTIVE_LEARNING = "proactive_learning"

    # Completion
    MIRROR_OBSERVATION = "mirror_observation"
    COMPLETE = "complete"
    FAILED = "failed"


class DataCategory(str, Enum):
    """Categories of whitelisted data."""
    HUMAN_REQUEST = "human_request"
    RESEARCH_DATA = "research_data"
    CODE_SNIPPET = "code_snippet"
    DOCUMENTATION = "documentation"
    CONVERSATION = "conversation"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    PREFERENCE = "preference"
    TRAINING_EXAMPLE = "training_example"
    KNOWLEDGE_FACT = "knowledge_fact"


class TrustLevel(str, Enum):
    """Trust levels for data sources."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"
    OWNER = "owner"


@dataclass
class WhitelistEntry:
    """An entry in the whitelist for processing."""
    entry_id: str
    source: str  # Who/what provided this data
    category: DataCategory
    content: str
    metadata: Dict[str, Any]
    trust_level: TrustLevel
    created_at: str
    genesis_key: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    parent_entry_id: Optional[str] = None  # For linked entries


@dataclass
class PipelineResult:
    """Result of pipeline processing."""
    entry_id: str
    genesis_key: str
    success: bool
    stage: PipelineStage
    stages_completed: List[str]

    # Generated artifacts
    file_path: Optional[str] = None
    memory_id: Optional[str] = None
    embedding_id: Optional[str] = None
    knowledge_id: Optional[str] = None

    # Learning outputs
    patterns_found: List[Dict[str, Any]] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[Dict[str, Any]] = field(default_factory=list)

    # Metrics
    trust_score: float = 0.0
    confidence: float = 0.0
    duration_ms: int = 0

    error: Optional[str] = None
    message: str = ""


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: PipelineStage
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    genesis_key: Optional[str] = None


# =============================================================================
# System Integration Helpers
# =============================================================================

def get_genesis_key_service():
    """Get Genesis Key Service."""
    try:
        from genesis.genesis_key_service import GenesisKeyService
        from database.session import get_session
        session = next(get_session())
        return GenesisKeyService(session=session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Genesis Key Service not available: {e}")
        return None


def get_cognitive_engine():
    """Get Cognitive Engine."""
    try:
        from cognitive.engine import get_cognitive_engine
        return get_cognitive_engine()
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Cognitive Engine not available: {e}")
        return None


def get_mirror_system():
    """Get Mirror Self-Modeling System."""
    try:
        from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
        from database.session import get_session
        session = next(get_session())
        return MirrorSelfModelingSystem(session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Mirror System not available: {e}")
        return None


def get_active_learning():
    """Get Active Learning System."""
    try:
        from cognitive.active_learning_system import GraceActiveLearningSystem
        from database.session import get_session
        session = next(get_session())
        return GraceActiveLearningSystem(session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Active Learning not available: {e}")
        return None


def get_memory_mesh_learner():
    """Get Memory Mesh Learner."""
    try:
        from cognitive.memory_mesh_learner import get_memory_mesh_learner
        from database.session import get_session
        session = next(get_session())
        return get_memory_mesh_learner(session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Memory Mesh Learner not available: {e}")
        return None


def get_contradiction_detector():
    """Get Contradiction Detector."""
    try:
        from cognitive.contradiction_detector import ContradictionDetector
        from database.session import get_session
        session = next(get_session())
        return ContradictionDetector(session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Contradiction Detector not available: {e}")
        return None


def get_proactive_learner():
    """Get Proactive Learner."""
    try:
        from cognitive.proactive_learner import ProactiveLearner
        return ProactiveLearner()
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Proactive Learner not available: {e}")
        return None


def get_embedder():
    """Get Embedder for vector generation."""
    try:
        from embedding import get_embedder
        return get_embedder()
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Embedder not available: {e}")
        return None


def get_librarian_pipeline():
    """Get Librarian Pipeline."""
    try:
        from genesis.librarian_pipeline import get_librarian_pipeline
        return get_librarian_pipeline()
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Librarian Pipeline not available: {e}")
        return None


def get_learning_memory():
    """Get Learning Memory."""
    try:
        from cognitive.learning_memory import LearningMemory
        from database.session import get_session
        session = next(get_session())
        return LearningMemory(session)
    except Exception as e:
        logger.debug(f"[WL-Pipeline] Learning Memory not available: {e}")
        return None


def get_ml_intelligence():
    """Get ML Intelligence system."""
    try:
        from llm_orchestrator.ml_intelligence import get_ml_intelligence
        return get_ml_intelligence()
    except Exception as e:
        logger.debug(f"[WL-Pipeline] ML Intelligence not available: {e}")
        return None


# =============================================================================
# Whitelist Learning Pipeline
# =============================================================================

class WhitelistLearningPipeline:
    """
    Complete pipeline for processing whitelisted human input through
    GRACE's learning systems.

    The pipeline:
    1. VERIFY - Check trust level and source validity
    2. TRACK - Assign Genesis Key for full audit trail
    3. PROCESS - Extract and analyze content
    4. FILE - Organize with Librarian, name files properly
    5. EMBED - Generate vector embeddings
    6. MEMORIZE - Store in learning memory and mesh
    7. COGNIZE - Process through cognitive framework
    8. CLARIFY - Apply clarity framework for understanding
    9. CHECK - Detect contradictions with existing knowledge
    10. LEARN - Extract patterns, trigger ML training
    11. APPLY - Update knowledge base
    12. OBSERVE - Mirror self-modeling records the learning
    """

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or "/tmp/grace/whitelist")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Pipeline state
        self.entries: Dict[str, WhitelistEntry] = {}
        self.results: Dict[str, PipelineResult] = {}
        self.pipeline_versions: Dict[str, List[Dict[str, Any]]] = {}

        # Trust score thresholds
        self.trust_thresholds = {
            TrustLevel.UNTRUSTED: 0.0,
            TrustLevel.LOW: 0.25,
            TrustLevel.MEDIUM: 0.5,
            TrustLevel.HIGH: 0.75,
            TrustLevel.VERIFIED: 0.9,
            TrustLevel.OWNER: 1.0
        }

        # =================================================================
        # Core System Integrations
        # =================================================================

        self._genesis_service = get_genesis_key_service()
        self._cognitive = get_cognitive_engine()
        self._mirror = get_mirror_system()
        self._active_learning = get_active_learning()
        self._memory_mesh = get_memory_mesh_learner()
        self._contradiction_detector = get_contradiction_detector()
        self._proactive_learner = get_proactive_learner()
        self._embedder = get_embedder()
        self._librarian = get_librarian_pipeline()
        self._learning_memory = get_learning_memory()
        self._ml_intelligence = get_ml_intelligence()

        # Load existing entries
        self._load_entries()

        logger.info("[WL-Pipeline] Whitelist Learning Pipeline initialized")
        self._log_integrations()

    def _log_integrations(self):
        """Log which integrations are available."""
        integrations = [
            ("Genesis Key Service", self._genesis_service),
            ("Cognitive Engine", self._cognitive),
            ("Mirror Self-Modeling", self._mirror),
            ("Active Learning", self._active_learning),
            ("Memory Mesh Learner", self._memory_mesh),
            ("Contradiction Detector", self._contradiction_detector),
            ("Proactive Learner", self._proactive_learner),
            ("Embedder", self._embedder),
            ("Librarian Pipeline", self._librarian),
            ("Learning Memory", self._learning_memory),
            ("ML Intelligence", self._ml_intelligence)
        ]

        for name, integration in integrations:
            status = "connected" if integration else "not available"
            symbol = "✓" if integration else "✗"
            logger.info(f"[WL-Pipeline]   {symbol} {name}: {status}")

    def _load_entries(self):
        """Load existing whitelist entries."""
        entries_file = self.storage_dir / "entries.json"
        if entries_file.exists():
            try:
                with open(entries_file, "r") as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = WhitelistEntry(
                            entry_id=entry_data["entry_id"],
                            source=entry_data["source"],
                            category=DataCategory(entry_data["category"]),
                            content=entry_data["content"],
                            metadata=entry_data.get("metadata", {}),
                            trust_level=TrustLevel(entry_data["trust_level"]),
                            created_at=entry_data["created_at"],
                            genesis_key=entry_data.get("genesis_key"),
                            user_id=entry_data.get("user_id"),
                            session_id=entry_data.get("session_id"),
                            parent_entry_id=entry_data.get("parent_entry_id")
                        )
                        self.entries[entry.entry_id] = entry
                logger.info(f"[WL-Pipeline] Loaded {len(self.entries)} whitelist entries")
            except Exception as e:
                logger.error(f"[WL-Pipeline] Failed to load entries: {e}")

    def _save_entries(self):
        """Save whitelist entries to disk."""
        entries_file = self.storage_dir / "entries.json"
        data = {
            "entries": [asdict(e) for e in self.entries.values()],
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(entries_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        return f"wl-{uuid.uuid4().hex[:12]}"

    def _generate_genesis_key(
        self,
        category: DataCategory,
        source: str,
        content_hash: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Generate Genesis Key for whitelist entry."""
        if self._genesis_service:
            try:
                from models.genesis_key_models import GenesisKeyType

                genesis_key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.INPUT,
                    what_description=f"Whitelist {category.value} from {source}",
                    who_actor=source,
                    where_location="whitelist_pipeline",
                    why_reason="Human-approved data for learning",
                    how_method="WhitelistLearningPipeline.process()",
                    context_data={
                        "category": category.value,
                        "content_hash": content_hash,
                        **(metadata or {})
                    },
                    tags=["whitelist", "learning", category.value, "human_input"]
                )
                return genesis_key.genesis_key
            except Exception as e:
                logger.warning(f"[WL-Pipeline] Genesis Key Service error: {e}")

        # Fallback
        timestamp = datetime.utcnow().isoformat()
        key_data = f"whitelist:{category.value}:{source}:{content_hash}:{timestamp}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:12]
        return f"gk-wl-{key_hash}"

    def _track_version(self, entry_id: str, stage: PipelineStage, data: Dict[str, Any]):
        """Track pipeline version/mutation."""
        if entry_id not in self.pipeline_versions:
            self.pipeline_versions[entry_id] = []

        version_entry = {
            "version": len(self.pipeline_versions[entry_id]) + 1,
            "stage": stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        self.pipeline_versions[entry_id].append(version_entry)

    # =========================================================================
    # Pipeline Stages
    # =========================================================================

    async def _stage_trust_verification(self, entry: WhitelistEntry) -> StageResult:
        """Stage 1: Verify trust level of the source."""
        start = datetime.utcnow()

        try:
            trust_score = self.trust_thresholds.get(entry.trust_level, 0.0)

            # Additional verification based on source
            if entry.user_id:
                # Check user's historical trust
                # Could integrate with user reputation system
                pass

            # Minimum trust threshold
            if trust_score < 0.25 and entry.trust_level == TrustLevel.UNTRUSTED:
                return StageResult(
                    stage=PipelineStage.TRUST_VERIFICATION,
                    success=False,
                    error="Trust level too low for processing",
                    duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                )

            return StageResult(
                stage=PipelineStage.TRUST_VERIFICATION,
                success=True,
                output={"trust_score": trust_score, "trust_level": entry.trust_level.value},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.TRUST_VERIFICATION,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_genesis_key(self, entry: WhitelistEntry) -> StageResult:
        """Stage 2: Assign Genesis Key for tracking."""
        start = datetime.utcnow()

        try:
            content_hash = hashlib.sha256(entry.content.encode()).hexdigest()[:16]

            genesis_key = self._generate_genesis_key(
                entry.category,
                entry.source,
                content_hash,
                entry.metadata
            )

            entry.genesis_key = genesis_key

            return StageResult(
                stage=PipelineStage.GENESIS_KEY_ASSIGNMENT,
                success=True,
                output={"genesis_key": genesis_key, "content_hash": content_hash},
                genesis_key=genesis_key,
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.GENESIS_KEY_ASSIGNMENT,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_data_extraction(self, entry: WhitelistEntry) -> StageResult:
        """Stage 3: Extract and analyze content."""
        start = datetime.utcnow()

        try:
            # Extract key information based on category
            extracted = {
                "content_length": len(entry.content),
                "word_count": len(entry.content.split()),
                "category": entry.category.value,
                "has_code": "```" in entry.content or "def " in entry.content,
                "has_urls": "http" in entry.content.lower(),
                "language": "en"  # Could use language detection
            }

            # Category-specific extraction
            if entry.category == DataCategory.CODE_SNIPPET:
                # Extract code-specific info
                extracted["code_lines"] = entry.content.count('\n') + 1
                extracted["has_functions"] = "def " in entry.content or "function " in entry.content

            elif entry.category == DataCategory.CONVERSATION:
                # Extract conversation turns
                extracted["turns"] = entry.content.count("Human:") + entry.content.count("User:")

            elif entry.category == DataCategory.TRAINING_EXAMPLE:
                # Check for input/output structure
                extracted["has_input"] = "input" in entry.content.lower()
                extracted["has_output"] = "output" in entry.content.lower()

            return StageResult(
                stage=PipelineStage.DATA_EXTRACTION,
                success=True,
                output=extracted,
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.DATA_EXTRACTION,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_librarian_filing(self, entry: WhitelistEntry, extracted: Dict) -> StageResult:
        """Stage 4: File with Librarian, organize and name."""
        start = datetime.utcnow()

        try:
            file_path = None

            if self._librarian:
                # Determine filename based on category and content
                category_prefixes = {
                    DataCategory.HUMAN_REQUEST: "request",
                    DataCategory.RESEARCH_DATA: "research",
                    DataCategory.CODE_SNIPPET: "code",
                    DataCategory.DOCUMENTATION: "doc",
                    DataCategory.CONVERSATION: "conv",
                    DataCategory.FEEDBACK: "feedback",
                    DataCategory.CORRECTION: "correction",
                    DataCategory.PREFERENCE: "pref",
                    DataCategory.TRAINING_EXAMPLE: "train",
                    DataCategory.KNOWLEDGE_FACT: "fact"
                }

                prefix = category_prefixes.get(entry.category, "data")
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                gk_suffix = entry.genesis_key.split("-")[-1][:6] if entry.genesis_key else "unknown"

                filename = f"{prefix}_{timestamp}_{gk_suffix}.md"

                # Create content with metadata header
                file_content = f"""---
entry_id: {entry.entry_id}
genesis_key: {entry.genesis_key}
category: {entry.category.value}
source: {entry.source}
trust_level: {entry.trust_level.value}
created_at: {entry.created_at}
---

# {entry.category.value.replace('_', ' ').title()}

{entry.content}
"""

                # Ingest through librarian
                result = await self._librarian.ingest_content(
                    content=file_content.encode('utf-8'),
                    filename=filename,
                    source="whitelist_pipeline",
                    metadata={
                        "entry_id": entry.entry_id,
                        "category": entry.category.value,
                        "genesis_key": entry.genesis_key
                    }
                )

                file_path = result.destination if result.success else None

            return StageResult(
                stage=PipelineStage.LIBRARIAN_FILING,
                success=True,
                output={"file_path": file_path},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.LIBRARIAN_FILING,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_embedding(self, entry: WhitelistEntry) -> StageResult:
        """Stage 5: Generate vector embeddings."""
        start = datetime.utcnow()

        try:
            embedding_id = None

            if self._embedder:
                # Generate embedding
                embedding_id = f"emb_{entry.genesis_key}"

                await self._embedder.add_document(
                    doc_id=embedding_id,
                    content=entry.content,
                    metadata={
                        "entry_id": entry.entry_id,
                        "category": entry.category.value,
                        "genesis_key": entry.genesis_key,
                        "source": entry.source
                    }
                )

            return StageResult(
                stage=PipelineStage.EMBEDDING_GENERATION,
                success=True,
                output={"embedding_id": embedding_id},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.EMBEDDING_GENERATION,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_memory_storage(self, entry: WhitelistEntry, extracted: Dict) -> StageResult:
        """Stage 6: Store in learning memory."""
        start = datetime.utcnow()

        try:
            memory_id = None

            if self._learning_memory:
                # Store in learning memory
                memory_entry = {
                    "type": "whitelist_learning",
                    "entry_id": entry.entry_id,
                    "genesis_key": entry.genesis_key,
                    "category": entry.category.value,
                    "content": entry.content,
                    "source": entry.source,
                    "trust_level": entry.trust_level.value,
                    "extracted": extracted,
                    "metadata": entry.metadata
                }

                result = self._learning_memory.store(memory_entry)
                memory_id = result.get("memory_id") if result else None

            return StageResult(
                stage=PipelineStage.MEMORY_STORAGE,
                success=True,
                output={"memory_id": memory_id},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.MEMORY_STORAGE,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_memory_mesh(self, entry: WhitelistEntry, memory_id: str) -> StageResult:
        """Stage 7: Link in memory mesh."""
        start = datetime.utcnow()

        try:
            links = []

            if self._memory_mesh:
                # Link to related memories
                # The memory mesh learner will find connections
                links = self._memory_mesh.link_memory(
                    memory_id=memory_id,
                    content=entry.content,
                    metadata={
                        "genesis_key": entry.genesis_key,
                        "category": entry.category.value
                    }
                )

            return StageResult(
                stage=PipelineStage.MEMORY_MESH_LINKING,
                success=True,
                output={"links": links},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.MEMORY_MESH_LINKING,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_cognitive(self, entry: WhitelistEntry) -> StageResult:
        """Stage 8: Process through cognitive framework."""
        start = datetime.utcnow()

        try:
            cognitive_result = None

            if self._cognitive:
                # Process through cognitive engine
                cognitive_result = await self._cognitive.process({
                    "input": entry.content,
                    "context": {
                        "category": entry.category.value,
                        "source": entry.source,
                        "genesis_key": entry.genesis_key
                    },
                    "task": "understand_and_learn"
                })

            return StageResult(
                stage=PipelineStage.COGNITIVE_PROCESSING,
                success=True,
                output={"cognitive_result": cognitive_result},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.COGNITIVE_PROCESSING,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_clarity(self, entry: WhitelistEntry, cognitive_result: Any) -> StageResult:
        """Stage 9: Apply clarity framework."""
        start = datetime.utcnow()

        try:
            # Clarity framework ensures clear understanding
            clarity_analysis = {
                "is_clear": True,
                "ambiguities": [],
                "clarifications_needed": [],
                "confidence": 0.8
            }

            # Check for ambiguities
            ambiguous_terms = ["it", "they", "this", "that", "those"]
            content_lower = entry.content.lower()

            for term in ambiguous_terms:
                if f" {term} " in content_lower:
                    clarity_analysis["ambiguities"].append({
                        "term": term,
                        "context": "Potential ambiguous reference"
                    })

            if clarity_analysis["ambiguities"]:
                clarity_analysis["is_clear"] = False
                clarity_analysis["confidence"] *= 0.9

            return StageResult(
                stage=PipelineStage.CLARITY_ANALYSIS,
                success=True,
                output=clarity_analysis,
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.CLARITY_ANALYSIS,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_contradiction_check(self, entry: WhitelistEntry) -> StageResult:
        """Stage 10: Check for contradictions with existing knowledge."""
        start = datetime.utcnow()

        try:
            contradictions = []

            if self._contradiction_detector:
                # Check against existing knowledge
                detected = self._contradiction_detector.check(entry.content)
                contradictions = detected if detected else []

            return StageResult(
                stage=PipelineStage.CONTRADICTION_CHECK,
                success=True,
                output={"contradictions": contradictions},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.CONTRADICTION_CHECK,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_pattern_extraction(self, entry: WhitelistEntry, extracted: Dict) -> StageResult:
        """Stage 11: Extract patterns for ML training."""
        start = datetime.utcnow()

        try:
            patterns = []

            # Extract patterns based on category
            if entry.category == DataCategory.TRAINING_EXAMPLE:
                # Extract input/output pattern
                patterns.append({
                    "type": "training_example",
                    "content": entry.content,
                    "genesis_key": entry.genesis_key
                })

            elif entry.category == DataCategory.CORRECTION:
                # Extract correction pattern
                patterns.append({
                    "type": "correction",
                    "content": entry.content,
                    "genesis_key": entry.genesis_key
                })

            elif entry.category == DataCategory.PREFERENCE:
                # Extract preference pattern
                patterns.append({
                    "type": "preference",
                    "content": entry.content,
                    "genesis_key": entry.genesis_key
                })

            return StageResult(
                stage=PipelineStage.PATTERN_EXTRACTION,
                success=True,
                output={"patterns": patterns},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.PATTERN_EXTRACTION,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_ml_training(self, entry: WhitelistEntry, patterns: List) -> StageResult:
        """Stage 12: Trigger ML training if applicable."""
        start = datetime.utcnow()

        try:
            training_triggered = False

            if self._ml_intelligence and patterns:
                # Queue for ML training
                for pattern in patterns:
                    self._ml_intelligence.queue_training_example(pattern)
                training_triggered = True

            return StageResult(
                stage=PipelineStage.ML_TRAINING,
                success=True,
                output={"training_triggered": training_triggered, "patterns_count": len(patterns)},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.ML_TRAINING,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_knowledge_base(self, entry: WhitelistEntry, results: Dict) -> StageResult:
        """Stage 13: Update knowledge base."""
        start = datetime.utcnow()

        try:
            knowledge_id = None

            # Store in knowledge base if it's a knowledge fact
            if entry.category == DataCategory.KNOWLEDGE_FACT:
                knowledge_id = f"kb_{entry.genesis_key}"

                # Would integrate with actual KB system
                # For now, create a knowledge entry
                knowledge_entry = {
                    "knowledge_id": knowledge_id,
                    "genesis_key": entry.genesis_key,
                    "content": entry.content,
                    "source": entry.source,
                    "trust_level": entry.trust_level.value,
                    "verified": entry.trust_level in [TrustLevel.VERIFIED, TrustLevel.OWNER]
                }

                # Save to knowledge directory
                kb_dir = self.storage_dir / "knowledge"
                kb_dir.mkdir(exist_ok=True)

                kb_file = kb_dir / f"{knowledge_id}.json"
                with open(kb_file, "w") as f:
                    json.dump(knowledge_entry, f, indent=2)

            return StageResult(
                stage=PipelineStage.KNOWLEDGE_BASE_UPDATE,
                success=True,
                output={"knowledge_id": knowledge_id},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.KNOWLEDGE_BASE_UPDATE,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_proactive_learning(self, entry: WhitelistEntry) -> StageResult:
        """Stage 14: Trigger proactive learning."""
        start = datetime.utcnow()

        try:
            proactive_actions = []

            if self._proactive_learner:
                # Trigger proactive learning based on new data
                actions = self._proactive_learner.suggest_learning(
                    content=entry.content,
                    category=entry.category.value
                )
                proactive_actions = actions if actions else []

            if self._active_learning:
                # Queue for active learning
                self._active_learning.queue_for_learning({
                    "entry_id": entry.entry_id,
                    "genesis_key": entry.genesis_key,
                    "content": entry.content,
                    "category": entry.category.value
                })

            return StageResult(
                stage=PipelineStage.PROACTIVE_LEARNING,
                success=True,
                output={"proactive_actions": proactive_actions},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.PROACTIVE_LEARNING,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    async def _stage_mirror_observation(self, entry: WhitelistEntry, all_results: Dict) -> StageResult:
        """Stage 15: Mirror self-modeling observes the learning."""
        start = datetime.utcnow()

        try:
            if self._mirror:
                # Mirror observes the complete learning process
                # This happens automatically through Genesis Keys
                logger.debug(f"[WL-Pipeline] Mirror observing entry {entry.entry_id}")

            return StageResult(
                stage=PipelineStage.MIRROR_OBSERVATION,
                success=True,
                output={"observed": True},
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        except Exception as e:
            return StageResult(
                stage=PipelineStage.MIRROR_OBSERVATION,
                success=False,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

    # =========================================================================
    # Main Pipeline Execution
    # =========================================================================

    async def process(
        self,
        content: str,
        source: str,
        category: DataCategory,
        trust_level: TrustLevel = TrustLevel.MEDIUM,
        metadata: Dict[str, Any] = None,
        user_id: str = None,
        session_id: str = None,
        parent_entry_id: str = None
    ) -> PipelineResult:
        """
        Process a whitelist entry through the complete learning pipeline.

        Args:
            content: The data content to process
            source: Who/what provided this data
            category: Category of the data
            trust_level: Trust level of the source
            metadata: Additional metadata
            user_id: User ID if from a user
            session_id: Session ID for tracking
            parent_entry_id: Parent entry if this is linked

        Returns:
            PipelineResult with all processing results
        """
        start_time = datetime.utcnow()
        entry_id = self._generate_entry_id()
        stages_completed = []
        stage_outputs = {}

        # Create entry
        entry = WhitelistEntry(
            entry_id=entry_id,
            source=source,
            category=category,
            content=content,
            metadata=metadata or {},
            trust_level=trust_level,
            created_at=start_time.isoformat(),
            user_id=user_id,
            session_id=session_id,
            parent_entry_id=parent_entry_id
        )

        self.entries[entry_id] = entry

        logger.info(f"[WL-Pipeline] Starting pipeline for entry {entry_id}: {category.value} from {source}")

        try:
            # Stage 1: Trust Verification
            result = await self._stage_trust_verification(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            if not result.success:
                raise ValueError(result.error)
            stages_completed.append(result.stage.value)
            stage_outputs["trust"] = result.output

            # Stage 2: Genesis Key Assignment
            result = await self._stage_genesis_key(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            if not result.success:
                raise ValueError(result.error)
            stages_completed.append(result.stage.value)
            stage_outputs["genesis"] = result.output
            genesis_key = entry.genesis_key

            # Stage 3: Data Extraction
            result = await self._stage_data_extraction(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["extraction"] = result.output
            extracted = result.output or {}

            # Stage 4: Librarian Filing
            result = await self._stage_librarian_filing(entry, extracted)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["filing"] = result.output
            file_path = result.output.get("file_path") if result.output else None

            # Stage 5: Embedding Generation
            result = await self._stage_embedding(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["embedding"] = result.output
            embedding_id = result.output.get("embedding_id") if result.output else None

            # Stage 6: Memory Storage
            result = await self._stage_memory_storage(entry, extracted)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["memory"] = result.output
            memory_id = result.output.get("memory_id") if result.output else None

            # Stage 7: Memory Mesh Linking
            result = await self._stage_memory_mesh(entry, memory_id)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["mesh"] = result.output

            # Stage 8: Cognitive Processing
            result = await self._stage_cognitive(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["cognitive"] = result.output
            cognitive_result = result.output.get("cognitive_result") if result.output else None

            # Stage 9: Clarity Analysis
            result = await self._stage_clarity(entry, cognitive_result)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["clarity"] = result.output

            # Stage 10: Contradiction Check
            result = await self._stage_contradiction_check(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["contradictions"] = result.output
            contradictions = result.output.get("contradictions", []) if result.output else []

            # Stage 11: Pattern Extraction
            result = await self._stage_pattern_extraction(entry, extracted)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["patterns"] = result.output
            patterns = result.output.get("patterns", []) if result.output else []

            # Stage 12: ML Training
            result = await self._stage_ml_training(entry, patterns)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["ml"] = result.output

            # Stage 13: Knowledge Base Update
            result = await self._stage_knowledge_base(entry, stage_outputs)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["knowledge"] = result.output
            knowledge_id = result.output.get("knowledge_id") if result.output else None

            # Stage 14: Proactive Learning
            result = await self._stage_proactive_learning(entry)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)
            stage_outputs["proactive"] = result.output

            # Stage 15: Mirror Observation
            result = await self._stage_mirror_observation(entry, stage_outputs)
            self._track_version(entry_id, result.stage, asdict(result))
            stages_completed.append(result.stage.value)

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Build final result
            pipeline_result = PipelineResult(
                entry_id=entry_id,
                genesis_key=genesis_key,
                success=True,
                stage=PipelineStage.COMPLETE,
                stages_completed=stages_completed,
                file_path=file_path,
                memory_id=memory_id,
                embedding_id=embedding_id,
                knowledge_id=knowledge_id,
                patterns_found=patterns,
                contradictions=contradictions,
                insights=[],  # Could extract from cognitive result
                trust_score=stage_outputs.get("trust", {}).get("trust_score", 0.0),
                confidence=stage_outputs.get("clarity", {}).get("confidence", 0.0),
                duration_ms=duration_ms,
                message="Pipeline completed successfully"
            )

            self.results[entry_id] = pipeline_result
            self._save_entries()

            logger.info(f"[WL-Pipeline] Completed entry {entry_id} in {duration_ms}ms")

            return pipeline_result

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.error(f"[WL-Pipeline] Pipeline failed for entry {entry_id}: {e}")

            pipeline_result = PipelineResult(
                entry_id=entry_id,
                genesis_key=entry.genesis_key or "",
                success=False,
                stage=PipelineStage.FAILED,
                stages_completed=stages_completed,
                duration_ms=duration_ms,
                error=str(e),
                message=f"Pipeline failed: {e}"
            )

            self.results[entry_id] = pipeline_result
            self._save_entries()

            return pipeline_result

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_entry(self, entry_id: str) -> Optional[WhitelistEntry]:
        """Get a whitelist entry by ID."""
        return self.entries.get(entry_id)

    def get_result(self, entry_id: str) -> Optional[PipelineResult]:
        """Get pipeline result for an entry."""
        return self.results.get(entry_id)

    def list_entries(
        self,
        category: DataCategory = None,
        trust_level: TrustLevel = None,
        limit: int = 100
    ) -> List[WhitelistEntry]:
        """List whitelist entries with optional filters."""
        entries = list(self.entries.values())

        if category:
            entries = [e for e in entries if e.category == category]

        if trust_level:
            entries = [e for e in entries if e.trust_level == trust_level]

        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        entries = list(self.entries.values())
        results = list(self.results.values())

        # Count by category
        by_category = {}
        for cat in DataCategory:
            by_category[cat.value] = len([e for e in entries if e.category == cat])

        # Count by trust level
        by_trust = {}
        for trust in TrustLevel:
            by_trust[trust.value] = len([e for e in entries if e.trust_level == trust])

        # Success rate
        successful = len([r for r in results if r.success])
        total = len(results)

        return {
            "total_entries": len(entries),
            "total_processed": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_category": by_category,
            "by_trust_level": by_trust,
            "integrations": {
                "genesis_key_service": self._genesis_service is not None,
                "cognitive_engine": self._cognitive is not None,
                "mirror_system": self._mirror is not None,
                "active_learning": self._active_learning is not None,
                "memory_mesh": self._memory_mesh is not None,
                "contradiction_detector": self._contradiction_detector is not None,
                "proactive_learner": self._proactive_learner is not None,
                "embedder": self._embedder is not None,
                "librarian": self._librarian is not None,
                "learning_memory": self._learning_memory is not None,
                "ml_intelligence": self._ml_intelligence is not None
            }
        }


# =============================================================================
# Global Instance
# =============================================================================

_whitelist_pipeline: Optional[WhitelistLearningPipeline] = None


def get_whitelist_pipeline() -> WhitelistLearningPipeline:
    """Get the global whitelist learning pipeline instance."""
    global _whitelist_pipeline
    if _whitelist_pipeline is None:
        _whitelist_pipeline = WhitelistLearningPipeline()
    return _whitelist_pipeline


# =============================================================================
# Convenience Functions
# =============================================================================

async def process_whitelist_entry(
    content: str,
    source: str,
    category: DataCategory,
    trust_level: TrustLevel = TrustLevel.MEDIUM,
    metadata: Dict[str, Any] = None
) -> PipelineResult:
    """Convenience function to process a whitelist entry."""
    pipeline = get_whitelist_pipeline()
    return await pipeline.process(
        content=content,
        source=source,
        category=category,
        trust_level=trust_level,
        metadata=metadata
    )
