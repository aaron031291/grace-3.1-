#!/usr/bin/env python3
"""
Ingest Code Knowledge from GitHub and Other Sources

This script helps build Grace's knowledge base by ingesting:
- GitHub repositories
- Code examples
- Algorithm implementations
- Common patterns

This makes Grace LLM-independent for common coding tasks.
"""

import sys
from pathlib import Path
import subprocess
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def ingest_github_repository(repo_url: str, category: str = "python_code") -> bool:
    """
    Ingest a GitHub repository into knowledge base.
    
    Args:
        repo_url: GitHub repository URL
        category: Category for the repository
        
    Returns:
        True if successful
    """
    print(f"\n{'='*80}")
    print(f"Ingesting GitHub Repository")
    print(f"{'='*80}")
    print(f"Repository: {repo_url}")
    print(f"Category: {category}")
    print()
    
    try:
        from database.session import initialize_session_factory
        from layer1.components.knowledge_base_connector import KnowledgeBaseIngestionConnector
        from layer1.message_bus import get_message_bus
        
        # Initialize session
        session_factory = initialize_session_factory()
        session = session_factory()
        
        # Get message bus
        message_bus = get_message_bus()
        
        # Create connector
        connector = KnowledgeBaseIngestionConnector(
            message_bus=message_bus,
            knowledge_base_path=project_root / "backend" / "knowledge_base"
        )
        
        # Clone repository to temp location
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        
        try:
            print(f"Cloning repository to {temp_dir}...")
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, temp_dir],
                check=True,
                capture_output=True
            )
            
            print(f"[OK] Repository cloned")
            
            # Ingest repository
            print(f"Ingesting repository...")
            result = connector.ingest_repository(
                repo_path=Path(temp_dir),
                category=category
            )
            
            if result.get("success"):
                print(f"[OK] Repository ingested successfully")
                stats = result.get("stats", {})
                print(f"  Files ingested: {stats.get('files_ingested', 0)}")
                print(f"  Total size: {stats.get('total_size', 0)} bytes")
                return True
            else:
                print(f"[FAIL] Ingestion failed: {result.get('error', 'Unknown error')}")
                return False
                
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        print(f"[ERROR] Failed to ingest repository: {e}")
        import traceback
        traceback.print_exc()
        return False


def ingest_code_examples(examples: list, category: str = "code_examples") -> bool:
    """
    Ingest code examples into knowledge base.
    
    Args:
        examples: List of code example dictionaries
        category: Category for examples
        
    Returns:
        True if successful
    """
    print(f"\n{'='*80}")
    print(f"Ingesting Code Examples")
    print(f"{'='*80}")
    print(f"Examples: {len(examples)}")
    print(f"Category: {category}")
    print()
    
    try:
        from database.session import initialize_session_factory
        from api.ingestion_integration import get_ingestion_integration
        
        # Initialize session
        session_factory = initialize_session_factory()
        session = session_factory()
        
        # Get ingestion integration
        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=project_root / "backend" / "knowledge_base"
        )
        
        success_count = 0
        for i, example in enumerate(examples, 1):
            print(f"[{i}/{len(examples)}] Ingesting: {example.get('description', 'Unknown')[:50]}...")
            
            # Create temporary file with code
            import tempfile
            import os
            
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            )
            temp_file.write(example.get("code", ""))
            temp_file.close()
            
            try:
                # Ingest file
                result = integration.ingest_file_with_tracking(
                    file_path=Path(temp_file.name),
                    user_id="system",
                    metadata={
                        "description": example.get("description", ""),
                        "tags": example.get("tags", []),
                        "category": category,
                        "source": "code_examples"
                    }
                )
                
                if result.get("status") == "success":
                    success_count += 1
                    print(f"  [OK] Ingested")
                else:
                    print(f"  [FAIL] {result.get('error', 'Unknown error')}")
                    
            finally:
                os.unlink(temp_file.name)
        
        print()
        print(f"Successfully ingested: {success_count}/{len(examples)}")
        return success_count > 0
        
    except Exception as e:
        print(f"[ERROR] Failed to ingest examples: {e}")
        import traceback
        traceback.print_exc()
        return False


