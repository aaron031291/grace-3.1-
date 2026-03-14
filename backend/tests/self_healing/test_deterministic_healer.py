"""Tests for the Deterministic Healer — 5 pattern-based auto-fixers."""
import os
import sys
import pytest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")

from self_healing.deterministic_healer import DeterministicHealer, HealResult


# ── Fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def healer():
    return DeterministicHealer()


# ── HealResult dataclass ─────────────────────────────────────────────────

class TestHealResult:
    def test_healed_true(self):
        r = HealResult(True, "fixed something", patch_applied=True, healer="tz")
        assert r.healed is True
        assert r.description == "fixed something"
        assert r.patch_applied is True
        assert r.healer == "tz"

    def test_healed_false_defaults(self):
        r = HealResult(False, "nope")
        assert r.healed is False
        assert r.patch_applied is False
        assert r.healer == ""

    def test_repr_success(self):
        r = HealResult(True, "ok", healer="tz")
        assert "✅" in repr(r)
        assert "tz" in repr(r)

    def test_repr_failure(self):
        r = HealResult(False, "fail", healer="ng")
        assert "❌" in repr(r)


# ── 1. Timezone healer ───────────────────────────────────────────────────

class TestTimezoneHealer:
    def test_positive_naive_datetime(self, healer, tmp_path):
        """Timezone healer detects naive datetime.now() in a temp file."""
        src = tmp_path / "tz_bug.py"
        src.write_text(
            "from datetime import datetime\n"
            "now = datetime.now()\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "can't subtract offset-naive and offset-aware datetimes",
            "exc_type": "TypeError",
            "location": "tz_bug",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "timezone"
        patched = src.read_text(encoding="utf-8")
        assert "timezone.utc" in patched

    def test_positive_utcnow(self, healer, tmp_path):
        """Timezone healer replaces datetime.utcnow() too."""
        src = tmp_path / "tz_utc.py"
        src.write_text(
            "import datetime\n"
            "now = datetime.utcnow()\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "offset-naive and offset-aware datetimes",
            "exc_type": "TypeError",
            "location": "tz_utc",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "timezone"

    def test_negative_unrelated_error(self, healer):
        """Unrelated error string should not match timezone healer."""
        payload = {
            "exc_str": "division by zero",
            "exc_type": "ZeroDivisionError",
            "location": "math_utils.divide",
            "tb": "",
            "context": {},
        }
        result = healer._heal_timezone(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "timezone"


# ── 2. NullGuard healer ──────────────────────────────────────────────────

class TestNullGuardHealer:
    def test_positive_nonetype_attribute(self, healer, tmp_path):
        """NullGuard detects NoneType attribute access and inserts guard."""
        src = tmp_path / "null_bug.py"
        src.write_text(
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "def process(data):\n"
            "    result = data.value\n"
            "    return result\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "'NoneType' object has no attribute 'value'",
            "exc_type": "AttributeError",
            "location": "null_bug.process",
            "tb": "    result = data.value\n",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "null_guard"
        patched = src.read_text(encoding="utf-8")
        assert "is None" in patched

    def test_negative_key_error(self, healer):
        """KeyError without NoneType should not match null_guard."""
        payload = {
            "exc_str": "KeyError: 'missing_key'",
            "exc_type": "KeyError",
            "location": "some_module.func",
            "tb": "",
            "context": {},
        }
        result = healer._heal_null_guard(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "null_guard"


# ── 3. Import probe healer ───────────────────────────────────────────────

class TestImportProbeHealer:
    def test_positive_cannot_import(self, healer):
        """Import probe detects 'cannot import name' errors."""
        payload = {
            "exc_str": "cannot import name 'NonExistentWidget' from 'os.path'",
            "exc_type": "ImportError",
            "location": "my_module",
            "tb": "",
            "context": {},
        }
        result = healer._heal_import_probe(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        # Should attempt to resolve — either found or not, but it matches
        assert result.healer == "import_probe"
        # It won't be healed (NonExistentWidget doesn't exist), but it tried
        # The key check is that it didn't return "Not an import error"
        assert "Not an import error" not in result.description

    def test_positive_no_module_named(self, healer):
        """Import probe detects 'No module named' errors."""
        payload = {
            "exc_str": "No module named 'fake_nonexistent_module_xyz'",
            "exc_type": "ModuleNotFoundError",
            "location": "my_module",
            "tb": "",
            "context": {},
        }
        result = healer._heal_import_probe(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healer == "import_probe"
        assert "Not an import error" not in result.description

    def test_negative_unrelated_error(self, healer):
        """ValueError should not match import probe."""
        payload = {
            "exc_str": "invalid literal for int() with base 10: 'abc'",
            "exc_type": "ValueError",
            "location": "parser.parse",
            "tb": "",
            "context": {},
        }
        result = healer._heal_import_probe(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "import_probe"
        assert "Not an import error" in result.description


# ── 4. Typo detector healer ──────────────────────────────────────────────

class TestTypoDetectorHealer:
    def test_positive_name_error_close_match(self, healer, tmp_path):
        """Typo detector finds close match for misspelled function name."""
        src = tmp_path / "typo_bug.py"
        src.write_text(
            "def calculate_total(items):\n"
            "    return sum(items)\n"
            "\n"
            "result = calculate_totl([1, 2, 3])\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "name 'calculate_totl' is not defined",
            "exc_type": "NameError",
            "location": "typo_bug",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "typo_detector"
        patched = src.read_text(encoding="utf-8")
        assert "calculate_total" in patched
        assert "calculate_totl" not in patched

    def test_positive_attribute_error_close_match(self, healer, tmp_path):
        """Typo detector finds close match for misspelled attribute."""
        src = tmp_path / "attr_typo.py"
        src.write_text(
            "class MyClass:\n"
            "    def initialize(self):\n"
            "        pass\n"
            "\n"
            "obj = MyClass()\n"
            "obj.initialze()\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "has no attribute 'initialze'",
            "exc_type": "AttributeError",
            "location": "attr_typo",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "typo_detector"

    def test_negative_no_close_match(self, healer, tmp_path):
        """No close match should return healed=False."""
        src = tmp_path / "no_match.py"
        src.write_text(
            "def alpha():\n"
            "    pass\n"
            "\n"
            "def beta():\n"
            "    pass\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "name 'xyzzy_nonexistent_func' is not defined",
            "exc_type": "NameError",
            "location": "no_match",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer._heal_typo_detector(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "typo_detector"

    def test_negative_not_name_or_attr_error(self, healer):
        """TypeError should not match typo_detector."""
        payload = {
            "exc_str": "unsupported operand type(s)",
            "exc_type": "TypeError",
            "location": "math.add",
            "tb": "",
            "context": {},
        }
        result = healer._heal_typo_detector(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "typo_detector"


# ── 5. Env var filler healer ─────────────────────────────────────────────

class TestEnvVarFillerHealer:
    def test_positive_missing_env_var_with_dotenv(self, healer, tmp_path, monkeypatch):
        """Env var filler adds missing var to .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR=hello\n", encoding="utf-8")

        # Monkeypatch _BACKEND_ROOT so .env is found in tmp_path
        import self_healing.deterministic_healer as dh_mod
        monkeypatch.setattr(dh_mod, "_BACKEND_ROOT", tmp_path)

        # Make sure the var is not in the environment
        monkeypatch.delenv("MY_TEST_VAR", raising=False)

        payload = {
            "exc_str": "KeyError: 'MY_TEST_VAR'",
            "exc_type": "KeyError",
            "location": "config.loader",
            "tb": "",
            "context": {},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "env_var_filler"
        assert result.patch_applied is True

        content = env_file.read_text(encoding="utf-8")
        assert "MY_TEST_VAR=PLACEHOLDER" in content

    def test_positive_var_already_set(self, healer, monkeypatch):
        """If the var is already set in os.environ, report success."""
        monkeypatch.setenv("ALREADY_SET_VAR", "somevalue")

        payload = {
            "exc_str": "KeyError: 'ALREADY_SET_VAR'",
            "exc_type": "KeyError",
            "location": "config.loader",
            "tb": "",
            "context": {},
        }
        result = healer._heal_env_var_filler(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is True
        assert result.healer == "env_var_filler"
        assert "already set" in result.description

    def test_negative_unrelated_error(self, healer):
        """Unrelated error should not match env_var_filler."""
        payload = {
            "exc_str": "IndexError: list index out of range",
            "exc_type": "IndexError",
            "location": "data.processor",
            "tb": "",
            "context": {},
        }
        result = healer._heal_env_var_filler(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert result.healer == "env_var_filler"

    def test_negative_var_in_env_file_but_not_loaded(self, healer, tmp_path, monkeypatch):
        """If var exists in .env but isn't loaded, report unhealed with hint."""
        import self_healing.deterministic_healer as dh_mod
        monkeypatch.setattr(dh_mod, "_BACKEND_ROOT", tmp_path)
        monkeypatch.delenv("MY_UNLOADED_VAR", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("MY_UNLOADED_VAR=secret\n", encoding="utf-8")

        payload = {
            "exc_str": "KeyError: 'MY_UNLOADED_VAR'",
            "exc_type": "KeyError",
            "location": "config.loader",
            "tb": "",
            "context": {},
        }
        result = healer._heal_env_var_filler(
            payload["exc_str"], payload["exc_type"],
            payload["location"], payload["tb"], payload,
        )
        assert result.healed is False
        assert "not loaded" in result.description


# ── Integration: try_heal routes correctly ────────────────────────────────

class TestTryHealRouting:
    def test_no_match_returns_none_healer(self, healer):
        """When nothing matches, healer should be 'none'."""
        payload = {
            "exc_str": "something completely unknown",
            "exc_type": "RuntimeError",
            "location": "unknown",
            "tb": "",
            "context": {},
        }
        result = healer.try_heal(payload)
        assert result.healed is False
        assert result.healer == "none"

    def test_first_matching_healer_wins(self, healer, tmp_path):
        """Timezone healer should fire before typo_detector."""
        src = tmp_path / "multi.py"
        src.write_text(
            "from datetime import datetime\n"
            "now = datetime.now()\n",
            encoding="utf-8",
        )
        payload = {
            "exc_str": "can't subtract offset-naive and offset-aware datetimes",
            "exc_type": "TypeError",
            "location": "multi",
            "tb": "",
            "context": {"target_file": str(src)},
        }
        result = healer.try_heal(payload)
        assert result.healed is True
        assert result.healer == "timezone"
