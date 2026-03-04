"""
Grace Internal Version Control System
======================================
Replaces Git/GitHub — no third-party dependency.

Every file change is tracked as a FileVersion record in the database.
Supports: snapshots, diffs, branches, rollback, history, merge.
Grace uses this to manage code for all tenant AI workspaces.

This is the core engine. It operates on workspace-scoped file trees
and stores everything in Grace's own database.
"""

import hashlib
import difflib
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.workspace_models import Workspace, Branch, FileVersion
from database.session import session_scope

logger = logging.getLogger(__name__)


class InternalVCS:
    """
    Grace's self-contained version control system.
    No Git, no GitHub — pure database-backed VCS.
    """

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id

    def _get_workspace(self, session: Session) -> Workspace:
        ws = session.query(Workspace).filter_by(workspace_id=self.workspace_id).first()
        if not ws:
            raise ValueError(f"Workspace '{self.workspace_id}' not found")
        return ws

    def _get_or_create_default_branch(self, session: Session, workspace: Workspace) -> Branch:
        branch = session.query(Branch).filter_by(
            workspace_id=workspace.id, is_default=True
        ).first()
        if not branch:
            branch = Branch(
                workspace_id=workspace.id,
                name="main",
                is_default=True,
                is_active=True,
            )
            session.add(branch)
            session.flush()
        return branch

    # ─── Snapshot: capture current state of a file ───

    def snapshot(
        self,
        file_path: str,
        content: str,
        message: str = "",
        author: str = "grace",
        branch_name: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a version snapshot of a file.
        Returns the version metadata.
        """
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        with session_scope() as session:
            ws = self._get_workspace(session)

            if branch_name:
                branch = session.query(Branch).filter_by(
                    workspace_id=ws.id, name=branch_name
                ).first()
                if not branch:
                    raise ValueError(f"Branch '{branch_name}' not found")
            else:
                branch = self._get_or_create_default_branch(session, ws)

            prev = (
                session.query(FileVersion)
                .filter_by(workspace_id=ws.id, file_path=file_path, branch_id=branch.id)
                .order_by(desc(FileVersion.version_number))
                .first()
            )

            if prev and prev.content_hash == content_hash:
                return {
                    "status": "unchanged",
                    "file_path": file_path,
                    "version": prev.version_number,
                    "content_hash": content_hash,
                }

            version_number = (prev.version_number + 1) if prev else 1
            old_content = prev.full_content if prev else ""
            diff = self._compute_diff(old_content, content, file_path)

            fv = FileVersion(
                workspace_id=ws.id,
                branch_id=branch.id,
                file_path=file_path,
                version_number=version_number,
                content_hash=content_hash,
                content_size=len(content.encode("utf-8")),
                diff_from_previous=diff,
                full_content=content,
                operation="create" if version_number == 1 else "modify",
                commit_message=message or f"v{version_number} of {file_path}",
                author=author,
                genesis_key_id=genesis_key_id,
                parent_version_id=prev.id if prev else None,
            )
            session.add(fv)

            branch.head_version_id = fv.id
            ws.total_versions = (ws.total_versions or 0) + 1
            session.flush()

            logger.info(f"[VCS] {self.workspace_id}/{file_path} → v{version_number}")

            return {
                "status": "created",
                "file_path": file_path,
                "version": version_number,
                "content_hash": content_hash,
                "diff_lines": len(diff.splitlines()),
                "branch": branch.name,
                "version_id": fv.id,
            }

    # ─── History: get all versions of a file ───

    def history(
        self,
        file_path: str,
        branch_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get version history of a file."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            q = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path
            )
            if branch_name:
                branch = session.query(Branch).filter_by(
                    workspace_id=ws.id, name=branch_name
                ).first()
                if branch:
                    q = q.filter_by(branch_id=branch.id)

            versions = q.order_by(desc(FileVersion.version_number)).limit(limit).all()
            return [
                {
                    "version": v.version_number,
                    "content_hash": v.content_hash,
                    "content_size": v.content_size,
                    "operation": v.operation,
                    "message": v.commit_message,
                    "author": v.author,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "version_id": v.id,
                }
                for v in versions
            ]

    # ─── Diff: compare two versions ───

    def diff(
        self,
        file_path: str,
        version_a: int,
        version_b: int,
        branch_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute diff between two versions of a file."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            va = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path, version_number=version_a
            ).first()
            vb = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path, version_number=version_b
            ).first()

            if not va or not vb:
                return {"error": "Version not found"}

            diff_text = self._compute_diff(
                va.full_content or "", vb.full_content or "", file_path
            )
            return {
                "file_path": file_path,
                "from_version": version_a,
                "to_version": version_b,
                "diff": diff_text,
                "lines_changed": len([l for l in diff_text.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]),
            }

    # ─── Rollback: restore a file to a previous version ───

    def rollback(
        self,
        file_path: str,
        target_version: int,
        author: str = "grace",
    ) -> Dict[str, Any]:
        """Rollback a file to a specific version. Creates a new version with the old content."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            target = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path, version_number=target_version
            ).first()

            if not target:
                return {"error": f"Version {target_version} not found for {file_path}"}

            content = target.full_content or ""

        result = self.snapshot(
            file_path=file_path,
            content=content,
            message=f"Rollback to v{target_version}",
            author=author,
        )
        result["rollback_from"] = target_version
        return result

    # ─── Get content at a specific version ───

    def get_content(
        self,
        file_path: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get file content at a specific version (or latest)."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            q = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path
            )
            if version:
                fv = q.filter_by(version_number=version).first()
            else:
                fv = q.order_by(desc(FileVersion.version_number)).first()

            if not fv:
                return {"error": "File not found in VCS"}

            return {
                "file_path": file_path,
                "version": fv.version_number,
                "content": fv.full_content,
                "content_hash": fv.content_hash,
                "author": fv.author,
                "message": fv.commit_message,
                "created_at": fv.created_at.isoformat() if fv.created_at else None,
            }

    # ─── Branch operations ───

    def create_branch(self, name: str, from_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch from an existing one."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            existing = session.query(Branch).filter_by(
                workspace_id=ws.id, name=name
            ).first()
            if existing:
                return {"error": f"Branch '{name}' already exists"}

            parent = session.query(Branch).filter_by(
                workspace_id=ws.id, name=from_branch
            ).first()
            if not parent:
                return {"error": f"Source branch '{from_branch}' not found"}

            branch = Branch(
                workspace_id=ws.id,
                name=name,
                is_default=False,
                is_active=True,
                head_version_id=parent.head_version_id,
                parent_branch_id=parent.id,
            )
            session.add(branch)
            session.flush()

            return {
                "branch": name,
                "from_branch": from_branch,
                "branch_id": branch.id,
                "status": "created",
            }

    def list_branches(self) -> List[Dict[str, Any]]:
        """List all branches in the workspace."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            branches = session.query(Branch).filter_by(workspace_id=ws.id).all()
            return [
                {
                    "name": b.name,
                    "is_default": b.is_default,
                    "is_active": b.is_active,
                    "branch_id": b.id,
                }
                for b in branches
            ]

    # ─── Workspace file listing ───

    def list_tracked_files(self, branch_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all files tracked in the VCS for this workspace."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            from sqlalchemy import func

            q = session.query(
                FileVersion.file_path,
                func.max(FileVersion.version_number).label("latest_version"),
                func.max(FileVersion.created_at).label("last_modified"),
            ).filter_by(workspace_id=ws.id)

            if branch_name:
                branch = session.query(Branch).filter_by(
                    workspace_id=ws.id, name=branch_name
                ).first()
                if branch:
                    q = q.filter_by(branch_id=branch.id)

            files = q.group_by(FileVersion.file_path).all()
            return [
                {
                    "file_path": f.file_path,
                    "latest_version": f.latest_version,
                    "last_modified": f.last_modified.isoformat() if f.last_modified else None,
                }
                for f in files
            ]

    # ─── Snapshot an entire directory tree ───

    def snapshot_directory(
        self,
        directory_path: str,
        message: str = "",
        author: str = "grace",
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Snapshot all files in a directory into the VCS."""
        with session_scope() as session:
            ws = self._get_workspace(session)

        root = Path(ws.root_path) / directory_path if directory_path else Path(ws.root_path)
        if not root.exists():
            return {"error": f"Directory not found: {directory_path}"}

        results = []
        for fp in root.rglob("*"):
            if not fp.is_file():
                continue
            if fp.name.startswith("."):
                continue
            if extensions and fp.suffix not in extensions:
                continue

            rel = str(fp.relative_to(Path(ws.root_path)))
            try:
                content = fp.read_text(errors="ignore")
                result = self.snapshot(
                    file_path=rel,
                    content=content,
                    message=message or f"Directory snapshot: {directory_path}",
                    author=author,
                )
                results.append(result)
            except Exception as e:
                results.append({"file_path": rel, "status": "error", "error": str(e)})

        created = sum(1 for r in results if r.get("status") == "created")
        unchanged = sum(1 for r in results if r.get("status") == "unchanged")
        errors = sum(1 for r in results if r.get("status") == "error")

        return {
            "directory": directory_path,
            "total_files": len(results),
            "created": created,
            "unchanged": unchanged,
            "errors": errors,
        }

    # ─── Diff helper ───

    @staticmethod
    def _compute_diff(old: str, new: str, file_path: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )


