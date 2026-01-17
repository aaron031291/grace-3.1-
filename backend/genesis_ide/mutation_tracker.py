import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import uuid
class Mutation:
    logger = logging.getLogger(__name__)
    """Represents a single mutation (change) to a file."""
    mutation_id: str
    genesis_key_id: str
    file_path: str
    mutation_type: str  # add, modify, delete, rename
    before_hash: str
    after_hash: str
    before_content: Optional[str] = None  # Stored for small files
    after_content: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    parent_mutation_id: Optional[str] = None
    is_reverted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "genesis_key_id": self.genesis_key_id,
            "file_path": self.file_path,
            "mutation_type": self.mutation_type,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "parent_mutation_id": self.parent_mutation_id,
            "is_reverted": self.is_reverted,
            "metadata": self.metadata
        }


class MutationTracker:
    """
    Tracks all file mutations with version control.

    Provides:
    - Mutation-level version control (finer than commits)
    - Genesis Key linking for traceability
    - Rollback capability
    - Mutation history
    """

    def __init__(
        self,
        session=None,
        genesis_service=None,
        git_service=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self._genesis_service = genesis_service
        self._git_service = git_service
        self.repo_path = repo_path or Path.cwd()

        # Mutation storage
        self._mutations: Dict[str, Mutation] = {}
        self._file_mutations: Dict[str, List[str]] = {}  # file_path -> mutation_ids

        # Version tracking
        self._file_versions: Dict[str, int] = {}  # file_path -> current version

        # Metrics
        self.metrics = {
            "mutations_tracked": 0,
            "mutations_reverted": 0,
            "files_tracked": 0
        }

        logger.info("[MUTATION-TRACKER] Initialized")

    async def track_mutation(
        self,
        file_path: str,
        genesis_key_id: Optional[str] = None,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
        mutation_type: str = "modify"
    ) -> Mutation:
        """
        Track a mutation to a file.

        Args:
            file_path: Path to the mutated file
            genesis_key_id: Associated genesis key
            before_content: Content before mutation
            after_content: Content after mutation
            mutation_type: Type of mutation (add, modify, delete, rename)

        Returns:
            Mutation record
        """
        path = Path(file_path)

        # Get content if not provided
        if before_content is None and path.exists():
            # Try to get from git or previous mutation
            before_content = self._get_previous_content(file_path)

        if after_content is None and path.exists():
            try:
                after_content = path.read_text()
            except Exception:
                after_content = ""

        # Calculate hashes
        before_hash = hashlib.sha256((before_content or "").encode()).hexdigest()[:16]
        after_hash = hashlib.sha256((after_content or "").encode()).hexdigest()[:16]

        # Get version
        if file_path not in self._file_versions:
            self._file_versions[file_path] = 0
        self._file_versions[file_path] += 1
        version = self._file_versions[file_path]

        # Get parent mutation
        parent_id = None
        if file_path in self._file_mutations and self._file_mutations[file_path]:
            parent_id = self._file_mutations[file_path][-1]

        # Create mutation record
        mutation = Mutation(
            mutation_id=f"MUT-{uuid.uuid4().hex[:12]}",
            genesis_key_id=genesis_key_id or "",
            file_path=file_path,
            mutation_type=mutation_type,
            before_hash=before_hash,
            after_hash=after_hash,
            before_content=before_content[:1000] if before_content and len(before_content) < 10000 else None,
            after_content=after_content[:1000] if after_content and len(after_content) < 10000 else None,
            version=version,
            parent_mutation_id=parent_id
        )

        # Store mutation
        self._mutations[mutation.mutation_id] = mutation

        if file_path not in self._file_mutations:
            self._file_mutations[file_path] = []
            self.metrics["files_tracked"] += 1
        self._file_mutations[file_path].append(mutation.mutation_id)

        self.metrics["mutations_tracked"] += 1

        # Create genesis key for the mutation
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            self._genesis_service.create_key(
                key_type=GenesisKeyType.MUTATION_TRACKED,
                what_description=f"Mutation {mutation_type}: {path.name}",
                who_actor="MutationTracker",
                where_location=file_path,
                why_reason="File content changed",
                how_method="Content diff tracking",
                file_path=file_path,
                parent_key_id=genesis_key_id,
                context_data={
                    "mutation_id": mutation.mutation_id,
                    "version": version,
                    "before_hash": before_hash,
                    "after_hash": after_hash
                },
                session=self.session
            )

        logger.debug(f"[MUTATION-TRACKER] Tracked mutation {mutation.mutation_id} for {file_path}")

        return mutation

    def _get_previous_content(self, file_path: str) -> Optional[str]:
        """Get previous content from git or mutation history."""
        # Try git
        if self._git_service:
            try:
                return self._git_service.get_file_content_at_head(file_path)
            except Exception:
                pass

        # Try mutation history
        if file_path in self._file_mutations and self._file_mutations[file_path]:
            last_mutation_id = self._file_mutations[file_path][-1]
            if last_mutation_id in self._mutations:
                return self._mutations[last_mutation_id].after_content

        return None

    async def revert_mutation(self, mutation_id: str) -> Dict[str, Any]:
        """
        Revert a mutation to its previous state.

        Returns the result of the reversion.
        """
        if mutation_id not in self._mutations:
            return {"success": False, "error": "Mutation not found"}

        mutation = self._mutations[mutation_id]

        if mutation.is_reverted:
            return {"success": False, "error": "Mutation already reverted"}

        if mutation.before_content is None:
            return {"success": False, "error": "Before content not stored"}

        try:
            # Write back the before content
            path = Path(mutation.file_path)
            path.write_text(mutation.before_content)

            mutation.is_reverted = True
            self.metrics["mutations_reverted"] += 1

            # Track the reversion as a new mutation
            await self.track_mutation(
                file_path=mutation.file_path,
                genesis_key_id=mutation.genesis_key_id,
                before_content=mutation.after_content,
                after_content=mutation.before_content,
                mutation_type="revert"
            )

            return {"success": True, "mutation_id": mutation_id}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_mutation(self, mutation_id: str) -> Optional[Dict[str, Any]]:
        """Get a mutation record."""
        if mutation_id in self._mutations:
            return self._mutations[mutation_id].to_dict()
        return None

    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get mutation history for a file."""
        if file_path not in self._file_mutations:
            return []

        history = []
        for mutation_id in self._file_mutations[file_path]:
            if mutation_id in self._mutations:
                history.append(self._mutations[mutation_id].to_dict())

        return history

    def get_mutation_chain(self, mutation_id: str) -> List[Dict[str, Any]]:
        """Get the chain of mutations leading to this one."""
        chain = []
        current_id = mutation_id

        while current_id:
            if current_id in self._mutations:
                mutation = self._mutations[current_id]
                chain.append(mutation.to_dict())
                current_id = mutation.parent_mutation_id
            else:
                break

        return list(reversed(chain))

    def get_recent_mutations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent mutations across all files."""
        sorted_mutations = sorted(
            self._mutations.values(),
            key=lambda m: m.created_at,
            reverse=True
        )
        return [m.to_dict() for m in sorted_mutations[:limit]]

    def get_mutations_by_genesis_key(self, genesis_key_id: str) -> List[Dict[str, Any]]:
        """Get all mutations linked to a genesis key."""
        return [
            m.to_dict() for m in self._mutations.values()
            if m.genesis_key_id == genesis_key_id
        ]

    def get_version_tree(self, file_path: str) -> Dict[str, Any]:
        """Get version tree visualization for a file."""
        if file_path not in self._file_mutations:
            return {"file": file_path, "versions": []}

        versions = []
        for mutation_id in self._file_mutations[file_path]:
            if mutation_id in self._mutations:
                m = self._mutations[mutation_id]
                versions.append({
                    "version": m.version,
                    "mutation_id": m.mutation_id,
                    "type": m.mutation_type,
                    "timestamp": m.created_at.isoformat(),
                    "is_reverted": m.is_reverted,
                    "hash": m.after_hash
                })

        return {
            "file": file_path,
            "current_version": self._file_versions.get(file_path, 0),
            "versions": versions
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get mutation tracker metrics."""
        return {
            **self.metrics,
            "active_mutations": len(self._mutations),
            "tracked_files": len(self._file_mutations)
        }

    async def sync_with_git(self):
        """Synchronize mutation history with git commits."""
        if not self._git_service:
            return {"error": "Git service not available"}

        # Get recent git commits
        try:
            commits = self._git_service.get_commits(limit=20)

            for commit in commits:
                # Check if we have mutations for files in this commit
                files = commit.get("files", [])
                for file_info in files:
                    file_path = file_info.get("path")
                    if file_path in self._file_mutations:
                        # Link mutations to commit
                        for mutation_id in self._file_mutations[file_path]:
                            if mutation_id in self._mutations:
                                self._mutations[mutation_id].metadata["git_commit"] = commit.get("sha")

            return {"synced": True, "commits_processed": len(commits)}

        except Exception as e:
            return {"error": str(e)}
