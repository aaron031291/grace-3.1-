"""
Check Qdrant connectivity. Run from project root: python backend/scripts/check_qdrant.py
Or from backend: python scripts/check_qdrant.py
"""
import sys
import os

# Allow importing from backend
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

def main():
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    url = os.getenv("QDRANT_URL", "")
    target = url or f"http://{host}:{port}"

    print(f"Checking Qdrant at {target} ...")
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        if client.is_connected():
            print("OK  Qdrant connection successful.")
            try:
                colls = client.list_collections()
                print(f"    Collections: {colls or '(none)'}")
            except Exception:
                pass
            return 0
    except Exception as e:
        print(f"FAIL Connection failure: {e}")
    print()
    print("To fix:")
    print("  1. Start Qdrant:  .\\start_services.bat qdrant")
    print("  2. Or manually:   docker start qdrant   (or  docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest)")
    print("  3. Verify:       curl http://localhost:6333/health")
    return 1

if __name__ == "__main__":
    sys.exit(main())
