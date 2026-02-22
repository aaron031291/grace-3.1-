#!/usr/bin/env python3
"""
Bulk Knowledge Pipeline - Download massive datasets and convert to vectors.

Reality check:
  - Billions of vectors = 8TB+ (we have 106GB)
  - Ollama embedding = 1,000/hour (too slow)
  - Target: 500K-2M vectors from pre-processed sources

Sources (no auth required, free, massive):
  1. Stack Overflow data dump (structured Q&A, public)
  2. GitHub trending repos (top code examples)
  3. HuggingFace datasets (pre-processed code/text)
  4. Wikipedia API (structured knowledge)
  5. Python docs (stdlib reference)
  6. Common programming patterns (curated)

Strategy:
  Phase 1: Download structured data (no embedding needed for SQL storage)
  Phase 2: Batch embed with faster model for vector search
  Phase 3: Index everything for retrieval
"""

import sys
import os
import json
import time
import hashlib
import requests
import re
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType

config = DatabaseConfig(db_type=DatabaseType.SQLITE, database_path="data/documents.db")
DatabaseConnection.initialize(config)
from database.migrate_all import run_all_migrations
run_all_migrations()

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
Session = sessionmaker(bind=DatabaseConnection.get_engine())


def store_facts(facts: List[Dict], domain: str, source: str):
    """Bulk store facts efficiently."""
    session = Session()
    from cognitive.knowledge_compiler import CompiledFact, CompiledEntityRelation
    stored = 0
    for f in facts:
        try:
            session.add(CompiledFact(
                subject=str(f.get("subject", ""))[:256],
                predicate=str(f.get("predicate", ""))[:256],
                object_value=str(f.get("object", ""))[:2000],
                object_type=f.get("type", "text"),
                confidence=f.get("confidence", 0.8),
                domain=domain,
                verified=f.get("verified", True),
                source_text=f"{source}:{f.get('source_id', '')}"[:500],
                tags={"source": source, "bulk": True},
            ))
            stored += 1
        except Exception:
            pass
        if stored % 500 == 0 and stored > 0:
            session.commit()
    session.commit()
    session.close()
    return stored


# =====================================================================
# SOURCE 1: GitHub - Top repos across languages and domains
# =====================================================================

