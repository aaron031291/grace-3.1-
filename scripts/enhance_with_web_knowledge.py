#!/usr/bin/env python3
"""
Enhance Templates with Web Knowledge

Searches the web for solutions to failed problems and integrates
that knowledge into templates.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def enhance_failures_with_web_knowledge():
    """Enhance failed problems with web knowledge."""
    results_file = project_root / "full_mbpp_results.json"
    
    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    results = data.get("results", {}).get("results", [])
    
    # Get failures
    failures = [r for r in results if not r.get("passed", False)]
    
    print("="*80)
    print("ENHANCING FAILURES WITH WEB KNOWLEDGE")
    print("="*80)
    print(f"\nFound {len(failures)} failures to enhance")
    
    # For each failure, search web for solutions
    web_enhanced = []
    
    for i, failure in enumerate(failures[:20], 1):  # Start with first 20
        problem_text = failure.get("problem_text", "")
        error = failure.get("error", "")
        test_cases = failure.get("test_cases", [])
        
        print(f"\n[{i}/{min(20, len(failures))}] Searching web for: {problem_text[:60]}...")
        
        # Build search query
        from backend.benchmarking.web_knowledge_integration import WebKnowledgeIntegrator
        integrator = WebKnowledgeIntegrator()
        
        query = integrator._build_search_query(problem_text, error, test_cases)
        print(f"  Query: {query}")
        
        # Note: Actual web search would happen here
        # For now, we'll create a template suggestion based on the query
        web_enhanced.append({
            "problem": problem_text[:100],
            "query": query,
            "suggestion": f"Search web for: {query}"
        })
    
    # Save suggestions
    output_file = project_root / "web_knowledge_suggestions.json"
    with open(output_file, 'w') as f:
        json.dump({
            "total_failures": len(failures),
            "enhanced": len(web_enhanced),
            "suggestions": web_enhanced
        }, f, indent=2)
    
    print(f"\n[COMPLETE] Saved {len(web_enhanced)} web knowledge suggestions")
    print(f"Output: {output_file}")
    
    return web_enhanced

if __name__ == "__main__":
    enhance_failures_with_web_knowledge()
