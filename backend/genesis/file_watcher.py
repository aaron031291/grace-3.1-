"""
File System Watcher for Automatic Version Control.

Watches file changes in the workspace and automatically creates
Genesis Keys + Version entries for all modifications.

This makes GRACE truly autonomous - file changes are tracked
in real-time without manual intervention.
"""
import os
import logging
import time
from typing import Optional, Set, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from database.session import session_scope

logger = logging.getLogger(__name__)


class GenesisFileWatcher(FileSystemEventHandler):
    """
    Watches file system changes and creates Genesis Keys + Versions automatically.

    Monitors a directory tree and triggers symbiotic version control
    for all file modifications, creates, and deletes.
    """

    def __init__(
        self,
        watch_path: str,
        exclude_patterns: Optional[Set[str]] = None,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize file watcher.

        Args:
            watch_path: Root path to watch for file changes
            exclude_patterns: Set of patterns to exclude (e.g., {'.git', '__pycache__', '.pyc'})
            debounce_seconds: Wait time after last change before triggering version control
        """
        self.watch_path = watch_path
        self.exclude_patterns = exclude_patterns or {
            '.git', '__pycache__', '.pyc', '.pyo', '.pyd',
            'node_modules', '.venv', 'venv', 'env',
            '.genesis_file_versions.json', '.genesis_immutable_memory.json',
            '.db', '.db-shm', '.db-wal',
            'observations.json',
            '.log', 'embedding_debug.log', 'logs',  # Exclude logs directory to prevent infinite loop
            'genesis_key',  # Exclude KB genesis_key folder to prevent recursive tracking
            'layer_1',  # Exclude entire layer_1 folder which contains genesis_key data
            'auto_search',  # Exclude internet search cache - no need for version control
            'GU-',  # Exclude Genesis User folders (pattern prefix)
            'session_SS-',  # Exclude session files (pattern prefix)
            'sandbox_lab',  # Exclude sandbox experiment files - too large, not useful to version
            'EXP-',  # Exclude experiment JSON files
        }
        self.debounce_seconds = debounce_seconds

        # Debouncing: track last modification time for each file
        self.last_modified: Dict[str, float] = {}
        self.symbiotic_vc = None
        self.files_tracked = 0

        logger.info(f"GenesisFileWatcher initialized for: {watch_path}")

    def _get_symbiotic_vc(self):
        """Lazy load symbiotic version control to avoid circular imports."""
        if self.symbiotic_vc is None:
            from genesis.symbiotic_version_control import get_symbiotic_version_control
            self.symbiotic_vc = get_symbiotic_version_control()
        return self.symbiotic_vc

    # Paths that should NEVER be watched — OS/browser/temp junk that
    # generates a firehose of events and poisons the DB session.
    _HARD_IGNORE_FRAGMENTS = (
        "AppData",
        "appdata",
        ".cache",
        "cache2",
        "Cache",
        "mozilla",
        "firefox",
        "Firefox",
        "chromium",
        "chrome",
        "Google",
        ".mozilla",
        "Temp",
        "tmp",
        ".tmp",
        "Local\\Packages",
        ".local/share/Trash",
        "Recycle.Bin",
        "thumbnails",
        ".thumbnails",
        "Recently Used",
        "recently-used",
        "fontconfig",
        "dconf",
        "pulse",
        "snap",
        "flatpak",
        "BrowserMetrics",
        "CrashReports",
    )

    def _should_ignore(self, file_path: str) -> bool:
        """Check if file should be ignored based on exclude patterns."""
        file_path_str = str(file_path)

        # Hard-ignore non-repo paths (browser caches, OS temp, etc.)
        for frag in self._HARD_IGNORE_FRAGMENTS:
            if frag in file_path_str:
                return True

        path_parts = Path(file_path).parts

        if 'genesis_key' in file_path_str or '/layer_1/' in file_path_str:
            return True
        
        if '/GU-' in file_path_str or '\\GU-' in file_path_str:
            return True
        
        if 'session_SS-' in file_path_str:
            return True

        for part in path_parts:
            for pattern in self.exclude_patterns:
                if pattern in part or part.endswith(pattern) or part.startswith(pattern):
                    return True

        filename = os.path.basename(file_path)
        for pattern in self.exclude_patterns:
            if filename.endswith(pattern) or pattern in filename or filename.startswith(pattern):
                return True

        return False


    def _is_debounced(self, file_path: str) -> bool:
        """
        Check if enough time has passed since last modification.

        Many editors trigger multiple file events for a single save.
        This debouncing prevents creating multiple versions for the same change.
        """
        current_time = time.time()
        last_time = self.last_modified.get(file_path, 0)

        if current_time - last_time < self.debounce_seconds:
            # Too soon, still debouncing
            return True

        # Update last modified time
        self.last_modified[file_path] = current_time
        return False

    def _track_file_change(self, file_path: str, operation_type: str):
        """Track file change using symbiotic version control."""
        try:
            # Ensure database is actually ready before trying to track
            try:
                from database.connection import DatabaseConnection
                engine = DatabaseConnection.get_engine()
                if not engine:
                    logger.debug(f"[FILE_WATCHER] DB not ready, skipping {operation_type} for {file_path}")
                    return
            except RuntimeError:
                logger.debug(f"[FILE_WATCHER] DB not initialized yet, skipping {operation_type} for {file_path}")
                return

            # Get relative path from watch root
            rel_path = os.path.relpath(file_path, self.watch_path)
            
            # Log the absolute path received from watchdog
            logger.info(f"[FILE_WATCHER] Received event: file_path={file_path}, watch_path={self.watch_path}, rel_path={rel_path}")

            symbiotic = self._get_symbiotic_vc()
            result = symbiotic.track_file_change(
                file_path=file_path,  # Use absolute path to avoid /backend/backend/ duplication
                user_id="file_watcher",
                change_description=f"File {operation_type} detected by watcher",
                operation_type=operation_type
            )

            self.files_tracked += 1

            logger.info(
                f"[FILE_WATCHER] Tracked: {rel_path} - "
                f"Operation: {operation_type}, "
                f"Genesis Key: {result['operation_genesis_key']}, "
                f"Version: {result.get('version_number', 'N/A')}"
            )

        except Exception as e:
            logger.error(f"[FILE_WATCHER] Error tracking {file_path}: {e}", exc_info=True)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Skip ignored files
        if self._should_ignore(file_path):
            return

        # Skip if debouncing
        if self._is_debounced(file_path):
            logger.debug(f"[FILE_WATCHER] Debouncing: {file_path}")
            return

        # Check if file exists (sometimes events fire before file is written)
        if not os.path.exists(file_path):
            return

        logger.debug(f"[FILE_WATCHER] File modified: {file_path}")
        self._track_file_change(file_path, "modify")

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Skip ignored files
        if self._should_ignore(file_path):
            return

        # Skip if debouncing
        if self._is_debounced(file_path):
            return

        # Check if file exists and has content
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return

        logger.debug(f"[FILE_WATCHER] File created: {file_path}")
        self._track_file_change(file_path, "create")

    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Skip ignored files
        if self._should_ignore(file_path):
            return

        logger.debug(f"[FILE_WATCHER] File deleted: {file_path}")

        # For deletions, we still create a Genesis Key to track the deletion
        # even though the file no longer exists
        try:
            # Get relative path from watch root
            rel_path = os.path.relpath(file_path, self.watch_path)
            
            from genesis.genesis_key_service import get_genesis_service
            from models.genesis_key_models import GenesisKeyType

            with session_scope() as session:
                genesis_service = get_genesis_service(session)
                genesis_service.create_key(
                    key_type=GenesisKeyType.FILE_OPERATION,
                    what_description=f"File deleted: {os.path.basename(file_path)}",
                    who_actor="file_watcher",
                    where_location=rel_path,
                    why_reason="File deletion detected by watcher",
                    how_method="File system watcher",
                    user_id="file_watcher",
                    file_path=rel_path,
                    context_data={
                        "operation_type": "delete",
                        "deleted_at": datetime.now(timezone.utc).isoformat()
                    },
                    tags=["file_delete", "watcher"],
                    session=session
                )

            logger.info(f"[FILE_WATCHER] Tracked deletion: {rel_path}")

        except Exception as e:
            logger.error(f"[FILE_WATCHER] Error tracking deletion {file_path}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get watcher statistics."""
        return {
            "watch_path": self.watch_path,
            "files_tracked": self.files_tracked,
            "excluded_patterns": list(self.exclude_patterns),
            "debounce_seconds": self.debounce_seconds,
            "active_files_monitoring": len(self.last_modified)
        }


class FileWatcherService:
    """
    Service to manage file watchers for multiple directories.

    Can watch multiple directories simultaneously and coordinate
    version tracking across all of them.
    """

    def __init__(self):
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, GenesisFileWatcher] = {}
        logger.info("FileWatcherService initialized")

    def start_watching(
        self,
        watch_path: str,
        recursive: bool = True,
        exclude_patterns: Optional[Set[str]] = None
    ) -> bool:
        """
        Start watching a directory for file changes.

        Args:
            watch_path: Path to watch
            recursive: Whether to watch subdirectories
            exclude_patterns: Patterns to exclude from watching

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Don't start if already watching
            if watch_path in self.observers:
                logger.warning(f"Already watching: {watch_path}")
                return False

            # Create handler
            handler = GenesisFileWatcher(
                watch_path=watch_path,
                exclude_patterns=exclude_patterns
            )

            # Create observer
            observer = Observer()
            observer.schedule(handler, watch_path, recursive=recursive)
            observer.start()

            # Store references
            self.observers[watch_path] = observer
            self.handlers[watch_path] = handler

            logger.info(f"[FILE_WATCHER_SERVICE] Started watching: {watch_path} (recursive={recursive})")
            return True

        except Exception as e:
            logger.error(f"[FILE_WATCHER_SERVICE] Failed to start watching {watch_path}: {e}")
            return False

    def stop_watching(self, watch_path: str) -> bool:
        """Stop watching a directory."""
        try:
            if watch_path not in self.observers:
                logger.warning(f"Not watching: {watch_path}")
                return False

            observer = self.observers[watch_path]
            observer.stop()
            observer.join(timeout=5.0)

            del self.observers[watch_path]
            del self.handlers[watch_path]

            logger.info(f"[FILE_WATCHER_SERVICE] Stopped watching: {watch_path}")
            return True

        except Exception as e:
            logger.error(f"[FILE_WATCHER_SERVICE] Failed to stop watching {watch_path}: {e}")
            return False

    def stop_all(self):
        """Stop all watchers."""
        for watch_path in list(self.observers.keys()):
            self.stop_watching(watch_path)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all watchers."""
        stats = {
            "active_watchers": len(self.observers),
            "watched_paths": list(self.observers.keys()),
            "handlers": {}
        }

        for watch_path, handler in self.handlers.items():
            stats["handlers"][watch_path] = handler.get_statistics()

        return stats


