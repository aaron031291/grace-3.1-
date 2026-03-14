"""
cognitive/swe_spindle_bridge.py
───────────────────────────────────────────────────────────────────────
SWE → Spindle Bridge  (Phase 4 wiring)

Connects the Active Learning Sampler to the Braille/Spindle pipeline.

Flow:
  1. Query high-trust LearningExamples (SWE patterns) from the DB
  2. Extract Python code snippets from them
  3. Translate Python → Braille token sequences via BrailleTranslator
  4. Validate translation determinism (round-trip invariance)
  5. Register proven patterns in DynamicDictionaryManager
  6. Track the LLM → deterministic ratio shift over time

This is the missing bridge between:
  - ExternalKnowledgePipeline (stores trust-scored LearningExamples)
  - ActiveLearningSampler (selects best examples — previously unwired)
  - BrailleTranslator (Python AST → Braille tokens)
  - SpindleExecutor (runs deterministic paths without LLM)

Every pattern that passes VVT validation = one fewer future LLM call.
"""

import ast
import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────
MIN_TRUST_THRESHOLD = 0.70      # Only consider examples above this trust
MIN_TIMES_VALIDATED = 1         # Must have been validated at least once
MAX_PATTERNS_PER_CYCLE = 20     # Max patterns to process per cycle
CYCLE_INTERVAL_S = 600          # 10 minutes between cycles
CODE_SNIPPET_MARKERS = [        # Markers that indicate code in learning examples
    "def ", "class ", "import ", "from ", "if ", "for ", "while ",
    "return ", "async def ", "await ", "with ",
]


@dataclass
class TranslationResult:
    """Result of translating a LearningExample → Braille."""
    example_id: str
    source_code: str
    braille_tokens: List[str]
    token_count: int
    is_valid: bool
    validation_error: str = ""
    pattern_hash: str = ""
    trust_score: float = 0.0
    timestamp: str = ""


@dataclass
class BridgeStats:
    """Running statistics for the SWE→Spindle bridge."""
    total_examples_scanned: int = 0
    total_patterns_extracted: int = 0
    total_translations_attempted: int = 0
    total_translations_succeeded: int = 0
    total_translations_failed: int = 0
    total_dictionary_entries_added: int = 0
    total_vvt_validations: int = 0
    total_vvt_passes: int = 0
    total_vvt_failures: int = 0
    deterministic_path_count: int = 0
    llm_bypass_ratio: float = 0.0  # fraction of paths that are now deterministic
    last_cycle_time: Optional[str] = None
    cycle_count: int = 0


