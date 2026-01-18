import logging
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict
from enum import Enum
import gzip
import shutil
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
from genesis.file_version_tracker import get_file_version_tracker
from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot
from cognitive.incremental_snapshot import IncrementalSnapshot
logger = logging.getLogger(__name__)

class VersionControlType(str, Enum):
    """Version control operation types."""
    COMMIT = "commit"
    BRANCH = "branch"
    TAG = "tag"
    MERGE = "merge"
    ROLLBACK = "rollback"
    RELEASE = "release"


class BranchStatus(str, Enum):
    """Branch status."""
    ACTIVE = "active"
    MERGED = "merged"
    ARCHIVED = "archived"
    DELETED = "deleted"


class EnterpriseVersionControl:
    """
    Enterprise-grade version control system.
    
    Features:
    - Branch management
    - Version tagging
    - Rollback capabilities
    - Integrity verification
    - Performance analytics
    - Health monitoring
    """
    
    def __init__(
        self,
        session: Session,
        repository_path: Path,
        knowledge_base_path: Optional[Path] = None
    ):
        """
        Initialize enterprise version control.
        
        Args:
            session: Database session
            repository_path: Path to repository root
            knowledge_base_path: Path to knowledge base (optional)
        """
        self.session = session
        self.repo_path = Path(repository_path)
        self.kb_path = knowledge_base_path or self.repo_path / "knowledge_base"
        
        # Version control metadata
        self.vc_metadata_path = self.repo_path / ".genesis_version_control.json"
        self.branches_path = self.repo_path / ".genesis_branches"
        self.tags_path = self.repo_path / ".genesis_tags"
        self.backups_path = self.repo_path / ".genesis_backups"
        
        # Create directories
        self.branches_path.mkdir(parents=True, exist_ok=True)
        self.tags_path.mkdir(parents=True, exist_ok=True)
        self.backups_path.mkdir(parents=True, exist_ok=True)
        
        # Load metadata
        self.metadata = self._load_metadata()
        
        # Initialize components
        self.file_tracker = get_file_version_tracker(str(self.repo_path))
        
        # Analytics tracking
        self.operation_count = 0
        self.operation_times = []
        self.error_count = 0
        
        logger.info("[ENTERPRISE-VC] Initialized")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load version control metadata."""
        if self.vc_metadata_path.exists():
            with open(self.vc_metadata_path, 'r') as f:
                return json.load(f)
        
        return {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "current_branch": "main",
            "branches": {},
            "tags": {},
            "commits": [],
            "last_commit": None,
            "statistics": {
                "total_commits": 0,
                "total_branches": 0,
                "total_tags": 0,
                "total_merges": 0,
                "total_rollbacks": 0
            }
        }
    
    def _save_metadata(self):
        """Save version control metadata."""
        with open(self.vc_metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    # ==================== BRANCH MANAGEMENT ====================
    
    def create_branch(
        self,
        branch_name: str,
        from_branch: Optional[str] = None,
        user_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the branch
            from_branch: Branch to fork from (default: current)
            user_id: User creating the branch
            description: Branch description
            
        Returns:
            Branch information
        """
        start_time = datetime.utcnow()
        
        try:
            from_branch = from_branch or self.metadata["current_branch"]
            
            if branch_name in self.metadata["branches"]:
                raise ValueError(f"Branch '{branch_name}' already exists")
            
            # Create branch Genesis Key
            branch_key_id = f"BRANCH-{hashlib.md5(branch_name.encode()).hexdigest()[:12]}"
            
            branch_info = {
                "branch_name": branch_name,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": user_id or "system",
                "from_branch": from_branch,
                "status": BranchStatus.ACTIVE.value,
                "description": description,
                "branch_key_id": branch_key_id,
                "commits": [],
                "last_commit": None
            }
            
            self.metadata["branches"][branch_name] = branch_info
            self.metadata["statistics"]["total_branches"] += 1
            self._save_metadata()
            
            # Save branch metadata
            branch_file = self.branches_path / f"{branch_name}.json"
            with open(branch_file, 'w') as f:
                json.dump(branch_info, f, indent=2, default=str)
            
            logger.info(f"[ENTERPRISE-VC] Created branch: {branch_name}")
            
            return branch_info
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"[ENTERPRISE-VC] Failed to create branch: {e}")
            raise
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.operation_times.append(duration)
            self.operation_count += 1
    
    def switch_branch(self, branch_name: str) -> Dict[str, Any]:
        """Switch to a different branch."""
        if branch_name not in self.metadata["branches"]:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        old_branch = self.metadata["current_branch"]
        self.metadata["current_branch"] = branch_name
        self._save_metadata()
        
        logger.info(f"[ENTERPRISE-VC] Switched from {old_branch} to {branch_name}")
        
        return {
            "previous_branch": old_branch,
            "current_branch": branch_name,
            "branch_info": self.metadata["branches"][branch_name]
        }
    
    def list_branches(self) -> List[Dict[str, Any]]:
        """List all branches."""
        return list(self.metadata["branches"].values())
    
    def delete_branch(
        self,
        branch_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a branch.
        
        Args:
            branch_name: Branch to delete
            force: Force deletion even if unmerged
        """
        if branch_name not in self.metadata["branches"]:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        if branch_name == self.metadata["current_branch"]:
            raise ValueError("Cannot delete current branch")
        
        branch_info = self.metadata["branches"][branch_name]
        
        if branch_info["status"] != BranchStatus.MERGED.value and not force:
            raise ValueError("Cannot delete unmerged branch (use force=True)")
        
        # Archive instead of delete
        branch_info["status"] = BranchStatus.ARCHIVED.value
        branch_info["deleted_at"] = datetime.utcnow().isoformat()
        
        # Remove from active branches but keep in metadata
        del self.metadata["branches"][branch_name]
        
        # Archive branch file
        branch_file = self.branches_path / f"{branch_name}.json"
        if branch_file.exists():
            archive_file = self.branches_path / f"{branch_name}.archived.json"
            shutil.move(branch_file, archive_file)
        
        self._save_metadata()
        
        logger.info(f"[ENTERPRISE-VC] Deleted branch: {branch_name}")
        
        return {"branch": branch_name, "status": "deleted"}
    
    # ==================== VERSION TAGGING ====================
    
    def create_tag(
        self,
        tag_name: str,
        commit_ref: Optional[str] = None,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        is_release: bool = False
    ) -> Dict[str, Any]:
        """
        Create a version tag.
        
        Args:
            tag_name: Tag name (e.g., "v1.0.0")
            commit_ref: Commit reference (default: last commit)
            user_id: User creating the tag
            description: Tag description
            is_release: Whether this is a release tag
        """
        commit_ref = commit_ref or self.metadata.get("last_commit")
        
        tag_info = {
            "tag_name": tag_name,
            "commit_ref": commit_ref,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id or "system",
            "description": description,
            "is_release": is_release,
            "tag_key_id": f"TAG-{hashlib.md5(tag_name.encode()).hexdigest()[:12]}"
        }
        
        self.metadata["tags"][tag_name] = tag_info
        self.metadata["statistics"]["total_tags"] += 1
        self._save_metadata()
        
        # Save tag file
        tag_file = self.tags_path / f"{tag_name}.json"
        with open(tag_file, 'w') as f:
            json.dump(tag_info, f, indent=2, default=str)
        
        logger.info(f"[ENTERPRISE-VC] Created tag: {tag_name}")
        
        return tag_info
    
    def list_tags(self) -> List[Dict[str, Any]]:
        """List all tags."""
        return list(self.metadata["tags"].values())
    
    # ==================== COMMITS ====================
    
    def create_commit(
        self,
        message: str,
        user_id: Optional[str] = None,
        files: Optional[List[str]] = None,
        create_snapshot: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new commit.
        
        Args:
            message: Commit message
            user_id: User making the commit
            files: List of files to commit (None = all changed)
            create_snapshot: Whether to create a memory snapshot
            
        Returns:
            Commit information
        """
        start_time = datetime.utcnow()
        
        try:
            commit_sha = hashlib.sha256(
                f"{datetime.utcnow().isoformat()}{message}".encode()
            ).hexdigest()[:12]
            
            commit_info = {
                "sha": commit_sha,
                "message": message,
                "author": user_id or "system",
                "timestamp": datetime.utcnow().isoformat(),
                "branch": self.metadata["current_branch"],
                "parent_sha": self.metadata.get("last_commit"),
                "files": files or [],
                "snapshot_created": False
            }
            
            # Create memory snapshot if requested
            if create_snapshot:
                try:
                    snapshotter = MemoryMeshSnapshot(
                        self.session,
                        self.kb_path
                    )
                    snapshot = snapshotter.create_snapshot()
                    commit_info["snapshot"] = snapshot["snapshot_metadata"]
                    commit_info["snapshot_created"] = True
                except Exception as e:
                    logger.warning(f"[ENTERPRISE-VC] Snapshot creation failed: {e}")
            
            # Update metadata
            self.metadata["commits"].append(commit_info)
            self.metadata["last_commit"] = commit_sha
            self.metadata["statistics"]["total_commits"] += 1
            
            # Update branch
            branch_name = self.metadata["current_branch"]
            if branch_name in self.metadata["branches"]:
                self.metadata["branches"][branch_name]["commits"].append(commit_sha)
                self.metadata["branches"][branch_name]["last_commit"] = commit_sha
            
            self._save_metadata()
            
            logger.info(f"[ENTERPRISE-VC] Created commit: {commit_sha[:8]}")
            
            return commit_info
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"[ENTERPRISE-VC] Failed to create commit: {e}")
            raise
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.operation_times.append(duration)
            self.operation_count += 1
    
    def get_commit_history(
        self,
        branch: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get commit history."""
        branch = branch or self.metadata["current_branch"]
        
        if branch and branch in self.metadata["branches"]:
            branch_commits = self.metadata["branches"][branch]["commits"]
            commits = [
                c for c in self.metadata["commits"]
                if c["sha"] in branch_commits
            ]
        else:
            commits = self.metadata["commits"]
        
        return commits[-limit:]
    
    # ==================== ROLLBACK ====================
    
    def rollback_to_commit(
        self,
        commit_sha: str,
        create_backup: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback to a specific commit.
        
        Args:
            commit_sha: Commit SHA to rollback to
            create_backup: Whether to create backup before rollback
            user_id: User performing rollback
        """
        # Find commit
        commit = next(
            (c for c in self.metadata["commits"] if c["sha"] == commit_sha),
            None
        )
        
        if not commit:
            raise ValueError(f"Commit {commit_sha} not found")
        
        # Create backup
        if create_backup:
            backup_info = self._create_backup("rollback_backup", user_id)
        
        # Update metadata
        rollback_info = {
            "rollback_to": commit_sha,
            "previous_commit": self.metadata.get("last_commit"),
            "rollback_at": datetime.utcnow().isoformat(),
            "rolled_back_by": user_id or "system",
            "backup_created": create_backup
        }
        
        if create_backup:
            rollback_info["backup"] = backup_info
        
        self.metadata["last_commit"] = commit_sha
        self.metadata["statistics"]["total_rollbacks"] += 1
        self._save_metadata()
        
        logger.info(f"[ENTERPRISE-VC] Rolled back to commit: {commit_sha[:8]}")
        
        return rollback_info
    
    def _create_backup(
        self,
        backup_name: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a backup before destructive operation."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backups_path / f"{backup_name}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy metadata
        shutil.copy(self.vc_metadata_path, backup_dir / "metadata.json")
        
        # Create compressed snapshot
        try:
            snapshotter = MemoryMeshSnapshot(self.session, self.kb_path)
            snapshot = snapshotter.create_snapshot()
            
            snapshot_file = backup_dir / "memory_snapshot.json.gz"
            with gzip.open(snapshot_file, 'wt') as f:
                json.dump(snapshot, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[ENTERPRISE-VC] Snapshot backup failed: {e}")
        
        backup_info = {
            "backup_name": backup_name,
            "backup_path": str(backup_dir),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id or "system"
        }
        
        return backup_info
    
    # ==================== MERGING ====================
    
    def merge_branch(
        self,
        source_branch: str,
        target_branch: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge a branch into target branch.
        
        Args:
            source_branch: Branch to merge from
            target_branch: Branch to merge into (default: current)
            user_id: User performing merge
            message: Merge commit message
        """
        target_branch = target_branch or self.metadata["current_branch"]
        
        if source_branch not in self.metadata["branches"]:
            raise ValueError(f"Source branch '{source_branch}' does not exist")
        
        if target_branch not in self.metadata["branches"]:
            raise ValueError(f"Target branch '{target_branch}' does not exist")
        
        source_commits = self.metadata["branches"][source_branch]["commits"]
        target_commits = self.metadata["branches"][target_branch]["commits"]
        
        # Find commits to merge
        commits_to_merge = [
            c for c in source_commits
            if c not in target_commits
        ]
        
        # Create merge commit
        merge_message = message or f"Merge branch '{source_branch}' into '{target_branch}'"
        merge_commit = self.create_commit(
            message=merge_message,
            user_id=user_id,
            create_snapshot=False
        )
        
        # Update branches
        self.metadata["branches"][target_branch]["commits"].extend(commits_to_merge)
        self.metadata["branches"][target_branch]["commits"].append(merge_commit["sha"])
        self.metadata["branches"][target_branch]["last_commit"] = merge_commit["sha"]
        self.metadata["branches"][source_branch]["status"] = BranchStatus.MERGED.value
        
        self.metadata["statistics"]["total_merges"] += 1
        self._save_metadata()
        
        merge_info = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "merge_commit": merge_commit["sha"],
            "commits_merged": len(commits_to_merge),
            "merged_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[ENTERPRISE-VC] Merged {source_branch} into {target_branch}")
        
        return merge_info
    
    # ==================== ANALYTICS & HEALTH ====================
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get version control analytics."""
        avg_time = (
            sum(self.operation_times) / len(self.operation_times)
            if self.operation_times else 0
        )
        
        return {
            "operations": {
                "total": self.operation_count,
                "average_time_seconds": avg_time,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(self.operation_count, 1)
            },
            "statistics": self.metadata["statistics"],
            "branches": {
                "total": len(self.metadata["branches"]),
                "active": sum(
                    1 for b in self.metadata["branches"].values()
                    if b["status"] == BranchStatus.ACTIVE.value
                )
            },
            "tags": {
                "total": len(self.metadata["tags"]),
                "releases": sum(
                    1 for t in self.metadata["tags"].values()
                    if t.get("is_release", False)
                )
            }
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get version control health metrics."""
        error_rate = self.error_count / max(self.operation_count, 1)
        
        health_score = 1.0
        if error_rate > 0.1:
            health_score = 0.5
        elif error_rate > 0.05:
            health_score = 0.75
        
        return {
            "health_score": health_score,
            "health_status": (
                "excellent" if health_score >= 0.9 else
                "good" if health_score >= 0.7 else
                "fair" if health_score >= 0.5 else
                "poor"
            ),
            "error_rate": error_rate,
            "operation_count": self.operation_count,
            "last_commit": self.metadata.get("last_commit"),
            "current_branch": self.metadata["current_branch"]
        }
    
    # ==================== INTEGRITY VERIFICATION ====================
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify version control integrity."""
        issues = []
        
        # Check commit chain
        commits = self.metadata["commits"]
        for i, commit in enumerate(commits[1:], 1):
            if commit.get("parent_sha") != commits[i-1]["sha"]:
                issues.append(f"Commit chain broken at {commit['sha']}")
        
        # Check branch references
        for branch_name, branch_info in self.metadata["branches"].items():
            for commit_sha in branch_info["commits"]:
                if not any(c["sha"] == commit_sha for c in commits):
                    issues.append(f"Branch {branch_name} references missing commit {commit_sha}")
        
        return {
            "integrity_verified": len(issues) == 0,
            "issues": issues,
            "issue_count": len(issues),
            "verified_at": datetime.utcnow().isoformat()
        }


def get_enterprise_version_control(
    session: Session,
    repository_path: Path,
    knowledge_base_path: Optional[Path] = None
) -> EnterpriseVersionControl:
    """Factory function to get enterprise version control instance."""
    return EnterpriseVersionControl(session, repository_path, knowledge_base_path)
