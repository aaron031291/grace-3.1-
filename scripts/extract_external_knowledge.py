#!/usr/bin/env python3
"""
Extract External Knowledge - GitHub, AI Research, LLMs

Runs knowledge extraction from external sources and integrates with Grace.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
from backend.database.session import get_session
from cognitive.external_knowledge_extractor import get_external_knowledge_extractor
from cognitive.memory_mesh_integration import get_memory_mesh_integration
from llm_orchestrator.llm_orchestrator import get_llm_orchestrator


def main():
    """Extract knowledge from external sources."""
    print("=" * 80)
    print("EXTERNAL KNOWLEDGE EXTRACTION")
    print("=" * 80)
    print()
    print("Extracting knowledge from:")
    print("  - GitHub (repos, issues, code)")
    print("  - AI Research (arXiv, HuggingFace)")
    print("  - SWE Platforms (Stack Overflow)")
    print()
    
    # Initialize database
    print("Initializing database...")
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database="grace",
            database_path=str(project_root / "data" / "grace.db"),
            echo=False,
        )
        DatabaseConnection.initialize(db_config)
        
        from backend.database.session import initialize_session_factory
        initialize_session_factory()
        
        print("[OK] Database initialized")
    except Exception as e:
        print(f"ERROR: Database initialization: {e}")
        return
    
    # Get session
    session = next(get_session())
    
    # Initialize Grace systems
    print("Initializing Grace systems...")
    try:
        memory_mesh = get_memory_mesh_integration(session=session)
        llm_orchestrator = get_llm_orchestrator(session=session)
        
        print("[OK] Grace systems initialized")
    except Exception as e:
        print(f"WARNING: Some Grace systems not available: {e}")
        memory_mesh = None
        llm_orchestrator = None
    
    # Initialize extractor
    print("Initializing knowledge extractor...")
    github_token = None  # Set your GitHub token here if you have one
    
    extractor = get_external_knowledge_extractor(
        session=session,
        memory_mesh=memory_mesh,
        llm_orchestrator=llm_orchestrator,
        github_token=github_token
    )
    
    print("[OK] Knowledge extractor initialized")
    print()
    
    # Extract from GitHub
    print("=" * 80)
    print("EXTRACTING FROM GITHUB")
    print("=" * 80)
    print()
    
    # Popular Python repos
    github_repos = [
        ("python", "cpython"),
        ("pytorch", "pytorch"),
        ("tensorflow", "tensorflow"),
        ("huggingface", "transformers"),
        ("sqlalchemy", "sqlalchemy"),
        ("fastapi", "fastapi"),
        ("pydantic", "pydantic"),
    ]
    
    all_sources = []
    
    for owner, repo in github_repos[:3]:  # Limit to 3 for now
        print(f"Extracting from {owner}/{repo}...")
        sources = extractor.extract_from_github_repo(
            owner=owner,
            repo=repo,
            topics=["python", "api", "framework"],
            max_files=10
        )
        all_sources.extend(sources)
        print(f"  Extracted {len(sources)} files")
    
    # Extract from GitHub issues
    print()
    print("Extracting from GitHub issues...")
    error_patterns = [
        "ImportError",
        "ModuleNotFoundError",
        "TypeError",
        "AttributeError"
    ]
    
    for owner, repo in github_repos[:2]:  # Limit to 2 for now
        print(f"  Extracting issues from {owner}/{repo}...")
        issue_sources = extractor.extract_from_github_issues(
            owner=owner,
            repo=repo,
            error_patterns=error_patterns,
            max_issues=20
        )
        all_sources.extend(issue_sources)
        print(f"    Extracted {len(issue_sources)} solutions")
    
    # Extract from GitHub code search
    print()
    print("Searching GitHub code...")
    code_queries = [
        "async def",
        "class BaseModel",
        "def create_engine",
        "logging.getLogger"
    ]
    
    for query in code_queries[:2]:  # Limit to 2 for now
        print(f"  Searching for: {query}")
        code_sources = extractor.extract_from_github_code_search(
            query=query,
            language="python",
            max_results=10
        )
        all_sources.extend(code_sources)
        print(f"    Found {len(code_sources)} code results")
    
    # Extract from arXiv
    print()
    print("=" * 80)
    print("EXTRACTING FROM AI RESEARCH")
    print("=" * 80)
    print()
    
    arxiv_queries = [
        "large language models",
        "code generation",
        "neural code synthesis",
        "programming language models"
    ]
    
    for query in arxiv_queries[:2]:  # Limit to 2 for now
        print(f"Searching arXiv for: {query}")
        arxiv_sources = extractor.extract_from_arxiv(
            query=query,
            max_results=10,
            categories=["cs.AI", "cs.LG", "cs.SE"]
        )
        all_sources.extend(arxiv_sources)
        print(f"  Extracted {len(arxiv_sources)} papers")
    
    # Extract from HuggingFace
    print()
    print("Extracting from HuggingFace...")
    hf_sources = extractor.extract_from_huggingface(
        task="text-generation",
        max_results=10
    )
    all_sources.extend(hf_sources)
    print(f"  Extracted {len(hf_sources)} models")
    
    # Extract from Stack Overflow
    print()
    print("=" * 80)
    print("EXTRACTING FROM STACK OVERFLOW")
    print("=" * 80)
    print()
    
    so_queries = [
        "Python async await",
        "SQLAlchemy session",
        "FastAPI dependency injection",
        "Pydantic validation"
    ]
    
    for query in so_queries[:2]:  # Limit to 2 for now
        print(f"Searching Stack Overflow for: {query}")
        so_sources = extractor.extract_from_stackoverflow(
            query=query,
            tags=["python"],
            max_results=10
        )
        all_sources.extend(so_sources)
        print(f"  Extracted {len(so_sources)} solutions")
    
    # Extract patterns
    print()
    print("=" * 80)
    print("EXTRACTING PATTERNS")
    print("=" * 80)
    print()
    
    print(f"Extracting patterns from {len(all_sources)} sources...")
    patterns = extractor.extract_patterns(all_sources)
    print(f"  Extracted {len(patterns)} patterns")
    
    # Store in Memory Mesh
    print()
    print("=" * 80)
    print("STORING IN MEMORY MESH")
    print("=" * 80)
    print()
    
    print(f"Storing {len(patterns)} patterns in Memory Mesh...")
    stored = extractor.store_in_memory_mesh(patterns)
    print(f"  Stored {stored} patterns")
    
    # Display statistics
    print()
    print("=" * 80)
    print("EXTRACTION STATISTICS")
    print("=" * 80)
    print()
    
    stats = extractor.get_stats()
    print(f"GitHub extracted: {stats['github_extracted']}")
    print(f"arXiv extracted: {stats['arxiv_extracted']}")
    print(f"HuggingFace extracted: {stats['huggingface_extracted']}")
    print(f"Stack Overflow extracted: {stats['stackoverflow_extracted']}")
    print(f"Patterns created: {stats['patterns_created']}")
    print(f"Memory Mesh stored: {stats['memory_mesh_stored']}")
    print()
    
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print()
    print("Knowledge has been extracted and integrated into Grace's Memory Mesh.")
    print("This knowledge is now available to:")
    print("  - Coding Agent")
    print("  - Self-Healing System")
    print("  - LLM Orchestrator")
    print("  - All Grace learning systems")
    print()


if __name__ == "__main__":
    main()
