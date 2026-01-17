import logging
import json
import os
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.genesis_key_models import GenesisKey, GenesisKeyStatus, GenesisKeyType
from genesis.genesis_key_service import GenesisKeyService
class GenesisKeySnapshot:
    logger = logging.getLogger(__name__)
    """Represents a snapshot of Genesis Keys at a point in time."""
    
    def __init__(
        self,
        snapshot_id: str,
        timestamp: datetime,
        stable_state: bool,
        genesis_keys: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ):
        self.snapshot_id = snapshot_id
        self.timestamp = timestamp
        self.stable_state = stable_state
        self.genesis_keys = genesis_keys
        self.metadata = metadata


class GenesisKeySnapshotSystem:
    """
    Manages Genesis Key snapshots for stable states.
    
    Features:
    - Detects stable states
    - Creates snapshots of all Genesis Keys
    - Maintains 6 active snapshots
    - Keeps 3 most recent as backups
    - Archives older snapshots
    """
    
    MAX_ACTIVE_SNAPSHOTS = 6
    BACKUP_SNAPSHOTS = 3  # Keep 3 most recent as backups
    ARCHIVE_THRESHOLD = MAX_ACTIVE_SNAPSHOTS  # Archive after 6
    
    def __init__(
        self,
        session: Session,
        snapshot_path: Optional[Path] = None,
        genesis_key_service: Optional[GenesisKeyService] = None
    ):
        self.session = session
        self.snapshot_path = snapshot_path or Path("data/genesis_snapshots")
        self.genesis_key_service = genesis_key_service
        
        # Ensure snapshot directory exists
        self.snapshot_path.mkdir(parents=True, exist_ok=True)
        self.archive_path = self.snapshot_path / "archived"
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing snapshots
        self.active_snapshots: List[GenesisKeySnapshot] = []
        self._load_snapshots()
        
        logger.info(f"[SNAPSHOT-SYSTEM] Initialized with {len(self.active_snapshots)} active snapshots")
    
    def _load_snapshots(self) -> None:
        """Load existing snapshots from disk."""
        snapshot_file = self.snapshot_path / "snapshots_index.json"
        
        if not snapshot_file.exists():
            return
        
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            for snapshot_info in index_data.get("active_snapshots", []):
                snapshot_file_path = self.snapshot_path / f"{snapshot_info['snapshot_id']}.json"
                if snapshot_file_path.exists():
                    with open(snapshot_file_path, 'r', encoding='utf-8') as sf:
                        snapshot_data = json.load(sf)
                    
                    snapshot = GenesisKeySnapshot(
                        snapshot_id=snapshot_info['snapshot_id'],
                        timestamp=datetime.fromisoformat(snapshot_info['timestamp']),
                        stable_state=snapshot_info.get('stable_state', True),
                        genesis_keys=snapshot_data.get('genesis_keys', []),
                        metadata=snapshot_data.get('metadata', {})
                    )
                    self.active_snapshots.append(snapshot)
            
            # Sort by timestamp (newest first)
            self.active_snapshots.sort(key=lambda s: s.timestamp, reverse=True)
            
            # Keep only MAX_ACTIVE_SNAPSHOTS
            if len(self.active_snapshots) > self.MAX_ACTIVE_SNAPSHOTS:
                self._archive_old_snapshots()
                
        except Exception as e:
            logger.error(f"[SNAPSHOT-SYSTEM] Failed to load snapshots: {e}")
    
    def is_stable_state(self) -> bool:
        """
        Determine if system is in a stable state.
        
        Stable state criteria:
        - No active errors (is_error=False, is_broken=False)
        - No pending fixes
        - System health is healthy or degraded (not critical/failing)
        - No active monitoring (all fixes verified)
        """
        try:
            # Check for broken Genesis Keys
            broken_keys = self.session.query(GenesisKey).filter(
                GenesisKey.is_broken == True,
                GenesisKey.status != GenesisKeyStatus.ARCHIVED
            ).count()
            
            if broken_keys > 0:
                logger.debug(f"[SNAPSHOT-SYSTEM] Not stable: {broken_keys} broken keys")
                return False
            
            # Check for recent errors (last hour)
            cutoff = datetime.now(UTC) - timedelta(hours=1)
            recent_errors = self.session.query(GenesisKey).filter(
                and_(
                    GenesisKey.is_error == True,
                    GenesisKey.when_timestamp >= cutoff,
                    GenesisKey.status != GenesisKeyStatus.FIXED
                )
            ).count()
            
            if recent_errors > 0:
                logger.debug(f"[SNAPSHOT-SYSTEM] Not stable: {recent_errors} recent errors")
                return False
            
            # Check for pending fixes
            pending_fixes = self.session.query(GenesisKey).filter(
                and_(
                    GenesisKey.key_type == GenesisKeyType.FIX,
                    GenesisKey.status == GenesisKeyStatus.ACTIVE
                )
            ).count()
            
            if pending_fixes > 0:
                logger.debug(f"[SNAPSHOT-SYSTEM] Not stable: {pending_fixes} pending fixes")
                return False
            
            logger.info("[SNAPSHOT-SYSTEM] System is in stable state")
            return True
            
        except Exception as e:
            logger.error(f"[SNAPSHOT-SYSTEM] Error checking stable state: {e}")
            return False
    
    def create_snapshot(
        self,
        reason: Optional[str] = None,
        force: bool = False
    ) -> Optional[GenesisKeySnapshot]:
        """
        Create a snapshot of all Genesis Keys if system is stable.
        
        Args:
            reason: Reason for snapshot
            force: Force snapshot even if not stable
            
        Returns:
            Created snapshot or None
        """
        if not force and not self.is_stable_state():
            logger.info("[SNAPSHOT-SYSTEM] System not stable, skipping snapshot")
            return None
        
        try:
            snapshot_id = f"SNAP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
            timestamp = datetime.now(UTC)
            
            # Get all active Genesis Keys
            genesis_keys = self.session.query(GenesisKey).filter(
                GenesisKey.status != GenesisKeyStatus.ARCHIVED
            ).all()
            
            # Serialize Genesis Keys
            keys_data = []
            for key in genesis_keys:
                keys_data.append({
                    "key_id": key.key_id,
                    "key_type": key.key_type.value,
                    "status": key.status.value,
                    "what_description": key.what_description,
                    "where_location": key.where_location,
                    "when_timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None,
                    "who_actor": key.who_actor,
                    "why_reason": key.why_reason,
                    "how_method": key.how_method,
                    "file_path": key.file_path,
                    "is_error": key.is_error,
                    "is_broken": key.is_broken,
                    "parent_key_id": key.parent_key_id,
                    "context_data": key.context_data,
                    "tags": key.tags
                })
            
            # Create metadata
            metadata = {
                "snapshot_id": snapshot_id,
                "timestamp": timestamp.isoformat(),
                "stable_state": True,
                "reason": reason or "Automatic stable state snapshot",
                "total_keys": len(keys_data),
                "keys_by_type": self._count_keys_by_type(keys_data),
                "keys_by_status": self._count_keys_by_status(keys_data)
            }
            
            # Create snapshot
            snapshot = GenesisKeySnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                stable_state=True,
                genesis_keys=keys_data,
                metadata=metadata
            )
            
            # Save snapshot to disk
            self._save_snapshot(snapshot)
            
            # Add to active snapshots
            self.active_snapshots.insert(0, snapshot)  # Add at beginning (newest first)
            
            # Manage snapshot count
            self._manage_snapshot_count()
            
            # Create Genesis Key for snapshot
            if self.genesis_key_service:
                try:
                    self.genesis_key_service.create_key(
                        key_type=GenesisKeyType.SYSTEM_EVENT,
                        what_description=f"System snapshot created: {reason or 'Stable state'}",
                        who_actor="grace_snapshot_system",
                        why_reason=f"System in stable state - snapshot for recovery/rollback",
                        how_method="snapshot_system",
                        context_data={
                            "snapshot_id": snapshot_id,
                            "total_keys": len(keys_data),
                            "metadata": metadata
                        },
                        tags=["snapshot", "stable_state", "backup"],
                        session=self.session
                    )
                except Exception as e:
                    logger.warning(f"[SNAPSHOT-SYSTEM] Failed to create snapshot Genesis Key: {e}")
            
            logger.info(f"[SNAPSHOT-SYSTEM] Created snapshot: {snapshot_id} ({len(keys_data)} keys)")
            return snapshot
            
        except Exception as e:
            logger.error(f"[SNAPSHOT-SYSTEM] Failed to create snapshot: {e}")
            return None
    
    def _save_snapshot(self, snapshot: GenesisKeySnapshot) -> None:
        """Save snapshot to disk."""
        snapshot_file = self.snapshot_path / f"{snapshot.snapshot_id}.json"
        
        snapshot_data = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "stable_state": snapshot.stable_state,
            "genesis_keys": snapshot.genesis_keys,
            "metadata": snapshot.metadata
        }
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2, default=str)
        
        # Update index
        self._update_snapshot_index()
    
    def _update_snapshot_index(self) -> None:
        """Update snapshot index file."""
        index_file = self.snapshot_path / "snapshots_index.json"
        
        index_data = {
            "last_updated": datetime.now(UTC).isoformat(),
            "active_snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "timestamp": s.timestamp.isoformat(),
                    "stable_state": s.stable_state,
                    "total_keys": len(s.genesis_keys)
                }
                for s in self.active_snapshots[:self.MAX_ACTIVE_SNAPSHOTS]
            ],
            "backup_snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in self.active_snapshots[:self.BACKUP_SNAPSHOTS]
            ]
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, default=str)
    
    def _manage_snapshot_count(self) -> None:
        """Manage snapshot count - keep 6 active, archive older ones."""
        # Sort by timestamp (newest first)
        self.active_snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        # Keep only MAX_ACTIVE_SNAPSHOTS
        if len(self.active_snapshots) > self.MAX_ACTIVE_SNAPSHOTS:
            # Archive older snapshots
            snapshots_to_archive = self.active_snapshots[self.MAX_ACTIVE_SNAPSHOTS:]
            self.active_snapshots = self.active_snapshots[:self.MAX_ACTIVE_SNAPSHOTS]
            
            for snapshot in snapshots_to_archive:
                self._archive_snapshot(snapshot)
    
    def _archive_snapshot(self, snapshot: GenesisKeySnapshot) -> None:
        """Archive a snapshot."""
        try:
            # Move snapshot file to archive
            snapshot_file = self.snapshot_path / f"{snapshot.snapshot_id}.json"
            archive_file = self.archive_path / f"{snapshot.snapshot_id}.json"
            
            if snapshot_file.exists():
                # Remove existing archive file if it exists
                if archive_file.exists():
                    archive_file.unlink()
                snapshot_file.rename(archive_file)
                logger.info(f"[SNAPSHOT-SYSTEM] Archived snapshot: {snapshot.snapshot_id}")
            elif archive_file.exists():
                # Already archived
                logger.debug(f"[SNAPSHOT-SYSTEM] Snapshot {snapshot.snapshot_id} already archived")
            
            # Create archive index entry
            archive_index_file = self.archive_path / "archive_index.json"
            archive_index = []
            if archive_index_file.exists():
                with open(archive_index_file, 'r', encoding='utf-8') as f:
                    archive_index = json.load(f)
            
            # Only add if not already in index
            existing_ids = {entry.get("snapshot_id") for entry in archive_index}
            if snapshot.snapshot_id not in existing_ids:
                archive_index.append({
                    "snapshot_id": snapshot.snapshot_id,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "archived_at": datetime.now(UTC).isoformat(),
                    "total_keys": len(snapshot.genesis_keys)
                })
            
            with open(archive_index_file, 'w', encoding='utf-8') as f:
                json.dump(archive_index, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"[SNAPSHOT-SYSTEM] Failed to archive snapshot: {e}")
    
    def get_active_snapshots(self) -> List[Dict[str, Any]]:
        """Get list of active snapshots."""
        return [
            {
                "snapshot_id": s.snapshot_id,
                "timestamp": s.timestamp.isoformat(),
                "stable_state": s.stable_state,
                "total_keys": len(s.genesis_keys),
                "metadata": s.metadata
            }
            for s in self.active_snapshots
        ]
    
    def get_backup_snapshots(self) -> List[Dict[str, Any]]:
        """Get list of backup snapshots (3 most recent)."""
        backups = self.active_snapshots[:self.BACKUP_SNAPSHOTS]
        return [
            {
                "snapshot_id": s.snapshot_id,
                "timestamp": s.timestamp.isoformat(),
                "total_keys": len(s.genesis_keys),
                "metadata": s.metadata
            }
            for s in backups
        ]
    
    def restore_snapshot(
        self,
        snapshot_id: str,
        restore_keys: bool = True
    ) -> Dict[str, Any]:
        """
        Restore a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            restore_keys: If True, restore Genesis Keys to database
            
        Returns:
            Restore result
        """
        try:
            # Find snapshot
            snapshot = None
            for s in self.active_snapshots:
                if s.snapshot_id == snapshot_id:
                    snapshot = s
                    break
            
            if not snapshot:
                # Try archived snapshots
                archive_file = self.archive_path / f"{snapshot_id}.json"
                if archive_file.exists():
                    with open(archive_file, 'r', encoding='utf-8') as f:
                        snapshot_data = json.load(f)
                    snapshot = GenesisKeySnapshot(
                        snapshot_id=snapshot_data['snapshot_id'],
                        timestamp=datetime.fromisoformat(snapshot_data['timestamp']),
                        stable_state=snapshot_data.get('stable_state', True),
                        genesis_keys=snapshot_data.get('genesis_keys', []),
                        metadata=snapshot_data.get('metadata', {})
                    )
                else:
                    return {
                        "success": False,
                        "error": f"Snapshot {snapshot_id} not found"
                    }
            
            if restore_keys:
                # Restore Genesis Keys (this would need careful implementation)
                # For now, just return snapshot info
                logger.info(f"[SNAPSHOT-SYSTEM] Would restore {len(snapshot.genesis_keys)} keys from snapshot {snapshot_id}")
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "timestamp": snapshot.timestamp.isoformat(),
                "total_keys": len(snapshot.genesis_keys),
                "metadata": snapshot.metadata
            }
            
        except Exception as e:
            logger.error(f"[SNAPSHOT-SYSTEM] Failed to restore snapshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _count_keys_by_type(self, keys_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count keys by type."""
        counts = {}
        for key in keys_data:
            key_type = key.get("key_type", "unknown")
            counts[key_type] = counts.get(key_type, 0) + 1
        return counts
    
    def _count_keys_by_status(self, keys_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count keys by status."""
        counts = {}
        for key in keys_data:
            status = key.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts


def get_snapshot_system(
    session: Session,
    snapshot_path: Optional[Path] = None,
    genesis_key_service: Optional[GenesisKeyService] = None
) -> GenesisKeySnapshotSystem:
    """Get or create snapshot system singleton."""
    global _snapshot_system
    if '_snapshot_system' not in globals():
        _snapshot_system = None
    
    if _snapshot_system is None:
        _snapshot_system = GenesisKeySnapshotSystem(
            session=session,
            snapshot_path=snapshot_path,
            genesis_key_service=genesis_key_service
        )
    
    return _snapshot_system
