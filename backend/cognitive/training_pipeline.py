"""
Training Data Pipeline — Terabyte-Scale Data Acquisition

Opus is too expensive for raw data generation (30KB per call = $$$).
Instead, this pipeline PULLS from free, massive open-source datasets
and uses Opus to CURATE and VERIFY, not generate.

Data Sources (all free, all terabyte-scale):

1. THE STACK (BigCode) — 6.4TB of permissively licensed code
   https://huggingface.co/datasets/bigcode/the-stack-v2
   Languages: Python, JS, TS, Rust, Go, Java, C++

2. GITHUB CODE — 1TB+ of GitHub repositories
   https://huggingface.co/datasets/codeparrot/github-code

3. WIKIPEDIA — 22GB compressed, full knowledge base
   https://dumps.wikimedia.org/

4. COMMON CRAWL — 380TB of web content
   https://commoncrawl.org/

5. ARXIV — 1.7M+ scientific papers
   https://www.kaggle.com/datasets/Cornell-University/arxiv

6. STACK OVERFLOW — 50GB+ of Q&A
   https://archive.org/details/stackexchange

7. HUGGINGFACE DATASETS — thousands of curated datasets
   https://huggingface.co/datasets

Pipeline:
  Source → Download → Filter → Chunk → Verify (Opus) → Index → Store

The pipeline downloads in chunks, filters for relevant content,
and uses Opus sparingly for quality verification only.
"""

import json
import logging
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).parent.parent / "data" / "training_pipeline"
DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "training_downloads"

# All free data sources Grace can pull from
DATA_SOURCES = {
    "the_stack_v2": {
        "name": "The Stack v2 (BigCode)",
        "url": "https://huggingface.co/datasets/bigcode/the-stack-v2",
        "type": "huggingface",
        "hf_dataset": "bigcode/the-stack-v2",
        "size": "6.4TB",
        "description": "6.4TB of permissively licensed source code from GitHub. Python, JavaScript, TypeScript, and 300+ languages.",
        "relevance": "critical",
        "free": True,
        "languages": ["python", "javascript", "typescript", "rust", "go"],
    },
    "github_code": {
        "name": "GitHub Code (CodeParrot)",
        "url": "https://huggingface.co/datasets/codeparrot/github-code",
        "type": "huggingface",
        "hf_dataset": "codeparrot/github-code",
        "size": "1TB+",
        "description": "Large-scale GitHub code dataset filtered for quality.",
        "relevance": "critical",
        "free": True,
        "languages": ["python", "javascript"],
    },
    "stack_overflow": {
        "name": "Stack Overflow Data Dump",
        "url": "https://archive.org/details/stackexchange",
        "type": "archive",
        "size": "50GB+",
        "description": "Complete Stack Overflow Q&A dump. Python, JavaScript, system design, architecture questions.",
        "relevance": "high",
        "free": True,
    },
    "arxiv_papers": {
        "name": "ArXiv Papers (CS/AI)",
        "url": "https://www.kaggle.com/datasets/Cornell-University/arxiv",
        "type": "kaggle",
        "size": "1.7M papers",
        "description": "Scientific papers on AI, ML, software engineering, distributed systems.",
        "relevance": "high",
        "free": True,
    },
    "wikipedia": {
        "name": "Wikipedia English Dump",
        "url": "https://dumps.wikimedia.org/enwiki/latest/",
        "type": "direct",
        "download_url": "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2",
        "size": "22GB compressed",
        "description": "Full English Wikipedia. General knowledge, technology, CS articles.",
        "relevance": "medium",
        "free": True,
    },
    "common_crawl": {
        "name": "Common Crawl",
        "url": "https://commoncrawl.org/",
        "type": "s3",
        "size": "380TB total",
        "description": "Web crawl data. Filter for tech blogs, documentation, tutorials.",
        "relevance": "medium",
        "free": True,
    },
    "redpajama": {
        "name": "RedPajama (Together AI)",
        "url": "https://huggingface.co/datasets/togethercomputer/RedPajama-Data-V2",
        "type": "huggingface",
        "hf_dataset": "togethercomputer/RedPajama-Data-V2",
        "size": "30TB",
        "description": "30TB web data curated for LLM training. High quality, deduplicated.",
        "relevance": "high",
        "free": True,
    },
    "refinedweb": {
        "name": "RefinedWeb (Falcon)",
        "url": "https://huggingface.co/datasets/tiiuae/falcon-refinedweb",
        "type": "huggingface",
        "hf_dataset": "tiiuae/falcon-refinedweb",
        "size": "600GB+",
        "description": "High-quality filtered web data used to train Falcon models.",
        "relevance": "high",
        "free": True,
    },
    "openwebtext2": {
        "name": "OpenWebText2",
        "url": "https://huggingface.co/datasets/openwebtext2",
        "type": "huggingface",
        "hf_dataset": "openwebtext2",
        "size": "65GB",
        "description": "Curated web text dataset for language model training.",
        "relevance": "medium",
        "free": True,
    },
    "dolma": {
        "name": "Dolma (AI2)",
        "url": "https://huggingface.co/datasets/allenai/dolma",
        "type": "huggingface",
        "hf_dataset": "allenai/dolma",
        "size": "3TB",
        "description": "3TB curated dataset from AI2. Code, web, academic papers, books.",
        "relevance": "high",
        "free": True,
    },
}


