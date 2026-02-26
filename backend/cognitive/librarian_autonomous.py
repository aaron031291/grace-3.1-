"""
Autonomous Librarian — Automatically organises ALL files system-wide.

The librarian doesn't wait to be asked. She:
1. Watches for new files/documents from ANY source
2. Analyses content to determine category
3. Creates the directory structure if it doesn't exist
4. Moves/places files into the right location
5. Tags and indexes everything
6. Keeps the knowledge base tidy continuously

Connected to: Genesis realtime (watches for uploads), Docs library,
Ingestion pipeline, Whitelist sources, Coding agent outputs,
Magma memory, Trust Engine.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# Standard directory taxonomy the librarian maintains
DIRECTORY_TAXONOMY = {
    "code": {
        "python": [".py"],
        "javascript": [".js", ".jsx", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "web": [".html", ".css", ".scss"],
        "styles": [".css", ".scss", ".less"],
        "react": [".jsx", ".tsx"],
    },
    "documentation": {
        "readme": [],
        "guides": [],
        "api_docs": [],
        "architecture": [],
    },
    "data": {
        "csv": [".csv"],
        "json": [".json"],
        "xml": [".xml"],
        "sql": [".sql"],
    },
    "reports": {},
    "research": {},
    "configuration": {
        "env": [".env", ".ini", ".cfg"],
        "yaml": [".yaml", ".yml", ".toml"],
    },
    "media": {
        "images": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"],
        "audio": [".mp3", ".wav", ".ogg"],
        "video": [".mp4", ".webm", ".avi"],
    },
    "logs": {
        "system": [],
        "audit": [],
    },
    "tests": {},
    "governance": {
        "rules": [],
        "compliance": [],
        "policies": [],
    },
    "projects": {},
    "training": {
        "datasets": [],
        "models": [],
        "exports": [],
    },
}


def _get_kb() -> Path:
    try:
        from settings import settings
        return Path(settings.KNOWLEDGE_BASE_PATH)
    except Exception:
        return Path("knowledge_base")


class AutonomousLibrarian:
    """
    Watches the system and automatically organises files.
    """

    def __init__(self):
        self._connected = False

    def connect_to_realtime(self):
        """Connect to genesis realtime engine to watch for new files."""
        if self._connected:
            return
        try:
            from genesis.realtime import get_realtime_engine
            rt = get_realtime_engine()
            rt.watch("upload", self._on_file_event)
            rt.watch("file_op", self._on_file_event)
            rt.watch("file_ingestion", self._on_file_event)
            self._connected = True
            logger.info("[LIBRARIAN] Connected to genesis realtime — watching for new files")
        except Exception as e:
            logger.debug(f"[LIBRARIAN] Realtime connection failed: {e}")

    def _on_file_event(self, event: Dict):
        """Called automatically when a file is created/uploaded anywhere."""
        file_path = event.get("data", {}).get("output", {}).get("path") or event.get("where", "")
        if not file_path:
            return

        try:
            self.organise_file(file_path)
        except Exception as e:
            logger.debug(f"[LIBRARIAN] Auto-organise failed for {file_path}: {e}")

    # ── Core: Analyse and organise a file ──────────────────────────────

    def organise_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyse a file and move it to the correct location.
        Creates directories if they don't exist.
        Genesis key tracks every decision.
        """
        kb = _get_kb()
        full_path = kb / file_path if not Path(file_path).is_absolute() else Path(file_path)

        if not full_path.exists():
            try:
                from api._genesis_tracker import track
                track(key_type="librarian", what=f"File not found: {file_path}",
                      where=file_path, tags=["librarian", "file_not_found"])
            except Exception:
                pass
            return {"action": "skip", "reason": "file not found"}

        # Already organised if in a proper subdirectory
        try:
            rel = full_path.relative_to(kb)
            if len(rel.parts) > 1 and rel.parts[0] in DIRECTORY_TAXONOMY:
                return {"action": "already_organised", "path": str(rel)}
        except ValueError:
            pass

        # Determine where this file should go
        suggestion = self.suggest_location(full_path)

        if not suggestion:
            try:
                from api._genesis_tracker import track
                track(key_type="librarian", what=f"No suggestion for: {full_path.name}",
                      where=str(full_path), file_path=str(full_path),
                      tags=["librarian", "no_suggestion"])
            except Exception:
                pass
            return {"action": "no_suggestion", "path": str(file_path)}

        # Create the target directory
        target_dir = kb / suggestion
        target_dir.mkdir(parents=True, exist_ok=True)

        # Move the file
        target = target_dir / full_path.name
        if target.exists():
            return {"action": "skip", "reason": "target already exists"}

        try:
            import shutil
            shutil.move(str(full_path), str(target))

            result = {
                "action": "organised",
                "from": str(file_path),
                "to": str(target.relative_to(kb)),
                "directory": suggestion,
            }

            # Track via genesis
            try:
                from api._genesis_tracker import track
                track(key_type="librarian", what=f"Auto-organised: {full_path.name} → {suggestion}",
                      where=str(target), file_path=str(target),
                      tags=["librarian", "auto_organise"])
            except Exception:
                pass

            # Store in Magma
            try:
                from cognitive.magma_bridge import store_decision
                store_decision("organise", str(full_path.name), f"Moved to {suggestion}")
            except Exception:
                pass

            logger.info(f"[LIBRARIAN] Organised: {full_path.name} → {suggestion}")
            return result

        except Exception as e:
            return {"action": "failed", "error": str(e)}

    # ── Suggest location for a file ────────────────────────────────────

    def suggest_location(self, file_path: Path) -> Optional[str]:
        """Determine where a file should be placed based on name, extension, content, and Kimi reasoning."""
        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        # Name-based rules (highest priority)
        if "readme" in name:
            return "documentation"
        if "test" in name and ext in (".py", ".js", ".ts"):
            return "tests"
        if "report" in name:
            return "reports"
        if name.startswith("config") or name.startswith("settings"):
            return "configuration"
        if "license" in name or "licence" in name:
            return "governance/compliance"
        if "gdpr" in name or "iso" in name or "compliance" in name or "policy" in name:
            return "governance/policies"

        # Extension-based rules
        for category, subcats in DIRECTORY_TAXONOMY.items():
            if isinstance(subcats, dict):
                for subcat, extensions in subcats.items():
                    if ext in extensions:
                        return f"{category}/{subcat}"

        # Fallback by extension
        ext_map = {
            ".py": "code/python", ".js": "code/javascript", ".ts": "code/typescript",
            ".jsx": "code/react", ".tsx": "code/react",
            ".html": "code/web", ".css": "code/styles",
            ".md": "documentation", ".rst": "documentation", ".txt": "documentation",
            ".pdf": "documentation",
            ".csv": "data/csv", ".json": "data/json", ".xml": "data/xml",
            ".yaml": "configuration/yaml", ".yml": "configuration/yaml",
            ".toml": "configuration/yaml", ".ini": "configuration/env",
            ".png": "media/images", ".jpg": "media/images", ".jpeg": "media/images",
            ".gif": "media/images", ".svg": "media/images",
            ".mp3": "media/audio", ".wav": "media/audio",
            ".mp4": "media/video",
            ".log": "logs/system",
            ".sql": "data/sql",
        }

        suggestion = ext_map.get(ext)
        if suggestion:
            return suggestion

        # Unknown file type — ask Kimi to reason about where it should go
        return self._ask_kimi_for_location(file_path)

    def _ask_kimi_for_location(self, file_path: Path) -> Optional[str]:
        """Query Kimi to reason about where an unknown file type should be placed."""
        try:
            # Read file preview for context
            content_preview = ""
            try:
                content_preview = file_path.read_text(errors="ignore")[:2000]
            except Exception:
                content_preview = f"[Binary file: {file_path.suffix}, size: {file_path.stat().st_size} bytes]"

            categories = ", ".join(DIRECTORY_TAXONOMY.keys())

            from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
            kimi = get_kimi_enhanced()
            response = kimi._call(
                f"You are a file organiser. Where should this file be placed?\n\n"
                f"Filename: {file_path.name}\n"
                f"Extension: {file_path.suffix}\n"
                f"Content preview:\n{content_preview[:1000]}\n\n"
                f"Available categories: {categories}\n"
                f"Subcategories can be created freely.\n\n"
                f"Respond with ONLY the directory path, e.g. 'documentation' or 'code/python' or 'research/ai'. Nothing else.",
                system="You are a librarian. Respond with only the directory path. No explanation.",
                temperature=0.1, max_tokens=50,
            )

            if response:
                # Clean the response — should be just a path
                suggestion = response.strip().strip("'\"").strip("/").lower()
                suggestion = suggestion.replace(" ", "_")
                # Validate it's reasonable
                if 1 < len(suggestion) < 50 and "/" in suggestion or suggestion in DIRECTORY_TAXONOMY:
                    logger.info(f"[LIBRARIAN] Kimi suggests: {file_path.name} → {suggestion}")

                    from api._genesis_tracker import track
                    track(key_type="librarian",
                          what=f"Kimi file reasoning: {file_path.name} → {suggestion}",
                          where=str(file_path), file_path=str(file_path),
                          input_data={"filename": file_path.name, "extension": file_path.suffix},
                          output_data={"suggestion": suggestion, "source": "kimi_reasoning"},
                          tags=["librarian", "kimi_reasoning", "file_placement"])
                    return suggestion
        except Exception as e:
            logger.debug(f"[LIBRARIAN] Kimi reasoning failed: {e}")

        return None

    # ── Organise entire knowledge base ─────────────────────────────────

    def organise_all(self, dry_run: bool = True) -> Dict[str, Any]:
        """Scan the knowledge base root and organise any misplaced files."""
        kb = _get_kb()
        if not kb.exists():
            return {"scanned": 0, "actions": []}

        actions = []
        for item in kb.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                suggestion = self.suggest_location(item)
                if suggestion:
                    action = {
                        "file": item.name,
                        "suggested": suggestion,
                        "action": "would_move" if dry_run else "moved",
                    }
                    if not dry_run:
                        result = self.organise_file(str(item.relative_to(kb)))
                        action["result"] = result
                    actions.append(action)

        try:
            from api._genesis_tracker import track
            track(key_type="librarian",
                  what=f"Organise scan: {len(actions)} files {'would be' if dry_run else ''} moved",
                  how="AutonomousLibrarian.organise_all",
                  output_data={"scanned": len(list(kb.iterdir())), "actions": len(actions), "dry_run": dry_run},
                  tags=["librarian", "organise_scan", "dry_run" if dry_run else "execute"])
        except Exception:
            pass

        return {"scanned": len(list(kb.iterdir())), "actions": actions, "dry_run": dry_run}

    # ── Ensure directory structure exists ───────────────────────────────

    def ensure_taxonomy(self) -> Dict[str, Any]:
        """Create the full directory taxonomy if it doesn't exist."""
        kb = _get_kb()
        created = []

        def _create(base: Path, taxonomy: dict, depth: int = 0):
            for name, children in taxonomy.items():
                dir_path = base / name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created.append(str(dir_path.relative_to(kb)))
                if isinstance(children, dict) and depth < 3:
                    _create(dir_path, children, depth + 1)

        _create(kb, DIRECTORY_TAXONOMY)

        if created:
            try:
                from api._genesis_tracker import track
                track(key_type="librarian", what=f"Created {len(created)} directories in taxonomy",
                      tags=["librarian", "taxonomy"])
            except Exception:
                pass

        return {"created": len(created), "directories": created}

    def get_status(self) -> Dict[str, Any]:
        kb = _get_kb()
        file_count = 0
        dir_count = 0
        root_files = 0
        if kb.exists():
            for item in kb.rglob("*"):
                if item.is_file() and not item.name.startswith('.'):
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
            for item in kb.iterdir():
                if item.is_file() and not item.name.startswith('.'):
                    root_files += 1

        return {
            "connected_to_realtime": self._connected,
            "total_files": file_count,
            "total_directories": dir_count,
            "root_files_unorganised": root_files,
            "taxonomy_categories": len(DIRECTORY_TAXONOMY),
        }


_librarian = None

def get_autonomous_librarian() -> AutonomousLibrarian:
    global _librarian
    if _librarian is None:
        _librarian = AutonomousLibrarian()
        _librarian.connect_to_realtime()
    return _librarian
