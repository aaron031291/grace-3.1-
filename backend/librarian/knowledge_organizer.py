"""
Knowledge Base Organizer

Auto-organizes the knowledge base into domain folders.
The librarian categorizes every ingested document and places it
into the correct domain directory.

Structure:
  knowledge_base/
    algorithms/
      Algorithm_Design_With_Haskell.pdf
      Intro_Algorithms_Data_Structures.txt
    architecture/
      Software_Architecture_in_Practice.txt
      Patterns_for_API_Design.pdf
    security/
      OWASP_Cheat_Sheets.md
      Cyber_Security_SOAR.txt
    ...

Each domain folder has a _manifest.json with:
- Document list with Genesis keys
- Trust scores per document
- Total coverage score
- Last updated timestamp

The frontend can browse this like a file manager and upload
documents directly to specific domain folders.

Classes:
- `KnowledgeOrganizer`

Key Methods:
- `classify_document()`
- `organize_file()`
- `organize_all()`
- `get_domain_structure()`
- `get_coverage_report()`
- `get_knowledge_organizer()`

Database Tables:
None (no DB tables)

Connects To:
Self-contained
"""

import logging
import os
import json
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# Domain taxonomy — maps keywords to domain folders
DOMAIN_TAXONOMY = {
    "algorithms": {
        "keywords": ["algorithm", "sorting", "searching", "data structure", "binary", "tree", "graph", "hashing", "dynamic programming", "greedy", "divide and conquer", "complexity", "big o"],
        "description": "Algorithms, data structures, and computational complexity",
    },
    "architecture": {
        "keywords": ["architecture", "design pattern", "microservice", "monolith", "modular", "layered", "hexagonal", "clean architecture", "enterprise", "TOGAF", "bounded context"],
        "description": "Software architecture, design patterns, and system design",
    },
    "api_design": {
        "keywords": ["api", "rest", "graphql", "endpoint", "openapi", "swagger", "grpc", "protocol buffer"],
        "description": "API design patterns, REST, GraphQL, and interface contracts",
    },
    "databases": {
        "keywords": ["sql", "nosql", "database", "query", "schema", "table", "index", "mongodb", "postgresql", "qdrant", "vector db", "redis"],
        "description": "Databases, SQL, NoSQL, and data storage",
    },
    "devops": {
        "keywords": ["devops", "ci/cd", "pipeline", "docker", "kubernetes", "terraform", "ansible", "deployment", "container", "orchestration", "azure devops", "github actions"],
        "description": "DevOps, CI/CD, containers, and infrastructure as code",
    },
    "security": {
        "keywords": ["security", "cybersecurity", "owasp", "encryption", "authentication", "authorization", "vulnerability", "penetration", "firewall", "ccsp", "devsecops"],
        "description": "Cybersecurity, application security, and compliance",
    },
    "ai_ml": {
        "keywords": ["machine learning", "deep learning", "neural network", "ai", "artificial intelligence", "nlp", "reinforcement", "training", "model", "pytorch", "tensorflow", "embedding", "transformer"],
        "description": "AI, machine learning, deep learning, and NLP",
    },
    "languages": {
        "keywords": ["python", "javascript", "typescript", "rust", "go", "java", "haskell", "c programming", "swift", "php", "prolog"],
        "description": "Programming languages and language-specific guides",
    },
    "frontend": {
        "keywords": ["react", "next.js", "vue", "angular", "css", "html", "frontend", "ui", "ux", "component", "jsx", "dom"],
        "description": "Frontend development, React, and web UI",
    },
    "testing": {
        "keywords": ["test", "tdd", "unit test", "integration test", "pytest", "jest", "coverage", "assertion", "mock"],
        "description": "Testing, TDD, and quality assurance",
    },
    "engineering_practice": {
        "keywords": ["clean code", "refactoring", "pragmatic", "software engineering", "craft", "agile", "scrum", "code review", "git"],
        "description": "Software engineering practices, methodologies, and craft",
    },
    "distributed_systems": {
        "keywords": ["distributed", "consensus", "replication", "partition", "cap theorem", "eventual consistency", "streaming", "kafka", "message queue", "event driven"],
        "description": "Distributed systems, consensus, and event streaming",
    },
    "networking": {
        "keywords": ["network", "tcp", "ip", "http", "dns", "socket", "protocol", "osi", "routing", "vpn", "wireless"],
        "description": "Computer networking, protocols, and communication",
    },
    "operating_systems": {
        "keywords": ["operating system", "kernel", "process", "thread", "memory management", "file system", "scheduling", "linux", "unix"],
        "description": "Operating systems, Linux, and system internals",
    },
    "compiler_theory": {
        "keywords": ["compiler", "parser", "lexer", "syntax", "grammar", "ast", "semantic", "code generation", "programming language theory"],
        "description": "Compilers, parsers, and programming language theory",
    },
    "cloud": {
        "keywords": ["cloud", "aws", "azure", "gcp", "oracle cloud", "iaas", "paas", "saas", "serverless", "lambda"],
        "description": "Cloud computing, AWS, Azure, GCP",
    },
    "concurrency": {
        "keywords": ["concurrency", "parallel", "async", "await", "thread", "lock", "mutex", "actor", "goroutine", "channel"],
        "description": "Concurrency, parallelism, and async programming",
    },
    "ddd": {
        "keywords": ["domain driven", "ddd", "aggregate", "value object", "entity", "repository pattern", "ubiquitous language", "bounded context"],
        "description": "Domain-Driven Design",
    },
}


