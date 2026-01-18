#!/usr/bin/env python3
"""
Integrate Web Knowledge into Templates

Searches the web for solutions to failed problems and automatically
adds them to the template library.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def integrate_web_knowledge():
    """Main integration function."""
    print("="*80)
    print("WEB KNOWLEDGE INTEGRATION")
    print("="*80)
    
    # Load failures
    results_file = project_root / "full_mbpp_results.json"
    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    results = data.get("results", {}).get("results", [])
    failures = [r for r in results if not r.get("passed", False)]
    
    print(f"\nFound {len(failures)} failures")
    print(f"Will search web for solutions to top 10 failures")
    
    # For each failure, create web search query
    web_queries = []
    
    for i, failure in enumerate(failures[:10], 1):
        problem_text = failure.get("problem_text", "")
        error = failure.get("error", "")
        test_cases = failure.get("test_cases", [])
        
        # Build query
        from backend.benchmarking.web_enhanced_template_generator import WebEnhancedTemplateGenerator
        generator = WebEnhancedTemplateGenerator()
        
        query = generator._build_web_query(problem_text, test_cases, error)
        
        web_queries.append({
            "index": i,
            "problem": problem_text[:100],
            "query": query,
            "error": error[:100] if error else None
        })
        
        print(f"\n{i}. Problem: {problem_text[:60]}...")
        print(f"   Query: {query}")
    
    # Save queries for web search
    output_file = project_root / "web_search_queries.json"
    with open(output_file, 'w') as f:
        json.dump({
            "total_failures": len(failures),
            "queries": web_queries,
            "instructions": "Use these queries to search web, then extract code examples and create templates"
        }, f, indent=2)
    
    print(f"\n[COMPLETE] Generated {len(web_queries)} web search queries")
    print(f"Saved to: {output_file}")
    print(f"\nNext: Search web with these queries and extract code examples")

if __name__ == "__main__":
    integrate_web_knowledge()
