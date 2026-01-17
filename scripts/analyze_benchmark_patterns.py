#!/usr/bin/env python3
"""
Analyze MBPP and HumanEval Problems to Extract Patterns

This script analyzes all problems from MBPP and HumanEval to:
1. Identify common patterns
2. Extract problem categories
3. Generate template suggestions
4. Create comprehensive pattern library
"""

import sys
from pathlib import Path
import json
import re
from collections import Counter, defaultdict
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def analyze_mbpp_problems() -> Dict[str, Any]:
    """Analyze MBPP problems to extract patterns."""
    print("="*80)
    print("ANALYZING MBPP PROBLEMS")
    print("="*80)
    print()
    
    try:
        from datasets import load_dataset
        
        print("Loading MBPP dataset...")
        dataset = load_dataset("mbpp", split="test")
        problems = [item for item in dataset]
        print(f"Loaded {len(problems)} problems")
        print()
        
        # Analyze patterns
        patterns = {
            "keywords": Counter(),
            "operations": Counter(),
            "data_types": Counter(),
            "algorithms": Counter(),
            "problem_types": defaultdict(list)
        }
        
        print("Analyzing problems...")
        for i, problem in enumerate(problems, 1):
            text = problem.get("text", "").lower()
            code = problem.get("code", "").lower()
            test_list = problem.get("test_list", [])
            
            # Extract keywords
            keywords = re.findall(r'\b\w+\b', text)
            patterns["keywords"].update(keywords)
            
            # Identify operations
            operations = [
                "sum", "max", "min", "average", "count",
                "filter", "map", "reduce", "sort", "reverse",
                "find", "search", "replace", "split", "join",
                "add", "remove", "insert", "delete", "update"
            ]
            for op in operations:
                if op in text or op in code:
                    patterns["operations"][op] += 1
            
            # Identify data types
            data_types = ["list", "dict", "string", "int", "float", "tuple", "set"]
            for dt in data_types:
                if dt in text or dt in code:
                    patterns["data_types"][dt] += 1
            
            # Identify algorithms
            algorithms = [
                "sort", "search", "binary", "linear", "recursive",
                "dynamic", "greedy", "backtrack", "graph", "tree",
                "fibonacci", "prime", "factorial", "gcd", "lcm"
            ]
            for alg in algorithms:
                if alg in text or alg in code:
                    patterns["algorithms"][alg] += 1
            
            # Categorize problem type
            problem_type = categorize_problem(text, code, test_list)
            patterns["problem_types"][problem_type].append(i)
            
            if i % 50 == 0:
                print(f"  Analyzed {i}/{len(problems)} problems...")
        
        print()
        print("="*80)
        print("MBPP PATTERN ANALYSIS RESULTS")
        print("="*80)
        print()
        
        print("Top Keywords:")
        for keyword, count in patterns["keywords"].most_common(20):
            print(f"  {keyword}: {count}")
        print()
        
        print("Top Operations:")
        for op, count in patterns["operations"].most_common(15):
            print(f"  {op}: {count}")
        print()
        
        print("Data Types:")
        for dt, count in patterns["data_types"].most_common(10):
            print(f"  {dt}: {count}")
        print()
        
        print("Algorithms:")
        for alg, count in patterns["algorithms"].most_common(15):
            print(f"  {alg}: {count}")
        print()
        
        print("Problem Categories:")
        for category, problem_ids in sorted(patterns["problem_types"].items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {category}: {len(problem_ids)} problems")
        print()
        
        return patterns
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {}


def analyze_humaneval_problems() -> Dict[str, Any]:
    """Analyze HumanEval problems to extract patterns."""
    print("="*80)
    print("ANALYZING HUMANEVAL PROBLEMS")
    print("="*80)
    print()
    
    try:
        from datasets import load_dataset
        
        print("Loading HumanEval dataset...")
        dataset = load_dataset("openai/openai_humaneval", split="test")
        problems = [item for item in dataset]
        print(f"Loaded {len(problems)} problems")
        print()
        
        # Analyze patterns
        patterns = {
            "keywords": Counter(),
            "operations": Counter(),
            "data_types": Counter(),
            "algorithms": Counter(),
            "problem_types": defaultdict(list)
        }
        
        print("Analyzing problems...")
        for i, problem in enumerate(problems, 1):
            prompt = problem.get("prompt", "").lower()
            canonical = problem.get("canonical_solution", "").lower()
            test = problem.get("test", "").lower()
            
            combined = f"{prompt} {canonical} {test}"
            
            # Extract keywords
            keywords = re.findall(r'\b\w+\b', prompt)
            patterns["keywords"].update(keywords)
            
            # Identify operations
            operations = [
                "sum", "max", "min", "average", "count",
                "filter", "map", "reduce", "sort", "reverse",
                "find", "search", "replace", "split", "join",
                "recursive", "iterative", "generator", "iterator"
            ]
            for op in operations:
                if op in combined:
                    patterns["operations"][op] += 1
            
            # Identify data types
            data_types = ["list", "dict", "string", "int", "float", "tuple", "set"]
            for dt in data_types:
                if dt in combined:
                    patterns["data_types"][dt] += 1
            
            # Identify algorithms
            algorithms = [
                "sort", "search", "binary", "linear", "recursive",
                "dynamic", "greedy", "backtrack", "graph", "tree",
                "fibonacci", "prime", "factorial", "gcd", "lcm"
            ]
            for alg in algorithms:
                if alg in combined:
                    patterns["algorithms"][alg] += 1
            
            # Categorize problem type
            problem_type = categorize_problem(prompt, canonical, [test])
            patterns["problem_types"][problem_type].append(i)
            
            if i % 20 == 0:
                print(f"  Analyzed {i}/{len(problems)} problems...")
        
        print()
        print("="*80)
        print("HUMANEVAL PATTERN ANALYSIS RESULTS")
        print("="*80)
        print()
        
        print("Top Keywords:")
        for keyword, count in patterns["keywords"].most_common(20):
            print(f"  {keyword}: {count}")
        print()
        
        print("Top Operations:")
        for op, count in patterns["operations"].most_common(15):
            print(f"  {op}: {count}")
        print()
        
        print("Data Types:")
        for dt, count in patterns["data_types"].most_common(10):
            print(f"  {dt}: {count}")
        print()
        
        print("Algorithms:")
        for alg, count in patterns["algorithms"].most_common(15):
            print(f"  {alg}: {count}")
        print()
        
        print("Problem Categories:")
        for category, problem_ids in sorted(patterns["problem_types"].items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {category}: {len(problem_ids)} problems")
        print()
        
        return patterns
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {}


def categorize_problem(text: str, code: str, tests: List[str]) -> str:
    """Categorize a problem into a type."""
    combined = f"{text} {code} {' '.join(tests)}".lower()
    
    # List operations
    if any(x in combined for x in ["list", "array", "elements", "items"]):
        if "sum" in combined:
            return "list_sum"
        elif "max" in combined or "maximum" in combined:
            return "list_max"
        elif "min" in combined or "minimum" in combined:
            return "list_min"
        elif "sort" in combined:
            return "list_sort"
        elif "reverse" in combined:
            return "list_reverse"
        elif "filter" in combined:
            return "list_filter"
        elif "unique" in combined or "duplicate" in combined:
            return "list_unique"
        else:
            return "list_operation"
    
    # String operations
    if any(x in combined for x in ["string", "str", "text", "char"]):
        if "reverse" in combined:
            return "string_reverse"
        elif "split" in combined:
            return "string_split"
        elif "join" in combined:
            return "string_join"
        elif "replace" in combined:
            return "string_replace"
        elif "find" in combined or "search" in combined:
            return "string_search"
        else:
            return "string_operation"
    
    # Number operations
    if any(x in combined for x in ["number", "num", "int", "integer", "digit"]):
        if "prime" in combined:
            return "number_prime"
        elif "factorial" in combined:
            return "number_factorial"
        elif "fibonacci" in combined:
            return "number_fibonacci"
        elif "even" in combined or "odd" in combined:
            return "number_parity"
        elif "gcd" in combined or "lcm" in combined:
            return "number_gcd_lcm"
        else:
            return "number_operation"
    
    # Dictionary operations
    if any(x in combined for x in ["dict", "dictionary", "map", "key", "value"]):
        return "dictionary_operation"
    
    # Set operations
    if "set" in combined and "{" in combined:
        return "set_operation"
    
    # Algorithm patterns
    if "sort" in combined:
        return "algorithm_sort"
    elif "search" in combined:
        return "algorithm_search"
    elif "recursive" in combined or "recursion" in combined:
        return "algorithm_recursive"
    elif "graph" in combined:
        return "algorithm_graph"
    elif "tree" in combined:
        return "algorithm_tree"
    elif "dynamic" in combined:
        return "algorithm_dp"
    
    # Default
    return "general"


def generate_template_suggestions(mbpp_patterns: Dict, humaneval_patterns: Dict) -> List[Dict]:
    """Generate template suggestions based on analysis."""
    print("="*80)
    print("GENERATING TEMPLATE SUGGESTIONS")
    print("="*80)
    print()
    
    suggestions = []
    
    # Combine patterns
    all_operations = set(mbpp_patterns.get("operations", {}).keys()) | set(humaneval_patterns.get("operations", {}).keys())
    all_categories = set(mbpp_patterns.get("problem_types", {}).keys()) | set(humaneval_patterns.get("problem_types", {}).keys())
    
    print(f"Found {len(all_operations)} unique operations")
    print(f"Found {len(all_categories)} problem categories")
    print()
    
    # Generate suggestions for missing patterns
    existing_templates = [
        "list_sum", "list_max", "list_min", "list_reverse", "list_filter",
        "string_length", "string_reverse", "string_uppercase", "string_lowercase",
        "is_even", "is_odd", "is_prime", "factorial", "fibonacci"
    ]
    
    missing_patterns = []
    for category in all_categories:
        if category not in existing_templates:
            missing_patterns.append(category)
    
    print(f"Missing templates: {len(missing_patterns)}")
    print()
    
    for pattern in sorted(missing_patterns)[:50]:  # Top 50 missing
        suggestions.append({
            "pattern": pattern,
            "priority": "high" if pattern in ["list_operation", "string_operation", "number_operation"] else "medium",
            "estimated_coverage": "high" if pattern in mbpp_patterns.get("problem_types", {}) else "medium"
        })
    
    return suggestions


def main():
    """Main function."""
    print("="*80)
    print("BENCHMARK PATTERN ANALYSIS")
    print("="*80)
    print()
    print("This script analyzes MBPP and HumanEval problems to:")
    print("  1. Identify common patterns")
    print("  2. Extract problem categories")
    print("  3. Generate template suggestions")
    print("  4. Create comprehensive pattern library")
    print()
    
    # Analyze MBPP
    mbpp_patterns = analyze_mbpp_problems()
    
    print()
    print()
    
    # Analyze HumanEval
    humaneval_patterns = analyze_humaneval_problems()
    
    print()
    print()
    
    # Generate suggestions
    suggestions = generate_template_suggestions(mbpp_patterns, humaneval_patterns)
    
    print("="*80)
    print("TEMPLATE SUGGESTIONS")
    print("="*80)
    print()
    print("High Priority Templates Needed:")
    high_priority = [s for s in suggestions if s["priority"] == "high"]
    for i, suggestion in enumerate(high_priority[:20], 1):
        print(f"  {i}. {suggestion['pattern']}")
    print()
    
    print("Medium Priority Templates Needed:")
    medium_priority = [s for s in suggestions if s["priority"] == "medium"]
    for i, suggestion in enumerate(medium_priority[:20], 1):
        print(f"  {i}. {suggestion['pattern']}")
    print()
    
    # Save results
    results = {
        "mbpp_patterns": {
            "keywords": dict(mbpp_patterns.get("keywords", {}).most_common(50)),
            "operations": dict(mbpp_patterns.get("operations", {})),
            "data_types": dict(mbpp_patterns.get("data_types", {})),
            "algorithms": dict(mbpp_patterns.get("algorithms", {})),
            "problem_types": {k: len(v) for k, v in mbpp_patterns.get("problem_types", {}).items()}
        },
        "humaneval_patterns": {
            "keywords": dict(humaneval_patterns.get("keywords", {}).most_common(50)),
            "operations": dict(humaneval_patterns.get("operations", {})),
            "data_types": dict(humaneval_patterns.get("data_types", {})),
            "algorithms": dict(humaneval_patterns.get("algorithms", {})),
            "problem_types": {k: len(v) for k, v in humaneval_patterns.get("problem_types", {}).items()}
        },
        "template_suggestions": suggestions
    }
    
    output_file = project_root / "benchmark_pattern_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Review pattern analysis results")
    print("  2. Create templates for missing patterns")
    print("  3. Expand template library to 100+ patterns")
    print("  4. Implement execution feedback loops")
    print("  5. Add multi-candidate generation")
    print()


if __name__ == "__main__":
    main()
