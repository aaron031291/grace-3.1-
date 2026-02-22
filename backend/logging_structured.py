"""
Structured Logging for Grace OS

JSON-formatted log output for production monitoring.
Every log entry is machine-parseable with consistent fields.

Fields on every log entry:
  timestamp, level, component, message, request_id, duration_ms

Can be piped to: ELK, Datadog, CloudWatch, Grafana Loki, or any
JSON log aggregator.

Usage:
    from logging_structured import setup_structured_logging
    setup_structured_logging()  # Call once at startup
"""

import logging
import json
import time
import uuid
import os
from datetime import datetime, timezone
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Format logs as JSON for machine parsing."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "file": f"{record.pathname}:{record.lineno}",
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable format for development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        component = record.name.split(".")[-1][:20]
        return f"{ts} {color}{record.levelname:7s}{self.RESET} [{component:20s}] {record.getMessage()}"


def setup_structured_logging(json_mode: Optional[bool] = None):
    """
    Configure structured logging for the entire application.

    Args:
        json_mode: Force JSON (True) or human (False) format.
                   Auto-detects from PRODUCTION_MODE env var if None.
    """
    if json_mode is None:
        json_mode = os.getenv("PRODUCTION_MODE", "false").lower() == "true"

    root = logging.getLogger()

    # Remove existing handlers
    root.handlers.clear()

    # Create handler
    handler = logging.StreamHandler()

    if json_mode:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    root.addHandler(handler)

    # Set level from env
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Quiet noisy libraries
    for lib in ["urllib3", "httpx", "httpcore", "qdrant_client", "sqlalchemy.engine"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Structured logging configured (mode={'json' if json_mode else 'human'}, level={level})"
    )
