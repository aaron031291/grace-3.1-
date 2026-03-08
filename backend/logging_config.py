import json
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime, timezone


import queue as _queue
import threading as _threading


class GenesisLogHandler(logging.Handler):
    """
    Sends WARNING+ log records to Genesis as keys -- NON-BLOCKING.

    Uses a background queue+thread so emit() never stalls the asyncio event
    loop or request handlers. Without this, genesis key creation (DB writes,
    file locks, thread spawns) would block every request that triggers a log.
    """
    # Class-level queue and worker thread shared across all instances
    _queue: "_queue.Queue" = _queue.Queue(maxsize=500)
    _worker = None
    _started = False

    def __init__(self, level=logging.WARNING):
        super().__init__(level=level)
        GenesisLogHandler._ensure_worker()

    @classmethod
    def _ensure_worker(cls):
        if cls._started:
            return
        cls._started = True
        t = _threading.Thread(target=cls._drain, daemon=True, name="genesis-log-worker")
        t.start()
        cls._worker = t

    @classmethod
    def _drain(cls):
        """Background thread: drain the queue and create genesis keys."""
        while True:
            try:
                item = cls._queue.get(timeout=2)
                if item is None:
                    break  # sentinel for shutdown
                try:
                    from api._genesis_tracker import track
                    track(**item)
                except Exception:
                    pass
                finally:
                    cls._queue.task_done()
            except _queue.Empty:
                continue
            except Exception:
                continue

    def emit(self, record):
        """Non-blocking: just enqueue the payload and return immediately."""
        try:
            msg = self.format(record)
            key_type = "error" if record.levelno >= logging.ERROR else "system"
            payload = dict(
                key_type=key_type,
                what=msg[:2000] if len(msg) > 2000 else msg,
                who=record.name,
                where=f"{record.module}:{record.funcName}:{record.lineno}",
                why=record.levelname,
                how="logging",
                tags=["log", record.levelname.lower(), record.name],
                is_error=(record.levelno >= logging.ERROR),
                error_message=record.getMessage() if record.levelno >= logging.ERROR else "",
            )
            # Non-blocking put -- drop if queue is full (never stall the caller)
            try:
                GenesisLogHandler._queue.put_nowait(payload)
            except _queue.Full:
                pass  # Drop silently -- better to lose a genesis key than block
        except Exception:
            pass  # never break logging



class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production/analysis."""

    def format(self, record):
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging():
    """
    Configure logging:
      - Console: WARNING+ (human-readable)
      - File: INFO+ (human-readable, daily rotation, Windows-safe)
      - Structured: INFO+ (JSON, daily rotation) — for BI/analysis
      - Audit: WARNING+ (separate file for security/governance events)

    NOTE: We use TimedRotatingFileHandler (daily, delay=True) instead of
    RotatingFileHandler because on Windows, os.rename() on an open file
    raises PermissionError: [WinError 32]. Daily rotation avoids this.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    # File handler — INFO+ (not DEBUG — avoids filelock spam filling disk)
    # TimedRotatingFileHandler is Windows-safe: no os.rename() on open files.
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "grace.log",
        when='midnight', interval=1, backupCount=5,
        encoding='utf-8', delay=True
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler — WARNING+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Structured JSON handler — INFO+, Windows-safe daily rotation
    structured_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "grace_structured.jsonl",
        when='midnight', interval=1, backupCount=3,
        encoding='utf-8', delay=True
    )
    structured_handler.setLevel(logging.INFO)
    structured_handler.setFormatter(StructuredFormatter())

    # Audit handler — WARNING+ security/governance events, Windows-safe
    audit_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "grace_audit.log",
        when='midnight', interval=1, backupCount=5,
        encoding='utf-8', delay=True
    )
    audit_handler.setLevel(logging.WARNING)
    audit_handler.setFormatter(logging.Formatter(
        '%(asctime)s [AUDIT] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(structured_handler)
    root_logger.addHandler(audit_handler)

    # Genesis: every log (old/new/existing) gets a Genesis key
    genesis_log_level = os.environ.get("GENESIS_LOG_LEVEL", "WARNING").upper()
    genesis_level = getattr(logging, genesis_log_level, logging.WARNING)
    genesis_handler = GenesisLogHandler(level=genesis_level)
    root_logger.addHandler(genesis_handler)
    print(f"[OK] Genesis log handler: {genesis_log_level}+ -> Genesis keys")

    # Suppress noisy third-party loggers
    for name in [
        "uvicorn.access", "uvicorn.error", "watchfiles", "sqlalchemy",
        "watchdog", "watchdog.observers", "watchdog.observers.inotify_buffer",
        "ingestion", "auto_ingest", "continuous_learning", "genesis", "embedding",
        # Critical: filelock floods grace.log with DEBUG spam at 1000+ lines/minute
        "filelock",
        # Other high-volume background loggers
        "genesis.kb_integration", "asyncio", "httpx", "httpcore",
        "urllib3", "charset_normalizer",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Keep important loggers at INFO
    for name in ["app", "scraping", "auto_search", "cognitive.consensus_engine",
                  "cognitive.immune_system", "cognitive.pipeline"]:
        logging.getLogger(name).setLevel(logging.INFO)

    print(f"[OK] Logging configured: Console(WARN+), File(DEBUG+), Structured(INFO+), Audit(WARN+) -> {log_dir}/")