# ─── Workspace management ───

def create_workspace(
    workspace_id: str,
    name: str,
    root_path: str,
    owner_id: Optional[str] = None,
    description: str = "",
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create a new workspace (AI container)."""
    with session_scope() as session:
        existing = session.query(Workspace).filter_by(workspace_id=workspace_id).first()
        if existing:
            return {"error": f"Workspace '{workspace_id}' already exists"}

        root = Path(root_path)
        root.mkdir(parents=True, exist_ok=True)
        (root / "knowledge_base").mkdir(exist_ok=True)
        (root / "data").mkdir(exist_ok=True)

        ws = Workspace(
            workspace_id=workspace_id,
            name=name,
            description=description,
            owner_id=owner_id,
            root_path=str(root.resolve()),
            config=config or {},
        )
        session.add(ws)
        session.flush()

        branch = Branch(
            workspace_id=ws.id,
            name="main",
            is_default=True,
            is_active=True,
        )
        session.add(branch)
        session.flush()

        logger.info(f"[Workspace] Created '{workspace_id}' at {root_path}")
        return {
            "workspace_id": workspace_id,
            "name": name,
            "root_path": str(root.resolve()),
            "default_branch": "main",
            "status": "created",
        }


def list_workspaces() -> List[Dict[str, Any]]:
    """List all workspaces."""
    with session_scope() as session:
        workspaces = session.query(Workspace).filter_by(is_active=True).all()
        return [
            {
                "workspace_id": ws.workspace_id,
                "name": ws.name,
                "description": ws.description,
                "root_path": ws.root_path,
                "total_files": ws.total_files or 0,
                "total_versions": ws.total_versions or 0,
                "total_pipeline_runs": ws.total_pipeline_runs or 0,
                "created_at": ws.created_at.isoformat() if ws.created_at else None,
            }
            for ws in workspaces
        ]


def get_vcs(workspace_id: str) -> InternalVCS:
    """Get the VCS engine for a workspace."""
    return InternalVCS(workspace_id)
