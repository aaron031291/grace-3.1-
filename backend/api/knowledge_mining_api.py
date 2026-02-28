"""
Knowledge Mining API — Mine LLMs for training data and store in Oracle.

Uses Opus/Kimi to generate comprehensive software engineering knowledge,
then stores it in the Oracle (training DB), unified memory, and flash cache.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import json
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-mine", tags=["Knowledge Mining"])

TRAINING_DIR = Path(__file__).parent.parent / "data" / "training_data"


class MiningRequest(BaseModel):
    topic: str
    depth: str = "comprehensive"  # brief, standard, comprehensive
    provider: str = "opus"  # opus, kimi
    store_in_oracle: bool = True
    store_in_flash_cache: bool = True


class BulkMiningRequest(BaseModel):
    topics: List[str]
    provider: str = "opus"


@router.post("/mine")
async def mine_knowledge(req: MiningRequest, background_tasks: BackgroundTasks):
    """Mine a specific topic from an LLM and store as training data."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client(provider=req.provider)

        depth_tokens = {"brief": 1024, "standard": 4096, "comprehensive": 8192}
        max_tokens = depth_tokens.get(req.depth, 4096)

        prompt = (
            f"Generate comprehensive software engineering training data on:\n\n"
            f"Topic: {req.topic}\n\n"
            f"Include:\n"
            f"- Core principles and best practices\n"
            f"- Common patterns and anti-patterns\n"
            f"- Python code examples (production-grade)\n"
            f"- Architecture decisions and trade-offs\n"
            f"- Testing strategies\n"
            f"- Production-readiness checklist\n"
            f"- Common pitfalls and how to avoid them\n\n"
            f"Be as detailed as possible. This is training data for an autonomous AI coding agent."
        )

        response = client.generate(
            prompt=prompt,
            system_prompt="You are a senior software engineering knowledge base. Generate comprehensive, production-grade training data.",
            temperature=0.3,
            max_tokens=max_tokens,
        )

        text = response if isinstance(response, str) else str(response)

        # Save to file
        safe_name = req.topic.replace(" ", "_").replace("/", "_")[:50]
        file_path = TRAINING_DIR / f"mined_{safe_name}.txt"
        file_path.write_text(text)

        result = {
            "mined": True,
            "topic": req.topic,
            "chars": len(text),
            "provider": req.provider,
            "file": str(file_path.name),
        }

        # Store in Oracle (background)
        if req.store_in_oracle:
            background_tasks.add_task(_store_in_oracle, req.topic, text)

        # Store in FlashCache
        if req.store_in_flash_cache:
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                kw = fc.extract_keywords(f"{req.topic} {text[:500]}")
                fc.register(
                    source_uri=f"internal://training/{safe_name}",
                    source_type="internal",
                    source_name=f"Training: {req.topic}",
                    keywords=kw,
                    summary=text[:500],
                    trust_score=0.85,
                    ttl_hours=8760 * 10,
                )
                result["flash_cache_registered"] = True
            except Exception:
                pass

        # Genesis Key
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Knowledge mined: {req.topic} ({len(text)} chars)",
                how=f"knowledge_mining_api ({req.provider})",
                output_data={"topic": req.topic, "chars": len(text)},
                tags=["knowledge_mining", req.provider, req.topic.split()[0].lower()],
            )
        except Exception:
            pass

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mine-bulk")
async def mine_bulk(req: BulkMiningRequest, background_tasks: BackgroundTasks):
    """Mine multiple topics in sequence."""
    results = []
    for topic in req.topics:
        try:
            single = MiningRequest(topic=topic, provider=req.provider)
            result = await mine_knowledge(single, background_tasks)
            results.append(result)
        except Exception as e:
            results.append({"topic": topic, "error": str(e)})

    return {
        "total": len(results),
        "successful": sum(1 for r in results if r.get("mined")),
        "results": results,
    }


# ── Training Corpus (committed to repo — available on startup) ────────

@router.post("/corpus/ingest")
async def ingest_corpus(force: bool = False):
    """Auto-ingest training corpus into Oracle + Memory + FlashCache."""
    from cognitive.training_ingest import ingest_training_corpus
    return ingest_training_corpus(force=force)


@router.get("/corpus/stats")
async def corpus_stats():
    """Get training corpus statistics."""
    from cognitive.training_ingest import get_corpus_stats
    return get_corpus_stats()


# ── Terabyte-Scale Training Pipeline ──────────────────────────────────

@router.get("/pipeline/sources")
async def list_data_sources():
    """List all free terabyte-scale training data sources."""
    from cognitive.training_pipeline import list_sources
    return {"sources": list_sources()}


@router.get("/pipeline/instructions/{source_id}")
async def get_download_instructions(source_id: str):
    """Get download instructions for a specific data source."""
    from cognitive.training_pipeline import get_download_instructions
    return get_download_instructions(source_id)


@router.get("/pipeline/plan")
async def get_recommended_plan(storage_gb: int = 1000):
    """Get a recommended download plan based on available storage."""
    from cognitive.training_pipeline import get_recommended_plan
    return get_recommended_plan(storage_gb)


@router.post("/pipeline/generate-scripts")
async def generate_download_scripts():
    """Generate download scripts for all HuggingFace datasets."""
    from cognitive.training_pipeline import generate_all_download_scripts
    scripts = generate_all_download_scripts()
    return {"scripts_generated": len(scripts), "scripts": scripts}


@router.get("/training-data")
async def list_training_data():
    """List all mined training data files."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(TRAINING_DIR.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": f.stat().st_mtime,
        })
    total_size = sum(f["size"] for f in files)
    return {
        "files": files,
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }


@router.get("/training-data/{filename}")
async def get_training_file(filename: str):
    """Read a specific training data file."""
    path = TRAINING_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "filename": filename,
        "content": path.read_text(errors="ignore"),
        "size": path.stat().st_size,
    }


async def _store_in_oracle(topic: str, text: str):
    """Store mined knowledge in Oracle DB."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()

        # Split into sections
        sections = text.split("\n## ")
        for section in sections:
            if len(section.strip()) < 50:
                continue
            lines = section.strip().split("\n")
            title = lines[0].strip().strip("#").strip()
            content = "\n".join(lines[1:]).strip()
            if len(content) < 30:
                continue

            mem.store_learning(
                input_ctx=f"Software Engineering: {title}",
                expected=content[:5000],
                trust=0.85,
                source="opus_knowledge_mining",
                example_type="engineering_knowledge",
            )
    except Exception as e:
        logger.warning(f"Oracle storage failed: {e}")
