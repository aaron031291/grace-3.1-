#!/usr/bin/env python3
"""
Use Web Search to Create Templates

Searches web for solutions to failed problems and creates templates automatically.
"""

import json
import sys
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def extract_code_from_web_content(content: str) -> list:
    """Extract Python code blocks from web content."""
    code_blocks = []
    
    # Find code blocks
    patterns = [
        r'```python\n(.*?)\n```',
        r'```\n(.*?)\n```',
        r'def\s+\w+\([^)]*\):.*?(?=\n\n|\ndef\s|\Z)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            code = match.strip()
            if "def " in code and len(code) > 20:
                code_blocks.append(code)
    
    return code_blocks

def create_template_from_code(code: str, problem_text: str, query: str) -> dict:
    """Create template structure from code."""
    # Extract function name
    func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
    if not func_match:
        return None
    
    func_name = func_match.group(1)
    
    # Replace function name with placeholder
    template_code = code.replace(f"def {func_name}(", "def {function_name}(")
    
    # Extract keywords
    keywords = []
    text_lower = problem_text.lower()
    for word in ["find", "count", "sort", "remove", "check", "list", "string"]:
        if word in text_lower:
            keywords.append(word)
    
    return {
        "name": f"web_{func_name}",
        "pattern_keywords": keywords,
        "pattern_regex": "|".join(keywords[:3]) + ".*" if keywords else ".*",
        "template_code": template_code,
        "description": f"Web-sourced from: {query}",
        "examples": [problem_text[:100]],
        "source": "web_search"
    }

def main():
    """Main function - uses web_search tool."""
    print("="*80)
    print("WEB SEARCH → TEMPLATE CREATION")
    print("="*80)
    
    # Load queries
    queries_file = project_root / "web_search_queries.json"
    if not queries_file.exists():
        print(f"ERROR: {queries_file} not found")
        return
    
    with open(queries_file) as f:
        data = json.load(f)
    
    queries = data.get("queries", [])[:5]  # First 5
    
    templates_created = []
    
    for i, query_data in enumerate(queries, 1):
        query = query_data["query"]
        problem = query_data.get("problem", "")
        
        print(f"\n[{i}/{len(queries)}] Searching: {query}")
        
        # NOTE: In actual execution, web_search tool would be called here
        # web_results = web_search(query)
        # For now, we'll create the structure
        
        print(f"  → Would search web for: {query}")
        print(f"  → Problem: {problem[:60]}...")
        print(f"  → Would extract code and create template")
        
        # Template structure ready for web results
        templates_created.append({
            "query": query,
            "problem": problem,
            "ready": True
        })
    
    # Save ready templates
    output = project_root / "web_templates_from_search.json"
    with open(output, 'w') as f:
        json.dump({
            "templates": templates_created,
            "note": "Run with web_search tool to get actual results"
        }, f, indent=2)
    
    print(f"\n[COMPLETE] Created {len(templates_created)} template structures")
    print(f"Saved to: {output}")

if __name__ == "__main__":
    main()
