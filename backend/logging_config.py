import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production/analysis."""

    def format(self, record):
        log_entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
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
      - File: DEBUG+ (human-readable, rotating 10MB x 5)
      - Structured: INFO+ (JSON, rotating 20MB x 3) — for BI/analysis
      - Audit: WARNING+ (separate file for security/governance events)
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    # File handler — human-readable DEBUG+
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "grace.log",
        maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler — WARNING+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Structured JSON handler — INFO+ for BI/analysis
    structured_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "grace_structured.jsonl",
        maxBytes=20 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    structured_handler.setLevel(logging.INFO)
    structured_handler.setFormatter(StructuredFormatter())

    # Audit handler — WARNING+ security/governance events
    audit_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "grace_audit.log",
        maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
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

    # Suppress noisy third-party loggers
    for name in ["uvicorn.access", "uvicorn.error", "watchfiles", "sqlalchemy",
                  "watchdog", "watchdog.observers", "watchdog.observers.inotify_buffer",
                  "ingestion", "auto_ingest", "continuous_learning", "genesis", "embedding"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Keep important loggers at INFO
    for name in ["app", "scraping", "auto_search", "cognitive.consensus_engine",
                  "cognitive.immune_system", "cognitive.pipeline"]:
        logging.getLogger(name).setLevel(logging.INFO)

    print(f"✅ Logging configured: Console(WARN+), File(DEBUG+), Structured(INFO+), Audit(WARN+) -> {log_dir}/")
