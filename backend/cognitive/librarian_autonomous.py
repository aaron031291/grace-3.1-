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
import json
from datetime import datetime, timezone

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

        # Check FlashCache for similar files/topics before asking Kimi
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = fc.extract_keywords(name)
            if kw:
                refs = fc.lookup(keywords=kw[:5], limit=3, min_trust=0.5)
                for ref in refs:
                    meta = ref.get("metadata", {})
                    if isinstance(meta, str):
                        import json
                        try:
                            meta = json.loads(meta)
                        except Exception:
                            meta = {}
                    source_type = meta.get("source_type", ref.get("source_type", ""))
                    if source_type in ("api", "web"):
                        return "research/external"
                    if source_type == "document":
                        return "documentation"
        except Exception:
            pass

        # Unknown file type — ask LLM (Qwen by default) to reason about where it should go
        return self._ask_llm_for_location(file_path)

    def _ask_llm_for_location(self, file_path: Path) -> Optional[str]:
        """Query LLM (Qwen document model by default) to reason about where an unknown file should be placed."""
        try:
            content_preview = ""
            try:
                content_preview = file_path.read_text(errors="ignore")[:2000]
            except Exception:
                content_preview = f"[Binary file: {file_path.suffix}, size: {file_path.stat().st_size} bytes]"

            categories = ", ".join(DIRECTORY_TAXONOMY.keys())
            prompt = (
                f"You are a file organiser. Where should this file be placed?\n\n"
                f"Filename: {file_path.name}\n"
                f"Extension: {file_path.suffix}\n"
                f"Content preview:\n{content_preview[:1000]}\n\n"
                f"Available categories: {categories}\n"
                f"Subcategories can be created freely.\n\n"
                f"Respond with ONLY the directory path, e.g. 'documentation' or 'code/python' or 'research/ai'. Nothing else."
            )

            from llm_orchestrator.factory import get_llm_for_task
            from llm_orchestrator.ollama_resolver import resolve_ollama_model
            client = get_llm_for_task("document")
            doc_model = resolve_ollama_model("document")
            if hasattr(client, "chat"):
                raw = client.chat(
                    model=doc_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    stream=False,
                )
                if isinstance(raw, dict) and "message" in raw:
                    response = raw["message"].get("content", "")
                else:
                    response = str(raw) if raw else ""
            else:
                response = ""

            if response:
                suggestion = response.strip().strip("'\"").strip("/").lower()
                suggestion = suggestion.replace(" ", "_")
                if 1 < len(suggestion) < 50 and ("/" in suggestion or suggestion in DIRECTORY_TAXONOMY):
                    logger.info(f"[LIBRARIAN] Qwen suggests: {file_path.name} → {suggestion}")
                    try:
                        from api._genesis_tracker import track
                        track(
                            key_type="librarian",
                            what=f"LLM file reasoning: {file_path.name} → {suggestion}",
                            where=str(file_path), file_path=str(file_path),
                            input_data={"filename": file_path.name, "extension": file_path.suffix},
                            output_data={"suggestion": suggestion, "source": "qwen_document"},
                            tags=["librarian", "file_placement"],
                        )
                    except Exception:
                        pass
                    return suggestion
        except Exception as e:
            logger.debug(f"[LIBRARIAN] LLM reasoning failed: {e}")

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

    def on_new_folder(self, folder_path: str) -> Dict[str, Any]:
        """Called when a new domain folder is created. Triggers auto-research and idle learning."""
        analysis = {}
        try:
            from cognitive.auto_research import get_auto_research
            research = get_auto_research()
            analysis = research.analyse_folder(folder_path)
        except Exception:
            analysis = {"suggested_research": []}

        # Register folder topic in FlashCache for keyword discovery
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            folder_name = Path(folder_path).name
            kw = fc.extract_keywords(folder_name.replace("_", " ").replace("-", " "))
            fc.register(
                source_uri=f"internal://folders/{folder_path}",
                source_type="internal",
                source_name=f"Folder: {folder_name}",
                keywords=kw,
                summary=f"Knowledge base folder: {folder_path}",
                trust_score=0.8,
                ttl_hours=8760,
            )
        except Exception:
            pass

        # Trigger idle learner to research the folder topic
        try:
            from cognitive.idle_learner import IdleLearner
            learner = IdleLearner()
            folder_name = Path(folder_path).name.replace("_", " ").replace("-", " ")
            if folder_name and len(folder_name) > 2:
                from cognitive.consensus_engine import queue_autonomous_query
                queue_autonomous_query(
                    prompt=f"Research the topic '{folder_name}' and identify key concepts, sub-topics, and recommended learning resources.",
                    context=f"New folder created at {folder_path}",
                    priority="normal",
                )
        except Exception:
            pass

        try:
            from api._genesis_tracker import track
            track(key_type="librarian",
                  what=f"New folder detected: {folder_path} — auto-research + idle learning triggered",
                  where=folder_path,
                  output_data={"topics": len(analysis.get("suggested_research", []))},
                  tags=["librarian", "new_folder", "auto_research"])
        except Exception:
            pass

        return {
            "notification": f"New folder '{folder_path}' detected. Research queued.",
            "folder": folder_path,
            "suggested_topics": analysis.get("suggested_research", []),
            "analysis": analysis,
        }

    def create_domain_environment(self, domain_name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a full domain environment — like a venv but for ANY topic.
        Auto-populates with structure, governance, and triggers learning.
        """
        kb = _get_kb()
        domain_path = kb / "domains" / domain_name.lower().replace(" ", "_")
        domain_path.mkdir(parents=True, exist_ok=True)

        # Create domain structure
        subdirs = ["documents", "code", "research", "data", "governance", "notes"]
        created = []
        for sub in subdirs:
            (domain_path / sub).mkdir(exist_ok=True)
            created.append(sub)

        # Create domain config
        config = {
            "domain": domain_name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "subdirectories": subdirs,
            "auto_learn": True,
            "governance_rules": [],
        }
        (domain_path / "domain_config.json").write_text(json.dumps(config, indent=2))

        # Register in FlashCache for keyword discovery
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = fc.extract_keywords(f"{domain_name} {description}")
            fc.register(
                source_uri=f"internal://domain/{domain_name}",
                source_type="internal",
                source_name=f"Domain: {domain_name}",
                keywords=kw,
                summary=description or f"Knowledge domain: {domain_name}",
                trust_score=0.8,
                ttl_hours=8760 * 10,
            )
        except Exception:
            pass

        # Trigger reverse kNN to find relevant sources
        try:
            from cognitive.reverse_knn import get_reverse_knn
            knn = get_reverse_knn()
            knn.log_query(domain_name, had_results=False)
            knn.log_query(f"{domain_name} best practices", had_results=False)
        except Exception:
            pass

        # Queue consensus research on the domain
        try:
            from cognitive.consensus_engine import queue_autonomous_query
            queue_autonomous_query(
                prompt=f"Research the domain '{domain_name}' ({description}). What are the key sub-topics, best practices, and learning resources?",
                context=f"New domain environment created at {domain_path}",
            )
        except Exception:
            pass

        # Genesis Key
        try:
            from api._genesis_tracker import track
            track(
                key_type="librarian",
                what=f"Domain environment created: {domain_name}",
                where=str(domain_path),
                output_data={"domain": domain_name, "subdirs": subdirs},
                tags=["librarian", "domain", "environment"],
            )
        except Exception:
            pass

        try:
            from cognitive.event_bus import publish
            publish("domain.created", {
                "domain": domain_name, "path": str(domain_path),
            }, source="librarian")
        except Exception:
            pass

        return {
            "created": True,
            "domain": domain_name,
            "path": str(domain_path.relative_to(kb)),
            "subdirectories": created,
            "config": config,
        }

    def smart_ingest_document(self, file_path: str) -> Dict[str, Any]:
        """
        Intelligent document processing: Read → Understand → Name → Categorise → Index.
        The librarian READS the document, extracts key concepts, auto-names it,
        and places it in the right domain/folder.
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        result = {
            "original_path": file_path,
            "original_name": path.name,
            "processed": False,
        }

        # Step 1: Read the document
        content = ""
        try:
            if path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.xml', '.yml', '.yaml']:
                content = path.read_text(errors="ignore")[:10000]
            elif path.suffix.lower() == '.pdf':
                try:
                    from ingestion.service import extract_file_text
                    content = extract_file_text(str(path))[:10000]
                except Exception:
                    content = f"[PDF file: {path.name}, {path.stat().st_size} bytes]"
            else:
                content = f"[{path.suffix} file: {path.name}, {path.stat().st_size} bytes]"
        except Exception as e:
            content = f"[Error reading: {e}]"

        result["content_preview"] = content[:200]

        # Step 2: Understand — extract key concepts via LLM or heuristics
        concepts = []
        suggested_name = path.stem
        suggested_category = self.suggest_location(path) or "uncategorized"

        if content and len(content) > 100:
            # Extract keywords
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                concepts = fc.extract_keywords(content[:2000])
            except Exception:
                pass

            # Try LLM for smart naming
            try:
                from llm_orchestrator.factory import get_llm_client
                client = get_llm_client()
                naming_response = client.generate(
                    prompt=f"Given this document content, suggest a short filename (no extension, snake_case) and one-line description:\n\n{content[:1000]}",
                    system_prompt="Respond with ONLY: filename|description. Example: api_design_guide|REST API design best practices",
                    temperature=0.1,
                    max_tokens=50,
                )
                if isinstance(naming_response, str) and "|" in naming_response:
                    parts = naming_response.strip().split("|")
                    suggested_name = parts[0].strip().replace(" ", "_")[:50]
                    result["ai_description"] = parts[1].strip() if len(parts) > 1 else ""
            except Exception:
                pass

        result["concepts"] = concepts[:10]
        result["suggested_name"] = suggested_name
        result["suggested_category"] = suggested_category

        # Step 3: Move to the right location with the right name
        kb = _get_kb()
        target_dir = kb / suggested_category
        target_dir.mkdir(parents=True, exist_ok=True)
        new_name = f"{suggested_name}{path.suffix}"
        target_path = target_dir / new_name

        # Avoid overwrite
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{suggested_name}_{counter}{path.suffix}"
            counter += 1

        try:
            import shutil
            shutil.move(str(path), str(target_path))
            result["new_path"] = str(target_path.relative_to(kb))
            result["new_name"] = target_path.name
            result["processed"] = True
        except Exception as e:
            result["error"] = f"Move failed: {e}"
            return result

        # Step 4: Register in docs library
        try:
            from api.docs_library_api import register_document
            register_document(
                filename=target_path.name,
                file_path=str(target_path),
                file_size=target_path.stat().st_size,
                source="librarian_smart_ingest",
                upload_method="smart_ingest",
                directory=suggested_category,
                tags=concepts[:5],
            )
        except Exception:
            pass

        # Step 5: Index in FlashCache
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            fc.register(
                source_uri=f"internal://doc/{target_path.name}",
                source_type="document",
                source_name=target_path.name,
                keywords=concepts,
                summary=content[:300],
                trust_score=0.7,
            )
        except Exception:
            pass

        # Step 6: Genesis Key
        try:
            from api._genesis_tracker import track
            track(
                key_type="librarian",
                what=f"Smart ingest: {path.name} → {target_path.name} in {suggested_category}",
                where=str(target_path),
                output_data={
                    "original": path.name,
                    "new_name": target_path.name,
                    "category": suggested_category,
                    "concepts": concepts[:5],
                },
                tags=["librarian", "smart_ingest", "auto_name"],
            )
        except Exception:
            pass

        return result

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
