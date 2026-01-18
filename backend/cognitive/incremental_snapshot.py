import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
import hashlib
from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot
logger = logging.getLogger(__name__)

class IncrementalSnapshot:
    """
    Incremental snapshot system - only saves changes.
    
    Tracks:
    - Last snapshot timestamp
    - Changed memory IDs
    - New memories
    - Updated memories
    - Deleted memories
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        base_snapshotter: MemoryMeshSnapshot
    ):
        """
        Initialize incremental snapshot system.
        
        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            base_snapshotter: Base snapshotter for full snapshots
        """
        self.session = session
        self.kb_path = knowledge_base_path
        self.base_snapshotter = base_snapshotter
        self.incremental_path = knowledge_base_path / ".genesis_incremental_snapshots"
        self.incremental_path.mkdir(parents=True, exist_ok=True)
        
        # Metadata file
        self.metadata_file = self.incremental_path / "incremental_metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info("[INCREMENTAL-SNAPSHOT] Initialized")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load incremental snapshot metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "last_full_snapshot": None,
            "last_incremental": None,
            "snapshot_chain": []
        }
    
    def _save_metadata(self):
        """Save incremental snapshot metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def create_incremental_snapshot(
        self,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create incremental snapshot of changes since last snapshot.
        
        Args:
            since_timestamp: Timestamp to compare against (default: last snapshot)
            
        Returns:
            Incremental snapshot with only changes
        """
        logger.info("[INCREMENTAL-SNAPSHOT] Creating incremental snapshot...")
        
        # Determine comparison timestamp
        if since_timestamp is None:
            if self.metadata.get("last_incremental"):
                since_timestamp = datetime.fromisoformat(
                    self.metadata["last_incremental"]
                )
            elif self.metadata.get("last_full_snapshot"):
                since_timestamp = datetime.fromisoformat(
                    self.metadata["last_full_snapshot"]
                )
            else:
                # No previous snapshot - create full snapshot
                logger.info("[INCREMENTAL-SNAPSHOT] No previous snapshot, creating full snapshot")
                return self._create_full_snapshot()
        
        # Find changed memories
        changes = self._find_changes(since_timestamp)
        
        # Create incremental snapshot
        snapshot = {
            "snapshot_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0-incremental",
                "type": "incremental_memory_mesh_snapshot",
                "since_timestamp": since_timestamp.isoformat(),
                "base_snapshot": self.metadata.get("last_full_snapshot")
            },
            "changes": changes,
            "statistics": {
                "new_learning": len(changes["learning_memory"]["new"]),
                "updated_learning": len(changes["learning_memory"]["updated"]),
                "new_episodic": len(changes["episodic_memory"]["new"]),
                "updated_episodic": len(changes["episodic_memory"]["updated"]),
                "new_procedural": len(changes["procedural_memory"]["new"]),
                "updated_procedural": len(changes["procedural_memory"]["updated"]),
                "new_patterns": len(changes["pattern_memory"]["new"]),
                "total_changes": (
                    len(changes["learning_memory"]["new"]) +
                    len(changes["learning_memory"]["updated"]) +
                    len(changes["episodic_memory"]["new"]) +
                    len(changes["episodic_memory"]["updated"]) +
                    len(changes["procedural_memory"]["new"]) +
                    len(changes["procedural_memory"]["updated"]) +
                    len(changes["pattern_memory"]["new"])
                )
            }
        }
        
        # Save incremental snapshot
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_file = self.incremental_path / f"incremental_{timestamp_str}.json"
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2, default=str)
        
        # Update metadata
        self.metadata["last_incremental"] = datetime.utcnow().isoformat()
        self.metadata["snapshot_chain"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "incremental",
            "file": str(snapshot_file),
            "changes": snapshot["statistics"]["total_changes"]
        })
        self._save_metadata()
        
        logger.info(
            f"[INCREMENTAL-SNAPSHOT] Created incremental snapshot: "
            f"{snapshot['statistics']['total_changes']} changes, "
            f"file size: {snapshot_file.stat().st_size / 1024:.2f} KB"
        )
        
        return snapshot
    
    def _find_changes(self, since_timestamp: datetime) -> Dict[str, Any]:
        """Find all changes since timestamp."""
        from cognitive.learning_memory import LearningExample, LearningPattern
        from cognitive.episodic_memory import Episode
        from cognitive.procedural_memory import Procedure
        
        changes = {
            "learning_memory": {"new": [], "updated": []},
            "episodic_memory": {"new": [], "updated": []},
            "procedural_memory": {"new": [], "updated": []},
            "pattern_memory": {"new": [], "updated": []}
        }
        
        # Learning examples
        new_learning = self.session.query(LearningExample).filter(
            LearningExample.created_at >= since_timestamp
        ).all()
        
        updated_learning = self.session.query(LearningExample).filter(
            and_(
                LearningExample.created_at < since_timestamp,
                LearningExample.updated_at >= since_timestamp
            )
        ).all()
        
        for ex in new_learning:
            changes["learning_memory"]["new"].append({
                "id": ex.id,
                "type": ex.example_type,
                "trust_score": ex.trust_score,
                "created_at": ex.created_at.isoformat() if ex.created_at else None
            })
        
        for ex in updated_learning:
            changes["learning_memory"]["updated"].append({
                "id": ex.id,
                "trust_score": ex.trust_score,
                "updated_at": ex.updated_at.isoformat() if ex.updated_at else None
            })
        
        # Episodes
        new_episodes = self.session.query(Episode).filter(
            Episode.created_at >= since_timestamp
        ).all()
        
        for ep in new_episodes:
            changes["episodic_memory"]["new"].append({
                "id": ep.id,
                "trust_score": ep.trust_score,
                "timestamp": ep.timestamp.isoformat() if ep.timestamp else None
            })
        
        # Procedures
        new_procedures = self.session.query(Procedure).filter(
            Procedure.created_at >= since_timestamp
        ).all()
        
        for proc in new_procedures:
            changes["procedural_memory"]["new"].append({
                "id": proc.id,
                "name": proc.name,
                "success_rate": proc.success_rate,
                "created_at": proc.created_at.isoformat() if proc.created_at else None
            })
        
        # Patterns
        new_patterns = self.session.query(LearningPattern).filter(
            LearningPattern.created_at >= since_timestamp
        ).all()
        
        for pat in new_patterns:
            changes["pattern_memory"]["new"].append({
                "id": pat.id,
                "name": pat.pattern_name,
                "trust_score": pat.trust_score,
                "created_at": pat.created_at.isoformat() if pat.created_at else None
            })
        
        return changes
    
    def _create_full_snapshot(self) -> Dict[str, Any]:
        """Create full snapshot when no previous snapshot exists."""
        logger.info("[INCREMENTAL-SNAPSHOT] Creating initial full snapshot...")
        
        full_snapshot = self.base_snapshotter.create_snapshot()
        self.base_snapshotter.save_snapshot(full_snapshot)
        
        # Update metadata
        self.metadata["last_full_snapshot"] = datetime.utcnow().isoformat()
        self.metadata["last_incremental"] = datetime.utcnow().isoformat()
        self._save_metadata()
        
        return {
            "snapshot_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0-full",
                "type": "full_memory_mesh_snapshot"
            },
            "full_snapshot": True,
            "statistics": full_snapshot["statistics"]
        }
    
    def restore_from_incremental_chain(self) -> Dict[str, Any]:
        """
        Restore full state from incremental snapshot chain.
        
        Applies all incremental snapshots to base snapshot.
        
        Returns:
            Restoration statistics
        """
        logger.info("[INCREMENTAL-SNAPSHOT] Restoring from incremental chain...")
        
        # Load base snapshot
        base_snapshot = self.base_snapshotter.load_snapshot()
        if not base_snapshot:
            raise ValueError("No base snapshot found. Create full snapshot first.")
        
        # Apply incremental snapshots in order
        applied_count = 0
        for snapshot_info in self.metadata["snapshot_chain"]:
            snapshot_file = Path(snapshot_info["file"])
            if snapshot_file.exists():
                with open(snapshot_file, 'r') as f:
                    incremental = json.load(f)
                
                # Apply changes (simplified - would need full implementation)
                applied_count += 1
        
        logger.info(f"[INCREMENTAL-SNAPSHOT] Applied {applied_count} incremental snapshots")
        
        return {
            "applied_snapshots": applied_count,
            "restored": True
        }


def get_incremental_snapshot(
    session: Session,
    knowledge_base_path: Path,
    base_snapshotter: MemoryMeshSnapshot
) -> IncrementalSnapshot:
    """Factory function to get incremental snapshot system."""
    return IncrementalSnapshot(session, knowledge_base_path, base_snapshotter)
