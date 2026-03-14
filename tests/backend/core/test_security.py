"""Tests for backend/core/security.py — RateLimiter, validation, sanitization, SQL injection."""

import importlib
import pathlib
import time

import pytest

# ── direct import of the module under test ──────────────────────────
_spec = importlib.util.spec_from_file_location(
    "security",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "security.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

RateLimiter = _mod.RateLimiter
check_rate_limit = _mod.check_rate_limit
get_rate_limit_status = _mod.get_rate_limit_status
validate_request_size = _mod.validate_request_size
sanitize_string = _mod.sanitize_string
check_sql_injection = _mod.check_sql_injection
MAX_REQUEST_SIZE = _mod.MAX_REQUEST_SIZE
MAX_FIELD_LENGTH = _mod.MAX_FIELD_LENGTH
BRAIN_RATE_LIMITS = _mod.BRAIN_RATE_LIMITS


# ════════════════════════════════════════════════════════════════════
#  RateLimiter
# ════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    """Unit tests for the sliding-window RateLimiter class."""

    def test_allow_under_limit(self):
        limiter = RateLimiter(requests_per_minute=5)
        assert limiter.allow("k1") is True

    def test_allow_false_when_exceeded(self):
        limiter = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            assert limiter.allow("k1") is True
        assert limiter.allow("k1") is False

    def test_remaining_shows_correct_count(self):
        limiter = RateLimiter(requests_per_minute=5)
        assert limiter.remaining("k1") == 5
        limiter.allow("k1")
        assert limiter.remaining("k1") == 4
        limiter.allow("k1")
        assert limiter.remaining("k1") == 3

    def test_expired_hits_cleaned_up(self):
        limiter = RateLimiter(requests_per_minute=2)
        # Manually inject old timestamps (> 60 s ago)
        old = time.time() - 120
        limiter._hits["k1"] = [old, old]
        # Those expired hits should be purged; new request allowed
        assert limiter.allow("k1") is True
        assert limiter.remaining("k1") == 1

    def test_different_keys_independent(self):
        limiter = RateLimiter(requests_per_minute=1)
        assert limiter.allow("a") is True
        assert limiter.allow("a") is False  # "a" exhausted
        assert limiter.allow("b") is True   # "b" still fresh


# ════════════════════════════════════════════════════════════════════
#  Rate-limit helper functions
# ════════════════════════════════════════════════════════════════════

class TestRateLimitFunctions:

    def test_check_rate_limit_fresh_key(self):
        # Use a unique brain name so it won't collide across runs
        assert check_rate_limit("test_fresh_brain_xyz", "127.0.0.1") is True

    def test_get_rate_limit_status_structure(self):
        status = get_rate_limit_status()
        assert "limits" in status
        assert "active_limiters" in status
        assert isinstance(status["limits"], dict)
        assert isinstance(status["active_limiters"], list)

    def test_brain_rate_limits_expected_domains(self):
        expected = {"chat", "ai", "system", "files", "govern", "data", "tasks", "code", "deterministic"}
        assert expected.issubset(set(BRAIN_RATE_LIMITS.keys()))


# ════════════════════════════════════════════════════════════════════
#  Request validation
# ════════════════════════════════════════════════════════════════════

class TestValidateRequestSize:

    def test_small_size_allowed(self):
        assert validate_request_size(1000) is True

    def test_over_max_rejected(self):
        assert validate_request_size(MAX_REQUEST_SIZE + 1) is False

    def test_boundary_exact_max_allowed(self):
        assert validate_request_size(MAX_REQUEST_SIZE) is True


# ════════════════════════════════════════════════════════════════════
#  sanitize_string
# ════════════════════════════════════════════════════════════════════

class TestSanitizeString:

    def test_normal_string_passes_through(self):
        assert sanitize_string("hello world") == "hello world"

    def test_null_bytes_removed(self):
        assert sanitize_string("hel\x00lo") == "hello"

    def test_non_string_converted_and_truncated(self):
        result = sanitize_string(12345, max_length=3)
        assert result == "123"

    def test_truncation_at_max_field_length(self):
        long = "a" * (MAX_FIELD_LENGTH + 100)
        assert len(sanitize_string(long)) == MAX_FIELD_LENGTH

    def test_custom_max_length(self):
        assert sanitize_string("abcdef", max_length=4) == "abcd"


# ════════════════════════════════════════════════════════════════════
#  SQL injection detection
# ════════════════════════════════════════════════════════════════════

class TestCheckSqlInjection:

    def test_normal_text_safe(self):
        assert check_sql_injection("normal text") is False

    def test_or_one_equals_one(self):
        assert check_sql_injection("' or '1'='1") is True

    def test_drop_table(self):
        assert check_sql_injection("'; drop table users") is True

    def test_union_select(self):
        assert check_sql_injection("union select * from") is True

    def test_script_tag(self):
        assert check_sql_injection("<script>alert(1)</script>") is True

    def test_xp_cmdshell(self):
        assert check_sql_injection("xp_cmdshell") is True

    def test_non_string_returns_false(self):
        assert check_sql_injection(12345) is False

    def test_case_insensitive(self):
        assert check_sql_injection("UNION SELECT") is True
