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


# ── Reverse kNN → Oracle → Knowledge Pipeline ────────────────────────

@router.post("/discover-and-fill")
async def discover_and_fill_gaps():
    """
    Full pipeline: Reverse kNN finds gaps → Opus suggests sources → 
    Whitelist hub fetches → FlashCache indexes → Oracle stores.
    """
    from cognitive.reverse_knn import get_reverse_knn
    
    # Step 1: Find gaps
    knn = get_reverse_knn()
    gaps = knn.scan_knowledge_gaps()
    suggestions = knn.suggest_expansion_topics(limit=5)
    
    # Step 2: For each gap, try to fill from existing sources
    filled = []
    for topic in suggestions[:3]:
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.search(topic, limit=3, min_trust=0.3)
            if refs:
                filled.append({"topic": topic, "source": "flash_cache", "refs": len(refs)})
                continue
        except Exception:
            pass
        
        # No cached refs — log as unfilled
        filled.append({"topic": topic, "source": "none", "refs": 0})
    
    # Step 3: Track
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Knowledge gap scan: {gaps['summary'].get('total_gaps', 0)} gaps, {len(filled)} topics processed",
            how="discover_and_fill_gaps",
            output_data={"gaps": gaps["summary"], "filled": filled},
            tags=["reverse_knn", "knowledge_gaps", "pipeline"],
        )
    except Exception:
        pass
    
    return {
        "gaps_found": gaps["summary"],
        "topics_suggested": suggestions,
        "fill_results": filled,
    }


@router.post("/discover-and-fill-active")
async def discover_and_fill_active(max_gaps: int = 5):
    """
    Active gap filling: Reverse kNN finds gaps → routes each gap through
    3 pathways (API, web search, web scrape) → ingests results.
    """
    from cognitive.reverse_knn import get_reverse_knn
    knn = get_reverse_knn()
    return knn.fill_gaps_actively(max_gaps=max_gaps)


