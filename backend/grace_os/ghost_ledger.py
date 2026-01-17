import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
import difflib
import uuid
class ChangeType(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of code changes tracked."""
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    RENAME = "rename"
    MOVE = "move"


class StabilityStatus(str, Enum):
    """Stability status for ghost records."""
    UNSTABLE = "unstable"        # Recent changes, still monitoring
    MONITORING = "monitoring"    # Stable but in observation period
    STABLE = "stable"            # Passed stability period
    ARCHIVED = "archived"        # Moved to Ghost Memory
    REGRESSED = "regressed"      # Had issues after being stable


@dataclass
class LineChange:
    """Represents a single line change."""
    line_number: int
    change_type: ChangeType
    old_content: Optional[str]
    new_content: Optional[str]
    timestamp: datetime
    genesis_key_id: Optional[str] = None
    confidence: float = 1.0
    source: str = "user"  # user, llm, healing, refactor


@dataclass
class GhostRecord:
    """A ghost ledger record for a code change session."""
    record_id: str
    file_path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    genesis_key_id: Optional[str] = None
    parent_genesis_key_id: Optional[str] = None
    line_changes: List[LineChange] = field(default_factory=list)
    stability_status: StabilityStatus = StabilityStatus.UNSTABLE
    stability_score: float = 0.0
    regression_count: int = 0
    last_regression: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "record_id": self.record_id,
            "file_path": self.file_path,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "genesis_key_id": self.genesis_key_id,
            "parent_genesis_key_id": self.parent_genesis_key_id,
            "line_changes": [
                {
                    "line_number": lc.line_number,
                    "change_type": lc.change_type.value,
                    "old_content": lc.old_content,
                    "new_content": lc.new_content,
                    "timestamp": lc.timestamp.isoformat(),
                    "genesis_key_id": lc.genesis_key_id,
                    "confidence": lc.confidence,
                    "source": lc.source
                }
                for lc in self.line_changes
            ],
            "stability_status": self.stability_status.value,
            "stability_score": self.stability_score,
            "regression_count": self.regression_count,
            "last_regression": self.last_regression.isoformat() if self.last_regression else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GhostRecord":
        """Create from dictionary."""
        record = cls(
            record_id=data["record_id"],
            file_path=data["file_path"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            genesis_key_id=data.get("genesis_key_id"),
            parent_genesis_key_id=data.get("parent_genesis_key_id"),
            stability_status=StabilityStatus(data.get("stability_status", "unstable")),
            stability_score=data.get("stability_score", 0.0),
            regression_count=data.get("regression_count", 0),
            last_regression=datetime.fromisoformat(data["last_regression"]) if data.get("last_regression") else None,
            metadata=data.get("metadata", {})
        )

        record.line_changes = [
            LineChange(
                line_number=lc["line_number"],
                change_type=ChangeType(lc["change_type"]),
                old_content=lc.get("old_content"),
                new_content=lc.get("new_content"),
                timestamp=datetime.fromisoformat(lc["timestamp"]),
                genesis_key_id=lc.get("genesis_key_id"),
                confidence=lc.get("confidence", 1.0),
                source=lc.get("source", "user")
            )
            for lc in data.get("line_changes", [])
        ]

        return record


@dataclass
class GhostMemoryEntry:
    """
    Ghost Memory entry - compressed learning from archived Ghost Records.

    Contains patterns and learnings without raw line-level data.
    """
    entry_id: str
    file_path: str
    pattern_type: str  # refactor, bug_fix, feature, optimization
    pattern_hash: str
    genesis_key_ids: List[str]  # All related genesis keys
    learned_at: datetime
    confidence: float
    pattern_summary: Dict[str, Any]
    evolution_trend: Optional[str] = None  # improving, stable, degrading
    regression_intelligence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "file_path": self.file_path,
            "pattern_type": self.pattern_type,
            "pattern_hash": self.pattern_hash,
            "genesis_key_ids": self.genesis_key_ids,
            "learned_at": self.learned_at.isoformat(),
            "confidence": self.confidence,
            "pattern_summary": self.pattern_summary,
            "evolution_trend": self.evolution_trend,
            "regression_intelligence": self.regression_intelligence
        }


class GhostLedger:
    """
    Ghost Ledger for line-by-line code generation tracking.

    Records all code changes outside Grace's core cognition.
    Manages lifecycle: Active → Stable → Archived (Ghost Memory)
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None,
        stability_period_days: int = 30,
        max_active_records: int = 10000,
        enable_background_learning: bool = True
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self.stability_period = timedelta(days=stability_period_days)
        self.max_active_records = max_active_records
        self.enable_background_learning = enable_background_learning

        # Active ghost records (in memory, persisted periodically)
        self.active_records: Dict[str, GhostRecord] = {}

        # Ghost Memory (compressed, long-term)
        self.ghost_memory: Dict[str, GhostMemoryEntry] = {}

        # File -> current record mapping
        self.file_record_map: Dict[str, str] = {}

        # Pattern registry for learning
        self.pattern_registry: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Metrics
        self.metrics = {
            "total_records": 0,
            "active_records": 0,
            "archived_records": 0,
            "patterns_learned": 0,
            "regressions_detected": 0
        }

        # Load persisted data
        self._load_persisted_data()

        logger.info(
            f"[GHOST-LEDGER] Initialized with stability_period={stability_period_days} days, "
            f"max_records={max_active_records}"
        )

    def _load_persisted_data(self):
        """Load persisted ghost ledger data."""
        ledger_file = self.repo_path / ".grace" / "ghost_ledger.json"
        memory_file = self.repo_path / ".grace" / "ghost_memory.json"

        try:
            if ledger_file.exists():
                with open(ledger_file, 'r') as f:
                    data = json.load(f)
                    for record_data in data.get("records", []):
                        record = GhostRecord.from_dict(record_data)
                        self.active_records[record.record_id] = record
                        if record.stability_status != StabilityStatus.ARCHIVED:
                            self.file_record_map[record.file_path] = record.record_id
                    self.metrics = data.get("metrics", self.metrics)

            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = GhostMemoryEntry(
                            entry_id=entry_data["entry_id"],
                            file_path=entry_data["file_path"],
                            pattern_type=entry_data["pattern_type"],
                            pattern_hash=entry_data["pattern_hash"],
                            genesis_key_ids=entry_data["genesis_key_ids"],
                            learned_at=datetime.fromisoformat(entry_data["learned_at"]),
                            confidence=entry_data["confidence"],
                            pattern_summary=entry_data["pattern_summary"],
                            evolution_trend=entry_data.get("evolution_trend"),
                            regression_intelligence=entry_data.get("regression_intelligence", {})
                        )
                        self.ghost_memory[entry.entry_id] = entry

            logger.info(
                f"[GHOST-LEDGER] Loaded {len(self.active_records)} records, "
                f"{len(self.ghost_memory)} memory entries"
            )

        except Exception as e:
            logger.warning(f"[GHOST-LEDGER] Could not load persisted data: {e}")

    async def persist(self):
        """Persist ghost ledger data to disk."""
        grace_dir = self.repo_path / ".grace"
        grace_dir.mkdir(parents=True, exist_ok=True)

        ledger_file = grace_dir / "ghost_ledger.json"
        memory_file = grace_dir / "ghost_memory.json"

        try:
            # Save active records
            ledger_data = {
                "records": [r.to_dict() for r in self.active_records.values()],
                "metrics": self.metrics,
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(ledger_file, 'w') as f:
                json.dump(ledger_data, f, indent=2)

            # Save ghost memory
            memory_data = {
                "entries": [e.to_dict() for e in self.ghost_memory.values()],
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)

            logger.debug("[GHOST-LEDGER] Persisted data to disk")

        except Exception as e:
            logger.error(f"[GHOST-LEDGER] Failed to persist data: {e}")

    # =========================================================================
    # Recording Changes
    # =========================================================================

    async def record_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        genesis_key_id: Optional[str] = None,
        source: str = "user",
        confidence: float = 1.0
    ) -> GhostRecord:
        """
        Record a code change at line-level granularity.

        Args:
            file_path: Path to the changed file
            old_content: Content before change
            new_content: Content after change
            genesis_key_id: Associated genesis key
            source: Source of change (user, llm, healing, etc.)
            confidence: Confidence in the change (0.0-1.0)

        Returns:
            The ghost record containing the changes
        """
        # Get or create record for this file
        record = self._get_or_create_record(file_path, genesis_key_id)

        # Calculate line-level diff
        line_changes = self._compute_line_diff(old_content, new_content, source, confidence)

        # Add genesis key reference to line changes
        for lc in line_changes:
            lc.genesis_key_id = genesis_key_id

        record.line_changes.extend(line_changes)
        record.metadata["last_change"] = datetime.utcnow().isoformat()
        record.metadata["change_count"] = record.metadata.get("change_count", 0) + 1

        # Update stability
        record.stability_status = StabilityStatus.UNSTABLE
        record.stability_score = self._calculate_stability_score(record)

        self.metrics["total_records"] = len(self.active_records)
        self.metrics["active_records"] = sum(
            1 for r in self.active_records.values()
            if r.stability_status != StabilityStatus.ARCHIVED
        )

        logger.debug(
            f"[GHOST-LEDGER] Recorded {len(line_changes)} line changes for {file_path}"
        )

        return record

    def _get_or_create_record(
        self,
        file_path: str,
        genesis_key_id: Optional[str] = None
    ) -> GhostRecord:
        """Get existing record or create new one for a file."""
        if file_path in self.file_record_map:
            record_id = self.file_record_map[file_path]
            if record_id in self.active_records:
                return self.active_records[record_id]

        # Create new record
        record_id = f"GR-{uuid.uuid4().hex[:16]}"
        record = GhostRecord(
            record_id=record_id,
            file_path=file_path,
            start_time=datetime.utcnow(),
            genesis_key_id=genesis_key_id
        )

        self.active_records[record_id] = record
        self.file_record_map[file_path] = record_id

        return record

    def _compute_line_diff(
        self,
        old_content: str,
        new_content: str,
        source: str,
        confidence: float
    ) -> List[LineChange]:
        """Compute line-by-line diff between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        changes = []
        now = datetime.utcnow()

        # Use difflib to get line-level diff
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))

        current_line = 0
        for line in diff:
            if line.startswith('@@'):
                # Parse line numbers from hunk header
                # Format: @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 3:
                    new_spec = parts[2]  # +start,count or +start
                    if new_spec.startswith('+'):
                        try:
                            if ',' in new_spec:
                                current_line = int(new_spec[1:].split(',')[0])
                            else:
                                current_line = int(new_spec[1:])
                        except ValueError:
                            pass

            elif line.startswith('-') and not line.startswith('---'):
                changes.append(LineChange(
                    line_number=current_line,
                    change_type=ChangeType.DELETION,
                    old_content=line[1:].rstrip('\n'),
                    new_content=None,
                    timestamp=now,
                    confidence=confidence,
                    source=source
                ))

            elif line.startswith('+') and not line.startswith('+++'):
                changes.append(LineChange(
                    line_number=current_line,
                    change_type=ChangeType.ADDITION,
                    old_content=None,
                    new_content=line[1:].rstrip('\n'),
                    timestamp=now,
                    confidence=confidence,
                    source=source
                ))
                current_line += 1

            elif not line.startswith('\\'):  # Skip "no newline" markers
                current_line += 1

        return changes

    def _calculate_stability_score(self, record: GhostRecord) -> float:
        """Calculate stability score for a record (0.0-1.0)."""
        if not record.line_changes:
            return 1.0

        score = 1.0

        # Reduce score for recent changes
        now = datetime.utcnow()
        recent_changes = [
            lc for lc in record.line_changes
            if (now - lc.timestamp).days < 7
        ]
        if recent_changes:
            score -= 0.1 * min(len(recent_changes) / 10, 0.5)

        # Reduce score for regressions
        if record.regression_count > 0:
            score -= 0.1 * min(record.regression_count, 3)

        # Reduce score for low confidence changes
        low_confidence = [lc for lc in record.line_changes if lc.confidence < 0.7]
        if low_confidence:
            score -= 0.05 * min(len(low_confidence) / len(record.line_changes), 0.3)

        return max(0.0, min(1.0, score))

    # =========================================================================
    # Stability Management
    # =========================================================================

    async def check_stability(self) -> Dict[str, Any]:
        """
        Check all records for stability and archive stable ones.

        Returns statistics about the stability check.
        """
        now = datetime.utcnow()
        stats = {
            "checked": 0,
            "promoted_to_stable": 0,
            "archived": 0,
            "regressed": 0
        }

        records_to_archive = []

        for record_id, record in self.active_records.items():
            if record.stability_status == StabilityStatus.ARCHIVED:
                continue

            stats["checked"] += 1

            # Calculate time since last change
            last_change_str = record.metadata.get("last_change")
            if last_change_str:
                last_change = datetime.fromisoformat(last_change_str)
                time_stable = now - last_change
            else:
                time_stable = now - record.start_time

            # Update stability score
            record.stability_score = self._calculate_stability_score(record)

            # Check if stable enough for promotion
            if record.stability_status == StabilityStatus.UNSTABLE:
                if time_stable >= timedelta(days=7) and record.stability_score >= 0.7:
                    record.stability_status = StabilityStatus.MONITORING
                    logger.debug(f"[GHOST-LEDGER] Record {record_id} promoted to MONITORING")

            elif record.stability_status == StabilityStatus.MONITORING:
                if time_stable >= self.stability_period and record.stability_score >= 0.8:
                    record.stability_status = StabilityStatus.STABLE
                    stats["promoted_to_stable"] += 1
                    logger.info(f"[GHOST-LEDGER] Record {record_id} is now STABLE")

            elif record.stability_status == StabilityStatus.STABLE:
                if record.regression_count == 0:
                    records_to_archive.append(record_id)

        # Archive stable records
        for record_id in records_to_archive:
            await self._archive_record(record_id)
            stats["archived"] += 1

        self.metrics["archived_records"] = sum(
            1 for r in self.active_records.values()
            if r.stability_status == StabilityStatus.ARCHIVED
        )

        return stats

    async def _archive_record(self, record_id: str):
        """Archive a stable record to Ghost Memory."""
        if record_id not in self.active_records:
            return

        record = self.active_records[record_id]

        # Extract patterns before archiving
        patterns = self._extract_patterns(record)

        # Create Ghost Memory entry
        entry = GhostMemoryEntry(
            entry_id=f"GM-{uuid.uuid4().hex[:16]}",
            file_path=record.file_path,
            pattern_type=self._classify_change_pattern(record),
            pattern_hash=self._compute_pattern_hash(record),
            genesis_key_ids=[record.genesis_key_id] if record.genesis_key_id else [],
            learned_at=datetime.utcnow(),
            confidence=record.stability_score,
            pattern_summary=patterns,
            evolution_trend=self._determine_evolution_trend(record)
        )

        # Add genesis keys from line changes
        for lc in record.line_changes:
            if lc.genesis_key_id and lc.genesis_key_id not in entry.genesis_key_ids:
                entry.genesis_key_ids.append(lc.genesis_key_id)

        self.ghost_memory[entry.entry_id] = entry

        # Mark record as archived (keep minimal reference)
        record.stability_status = StabilityStatus.ARCHIVED
        record.line_changes = []  # Clear line-level data
        record.end_time = datetime.utcnow()
        record.metadata["archived_to"] = entry.entry_id

        self.metrics["patterns_learned"] += 1

        logger.info(
            f"[GHOST-LEDGER] Archived record {record_id} to Ghost Memory {entry.entry_id}"
        )

    def _extract_patterns(self, record: GhostRecord) -> Dict[str, Any]:
        """Extract learning patterns from a ghost record."""
        patterns = {
            "total_changes": len(record.line_changes),
            "additions": sum(1 for lc in record.line_changes if lc.change_type == ChangeType.ADDITION),
            "deletions": sum(1 for lc in record.line_changes if lc.change_type == ChangeType.DELETION),
            "modifications": sum(1 for lc in record.line_changes if lc.change_type == ChangeType.MODIFICATION),
            "sources": {},
            "confidence_avg": 0.0,
            "time_span_hours": 0.0
        }

        if record.line_changes:
            # Source distribution
            for lc in record.line_changes:
                patterns["sources"][lc.source] = patterns["sources"].get(lc.source, 0) + 1

            # Average confidence
            patterns["confidence_avg"] = sum(
                lc.confidence for lc in record.line_changes
            ) / len(record.line_changes)

            # Time span
            times = [lc.timestamp for lc in record.line_changes]
            patterns["time_span_hours"] = (max(times) - min(times)).total_seconds() / 3600

        return patterns

    def _classify_change_pattern(self, record: GhostRecord) -> str:
        """Classify the overall pattern type of changes."""
        if not record.line_changes:
            return "unknown"

        additions = sum(1 for lc in record.line_changes if lc.change_type == ChangeType.ADDITION)
        deletions = sum(1 for lc in record.line_changes if lc.change_type == ChangeType.DELETION)
        total = len(record.line_changes)

        if deletions / total > 0.7:
            return "cleanup"
        elif additions / total > 0.7:
            return "feature"
        elif abs(additions - deletions) / total < 0.3:
            return "refactor"
        else:
            return "modification"

    def _compute_pattern_hash(self, record: GhostRecord) -> str:
        """Compute a hash representing the change pattern."""
        pattern_data = {
            "file": record.file_path,
            "changes": len(record.line_changes),
            "types": [lc.change_type.value for lc in record.line_changes[:10]]  # Sample
        }
        return hashlib.sha256(json.dumps(pattern_data, sort_keys=True).encode()).hexdigest()[:16]

    def _determine_evolution_trend(self, record: GhostRecord) -> str:
        """Determine the evolution trend of the record."""
        if record.regression_count > 2:
            return "degrading"
        elif record.stability_score >= 0.9:
            return "improving"
        else:
            return "stable"

    # =========================================================================
    # Regression Detection
    # =========================================================================

    async def report_regression(
        self,
        file_path: str,
        regression_type: str,
        details: Dict[str, Any]
    ):
        """Report a regression in previously stable code."""
        if file_path not in self.file_record_map:
            return

        record_id = self.file_record_map[file_path]
        if record_id not in self.active_records:
            return

        record = self.active_records[record_id]
        record.regression_count += 1
        record.last_regression = datetime.utcnow()
        record.stability_status = StabilityStatus.REGRESSED

        # Store regression details
        if "regressions" not in record.metadata:
            record.metadata["regressions"] = []
        record.metadata["regressions"].append({
            "type": regression_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        })

        self.metrics["regressions_detected"] += 1

        logger.warning(
            f"[GHOST-LEDGER] Regression detected in {file_path}: {regression_type}"
        )

    # =========================================================================
    # Background Learning
    # =========================================================================

    async def extract_learning(self) -> Dict[str, Any]:
        """
        Extract learning from Ghost Memory without entering active cognition.

        Returns patterns, evolution trends, and regression intelligence.
        """
        if not self.enable_background_learning:
            return {"enabled": False}

        learning = {
            "pattern_frequencies": {},
            "evolution_trends": {},
            "regression_patterns": [],
            "high_confidence_patterns": [],
            "file_change_hotspots": {}
        }

        # Analyze ghost memory
        for entry in self.ghost_memory.values():
            # Pattern frequencies
            pattern_type = entry.pattern_type
            learning["pattern_frequencies"][pattern_type] = (
                learning["pattern_frequencies"].get(pattern_type, 0) + 1
            )

            # Evolution trends
            if entry.evolution_trend:
                learning["evolution_trends"][entry.evolution_trend] = (
                    learning["evolution_trends"].get(entry.evolution_trend, 0) + 1
                )

            # High confidence patterns
            if entry.confidence >= 0.9:
                learning["high_confidence_patterns"].append({
                    "file": entry.file_path,
                    "type": entry.pattern_type,
                    "confidence": entry.confidence,
                    "summary": entry.pattern_summary
                })

            # File hotspots
            learning["file_change_hotspots"][entry.file_path] = (
                learning["file_change_hotspots"].get(entry.file_path, 0) + 1
            )

        # Sort hotspots
        learning["file_change_hotspots"] = dict(
            sorted(
                learning["file_change_hotspots"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
        )

        return learning

    # =========================================================================
    # Query Interface
    # =========================================================================

    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get ghost ledger history for a file."""
        history = []

        # Check active records
        for record in self.active_records.values():
            if record.file_path == file_path:
                history.append({
                    "record_id": record.record_id,
                    "type": "active",
                    "start_time": record.start_time.isoformat(),
                    "status": record.stability_status.value,
                    "changes": len(record.line_changes),
                    "stability_score": record.stability_score
                })

        # Check ghost memory
        for entry in self.ghost_memory.values():
            if entry.file_path == file_path:
                history.append({
                    "entry_id": entry.entry_id,
                    "type": "archived",
                    "learned_at": entry.learned_at.isoformat(),
                    "pattern_type": entry.pattern_type,
                    "confidence": entry.confidence,
                    "genesis_keys": len(entry.genesis_key_ids)
                })

        return sorted(history, key=lambda x: x.get("start_time") or x.get("learned_at"), reverse=True)

    def get_recent_changes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent line-level changes across all files."""
        all_changes = []

        for record in self.active_records.values():
            if record.stability_status == StabilityStatus.ARCHIVED:
                continue

            for lc in record.line_changes[-limit:]:
                all_changes.append({
                    "file_path": record.file_path,
                    "line_number": lc.line_number,
                    "change_type": lc.change_type.value,
                    "timestamp": lc.timestamp.isoformat(),
                    "source": lc.source,
                    "confidence": lc.confidence
                })

        # Sort by timestamp and limit
        all_changes.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_changes[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get ghost ledger statistics."""
        return {
            **self.metrics,
            "ghost_memory_entries": len(self.ghost_memory),
            "stability_distribution": {
                status.value: sum(
                    1 for r in self.active_records.values()
                    if r.stability_status == status
                )
                for status in StabilityStatus
            }
        }


class GhostMemory:
    """
    Read-only interface to Ghost Memory for pattern retrieval.

    Used by other systems to learn from historical patterns without
    modifying ghost ledger data.
    """

    def __init__(self, ghost_ledger: GhostLedger):
        self._ledger = ghost_ledger

    def query_patterns(
        self,
        pattern_type: Optional[str] = None,
        file_path: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[GhostMemoryEntry]:
        """Query ghost memory for patterns."""
        results = []

        for entry in self._ledger.ghost_memory.values():
            if pattern_type and entry.pattern_type != pattern_type:
                continue
            if file_path and entry.file_path != file_path:
                continue
            if entry.confidence < min_confidence:
                continue
            results.append(entry)

        return sorted(results, key=lambda x: x.confidence, reverse=True)

    def get_evolution_intelligence(self) -> Dict[str, Any]:
        """Get evolution trend intelligence from ghost memory."""
        trends = {}

        for entry in self._ledger.ghost_memory.values():
            if entry.evolution_trend:
                if entry.evolution_trend not in trends:
                    trends[entry.evolution_trend] = {
                        "count": 0,
                        "files": [],
                        "avg_confidence": 0.0
                    }
                trends[entry.evolution_trend]["count"] += 1
                trends[entry.evolution_trend]["files"].append(entry.file_path)
                trends[entry.evolution_trend]["avg_confidence"] += entry.confidence

        # Calculate averages
        for trend, data in trends.items():
            if data["count"] > 0:
                data["avg_confidence"] /= data["count"]
                data["files"] = list(set(data["files"]))[:10]  # Dedupe and limit

        return trends

    def get_regression_intelligence(self) -> Dict[str, Any]:
        """Get regression pattern intelligence."""
        regressions = {
            "total_regressions": self._ledger.metrics.get("regressions_detected", 0),
            "regressed_records": [],
            "common_regression_files": {}
        }

        for record in self._ledger.active_records.values():
            if record.stability_status == StabilityStatus.REGRESSED:
                regressions["regressed_records"].append({
                    "file": record.file_path,
                    "count": record.regression_count,
                    "last": record.last_regression.isoformat() if record.last_regression else None
                })
                regressions["common_regression_files"][record.file_path] = (
                    regressions["common_regression_files"].get(record.file_path, 0) + 1
                )

        return regressions