# Global file watcher service
_file_watcher_service: Optional[FileWatcherService] = None


def get_file_watcher_service() -> FileWatcherService:
    """Get or create the global file watcher service."""
    global _file_watcher_service
    if _file_watcher_service is None:
        _file_watcher_service = FileWatcherService()
    return _file_watcher_service


def start_watching_workspace(workspace_path: Optional[str] = None) -> bool:
    """
    Convenience function to start watching the GRACE workspace.

    Args:
        workspace_path: Path to workspace (defaults to grace_3 root)

    Returns:
        True if started successfully
    """
    if workspace_path is None:
        # Default to grace_3 root
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        workspace_path = os.path.dirname(backend_dir)

    service = get_file_watcher_service()
    return service.start_watching(
        watch_path=workspace_path,
        recursive=True,
        exclude_patterns={
            '.git', '__pycache__', '.pyc', '.pyo', '.pyd',
            'node_modules', '.venv', 'venv', 'env',
            '.genesis_file_versions.json', '.genesis_immutable_memory.json',
            '.db', '.db-shm', '.db-wal',
            'observations.json',
            '.log', 'embedding_debug.log', 'nul', 'logs',  # Exclude logs directory
            'auto_search',  # Exclude internet search cache
            'sandbox_lab',  # Exclude sandbox experiment files
            'EXP-',  # Exclude experiment JSON files
        }
    )