@router.post("/seed-sources")
async def seed_engineering_sources():
    """
    Seed Grace's whitelist with 10 free software engineering sources
    recommended by Kimi+Opus consensus. These feed the reverse kNN pipeline.
    """
    sources = [
        # Software Engineering
        {"name": "Python PEPs", "url": "https://peps.python.org/api/peps.json",
         "description": "All Python Enhancement Proposals in JSON", "source_type": "api", "tags": ["python", "peps", "standards"]},
        {"name": "Python Packaging Guide", "url": "https://packaging.python.org/sitemap.xml",
         "description": "Python packaging best practices", "source_type": "website", "tags": ["python", "packaging"]},
        {"name": "MDN HTTP Reference", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP",
         "description": "Complete HTTP specification and best practices", "source_type": "website", "tags": ["http", "api", "web"]},
        {"name": "12-Factor App", "url": "https://12factor.net/",
         "description": "12-factor methodology for building SaaS apps", "source_type": "website", "tags": ["architecture", "devops", "best-practices"]},
        {"name": "OWASP Cheat Sheets", "url": "https://api.github.com/repos/OWASP/CheatSheetSeries/contents/cheatsheets",
         "description": "Security best practices for developers", "source_type": "api", "tags": ["security", "owasp", "best-practices"]},
        {"name": "Semver Spec", "url": "https://semver.org/",
         "description": "Semantic versioning specification", "source_type": "website", "tags": ["versioning", "standards"]},
        {"name": "Google API Design Guide", "url": "https://google.github.io/styleguide/jsoncstyleguide.xml",
         "description": "Google's API design best practices", "source_type": "website", "tags": ["api", "design", "google"]},
        {"name": "Kubernetes Contributor Guide", "url": "https://raw.githubusercontent.com/kubernetes/community/master/contributors/guide/pull-requests.md",
         "description": "K8s contribution and PR best practices", "source_type": "website", "tags": ["kubernetes", "devops", "open-source"]},
        {"name": "Debian Policy Manual", "url": "https://www.debian.org/doc/debian-policy/",
         "description": "Software packaging and distribution policy", "source_type": "website", "tags": ["linux", "packaging", "policy"]},
        {"name": "GitHub REST API", "url": "https://api.github.com",
         "description": "GitHub API — endpoints, auth, best practices", "source_type": "api", "tags": ["github", "api", "git"]},

        # AI Research APIs (free, no key needed)
        {"name": "ArXiv AI Papers", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=50",
         "description": "Latest AI and machine learning research papers from ArXiv", "source_type": "api", "tags": ["ai", "research", "papers", "arxiv", "machine-learning"]},
        {"name": "ArXiv NLP Papers", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=50",
         "description": "Latest NLP and language model research papers", "source_type": "api", "tags": ["nlp", "research", "papers", "language-models"]},
        {"name": "ArXiv Software Engineering", "url": "http://export.arxiv.org/api/query?search_query=cat:cs.SE&sortBy=submittedDate&sortOrder=descending&max_results=50",
         "description": "Latest software engineering research papers", "source_type": "api", "tags": ["software-engineering", "research", "papers"]},
        {"name": "Semantic Scholar AI", "url": "https://api.semanticscholar.org/graph/v1/paper/search?query=autonomous+AI+systems&limit=50&fields=title,abstract,year,citationCount",
         "description": "200M+ academic papers — search for autonomous AI research", "source_type": "api", "tags": ["ai", "research", "academic", "citations"]},
        {"name": "Semantic Scholar Code Gen", "url": "https://api.semanticscholar.org/graph/v1/paper/search?query=code+generation+LLM&limit=50&fields=title,abstract,year,citationCount",
         "description": "Research on LLM code generation", "source_type": "api", "tags": ["code-generation", "llm", "research"]},
        {"name": "Papers With Code", "url": "https://paperswithcode.com/api/v1/papers/?ordering=-proceeding&limit=50",
         "description": "Latest papers with code implementations", "source_type": "api", "tags": ["papers", "code", "implementations", "benchmarks"]},
        {"name": "Papers With Code — Methods", "url": "https://paperswithcode.com/api/v1/methods/?limit=50",
         "description": "ML methods and techniques with implementations", "source_type": "api", "tags": ["methods", "techniques", "ml", "implementations"]},
        {"name": "HuggingFace Models", "url": "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=50",
         "description": "Most popular AI models on HuggingFace", "source_type": "api", "tags": ["models", "huggingface", "ai", "downloads"]},
        {"name": "HuggingFace Datasets", "url": "https://huggingface.co/api/datasets?sort=downloads&direction=-1&limit=50",
         "description": "Most popular datasets for AI training", "source_type": "api", "tags": ["datasets", "training", "ai", "huggingface"]},
        {"name": "GitHub Trending AI", "url": "https://api.github.com/search/repositories?q=topic:artificial-intelligence&sort=stars&order=desc&per_page=30",
         "description": "Top trending AI repositories on GitHub", "source_type": "api", "tags": ["github", "ai", "trending", "open-source"]},
        {"name": "GitHub Trending Python", "url": "https://api.github.com/search/repositories?q=language:python+stars:>1000&sort=updated&order=desc&per_page=30",
         "description": "Most active Python repositories with 1000+ stars", "source_type": "api", "tags": ["github", "python", "trending", "popular"]},
    ]
    
    registered = []
    for src in sources:
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            kw = fc.extract_keywords(f"{src['name']} {src['description']}")
            kw.extend(src.get("tags", []))
            entry_id = fc.register(
                source_uri=src["url"],
                source_type=src["source_type"],
                source_name=src["name"],
                keywords=list(set(kw)),
                summary=src["description"],
                trust_score=0.8,
                ttl_hours=8760,
                metadata={"tags": src.get("tags", []), "seeded_by": "kimi_opus_consensus"},
            )
            registered.append({"name": src["name"], "entry_id": entry_id, "url": src["url"]})
        except Exception as e:
            registered.append({"name": src["name"], "error": str(e)})
    
    # Also register API sources in the whitelist hub
    try:
        from pathlib import Path
        import json as _json
        data_dir = Path(__file__).parent.parent / "data" / "whitelist_sources"
        data_dir.mkdir(parents=True, exist_ok=True)
        api_sources_file = data_dir / "api_sources.json"
        existing = []
        if api_sources_file.exists():
            try:
                existing = _json.loads(api_sources_file.read_text())
            except Exception:
                pass
        existing_urls = {s.get("url") for s in existing}
        for src in sources:
            if src["source_type"] == "api" and src["url"] not in existing_urls:
                existing.append({
                    "id": f"api-seed-{len(existing)}",
                    "name": src["name"],
                    "url": src["url"],
                    "description": src["description"],
                    "status": "active",
                    "headers": {},
                    "api_key": "",
                    "run_count": 0,
                    "documents": [],
                })
        api_sources_file.write_text(_json.dumps(existing, indent=2, default=str))
    except Exception:
        pass

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Seeded {len(registered)} sources (engineering + AI research) into whitelist + FlashCache",
            how="seed_engineering_sources",
            tags=["reverse_knn", "seed", "sources"],
        )
    except Exception:
        pass
    
    return {"seeded": len(registered), "sources": registered}


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
