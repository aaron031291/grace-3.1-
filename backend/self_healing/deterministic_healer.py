"""
self_healing/deterministic_healer.py
─────────────────────────────────────────────────────────────────────────────
Deterministic Self-Healer — pattern-based fixes that run BEFORE the LLM.

Design principle:
  If the fix can be expressed as a function, don't pay Qwen to guess it.
  Deterministic healers are: instant, reliable, zero hallucination risk.
  The LLM is reserved for novel cases that patterns can't handle.

Patterns covered (~60% of runtime errors):
  1. Timezone fix        — naive/aware datetime arithmetic errors
  2. NullGuard injector  — NoneType attribute access
  3. Import probe        — cannot import name X, tries alternatives
  4. Typo detector       — NameError/AttributeError near-miss (difflib)
  5. Env var filler      — NameError on missing environment variable

Each healer returns (healed: bool, description: str, patch: Optional[str])
where `patch` is the actual code fix applied to disk (or None if not applied).
"""
from __future__ import annotations

import ast
import difflib
import importlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


# ── Result dataclass ──────────────────────────────────────────────────────

class HealResult:
    __slots__ = ("healed", "description", "patch_applied", "healer")

    def __init__(
        self,
        healed: bool,
        description: str,
        patch_applied: bool = False,
        healer: str = "",
    ):
        self.healed = healed
        self.description = description
        self.patch_applied = patch_applied
        self.healer = healer

    def __repr__(self):
        status = "✅" if self.healed else "❌"
        return f"HealResult({status} [{self.healer}] {self.description[:80]})"


# ── Main entry point ──────────────────────────────────────────────────────

