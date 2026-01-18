"""
Run Standard LLM Benchmarks - HumanEval, GSM8K, MMLU, Reliability & Safety

Usage:
    python scripts/run_standard_benchmarks.py --provider openai --api-key YOUR_KEY
    python scripts/run_standard_benchmarks.py --provider anthropic --all
    python scripts/run_standard_benchmarks.py --provider grace --benchmark humaneval
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.benchmarks.standard_llm_benchmarks import (
    StandardLLMBenchmarks,
    LLMProvider,
    BenchmarkResult,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_openai_llm_call(api_key: str, model: str = "gpt-4o"):
    """Create OpenAI LLM call function."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        def llm_call(prompt: str) -> str:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.0
            )
            return response.choices[0].message.content
        
        return llm_call
    except ImportError:
        logger.error("OpenAI package not installed. Run: pip install openai")
        return None


def get_anthropic_llm_call(api_key: str, model: str = "claude-3-5-sonnet-20241022"):
    """Create Anthropic LLM call function."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        def llm_call(prompt: str) -> str:
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        return llm_call
    except ImportError:
        logger.error("Anthropic package not installed. Run: pip install anthropic")
        return None


def get_google_llm_call(api_key: str, model: str = "gemini-1.5-pro"):
    """Create Google Gemini LLM call function."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)
        
        def llm_call(prompt: str) -> str:
            response = model_instance.generate_content(prompt)
            return response.text
        
        return llm_call
    except ImportError:
        logger.error("Google GenAI package not installed. Run: pip install google-generativeai")
        return None


def get_deepseek_llm_call(api_key: str, model: str = "deepseek-coder"):
    """Create DeepSeek LLM call function."""
    try:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        def llm_call(prompt: str) -> str:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.0
            )
            return response.choices[0].message.content
        
        return llm_call
    except ImportError:
        logger.error("OpenAI package not installed. Run: pip install openai")
        return None


def get_grace_llm_call():
    """Create Grace LLM call function."""
    try:
        from backend.agent.grace_agent import GraceAgent
        agent = GraceAgent()
        
        def llm_call(prompt: str) -> str:
            return agent.generate(prompt)
        
        return llm_call
    except Exception as e:
        logger.error(f"Grace agent not available: {e}")
        
        def fallback_llm_call(prompt: str) -> str:
            return "Grace agent not available"
        
        return fallback_llm_call


def get_llm_call(provider: str, api_key: str = None, model: str = None):
    """Get LLM call function for provider."""
    provider = provider.lower()
    
    if provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        return get_openai_llm_call(key, model or "gpt-4o")
    
    elif provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY or use --api-key")
        return get_anthropic_llm_call(key, model or "claude-3-5-sonnet-20241022")
    
    elif provider == "google":
        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY or use --api-key")
        return get_google_llm_call(key, model or "gemini-1.5-pro")
    
    elif provider == "deepseek":
        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DeepSeek API key required. Set DEEPSEEK_API_KEY or use --api-key")
        return get_deepseek_llm_call(key, model or "deepseek-coder")
    
    elif provider == "grace":
        return get_grace_llm_call()
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def run_benchmarks(args):
    """Run benchmarks based on arguments."""
    logger.info(f"Starting benchmarks for provider: {args.provider}")
    
    llm_call = get_llm_call(args.provider, args.api_key, args.model)
    if not llm_call:
        logger.error("Failed to initialize LLM call function")
        return
    
    provider = LLMProvider(args.provider.lower())
    benchmarks = StandardLLMBenchmarks()
    
    results = {}
    
    if args.benchmark == "all" or args.benchmark == "humaneval":
        logger.info("Running HumanEval benchmark...")
        results['humaneval'] = await benchmarks.run_humaneval_benchmark(
            llm_call, provider, args.num_problems
        )
        logger.info(f"HumanEval: {results['humaneval'].accuracy:.2%}")
    
    if args.benchmark == "all" or args.benchmark == "gsm8k":
        logger.info("Running GSM8K benchmark...")
        results['gsm8k'] = await benchmarks.run_gsm8k_benchmark(
            llm_call, provider, args.num_problems
        )
        logger.info(f"GSM8K: {results['gsm8k'].accuracy:.2%}")
    
    if args.benchmark == "all" or args.benchmark == "mmlu":
        logger.info("Running MMLU benchmark...")
        subjects = args.subjects.split(",") if args.subjects else None
        results['mmlu'] = await benchmarks.run_mmlu_benchmark(
            llm_call, provider, subjects
        )
        logger.info(f"MMLU: {results['mmlu'].accuracy:.2%}")
    
    if args.benchmark == "all" or args.benchmark == "reliability":
        logger.info("Running Reliability benchmark...")
        results['reliability'] = await benchmarks.run_reliability_benchmark(
            llm_call, provider, args.iterations
        )
        logger.info(f"Reliability: {results['reliability'].accuracy:.2%}")
    
    if args.benchmark == "all" or args.benchmark == "safety":
        logger.info("Running Safety benchmark...")
        results['safety'] = await benchmarks.run_safety_benchmark(llm_call, provider)
        logger.info(f"Safety: {results['safety'].accuracy:.2%}")
    
    report = benchmarks.generate_report(results)
    print(report)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output or f"benchmark_results_{args.provider}_{timestamp}.json"
    benchmarks.save_results(results, output_file)
    logger.info(f"Results saved to {output_file}")
    
    report_file = output_file.replace(".json", ".txt")
    with open(report_file, 'w') as f:
        f.write(report)
    logger.info(f"Report saved to {report_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run Standard LLM Benchmarks")
    
    parser.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["openai", "anthropic", "google", "deepseek", "grace"],
        help="LLM provider to benchmark"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key for the provider (or set via environment variable)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model to use (defaults to provider's best model)"
    )
    
    parser.add_argument(
        "--benchmark",
        type=str,
        default="all",
        choices=["all", "humaneval", "gsm8k", "mmlu", "reliability", "safety"],
        help="Which benchmark to run"
    )
    
    parser.add_argument(
        "--num-problems",
        type=int,
        default=10,
        help="Number of problems for HumanEval/GSM8K"
    )
    
    parser.add_argument(
        "--subjects",
        type=str,
        help="Comma-separated MMLU subjects (e.g., 'computer_science,machine_learning')"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations for reliability benchmark"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for results"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmarks(args))


if __name__ == "__main__":
    main()