class KnowledgeOrganizer:
    """
    Organizes the knowledge base into domain folders.

    The librarian calls this after every ingestion to:
    1. Classify the document into a domain
    2. Move/copy it to the correct domain folder
    3. Update the domain manifest
    4. Track coverage per domain
    """

    def __init__(self, kb_path: str = None):
        self.kb_path = Path(kb_path) if kb_path else Path(__file__).parent.parent.parent / "knowledge_base"
        self.domains = dict(DOMAIN_TAXONOMY)

    def classify_document(self, filename: str, content_preview: str = "") -> str:
        """Classify a document into a domain based on filename and content."""
        search_text = (filename + " " + content_preview).lower()

        scores = {}
        for domain, info in self.domains.items():
            score = 0
            for kw in info["keywords"]:
                if len(kw) <= 3:
                    # Short keywords need word boundary match
                    if f" {kw} " in f" {search_text} ":
                        score += 1
                else:
                    if kw in search_text:
                        score += 1
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def organize_file(self, file_path: str, genesis_key: str = None, trust_score: float = 0.5) -> Dict[str, Any]:
        """Organize a single file into the correct domain folder."""
        src = Path(file_path)
        if not src.exists():
            return {"error": f"File not found: {file_path}"}

        # Read preview for classification
        preview = ""
        try:
            if src.suffix == ".txt" or src.suffix == ".md":
                preview = src.read_text(errors="ignore")[:2000]
            elif src.suffix == ".pdf":
                preview = src.stem.replace("_", " ").replace("-", " ")
        except Exception:
            preview = src.stem.replace("_", " ")

        domain = self.classify_document(src.name, preview)

        # Create domain folder
        domain_dir = self.kb_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        # Copy file to domain folder (keep original in books/ too)
        dest = domain_dir / src.name
        if not dest.exists():
            shutil.copy2(str(src), str(dest))

        # Update manifest
        self._update_manifest(domain, src.name, genesis_key, trust_score)

        return {
            "file": src.name,
            "domain": domain,
            "path": str(dest),
            "genesis_key": genesis_key,
            "trust_score": trust_score,
        }

    def organize_all(self) -> Dict[str, Any]:
        """Organize all files in the knowledge base."""
        books_dir = self.kb_path / "books"
        if not books_dir.is_dir():
            return {"error": "No books directory found"}

        results = []
        for f in books_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                result = self.organize_file(str(f))
                results.append(result)

        # Count per domain
        domain_counts = {}
        for r in results:
            d = r.get("domain", "unknown")
            domain_counts[d] = domain_counts.get(d, 0) + 1

        return {
            "total_organized": len(results),
            "domain_counts": domain_counts,
            "files": results,
        }

    def get_domain_structure(self) -> Dict[str, Any]:
        """Get the full domain folder structure for the frontend."""
        structure = {}

        for domain, info in self.domains.items():
            domain_dir = self.kb_path / domain
            files = []
            if domain_dir.is_dir():
                for f in sorted(domain_dir.iterdir()):
                    if f.is_file() and not f.name.startswith((".", "_")):
                        files.append({
                            "name": f.name,
                            "size": f.stat().st_size,
                            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        })

            # Load manifest
            manifest = self._load_manifest(domain)

            structure[domain] = {
                "description": info["description"],
                "files": files,
                "file_count": len(files),
                "manifest": manifest,
            }

        # Also include general/uncategorized
        for d in self.kb_path.iterdir():
            if d.is_dir() and d.name not in self.domains and d.name not in ("books", "ai_research", "cicd_pipelines", "__pycache__"):
                files = [{"name": f.name, "size": f.stat().st_size} for f in d.iterdir() if f.is_file()]
                structure[d.name] = {
                    "description": "Uncategorized",
                    "files": files,
                    "file_count": len(files),
                }

        return structure

    def get_coverage_report(self) -> Dict[str, Any]:
        """Get coverage report — which domains are strong vs weak."""
        report = {}
        for domain, info in self.domains.items():
            domain_dir = self.kb_path / domain
            count = len(list(domain_dir.glob("*"))) if domain_dir.is_dir() else 0
            report[domain] = {
                "description": info["description"],
                "document_count": count,
                "coverage": "strong" if count >= 3 else ("moderate" if count >= 1 else "empty"),
            }
        return report

    def _update_manifest(self, domain: str, filename: str, genesis_key: str = None, trust_score: float = 0.5):
        """Update the domain manifest."""
        manifest_path = self.kb_path / domain / "_manifest.json"
        manifest = self._load_manifest(domain)

        # Add or update entry
        manifest["documents"][filename] = {
            "genesis_key": genesis_key,
            "trust_score": trust_score,
            "added_at": datetime.now().isoformat(),
        }
        manifest["last_updated"] = datetime.now().isoformat()
        manifest["document_count"] = len(manifest["documents"])

        try:
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

    def _load_manifest(self, domain: str) -> Dict[str, Any]:
        """Load a domain manifest."""
        manifest_path = self.kb_path / domain / "_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"documents": {}, "last_updated": None, "document_count": 0}


_organizer: Optional[KnowledgeOrganizer] = None

def get_knowledge_organizer() -> KnowledgeOrganizer:
    global _organizer
    if _organizer is None:
        _organizer = KnowledgeOrganizer()
    return _organizer
