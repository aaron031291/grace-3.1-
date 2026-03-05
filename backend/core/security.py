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
#  PER-USER RATE LIMITER — tracks by user_id, not just IP
# ═══════════════════════════════════════════════════════════════════

_user_limiters: Dict[str, RateLimiter] = {}
_user_limiter_lock = threading.Lock()

USER_RATE_LIMITS = {
    "free": 30,
    "pro": 120,
    "admin": 500,
    "default": 60,
}


def check_user_rate_limit(user_id: str, tier: str = "default") -> dict:
    """
    Per-user rate limiting. Returns dict with allowed, remaining, limit.

    Args:
        user_id: Unique user identifier
        tier: User tier (free, pro, admin, default)
    """
    rpm = USER_RATE_LIMITS.get(tier, USER_RATE_LIMITS["default"])

    with _user_limiter_lock:
        if user_id not in _user_limiters:
            _user_limiters[user_id] = RateLimiter(requests_per_minute=rpm)

    limiter = _user_limiters[user_id]
    allowed = limiter.allow(user_id)
    remaining = limiter.remaining(user_id)

    return {
        "allowed": allowed,
        "remaining": remaining,
        "limit": rpm,
        "tier": tier,
        "user_id": user_id,
    }


# ═══════════════════════════════════════════════════════════════════
#  LLM RESPONSE CACHE — avoids repeated API calls for same queries
# ═══════════════════════════════════════════════════════════════════

class LLMCache:
    """
    In-memory LRU cache for LLM responses with TTL.
    Avoids costly re-calls for identical or near-identical prompts.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: Dict[str, dict] = {}
        self._access_order: list = []
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, prompt: str, model: str = "", temperature: float = 0.7) -> str:
        normalized = prompt.strip().lower()[:2000]
        raw = f"{model}:{temperature}:{normalized}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str = "", temperature: float = 0.7) -> Optional[str]:
        key = self._make_key(prompt, model, temperature)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() - entry["ts"] > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry["response"]

    def put(self, prompt: str, response: str, model: str = "", temperature: float = 0.7):
        key = self._make_key(prompt, model, temperature)
        with self._lock:
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]["ts"])
                del self._cache[oldest_key]
            self._cache[key] = {
                "response": response,
                "ts": time.time(),
                "model": model,
            }

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 3),
            }

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0


_llm_cache: Optional[LLMCache] = None
_cache_lock = threading.Lock()


def get_llm_cache() -> LLMCache:
    global _llm_cache
    if _llm_cache is None:
        with _cache_lock:
            if _llm_cache is None:
                max_size = int(os.getenv("LLM_CACHE_SIZE", "500"))
                ttl = int(os.getenv("LLM_CACHE_TTL", "3600"))
                _llm_cache = LLMCache(max_size=max_size, ttl_seconds=ttl)
    return _llm_cache


# ═══════════════════════════════════════════════════════════════════
#  API COST TRACKER — monitors LLM API spend
# ═══════════════════════════════════════════════════════════════════

class APICostTracker:
    """Tracks estimated API costs per model and per user."""

    COST_PER_1K_TOKENS = {
        "kimi-k2.5": {"input": 0.002, "output": 0.006},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "deepseek-r1:7b": {"input": 0.0, "output": 0.0},
        "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},
        "qwen2.5:7b": {"input": 0.0, "output": 0.0},
        "mistral:7b": {"input": 0.0, "output": 0.0},
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._by_model: Dict[str, dict] = defaultdict(
            lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        )
        self._by_user: Dict[str, dict] = defaultdict(
            lambda: {"calls": 0, "cost_usd": 0.0}
        )
        self._total_cost = 0.0

    def record(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        user_id: str = "system",
    ):
        rates = self.COST_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.003})
        cost = (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])

        with self._lock:
            m = self._by_model[model]
            m["calls"] += 1
            m["input_tokens"] += input_tokens
            m["output_tokens"] += output_tokens
            m["cost_usd"] += cost

            u = self._by_user[user_id]
            u["calls"] += 1
            u["cost_usd"] += cost

            self._total_cost += cost

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "total_cost_usd": round(self._total_cost, 4),
                "by_model": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in self._by_model.items()},
                "by_user": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in self._by_user.items()},
            }


_cost_tracker: Optional[APICostTracker] = None
_cost_lock = threading.Lock()


def get_cost_tracker() -> APICostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        with _cost_lock:
            if _cost_tracker is None:
                _cost_tracker = APICostTracker()
    return _cost_tracker


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
    """Create a timestamped backup — supports both SQLite (file copy) and PostgreSQL (pg_dump)."""
    import shutil
    import subprocess
    from datetime import datetime

    try:
        from settings import settings
        db_type = getattr(settings, "DATABASE_TYPE", "sqlite")
    except Exception:
        db_type = os.getenv("DATABASE_TYPE", "sqlite")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if db_type == "postgresql":
        if not backup_dir:
            backup_dir = str(Path(__file__).parent.parent / "data" / "backups")
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        backup_path = f"{backup_dir}/grace_{timestamp}.sql"

        try:
            from settings import settings as s
            pg_env = {
                **os.environ,
                "PGPASSWORD": s.DATABASE_PASSWORD or "",
            }
            cmd = [
                "pg_dump",
                "-h", s.DATABASE_HOST or "localhost",
                "-p", str(s.DATABASE_PORT or 5432),
                "-U", s.DATABASE_USER or "grace",
                "-d", s.DATABASE_NAME or "grace",
                "-F", "c",
                "-f", backup_path,
            ]
            subprocess.run(cmd, env=pg_env, check=True, timeout=300)
            size_mb = round(Path(backup_path).stat().st_size / 1048576, 2)
            logger.info(f"PostgreSQL backup: {backup_path} ({size_mb} MB)")
        except FileNotFoundError:
            backup_path = f"pg_dump not found — install PostgreSQL client tools"
        except subprocess.CalledProcessError as e:
            backup_path = f"pg_dump failed: {e}"
        except Exception as e:
            backup_path = f"PostgreSQL backup failed: {e}"
    else:
        if not source_path:
            try:
                from settings import settings
                source_path = settings.DATABASE_PATH
            except Exception:
                source_path = "data/grace.db"

        if not backup_dir:
            backup_dir = str(Path(source_path).parent / "backups")

        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        backup_path = f"{backup_dir}/grace_{timestamp}.db"

        source = Path(source_path)
        if not source.exists():
            return f"Source not found: {source_path}"

        shutil.copy2(str(source), backup_path)

        wal = Path(f"{source_path}-wal")
        if wal.exists():
            shutil.copy2(str(wal), f"{backup_path}-wal")

        size_mb = round(Path(backup_path).stat().st_size / 1048576, 2)
        logger.info(f"SQLite backup: {backup_path} ({size_mb} MB)")

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Database backup: {backup_path}",
              who="security.backup_database", tags=["backup", "database"])
    except Exception:
        pass

    return backup_path
