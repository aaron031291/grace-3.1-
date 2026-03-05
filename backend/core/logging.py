"""
Structured JSON Logging with correlation IDs.

Every log entry includes:
  - timestamp (ISO 8601)
  - level
  - message
  - correlation_id (traces a request across brains)
  - brain_domain (which brain handled the request)
  - component (which service module)
  - latency_ms (for request logs)
"""

import logging
import json
import uuid
import threading
import time
from datetime import datetime
from typing import Optional

_correlation = threading.local()


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    return getattr(_correlation, "id", None) or str(uuid.uuid4())[:12]


def set_correlation_id(cid: str = None):
    """Set a correlation ID for the current thread/request."""
    _correlation.id = cid or str(uuid.uuid4())[:12]


class StructuredFormatter(logging.Formatter):
    """JSON log formatter with correlation IDs."""

    def format(self, record):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "cid": get_correlation_id(),
        }

        if hasattr(record, "brain"):
            entry["brain"] = record.brain
        if hasattr(record, "action"):
            entry["action"] = record.action
        if hasattr(record, "latency_ms"):
            entry["latency_ms"] = record.latency_ms
        if hasattr(record, "component"):
            entry["component"] = record.component

        if record.exc_info and record.exc_info[0]:
            entry["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(entry, default=str)


def setup_structured_logging(level: str = "INFO"):
    """Configure structured JSON logging for the entire app."""
    root = logging.getLogger()

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Don't double-add
    for h in root.handlers[:]:
        if isinstance(h.formatter, StructuredFormatter):
            return

    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
