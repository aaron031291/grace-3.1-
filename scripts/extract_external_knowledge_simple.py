#!/usr/bin/env python3
"""
Simple External Knowledge Extraction - Without Full LLM Orchestrator

Extracts knowledge from external sources and stores basic patterns.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any


def extract_github_code_search(query: str, max_results: int = 10) -> List[Dict]:
    """Extract code patterns from GitHub."""
    sources = []
    
    try:
        search_url = "https://api.github.com/search/code"
        params = {
            "q": f"{query} language:python",
            "sort": "indexed",
            "order": "desc",
            "per_page": min(max_results, 100)
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            results = response.json().get("items", [])
            
            for result in results[:max_results]:
                sources.append({
                    "source_type": "github_code",
                    "source_id": result.get("sha", ""),
                    "title": f"{result.get('repository', {}).get('full_name', '')}: {result.get('path', '')}",
                    "url": result.get("html_url", ""),
                    "query": query
                })
                time.sleep(0.1)  # Rate limiting
        
        print(f"  Extracted {len(sources)} code results from GitHub")
        
    except Exception as e:
        print(f"  ERROR: GitHub extraction failed: {e}")
    
    return sources


def extract_stackoverflow(query: str, max_results: int = 10) -> List[Dict]:
    """Extract solutions from Stack Overflow."""
    sources = []
    
    try:
        search_url = "https://api.stackexchange.com/2.3/search"
        params = {
            "order": "desc",
            "sort": "votes",
            "intitle": query,
            "tagged": "python",
            "site": "stackoverflow",
            "filter": "withbody",
            "pagesize": min(max_results, 100)
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            questions = response.json().get("items", [])
            
            for question in questions[:max_results]:
                if question.get("accepted_answer_id"):
                    sources.append({
                        "source_type": "stackoverflow",
                        "source_id": str(question.get("question_id", "")),
                        "title": question.get("title", ""),
                        "url": question.get("link", ""),
                        "score": question.get("score", 0),
                        "is_accepted": True,
                        "query": query
                    })
        
        print(f"  Extracted {len(sources)} solutions from Stack Overflow")
        
    except Exception as e:
        print(f"  ERROR: Stack Overflow extraction failed: {e}")
    
    return sources


def extract_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Extract papers from arXiv."""
    sources = []
    
    try:
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        response = requests.get(arxiv_url, params=params, timeout=10)
        
        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", namespace)
            
            for entry in entries:
                try:
                    title = entry.find("atom:title", namespace)
                    title_text = title.text if title is not None else ""
                    arxiv_id = entry.find("atom:id", namespace)
                    arxiv_id_text = arxiv_id.text.split("/")[-1] if arxiv_id is not None else ""
                    
                    sources.append({
                        "source_type": "arxiv",
                        "source_id": arxiv_id_text,
                        "title": title_text,
                        "url": f"https://arxiv.org/abs/{arxiv_id_text}",
                        "query": query
                    })
                except Exception as e:
                    pass
        
        print(f"  Extracted {len(sources)} papers from arXiv")
        
    except Exception as e:
        print(f"  ERROR: arXiv extraction failed: {e}")
    
    return sources


def main():
    """Extract knowledge from external sources."""
    print("=" * 80)
    print("EXTERNAL KNOWLEDGE EXTRACTION (SIMPLE)")
    print("=" * 80)
    print()
    print("Extracting knowledge from:")
    print("  - GitHub (code search)")
    print("  - Stack Overflow (solutions)")
    print("  - arXiv (AI research)")
    print()
    
    all_sources = []
    
    # GitHub code search
    print("=" * 80)
    print("EXTRACTING FROM GITHUB")
    print("=" * 80)
    print()
    
    github_queries = [
        "async def",
        "class BaseModel",
        "def create_engine",
        "logging.getLogger"
    ]
    
    for query in github_queries:
        print(f"Searching GitHub for: {query}")
        sources = extract_github_code_search(query, max_results=5)
        all_sources.extend(sources)
        time.sleep(1)  # Rate limiting
    
    # Stack Overflow
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
    
    for query in so_queries:
        print(f"Searching Stack Overflow for: {query}")
        sources = extract_stackoverflow(query, max_results=5)
        all_sources.extend(sources)
        time.sleep(1)  # Rate limiting
    
    # arXiv
    print()
    print("=" * 80)
    print("EXTRACTING FROM ARXIV")
    print("=" * 80)
    print()
    
    arxiv_queries = [
        "large language models",
        "code generation"
    ]
    
    for query in arxiv_queries:
        print(f"Searching arXiv for: {query}")
        sources = extract_arxiv(query, max_results=5)
        all_sources.extend(sources)
        time.sleep(1)  # Rate limiting
    
    # Save results
    print()
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()
    
    output_file = project_root / "data" / "external_knowledge.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "extracted_at": datetime.utcnow().isoformat(),
            "total_sources": len(all_sources),
            "sources": all_sources
        }, f, indent=2)
    
    print(f"Saved {len(all_sources)} knowledge sources to: {output_file}")
    print()
    
    # Display summary
    print("=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)
    print()
    
    by_type = {}
    for source in all_sources:
        source_type = source.get("source_type", "unknown")
        by_type[source_type] = by_type.get(source_type, 0) + 1
    
    for source_type, count in by_type.items():
        print(f"  {source_type}: {count}")
    
    print()
    print(f"Total sources extracted: {len(all_sources)}")
    print()
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print()
    print("Knowledge has been extracted and saved.")
    print("This knowledge can now be integrated into Grace's Memory Mesh.")
    print()


if __name__ == "__main__":
    main()
