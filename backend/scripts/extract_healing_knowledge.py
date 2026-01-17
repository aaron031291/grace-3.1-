#!/usr/bin/env python3
"""
Extract healing knowledge and add to knowledge base.

Run this script to:
1. Extract errors from healing_results.json
2. Search Stack Overflow and GitHub for solutions
3. Generate new fix patterns
4. Add to healing knowledge base
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
from cognitive.knowledge_extractor import extract_and_add_knowledge

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 80)
    print("GRACE HEALING KNOWLEDGE EXTRACTION")
    print("=" * 80)
    print()
    
    result = extract_and_add_knowledge()
    
    print()
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Patterns found: {result['patterns_found']}")
    print(f"Fix patterns generated: {result['fix_patterns_generated']}")
    print(f"New patterns: {len(result['new_patterns'])}")
    print()
    
    if result['new_patterns']:
        print("New patterns to add:")
        for pattern in result['new_patterns']:
            print(f"  - {pattern['issue_type']} (confidence: {pattern['confidence']})")
    
    print()
    print("Next steps:")
    print("1. Review new patterns in knowledge base")
    print("2. Test patterns with real errors")
    print("3. Update confidence scores based on results")
