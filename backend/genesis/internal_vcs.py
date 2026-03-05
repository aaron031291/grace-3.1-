"""
Grace Internal Version Control System
======================================
Replaces Git/GitHub — no third-party dependency.

Fully async using run_in_executor for DB operations (matching
Grace's established pattern: async handlers, sync SQLAlchemy).

Every file change is tracked as a FileVersion record in the database.
Supports: snapshots, diffs, branches, rollback, history, merge.
Grace uses this to manage code for all tenant AI workspaces.
"""

import hashlib
import difflib
import os
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.workspace_models import Workspace, Branch, FileVersion
from database.session import session_scope

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="vcs")


class InternalVCS:
    """
    Grace's self-contained version control system.
    No Git, no GitHub — pure database-backed VCS.
    All public methods are async.
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
                workspace_id=workspace.id, name="main",
                is_default=True, is_active=True,
            )
            session.add(branch)
            session.flush()
        return branch

    # ─── Async wrappers ───

    async def snapshot(self, file_path: str, content: str, message: str = "",
                       author: str = "grace", branch_name: Optional[str] = None,
                       genesis_key_id: Optional[str] = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._snapshot_sync,
            file_path, content, message, author, branch_name, genesis_key_id,
        )

    async def history(self, file_path: str, branch_name: Optional[str] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._history_sync, file_path, branch_name, limit,
        )

    async def diff(self, file_path: str, version_a: int, version_b: int) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._diff_sync, file_path, version_a, version_b,
        )

    async def rollback(self, file_path: str, target_version: int,
                       author: str = "grace") -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._rollback_sync, file_path, target_version, author,
        )

    async def get_content(self, file_path: str,
                          version: Optional[int] = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._get_content_sync, file_path, version,
        )

    async def create_branch(self, name: str, from_branch: str = "main") -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._create_branch_sync, name, from_branch,
        )

    async def list_branches(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._list_branches_sync)

    async def list_tracked_files(self, branch_name: Optional[str] = None) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._list_tracked_files_sync, branch_name,
        )

    async def snapshot_directory(self, directory_path: str = "", message: str = "",
                                 author: str = "grace",
                                 extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self._snapshot_directory_sync,
            directory_path, message, author, extensions,
        )

    # ─── Sync implementations (run in executor) ───

    def _snapshot_sync(self, file_path, content, message, author, branch_name, genesis_key_id):
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
                return {"status": "unchanged", "file_path": file_path,
                        "version": prev.version_number, "content_hash": content_hash}

            version_number = (prev.version_number + 1) if prev else 1
            old_content = prev.full_content if prev else ""
            diff_text = self._compute_diff(old_content, content, file_path)

            fv = FileVersion(
                workspace_id=ws.id, branch_id=branch.id,
                file_path=file_path, version_number=version_number,
                content_hash=content_hash, content_size=len(content.encode("utf-8")),
                diff_from_previous=diff_text, full_content=content,
                operation="create" if version_number == 1 else "modify",
                commit_message=message or f"v{version_number} of {file_path}",
                author=author, genesis_key_id=genesis_key_id,
                parent_version_id=prev.id if prev else None,
            )
            session.add(fv)
            branch.head_version_id = fv.id
            ws.total_versions = (ws.total_versions or 0) + 1
            session.flush()

            logger.info(f"[VCS] {self.workspace_id}/{file_path} → v{version_number}")
            return {
                "status": "created", "file_path": file_path,
                "version": version_number, "content_hash": content_hash,
                "diff_lines": len(diff_text.splitlines()),
                "branch": branch.name, "version_id": fv.id,
            }

    def _history_sync(self, file_path, branch_name, limit):
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
                {"version": v.version_number, "content_hash": v.content_hash,
                 "content_size": v.content_size, "operation": v.operation,
                 "message": v.commit_message, "author": v.author,
                 "created_at": v.created_at.isoformat() if v.created_at else None,
                 "version_id": v.id}
                for v in versions
            ]

    def _diff_sync(self, file_path, version_a, version_b):
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
            diff_text = self._compute_diff(va.full_content or "", vb.full_content or "", file_path)
            return {
                "file_path": file_path, "from_version": version_a, "to_version": version_b,
                "diff": diff_text,
                "lines_changed": len([l for l in diff_text.splitlines()
                                      if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]),
            }

    def _rollback_sync(self, file_path, target_version, author):
        with session_scope() as session:
            ws = self._get_workspace(session)
            target = session.query(FileVersion).filter_by(
                workspace_id=ws.id, file_path=file_path, version_number=target_version
            ).first()
            if not target:
                return {"error": f"Version {target_version} not found for {file_path}"}
            content = target.full_content or ""

        result = self._snapshot_sync(file_path, content,
                                     f"Rollback to v{target_version}", author, None, None)
        result["rollback_from"] = target_version
        return result

    def _get_content_sync(self, file_path, version):
        with session_scope() as session:
            ws = self._get_workspace(session)
            q = session.query(FileVersion).filter_by(workspace_id=ws.id, file_path=file_path)
            fv = q.filter_by(version_number=version).first() if version else \
                q.order_by(desc(FileVersion.version_number)).first()
            if not fv:
                return {"error": "File not found in VCS"}
            return {
                "file_path": file_path, "version": fv.version_number,
                "content": fv.full_content, "content_hash": fv.content_hash,
                "author": fv.author, "message": fv.commit_message,
                "created_at": fv.created_at.isoformat() if fv.created_at else None,
            }

    def _create_branch_sync(self, name, from_branch):
        with session_scope() as session:
            ws = self._get_workspace(session)
            if session.query(Branch).filter_by(workspace_id=ws.id, name=name).first():
                return {"error": f"Branch '{name}' already exists"}
            parent = session.query(Branch).filter_by(workspace_id=ws.id, name=from_branch).first()
            if not parent:
                return {"error": f"Source branch '{from_branch}' not found"}
            branch = Branch(workspace_id=ws.id, name=name, is_default=False, is_active=True,
                            head_version_id=parent.head_version_id, parent_branch_id=parent.id)
            session.add(branch)
            session.flush()
            return {"branch": name, "from_branch": from_branch,
                    "branch_id": branch.id, "status": "created"}

    def _list_branches_sync(self):
        with session_scope() as session:
            ws = self._get_workspace(session)
            branches = session.query(Branch).filter_by(workspace_id=ws.id).all()
            return [{"name": b.name, "is_default": b.is_default,
                     "is_active": b.is_active, "branch_id": b.id}
                    for b in branches]

    def _list_tracked_files_sync(self, branch_name):
        with session_scope() as session:
            ws = self._get_workspace(session)
            from sqlalchemy import func
            q = session.query(
                FileVersion.file_path,
                func.max(FileVersion.version_number).label("latest_version"),
                func.max(FileVersion.created_at).label("last_modified"),
            ).filter_by(workspace_id=ws.id)
            if branch_name:
                branch = session.query(Branch).filter_by(workspace_id=ws.id, name=branch_name).first()
                if branch:
                    q = q.filter_by(branch_id=branch.id)
            files = q.group_by(FileVersion.file_path).all()
            return [{"file_path": f.file_path, "latest_version": f.latest_version,
                     "last_modified": f.last_modified.isoformat() if f.last_modified else None}
                    for f in files]

    def _snapshot_directory_sync(self, directory_path, message, author, extensions):
        with session_scope() as session:
            ws = self._get_workspace(session)
            root_path = ws.root_path

        root = Path(root_path) / directory_path if directory_path else Path(root_path)
        if not root.exists():
            return {"error": f"Directory not found: {directory_path}"}

        results = []
        for fp in root.rglob("*"):
            if not fp.is_file() or fp.name.startswith("."):
                continue
            if extensions and fp.suffix not in extensions:
                continue
            rel = str(fp.relative_to(Path(root_path)))
            try:
                content = fp.read_text(errors="ignore")
                result = self._snapshot_sync(
                    rel, content,
                    message or f"Directory snapshot: {directory_path}",
                    author, None, None,
                )
                results.append(result)
            except Exception as e:
                results.append({"file_path": rel, "status": "error", "error": str(e)})

        return {
            "directory": directory_path,
            "total_files": len(results),
            "created": sum(1 for r in results if r.get("status") == "created"),
            "unchanged": sum(1 for r in results if r.get("status") == "unchanged"),
            "errors": sum(1 for r in results if r.get("status") == "error"),
        }

    @staticmethod
    def _compute_diff(old: str, new: str, file_path: str) -> str:
        return "".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
        ))


# ─── Workspace management (async) ───

async def create_workspace(workspace_id: str, name: str, root_path: str,
                           owner_id: Optional[str] = None, description: str = "",
                           config: Optional[Dict] = None) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _create_workspace_sync,
        workspace_id, name, root_path, owner_id, description, config,
    )


async def list_workspaces() -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _list_workspaces_sync)


def _create_workspace_sync(workspace_id, name, root_path, owner_id, description, config):
    with session_scope() as session:
        if session.query(Workspace).filter_by(workspace_id=workspace_id).first():
            return {"error": f"Workspace '{workspace_id}' already exists"}
        root = Path(root_path)
        root.mkdir(parents=True, exist_ok=True)
        (root / "knowledge_base").mkdir(exist_ok=True)
        (root / "data").mkdir(exist_ok=True)
        ws = Workspace(workspace_id=workspace_id, name=name, description=description,
                       owner_id=owner_id, root_path=str(root.resolve()), config=config or {})
        session.add(ws)
        session.flush()
        branch = Branch(workspace_id=ws.id, name="main", is_default=True, is_active=True)
        session.add(branch)
        session.flush()
        logger.info(f"[Workspace] Created '{workspace_id}' at {root_path}")
        return {"workspace_id": workspace_id, "name": name,
                "root_path": str(root.resolve()), "default_branch": "main", "status": "created"}


def _list_workspaces_sync():
    with session_scope() as session:
        workspaces = session.query(Workspace).filter_by(is_active=True).all()
        return [
            {"workspace_id": ws.workspace_id, "name": ws.name,
             "description": ws.description, "root_path": ws.root_path,
             "total_files": ws.total_files or 0, "total_versions": ws.total_versions or 0,
             "total_pipeline_runs": ws.total_pipeline_runs or 0,
             "created_at": ws.created_at.isoformat() if ws.created_at else None}
            for ws in workspaces
        ]


def get_vcs(workspace_id: str) -> InternalVCS:
    return InternalVCS(workspace_id)