def download_github_bulk(topics: List[str], repos_per_topic: int = 30) -> int:
    """Download top GitHub repos: descriptions, READMEs, topics."""
    print("\n[GITHUB] Downloading top repos across topics...")
    total = 0

    for topic in topics:
        facts = []
        try:
            for page in range(1, (repos_per_topic // 30) + 2):
                resp = requests.get(
                    "https://api.github.com/search/repositories",
                    params={"q": topic, "sort": "stars", "per_page": 30, "page": page},
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=15,
                )
                if resp.status_code == 403:
                    print(f"  [RATE] GitHub rate limited, waiting 60s...")
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    break

                for repo in resp.json().get("items", []):
                    name = repo.get("full_name", "")
                    desc = repo.get("description", "") or ""
                    stars = repo.get("stargazers_count", 0)
                    lang = repo.get("language", "") or ""
                    topics_list = repo.get("topics", [])

                    facts.append({
                        "subject": name,
                        "predicate": "github_repo",
                        "object": f"{desc}. Language: {lang}. Stars: {stars}. Topics: {', '.join(topics_list[:5])}",
                        "confidence": min(0.95, 0.4 + stars / 5000),
                        "source_id": repo.get("html_url", ""),
                    })

                time.sleep(1)

        except Exception as e:
            print(f"  [ERR] {topic}: {e}")

        if facts:
            stored = store_facts(facts, topic.replace(" ", "_"), "github_bulk")
            total += stored
            print(f"  [OK] {topic}: {stored} repos")

    print(f"  Total GitHub: {total}")
    return total


# =====================================================================
# SOURCE 2: Stack Exchange - Top Q&A across sites
# =====================================================================

def download_stackoverflow_bulk(tags: List[str], questions_per_tag: int = 100) -> int:
    """Download top StackOverflow Q&A with accepted answers."""
    print("\n[STACKOVERFLOW] Downloading top Q&A...")
    total = 0

    for tag in tags:
        facts = []
        try:
            for page in range(1, (questions_per_tag // 30) + 2):
                resp = requests.get(
                    "https://api.stackexchange.com/2.3/questions",
                    params={
                        "tagged": tag, "site": "stackoverflow",
                        "sort": "votes", "order": "desc",
                        "pagesize": 30, "page": page,
                        "filter": "withbody",
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                for q in data.get("items", []):
                    title = q.get("title", "")
                    body = q.get("body", "")
                    score = q.get("score", 0)
                    answered = q.get("is_answered", False)
                    q_tags = q.get("tags", [])

                    # Strip HTML from body
                    clean_body = re.sub(r'<[^>]+>', '', body)[:500]

                    facts.append({
                        "subject": title[:256],
                        "predicate": "stackoverflow_qa",
                        "object": f"{clean_body}. Score: {score}. Answered: {answered}. Tags: {', '.join(q_tags[:5])}",
                        "confidence": min(0.9, 0.3 + score / 50),
                        "type": "code" if "```" in body or "<code>" in body else "text",
                        "verified": answered,
                        "source_id": str(q.get("question_id", "")),
                    })

                if data.get("has_more") is False:
                    break
                time.sleep(0.5)

        except Exception as e:
            print(f"  [ERR] {tag}: {e}")

        if facts:
            stored = store_facts(facts, f"stackoverflow_{tag}", "stackoverflow_bulk")
            total += stored
            print(f"  [OK] {tag}: {stored} Q&A")

    print(f"  Total SO: {total}")
    return total


# =====================================================================
# SOURCE 3: Python Standard Library Documentation
# =====================================================================

def download_python_docs() -> int:
    """Download Python stdlib module docs."""
    print("\n[PYTHON DOCS] Downloading stdlib documentation...")

    modules = [
        "os", "sys", "json", "re", "datetime", "collections", "itertools",
        "functools", "typing", "pathlib", "subprocess", "threading",
        "asyncio", "logging", "unittest", "dataclasses", "abc",
        "contextlib", "hashlib", "hmac", "secrets", "sqlite3",
        "http.client", "urllib.parse", "socket", "ssl", "email",
        "argparse", "configparser", "csv", "io", "tempfile",
        "shutil", "glob", "fnmatch", "stat", "struct", "codecs",
        "pprint", "textwrap", "difflib", "enum", "queue",
        "heapq", "bisect", "array", "weakref", "copy",
        "math", "random", "statistics", "decimal", "fractions",
    ]

    facts = []
    for mod in modules:
        try:
            m = __import__(mod)
            doc = getattr(m, '__doc__', '') or ''

            # Get all public functions/classes
            members = [name for name in dir(m) if not name.startswith('_')]
            public_funcs = []
            for name in members[:20]:
                obj = getattr(m, name, None)
                if callable(obj):
                    sig = ""
                    try:
                        import inspect
                        sig = str(inspect.signature(obj))
                    except (ValueError, TypeError):
                        pass
                    obj_doc = getattr(obj, '__doc__', '') or ''
                    public_funcs.append(f"{name}{sig}: {obj_doc[:100]}")

            facts.append({
                "subject": f"python::{mod}",
                "predicate": "stdlib_module",
                "object": f"{doc[:300]}. Key functions: {'; '.join(public_funcs[:10])}",
                "type": "code",
                "confidence": 1.0,
                "source_id": f"python_stdlib:{mod}",
            })

            # Individual function entries for high-value modules
            if mod in ("os", "json", "re", "datetime", "collections", "asyncio", "pathlib", "typing"):
                for func_info in public_funcs[:15]:
                    name_part = func_info.split(":")[0].split("(")[0]
                    facts.append({
                        "subject": f"python::{mod}.{name_part}",
                        "predicate": "function_reference",
                        "object": func_info[:500],
                        "type": "code",
                        "confidence": 1.0,
                        "source_id": f"python_stdlib:{mod}.{name_part}",
                    })

        except ImportError:
            pass

    stored = store_facts(facts, "python_stdlib", "python_docs")
    print(f"  [OK] {stored} stdlib entries")
    return stored


# =====================================================================
# SOURCE 4: Programming Concepts Encyclopedia
# =====================================================================

def download_programming_concepts() -> int:
    """Curated programming concepts that every coder needs."""
    print("\n[CONCEPTS] Storing programming encyclopedia...")

    concepts = [
        # Data Structures
        ("Array", "data_structures", "Contiguous memory block for indexed access. O(1) read, O(n) insert. Use when: fixed size, random access needed. Python: list. Java: ArrayList."),
        ("LinkedList", "data_structures", "Chain of nodes with pointers. O(1) insert/delete at head, O(n) search. Use when: frequent insertions/deletions. Python: collections.deque."),
        ("HashMap", "data_structures", "Key-value store with O(1) average lookup via hashing. Use when: need fast key-based access. Python: dict. Java: HashMap. Handle collisions: chaining or open addressing."),
        ("BinaryTree", "data_structures", "Hierarchical structure where each node has at most 2 children. BST: left < root < right. O(log n) operations when balanced."),
        ("Stack", "data_structures", "LIFO data structure. O(1) push/pop. Use for: undo systems, expression parsing, DFS. Python: list (append/pop) or collections.deque."),
        ("Queue", "data_structures", "FIFO data structure. O(1) enqueue/dequeue. Use for: BFS, task scheduling, buffering. Python: collections.deque or queue.Queue."),
        ("Heap", "data_structures", "Complete binary tree where parent >= children (max-heap) or parent <= children (min-heap). O(log n) insert/extract. Python: heapq module."),
        ("Trie", "data_structures", "Tree for string prefix matching. O(m) lookup where m is key length. Use for: autocomplete, spell checking, IP routing."),
        ("Graph", "data_structures", "Vertices connected by edges. Representations: adjacency list (sparse), adjacency matrix (dense). Algorithms: BFS, DFS, Dijkstra, Bellman-Ford."),
        ("BloomFilter", "data_structures", "Probabilistic set membership test. No false negatives, possible false positives. Use for: cache filtering, duplicate detection. Space-efficient."),
        # Algorithms
        ("BinarySearch", "algorithms", "Search sorted array by halving. O(log n). Template: left, right = 0, len(arr)-1; while left <= right: mid = (left+right)//2."),
        ("QuickSort", "algorithms", "Divide-and-conquer sort. Average O(n log n), worst O(n²). Pick pivot, partition, recurse. In-place. Python: sorted() uses Timsort instead."),
        ("MergeSort", "algorithms", "Divide-and-conquer sort. Always O(n log n). Stable. Uses O(n) extra space. Good for linked lists and external sorting."),
        ("DFS", "algorithms", "Depth-First Search. Explore as far as possible before backtracking. Stack-based (recursive or explicit). Use for: cycle detection, topological sort, path finding."),
        ("BFS", "algorithms", "Breadth-First Search. Explore all neighbors before going deeper. Queue-based. Use for: shortest path (unweighted), level-order traversal."),
        ("DynamicProgramming", "algorithms", "Break problem into overlapping subproblems. Memoize results. Bottom-up (tabulation) or top-down (recursion + cache). Key: identify state and transition."),
        ("Dijkstra", "algorithms", "Shortest path in weighted graph (non-negative edges). O((V+E) log V) with priority queue. Python: heapq."),
        ("TwoPointers", "algorithms", "Two indices moving through array. Use for: sorted array problems, palindrome check, container with most water. O(n) time."),
        ("SlidingWindow", "algorithms", "Fixed or variable window over array/string. Track window state as it moves. Use for: subarray sum, longest substring, min window substring."),
        ("Backtracking", "algorithms", "Try all possibilities, undo on failure. Use for: N-queens, sudoku, permutations, combinations. Prune invalid branches early."),
        # Design Principles
        ("SOLID_S", "design_principles", "Single Responsibility: A class should have one reason to change. If a class does too many things, split it."),
        ("SOLID_O", "design_principles", "Open/Closed: Open for extension, closed for modification. Use interfaces/abstract classes to extend behavior without changing existing code."),
        ("SOLID_L", "design_principles", "Liskov Substitution: Subtypes must be substitutable for their base types. If Square extends Rectangle, it must work wherever Rectangle is used."),
        ("SOLID_I", "design_principles", "Interface Segregation: Clients shouldn't depend on interfaces they don't use. Split fat interfaces into focused ones."),
        ("SOLID_D", "design_principles", "Dependency Inversion: Depend on abstractions, not concretions. High-level modules shouldn't depend on low-level modules."),
        ("DRY", "design_principles", "Don't Repeat Yourself. Extract shared logic into functions/classes. But don't over-abstract - WET (Write Everything Twice) is sometimes OK."),
        ("KISS", "design_principles", "Keep It Simple, Stupid. The simplest solution that works is usually the best. Complexity is the enemy of reliability."),
        ("YAGNI", "design_principles", "You Ain't Gonna Need It. Don't build features until they're needed. Premature abstraction is as bad as premature optimization."),
        # Networking
        ("HTTP", "networking", "Hypertext Transfer Protocol. Methods: GET (read), POST (create), PUT (update), DELETE (remove), PATCH (partial update). Status: 2xx success, 4xx client error, 5xx server error."),
        ("TCP", "networking", "Transmission Control Protocol. Reliable, ordered, connection-oriented. 3-way handshake (SYN, SYN-ACK, ACK). Flow control with sliding window."),
        ("DNS", "networking", "Domain Name System. Resolves domain names to IP addresses. Record types: A (IPv4), AAAA (IPv6), CNAME (alias), MX (mail), TXT (text)."),
        ("WebSocket", "networking", "Full-duplex communication over single TCP connection. Upgrade from HTTP. Use for: real-time apps, chat, live data feeds."),
        ("REST", "networking", "Representational State Transfer. Resources identified by URLs. Stateless. HATEOAS. Use HTTP methods semantically."),
        ("gRPC", "networking", "Remote Procedure Call with Protocol Buffers. Binary format, HTTP/2, streaming. Faster than REST for service-to-service communication."),
        # Concurrency
        ("Thread", "concurrency", "OS-level thread for parallel execution. Python GIL limits CPU parallelism. Use threading for I/O-bound, multiprocessing for CPU-bound."),
        ("AsyncAwait", "concurrency", "Cooperative multitasking with event loop. async def declares coroutine, await suspends. Use for: I/O-bound operations, network requests."),
        ("Mutex", "concurrency", "Mutual exclusion lock. Prevents concurrent access to shared resource. Python: threading.Lock(). Always use with 'with' statement."),
        ("Semaphore", "concurrency", "Counter-based lock allowing N concurrent accesses. Use for: connection pools, rate limiting. Python: threading.Semaphore(N)."),
        ("Deadlock", "concurrency", "Two+ threads waiting for each other's locks. Prevention: lock ordering, timeout, try-lock. Detection: resource allocation graph."),
        # Git
        ("GitBranching", "git", "git branch feature; git checkout feature; git merge feature. Strategies: feature branches, git flow, trunk-based. Rebase for linear history."),
        ("GitConflict", "git", "Occurs when same lines changed in different branches. Resolution: edit conflicted files, remove markers (<<<<<<, ======, >>>>>>), git add, git commit."),
    ]

    facts = []
    for name, domain, desc in concepts:
        facts.append({
            "subject": name,
            "predicate": "programming_concept",
            "object": desc,
            "confidence": 0.98,
            "type": "code" if any(kw in desc for kw in ["O(", "def ", "import ", "()."]) else "text",
            "source_id": f"encyclopedia:{name}",
        })

    stored = store_facts(facts, "programming_concepts", "encyclopedia")
    print(f"  [OK] {stored} concepts")
    return stored


# =====================================================================
# SOURCE 5: arXiv CS papers (bulk)
# =====================================================================

def download_arxiv_bulk(queries: List[str], per_query: int = 50) -> int:
    """Download arXiv CS paper abstracts in bulk."""
    print("\n[ARXIV] Downloading research paper abstracts...")
    total = 0

    for query in queries:
        facts = []
        try:
            resp = requests.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": f"cat:cs.* AND all:{query}", "max_results": per_query, "sortBy": "relevance"},
                timeout=30,
            )
            if resp.status_code == 200:
                entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
                for entry in entries:
                    title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    if title and summary:
                        facts.append({
                            "subject": title.group(1).strip().replace('\n', ' ')[:256],
                            "predicate": "research_paper",
                            "object": summary.group(1).strip().replace('\n', ' ')[:1000],
                            "confidence": 0.92,
                            "source_id": f"arxiv:{query}",
                        })
        except Exception as e:
            print(f"  [ERR] {query}: {e}")

        if facts:
            stored = store_facts(facts, "research_papers", "arxiv_bulk")
            total += stored
            print(f"  [OK] {query}: {stored} papers")

        time.sleep(3)  # arXiv rate limiting

    print(f"  Total arXiv: {total}")
    return total


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BULK KNOWLEDGE PIPELINE")
    print("=" * 70)

    # Check current state
    session = Session()
    from cognitive.knowledge_compiler import CompiledFact
    current = session.query(func.count(CompiledFact.id)).scalar()
    print(f"Current facts: {current}")
    session.close()

    grand_total = 0

    # Phase 1: GitHub bulk (top repos across SE domains)
    github_topics = [
        "python", "javascript", "typescript", "rust", "go",
        "react", "vue", "fastapi", "django", "flask",
        "docker", "kubernetes", "terraform", "ansible",
        "machine learning", "deep learning", "nlp", "computer vision",
        "database", "redis", "postgresql", "mongodb",
        "testing", "ci cd", "devops", "microservices",
        "api design", "graphql", "grpc", "websocket",
    ]
    grand_total += download_github_bulk(github_topics, repos_per_topic=30)

    # Phase 2: Stack Overflow (top Q&A)
    so_tags = [
        "python", "javascript", "typescript", "react", "docker",
        "sql", "postgresql", "redis", "fastapi", "flask",
        "git", "linux", "bash", "kubernetes", "terraform",
        "machine-learning", "deep-learning", "pytorch", "tensorflow",
        "rest", "graphql", "websocket", "async", "testing",
    ]
    grand_total += download_stackoverflow_bulk(so_tags, questions_per_tag=50)

    # Phase 3: Python stdlib docs
    grand_total += download_python_docs()

    # Phase 4: Programming concepts encyclopedia
    grand_total += download_programming_concepts()

    # Phase 5: arXiv papers
    arxiv_queries = [
        "software engineering", "machine learning", "deep learning",
        "natural language processing", "reinforcement learning",
        "distributed systems", "database systems", "computer security",
    ]
    grand_total += download_arxiv_bulk(arxiv_queries, per_query=30)

    # Final report
    session = Session()
    final = session.query(func.count(CompiledFact.id)).scalar()
    code_patterns = session.query(func.count(CompiledFact.id)).filter(CompiledFact.object_type == "code").scalar()
    domains = session.query(CompiledFact.domain).distinct().count()
    session.close()

    print("\n" + "=" * 70)
    print("BULK PIPELINE COMPLETE")
    print(f"  Added: {grand_total} facts")
    print(f"  Total facts: {final}")
    print(f"  Code patterns: {code_patterns}")
    print(f"  Domains: {domains}")
    print("=" * 70)
