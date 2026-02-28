#!/usr/bin/env python3
"""
Training Data Downloader — Pull 2TB of open-source data into Grace's Oracle.

Run: python scripts/download_training_data.py

Downloads in order of value:
  1. Stack Overflow Python Q&A (~10GB)
  2. The Stack v2 Python subset (~100GB)
  3. OWASP Security data (~1GB)
  4. RefinedWeb (~100GB subset)
  5. ArXiv CS/AI papers (~30GB)

Each batch streams to disk, then ingests into Oracle.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "training_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def download_huggingface(dataset_id: str, output_dir: Path, languages: list = None,
                         max_samples: int = 100000, batch_size: int = 5000):
    """Stream download from HuggingFace datasets."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Installing datasets library...")
        os.system(f"{sys.executable} -m pip install datasets huggingface_hub")
        from datasets import load_dataset

    print(f"\nDownloading: {dataset_id}")
    print(f"Output: {output_dir}")
    print(f"Max samples: {max_samples}")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        ds = load_dataset(dataset_id, streaming=True, split="train", trust_remote_code=True)

        batch_num = 0
        total_samples = 0
        total_bytes = 0

        for batch in ds.iter(batch_size=batch_size):
            if total_samples >= max_samples:
                break

            # Get content field (different datasets use different names)
            content_field = None
            for field in ["content", "text", "code", "body", "answer_body", "question_body", "answer", "question"]:
                if field in batch:
                    content_field = field
                    break

            if not content_field:
                # Try combining question + answer for Q&A datasets
                if "question_body" in batch and "answer_body" in batch:
                    content_field = "__combined_qa__"
                else:
                    print(f"  No content field found. Fields: {list(batch.keys())[:5]}")
                    continue

            samples = []
            if content_field == "__combined_qa__":
                questions = batch["question_body"]
                answers = batch["answer_body"]
                titles = batch.get("title", [""] * len(questions))
                contents = [f"Q: {titles[i]}\n{questions[i]}\n\nA: {answers[i]}" 
                           for i in range(len(questions))]
            else:
                contents = batch[content_field]
            for i, content in enumerate(contents):
                if not content or len(str(content)) < 50:
                    continue
                if len(str(content)) > 100000:
                    continue

                # Language filter
                if languages:
                    lang = batch.get("lang", batch.get("language", [None] * len(contents)))[i]
                    if lang and lang not in languages:
                        continue

                samples.append({"content": str(content)[:50000], "index": total_samples + len(samples)})

            if samples:
                output_file = output_dir / f"batch_{batch_num:06d}.jsonl"
                with open(output_file, "w") as f:
                    for sample in samples:
                        f.write(json.dumps(sample) + "\n")

                total_samples += len(samples)
                total_bytes += output_file.stat().st_size
                print(f"  Batch {batch_num}: {len(samples)} samples ({total_bytes / 1024 / 1024:.1f} MB total, {total_samples} samples)")

            batch_num += 1

        print(f"  Done: {total_samples} samples, {total_bytes / 1024 / 1024:.1f} MB")
        return {"samples": total_samples, "bytes": total_bytes}

    except Exception as e:
        print(f"  Error: {e}")
        return {"error": str(e)}


def ingest_to_oracle(data_dir: Path, source_name: str):
    """Ingest downloaded data into Oracle (learning_examples)."""
    print(f"\nIngesting {source_name} to Oracle...")

    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()

        count = 0
        for f in sorted(data_dir.glob("*.jsonl")):
            with open(f) as fh:
                for line in fh:
                    try:
                        sample = json.loads(line)
                        content = sample.get("content", "")
                        if len(content) > 50:
                            mem.store_learning(
                                input_ctx=f"Training data ({source_name})",
                                expected=content[:5000],
                                trust=0.6,
                                source=f"training_{source_name}",
                                example_type="training_data",
                            )
                            count += 1
                            if count % 100 == 0:
                                print(f"  Ingested: {count}")
                    except Exception:
                        continue

        print(f"  Total ingested: {count}")
        return count
    except Exception as e:
        print(f"  Ingest error: {e}")
        return 0


def main():
    print("=" * 60)
    print("  Grace Training Data Downloader")
    print("  Target: 2TB across multiple sources")
    print("=" * 60)

    sources = [
        {
            "name": "stack_overflow_python",
            "dataset": "koutch/stackoverflow_python",
            "dir": DOWNLOAD_DIR / "stackoverflow_python",
            "max": 200000,
            "desc": "Stack Overflow Python Q&A",
        },
        {
            "name": "the_stack_python",
            "dataset": "bigcode/the-stack-v2-train-smol-ids",
            "dir": DOWNLOAD_DIR / "the_stack_python",
            "languages": ["Python"],
            "max": 500000,
            "desc": "The Stack v2 — Python source code",
        },
        {
            "name": "refinedweb",
            "dataset": "tiiuae/falcon-refinedweb",
            "dir": DOWNLOAD_DIR / "refinedweb",
            "max": 200000,
            "desc": "RefinedWeb — high-quality web text",
        },
    ]

    for src in sources:
        print(f"\n{'='*40}")
        print(f"  Source: {src['desc']}")
        print(f"{'='*40}")

        result = download_huggingface(
            dataset_id=src["dataset"],
            output_dir=src["dir"],
            languages=src.get("languages"),
            max_samples=src["max"],
        )

        if not result.get("error"):
            ingest_to_oracle(src["dir"], src["name"])

    # Summary
    total_size = sum(
        sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        for d in DOWNLOAD_DIR.iterdir() if d.is_dir()
    )
    print(f"\n{'='*60}")
    print(f"  Download complete: {total_size / 1024 / 1024 / 1024:.2f} GB total")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