def ingest_popular_repositories():
    """Ingest popular Python repositories for code examples."""
    repositories = [
        {
            "url": "https://github.com/python/cpython",
            "category": "python_core",
            "description": "Python core library"
        },
        {
            "url": "https://github.com/numpy/numpy",
            "category": "scientific_computing",
            "description": "NumPy library"
        },
        {
            "url": "https://github.com/pandas-dev/pandas",
            "category": "data_analysis",
            "description": "Pandas library"
        },
        {
            "url": "https://github.com/django/django",
            "category": "web_framework",
            "description": "Django framework"
        },
        {
            "url": "https://github.com/flask/flask",
            "category": "web_framework",
            "description": "Flask framework"
        },
        {
            "url": "https://github.com/psf/requests",
            "category": "http_library",
            "description": "Requests library"
        },
        {
            "url": "https://github.com/python-pillow/Pillow",
            "category": "image_processing",
            "description": "Pillow image library"
        },
    ]
    
    print("="*80)
    print("INGESTING POPULAR PYTHON REPOSITORIES")
    print("="*80)
    print()
    print("This will clone and ingest popular Python repositories")
    print("to build Grace's knowledge base.")
    print()
    print("Repositories to ingest:")
    for repo in repositories:
        print(f"  - {repo['url']} ({repo['category']})")
    print()
    
    success_count = 0
    for repo in repositories:
        if ingest_github_repository(repo["url"], repo["category"]):
            success_count += 1
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Successfully ingested: {success_count}/{len(repositories)} repositories")
    print()


def ingest_common_patterns():
    """Ingest common Python programming patterns."""
    patterns = [
        {
            "code": """def sum_list(lst):
    \"\"\"Sum all elements in a list.\"\"\"
    return sum(lst)
""",
            "description": "Sum elements in a list",
            "tags": ["list", "sum", "python", "basic"]
        },
        {
            "code": """def find_max(numbers):
    \"\"\"Find maximum value in a list.\"\"\"
    if not numbers:
        return None
    return max(numbers)
""",
            "description": "Find maximum in a list",
            "tags": ["list", "max", "python", "basic"]
        },
        {
            "code": """def reverse_string(s):
    \"\"\"Reverse a string.\"\"\"
    return s[::-1]
""",
            "description": "Reverse a string",
            "tags": ["string", "reverse", "python", "basic"]
        },
        {
            "code": """def is_prime(n):
    \"\"\"Check if number is prime.\"\"\"
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
""",
            "description": "Check if number is prime",
            "tags": ["number", "prime", "python", "algorithm"]
        },
        {
            "code": """def factorial(n):
    \"\"\"Calculate factorial.\"\"\"
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
""",
            "description": "Calculate factorial",
            "tags": ["number", "factorial", "python", "algorithm"]
        },
        {
            "code": """def fibonacci(n):
    \"\"\"Calculate Fibonacci number.\"\"\"
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
""",
            "description": "Calculate Fibonacci number",
            "tags": ["number", "fibonacci", "python", "algorithm"]
        },
        {
            "code": """def unique_elements(lst):
    \"\"\"Get unique elements from list.\"\"\"
    return list(set(lst))
""",
            "description": "Get unique elements from list",
            "tags": ["list", "unique", "python", "basic"]
        },
        {
            "code": """def sort_list(lst):
    \"\"\"Sort a list.\"\"\"
    return sorted(lst)
""",
            "description": "Sort a list",
            "tags": ["list", "sort", "python", "basic"]
        },
    ]
    
    print("="*80)
    print("INGESTING COMMON PATTERNS")
    print("="*80)
    print()
    
    return ingest_code_examples(patterns, category="common_patterns")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest code knowledge from various sources")
    parser.add_argument(
        "--source",
        choices=["github", "patterns", "both"],
        default="patterns",
        help="Source to ingest from"
    )
    parser.add_argument(
        "--repo-url",
        type=str,
        help="Specific GitHub repository URL to ingest"
    )
    parser.add_argument(
        "--category",
        type=str,
        default="python_code",
        help="Category for ingested content"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("CODE KNOWLEDGE INGESTION")
    print("="*80)
    print()
    print("This script builds Grace's knowledge base by ingesting:")
    print("  - GitHub repositories")
    print("  - Code examples")
    print("  - Common patterns")
    print()
    print("This makes Grace LLM-independent for common coding tasks.")
    print()
    
    if args.repo_url:
        # Ingest specific repository
        ingest_github_repository(args.repo_url, args.category)
    elif args.source == "github":
        # Ingest popular repositories
        ingest_popular_repositories()
    elif args.source == "patterns":
        # Ingest common patterns
        ingest_common_patterns()
    elif args.source == "both":
        # Ingest both
        ingest_common_patterns()
        print()
        print()
        ingest_popular_repositories()
    
    print()
    print("="*80)
    print("INGESTION COMPLETE")
    print("="*80)
    print()
    print("Grace's knowledge base has been updated.")
    print("The coding agent can now use this knowledge to generate code")
    print("without requiring LLMs for common patterns.")
    print()


if __name__ == "__main__":
    main()
