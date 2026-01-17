#!/usr/bin/env python3
"""
Download Full Benchmark Datasets

Ensures datasets library is installed and downloads full HumanEval and MBPP datasets.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))


def ensure_datasets_library():
    """Ensure datasets library is installed."""
    print("=" * 80)
    print("ENSURING DATASETS LIBRARY IS INSTALLED")
    print("=" * 80)
    print()
    
    try:
        import datasets
        print(f"[OK] datasets library already installed (version: {datasets.__version__})")
        return True
    except ImportError:
        print("Installing datasets library...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "datasets", "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            import datasets
            print(f"[OK] datasets library installed successfully (version: {datasets.__version__})")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to install datasets library: {e}")
            return False


def download_humaneval():
    """Download full HumanEval dataset."""
    print()
    print("=" * 80)
    print("DOWNLOADING HUMANEVAL DATASET")
    print("=" * 80)
    print()
    
    try:
        from datasets import load_dataset
        
        dataset_names = [
            "openai/humaneval",
            "bigcode/humaneval",
            "THUDM/humaneval"
        ]
        
        for name in dataset_names:
            try:
                print(f"Trying to load: {name}...")
                dataset = load_dataset(name, split="test")
                problems = [item for item in dataset]
                print(f"[OK] Successfully loaded {len(problems)} problems from {name}")
                return True, len(problems)
            except Exception as e:
                print(f"  Failed: {e}")
                continue
        
        print("[FAIL] Could not load from any HuggingFace source")
        return False, 0
        
    except Exception as e:
        print(f"[FAIL] Error downloading HumanEval: {e}")
        return False, 0


def download_mbpp():
    """Download full MBPP dataset."""
    print()
    print("=" * 80)
    print("DOWNLOADING MBPP DATASET")
    print("=" * 80)
    print()
    
    try:
        from datasets import load_dataset
        
        dataset_names = [
            "mbpp",
            "mbpp/sanitized",
            "google/mbpp"
        ]
        
        for name in dataset_names:
            try:
                print(f"Trying to load: {name}...")
                dataset = load_dataset(name, split="test")
                problems = [item for item in dataset]
                print(f"[OK] Successfully loaded {len(problems)} problems from {name}")
                return True, len(problems)
            except Exception as e:
                print(f"  Failed: {e}")
                continue
        
        print("[FAIL] Could not load from any HuggingFace source")
        return False, 0
        
    except Exception as e:
        print(f"[FAIL] Error downloading MBPP: {e}")
        return False, 0


def main():
    """Main function."""
    print("=" * 80)
    print("FULL BENCHMARK DATASET DOWNLOADER")
    print("=" * 80)
    print()
    print("This script will:")
    print("1. Ensure datasets library is installed")
    print("2. Download full HumanEval dataset (164 problems)")
    print("3. Download full MBPP dataset (~974 problems)")
    print()
    
    # Step 1: Ensure datasets library
    if not ensure_datasets_library():
        print("\n✗ Cannot proceed without datasets library")
        return 1
    
    # Step 2: Download HumanEval
    humaneval_success, humaneval_count = download_humaneval()
    
    # Step 3: Download MBPP
    mbpp_success, mbpp_count = download_mbpp()
    
    # Summary
    print()
    print("=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print()
    print(f"HumanEval: {'[OK]' if humaneval_success else '[FAIL]'} ({humaneval_count} problems)")
    print(f"MBPP:      {'[OK]' if mbpp_success else '[FAIL]'} ({mbpp_count} problems)")
    print()
    
    if humaneval_success and mbpp_success:
        print("[OK] Both datasets downloaded successfully!")
        print("You can now run benchmarks with full datasets:")
        print("  python scripts/run_all_benchmarks.py --benchmarks humaneval mbpp")
        return 0
    else:
        print("[WARN] Some datasets failed to download")
        print("Benchmarks will use sample problems if full datasets unavailable")
        return 1


if __name__ == "__main__":
    sys.exit(main())