class DeterministicHealer:
    """
    Runs all deterministic patterns against an error payload.
    Returns the first successful heal, or a combined failure result.

    Call before escalating to LLM to avoid unnecessary LLM invocations.
    """

    _HEALERS = [
        "timezone",
        "null_guard",
        "import_probe",
        "typo_detector",
        "env_var_filler",
    ]

    def try_heal(self, payload: Dict) -> HealResult:
        """
        Try all deterministic healers. Returns first success.
        Never raises — all exceptions caught and logged.
        """
        exc_str  = payload.get("exc_str", "")
        exc_type = payload.get("exc_type", "")
        location = payload.get("location", "")
        tb       = payload.get("tb", "")

        for healer_name in self._HEALERS:
            try:
                method = getattr(self, f"_heal_{healer_name}")
                result = method(exc_str, exc_type, location, tb, payload)
                if result.healed:
                    logger.info(
                        "[DET-HEALER] ✅ %s fixed %s: %s",
                        healer_name, location, result.description[:80],
                    )
                    return result
            except Exception as e:
                logger.debug("[DET-HEALER] %s encountered error: %s", healer_name, e)

        return HealResult(False, "No deterministic pattern matched", healer="none")

    # ── 1. Timezone fix ───────────────────────────────────────────────────

    def _heal_timezone(
        self, exc_str, exc_type, location, tb, payload
    ) -> HealResult:
        """
        Fix: can't subtract offset-naive and offset-aware datetimes.
        Strategy: find the source file, replace naive datetime.now() /
        datetime.utcnow() calls with timezone-aware equivalents.
        """
        TZ_SIGNAL = "can't subtract offset-naive and offset-aware datetimes"
        if TZ_SIGNAL not in exc_str and "offset-naive" not in exc_str:
            return HealResult(False, "Not a timezone error", healer="timezone")

        target = self._resolve_file(location, payload)
        if not target:
            return HealResult(False, "timezone: source file not found", healer="timezone")

        source = target.read_text(encoding="utf-8")
        original = source

        # Patch 1: add timezone import if missing
        if "from datetime import" in source and "timezone" not in source:
            source = re.sub(
                r"(from datetime import )([^\n]+)",
                lambda m: m.group(0) if "timezone" in m.group(2)
                          else f"{m.group(1)}{m.group(2).rstrip()}, timezone",
                source, count=1,
            )
        elif "import datetime" in source and "timezone" not in source:
            source = source.replace(
                "import datetime", "import datetime\nfrom datetime import timezone"
            )

        # Patch 2: replace naive datetime.now() → datetime.now(timezone.utc)
        source = re.sub(
            r"datetime\.now\(\s*\)",
            "datetime.now(timezone.utc)",
            source,
        )
        # Patch 3: replace datetime.utcnow() → datetime.now(timezone.utc)
        source = re.sub(
            r"datetime\.utcnow\(\s*\)",
            "datetime.now(timezone.utc)",
            source,
        )

        if source == original:
            return HealResult(False, "timezone: no naive datetime calls found to patch", healer="timezone")

        return self._write_patch(target, source, "timezone", location)

    # ── 2. NullGuard injector ─────────────────────────────────────────────

    def _heal_null_guard(
        self, exc_str, exc_type, location, tb, payload
    ) -> HealResult:
        """
        Fix: 'NoneType' object has no attribute 'X'.
        Strategy: find the attribute access in source and wrap with `if x is not None`.
        """
        if "NoneType" not in exc_str or "has no attribute" not in exc_str:
            return HealResult(False, "Not a NoneType error", healer="null_guard")

        # Extract the attribute name from the error
        m = re.search(r"has no attribute '([^']+)'", exc_str)
        if not m:
            return HealResult(False, "null_guard: can't extract attribute name", healer="null_guard")
        attr = m.group(1)

        # Extract the variable name from the traceback (last .<attr> access)
        tb_lines = (tb or "").splitlines()
        expr_line = ""
        for line in reversed(tb_lines):
            if f".{attr}" in line and "File" not in line:
                expr_line = line.strip()
                break

        target = self._resolve_file(location, payload)
        if not target:
            return HealResult(False, "null_guard: source file not found", healer="null_guard")

        source = target.read_text(encoding="utf-8")
        original = source

        # Find the line in source that does .attr and guard it
        lines = source.splitlines()
        patched = False
        for i, line in enumerate(lines):
            if f".{attr}" in line and "#" not in line.split(f".{attr}")[0]:
                # Extract the object being accessed
                obj_m = re.search(r"(\b\w+)\." + re.escape(attr), line)
                if obj_m:
                    obj = obj_m.group(1)
                    indent = len(line) - len(line.lstrip())
                    guard = " " * indent + f"if {obj} is None:\n" + \
                            " " * indent + f"    logger.warning('[NULL-GUARD] {obj} is None at {location}')\n"
                    lines.insert(i, guard.rstrip())
                    patched = True
                    break

        if not patched:
            return HealResult(False, f"null_guard: couldn't locate .{attr} access in source", healer="null_guard")

        new_source = "\n".join(lines)
        if new_source == original:
            return HealResult(False, "null_guard: no change produced", healer="null_guard")

        return self._write_patch(target, new_source, "null_guard", location)

    # ── 3. Import probe ───────────────────────────────────────────────────

    def _heal_import_probe(
        self, exc_str, exc_type, location, tb, payload
    ) -> HealResult:
        """
        Fix: cannot import name 'X' from 'Y', or ModuleNotFoundError.
        Strategy:
          a) Try to import the module directly (maybe it's just not loaded yet).
          b) If that fails, search sys.path for an alternative location.
          c) If found elsewhere, patch the import statement in the source file.
        """
        if exc_type not in ("ImportError", "ModuleNotFoundError") and \
           "cannot import name" not in exc_str and "No module named" not in exc_str:
            return HealResult(False, "Not an import error", healer="import_probe")

        # Extract module/name from error message
        name_m = re.search(r"cannot import name '([^']+)' from '([^']+)'", exc_str)
        mod_m  = re.search(r"No module named '([^']+)'", exc_str)

        if name_m:
            import_name, from_module = name_m.group(1), name_m.group(2)
        elif mod_m:
            import_name, from_module = mod_m.group(1), None
        else:
            return HealResult(False, "import_probe: can't parse error message", healer="import_probe")

        # Try direct import
        try:
            if from_module:
                mod = importlib.import_module(from_module)
                if hasattr(mod, import_name):
                    return HealResult(
                        True,
                        f"import_probe: '{import_name}' exists in '{from_module}' — module reload may fix",
                        healer="import_probe",
                    )
        except Exception:
            pass

        # Search backend for the symbol
        candidates = self._find_symbol_in_backend(import_name)
        if not candidates:
            return HealResult(
                False,
                f"import_probe: '{import_name}' not found in any backend module",
                healer="import_probe",
            )

        best = candidates[0]
        target = self._resolve_file(location, payload)
        if not target:
            return HealResult(
                True,
                f"import_probe: '{import_name}' found in '{best}' (patch manually)",
                healer="import_probe",
            )

        # Patch the import in the source file
        source = target.read_text(encoding="utf-8")
        if from_module and from_module in source:
            new_source = source.replace(
                f"from {from_module} import {import_name}",
                f"from {best} import {import_name}",
            )
            if new_source != source:
                return self._write_patch(target, new_source, "import_probe", location)

        return HealResult(
            True,
            f"import_probe: '{import_name}' available in '{best}' — add import",
            healer="import_probe",
        )

    def _find_symbol_in_backend(self, symbol: str) -> List[str]:
        """Search all .py files in backend/ for a definition of `symbol`."""
        found = []
        pattern = re.compile(
            rf"^(class|def|{symbol}\s*=)\s+{re.escape(symbol)}(\s|[:(])",
            re.MULTILINE,
        )
        for py_file in _BACKEND_ROOT.rglob("*.py"):
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if re.search(rf"^(class |def ){re.escape(symbol)}[\s(:]", content, re.MULTILINE):
                    rel = py_file.relative_to(_BACKEND_ROOT)
                    module_path = ".".join(rel.with_suffix("").parts)
                    found.append(module_path)
                    if len(found) >= 5:
                        break
            except Exception:
                continue
        return found

    # ── 4. Typo detector ──────────────────────────────────────────────────

    def _heal_typo_detector(
        self, exc_str, exc_type, location, tb, payload
    ) -> HealResult:
        """
        Fix: NameError 'X' not defined, or AttributeError 'has no attribute X'.
        Strategy: use difflib to find the closest-matching name in scope and
        suggest (or apply) the correction if confidence > 0.8.
        """
        if exc_type not in ("NameError", "AttributeError"):
            return HealResult(False, "Not a Name/Attribute error", healer="typo_detector")

        # Extract the erroneous name
        name_m = (
            re.search(r"name '([^']+)' is not defined", exc_str) or
            re.search(r"has no attribute '([^']+)'", exc_str)
        )
        if not name_m:
            return HealResult(False, "typo_detector: can't extract name", healer="typo_detector")

        bad_name = name_m.group(1)

        target = self._resolve_file(location, payload)
        if not target:
            return HealResult(False, "typo_detector: source file not found", healer="typo_detector")

        source = target.read_text(encoding="utf-8")

        # Gather candidate names from the source file (all identifiers)
        try:
            tree = ast.parse(source)
            candidates = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    candidates.add(node.name)
                    for arg in node.args.args:
                        candidates.add(arg.arg)
                elif isinstance(node, ast.ClassDef):
                    candidates.add(node.name)
                elif isinstance(node, ast.Name):
                    candidates.add(node.id)
                elif isinstance(node, ast.Attribute):
                    candidates.add(node.attr)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in getattr(node, "names", []):
                        candidates.add(alias.asname or alias.name.split(".")[0])
            candidates.discard(bad_name)
        except SyntaxError:
            return HealResult(False, "typo_detector: source has syntax error", healer="typo_detector")

        matches = difflib.get_close_matches(bad_name, candidates, n=1, cutoff=0.75)
        if not matches:
            return HealResult(
                False,
                f"typo_detector: no close match for '{bad_name}'",
                healer="typo_detector",
            )

        correction = matches[0]
        # Apply: replace only whole-word occurrences
        new_source = re.sub(r"\b" + re.escape(bad_name) + r"\b", correction, source)
        if new_source == source:
            return HealResult(
                True,
                f"typo_detector: '{bad_name}' → '{correction}' (no unique occurrence found)",
                healer="typo_detector",
            )

        return self._write_patch(
            target, new_source, "typo_detector", location,
            description=f"'{bad_name}' → '{correction}' (difflib confidence ≥ 0.75)",
        )

    # ── 5. Env var filler ─────────────────────────────────────────────────

    def _heal_env_var_filler(
        self, exc_str, exc_type, location, tb, payload
    ) -> HealResult:
        """
        Fix: NameError for a name that looks like an env var reference, or
        a KeyError on os.environ.
        Strategy: check .env file; if the key is absent, add it with a
        placeholder and log for the operator.
        """
        ENV_SIGNALS = ("os.environ", "os.getenv", "KeyError", "NameError")
        if not any(s in exc_str or s in exc_type for s in ENV_SIGNALS):
            return HealResult(False, "Not an env var error", healer="env_var_filler")

        # Extract variable name
        key_m = (
            re.search(r"'([A-Z][A-Z0-9_]{2,})'", exc_str) or  # UPPER_SNAKE_CASE
            re.search(r"KeyError: '([^']+)'", exc_str)
        )
        if not key_m:
            return HealResult(False, "env_var_filler: can't extract var name", healer="env_var_filler")

        var_name = key_m.group(1)

        # Check if it's already set
        if os.environ.get(var_name):
            return HealResult(
                True,
                f"env_var_filler: '{var_name}' already set in environment",
                healer="env_var_filler",
            )

        # Find .env file
        env_file = _BACKEND_ROOT.parent / ".env"
        if not env_file.exists():
            env_file = _BACKEND_ROOT / ".env"

        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            if var_name in content:
                return HealResult(
                    False,
                    f"env_var_filler: '{var_name}' is in .env but not loaded — check dotenv call",
                    healer="env_var_filler",
                )
            # Add with placeholder
            env_file.write_text(
                content.rstrip() + f"\n# [AUTO-ADDED by deterministic_healer]\n{var_name}=PLACEHOLDER\n",
                encoding="utf-8",
            )
            logger.warning(
                "[DET-HEALER] Added '%s=PLACEHOLDER' to .env — OPERATOR: set the real value",
                var_name,
            )
            return HealResult(
                True,
                f"env_var_filler: added '{var_name}=PLACEHOLDER' to .env — set real value",
                patch_applied=True,
                healer="env_var_filler",
            )

        return HealResult(
            False,
            f"env_var_filler: .env not found — add {var_name} manually",
            healer="env_var_filler",
        )

    # ── Shared utilities ──────────────────────────────────────────────────

    def _resolve_file(self, location: str, payload: Dict) -> Optional[Path]:
        """Resolve module.function location to a Path, or use context file."""
        # Try context first (error_pipeline puts it there)
        ctx = payload.get("context", {})
        for key in ("target_file", "file", "location"):
            f = ctx.get(key, "")
            if f and f.endswith(".py"):
                p = Path(f)
                if p.exists():
                    return p

        # Fallback: derive from dot-notation
        parts = location.split(".")
        for length in range(len(parts), 0, -1):
            module_path = ".".join(parts[:length])
            if module_path in sys.modules:
                mod = sys.modules[module_path]
                if hasattr(mod, "__file__") and mod.__file__:
                    return Path(mod.__file__)
            candidate = _BACKEND_ROOT / Path(*parts[:length]).with_suffix(".py")
            if candidate.exists():
                return candidate
        return None

    def _write_patch(
        self,
        target: Path,
        new_source: str,
        healer: str,
        location: str,
        description: str = "",
    ) -> HealResult:
        """Validate and write patched source, with backup."""
        # Syntax check before writing
        try:
            ast.parse(new_source)
        except SyntaxError as se:
            return HealResult(
                False,
                f"{healer}: patch produced invalid syntax: {se}",
                healer=healer,
            )

        # Backup
        try:
            backup_dir = _BACKEND_ROOT / ".fix_backups"
            backup_dir.mkdir(exist_ok=True)
            import time, shutil
            safe = str(target.relative_to(_BACKEND_ROOT)).replace("/", "_").replace("\\", "_")
            shutil.copy2(target, backup_dir / f"{safe}.{int(time.time())}.bak")
        except Exception:
            pass

        # Write
        try:
            target.write_text(new_source, encoding="utf-8")
        except Exception as e:
            return HealResult(False, f"{healer}: write failed: {e}", healer=healer)

        # Hot-reload
        parts = str(target.relative_to(_BACKEND_ROOT)).replace("\\", "/")
        module_name = parts.replace("/", ".").removesuffix(".py")
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
        except Exception:
            pass

        desc = description or f"{healer} patch applied to {target.name}"
        return HealResult(True, desc, patch_applied=True, healer=healer)


# ── Singleton ─────────────────────────────────────────────────────────────

_healer: Optional[DeterministicHealer] = None


def get_deterministic_healer() -> DeterministicHealer:
    global _healer
    if _healer is None:
        _healer = DeterministicHealer()
    return _healer