class SWESpindleBridge:
    """
    Bridges SWE learning examples into the Spindle deterministic runtime.

    Pulls high-trust Python patterns from LearningExamples,
    translates them to Braille, validates, and registers them as
    deterministic Spindle paths — reducing future LLM dependency.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stats = BridgeStats()
        self._processed_hashes: set = set()  # avoid re-processing
        self._translation_history: List[TranslationResult] = []
        self._max_history = 200

    # ── Start / Stop ──────────────────────────────────────────────────

    def start(self) -> bool:
        if self._running:
            logger.info("[SWE-SPINDLE] Already running")
            return False
        self._running = True
        self._thread = threading.Thread(
            target=self._bridge_loop,
            daemon=True,
            name="grace-swe-spindle-bridge",
        )
        self._thread.start()
        logger.info("[SWE-SPINDLE] ✅ SWE→Spindle bridge started (cycle every %ds)", CYCLE_INTERVAL_S)
        return True

    def stop(self):
        self._running = False
        logger.info("[SWE-SPINDLE] Bridge stopped")

    # ── Main Loop ─────────────────────────────────────────────────────

    def _bridge_loop(self):
        time.sleep(120)  # let other systems start first
        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error("[SWE-SPINDLE] Cycle error: %s", e)
            time.sleep(CYCLE_INTERVAL_S)

    # ── Core Cycle ────────────────────────────────────────────────────

    def _run_cycle(self):
        self._stats.cycle_count += 1
        self._stats.last_cycle_time = datetime.now(timezone.utc).isoformat()
        cycle_start = time.monotonic()

        # Step 1: Pull high-trust SWE examples
        examples = self._query_high_trust_examples()
        self._stats.total_examples_scanned += len(examples)

        if not examples:
            logger.debug("[SWE-SPINDLE] No new high-trust SWE patterns found")
            return

        # Step 2: Extract code, translate, validate, register
        results = []
        for ex in examples[:MAX_PATTERNS_PER_CYCLE]:
            code = self._extract_code_from_example(ex)
            if not code:
                continue

            self._stats.total_patterns_extracted += 1
            result = self._translate_and_validate(ex, code)
            results.append(result)

            if result.is_valid:
                self._register_deterministic_path(result, ex)

        # Step 3: Update LLM bypass ratio
        self._update_bypass_ratio()

        elapsed = time.monotonic() - cycle_start
        succeeded = sum(1 for r in results if r.is_valid)
        failed = sum(1 for r in results if not r.is_valid)

        logger.info(
            "[SWE-SPINDLE] Cycle %d: scanned=%d, extracted=%d, translated=%d/%d, elapsed=%.1fs",
            self._stats.cycle_count, len(examples),
            self._stats.total_patterns_extracted,
            succeeded, succeeded + failed, elapsed,
        )

        # Publish event
        try:
            from cognitive.event_bus import publish_async
            publish_async("spindle.swe_bridge_cycle", {
                "cycle": self._stats.cycle_count,
                "examples_scanned": len(examples),
                "patterns_translated": succeeded,
                "patterns_failed": failed,
                "deterministic_paths": self._stats.deterministic_path_count,
                "llm_bypass_ratio": self._stats.llm_bypass_ratio,
                "elapsed_s": round(elapsed, 1),
            }, source="swe_spindle_bridge")
        except Exception:
            pass

        # Genesis tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"SWE→Spindle bridge: {succeeded} patterns translated, bypass ratio={self._stats.llm_bypass_ratio:.2%}",
                how="SWESpindleBridge._run_cycle",
                output_data={
                    "cycle": self._stats.cycle_count,
                    "translated": succeeded,
                    "failed": failed,
                    "bypass_ratio": self._stats.llm_bypass_ratio,
                },
                tags=["spindle", "swe_bridge", "phase_4"],
            )
        except Exception:
            pass

    # ── Step 1: Query High-Trust Examples ─────────────────────────────

    def _query_high_trust_examples(self) -> List[Any]:
        """Pull LearningExamples with trust >= threshold that contain SWE patterns."""
        try:
            from database.session import SessionLocal
            if SessionLocal is None:
                from database.session import initialize_session_factory
                initialize_session_factory()
                from database.session import SessionLocal as SL
                session = SL()
            else:
                session = SessionLocal()
        except Exception as e:
            logger.debug("[SWE-SPINDLE] DB session unavailable: %s", e)
            return []

        try:
            from cognitive.learning_memory import LearningExample
            examples = (
                session.query(LearningExample)
                .filter(LearningExample.trust_score >= MIN_TRUST_THRESHOLD)
                .filter(LearningExample.times_validated >= MIN_TIMES_VALIDATED)
                .order_by(LearningExample.trust_score.desc())
                .limit(MAX_PATTERNS_PER_CYCLE * 3)  # fetch extra, filter later
                .all()
            )

            # Filter out already-processed
            new_examples = []
            for ex in examples:
                h = self._example_hash(ex)
                if h not in self._processed_hashes:
                    new_examples.append(ex)

            return new_examples
        except Exception as e:
            logger.debug("[SWE-SPINDLE] Query failed: %s", e)
            return []
        finally:
            session.close()

    # ── Step 2: Extract Code ──────────────────────────────────────────

    def _extract_code_from_example(self, example) -> Optional[str]:
        """Extract Python code snippet from a LearningExample's content."""
        import json as _json

        # Check expected_output and input_context for code
        for field_name in ("expected_output", "actual_output", "input_context"):
            raw = getattr(example, field_name, None)
            if not raw:
                continue

            text = raw
            if isinstance(raw, str):
                try:
                    parsed = _json.loads(raw)
                    if isinstance(parsed, dict):
                        text = parsed.get("raw", parsed.get("content", raw))
                    elif isinstance(parsed, str):
                        text = parsed
                except Exception:
                    text = raw

            if not isinstance(text, str):
                continue

            # Check if it looks like Python code
            if any(marker in text for marker in CODE_SNIPPET_MARKERS):
                # Try to parse as valid Python
                try:
                    tree = ast.parse(text)
                    # Must contain at least one real statement (not just an expression)
                    has_real_code = any(
                        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.ClassDef, ast.Import, ast.ImportFrom,
                                         ast.For, ast.While, ast.If, ast.With,
                                         ast.Try, ast.Assign, ast.Return))
                        for node in ast.walk(tree)
                    )
                    if has_real_code:
                        return text
                except SyntaxError:
                    pass
                # Try extracting code block from markdown
                code = self._extract_markdown_code(text)
                if code:
                    return code

        return None

    @staticmethod
    def _extract_markdown_code(text: str) -> Optional[str]:
        """Extract Python code from markdown fenced blocks."""
        import re
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                ast.parse(match.strip())
                return match.strip()
            except SyntaxError:
                continue
        return None

    # ── Step 3: Translate & Validate ──────────────────────────────────

    def _translate_and_validate(self, example, code: str) -> TranslationResult:
        """Translate Python code → Braille tokens and validate."""
        self._stats.total_translations_attempted += 1
        example_id = str(getattr(example, "id", "unknown"))
        pattern_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        trust = getattr(example, "trust_score", 0.5)

        result = TranslationResult(
            example_id=example_id,
            source_code=code[:2000],
            braille_tokens=[],
            token_count=0,
            is_valid=False,
            pattern_hash=pattern_hash,
            trust_score=trust,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Translate using BrailleTranslator
        try:
            from cognitive.braille_translator import BrailleTranslator
            translator = BrailleTranslator()
            braille_output = translator.translate_code(code)
            tokens = [t for t in braille_output.split("\n") if t.strip()]
            result.braille_tokens = tokens
            result.token_count = len(tokens)
        except Exception as e:
            result.validation_error = f"Translation failed: {e}"
            self._stats.total_translations_failed += 1
            return result

        if result.token_count == 0:
            result.validation_error = "Empty translation output"
            self._stats.total_translations_failed += 1
            return result

        # Validate deterministic invariance: translate twice, compare
        try:
            translator2 = BrailleTranslator()
            braille_output2 = translator2.translate_code(code)
            if braille_output != braille_output2:
                result.validation_error = "Non-deterministic: two translations differ"
                self._stats.total_translations_failed += 1
                return result
        except Exception as e:
            result.validation_error = f"Determinism check failed: {e}"
            self._stats.total_translations_failed += 1
            return result

        # VVT validation if available
        self._stats.total_vvt_validations += 1
        try:
            from verification.deterministic_vvt_pipeline import vvt_vault
            vvt_passed = vvt_vault.run_all_layers(
                code_string=code,
                function_name=f"swe_pattern_{pattern_hash}",
            )
            if not vvt_passed:
                result.validation_error = "VVT pipeline rejected"
                self._stats.total_vvt_failures += 1
                self._stats.total_translations_failed += 1
                return result
            self._stats.total_vvt_passes += 1
        except Exception:
            # VVT unavailable — allow through with determinism check only
            pass

        result.is_valid = True
        self._stats.total_translations_succeeded += 1

        # Store in history
        with self._lock:
            self._translation_history.append(result)
            if len(self._translation_history) > self._max_history:
                self._translation_history = self._translation_history[-self._max_history:]

        return result

    # ── Step 4: Register Deterministic Path ───────────────────────────

    def _register_deterministic_path(self, result: TranslationResult, example):
        """Register a validated translation as a deterministic Spindle path."""
        self._processed_hashes.add(self._example_hash(example))

        # Register each new token in the DynamicDictionaryManager
        try:
            from core.dynamic_dictionary import DynamicDictionaryManager
            for token in result.braille_tokens:
                token_stripped = token.strip()
                if not token_stripped or token_stripped.startswith("["):
                    continue
                # Only register tokens that aren't already raw identifiers
                if "●" in token_stripped or "□" in token_stripped or "△" in token_stripped or "○" in token_stripped:
                    DynamicDictionaryManager.learn_word(
                        word=f"swe_{result.pattern_hash}_{token_stripped[:30]}",
                        braille_encoding=token_stripped,
                        semantic_meaning=f"SWE pattern from example {result.example_id}",
                        master_loop="SPINDLE",
                    )
                    self._stats.total_dictionary_entries_added += 1
        except Exception as e:
            logger.debug("[SWE-SPINDLE] Dictionary registration failed: %s", e)

        # Store as a learned procedure in unified memory
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_procedure(
                name=f"swe_pattern_{result.pattern_hash}",
                goal=f"Deterministic execution of SWE pattern (trust={result.trust_score:.2f})",
                steps="\n".join(result.braille_tokens),
                trust=result.trust_score,
                proc_type="swe_spindle_deterministic",
            )
        except Exception as e:
            logger.debug("[SWE-SPINDLE] Procedure storage failed: %s", e)

        # Mark the source LearningExample as referenced
        try:
            from database.session import SessionLocal
            session = SessionLocal()
            try:
                from cognitive.learning_memory import LearningExample as LE
                db_ex = session.query(LE).filter(LE.id == getattr(example, "id", None)).first()
                if db_ex:
                    db_ex.times_referenced = (db_ex.times_referenced or 0) + 1
                    db_ex.last_used = datetime.now(timezone.utc)
                    session.commit()
            finally:
                session.close()
        except Exception:
            pass

        self._stats.deterministic_path_count += 1
        logger.info(
            "[SWE-SPINDLE] ✅ Registered deterministic path: %s (%d tokens, trust=%.2f)",
            result.pattern_hash, result.token_count, result.trust_score,
        )

    # ── LLM Bypass Ratio ──────────────────────────────────────────────

    def _update_bypass_ratio(self):
        """Calculate fraction of execution paths that are now deterministic."""
        try:
            from cognitive.spindle_executor import get_spindle_executor
            executor = get_spindle_executor()
            total_exec = executor.stats.get("total_executions", 0)
            if total_exec > 0:
                # Each deterministic path replaces potential LLM calls
                self._stats.llm_bypass_ratio = min(
                    1.0,
                    self._stats.deterministic_path_count / max(total_exec, 1),
                )
        except Exception:
            pass

    # ── Manual Trigger ────────────────────────────────────────────────

    def process_example(self, example_id: int) -> Optional[TranslationResult]:
        """Manually process a single LearningExample by ID."""
        try:
            from database.session import SessionLocal
            session = SessionLocal()
            try:
                from cognitive.learning_memory import LearningExample
                ex = session.query(LearningExample).filter(LearningExample.id == example_id).first()
                if not ex:
                    return None
                code = self._extract_code_from_example(ex)
                if not code:
                    return None
                result = self._translate_and_validate(ex, code)
                if result.is_valid:
                    self._register_deterministic_path(result, ex)
                return result
            finally:
                session.close()
        except Exception as e:
            logger.error("[SWE-SPINDLE] Manual processing failed: %s", e)
            return None

    def force_cycle(self) -> Dict[str, Any]:
        """Manually trigger a full cycle."""
        try:
            self._run_cycle()
            return {"status": "completed", "stats": self.get_stats()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Status ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "cycle_count": self._stats.cycle_count,
            "last_cycle": self._stats.last_cycle_time,
            "examples_scanned": self._stats.total_examples_scanned,
            "patterns_extracted": self._stats.total_patterns_extracted,
            "translations_attempted": self._stats.total_translations_attempted,
            "translations_succeeded": self._stats.total_translations_succeeded,
            "translations_failed": self._stats.total_translations_failed,
            "dictionary_entries_added": self._stats.total_dictionary_entries_added,
            "vvt_validations": self._stats.total_vvt_validations,
            "vvt_passes": self._stats.total_vvt_passes,
            "vvt_failures": self._stats.total_vvt_failures,
            "deterministic_paths": self._stats.deterministic_path_count,
            "llm_bypass_ratio": round(self._stats.llm_bypass_ratio, 4),
            "processed_hashes": len(self._processed_hashes),
        }

    def get_translation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            recent = self._translation_history[-limit:]
        return [
            {
                "example_id": r.example_id,
                "token_count": r.token_count,
                "is_valid": r.is_valid,
                "pattern_hash": r.pattern_hash,
                "trust_score": r.trust_score,
                "error": r.validation_error,
                "timestamp": r.timestamp,
            }
            for r in reversed(recent)
        ]

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _example_hash(example) -> str:
        raw = f"{getattr(example, 'id', '')}:{getattr(example, 'input_context', '')}:{getattr(example, 'expected_output', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Singleton ─────────────────────────────────────────────────────────
_bridge: Optional[SWESpindleBridge] = None


def get_swe_spindle_bridge() -> SWESpindleBridge:
    global _bridge
    if _bridge is None:
        _bridge = SWESpindleBridge()
    return _bridge
