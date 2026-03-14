"""Tests for backend/core/datetime_utils.py"""
import importlib
import pathlib
from datetime import datetime, timezone, timedelta

import pytest

_spec = importlib.util.spec_from_file_location(
    "datetime_utils",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "datetime_utils.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ensure_aware = _mod.ensure_aware
as_naive_utc = _mod.as_naive_utc


NAIVE_DT = datetime(2025, 6, 15, 12, 0, 0)
AWARE_UTC_DT = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
PLUS5 = timezone(timedelta(hours=5))
AWARE_NON_UTC_DT = datetime(2025, 6, 15, 12, 0, 0, tzinfo=PLUS5)


# ── ensure_aware ─────────────────────────────────────────────

class TestEnsureAware:
    def test_none_returns_none(self):
        assert ensure_aware(None) is None

    def test_naive_gets_utc(self):
        result = ensure_aware(NAIVE_DT)
        assert result.tzinfo is timezone.utc
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 12

    def test_aware_utc_unchanged(self):
        result = ensure_aware(AWARE_UTC_DT)
        assert result == AWARE_UTC_DT
        assert result.tzinfo is timezone.utc

    def test_aware_non_utc_converted(self):
        result = ensure_aware(AWARE_NON_UTC_DT)
        assert result.tzinfo is timezone.utc
        # 12:00 +05:00 → 07:00 UTC
        assert result.hour == 7
        assert result.minute == 0


# ── as_naive_utc ─────────────────────────────────────────────

class TestAsNaiveUtc:
    def test_none_returns_none(self):
        assert as_naive_utc(None) is None

    def test_naive_unchanged(self):
        result = as_naive_utc(NAIVE_DT)
        assert result == NAIVE_DT
        assert result.tzinfo is None

    def test_aware_utc_stripped(self):
        result = as_naive_utc(AWARE_UTC_DT)
        assert result.tzinfo is None
        assert result.hour == 12

    def test_aware_non_utc_converted_and_stripped(self):
        result = as_naive_utc(AWARE_NON_UTC_DT)
        assert result.tzinfo is None
        # 12:00 +05:00 → 07:00 UTC, then stripped
        assert result.hour == 7
        assert result.minute == 0
