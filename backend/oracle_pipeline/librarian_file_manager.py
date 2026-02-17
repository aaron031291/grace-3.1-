"""
Librarian File Management System

Grace's librarian is fully in charge of the file system -- like Windows 98
Explorer but for an AI codebase. She sorts, names, creates, moves, and
organizes ALL files, folders, and subdirectories.

Two separate trees:
  /codebase/   - All code files (scripts, modules, configs)
  /documents/  - All documents (research, notes, uploads, reports)

Genesis Keys are organized into 24-hour blocks with time/date stamps
so you can click into any block and see exactly what happened.

Full CRUD operations with undo support (soft-delete + history).
Every operation gets a Genesis Key for full provenance.
"""

import logging
import uuid
import hashlib
import shutil
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)


class FileCategory(str, Enum):
    """Top-level file categories."""
    CODE = "codebase"
    DOCUMENTS = "documents"


class FileType(str, Enum):
    """Types of files the librarian manages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    CONFIG = "config"
    MARKDOWN = "markdown"
    PDF = "pdf"
    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    IMAGE = "image"
    GENESIS_KEY = "genesis_key"
    KPI_REPORT = "kpi_report"
    RESEARCH = "research"
    UPLOAD = "upload"
    OTHER = "other"


class OperationType(str, Enum):
    """Types of file operations."""
    CREATE_FILE = "create_file"
    CREATE_DIRECTORY = "create_directory"
    RENAME = "rename"
    MOVE = "move"
    DELETE = "delete"
    EDIT = "edit"
    COPY = "copy"
    SORT = "sort"
    ORGANIZE = "organize"


@dataclass
class FileNode:
    """A file or directory in the managed tree."""
    node_id: str
    name: str
    path: str
    is_directory: bool
    category: FileCategory
    file_type: FileType = FileType.OTHER
    size_bytes: int = 0
    content: Optional[str] = None
    parent_path: str = ""
    children: List[str] = field(default_factory=list)  # child node_ids
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted: bool = False
    deleted_at: Optional[datetime] = None


@dataclass
class FileOperation:
    """A recorded file operation (for undo support)."""
    operation_id: str
    operation_type: OperationType
    target_path: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = None  # For undo
    undone: bool = False
    genesis_key_id: Optional[str] = None


@dataclass
class GenesisKeyBlock:
    """A 24-hour block of Genesis Keys."""
    block_id: str
    date: str  # YYYY-MM-DD
    hour_start: int  # 0-23
    hour_end: int
    key_count: int
    keys: List[Dict[str, Any]]
    folder_path: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# File extension to type mapping
EXTENSION_MAP = {
    ".py": FileType.PYTHON,
    ".js": FileType.JAVASCRIPT,
    ".ts": FileType.TYPESCRIPT,
    ".rs": FileType.RUST,
    ".go": FileType.GO,
    ".json": FileType.JSON,
    ".yaml": FileType.YAML,
    ".yml": FileType.YAML,
    ".md": FileType.MARKDOWN,
    ".txt": FileType.TEXT,
    ".pdf": FileType.PDF,
    ".csv": FileType.CSV,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".gif": FileType.IMAGE,
    ".toml": FileType.CONFIG,
    ".ini": FileType.CONFIG,
    ".cfg": FileType.CONFIG,
    ".env": FileType.CONFIG,
}

# Category detection: code vs document
CODE_TYPES = {
    FileType.PYTHON, FileType.JAVASCRIPT, FileType.TYPESCRIPT,
    FileType.RUST, FileType.GO, FileType.CONFIG, FileType.JSON,
    FileType.YAML,
}
DOCUMENT_TYPES = {
    FileType.MARKDOWN, FileType.PDF, FileType.TEXT, FileType.CSV,
    FileType.IMAGE, FileType.RESEARCH, FileType.UPLOAD,
    FileType.GENESIS_KEY, FileType.KPI_REPORT,
}


class LibrarianFileManager:
    """
    Grace's Librarian - full file management system.

    Manages two trees:
      /codebase/     - Code files organized by language/project
      /documents/    - Documents organized by type/date

    Genesis Keys are sorted into 24-hour blocks:
      /documents/genesis_keys/2026-02-16/00-04h/
      /documents/genesis_keys/2026-02-16/04-08h/
      ...

    Full CRUD with undo:
      create_file, create_directory, rename, move, delete, edit, copy
      undo_last_operation (soft-delete + operation history)

    Auto-categorization:
      Detects code vs document, assigns file type, generates names
      using LLM context when available.
    """

    def __init__(self):
        self.nodes: Dict[str, FileNode] = {}
        self._path_index: Dict[str, str] = {}  # path -> node_id
        self.operations: List[FileOperation] = []
        self._genesis_key_blocks: Dict[str, GenesisKeyBlock] = {}

        # Create root directories
        self._init_root_structure()
        logger.info("[LIBRARIAN] File Management System initialized")

    def _init_root_structure(self):
        """Create the root codebase and documents trees."""
        self._create_directory_internal("/codebase", FileCategory.CODE)
        self._create_directory_internal("/documents", FileCategory.DOCUMENTS)
        self._create_directory_internal("/documents/genesis_keys", FileCategory.DOCUMENTS)
        self._create_directory_internal("/documents/kpi_reports", FileCategory.DOCUMENTS)
        self._create_directory_internal("/documents/research", FileCategory.DOCUMENTS)
        self._create_directory_internal("/documents/uploads", FileCategory.DOCUMENTS)

    def _create_directory_internal(
        self, path: str, category: FileCategory
    ) -> FileNode:
        """Internal directory creation (no operation log)."""
        node_id = f"dir-{uuid.uuid4().hex[:12]}"
        parent = str(PurePosixPath(path).parent)

        node = FileNode(
            node_id=node_id,
            name=PurePosixPath(path).name or path,
            path=path,
            is_directory=True,
            category=category,
            parent_path=parent,
        )
        self.nodes[node_id] = node
        self._path_index[path] = node_id

        # Link to parent
        if parent in self._path_index and parent != path:
            parent_id = self._path_index[parent]
            if parent_id in self.nodes:
                self.nodes[parent_id].children.append(node_id)

        return node

    # =========================================================================
    # FILE TYPE DETECTION
    # =========================================================================

    def detect_file_type(self, filename: str) -> FileType:
        """Detect file type from filename."""
        ext = PurePosixPath(filename).suffix.lower()
        return EXTENSION_MAP.get(ext, FileType.OTHER)

    def detect_category(self, file_type: FileType, content: Optional[str] = None) -> FileCategory:
        """Detect whether a file belongs in codebase or documents."""
        if file_type in CODE_TYPES:
            return FileCategory.CODE
        if file_type in DOCUMENT_TYPES:
            return FileCategory.DOCUMENTS
        # Fallback: check content for code indicators
        if content:
            code_indicators = ["def ", "class ", "import ", "function ", "const ", "let ", "var "]
            if any(ind in content for ind in code_indicators):
                return FileCategory.CODE
        return FileCategory.DOCUMENTS

    def generate_smart_name(
        self, content: str, file_type: FileType, domain: Optional[str] = None
    ) -> str:
        """Generate a smart filename from content context."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        type_prefixes = {
            FileType.PYTHON: "py",
            FileType.JAVASCRIPT: "js",
            FileType.TYPESCRIPT: "ts",
            FileType.RUST: "rs",
            FileType.GO: "go",
            FileType.MARKDOWN: "doc",
            FileType.PDF: "pdf",
            FileType.TEXT: "txt",
            FileType.JSON: "data",
            FileType.RESEARCH: "research",
            FileType.GENESIS_KEY: "gk",
            FileType.KPI_REPORT: "kpi",
        }

        prefix = type_prefixes.get(file_type, "file")
        domain_part = f"_{domain}" if domain else ""

        # Extract first meaningful words from content
        words = content.split()[:4]
        slug = "_".join(w.lower().strip(".,!?:;") for w in words if len(w) > 2)[:30]

        ext_map = {
            FileType.PYTHON: ".py",
            FileType.JAVASCRIPT: ".js",
            FileType.TYPESCRIPT: ".ts",
            FileType.RUST: ".rs",
            FileType.GO: ".go",
            FileType.MARKDOWN: ".md",
            FileType.PDF: ".pdf",
            FileType.TEXT: ".txt",
            FileType.JSON: ".json",
            FileType.YAML: ".yaml",
        }
        ext = ext_map.get(file_type, ".txt")

        return f"{prefix}{domain_part}_{slug}_{timestamp}{ext}"

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    def create_file(
        self,
        name: str,
        content: str,
        parent_path: Optional[str] = None,
        file_type: Optional[FileType] = None,
        category: Optional[FileCategory] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        genesis_key_id: Optional[str] = None,
    ) -> FileNode:
        """
        Create a new file.

        Auto-detects type and category if not provided.
        Auto-places in correct tree (/codebase or /documents).
        """
        if file_type is None:
            file_type = self.detect_file_type(name)
        if category is None:
            category = self.detect_category(file_type, content)

        if parent_path is None:
            parent_path = f"/{category.value}"

        # Ensure parent exists
        if parent_path not in self._path_index:
            self._create_directory_internal(parent_path, category)

        path = f"{parent_path}/{name}"

        node_id = f"file-{uuid.uuid4().hex[:12]}"
        node = FileNode(
            node_id=node_id,
            name=name,
            path=path,
            is_directory=False,
            category=category,
            file_type=file_type,
            size_bytes=len(content.encode("utf-8")),
            content=content,
            parent_path=parent_path,
            tags=list(tags or []),
            metadata=dict(metadata or {}),
            genesis_key_id=genesis_key_id,
        )

        self.nodes[node_id] = node
        self._path_index[path] = node_id

        # Link to parent
        parent_id = self._path_index.get(parent_path)
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)

        # Log operation
        self._log_operation(
            OperationType.CREATE_FILE, path,
            details={"name": name, "file_type": file_type.value, "category": category.value},
            genesis_key_id=genesis_key_id,
        )

        return node

    def create_directory(
        self,
        name: str,
        parent_path: str = "/documents",
        category: Optional[FileCategory] = None,
    ) -> FileNode:
        """Create a new directory."""
        if category is None:
            category = (
                FileCategory.CODE if parent_path.startswith("/codebase")
                else FileCategory.DOCUMENTS
            )

        path = f"{parent_path}/{name}"
        node = self._create_directory_internal(path, category)

        self._log_operation(
            OperationType.CREATE_DIRECTORY, path,
            details={"name": name, "category": category.value},
        )

        return node

    def rename(self, path: str, new_name: str) -> Optional[FileNode]:
        """Rename a file or directory."""
        node_id = self._path_index.get(path)
        if not node_id or node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        old_name = node.name
        old_path = node.path

        parent = str(PurePosixPath(path).parent)
        new_path = f"{parent}/{new_name}"

        # Store previous state for undo
        previous_state = {"name": old_name, "path": old_path}

        node.name = new_name
        node.path = new_path
        node.updated_at = datetime.now(timezone.utc)

        # Update path index
        del self._path_index[old_path]
        self._path_index[new_path] = node_id

        self._log_operation(
            OperationType.RENAME, old_path,
            details={"old_name": old_name, "new_name": new_name, "new_path": new_path},
            previous_state=previous_state,
        )

        return node

    def move(self, source_path: str, dest_parent: str) -> Optional[FileNode]:
        """Move a file or directory to a new parent."""
        node_id = self._path_index.get(source_path)
        if not node_id or node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        old_path = node.path
        old_parent = node.parent_path

        new_path = f"{dest_parent}/{node.name}"
        previous_state = {"path": old_path, "parent_path": old_parent}

        # Remove from old parent
        old_parent_id = self._path_index.get(old_parent)
        if old_parent_id and old_parent_id in self.nodes:
            children = self.nodes[old_parent_id].children
            if node_id in children:
                children.remove(node_id)

        # Ensure dest parent exists
        if dest_parent not in self._path_index:
            cat = FileCategory.CODE if dest_parent.startswith("/codebase") else FileCategory.DOCUMENTS
            self._create_directory_internal(dest_parent, cat)

        # Add to new parent
        dest_parent_id = self._path_index.get(dest_parent)
        if dest_parent_id and dest_parent_id in self.nodes:
            self.nodes[dest_parent_id].children.append(node_id)

        node.path = new_path
        node.parent_path = dest_parent
        node.updated_at = datetime.now(timezone.utc)

        del self._path_index[old_path]
        self._path_index[new_path] = node_id

        self._log_operation(
            OperationType.MOVE, old_path,
            details={"old_path": old_path, "new_path": new_path},
            previous_state=previous_state,
        )

        return node

    def delete(self, path: str) -> bool:
        """
        Soft-delete a file or directory (supports undo).

        The file is marked deleted but kept in memory for undo.
        """
        node_id = self._path_index.get(path)
        if not node_id or node_id not in self.nodes:
            return False

        node = self.nodes[node_id]
        previous_state = {
            "path": node.path,
            "name": node.name,
            "parent_path": node.parent_path,
            "deleted": False,
            "content": node.content,
        }

        node.deleted = True
        node.deleted_at = datetime.now(timezone.utc)
        node.updated_at = datetime.now(timezone.utc)

        self._log_operation(
            OperationType.DELETE, path,
            details={"name": node.name},
            previous_state=previous_state,
        )

        return True

    def edit(self, path: str, new_content: str) -> Optional[FileNode]:
        """Edit file content."""
        node_id = self._path_index.get(path)
        if not node_id or node_id not in self.nodes:
            return None

        node = self.nodes[node_id]
        if node.is_directory:
            return None

        previous_state = {"content": node.content, "size_bytes": node.size_bytes}
        node.content = new_content
        node.size_bytes = len(new_content.encode("utf-8"))
        node.updated_at = datetime.now(timezone.utc)

        self._log_operation(
            OperationType.EDIT, path,
            details={"old_size": previous_state["size_bytes"], "new_size": node.size_bytes},
            previous_state=previous_state,
        )

        return node

    def undo_last_operation(self) -> Optional[FileOperation]:
        """
        Undo the last file operation.

        Restores previous state from the operation history.
        """
        # Find last un-undone operation
        for op in reversed(self.operations):
            if not op.undone and op.previous_state:
                return self._undo_operation(op)
        return None

    def _undo_operation(self, op: FileOperation) -> FileOperation:
        """Undo a specific operation."""
        prev = op.previous_state
        if not prev:
            op.undone = True
            return op

        if op.operation_type == OperationType.DELETE:
            node_id = self._path_index.get(op.target_path)
            if node_id and node_id in self.nodes:
                self.nodes[node_id].deleted = False
                self.nodes[node_id].deleted_at = None

        elif op.operation_type == OperationType.RENAME:
            node_id = self._path_index.get(op.details.get("new_path", ""))
            if node_id and node_id in self.nodes:
                node = self.nodes[node_id]
                new_path = op.details.get("new_path", "")
                old_path = prev["path"]
                node.name = prev["name"]
                node.path = old_path
                if new_path in self._path_index:
                    del self._path_index[new_path]
                self._path_index[old_path] = node_id

        elif op.operation_type == OperationType.EDIT:
            node_id = self._path_index.get(op.target_path)
            if node_id and node_id in self.nodes:
                self.nodes[node_id].content = prev.get("content")
                self.nodes[node_id].size_bytes = prev.get("size_bytes", 0)

        elif op.operation_type == OperationType.MOVE:
            node_id = self._path_index.get(op.details.get("new_path", ""))
            if node_id and node_id in self.nodes:
                node = self.nodes[node_id]
                new_path = op.details.get("new_path", "")
                old_path = prev["path"]
                node.path = old_path
                node.parent_path = prev["parent_path"]
                if new_path in self._path_index:
                    del self._path_index[new_path]
                self._path_index[old_path] = node_id

        op.undone = True
        return op

    # =========================================================================
    # GENESIS KEY 24-HOUR BLOCK ORGANIZATION
    # =========================================================================

    def organize_genesis_keys(
        self, keys: List[Dict[str, Any]], block_hours: int = 4
    ) -> List[GenesisKeyBlock]:
        """
        Organize Genesis Keys into time-block folders.

        Creates folder structure:
          /documents/genesis_keys/2026-02-16/00-04h/
          /documents/genesis_keys/2026-02-16/04-08h/
          ...

        Args:
            keys: List of Genesis Key dicts with 'when_timestamp', 'key_id', etc.
            block_hours: Hours per block (default 4 = six blocks per day)

        Returns:
            List of GenesisKeyBlock
        """
        # Group keys by date and time block
        blocks_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for key in keys:
            ts = key.get("when_timestamp")
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts)
                except (ValueError, TypeError):
                    dt = datetime.now(timezone.utc)
            elif isinstance(ts, datetime):
                dt = ts
            else:
                dt = datetime.now(timezone.utc)

            date_str = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            block_start = (hour // block_hours) * block_hours
            block_end = block_start + block_hours
            block_label = f"{block_start:02d}-{block_end:02d}h"
            block_key = f"{date_str}/{block_label}"

            blocks_map[block_key].append(key)

        # Create folders and organize
        blocks: List[GenesisKeyBlock] = []
        for block_key, block_keys in blocks_map.items():
            folder_path = f"/documents/genesis_keys/{block_key}"

            # Ensure folder exists
            parts = folder_path.split("/")
            for i in range(2, len(parts) + 1):
                partial = "/".join(parts[:i])
                if partial and partial not in self._path_index:
                    self._create_directory_internal(partial, FileCategory.DOCUMENTS)

            # Create a summary file for the block
            date_str = block_key.split("/")[0]
            block_label = block_key.split("/")[1]
            hour_start = int(block_label.split("-")[0])
            hour_end = int(block_label.split("-")[1].replace("h", ""))

            # Store each key as a file
            for gk in block_keys:
                key_id = gk.get("key_id", f"gk-{uuid.uuid4().hex[:8]}")
                content = self._format_genesis_key(gk)
                self.create_file(
                    name=f"{key_id}.md",
                    content=content,
                    parent_path=folder_path,
                    file_type=FileType.GENESIS_KEY,
                    category=FileCategory.DOCUMENTS,
                    tags=["genesis_key", date_str, block_label],
                    metadata={"genesis_key_id": key_id, "block": block_key},
                )

            block = GenesisKeyBlock(
                block_id=f"gkb-{uuid.uuid4().hex[:12]}",
                date=date_str,
                hour_start=hour_start,
                hour_end=hour_end,
                key_count=len(block_keys),
                keys=block_keys,
                folder_path=folder_path,
            )
            blocks.append(block)
            self._genesis_key_blocks[block_key] = block

        logger.info(
            f"[LIBRARIAN] Organized {len(keys)} Genesis Keys into "
            f"{len(blocks)} blocks"
        )
        return blocks

    def _format_genesis_key(self, gk: Dict[str, Any]) -> str:
        """Format a Genesis Key as a readable document."""
        lines = [
            f"# Genesis Key: {gk.get('key_id', 'unknown')}",
            "",
            f"**Type:** {gk.get('key_type', 'unknown')}",
            f"**When:** {gk.get('when_timestamp', 'unknown')}",
            f"**Who:** {gk.get('who_actor', 'unknown')}",
            f"**What:** {gk.get('what_description', 'unknown')}",
        ]
        if gk.get("where_location"):
            lines.append(f"**Where:** {gk['where_location']}")
        if gk.get("why_reason"):
            lines.append(f"**Why:** {gk['why_reason']}")
        if gk.get("how_method"):
            lines.append(f"**How:** {gk['how_method']}")
        if gk.get("file_path"):
            lines.append(f"**File:** {gk['file_path']}")
        if gk.get("is_error"):
            lines.append(f"\n## Error Details")
            lines.append(f"**Error Type:** {gk.get('error_type', '')}")
            lines.append(f"**Message:** {gk.get('error_message', '')}")
        return "\n".join(lines)

    # =========================================================================
    # AUTO-SORT AND ORGANIZE
    # =========================================================================

    def auto_sort_file(
        self, content: str, filename: str, domain: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
    ) -> FileNode:
        """
        Auto-sort a file into the correct location.

        Detects type, category, generates smart name if needed,
        and places into correct directory tree.
        """
        file_type = self.detect_file_type(filename)
        category = self.detect_category(file_type, content)

        # Determine subdirectory based on domain or type
        if category == FileCategory.CODE:
            parent = self._get_code_directory(file_type, domain)
        else:
            parent = self._get_document_directory(file_type, domain)

        return self.create_file(
            name=filename,
            content=content,
            parent_path=parent,
            file_type=file_type,
            category=category,
            domain=domain,
            genesis_key_id=genesis_key_id,
        )

    def _get_code_directory(
        self, file_type: FileType, domain: Optional[str]
    ) -> str:
        """Get or create appropriate code subdirectory."""
        if domain:
            path = f"/codebase/{domain}"
        elif file_type == FileType.PYTHON:
            path = "/codebase/python"
        elif file_type == FileType.JAVASCRIPT:
            path = "/codebase/javascript"
        elif file_type == FileType.RUST:
            path = "/codebase/rust"
        elif file_type == FileType.CONFIG:
            path = "/codebase/config"
        else:
            path = "/codebase/general"

        if path not in self._path_index:
            self._create_directory_internal(path, FileCategory.CODE)
        return path

    def _get_document_directory(
        self, file_type: FileType, domain: Optional[str]
    ) -> str:
        """Get or create appropriate document subdirectory."""
        if file_type == FileType.GENESIS_KEY:
            path = "/documents/genesis_keys"
        elif file_type == FileType.KPI_REPORT:
            path = "/documents/kpi_reports"
        elif file_type == FileType.RESEARCH:
            path = "/documents/research"
        elif domain:
            path = f"/documents/{domain}"
        else:
            path = "/documents/uploads"

        if path not in self._path_index:
            self._create_directory_internal(path, FileCategory.DOCUMENTS)
        return path

    # =========================================================================
    # QUERY AND BROWSE
    # =========================================================================

    def get_node(self, path: str) -> Optional[FileNode]:
        """Get a file or directory node by path."""
        node_id = self._path_index.get(path)
        if not node_id:
            return None
        node = self.nodes.get(node_id)
        if node and not node.deleted:
            return node
        return None

    def list_directory(self, path: str) -> List[FileNode]:
        """List contents of a directory (non-deleted only)."""
        node_id = self._path_index.get(path)
        if not node_id or node_id not in self.nodes:
            return []
        node = self.nodes[node_id]
        if not node.is_directory:
            return []
        children = []
        for child_id in node.children:
            if child_id in self.nodes and not self.nodes[child_id].deleted:
                children.append(self.nodes[child_id])
        return children

    def search_files(
        self, query: str, category: Optional[FileCategory] = None
    ) -> List[FileNode]:
        """Search files by name or content."""
        query_lower = query.lower()
        results = []
        for node in self.nodes.values():
            if node.deleted or node.is_directory:
                continue
            if category and node.category != category:
                continue
            if query_lower in node.name.lower():
                results.append(node)
            elif node.content and query_lower in node.content.lower():
                results.append(node)
        return results

    def get_tree(self, root_path: str = "/", max_depth: int = 3) -> Dict[str, Any]:
        """Get directory tree structure."""
        node_id = self._path_index.get(root_path)
        if not node_id:
            return {"path": root_path, "children": []}
        return self._build_tree(node_id, 0, max_depth)

    def _build_tree(self, node_id: str, depth: int, max_depth: int) -> Dict[str, Any]:
        """Recursively build tree structure."""
        if node_id not in self.nodes or depth > max_depth:
            return {}
        node = self.nodes[node_id]
        if node.deleted:
            return {}
        result = {
            "name": node.name,
            "path": node.path,
            "is_directory": node.is_directory,
            "file_type": node.file_type.value if not node.is_directory else None,
            "size": node.size_bytes,
        }
        if node.is_directory:
            result["children"] = [
                self._build_tree(cid, depth + 1, max_depth)
                for cid in node.children
                if cid in self.nodes and not self.nodes[cid].deleted
            ]
            result["children"] = [c for c in result["children"] if c]
        return result

    def get_genesis_key_blocks(self, date: Optional[str] = None) -> List[GenesisKeyBlock]:
        """Get Genesis Key blocks, optionally filtered by date."""
        blocks = list(self._genesis_key_blocks.values())
        if date:
            blocks = [b for b in blocks if b.date == date]
        return blocks

    # =========================================================================
    # OPERATION HISTORY
    # =========================================================================

    def _log_operation(
        self,
        op_type: OperationType,
        target_path: str,
        details: Optional[Dict[str, Any]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        genesis_key_id: Optional[str] = None,
    ) -> FileOperation:
        """Log a file operation."""
        op = FileOperation(
            operation_id=f"op-{uuid.uuid4().hex[:12]}",
            operation_type=op_type,
            target_path=target_path,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            previous_state=previous_state,
            genesis_key_id=genesis_key_id,
        )
        self.operations.append(op)
        return op

    def get_operation_history(self, limit: int = 50) -> List[FileOperation]:
        """Get recent operation history."""
        return self.operations[-limit:]

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get file management statistics."""
        active_nodes = [n for n in self.nodes.values() if not n.deleted]
        files = [n for n in active_nodes if not n.is_directory]
        dirs = [n for n in active_nodes if n.is_directory]
        code_files = [f for f in files if f.category == FileCategory.CODE]
        doc_files = [f for f in files if f.category == FileCategory.DOCUMENTS]
        total_size = sum(f.size_bytes for f in files)

        return {
            "total_files": len(files),
            "total_directories": len(dirs),
            "code_files": len(code_files),
            "document_files": len(doc_files),
            "total_size_bytes": total_size,
            "genesis_key_blocks": len(self._genesis_key_blocks),
            "total_operations": len(self.operations),
            "deleted_files": sum(1 for n in self.nodes.values() if n.deleted),
        }
