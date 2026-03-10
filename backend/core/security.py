"""
Enterprise Security Module — secrets management, rate limiting,
request validation, SQL injection prevention.
"""

import os
import json
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache
from collections import defaultdict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  SECRETS MANAGER — encrypted local vault, env fallback
# ═══════════════════════════════════════════════════════════════════

VAULT_PATH = Path(__file__).parent.parent / "data" / ".vault.enc"
_vault_cache: Optional[dict] = None


def _get_cipher():
    """Get Fernet cipher from GRACE_MASTER_KEY env var."""
    key = os.environ.get("GRACE_MASTER_KEY")
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except ImportError:
        logger.debug("cryptography not installed — vault disabled")
        return None
    except Exception:
        return None


def get_secret(name: str, default: str = "") -> str:
    """
    Get a secret value. Priority:
      1. Encrypted vault (GRACE_MASTER_KEY + .vault.enc)
      2. Environment variable
      3. .env file value
      4. Default
    """
    global _vault_cache

    # 1. Try vault
    if _vault_cache is None:
        cipher = _get_cipher()
        if cipher and VAULT_PATH.exists():
            try:
                encrypted = VAULT_PATH.read_bytes()
                decrypted = cipher.decrypt(encrypted)
                _vault_cache = json.loads(decrypted)
                logger.info("Secrets vault loaded")
            except Exception as e:
                logger.debug(f"Vault load failed: {e}")
                _vault_cache = {}
        else:
            _vault_cache = {}

    if name in _vault_cache:
        return _vault_cache[name]

    # 2. Try env
    env_val = os.environ.get(name, "")
    if env_val:
        return env_val

    # 3. Try settings
    try:
        from settings import settings
        return getattr(settings, name, default)
    except Exception:
        return default


def create_vault(secrets: dict):
    """Create/overwrite the encrypted vault."""
    cipher = _get_cipher()
    if not cipher:
        raise RuntimeError("Set GRACE_MASTER_KEY env var first")
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encrypted = cipher.encrypt(json.dumps(secrets).encode())
    VAULT_PATH.write_bytes(encrypted)
    global _vault_cache
    _vault_cache = dict(secrets)
    logger.info(f"Vault created with {len(secrets)} secrets")


# ═══════════════════════════════════════════════════════════════════
#  RATE LIMITER — per-brain, per-IP, sliding window
# ═══════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Sliding window rate limiter.
    Usage:
        limiter = RateLimiter(requests_per_minute=100)
        if not limiter.allow("brain:chat:192.168.1.1"):
            return 429
    """

    def __init__(self, requests_per_minute: int = 100):
        self.rpm = requests_per_minute
        self.window = 60.0
        self._hits: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            hits = self._hits[key]
            # Remove expired
            self._hits[key] = [t for t in hits if t > cutoff]
            if len(self._hits[key]) >= self.rpm:
                return False
            self._hits[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if t > cutoff]
            return max(0, self.rpm - len(hits))


# Global rate limiters per brain domain
_brain_limiters: Dict[str, RateLimiter] = {}
_limiter_lock = threading.Lock()

BRAIN_RATE_LIMITS = {
    "chat": 60,
    "ai": 30,
    "system": 100,
    "files": 100,
    "govern": 50,
    "data": 50,
    "tasks": 100,
    "code": 30,
    "deterministic": 20,  # scan/fix are heavier; conservative limit
}


def check_rate_limit(brain: str, client_ip: str = "unknown") -> bool:
    """Check if a brain request is within rate limits. Returns True if allowed."""
    with _limiter_lock:
        if brain not in _brain_limiters:
            rpm = BRAIN_RATE_LIMITS.get(brain, 100)
            _brain_limiters[brain] = RateLimiter(requests_per_minute=rpm)

    key = f"{brain}:{client_ip}"
    return _brain_limiters[brain].allow(key)


def get_rate_limit_status() -> dict:
    """Get current rate limit configuration."""
    return {
        "limits": BRAIN_RATE_LIMITS,
        "active_limiters": list(_brain_limiters.keys()),
    }


# ═══════════════════════════════════════════════════════════════════
#  REQUEST VALIDATION — size caps, input sanitization
# ═══════════════════════════════════════════════════════════════════

MAX_REQUEST_SIZE = 16 * 1024 * 1024  # 16 MB
MAX_FIELD_LENGTH = 50000  # 50K chars per field


def validate_request_size(content_length: int) -> bool:
    return content_length <= MAX_REQUEST_SIZE


def sanitize_string(value: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    """Remove dangerous characters, truncate."""
    if not isinstance(value, str):
        return str(value)[:max_length]
    value = value[:max_length]
    # Remove null bytes
    value = value.replace("\x00", "")
    return value


def check_sql_injection(value: str) -> bool:
    """Returns True if value looks like SQL injection attempt."""
    if not isinstance(value, str):
        return False
    lower = value.lower()
    patterns = [
        "'; drop", "'; delete", "'; update", "'; insert",
        "' or '1'='1", "' or 1=1", "union select",
        "exec(", "execute(", "xp_cmdshell",
        "<script>", "javascript:", "onerror=",
    ]
    return any(p in lower for p in patterns)


def safe_sql_text(sql: str, params: dict):
    """Wrap raw SQL text() with injection checks."""
    from sqlalchemy import text
    if "--" in sql and ";" in sql:
        raise ValueError("Potential SQL injection detected")
    for key, val in params.items():
        if isinstance(val, str) and check_sql_injection(val):
            raise ValueError(f"SQL injection attempt in parameter '{key}'")
    return text(sql).bindparams(**params)


# ═══════════════════════════════════════════════════════════════════
#  DATABASE BACKUP
# ═══════════════════════════════════════════════════════════════════

def backup_database(source_path: str = None, backup_dir: str = None) -> str:
    """Create a timestamped backup of the SQLite database."""
    import shutil
    from datetime import datetime, timezone

    if not source_path:
        try:
            from settings import settings
            source_path = settings.DATABASE_PATH
        except Exception:
            source_path = "data/grace.db"

    if not backup_dir:
        backup_dir = str(Path(source_path).parent / "backups")

    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/grace_{timestamp}.db"

    source = Path(source_path)
    if not source.exists():
        return f"Source not found: {source_path}"

    shutil.copy2(str(source), backup_path)

    # Also backup WAL if present
    wal = Path(f"{source_path}-wal")
    if wal.exists():
        shutil.copy2(str(wal), f"{backup_path}-wal")

    size_mb = round(Path(backup_path).stat().st_size / 1048576, 2)
    logger.info(f"Database backup: {backup_path} ({size_mb} MB)")

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Database backup: {backup_path} ({size_mb}MB)",
              who="security.backup_database", tags=["backup", "database"])
    except Exception:
        pass

    return backup_path
