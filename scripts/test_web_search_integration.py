#!/usr/bin/env python3
"""
Test Web Search Integration

Demonstrates how to use web_search tool to create templates.
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def test_web_search_integration():
    """Test web search → template creation."""
    print("="*80)
    print("TESTING WEB SEARCH INTEGRATION")
    print("="*80)
    
    # Example problem
    problem_text = "Write a function to find the maximum element in a list"
    test_cases = ["assert find_max([1, 2, 3]) == 3"]
    
    print(f"\nProblem: {problem_text}")
    print(f"Test cases: {test_cases}")
    
    # Import integration
    from backend.benchmarking.web_search_integration import WebSearchTemplateIntegration
    
    integration = WebSearchTemplateIntegration()
    
    # Build query
    query = integration._build_query(problem_text, test_cases)
    print(f"\nSearch query: {query}")
    
    print("\n[INFO] To use web_search tool:")
    print("1. Uncomment web search code in mbpp_integration.py")
    print("2. Pass web_search function to search_and_create_template()")
    print("3. Templates will be created automatically from web results")
    
    print("\n[EXAMPLE CODE]:")
    print("""
    # In mbpp_integration.py, replace web search block with:
    
    from backend.benchmarking.web_search_integration import WebSearchTemplateIntegration
    
    web_integration = WebSearchTemplateIntegration()
    web_template = web_integration.search_and_create_template(
        problem_text=problem["text"],
        test_cases=problem.get("test_list", []),
        web_search_func=web_search  # web_search tool from context
    )
    
    if web_template:
        from backend.benchmarking.mbpp_templates import MBPPTemplate
        template = MBPPTemplate(**web_template)
        code = template.generate_code(function_name, problem["text"], test_cases)
        if code:
            generation_method = "web_knowledge"
    """)

if __name__ == "__main__":
    test_web_search_integration()
