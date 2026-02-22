"""
CodeNet Data Source Adapter for GRACE

Integrates IBM's Project CodeNet dataset into GRACE's ingestion pipeline.
Focuses on extracting actionable learning signals rather than bulk ingestion:
  - Error pattern pairs (rejected → accepted for the same problem)
  - Code similarity groups (multiple solutions to the same problem)
  - Performance metrics (runtime/memory data for optimization learning)

Usage:
    adapter = CodeNetAdapter("/path/to/Project_CodeNet")
    samples = adapter.load_curated_subset(languages=["Python", "Java"], max_per_problem=5)
    signals = adapter.extract_learning_signals(problem_id="p00001")
"""

import csv
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SubmissionStatus(Enum):
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"
    OUTPUT_LIMIT_EXCEEDED = "Output Limit Exceeded"
    OTHER = "Other"

    @classmethod
    def from_string(cls, s: str) -> "SubmissionStatus":
        mapping = {
            "accepted": cls.ACCEPTED,
            "wrong answer": cls.WRONG_ANSWER,
            "time limit exceeded": cls.TIME_LIMIT_EXCEEDED,
            "memory limit exceeded": cls.MEMORY_LIMIT_EXCEEDED,
            "runtime error": cls.RUNTIME_ERROR,
            "compile error": cls.COMPILE_ERROR,
            "output limit exceeded": cls.OUTPUT_LIMIT_EXCEEDED,
        }
        return mapping.get(s.strip().lower(), cls.OTHER)


@dataclass
class CodeNetSample:
    submission_id: str
    problem_id: str
    language: str
    status: SubmissionStatus
    cpu_time_ms: Optional[float] = None
    memory_kb: Optional[float] = None
    code_size_bytes: Optional[int] = None
    source_code: str = ""
    file_path: str = ""


@dataclass
class LearningPair:
    """A rejected/accepted pair for the same problem — ideal for pattern learning."""
    problem_id: str
    language: str
    rejected: CodeNetSample
    accepted: CodeNetSample
    error_type: str = ""
    performance_delta_ms: Optional[float] = None


@dataclass
class SimilarityGroup:
    """Multiple solutions to the same problem across languages."""
    problem_id: str
    solutions: List[CodeNetSample] = field(default_factory=list)

    @property
    def languages(self) -> List[str]:
        return list({s.language for s in self.solutions})


LANGUAGE_EXTENSIONS = {
    "C": ".c", "C++": ".cpp", "Java": ".java", "Python": ".py",
    "Ruby": ".rb", "Go": ".go", "JavaScript": ".js", "Rust": ".rs",
    "C#": ".cs", "PHP": ".php", "Kotlin": ".kt", "Swift": ".swift",
    "Scala": ".scala", "Haskell": ".hs", "COBOL": ".cbl",
    "FORTRAN": ".f", "Pascal": ".pas",
}

SUPPORTED_LANGUAGES = {"Python", "Java", "C++", "C", "JavaScript", "Go", "Rust", "Ruby"}


