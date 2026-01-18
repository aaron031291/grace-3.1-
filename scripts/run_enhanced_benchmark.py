#!/usr/bin/env python3
"""
Enhanced Benchmark Runner

Run MBPP/HumanEval with all Grace enhancement techniques:
1. AST-based function name extraction
2. Bidirectional LLM client with circuit breakers
3. Verifier amplification with partial credit
4. Error-conditioned repair loop
5. Multi-candidate generation

Usage:
    python scripts/run_enhanced_benchmark.py --problems 100 --benchmark mbpp
    python scripts/run_enhanced_benchmark.py --problems 50 --benchmark humaneval --all-techniques
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'benchmark_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )


def check_systems():
    """Check that all systems are available."""
    print("\n" + "="*60)
    print("SYSTEM CHECK")
    print("="*60)
    
    status = {}
    
    # Check AST processor
    try:
        from benchmarking.ast_code_processor import ASTCodeProcessor
        processor = ASTCodeProcessor()
        status["AST Processor"] = "✓ Available"
    except Exception as e:
        status["AST Processor"] = f"✗ {e}"
    
    # Check bidirectional LLM client
    try:
        from llm_orchestrator.bidirectional_llm_client import get_bidirectional_llm_client
        client = get_bidirectional_llm_client()
        client_status = client.get_status()
        status["LLM Client"] = f"✓ {client_status['state']}"
    except Exception as e:
        status["LLM Client"] = f"✗ {e}"
    
    # Check verifier
    try:
        from benchmarking.verifier_amplification import VerifierAmplification
        verifier = VerifierAmplification()
        status["Verifier"] = "✓ Available"
    except Exception as e:
        status["Verifier"] = f"✗ {e}"
    
    # Check templates
    try:
        from benchmarking.mbpp_templates import generate_from_template
        status["Templates"] = "✓ Available"
    except Exception as e:
        status["Templates"] = f"✗ {e}"
    
    # Check enhanced integration
    try:
        from benchmarking.enhanced_mbpp_integration import EnhancedMBPPIntegration
        status["Enhanced MBPP"] = "✓ Available"
    except Exception as e:
        status["Enhanced MBPP"] = f"✗ {e}"
    
    for system, state in status.items():
        print(f"  {system}: {state}")
    
    print("="*60 + "\n")
    
    return all("✓" in s for s in status.values())


def run_mbpp(args):
    """Run MBPP benchmark."""
    from benchmarking.enhanced_mbpp_integration import (
        EnhancedMBPPIntegration, 
        EvaluationConfig
    )
    
    config = EvaluationConfig(
        max_problems=args.problems,
        use_ast_processing=args.all_techniques or args.ast,
        use_verifier=args.all_techniques or args.verifier,
        use_repair=args.all_techniques or args.repair,
        use_multi_candidate=args.all_techniques or args.multi_candidate,
        use_extra_tests=args.all_techniques or args.extra_tests,
        num_candidates=args.num_candidates,
        parallel_workers=args.workers,
        template_first=not args.llm_first
    )
    
    print("\nConfiguration:")
    print(f"  Problems: {config.max_problems}")
    print(f"  AST Processing: {config.use_ast_processing}")
    print(f"  Verifier: {config.use_verifier}")
    print(f"  Repair: {config.use_repair}")
    print(f"  Multi-candidate: {config.use_multi_candidate}")
    print(f"  Extra tests: {config.use_extra_tests}")
    print(f"  Workers: {config.parallel_workers}")
    print()
    
    integration = EnhancedMBPPIntegration(config)
    result = integration.run_evaluation(parallel=args.workers > 1)
    
    # Save results
    output_file = f"mbpp_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    integration.save_results(result, output_file)
    
    return result


def run_humaneval(args):
    """Run HumanEval benchmark."""
    print("\nHumanEval evaluation with enhanced techniques...")
    
    # For now, use the existing humaneval integration
    try:
        from benchmarking.humaneval_integration import HumanEvalIntegration
        
        integration = HumanEvalIntegration()
        
        # Apply AST processing to HumanEval
        if args.all_techniques or args.ast:
            from benchmarking.ast_code_processor import ASTCodeProcessor
            integration.ast_processor = ASTCodeProcessor()
        
        result = integration.run_evaluation(max_problems=args.problems)
        
        print(f"\nHumanEval Pass Rate: {result.get('pass_rate', 0):.2%}")
        return result
        
    except Exception as e:
        print(f"HumanEval evaluation failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Run enhanced benchmarks with Grace systems"
    )
    
    parser.add_argument(
        "--benchmark", "-b",
        choices=["mbpp", "humaneval", "both"],
        default="mbpp",
        help="Benchmark to run"
    )
    
    parser.add_argument(
        "--problems", "-p",
        type=int,
        default=100,
        help="Number of problems to evaluate"
    )
    
    parser.add_argument(
        "--all-techniques", "-a",
        action="store_true",
        help="Enable all enhancement techniques"
    )
    
    parser.add_argument(
        "--ast",
        action="store_true",
        help="Enable AST-based processing"
    )
    
    parser.add_argument(
        "--verifier",
        action="store_true",
        help="Enable verifier amplification"
    )
    
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Enable error-conditioned repair"
    )
    
    parser.add_argument(
        "--multi-candidate",
        action="store_true",
        help="Enable multi-candidate generation"
    )
    
    parser.add_argument(
        "--extra-tests",
        action="store_true",
        help="Generate extra tests for scoring"
    )
    
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=5,
        help="Number of candidates to generate"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--llm-first",
        action="store_true",
        help="Try LLM before templates"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check system availability"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Check systems
    all_available = check_systems()
    
    if args.check_only:
        sys.exit(0 if all_available else 1)
    
    if not all_available:
        print("Warning: Some systems not available. Continuing with available systems...")
    
    # Run benchmarks
    if args.benchmark in ["mbpp", "both"]:
        print("\n" + "="*60)
        print("RUNNING MBPP BENCHMARK")
        print("="*60)
        mbpp_result = run_mbpp(args)
        
        if mbpp_result:
            print(f"\n✓ MBPP Complete: {mbpp_result.pass_rate*100:.2f}% pass rate")
    
    if args.benchmark in ["humaneval", "both"]:
        print("\n" + "="*60)
        print("RUNNING HUMANEVAL BENCHMARK")
        print("="*60)
        humaneval_result = run_humaneval(args)
        
        if humaneval_result:
            print(f"\n✓ HumanEval Complete")
    
    print("\n" + "="*60)
    print("BENCHMARK RUN COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
