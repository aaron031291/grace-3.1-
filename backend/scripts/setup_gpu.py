#!/usr/bin/env python3
"""
Set up GPU components for GRACE: PyTorch with CUDA, and EMBEDDING_DEVICE=cuda.
Run from backend with venv active:  python scripts/setup_gpu.py
Or from project root:  py -3.12 backend/scripts/setup_gpu.py  (use 3.12 for CUDA wheels)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND / ".env"
ENV_EXAMPLE = BACKEND / ".env.example"
# PyTorch CUDA 12.1 wheels (no local CUDA toolkit required)
TORCH_CUDA_INDEX = "https://download.pytorch.org/whl/cu121"

# Python 3.11/3.12 have CUDA wheels; 3.13+ often do not
def _python_version_ok_for_cuda():
    v = sys.version_info
    return (v.major == 3 and v.minor in (11, 12))


def run(cmd, capture=True, shell=True):
    try:
        r = subprocess.run(
            cmd if isinstance(cmd, str) else " ".join(cmd),
            shell=shell,
            capture_output=capture,
            text=True,
            timeout=300,
            cwd=str(BACKEND),
        )
        return (r.returncode == 0, (r.stdout or "") + (r.stderr or ""))
    except Exception as e:
        return False, str(e)


def check_nvidia_smi():
    ok, out = run("nvidia-smi", capture=True)
    if not ok:
        print("[GPU] nvidia-smi not found or failed. Install NVIDIA drivers.")
        return False
    print("[GPU] NVIDIA driver OK")
    print(out.strip()[:400])
    return True


def install_torch_cuda():
    print("[GPU] Installing PyTorch with CUDA 12.1 (this may take a few minutes)...")
    ok, out = run(
        [
            sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall",
            "torch",
            "--index-url", TORCH_CUDA_INDEX,
        ],
        capture=True,
        shell=False,
    )
    if ok:
        print("[GPU] PyTorch CUDA install completed.")
        return True
    # No CUDA wheels for this Python (e.g. 3.14); try default PyTorch (often CPU-only)
    if "No matching distribution" in out or "none" in out:
        import platform
        py_ver = platform.python_version()
        print(f"[GPU] No PyTorch CUDA wheels for Python {py_ver}. Installing default torch (may be CPU-only).")
        print("[GPU] For GPU embeddings, use Python 3.11 or 3.12:  py -3.12 -m venv venv  then re-run this script.")
    ok2, out2 = run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "torch"],
        capture=True,
        shell=False,
    )
    if not ok2:
        print("[GPU] PyTorch install failed:")
        print(out2[-1500:] if len(out2) > 1500 else out2)
        return False
    print("[GPU] PyTorch (default) installed. Set EMBEDDING_DEVICE=cuda when using Python 3.11/3.12 for GPU.")
    return True


def verify_torch_cuda():
    """Verify CUDA works with a real kernel (catches RTX 5090 / sm_120 with PyTorch built for older archs)."""
    try:
        import torch
        if not torch.cuda.is_available():
            print("[GPU] PyTorch installed but CUDA not available (driver or GPU issue).")
            return False
        name = torch.cuda.get_device_name(0)
        mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        # Actually run a kernel; RTX 5090 (sm_120) fails with "no kernel image is available"
        try:
            torch.zeros(1, device="cuda").item()
        except RuntimeError as e:
            if "no kernel image is available" in str(e):
                print(f"[GPU] {name} detected but PyTorch has no kernel for this GPU (e.g. RTX 5090 / sm_120).")
                print("[GPU] Use CPU for embeddings until PyTorch ships sm_120 support. Setting EMBEDDING_DEVICE=cpu.")
                return False
            raise
        print(f"[GPU] PyTorch CUDA OK: {name} ({mem_gb:.1f} GB)")
        return True
    except Exception as e:
        print(f"[GPU] Verify failed: {e}")
        return False


def set_env_embedding_device(use_cuda: bool):
    """Set EMBEDDING_DEVICE in .env to cuda or cpu to match actual capability."""
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            import shutil
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            print("[GPU] Created .env from .env.example")
        else:
            print("[GPU] No .env or .env.example; set EMBEDDING_DEVICE=cuda or cpu manually.")
            return False

    value = "cuda" if use_cuda else "cpu"
    text = ENV_FILE.read_text(encoding="utf-8")
    if "EMBEDDING_DEVICE=" in text:
        new_text = re.sub(r"EMBEDDING_DEVICE=\w+", f"EMBEDDING_DEVICE={value}", text)
    else:
        if "EMBEDDING_DEFAULT=" in text:
            new_text = re.sub(
                r"(EMBEDDING_DEFAULT=[^\n]*)",
                f"\\1\nEMBEDDING_DEVICE={value}",
                text,
                count=1,
            )
        else:
            new_text = text.rstrip() + f"\nEMBEDDING_DEVICE={value}\n"

    if new_text != text:
        ENV_FILE.write_text(new_text, encoding="utf-8")
        print(f"[GPU] Set EMBEDDING_DEVICE={value} in backend/.env")
    else:
        print(f"[GPU] EMBEDDING_DEVICE={value} already set.")
    return True


def main():
    print("=== GRACE GPU setup ===\n")
    if not _python_version_ok_for_cuda():
        print(f"[GPU] Current Python is {sys.version.split()[0]}. CUDA wheels are for 3.11 or 3.12.")
        print("[GPU] From project root run:  py -3.12 backend\\scripts\\setup_gpu.py")
        print("[GPU] Or create a 3.12 venv:  cd backend  &&  py -3.12 -m venv venv  &&  venv\\Scripts\\activate  &&  pip install -r requirements.txt  &&  python scripts\\setup_gpu.py")
        print()
    if not check_nvidia_smi():
        print("\nStopping. Fix NVIDIA drivers and re-run.")
        return 1
    print()
    if not install_torch_cuda():
        return 1
    print()
    cuda_ok = verify_torch_cuda()
    if not cuda_ok:
        print("CUDA not available; embeddings will use CPU.")
    print()
    set_env_embedding_device(use_cuda=cuda_ok)
    if cuda_ok:
        print("\nDone. Restart the backend to use GPU for embeddings.")
    else:
        print("\nDone. Embeddings will use CPU. For GPU: use Python 3.11 or 3.12, then re-run this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