class CodeNetAdapter:
    """
    Adapter for loading and processing IBM Project CodeNet data
    into GRACE's ingestion and learning systems.
    """

    def __init__(self, codenet_root: str):
        self.root = Path(codenet_root)
        self.data_dir = self.root / "data"
        self.metadata_dir = self.root / "metadata"
        self._validate_structure()

    def _validate_structure(self):
        if not self.root.exists():
            raise FileNotFoundError(
                f"CodeNet root not found: {self.root}. "
                "Download from https://developer.ibm.com/exchanges/data/all/project-codenet/"
            )
        if not self.metadata_dir.exists():
            logger.warning(
                f"Metadata directory not found at {self.metadata_dir}. "
                "Some features will be unavailable."
            )

    def list_problems(self) -> List[str]:
        if not self.data_dir.exists():
            return []
        return sorted(
            d.name for d in self.data_dir.iterdir()
            if d.is_dir() and d.name.startswith("p")
        )

    def load_problem_metadata(self, problem_id: str) -> List[Dict[str, Any]]:
        csv_path = self.metadata_dir / f"{problem_id}.csv"
        if not csv_path.exists():
            return []
        rows = []
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def load_sample(self, problem_id: str, submission_id: str, language: str) -> Optional[CodeNetSample]:
        lang_dir = self.data_dir / problem_id / language
        if not lang_dir.exists():
            return None

        ext = LANGUAGE_EXTENSIONS.get(language, "")
        source_file = lang_dir / f"{submission_id}{ext}"
        if not source_file.exists():
            for f in lang_dir.iterdir():
                if f.stem == submission_id:
                    source_file = f
                    break
            else:
                return None

        try:
            source_code = source_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Could not read {source_file}: {e}")
            return None

        return CodeNetSample(
            submission_id=submission_id,
            problem_id=problem_id,
            language=language,
            status=SubmissionStatus.OTHER,
            source_code=source_code,
            file_path=str(source_file),
        )

    def load_curated_subset(
        self,
        languages: Optional[List[str]] = None,
        max_per_problem: int = 5,
        max_problems: int = 1000,
        accepted_only: bool = False,
    ) -> List[CodeNetSample]:
        """
        Load a curated subset of CodeNet samples suitable for GRACE's ingestion.

        Args:
            languages: Filter to these languages (default: SUPPORTED_LANGUAGES)
            max_per_problem: Max accepted submissions per problem per language
            max_problems: Max number of problems to process
            accepted_only: Only load accepted submissions
        """
        languages = set(languages or SUPPORTED_LANGUAGES)
        samples = []
        problems = self.list_problems()[:max_problems]

        for problem_id in problems:
            metadata = self.load_problem_metadata(problem_id)
            by_lang: Dict[str, List[Dict]] = {}
            for row in metadata:
                lang = row.get("language", "")
                if lang not in languages:
                    continue
                status = row.get("status", "")
                if accepted_only and status.lower() != "accepted":
                    continue
                by_lang.setdefault(lang, []).append(row)

            for lang, rows in by_lang.items():
                accepted = [r for r in rows if r.get("status", "").lower() == "accepted"]
                selected = accepted[:max_per_problem] if accepted else rows[:max_per_problem]

                for row in selected:
                    sid = row.get("submission_id", "")
                    sample = self.load_sample(problem_id, sid, lang)
                    if sample:
                        sample.status = SubmissionStatus.from_string(row.get("status", ""))
                        sample.cpu_time_ms = _safe_float(row.get("cpu_time"))
                        sample.memory_kb = _safe_float(row.get("memory"))
                        sample.code_size_bytes = _safe_int(row.get("code_size"))
                        samples.append(sample)

        logger.info(f"Loaded {len(samples)} curated CodeNet samples from {len(problems)} problems")
        return samples

    def extract_learning_signals(
        self, problem_id: str, languages: Optional[List[str]] = None
    ) -> List[LearningPair]:
        """
        Extract learning pairs (rejected → accepted) for a problem.
        These map directly to GRACE's FeedbackProcessor LearningSignal format.
        """
        languages = set(languages or SUPPORTED_LANGUAGES)
        metadata = self.load_problem_metadata(problem_id)
        pairs = []

        by_lang: Dict[str, Dict[str, List[Dict]]] = {}
        for row in metadata:
            lang = row.get("language", "")
            if lang not in languages:
                continue
            status = row.get("status", "").lower()
            by_lang.setdefault(lang, {}).setdefault(status, []).append(row)

        for lang, status_groups in by_lang.items():
            accepted = status_groups.get("accepted", [])
            if not accepted:
                continue

            best_accepted = min(
                accepted,
                key=lambda r: _safe_float(r.get("cpu_time"), float("inf")),
            )
            accepted_sample = self.load_sample(problem_id, best_accepted["submission_id"], lang)
            if not accepted_sample:
                continue
            accepted_sample.status = SubmissionStatus.ACCEPTED
            accepted_sample.cpu_time_ms = _safe_float(best_accepted.get("cpu_time"))

            error_types = [
                "wrong answer", "time limit exceeded", "memory limit exceeded", "runtime error"
            ]
            for error_type in error_types:
                rejected_rows = status_groups.get(error_type, [])
                if not rejected_rows:
                    continue

                rejected_row = rejected_rows[0]
                rejected_sample = self.load_sample(problem_id, rejected_row["submission_id"], lang)
                if not rejected_sample:
                    continue
                rejected_sample.status = SubmissionStatus.from_string(error_type)
                rejected_sample.cpu_time_ms = _safe_float(rejected_row.get("cpu_time"))

                perf_delta = None
                if accepted_sample.cpu_time_ms and rejected_sample.cpu_time_ms:
                    perf_delta = rejected_sample.cpu_time_ms - accepted_sample.cpu_time_ms

                pairs.append(LearningPair(
                    problem_id=problem_id,
                    language=lang,
                    rejected=rejected_sample,
                    accepted=accepted_sample,
                    error_type=error_type,
                    performance_delta_ms=perf_delta,
                ))

        return pairs

    def build_similarity_groups(
        self,
        problem_ids: Optional[List[str]] = None,
        min_languages: int = 2,
        max_per_language: int = 1,
    ) -> List[SimilarityGroup]:
        """
        Build groups of semantically equivalent solutions (same problem, different languages).
        Useful for training GRACE's embedding model on cross-language similarity.
        """
        problem_ids = problem_ids or self.list_problems()[:500]
        groups = []

        for problem_id in problem_ids:
            metadata = self.load_problem_metadata(problem_id)
            accepted_by_lang: Dict[str, List[Dict]] = {}
            for row in metadata:
                if row.get("status", "").lower() != "accepted":
                    continue
                lang = row.get("language", "")
                if lang in SUPPORTED_LANGUAGES:
                    accepted_by_lang.setdefault(lang, []).append(row)

            if len(accepted_by_lang) < min_languages:
                continue

            group = SimilarityGroup(problem_id=problem_id)
            for lang, rows in accepted_by_lang.items():
                best = min(rows, key=lambda r: _safe_float(r.get("cpu_time"), float("inf")))
                sample = self.load_sample(problem_id, best["submission_id"], lang)
                if sample:
                    sample.status = SubmissionStatus.ACCEPTED
                    sample.cpu_time_ms = _safe_float(best.get("cpu_time"))
                    group.solutions.append(sample)

            if len(group.languages) >= min_languages:
                groups.append(group)

        logger.info(f"Built {len(groups)} similarity groups from {len(problem_ids)} problems")
        return groups

    def to_ingestion_documents(
        self, samples: List[CodeNetSample]
    ) -> List[Dict[str, Any]]:
        """
        Convert CodeNet samples to the document format expected by
        GRACE's ingestion service (TextIngestionService.ingest_text).
        """
        documents = []
        for sample in samples:
            metadata = {
                "source": "codenet",
                "problem_id": sample.problem_id,
                "language": sample.language,
                "status": sample.status.value,
                "submission_id": sample.submission_id,
            }
            if sample.cpu_time_ms is not None:
                metadata["cpu_time_ms"] = sample.cpu_time_ms
            if sample.memory_kb is not None:
                metadata["memory_kb"] = sample.memory_kb
            if sample.code_size_bytes is not None:
                metadata["code_size_bytes"] = sample.code_size_bytes

            documents.append({
                "text": sample.source_code,
                "title": f"CodeNet/{sample.problem_id}/{sample.language}/{sample.submission_id}",
                "source_path": sample.file_path,
                "metadata": metadata,
            })
        return documents

    def to_feedback_signals(
        self, pairs: List[LearningPair]
    ) -> List[Dict[str, Any]]:
        """
        Convert learning pairs to the signal format expected by
        GRACE's FeedbackProcessor.
        """
        signals = []
        for pair in pairs:
            signals.append({
                "signal_type": "correction",
                "context": {
                    "problem_id": pair.problem_id,
                    "language": pair.language,
                    "error_type": pair.error_type,
                    "rejected_code_snippet": pair.rejected.source_code[:500],
                    "accepted_code_snippet": pair.accepted.source_code[:500],
                },
                "outcome": f"corrected_{pair.error_type.replace(' ', '_')}",
                "confidence": 0.9 if pair.error_type == "wrong answer" else 0.7,
                "patterns": _extract_diff_patterns(
                    pair.rejected.source_code, pair.accepted.source_code
                ),
            })
        return signals


def _safe_float(val, default=None) -> Optional[float]:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None) -> Optional[int]:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _extract_diff_patterns(rejected: str, accepted: str) -> List[str]:
    """Extract high-level diff patterns between rejected and accepted code."""
    patterns = []
    r_lines = set(rejected.strip().splitlines())
    a_lines = set(accepted.strip().splitlines())

    added = a_lines - r_lines
    removed = r_lines - a_lines

    if len(accepted) < len(rejected) * 0.7:
        patterns.append("significant_simplification")
    if len(accepted) > len(rejected) * 1.5:
        patterns.append("added_complexity")

    for line in added:
        stripped = line.strip()
        if stripped.startswith("if ") or stripped.startswith("elif "):
            patterns.append("added_condition")
            break
    for line in added:
        stripped = line.strip()
        if "try" in stripped or "except" in stripped or "catch" in stripped:
            patterns.append("added_error_handling")
            break
    for line in added:
        stripped = line.strip()
        if "sort" in stripped.lower():
            patterns.append("added_sorting")
            break

    if not patterns:
        patterns.append("structural_change")

    return patterns[:5]
