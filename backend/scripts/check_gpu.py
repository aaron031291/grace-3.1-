"""Quick check: is the GPU available for embeddings? Run from backend: python scripts/check_gpu.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass
import os

def main():
    device_env = os.getenv("EMBEDDING_DEVICE", "cpu")
    print("EMBEDDING_DEVICE in .env:", device_env)
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        if cuda_ok:
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print("PyTorch CUDA: OK -", name, f"({mem:.1f} GB)")
            if device_env != "cuda":
                print("-> Set EMBEDDING_DEVICE=cuda in backend/.env to use GPU for embeddings.")
            else:
                print("-> Embeddings will use GPU.")
        else:
            print("PyTorch CUDA: not available (CPU-only PyTorch or no GPU).")
            if device_env == "cuda":
                print("-> Run fix_embedding_gpu.bat (Python 3.12 + PyTorch CUDA), then set EMBEDDING_DEVICE=cuda.")
            else:
                print("-> Embeddings use CPU (expected).")
    except Exception as e:
        print("Check failed:", e)
    print("Python:", sys.version.split()[0])

if __name__ == "__main__":
    main()
