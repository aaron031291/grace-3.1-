#!/usr/bin/env python3
"""
Build Vector Store - Fast bulk vectorization of ALL knowledge.

Uses sentence-transformers (7.6M vectors/hour) instead of Ollama (1K/hour).
Creates a new 384-dim collection alongside the existing 2048-dim one.

Phases:
  1. Vectorize all 22K+ compiled facts from SQL
  2. Download and vectorize CodeSearchNet (600K+ code functions)
  3. Verify with search queries
"""

import sys
import os
import time
import hashlib
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

QDRANT_PATH = "/workspace/qdrant_unified"
COLLECTION = "knowledge"  # New 384-dim collection

def setup_collection():
    """Create 384-dim collection if it doesn't exist."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance

    lock = os.path.join(QDRANT_PATH, ".lock")
    if os.path.exists(lock):
        os.remove(lock)

    qc = QdrantClient(path=QDRANT_PATH)
    collections = [c.name for c in qc.get_collections().collections]

    if COLLECTION not in collections:
        qc.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        print(f"[OK] Created collection '{COLLECTION}' (384-dim)")
    else:
        info = qc.get_collection(COLLECTION)
        print(f"[OK] Collection '{COLLECTION}' exists: {info.points_count} vectors")

    qc.close()


def phase1_vectorize_facts():
    """Vectorize all compiled facts from SQL."""
    print("\n" + "=" * 60)
    print("PHASE 1: Vectorize compiled facts")
    print("=" * 60)

    from database.connection import DatabaseConnection
    from database.config import DatabaseConfig, DatabaseType
    config = DatabaseConfig(db_type=DatabaseType.SQLITE, database_path="data/documents.db")
    DatabaseConnection.initialize(config)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=DatabaseConnection.get_engine())
    session = Session()

    from cognitive.knowledge_compiler import CompiledFact
    facts = session.query(CompiledFact).all()
    print(f"  Facts to vectorize: {len(facts)}")

    from embedding.fast_embedder import embed_texts
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    lock = os.path.join(QDRANT_PATH, ".lock")
    if os.path.exists(lock):
        os.remove(lock)
    qc = QdrantClient(path=QDRANT_PATH)

    batch_size = 256
    total = 0
    start = time.time()

    for i in range(0, len(facts), batch_size):
        batch = facts[i:i + batch_size]
        texts = []
        points_meta = []

        for f in batch:
            text = f"{f.subject}: {f.object_value}"[:500]
            vid = hashlib.md5(text[:200].encode()).hexdigest()
            texts.append(text)
            points_meta.append((vid, {
                "text": text[:1000],
                "subject": (f.subject or "")[:200],
                "predicate": (f.predicate or "")[:100],
                "domain": f.domain or "general",
                "confidence": f.confidence or 0.5,
                "type": f.object_type or "text",
                "source": "compiled_fact",
            }))

        embeddings = embed_texts(texts, batch_size=batch_size)
        points = [
            PointStruct(id=points_meta[j][0], vector=embeddings[j], payload=points_meta[j][1])
            for j in range(len(texts))
        ]
        qc.upsert(collection_name=COLLECTION, points=points)
        total += len(points)

        if total % 2000 == 0 or i + batch_size >= len(facts):
            elapsed = time.time() - start
            rate = total / max(elapsed, 0.1)
            print(f"  Vectorized: {total}/{len(facts)} ({rate:.0f}/sec)")

    info = qc.get_collection(COLLECTION)
    print(f"  Collection '{COLLECTION}': {info.points_count} vectors")
    qc.close()
    session.close()
    return total


def phase2_codesearchnet():
    """Download and vectorize CodeSearchNet dataset."""
    print("\n" + "=" * 60)
    print("PHASE 2: CodeSearchNet (code function embeddings)")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  [SKIP] 'datasets' not installed")
        return 0

    from embedding.fast_embedder import embed_texts
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    lock = os.path.join(QDRANT_PATH, ".lock")
    if os.path.exists(lock):
        os.remove(lock)
    qc = QdrantClient(path=QDRANT_PATH)

    languages = ["python", "javascript", "go"]
    total = 0
    target_per_lang = 100_000  # 100K per language = 300K total

    for lang in languages:
        print(f"\n  [{lang.upper()}] Loading CodeSearchNet...")
        try:
            ds = load_dataset(
                "code_search_net", lang,
                split="train",
                streaming=True,
                trust_remote_code=True,
            )

            batch_texts = []
            batch_meta = []
            lang_count = 0

            for example in ds:
                if lang_count >= target_per_lang:
                    break

                docstring = example.get("func_documentation_string", "") or ""
                code = example.get("func_code_string", "") or ""
                name = example.get("func_name", "") or ""
                repo = example.get("repository_name", "") or ""

                if not code or len(code) < 20:
                    continue

                text = f"{name}: {docstring[:200]} | {code[:300]}" if docstring else f"{name}: {code[:500]}"
                vid = hashlib.md5(f"{repo}:{name}:{code[:100]}".encode()).hexdigest()

                batch_texts.append(text)
                batch_meta.append((vid, {
                    "text": text[:1000],
                    "subject": name[:200],
                    "predicate": "code_function",
                    "domain": f"codesearchnet_{lang}",
                    "language": lang,
                    "repo": repo[:200],
                    "type": "code",
                    "confidence": 0.85,
                    "source": "codesearchnet",
                }))

                if len(batch_texts) >= 512:
                    embeddings = embed_texts(batch_texts, batch_size=512)
                    points = [
                        PointStruct(id=batch_meta[j][0], vector=embeddings[j], payload=batch_meta[j][1])
                        for j in range(len(batch_texts))
                    ]
                    qc.upsert(collection_name=COLLECTION, points=points)
                    total += len(points)
                    lang_count += len(points)
                    batch_texts = []
                    batch_meta = []

                    if lang_count % 10000 == 0:
                        print(f"    {lang}: {lang_count}/{target_per_lang}")

            # Flush remaining
            if batch_texts:
                embeddings = embed_texts(batch_texts, batch_size=512)
                points = [
                    PointStruct(id=batch_meta[j][0], vector=embeddings[j], payload=batch_meta[j][1])
                    for j in range(len(batch_texts))
                ]
                qc.upsert(collection_name=COLLECTION, points=points)
                total += len(points)
                lang_count += len(points)

            print(f"    {lang}: {lang_count} functions vectorized")

        except Exception as e:
            print(f"    {lang}: ERROR - {str(e)[:100]}")

    info = qc.get_collection(COLLECTION)
    print(f"\n  Collection '{COLLECTION}': {info.points_count} vectors")
    qc.close()
    return total


def phase3_verify():
    """Verify the vector store works with search queries."""
    print("\n" + "=" * 60)
    print("PHASE 3: Verification")
    print("=" * 60)

    from embedding.fast_embedder import embed_single
    from qdrant_client import QdrantClient

    lock = os.path.join(QDRANT_PATH, ".lock")
    if os.path.exists(lock):
        os.remove(lock)
    qc = QdrantClient(path=QDRANT_PATH)

    queries = [
        "How to create a FastAPI endpoint",
        "Sort a list in Python",
        "Docker container networking",
        "Machine learning classification",
        "SQL database query optimization",
        "async await pattern in Python",
        "React component state management",
        "Kubernetes pod deployment",
    ]

    for q in queries:
        emb = embed_single(q)
        results = qc.query_points(collection_name=COLLECTION, query=emb, limit=3)
        if results and hasattr(results, "points") and results.points:
            top = results.points[0]
            text_preview = top.payload.get("text", "")[:80]
            score = top.score
            domain = top.payload.get("domain", "?")
            print(f"  Q: {q[:40]:40s} -> [{domain:20s}] score={score:.3f} | {text_preview}")
        else:
            print(f"  Q: {q[:40]:40s} -> NO RESULTS")

    info = qc.get_collection(COLLECTION)
    print(f"\n  FINAL: {info.points_count} vectors in '{COLLECTION}'")
    qc.close()


if __name__ == "__main__":
    print("=" * 60)
    print("BUILD VECTOR STORE")
    print("Fast embedder: all-MiniLM-L6-v2 (384-dim, 7.6M/hour)")
    print("=" * 60)

    setup_collection()

    t1 = phase1_vectorize_facts()
    print(f"\n  Phase 1 complete: {t1} fact vectors")

    t2 = phase2_codesearchnet()
    print(f"\n  Phase 2 complete: {t2} code vectors")

    phase3_verify()

    print("\n" + "=" * 60)
    print(f"TOTAL VECTORS: {t1 + t2}")
    print("=" * 60)