@dataclass
class DownloadJob:
    source_id: str
    status: str = "pending"  # pending, downloading, processing, complete, failed
    progress_percent: float = 0
    bytes_downloaded: int = 0
    total_bytes: int = 0
    chunks_processed: int = 0
    chunks_verified: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    output_path: Optional[str] = None


def list_sources() -> List[Dict[str, Any]]:
    """List all available training data sources with sizes."""
    return [
        {
            "id": sid,
            "name": src["name"],
            "url": src["url"],
            "type": src["type"],
            "size": src["size"],
            "description": src["description"],
            "relevance": src["relevance"],
            "free": src["free"],
            "languages": src.get("languages", []),
        }
        for sid, src in DATA_SOURCES.items()
    ]


def get_download_instructions(source_id: str) -> Dict[str, Any]:
    """
    Get step-by-step instructions to download a specific dataset.
    These are designed to run on the user's local machine with storage.
    """
    source = DATA_SOURCES.get(source_id)
    if not source:
        return {"error": f"Unknown source: {source_id}"}

    instructions = {
        "source": source["name"],
        "size": source["size"],
        "url": source["url"],
    }

    if source["type"] == "huggingface":
        instructions["method"] = "huggingface_datasets"
        instructions["steps"] = [
            "pip install datasets huggingface_hub",
            f"# Python script to download:",
            f"from datasets import load_dataset",
            f"ds = load_dataset('{source.get('hf_dataset', '')}', streaming=True)",
            f"# Stream and save chunks:",
            f"for i, batch in enumerate(ds['train'].iter(batch_size=10000)):",
            f"    # Process and save batch to knowledge_base/training/",
            f"    pass",
        ]
        instructions["python_script"] = _generate_hf_download_script(source)

    elif source["type"] == "archive":
        instructions["method"] = "direct_download"
        instructions["steps"] = [
            f"# Download from: {source['url']}",
            "# Extract and filter for relevant content",
            "# Process into Grace's training format",
        ]

    elif source["type"] == "direct":
        instructions["method"] = "wget"
        instructions["steps"] = [
            f"wget {source.get('download_url', source['url'])}",
            "# Extract and process",
        ]

    elif source["type"] == "kaggle":
        instructions["method"] = "kaggle_cli"
        instructions["steps"] = [
            "pip install kaggle",
            "kaggle datasets download -d Cornell-University/arxiv",
        ]

    return instructions


