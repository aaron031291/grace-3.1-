#!/usr/bin/env python3
"""
Service Health Checker for GRACE 3.1

Checks status of all required and optional services before/during startup.
Provides clear status report and setup instructions.
"""

import sys
import requests
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def check_database() -> Tuple[bool, str]:
    """Check database connection."""
    try:
        from database.connection import DatabaseConnection
        if DatabaseConnection.health_check():
            return True, "[OK] Connected"
        else:
            return False, "[FAIL] Connection unhealthy"
    except Exception as e:
        return False, f"[FAIL] Error: {str(e)}"


def check_qdrant() -> Tuple[bool, str]:
    """Check Qdrant vector database."""
    try:
        response = requests.get("http://localhost:6333/healthz", timeout=2)
        if response.status_code == 200:
            return True, "[OK] Running on port 6333"
        else:
            return False, f"[FAIL] Unexpected status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "[SKIP] Not running (optional service)"
    except Exception as e:
        return False, f"[FAIL] Error: {str(e)}"


def check_ollama() -> Tuple[bool, str]:
    """Check Ollama service."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_count = len(models)
            return True, f"[OK] Running with {model_count} model(s) (optional service)"
        else:
            return False, f"[FAIL] Unexpected status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "[SKIP] Not running (optional service)"
    except Exception as e:
        return False, f"[FAIL] Error: {str(e)}"


def check_embedding_model() -> Tuple[bool, str]:
    """Check if embedding model exists."""
    try:
        from settings import Settings
        model_path = Path(Settings.EMBEDDING_MODEL_PATH)
        if model_path.exists():
            return True, f"[OK] Found at {model_path}"
        else:
            return False, "[WARN] Not found (will download on first use - optional)"
    except Exception as e:
        return False, f"[FAIL] Error checking: {str(e)}"


def check_backend_api() -> Tuple[bool, str]:
    """Check if backend API is responding."""
    try:
        response = requests.get("http://localhost:8000/health/live", timeout=2)
        if response.status_code == 200:
            return True, "[OK] Running on port 8000"
        else:
            return False, f"[FAIL] Unexpected status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "[FAIL] Not running"
    except Exception as e:
        return False, f"[FAIL] Error: {str(e)}"


def get_health_status() -> Dict:
    """Get overall health status from backend."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "unknown", "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def main():
    """Run service health checks."""
    print("=" * 80)
    print("GRACE 3.1 Service Health Check")
    print("=" * 80)
    print()
    
    services = {
        "Required Services": [
            ("Database (SQLite/PostgreSQL)", check_database, True),
            ("Backend API (FastAPI)", check_backend_api, True),
        ],
        "Optional Services": [
            ("Qdrant Vector DB", check_qdrant, False),
            ("Ollama LLM Service", check_ollama, False),
            ("Embedding Model", check_embedding_model, False),
        ]
    }
    
    all_required_ok = True
    any_optional_ok = False
    
    for category, service_list in services.items():
        print(f"{category}:")
        print("-" * 80)
        
        for name, check_func, required in service_list:
            is_ok, message = check_func()
            print(f"  {name}: {message}")
            
            if required and not is_ok:
                all_required_ok = False
            if not required and is_ok:
                any_optional_ok = True
        
        print()
    
    # Check backend health endpoint
    print("Backend Health Status:")
    print("-" * 80)
    health = get_health_status()
    if "error" in health:
        print(f"  [WARN] Could not check: {health['error']}")
    else:
        status = health.get("status", "unknown")
        print(f"  Status: {status.upper()}")
        
        if "details" in health:
            details = health["details"]
            for service, status_detail in details.items():
                if isinstance(status_detail, dict):
                    svc_status = status_detail.get("status", "unknown")
                    print(f"    - {service}: {svc_status}")
    
    print()
    print("=" * 80)
    
    # Summary
    if all_required_ok:
        if health.get("status") == "healthy":
            print("[OK] System Status: FULL OPERATIONAL")
            print("   All required and optional services are running.")
        elif health.get("status") == "degraded":
            print("[WARN] System Status: DEGRADED MODE")
            print("   Core services OK, but some optional services unavailable.")
            print("   System is functional but with limited capabilities.")
        else:
            print("[WARN] System Status: UNKNOWN")
            print("   Backend may be starting or experiencing issues.")
    else:
        print("[FAIL] System Status: STARTUP BLOCKED")
        print("   Required services are missing or unavailable.")
        print("   Please fix required service issues before starting.")
    
    print("=" * 80)
    
    # Setup instructions for missing services
    if not all_required_ok or health.get("status") == "degraded":
        print()
        print("Setup Instructions:")
        print("-" * 80)
        
        qdrant_ok, _ = check_qdrant()
        if not qdrant_ok:
            print("[SETUP] To start Qdrant:")
            print("   docker run -d -p 6333:6333 qdrant/qdrant")
        
        ollama_ok, _ = check_ollama()
        if not ollama_ok:
            print("[SETUP] To start Ollama:")
            print("   1. Install: https://ollama.ai/download")
            print("   2. Run: ollama serve")
        
        embedding_ok, _ = check_embedding_model()
        if not embedding_ok:
            print("[SETUP] Embedding model:")
            print("   Will download automatically on first use")
            print("   Or manually: python -c 'from embedding.embedder import get_embedding_model; get_embedding_model()'")


if __name__ == "__main__":
    main()