#!/usr/bin/env python3
"""
Show Learned Topics (Simple Version)

Displays what Grace has learned from self-healing training practice.
Simple version that doesn't require database initialization.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

print("=" * 70)
print("GRACE'S LEARNED TOPICS FROM SELF-HEALING TRAINING")
print("=" * 70)
print()

# Try to read training cycles from file if they exist
training_data_path = Path("knowledge_base/training_cycles.json")
sandbox_practice_path = Path("knowledge_base/sandbox_practice")
sandbox_logs_path = Path("knowledge_base/sandbox_lab/logs")

# Collect topics from various sources
topics = []
topics_by_category = defaultdict(list)
patterns = Counter()

print("[INFO] Searching for training data...")
print()

# 1. Check sandbox practice logs
if sandbox_logs_path.exists():
    print(f"[INFO] Found sandbox logs: {sandbox_logs_path}")
    for log_file in sandbox_logs_path.glob("*.log"):
        try:
            content = log_file.read_text(encoding='utf-8', errors='ignore')
            # Extract topics from log content
            if "syntax" in content.lower():
                topics.append("Syntax error fixes")
                topics_by_category["syntax"].append("Syntax error patterns")
            if "logic" in content.lower():
                topics.append("Logic error fixes")
                topics_by_category["logic"].append("Logic error patterns")
            if "performance" in content.lower():
                topics.append("Performance optimization")
                topics_by_category["performance"].append("Performance patterns")
            if "security" in content.lower():
                topics.append("Security fixes")
                topics_by_category["security"].append("Security patterns")
        except:
            pass

# 2. Check sandbox practice directory
if sandbox_practice_path.exists():
    print(f"[INFO] Found sandbox practice: {sandbox_practice_path}")
    # Look for fixed files
    fixed_files = list(sandbox_practice_path.rglob("*.py"))
    if fixed_files:
        print(f"[INFO] Found {len(fixed_files)} practice files")
        # Categorize by filename/path
        for file_path in fixed_files[:50]:  # Sample first 50
            file_str = str(file_path).lower()
            if "syntax" in file_str or "error" in file_str:
                patterns["syntax_errors"] += 1
            elif "logic" in file_str or "bug" in file_str:
                patterns["logic_errors"] += 1
            elif "performance" in file_str or "optimization" in file_str:
                patterns["performance_issues"] += 1
            elif "security" in file_str or "vulnerability" in file_str:
                patterns["security_issues"] += 1

# 3. Check for learning memory
learning_memory_path = Path("knowledge_base/learning_memory")
if learning_memory_path.exists():
    print(f"[INFO] Found learning memory: {learning_memory_path}")

print()
print("-" * 70)
print("LEARNED TOPICS SUMMARY")
print("-" * 70)
print()

if not topics and not patterns:
    print("[INFO] No training cycles found yet.")
    print()
    print("Grace learns topics from self-healing training practice cycles.")
    print("Topics are extracted from:")
    print("  - Practice cycles (100 files per cycle)")
    print("  - Knowledge gained from fixes")
    print("  - Fix patterns identified")
    print("  - Problem perspectives practiced")
    print()
    print("To see learned topics, Grace needs to run training cycles first.")
    print()
    print("Expected Topics Grace Will Learn:")
    print()
    print("  [SYNTAX] - Syntax error fixes")
    print("    - Missing colon fixes")
    print("    - Indentation error corrections")
    print("    - Syntax error patterns")
    print()
    print("  [LOGIC] - Logic error fixes")
    print("    - Off-by-one error fixes")
    print("    - Condition logic corrections")
    print("    - Loop logic improvements")
    print()
    print("  [PERFORMANCE] - Performance optimization")
    print("    - Algorithm optimization")
    print("    - Complexity reduction")
    print("    - Data structure improvements")
    print()
    print("  [SECURITY] - Security fixes")
    print("    - Input validation fixes")
    print("    - Access control improvements")
    print("    - Security vulnerability patterns")
    print()
    print("=" * 70)
    print("API Endpoint: GET /training-knowledge/topics")
    print("Documentation: WHAT_GRACE_LEARNS.md")
    print("=" * 70)
else:
    # Display found topics
    print(f"Total Topics Found: {len(set(topics))}")
    print(f"Patterns Found: {len(patterns)}")
    print()
    
    if patterns:
        print("Fix Patterns Identified:")
        print("-" * 70)
        for pattern, count in patterns.most_common():
            print(f"  - {pattern.replace('_', ' ').title()}: {count} occurrences")
        print()
    
    if topics_by_category:
        print("Topics by Category:")
        print("-" * 70)
        for category, cat_topics in topics_by_category.items():
            print(f"\n[{category.upper()}] - {len(set(cat_topics))} topics")
            for topic in list(set(cat_topics))[:5]:
                print(f"  - {topic}")
        print()
    
    print("=" * 70)
    print("For complete learning data, use API: GET /training-knowledge/topics")
    print("=" * 70)
