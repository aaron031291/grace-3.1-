"""
CI/CD Pipeline Version Control
==============================
Version control for all pipeline mutations.
Tracks every change with Genesis Keys for full audit trail.
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)


class MutationType(str, Enum):
    """Types of pipeline mutations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ENABLE = "enable"
    DISABLE = "disable"
    ROLLBACK = "rollback"


@dataclass
class PipelineVersion:
    """A versioned snapshot of a pipeline configuration."""
    version_id: str
    pipeline_id: str
    version_number: int
    mutation_type: MutationType
    genesis_key: str
    timestamp: str
    author: str
    message: str
    config_hash: str
    config_snapshot: Dict[str, Any]
    previous_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineVersionHistory:
    """Complete version history for a pipeline."""
    pipeline_id: str
    current_version: int
    versions: List[PipelineVersion]
    created_at: str
    updated_at: str


class CICDVersionControl:
    """
    Version control system for CI/CD pipelines.

    Features:
    - Automatic versioning on every mutation
    - Genesis Key tracking for audit trail
    - Rollback to any previous version
    - Diff between versions
    - Full history retention
    """

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or "/tmp/grace-cicd/versions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory version index
        self.version_index: Dict[str, PipelineVersionHistory] = {}

        # Load existing versions
        self._load_versions()

    def _load_versions(self):
        """Load version history from disk."""
        for history_file in self.storage_dir.glob("*/history.json"):
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)
                    pipeline_id = data["pipeline_id"]

                    versions = []
                    for v in data.get("versions", []):
                        versions.append(PipelineVersion(
                            version_id=v["version_id"],
                            pipeline_id=v["pipeline_id"],
                            version_number=v["version_number"],
                            mutation_type=MutationType(v["mutation_type"]),
                            genesis_key=v["genesis_key"],
                            timestamp=v["timestamp"],
                            author=v["author"],
                            message=v["message"],
                            config_hash=v["config_hash"],
                            config_snapshot=v["config_snapshot"],
                            previous_version=v.get("previous_version"),
                            metadata=v.get("metadata", {})
                        ))

                    self.version_index[pipeline_id] = PipelineVersionHistory(
                        pipeline_id=pipeline_id,
                        current_version=data["current_version"],
                        versions=versions,
                        created_at=data["created_at"],
                        updated_at=data["updated_at"]
                    )

                    logger.info(f"[VC] Loaded {len(versions)} versions for pipeline '{pipeline_id}'")

            except Exception as e:
                logger.error(f"[VC] Failed to load version history: {e}")

    def _save_history(self, pipeline_id: str):
        """Save version history to disk."""
        if pipeline_id not in self.version_index:
            return

        history = self.version_index[pipeline_id]
        pipeline_dir = self.storage_dir / pipeline_id
        pipeline_dir.mkdir(parents=True, exist_ok=True)

        history_data = {
            "pipeline_id": history.pipeline_id,
            "current_version": history.current_version,
            "versions": [asdict(v) for v in history.versions],
            "created_at": history.created_at,
            "updated_at": history.updated_at
        }

        with open(pipeline_dir / "history.json", "w") as f:
            json.dump(history_data, f, indent=2, default=str)

        logger.debug(f"[VC] Saved version history for pipeline '{pipeline_id}'")

    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """Compute hash of pipeline configuration."""
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def _generate_version_id(self, pipeline_id: str, version_number: int) -> str:
        """Generate unique version ID."""
        return f"{pipeline_id}-v{version_number}"

    def _generate_genesis_key(self, mutation_type: MutationType, pipeline_id: str, version: int) -> str:
        """Generate Genesis Key for version control operation."""
        timestamp = datetime.now().isoformat()
        key_data = f"cicd:version:{mutation_type.value}:{pipeline_id}:v{version}:{timestamp}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:12]
        return f"gk-vc-{key_hash}"

    def record_mutation(
        self,
        pipeline_id: str,
        mutation_type: MutationType,
        config: Dict[str, Any],
        author: str = "system",
        message: str = ""
    ) -> PipelineVersion:
        """
        Record a pipeline mutation.

        Args:
            pipeline_id: Pipeline identifier
            mutation_type: Type of mutation
            config: Current pipeline configuration
            author: Who made the change
            message: Commit message

        Returns:
            PipelineVersion object
        """
        timestamp = datetime.now().isoformat()
        config_hash = self._compute_hash(config)

        # Get or create history
        if pipeline_id not in self.version_index:
            self.version_index[pipeline_id] = PipelineVersionHistory(
                pipeline_id=pipeline_id,
                current_version=0,
                versions=[],
                created_at=timestamp,
                updated_at=timestamp
            )

        history = self.version_index[pipeline_id]

        # Increment version
        new_version_number = history.current_version + 1
        version_id = self._generate_version_id(pipeline_id, new_version_number)

        # Generate Genesis Key
        genesis_key = self._generate_genesis_key(mutation_type, pipeline_id, new_version_number)

        # Get previous version
        previous_version = None
        if history.versions:
            previous_version = history.versions[-1].version_id

        # Create version record
        version = PipelineVersion(
            version_id=version_id,
            pipeline_id=pipeline_id,
            version_number=new_version_number,
            mutation_type=mutation_type,
            genesis_key=genesis_key,
            timestamp=timestamp,
            author=author,
            message=message or f"{mutation_type.value} pipeline '{pipeline_id}'",
            config_hash=config_hash,
            config_snapshot=config.copy(),
            previous_version=previous_version,
            metadata={
                "mutation_type": mutation_type.value,
                "config_hash": config_hash
            }
        )

        # Update history
        history.versions.append(version)
        history.current_version = new_version_number
        history.updated_at = timestamp

        # Save to disk
        self._save_history(pipeline_id)

        # Also save individual version file
        self._save_version_file(version)

        logger.info(f"[VC] Recorded {mutation_type.value} for pipeline '{pipeline_id}' -> v{new_version_number} ({genesis_key})")

        return version

    def _save_version_file(self, version: PipelineVersion):
        """Save individual version snapshot."""
        version_dir = self.storage_dir / version.pipeline_id / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)

        version_file = version_dir / f"v{version.version_number}.json"
        with open(version_file, "w") as f:
            json.dump(asdict(version), f, indent=2, default=str)

    def get_version(self, pipeline_id: str, version_number: int = None) -> Optional[PipelineVersion]:
        """
        Get a specific version of a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            version_number: Version number (default: latest)

        Returns:
            PipelineVersion or None
        """
        if pipeline_id not in self.version_index:
            return None

        history = self.version_index[pipeline_id]

        if version_number is None:
            return history.versions[-1] if history.versions else None

        for v in history.versions:
            if v.version_number == version_number:
                return v

        return None

    def get_history(self, pipeline_id: str, limit: int = 50) -> List[PipelineVersion]:
        """
        Get version history for a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            limit: Maximum versions to return

        Returns:
            List of PipelineVersion objects (newest first)
        """
        if pipeline_id not in self.version_index:
            return []

        history = self.version_index[pipeline_id]
        return list(reversed(history.versions[-limit:]))

    def get_all_histories(self) -> Dict[str, PipelineVersionHistory]:
        """Get all pipeline version histories."""
        return self.version_index.copy()

    def diff_versions(
        self,
        pipeline_id: str,
        version_a: int,
        version_b: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            version_a: First version number
            version_b: Second version number

        Returns:
            Dict with differences
        """
        v_a = self.get_version(pipeline_id, version_a)
        v_b = self.get_version(pipeline_id, version_b)

        if not v_a or not v_b:
            return {"error": "Version not found"}

        config_a = v_a.config_snapshot
        config_b = v_b.config_snapshot

        # Simple diff - find changed keys
        added = {}
        removed = {}
        modified = {}

        all_keys = set(config_a.keys()) | set(config_b.keys())

        for key in all_keys:
            if key not in config_a:
                added[key] = config_b[key]
            elif key not in config_b:
                removed[key] = config_a[key]
            elif config_a[key] != config_b[key]:
                modified[key] = {
                    "old": config_a[key],
                    "new": config_b[key]
                }

        return {
            "pipeline_id": pipeline_id,
            "version_a": version_a,
            "version_b": version_b,
            "hash_a": v_a.config_hash,
            "hash_b": v_b.config_hash,
            "changes": {
                "added": added,
                "removed": removed,
                "modified": modified
            },
            "has_changes": bool(added or removed or modified)
        }

    def rollback(
        self,
        pipeline_id: str,
        target_version: int,
        author: str = "system"
    ) -> Optional[PipelineVersion]:
        """
        Rollback a pipeline to a previous version.

        Args:
            pipeline_id: Pipeline identifier
            target_version: Version to rollback to
            author: Who performed the rollback

        Returns:
            New PipelineVersion representing the rollback
        """
        target = self.get_version(pipeline_id, target_version)

        if not target:
            logger.error(f"[VC] Cannot rollback: version {target_version} not found for pipeline '{pipeline_id}'")
            return None

        # Create rollback version
        rollback_version = self.record_mutation(
            pipeline_id=pipeline_id,
            mutation_type=MutationType.ROLLBACK,
            config=target.config_snapshot,
            author=author,
            message=f"Rollback to version {target_version}"
        )

        rollback_version.metadata["rollback_target"] = target_version
        rollback_version.metadata["rollback_hash"] = target.config_hash

        # Re-save with metadata
        self._save_history(pipeline_id)
        self._save_version_file(rollback_version)

        logger.info(f"[VC] Rolled back pipeline '{pipeline_id}' to v{target_version}")

        return rollback_version

    def get_genesis_keys(self, pipeline_id: str = None) -> List[Dict[str, Any]]:
        """
        Get Genesis Keys for version control operations.

        Args:
            pipeline_id: Optional filter by pipeline

        Returns:
            List of Genesis Key records
        """
        keys = []

        for pid, history in self.version_index.items():
            if pipeline_id and pid != pipeline_id:
                continue

            for v in history.versions:
                keys.append({
                    "genesis_key": v.genesis_key,
                    "pipeline_id": v.pipeline_id,
                    "version": v.version_number,
                    "mutation_type": v.mutation_type.value,
                    "author": v.author,
                    "timestamp": v.timestamp,
                    "message": v.message
                })

        # Sort by timestamp descending
        keys.sort(key=lambda k: k["timestamp"], reverse=True)

        return keys

    def export_history(self, pipeline_id: str, format: str = "json") -> str:
        """
        Export version history.

        Args:
            pipeline_id: Pipeline identifier
            format: Export format (json, markdown)

        Returns:
            Exported history string
        """
        if pipeline_id not in self.version_index:
            return ""

        history = self.version_index[pipeline_id]

        if format == "markdown":
            lines = [
                f"# Version History: {pipeline_id}",
                "",
                f"**Current Version:** {history.current_version}",
                f"**Created:** {history.created_at}",
                f"**Last Updated:** {history.updated_at}",
                "",
                "## Versions",
                ""
            ]

            for v in reversed(history.versions):
                lines.extend([
                    f"### v{v.version_number} ({v.mutation_type.value})",
                    f"- **Genesis Key:** `{v.genesis_key}`",
                    f"- **Author:** {v.author}",
                    f"- **Timestamp:** {v.timestamp}",
                    f"- **Message:** {v.message}",
                    f"- **Config Hash:** `{v.config_hash}`",
                    ""
                ])

            return "\n".join(lines)

        else:  # json
            return json.dumps({
                "pipeline_id": history.pipeline_id,
                "current_version": history.current_version,
                "created_at": history.created_at,
                "updated_at": history.updated_at,
                "versions": [asdict(v) for v in history.versions]
            }, indent=2, default=str)


# =============================================================================
# Global Instance
# =============================================================================

_version_control: Optional[CICDVersionControl] = None


def get_version_control() -> CICDVersionControl:
    """Get the global version control instance."""
    global _version_control
    if _version_control is None:
        _version_control = CICDVersionControl()
    return _version_control


# =============================================================================
# Integration with CI/CD System
# =============================================================================

def on_pipeline_create(pipeline_id: str, config: Dict[str, Any], author: str = "system"):
    """Hook: Record pipeline creation."""
    vc = get_version_control()
    return vc.record_mutation(pipeline_id, MutationType.CREATE, config, author, "Pipeline created")


def on_pipeline_update(pipeline_id: str, config: Dict[str, Any], author: str = "system", message: str = ""):
    """Hook: Record pipeline update."""
    vc = get_version_control()
    return vc.record_mutation(pipeline_id, MutationType.UPDATE, config, author, message or "Pipeline updated")


def on_pipeline_delete(pipeline_id: str, config: Dict[str, Any], author: str = "system"):
    """Hook: Record pipeline deletion."""
    vc = get_version_control()
    return vc.record_mutation(pipeline_id, MutationType.DELETE, config, author, "Pipeline deleted")
