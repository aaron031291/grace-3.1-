"""
Training Corpus Auto-Ingest — Loads training data on startup.

When Grace's system starts, this module checks the training_corpus/
directory and ingests any new training data into:
  1. Oracle (learning_examples table)
  2. Unified Memory
  3. FlashCache (keyword index)

The INDEX.json file tracks what's available.
Files are marked as ingested so they're not re-processed.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

CORPUS_DIR = Path(__file__).parent.parent / "training_corpus"
INGESTED_FILE = Path(__file__).parent.parent / "data" / "training_ingested.json"


def _load_ingested() -> set:
    if INGESTED_FILE.exists():
        try:
            return set(json.loads(INGESTED_FILE.read_text()))
        except Exception:
            pass
    return set()


def _save_ingested(ingested: set):
    INGESTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    INGESTED_FILE.write_text(json.dumps(sorted(ingested)))


def ingest_training_corpus(force: bool = False) -> Dict[str, Any]:
    """
    Auto-ingest training corpus into Oracle + Memory + FlashCache.
    Called on startup or manually via API.
    
    Args:
        force: If True, re-ingest even if already processed.
    """
    if not CORPUS_DIR.exists():
        return {"status": "no_corpus", "message": "training_corpus/ directory not found"}

    # Ensure database is actually ready before trying to track
    try:
        from database.connection import DatabaseConnection
        engine = DatabaseConnection.get_engine()
        if not engine:
            logger.debug("[TRAINING] DB not ready, deferring training ingestion")
            return {"status": "deferred", "message": "DB not ready"}
    except RuntimeError:
        logger.debug("[TRAINING] DB not initialized yet, deferring training ingestion")
        return {"status": "deferred", "message": "DB not initialized"}

    ingested = set() if force else _load_ingested()
    results = {"ingested": 0, "skipped": 0, "errors": 0, "details": []}

    for category_dir in sorted(CORPUS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue

        category = category_dir.name
        for txt_file in sorted(category_dir.glob("*.txt")):
            file_key = f"{category}/{txt_file.name}"

            if file_key in ingested and not force:
                results["skipped"] += 1
                continue

            try:
                content = txt_file.read_text(errors="ignore")
                sections = _split_sections(content)

                stored = 0
                for title, body in sections:
                    if len(body) < 30:
                        continue
                    _store_section(category, title, body)
                    stored += 1

                # Register in FlashCache
                _register_in_cache(category, txt_file.name, content[:1000])

                ingested.add(file_key)
                results["ingested"] += 1
                results["details"].append({
                    "file": file_key,
                    "sections": stored,
                    "size_kb": round(len(content) / 1024, 1),
                })

            except Exception as e:
                results["errors"] += 1
                results["details"].append({"file": file_key, "error": str(e)})

    _save_ingested(ingested)

    # Genesis tracking
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Training corpus ingested: {results['ingested']} files, {results['skipped']} skipped",
            how="training_ingest.ingest_training_corpus",
            output_data=results,
            tags=["training", "ingest", "startup"],
        )
    except Exception:
        pass

    logger.info(f"[TRAINING] Ingested {results['ingested']} files, skipped {results['skipped']}")
    return results


def _split_sections(content: str) -> List[tuple]:
    """Split content into (title, body) sections."""
    sections = []
    parts = content.split("\n## ")
    for part in parts:
        lines = part.strip().split("\n")
        if not lines:
            continue
        title = lines[0].strip().strip("#").strip()
        body = "\n".join(lines[1:]).strip()
        if title and body:
            sections.append((title, body))
    return sections


def _store_section(category: str, title: str, body: str):
    """Store a section in the Oracle database."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        mem.store_learning(
            input_ctx=f"Engineering Knowledge ({category}): {title}",
            expected=body[:5000],
            trust=0.85,
            source=f"training_corpus_{category}",
            example_type="engineering_knowledge",
        )
    except Exception:
        pass


def _register_in_cache(category: str, filename: str, preview: str):
    """Register training file in FlashCache for keyword discovery."""
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        kw = fc.extract_keywords(preview)
        fc.register(
            source_uri=f"internal://training/{category}/{filename}",
            source_type="internal",
            source_name=f"Training: {category}/{filename}",
            keywords=kw,
            summary=preview[:500],
            trust_score=0.85,
            ttl_hours=8760 * 10,
        )
    except Exception:
        pass


def get_corpus_stats() -> Dict[str, Any]:
    """Get stats about the training corpus."""
    if not CORPUS_DIR.exists():
        return {"exists": False}

    ingested = _load_ingested()
    stats = {
        "exists": True,
        "categories": {},
        "total_files": 0,
        "total_size_bytes": 0,
        "ingested_count": len(ingested),
    }

    for category_dir in sorted(CORPUS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        files = list(category_dir.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        stats["categories"][category_dir.name] = {
            "files": len(files),
            "size_kb": round(total_size / 1024, 1),
            "ingested": sum(1 for f in files if f"{category_dir.name}/{f.name}" in ingested),
        }
        stats["total_files"] += len(files)
        stats["total_size_bytes"] += total_size

    stats["total_size_kb"] = round(stats["total_size_bytes"] / 1024, 1)
    return stats
