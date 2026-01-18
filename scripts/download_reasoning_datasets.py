"""
Download Math & Reasoning Datasets for Oracle Knowledge Base

Datasets distilled from GPT-4, Claude, and open-source LLMs.
Use for benchmarking and training Grace's reasoning capabilities.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# DATASET REGISTRY - Math & Reasoning Knowledge from LLMs
# =============================================================================

DATASETS = {
    # -------------------------------------------------------------------------
    # MATH DATASETS (Grade School to Competition Level)
    # -------------------------------------------------------------------------
    "gsm8k": {
        "name": "gsm8k",
        "config": "main",
        "description": "8.5K grade school math problems with step-by-step solutions",
        "source": "OpenAI",
        "size": "~8,500 problems",
        "category": "math",
        "benchmark": True,
    },
    "math": {
        "name": "lighteval/MATH",
        "config": "all",
        "description": "12.5K competition math (AMC, AIME level)",
        "source": "Hendrycks et al.",
        "size": "~12,500 problems",
        "category": "math",
        "benchmark": True,
    },
    "metamath": {
        "name": "meta-math/MetaMathQA",
        "config": None,
        "description": "395K math Q&A - GPT-3.5 distilled, augmented GSM8K/MATH",
        "source": "GPT-3.5 Distillation",
        "size": "~395,000 problems",
        "category": "math",
        "benchmark": False,
    },
    "orca_math": {
        "name": "microsoft/orca-math-word-problems-200k",
        "config": None,
        "description": "200K word problems - GPT-4 distilled",
        "source": "GPT-4 Distillation (Microsoft)",
        "size": "~200,000 problems",
        "category": "math",
        "benchmark": False,
    },
    "openmath": {
        "name": "nvidia/OpenMathInstruct-1",
        "config": None,
        "description": "1.8M math solutions - Mixtral distilled",
        "source": "Mixtral Distillation (Nvidia)",
        "size": "~1,800,000 problems",
        "category": "math",
        "benchmark": False,
    },
    
    # -------------------------------------------------------------------------
    # REASONING DATASETS
    # -------------------------------------------------------------------------
    "arc": {
        "name": "allenai/ai2_arc",
        "config": "ARC-Challenge",
        "description": "Science reasoning questions (grade 3-9)",
        "source": "AI2",
        "size": "~7,787 questions",
        "category": "reasoning",
        "benchmark": True,
    },
    "hellaswag": {
        "name": "Rowan/hellaswag",
        "config": None,
        "description": "Commonsense reasoning - sentence completion",
        "source": "AI2",
        "size": "~70,000 examples",
        "category": "reasoning",
        "benchmark": True,
    },
    "winogrande": {
        "name": "allenai/winogrande",
        "config": "winogrande_xl",
        "description": "Commonsense reasoning - pronoun resolution",
        "source": "AI2",
        "size": "~44,000 examples",
        "category": "reasoning",
        "benchmark": True,
    },
    "boolq": {
        "name": "google/boolq",
        "config": None,
        "description": "Yes/No reading comprehension questions",
        "source": "Google",
        "size": "~16,000 questions",
        "category": "reasoning",
        "benchmark": True,
    },
    "piqa": {
        "name": "ybisk/piqa",
        "config": None,
        "description": "Physical intuition reasoning",
        "source": "AI2",
        "size": "~21,000 questions",
        "category": "reasoning",
        "benchmark": True,
    },
    
    # -------------------------------------------------------------------------
    # CHAIN-OF-THOUGHT / REASONING TRACES
    # -------------------------------------------------------------------------
    "cot_collection": {
        "name": "kaist-ai/CoT-Collection",
        "config": None,
        "description": "1.88M chain-of-thought reasoning traces",
        "source": "Multiple LLMs",
        "size": "~1,880,000 traces",
        "category": "cot",
        "benchmark": False,
    },
    "orca": {
        "name": "Open-Orca/OpenOrca",
        "config": None,
        "description": "4.2M GPT-4 reasoning explanations",
        "source": "GPT-4 Distillation",
        "size": "~4,200,000 examples",
        "category": "cot",
        "benchmark": False,
    },
    
    # -------------------------------------------------------------------------
    # CODE REASONING
    # -------------------------------------------------------------------------
    "humaneval": {
        "name": "openai/openai_humaneval",
        "config": None,
        "description": "164 Python coding problems (benchmark)",
        "source": "OpenAI",
        "size": "164 problems",
        "category": "code",
        "benchmark": True,
    },
    "mbpp": {
        "name": "google-research-datasets/mbpp",
        "config": None,
        "description": "974 Python programming problems",
        "source": "Google",
        "size": "974 problems",
        "category": "code",
        "benchmark": True,
    },
    "code_alpaca": {
        "name": "sahil2801/CodeAlpaca-20k",
        "config": None,
        "description": "20K code instruction-following examples",
        "source": "GPT-3.5 Distillation",
        "size": "~20,000 examples",
        "category": "code",
        "benchmark": False,
    },
}


class OracleKnowledgeDownloader:
    """Download and format datasets for Oracle knowledge base."""
    
    def __init__(self, output_dir: str = "./data/oracle_knowledge"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.math_dir = self.output_dir / "math"
        self.reasoning_dir = self.output_dir / "reasoning"
        self.cot_dir = self.output_dir / "chain_of_thought"
        self.code_dir = self.output_dir / "code"
        self.benchmark_dir = self.output_dir / "benchmarks"
        
        for d in [self.math_dir, self.reasoning_dir, self.cot_dir, 
                  self.code_dir, self.benchmark_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def download_dataset(self, dataset_key: str, max_samples: Optional[int] = None) -> bool:
        """Download a single dataset."""
        
        if dataset_key not in DATASETS:
            logger.error(f"Unknown dataset: {dataset_key}")
            return False
        
        info = DATASETS[dataset_key]
        
        try:
            from datasets import load_dataset
        except ImportError:
            logger.error("Install datasets: pip install datasets")
            return False
        
        logger.info(f"Downloading: {info['name']}")
        logger.info(f"  Source: {info['source']} | Size: {info['size']}")
        
        try:
            # Load dataset
            if info.get("config"):
                ds = load_dataset(info["name"], info["config"], trust_remote_code=True)
            else:
                ds = load_dataset(info["name"], trust_remote_code=True)
            
            # Get output directory based on category
            category_dirs = {
                "math": self.math_dir,
                "reasoning": self.reasoning_dir,
                "cot": self.cot_dir,
                "code": self.code_dir,
            }
            output_path = category_dirs.get(info["category"], self.output_dir)
            
            # Also save to benchmarks if it's a benchmark dataset
            if info.get("benchmark"):
                self._save_benchmark(ds, dataset_key, info, max_samples)
            
            # Save full dataset
            dataset_path = output_path / dataset_key
            
            # Convert to list of dicts for JSON storage
            for split_name, split_data in ds.items():
                if max_samples and len(split_data) > max_samples:
                    split_data = split_data.select(range(max_samples))
                
                # Save as JSON for easy access
                json_path = dataset_path / f"{split_name}.json"
                json_path.parent.mkdir(parents=True, exist_ok=True)
                
                records = [dict(row) for row in split_data]
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"  Saved {len(records)} records to {json_path}")
            
            # Save metadata
            meta_path = dataset_path / "metadata.json"
            with open(meta_path, "w") as f:
                json.dump({
                    **info,
                    "downloaded_at": datetime.now().isoformat(),
                    "max_samples": max_samples,
                }, f, indent=2)
            
            logger.info(f"✓ Downloaded {dataset_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {dataset_key}: {e}")
            return False
    
    def _save_benchmark(self, ds, dataset_key: str, info: Dict, max_samples: Optional[int]):
        """Save benchmark-formatted version."""
        
        benchmark_path = self.benchmark_dir / f"{dataset_key}_benchmark.json"
        
        # Get test/validation split for benchmarking
        if "test" in ds:
            data = ds["test"]
        elif "validation" in ds:
            data = ds["validation"]
        else:
            data = list(ds.values())[0]
        
        if max_samples and len(data) > max_samples:
            data = data.select(range(max_samples))
        
        # Format for benchmarking
        benchmark_data = {
            "name": dataset_key,
            "description": info["description"],
            "category": info["category"],
            "source": info["source"],
            "num_problems": len(data),
            "problems": [dict(row) for row in data],
        }
        
        with open(benchmark_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"  Benchmark saved: {benchmark_path}")
    
    def download_core_benchmarks(self, max_samples: int = 500):
        """Download core benchmark datasets for testing."""
        
        logger.info("=" * 60)
        logger.info("DOWNLOADING CORE BENCHMARKS")
        logger.info("=" * 60)
        
        core = ["gsm8k", "math", "arc", "humaneval", "mbpp", "hellaswag"]
        
        results = {}
        for key in core:
            success = self.download_dataset(key, max_samples=max_samples)
            results[key] = success
        
        return results
    
    def download_math_training(self, max_samples: int = 50000):
        """Download math training data (distilled from LLMs)."""
        
        logger.info("=" * 60)
        logger.info("DOWNLOADING MATH TRAINING DATA")
        logger.info("=" * 60)
        
        # Ordered by quality/size
        training = ["metamath", "orca_math"]
        
        results = {}
        for key in training:
            success = self.download_dataset(key, max_samples=max_samples)
            results[key] = success
        
        return results
    
    def download_reasoning_traces(self, max_samples: int = 100000):
        """Download chain-of-thought reasoning traces."""
        
        logger.info("=" * 60)
        logger.info("DOWNLOADING REASONING TRACES (COT)")
        logger.info("=" * 60)
        
        cot_datasets = ["cot_collection"]
        
        results = {}
        for key in cot_datasets:
            success = self.download_dataset(key, max_samples=max_samples)
            results[key] = success
        
        return results
    
    def download_all(self, max_samples: Optional[int] = None):
        """Download all datasets."""
        
        logger.info("=" * 60)
        logger.info("DOWNLOADING ALL ORACLE KNOWLEDGE")
        logger.info("=" * 60)
        
        results = {}
        for key in DATASETS:
            success = self.download_dataset(key, max_samples=max_samples)
            results[key] = success
        
        # Generate summary
        self._generate_summary(results)
        return results
    
    def _generate_summary(self, results: Dict[str, bool]):
        """Generate download summary."""
        
        summary = {
            "downloaded_at": datetime.now().isoformat(),
            "datasets": {},
            "statistics": {
                "total": len(results),
                "successful": sum(results.values()),
                "failed": len(results) - sum(results.values()),
            }
        }
        
        for key, success in results.items():
            info = DATASETS[key]
            summary["datasets"][key] = {
                **info,
                "downloaded": success,
            }
        
        summary_path = self.output_dir / "oracle_knowledge_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\nSummary saved to {summary_path}")
        logger.info(f"  Total: {summary['statistics']['total']}")
        logger.info(f"  Downloaded: {summary['statistics']['successful']}")
        logger.info(f"  Failed: {summary['statistics']['failed']}")


def list_datasets():
    """List all available datasets."""
    
    print("\n" + "=" * 80)
    print("AVAILABLE DATASETS FOR ORACLE KNOWLEDGE BASE")
    print("=" * 80)
    
    categories = {}
    for key, info in DATASETS.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, info))
    
    for category, datasets in categories.items():
        print(f"\n📚 {category.upper()}")
        print("-" * 40)
        
        for key, info in datasets:
            benchmark = "🎯" if info.get("benchmark") else "  "
            print(f"  {benchmark} {key}")
            print(f"      {info['description']}")
            print(f"      Source: {info['source']} | Size: {info['size']}")
    
    print("\n" + "=" * 80)
    print("🎯 = Benchmark dataset (for testing)")
    print("=" * 80 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download reasoning datasets for Oracle")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--dataset", type=str, help="Download specific dataset")
    parser.add_argument("--benchmarks", action="store_true", help="Download core benchmarks only")
    parser.add_argument("--math", action="store_true", help="Download math training data")
    parser.add_argument("--cot", action="store_true", help="Download chain-of-thought traces")
    parser.add_argument("--all", action="store_true", help="Download all datasets")
    parser.add_argument("--output", type=str, default="./data/oracle_knowledge", help="Output directory")
    parser.add_argument("--max-samples", type=int, default=None, help="Max samples per dataset")
    
    args = parser.parse_args()
    
    if args.list or not any([args.dataset, args.benchmarks, args.math, args.cot, args.all]):
        list_datasets()
        return
    
    downloader = OracleKnowledgeDownloader(args.output)
    
    if args.dataset:
        downloader.download_dataset(args.dataset, args.max_samples)
    elif args.benchmarks:
        downloader.download_core_benchmarks(args.max_samples or 500)
    elif args.math:
        downloader.download_math_training(args.max_samples or 50000)
    elif args.cot:
        downloader.download_reasoning_traces(args.max_samples or 100000)
    elif args.all:
        downloader.download_all(args.max_samples)


if __name__ == "__main__":
    main()
