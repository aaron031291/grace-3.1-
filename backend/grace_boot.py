"""
Grace 3.1 — Phased Enterprise Boot Launcher
============================================

Phase 1 (sync):   Config → credentials → database connection
Phase 2 (parallel): Qdrant + Ollama + Embedding in parallel threads
Phase 3 (start):  Uvicorn serves API — UI available at ~15s
Phase 4 (lazy):   Background subsystems load after API is live

Nothing in Grace's existing code is modified. This file wraps the boot.
"""

import sys
import os
import time
import threading
import signal
import logging

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Ensure we're in backend/ ──────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("grace.boot")


# ══════════════════════════════════════════════════════════════════
# PHASE 1 — Synchronous: Config + Credentials + Database
# ══════════════════════════════════════════════════════════════════

def phase1_config():
    """Load settings, validate credentials, connect to database."""
    t0 = time.time()
    log.info("PHASE 1 — Config + Database")

    # 1a. Load settings
    try:
        from settings import settings
        provider = settings.LLM_PROVIDER
        log.info(f"  [OK] Settings loaded (LLM_PROVIDER={provider})")
    except Exception as e:
        log.error(f"  [FAIL] Settings: {e}")
        return False

    # 1b. Validate credentials based on provider
    cred_ok = True
    if provider == "kimi" and not settings.KIMI_API_KEY:
        log.warning("  [WARN] KIMI_API_KEY not set")
        cred_ok = False
    if provider == "opus" and not settings.OPUS_API_KEY:
        log.warning("  [WARN] OPUS_API_KEY not set")
        cred_ok = False
    if cred_ok:
        log.info("  [OK] Credentials validated")

    # 1c. Database connection
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory
        from database.migration import create_tables

        db_type = DatabaseType(getattr(settings, 'DATABASE_TYPE', 'sqlite'))
        db_config = DatabaseConfig(
            db_type=db_type,
            host=getattr(settings, 'DATABASE_HOST', None),
            port=getattr(settings, 'DATABASE_PORT', None),
            username=getattr(settings, 'DATABASE_USER', ''),
            password=getattr(settings, 'DATABASE_PASSWORD', ''),
            database=getattr(settings, 'DATABASE_NAME', 'grace'),
            database_path=getattr(settings, 'DATABASE_PATH', ''),
            echo=getattr(settings, 'DATABASE_ECHO', False),
            sslmode=(getattr(settings, 'DATABASE_SSLMODE', '') or '').strip() or None,
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        create_tables()
        log.info(f"  [OK] Database connected ({db_type.value})")
    except Exception as e:
        log.error(f"  [FAIL] Database: {e}")
        return False

    # 1d. Auto-migrate schema
    try:
        from database.auto_migrate import run_auto_migrate
        engine = DatabaseConnection.get_engine()
        changes = run_auto_migrate(engine)
        if changes:
            log.info(f"  [OK] Schema migrated: {len(changes)} fix(es)")
        else:
            log.info("  [OK] Schema up to date")
    except Exception as e:
        log.warning(f"  [WARN] Schema migrate: {e}")

    log.info(f"  Phase 1 done in {time.time()-t0:.1f}s")
    return True


# ══════════════════════════════════════════════════════════════════
# PHASE 2 — Parallel: External services (Qdrant, Ollama, Embedding)
# ══════════════════════════════════════════════════════════════════

class ServiceProbe:
    """Probes an external service in a thread, reports ready/not."""
    def __init__(self, name, probe_fn):
        self.name = name
        self.probe_fn = probe_fn
        self.ready = False
        self.error = None
        self.latency_ms = 0

    def run(self):
        t0 = time.time()
        try:
            self.probe_fn()
            self.ready = True
            self.latency_ms = round((time.time() - t0) * 1000)
        except Exception as e:
            self.error = str(e)[:200]
            self.latency_ms = round((time.time() - t0) * 1000)


def _probe_ollama():
    from settings import settings
    from llm_orchestrator.factory import get_llm_client
    client = get_llm_client()
    if not client.is_running():
        raise RuntimeError("Ollama not responding")


def _probe_qdrant():
    from settings import settings
    if getattr(settings, 'SKIP_QDRANT_CHECK', False):
        return
    from vector_db.client import get_qdrant_client
    client = get_qdrant_client()
    collections = client.get_collections()


def _probe_embedding():
    from settings import settings
    if getattr(settings, 'SKIP_EMBEDDING_LOAD', False):
        return
    from embedding import get_embedder
    embedder = get_embedder()
    embedder.embed_text(["boot check"])


def phase2_services():
    """Probe Ollama, Qdrant, Embedding in parallel."""
    t0 = time.time()
    log.info("PHASE 2 — Services (parallel)")

    probes = [
        ServiceProbe("Ollama/LLM", _probe_ollama),
        ServiceProbe("Qdrant", _probe_qdrant),
        ServiceProbe("Embedding", _probe_embedding),
    ]

    threads = []
    for p in probes:
        t = threading.Thread(target=p.run, name=f"probe-{p.name}", daemon=True)
        threads.append(t)
        t.start()

    # Wait max 30s for all probes
    for t in threads:
        t.join(timeout=30)

    all_ok = True
    for p in probes:
        if p.ready:
            log.info(f"  [OK] {p.name} ready ({p.latency_ms}ms)")
        else:
            log.warning(f"  [WARN] {p.name}: {p.error or 'timeout'}")
            all_ok = False

    log.info(f"  Phase 2 done in {time.time()-t0:.1f}s")
    return all_ok


# ══════════════════════════════════════════════════════════════════
# PHASE 3 — Start API Server (UI available after this)
# ══════════════════════════════════════════════════════════════════

def phase3_serve():
    """Start uvicorn — API becomes available, UI can connect."""
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        timeout_keep_alive=120,
    )


# ══════════════════════════════════════════════════════════════════
# MAIN — Phased boot sequence
# ══════════════════════════════════════════════════════════════════

def main():
    boot_start = time.time()

    print()
    print("=" * 60)
    print("  Grace 3.1 — Enterprise Phased Boot")
    print("=" * 60)
    print()

    # Phase 1: Config + DB (synchronous, must succeed)
    if not phase1_config():
        log.error("Phase 1 FAILED — cannot start without config + database")
        sys.exit(1)

    # Phase 2: External services (parallel, warnings only)
    phase2_services()

    boot_time = time.time() - boot_start
    print()
    log.info(f"PHASE 3 — Starting API server")
    print()
    print(f"  Boot completed in {boot_time:.1f}s")
    print(f"  4 coding agents: qwen, kimi, opus, ollama")
    print(f"  Subsystems lazy-load on first request")
    print()
    print(f"  API:         http://localhost:8000")
    print(f"  API Docs:    http://localhost:8000/docs")
    print(f"  Frontend:    http://localhost:5173")
    print(f"  Ops Console: open dev-console/index.html")
    print()
    print("=" * 60)
    print()

    # Phase 3: Start serving (blocks)
    phase3_serve()


if __name__ == "__main__":
    main()
