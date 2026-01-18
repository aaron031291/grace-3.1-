import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import uuid
logger = logging.getLogger(__name__)

class FailureType(str, Enum):
    """Types of failures to track."""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    BUILD_FAILURE = "build_failure"
    LINT_ERROR = "lint_error"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INTEGRATION = "integration"
    UNKNOWN = "unknown"


class ResolutionStatus(str, Enum):
    """Resolution status of a failure."""
    UNRESOLVED = "unresolved"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


@dataclass
class FailureRecord:
    """Record of a failure for learning."""
    failure_id: str
    failure_type: FailureType
    error_message: str
    stack_trace: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_context: Optional[str] = None
    genesis_key_id: Optional[str] = None
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    resolution: Optional[str] = None
    similar_failures: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_context": self.code_context,
            "genesis_key_id": self.genesis_key_id,
            "resolution_status": self.resolution_status.value,
            "resolution": self.resolution,
            "similar_failures": self.similar_failures,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }


class FailureLearningSystem:
    """
    System for learning from failures.

    Stores failures in VectorDB for:
    - Pattern recognition
    - Similar failure lookup
    - Solution suggestion
    - Training data generation
    """

    def __init__(
        self,
        session=None,
        vector_db=None
    ):
        self.session = session
        self._vector_db = vector_db

        # In-memory failure cache
        self._failures: Dict[str, FailureRecord] = {}

        # Resolution patterns (learned)
        self._resolution_patterns: Dict[str, List[str]] = {}

        # Metrics
        self.metrics = {
            "failures_recorded": 0,
            "failures_resolved": 0,
            "patterns_learned": 0,
            "solutions_suggested": 0
        }

        # VectorDB collections
        self._collections = {
            "failures": "grace_failures",
            "resolutions": "grace_resolutions",
            "training_data": "grace_training_failures"
        }

        logger.info("[FAILURE-LEARNING] System initialized")

    async def record_failure(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        error: str,
        genesis_key_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        file_path: Optional[str] = None,
        code_context: Optional[str] = None
    ) -> FailureRecord:
        """
        Record a failure for learning.

        Args:
            action_type: Type of action that failed
            parameters: Action parameters
            error: Error message
            genesis_key_id: Associated genesis key
            stack_trace: Full stack trace
            file_path: File where failure occurred
            code_context: Surrounding code context

        Returns:
            FailureRecord for tracking
        """
        # Classify failure type
        failure_type = self._classify_failure(error, stack_trace)

        # Create record
        record = FailureRecord(
            failure_id=f"FAIL-{uuid.uuid4().hex[:12]}",
            failure_type=failure_type,
            error_message=error,
            stack_trace=stack_trace,
            file_path=file_path,
            code_context=code_context,
            genesis_key_id=genesis_key_id,
            metadata={
                "action_type": action_type,
                "parameters": parameters
            }
        )

        # Find similar failures
        similar = await self._find_similar_failures(record)
        record.similar_failures = similar

        # Store in memory
        self._failures[record.failure_id] = record

        # Store in VectorDB
        await self._store_in_vectordb(record)

        self.metrics["failures_recorded"] += 1

        logger.info(f"[FAILURE-LEARNING] Recorded failure {record.failure_id}: {error[:50]}")

        return record

    def _classify_failure(self, error: str, stack_trace: Optional[str]) -> FailureType:
        """Classify the type of failure."""
        error_lower = error.lower()

        if "syntax" in error_lower or "syntaxerror" in error_lower:
            return FailureType.SYNTAX_ERROR
        elif "import" in error_lower or "modulenotfound" in error_lower:
            return FailureType.IMPORT_ERROR
        elif "type" in error_lower or "typeerror" in error_lower:
            return FailureType.TYPE_ERROR
        elif "test" in error_lower or "assertion" in error_lower:
            return FailureType.TEST_FAILURE
        elif "build" in error_lower or "compile" in error_lower:
            return FailureType.BUILD_FAILURE
        elif "lint" in error_lower or "style" in error_lower:
            return FailureType.LINT_ERROR
        elif "runtime" in error_lower or "exception" in error_lower:
            return FailureType.RUNTIME_ERROR
        elif "performance" in error_lower or "timeout" in error_lower:
            return FailureType.PERFORMANCE
        elif "security" in error_lower or "auth" in error_lower:
            return FailureType.SECURITY
        else:
            return FailureType.UNKNOWN

    async def _find_similar_failures(self, record: FailureRecord) -> List[str]:
        """Find similar failures in VectorDB."""
        if not self._vector_db:
            return []

        try:
            # Create embedding from failure text
            from embedding.embedder import get_embedder
            embedder = get_embedder()

            text = f"{record.error_message} {record.code_context or ''}"
            embedding = await embedder.embed(text)

            # Search VectorDB
            results = await self._vector_db.search(
                collection_name=self._collections["failures"],
                query_vector=embedding,
                limit=5
            )

            return [r.id for r in results if r.score > 0.7]

        except Exception as e:
            logger.warning(f"[FAILURE-LEARNING] Similar failure search failed: {e}")
            return []

    async def _store_in_vectordb(self, record: FailureRecord):
        """Store failure record in VectorDB."""
        if not self._vector_db:
            return

        try:
            from embedding.embedder import get_embedder
            embedder = get_embedder()

            # Create embedding
            text = f"{record.failure_type.value}: {record.error_message} {record.code_context or ''}"
            embedding = await embedder.embed(text)

            # Upsert to VectorDB
            await self._vector_db.upsert(
                collection_name=self._collections["failures"],
                points=[{
                    "id": record.failure_id,
                    "vector": embedding,
                    "payload": record.to_dict()
                }]
            )

        except Exception as e:
            logger.warning(f"[FAILURE-LEARNING] VectorDB store failed: {e}")

    async def record_resolution(
        self,
        failure_id: str,
        resolution: str,
        resolution_code: Optional[str] = None
    ) -> bool:
        """
        Record how a failure was resolved.

        This is key for learning and suggesting solutions.
        """
        if failure_id not in self._failures:
            return False

        record = self._failures[failure_id]
        record.resolution = resolution
        record.resolution_status = ResolutionStatus.RESOLVED
        record.resolved_at = datetime.utcnow()

        # Store resolution pattern
        pattern_key = f"{record.failure_type.value}:{self._hash_error(record.error_message)}"
        if pattern_key not in self._resolution_patterns:
            self._resolution_patterns[pattern_key] = []
        self._resolution_patterns[pattern_key].append(resolution)

        self.metrics["failures_resolved"] += 1
        self.metrics["patterns_learned"] += 1

        # Store resolution in VectorDB for future suggestions
        if self._vector_db:
            try:
                from embedding.embedder import get_embedder
                embedder = get_embedder()

                text = f"Resolution for {record.error_message}: {resolution}"
                embedding = await embedder.embed(text)

                await self._vector_db.upsert(
                    collection_name=self._collections["resolutions"],
                    points=[{
                        "id": f"RES-{failure_id}",
                        "vector": embedding,
                        "payload": {
                            "failure_id": failure_id,
                            "failure_type": record.failure_type.value,
                            "error_message": record.error_message,
                            "resolution": resolution,
                            "resolution_code": resolution_code
                        }
                    }]
                )
            except Exception as e:
                logger.warning(f"[FAILURE-LEARNING] Resolution store failed: {e}")

        logger.info(f"[FAILURE-LEARNING] Recorded resolution for {failure_id}")

        return True

    async def suggest_solution(
        self,
        error_message: str,
        code_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest solutions based on past resolutions.

        Searches VectorDB for similar past failures and their resolutions.
        """
        suggestions = []

        if not self._vector_db:
            return suggestions

        try:
            from embedding.embedder import get_embedder
            embedder = get_embedder()

            text = f"{error_message} {code_context or ''}"
            embedding = await embedder.embed(text)

            # Search resolutions
            results = await self._vector_db.search(
                collection_name=self._collections["resolutions"],
                query_vector=embedding,
                limit=5
            )

            for result in results:
                if result.score > 0.6:
                    payload = result.payload or {}
                    suggestions.append({
                        "similarity": result.score,
                        "past_error": payload.get("error_message", ""),
                        "resolution": payload.get("resolution", ""),
                        "resolution_code": payload.get("resolution_code")
                    })

            self.metrics["solutions_suggested"] += len(suggestions)

        except Exception as e:
            logger.warning(f"[FAILURE-LEARNING] Solution suggestion failed: {e}")

        return suggestions

    async def store_learning(
        self,
        feedback: str,
        example: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store learning feedback for training."""
        learning_id = f"LEARN-{uuid.uuid4().hex[:8]}"

        if self._vector_db:
            try:
                from embedding.embedder import get_embedder
                embedder = get_embedder()

                text = f"{feedback} {example or ''}"
                embedding = await embedder.embed(text)

                await self._vector_db.upsert(
                    collection_name=self._collections["training_data"],
                    points=[{
                        "id": learning_id,
                        "vector": embedding,
                        "payload": {
                            "feedback": feedback,
                            "example": example,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }]
                )

                return {"success": True, "learning_id": learning_id}

            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "VectorDB not available"}

    def _hash_error(self, error: str) -> str:
        """Create hash of error for pattern matching."""
        return hashlib.md5(error.encode()).hexdigest()[:8]

    def get_failure(self, failure_id: str) -> Optional[Dict[str, Any]]:
        """Get a failure record."""
        if failure_id in self._failures:
            return self._failures[failure_id].to_dict()
        return None

    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failures."""
        sorted_failures = sorted(
            self._failures.values(),
            key=lambda f: f.created_at,
            reverse=True
        )
        return [f.to_dict() for f in sorted_failures[:limit]]

    def get_learning_status(self) -> Dict[str, Any]:
        """Get learning system status."""
        failure_distribution = {}
        for f in self._failures.values():
            ft = f.failure_type.value
            failure_distribution[ft] = failure_distribution.get(ft, 0) + 1

        return {
            **self.metrics,
            "total_failures": len(self._failures),
            "resolution_patterns": len(self._resolution_patterns),
            "failure_distribution": failure_distribution
        }

    async def generate_training_data(self) -> List[Dict[str, Any]]:
        """Generate training data from resolved failures."""
        training_data = []

        for failure in self._failures.values():
            if failure.resolution_status == ResolutionStatus.RESOLVED:
                training_data.append({
                    "input": {
                        "error_type": failure.failure_type.value,
                        "error_message": failure.error_message,
                        "code_context": failure.code_context
                    },
                    "output": {
                        "resolution": failure.resolution
                    }
                })

        return training_data
