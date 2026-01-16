"""
Genesis State Machine Versioning System

Layer 2: Genesis must be versioned as a state machine, not a value.

Features:
- Immutable Genesis snapshots
- Monotonic versioning
- Explicit upgrade paths
- Delta tracking

If Genesis can be overwritten, rolled back implicitly, or merged like code → you lose determinism.

Git must never be the source of truth for Genesis state.
Git is just transport.
"""

import logging
import json
import hashlib
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from enum import Enum

from models.genesis_key_models import GenesisKey, GenesisKeyStatus
from genesis.validation_gate import DeltaType, AuthorityScope, get_validation_gate

logger = logging.getLogger(__name__)


class GenesisVersionState(str, Enum):
    """State of a Genesis version."""
    PENDING = "pending"  # Created but not yet committed
    ACTIVE = "active"  # Active version
    SUPERSEDED = "superseded"  # Replaced by newer version
    REVERTED = "reverted"  # Explicitly reverted
    ARCHIVED = "archived"  # Archived for historical record


class GenesisStateMachine:
    """
    State machine for Genesis versioning.
    
    Every change creates a new Genesis version:
    - Previous versions are never mutated
    - Rollback = explicit reversion event, not overwrite
    - Upgrade paths are explicit and tracked
    """
    
    def __init__(self, session: Session, state_dir: Optional[Path] = None):
        self.session = session
        self.state_dir = state_dir or Path("backend/data/genesis_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Load current state
        self.current_version = self._load_current_version()
        self.version_history: List[Dict[str, Any]] = []
        self._load_version_history()
        
        logger.info(f"[STATE-MACHINE] Initialized with current version: {self.current_version}")
    
    def _load_current_version(self) -> int:
        """Load current Genesis version number."""
        version_file = self.state_dir / "current_version.json"
        
        if not version_file.exists():
            return 0
        
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get("version", 0)
        except Exception as e:
            logger.error(f"[STATE-MACHINE] Failed to load current version: {e}")
            return 0
    
    def _save_current_version(self, version: int):
        """Save current Genesis version number."""
        version_file = self.state_dir / "current_version.json"
        
        data = {
            "version": version,
            "updated_at": datetime.now(UTC).isoformat()
        }
        
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_version_history(self):
        """Load version history."""
        history_file = self.state_dir / "version_history.json"
        
        if not history_file.exists():
            self.version_history = []
            return
        
        try:
            with open(history_file, 'r') as f:
                self.version_history = json.load(f)
        except Exception as e:
            logger.error(f"[STATE-MACHINE] Failed to load version history: {e}")
            self.version_history = []
    
    def _save_version_history(self):
        """Save version history."""
        history_file = self.state_dir / "version_history.json"
        
        with open(history_file, 'w') as f:
            json.dump(self.version_history, f, indent=2)
    
    def create_new_version(
        self,
        key: GenesisKey,
        delta_type: DeltaType,
        constraints_added: Optional[List[str]] = None,
        constraints_removed: Optional[List[str]] = None,
        signed_by: Optional[str] = None,
        upgrade_path: Optional[Dict[str, Any]] = None
    ) -> GenesisKey:
        """
        Create a new immutable Genesis version.
        
        Args:
            key: Genesis key to version
            delta_type: Type of change
            constraints_added: Constraints added in this version
            constraints_removed: Constraints removed in this version
            signed_by: Who signed this version (ROOT, QUORUM, etc.)
            upgrade_path: Explicit upgrade path from previous version
            
        Returns:
            New versioned Genesis key
        """
        # Increment version number (monotonic)
        new_version = self.current_version + 1
        
        # Set version fields
        key.genesis_version = new_version
        key.derived_from_version = self.current_version
        key.delta_type = delta_type.value
        key.constraints_added = constraints_added or []
        key.constraints_removed = constraints_removed or []
        key.signed_by = signed_by or AuthorityScope.SYSTEM.value
        
        # Create explicit upgrade path
        if upgrade_path is None:
            upgrade_path = {
                "from_version": self.current_version,
                "to_version": new_version,
                "delta_type": delta_type.value,
                "upgrade_steps": [
                    {
                        "step": 1,
                        "action": f"Apply {delta_type.value}",
                        "description": f"Upgrade from v{self.current_version} to v{new_version}"
                    }
                ],
                "rollback_supported": True,
                "created_at": datetime.now(UTC).isoformat()
            }
        
        key.upgrade_path = upgrade_path
        
        # Validate before creating version
        validation_gate = get_validation_gate()
        try:
            validation_gate.validate_genesis_key(
                key,
                is_mutation=(self.current_version > 0),
                previous_version=self._get_version(self.current_version) if self.current_version > 0 else None
            )
        except Exception as e:
            logger.error(f"[STATE-MACHINE] Validation failed for version {new_version}: {e}")
            raise
        
        # Create immutable snapshot
        snapshot = self._create_version_snapshot(new_version, key)
        
        # Update current version
        self.current_version = new_version
        self._save_current_version(new_version)
        
        # Add to history
        version_entry = {
            "version": new_version,
            "derived_from": self.current_version - 1,
            "delta_type": delta_type.value,
            "constraints_added": constraints_added or [],
            "constraints_removed": constraints_removed or [],
            "signed_by": signed_by or AuthorityScope.SYSTEM.value,
            "created_at": datetime.now(UTC).isoformat(),
            "snapshot_id": snapshot["snapshot_id"],
            "key_id": key.key_id
        }
        
        self.version_history.append(version_entry)
        self._save_version_history()
        
        logger.info(f"[STATE-MACHINE] Created new Genesis version {new_version} (delta: {delta_type.value})")
        
        return key
    
    def _create_version_snapshot(self, version: int, key: GenesisKey) -> Dict[str, Any]:
        """Create immutable snapshot of Genesis state at this version."""
        snapshot_id = f"GENESIS-v{version}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        snapshot_file = self.state_dir / f"{snapshot_id}.json"
        
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
            "key_id": key.key_id,
            "key_data": {
                "key_id": key.key_id,
                "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
                "status": key.status.value if hasattr(key.status, 'value') else str(key.status),
                "what_description": key.what_description,
                "who_actor": key.who_actor,
                "when_timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None,
                "change_origin": key.change_origin,
                "authority_scope": key.authority_scope,
                "allowed_action_classes": key.allowed_action_classes,
                "forbidden_action_classes": key.forbidden_action_classes,
                "propagation_depth": key.propagation_depth,
                "genesis_version": key.genesis_version,
                "derived_from_version": key.derived_from_version,
                "delta_type": key.delta_type,
                "constraints_added": key.constraints_added,
                "constraints_removed": key.constraints_removed,
                "signed_by": key.signed_by,
                "upgrade_path": key.upgrade_path,
                "required_capabilities": key.required_capabilities,
                "granted_capabilities": key.granted_capabilities,
                "trust_score": key.trust_score,
                "constraint_tags": key.constraint_tags
            },
            "hash": self._compute_snapshot_hash(key)
        }
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        logger.info(f"[STATE-MACHINE] Created snapshot {snapshot_id} for version {version}")
        
        return {
            "snapshot_id": snapshot_id,
            "version": version,
            "file": str(snapshot_file)
        }
    
    def _compute_snapshot_hash(self, key: GenesisKey) -> str:
        """Compute hash of Genesis key state for integrity checking."""
        key_data = {
            "key_id": key.key_id,
            "genesis_version": key.genesis_version,
            "change_origin": key.change_origin,
            "authority_scope": key.authority_scope,
            "allowed_action_classes": key.allowed_action_classes,
            "forbidden_action_classes": key.forbidden_action_classes,
            "propagation_depth": key.propagation_depth
        }
        
        data_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _get_version(self, version: int) -> Optional[GenesisKey]:
        """Get Genesis key for a specific version."""
        # Find version in history
        version_entry = next(
            (v for v in self.version_history if v["version"] == version),
            None
        )
        
        if not version_entry:
            return None
        
        # Load from snapshot
        snapshot_id = version_entry.get("snapshot_id")
        if not snapshot_id:
            return None
        
        snapshot_file = self.state_dir / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            return None
        
        try:
            with open(snapshot_file, 'r') as f:
                snapshot_data = json.load(f)
                key_data = snapshot_data.get("key_data", {})
                
                # Reconstruct key (simplified - in practice would need full model)
                # This is just for validation purposes
                key = GenesisKey()
                for attr, value in key_data.items():
                    if hasattr(key, attr):
                        setattr(key, attr, value)
                
                return key
        except Exception as e:
            logger.error(f"[STATE-MACHINE] Failed to load version {version}: {e}")
            return None
    
    def get_current_version(self) -> int:
        """Get current Genesis version."""
        return self.current_version
    
    def get_version_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get version history."""
        return self.version_history[-limit:]
    
    def rollback_to_version(
        self,
        target_version: int,
        rolled_back_by: str,
        reason: str
    ) -> GenesisKey:
        """
        Explicit rollback to a previous version.
        
        This creates a NEW version that reverts to the target version's state.
        It does NOT overwrite the target version.
        """
        if target_version >= self.current_version:
            raise ValueError(f"Cannot rollback to version {target_version} (current: {self.current_version})")
        
        target_key = self._get_version(target_version)
        if not target_key:
            raise ValueError(f"Version {target_version} not found")
        
        # Create new version that reverts to target state
        rollback_key = GenesisKey(
            key_id=target_key.key_id,  # Same key ID
            what_description=f"Rollback to version {target_version}: {reason}",
            who_actor=rolled_back_by,
            why_reason=reason,
            change_origin="rollback",
            authority_scope=AuthorityScope.USER.value,  # Rollbacks typically require user authority
            allowed_action_classes=target_key.allowed_action_classes,
            forbidden_action_classes=target_key.forbidden_action_classes,
            propagation_depth=0,  # Rollbacks don't propagate
            derived_from_version=self.current_version,
            delta_type=DeltaType.STRUCTURE_CHANGE.value,
            constraints_added=[],
            constraints_removed=[],
            signed_by=rolled_back_by
        )
        
        # Create new version
        return self.create_new_version(
            rollback_key,
            DeltaType.STRUCTURE_CHANGE,
            signed_by=rolled_back_by
        )


def get_state_machine(session: Session, state_dir: Optional[Path] = None) -> GenesisStateMachine:
    """Get or create state machine instance."""
    return GenesisStateMachine(session, state_dir)