def _generate_hf_download_script(source: Dict) -> str:
    """Generate a Python script to download and process a HuggingFace dataset."""
    dataset_id = source.get("hf_dataset", "")
    languages = source.get("languages", ["python"])

    return f'''#!/usr/bin/env python3
"""
Auto-generated script to download {source["name"]} for Grace training.
Run this on your local machine with sufficient storage.

Dataset: {dataset_id}
Size: {source["size"]}
"""

import os
import json
import hashlib
from pathlib import Path
from datasets import load_dataset

OUTPUT_DIR = Path("training_data/{dataset_id.replace("/", "_")}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LANGUAGES = {json.dumps(languages)}
MAX_FILE_SIZE = 100_000  # Skip files larger than 100KB
BATCH_SIZE = 5000
MAX_BATCHES = 200  # ~1M samples

print(f"Downloading {{dataset_id}}...")
print(f"Output: {{OUTPUT_DIR}}")
print(f"Languages: {{LANGUAGES}}")

ds = load_dataset("{dataset_id}", streaming=True, split="train")

batch_num = 0
total_samples = 0
total_bytes = 0

for batch in ds.iter(batch_size=BATCH_SIZE):
    if batch_num >= MAX_BATCHES:
        break

    samples = []
    for i in range(len(batch.get("content", batch.get("text", [])))):
        content = batch.get("content", batch.get("text", []))[i]
        lang = batch.get("lang", batch.get("language", ["unknown"] * len(batch.get("content", []))))[i]

        if lang not in LANGUAGES and LANGUAGES != ["all"]:
            continue
        if len(content) > MAX_FILE_SIZE:
            continue
        if len(content) < 50:
            continue

        samples.append({{
            "content": content,
            "language": lang,
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
        }})

    if samples:
        output_file = OUTPUT_DIR / f"batch_{{batch_num:06d}}.jsonl"
        with open(output_file, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\\n")
        total_samples += len(samples)
        total_bytes += output_file.stat().st_size
        print(f"Batch {{batch_num}}: {{len(samples)}} samples ({{total_bytes/1024/1024:.1f}} MB total)")

    batch_num += 1

print(f"\\nDone! {{total_samples}} samples, {{total_bytes/1024/1024:.1f}} MB")
print(f"Copy {{OUTPUT_DIR}} to Grace\\'s backend/knowledge_base/training/")
'''


def generate_all_download_scripts() -> Dict[str, str]:
    """Generate download scripts for all sources."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    scripts = {}

    for sid, source in DATA_SOURCES.items():
        if source["type"] == "huggingface":
            script = _generate_hf_download_script(source)
            script_path = PIPELINE_DIR / f"download_{sid}.py"
            script_path.write_text(script)
            scripts[sid] = str(script_path)

    return scripts


def get_recommended_plan(available_storage_gb: int = 1000) -> Dict[str, Any]:
    """
    Given available storage, recommend which datasets to download
    and in what order for maximum training value.
    """
    plan = {
        "available_storage_gb": available_storage_gb,
        "recommended_order": [],
        "total_estimated_gb": 0,
    }

    # Priority order based on relevance to Grace
    priority = [
        ("the_stack_v2", 100, "Start with Python subset only (~100GB)"),
        ("dolma", 200, "AI2's curated mix — code, web, academic (~200GB subset)"),
        ("stack_overflow", 50, "All Python/JS/architecture Q&A (~50GB)"),
        ("refinedweb", 100, "High-quality web text (~100GB subset)"),
        ("arxiv_papers", 30, "CS/AI papers (~30GB)"),
        ("redpajama", 200, "Web data for general knowledge (~200GB subset)"),
        ("github_code", 100, "Additional code samples (~100GB)"),
        ("wikipedia", 22, "General knowledge base (~22GB)"),
    ]

    running_total = 0
    for source_id, est_gb, note in priority:
        if running_total + est_gb > available_storage_gb:
            plan["recommended_order"].append({
                "source": source_id,
                "estimated_gb": est_gb,
                "note": f"SKIP — exceeds storage ({running_total + est_gb}GB > {available_storage_gb}GB)",
                "status": "skip",
            })
            continue

        plan["recommended_order"].append({
            "source": source_id,
            "estimated_gb": est_gb,
            "note": note,
            "status": "recommended",
            "name": DATA_SOURCES[source_id]["name"],
        })
        running_total += est_gb

    plan["total_estimated_gb"] = running_total
    return plan
