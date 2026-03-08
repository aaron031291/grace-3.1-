"""
Semantic Entity Classifier — Translation layer between raw incoming data and
Grace's canonical domain model.

Problem it solves:
  Without this, every ingestion pipeline dumps raw text directly into the DB.
  Tables explode. No relational coherence. Hard to query or trust.

With this:
  Raw data → classify entity type → normalize into canonical bucket
  → only then materialize in the right DB table / collection.

Entity Buckets:
  CUSTOMER    — user, person, contact, account
  TRANSACTION — payment, order, event, trade
  BEHAVIOR    — action, interaction, signal, log
  KNOWLEDGE   — document, article, fact, Q&A
  CODE        — function, class, module, snippet
  TASK        — todo, ticket, milestone, project item
  SYSTEM      — metric, alert, health signal, configuration
  UNKNOWN     — could not be classified
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Entity types ───────────────────────────────────────────────────

ENTITY_TYPES = {
    "CUSTOMER": ["user", "customer", "person", "contact", "account", "client", "profile", "subscriber"],
    "TRANSACTION": ["order", "payment", "invoice", "transaction", "purchase", "trade", "checkout", "refund"],
    "BEHAVIOR": ["click", "action", "event", "interaction", "signal", "session", "visit", "view", "log"],
    "KNOWLEDGE": ["article", "document", "fact", "definition", "explanation", "wiki", "tutorial", "guide", "question", "answer"],
    "CODE": ["function", "class", "method", "module", "snippet", "import", "def ", "async ", "return ", "lambda"],
    "TASK": ["todo", "task", "ticket", "issue", "milestone", "project", "sprint", "backlog", "bug", "feature"],
    "SYSTEM": ["metric", "alert", "health", "status", "config", "configuration", "monitor", "diagnostic", "error", "exception"],
}

# ── Schema mappings ────────────────────────────────────────────────
# Maps entity type → (DB table, vector collection)

ENTITY_SCHEMA_MAP = {
    "CUSTOMER":    ("entity_customers",    "entities_customers"),
    "TRANSACTION": ("entity_transactions", "entities_transactions"),
    "BEHAVIOR":    ("entity_behaviors",    "entities_behaviors"),
    "KNOWLEDGE":   ("documents",           "documents"),
    "CODE":        ("code_entities",       "codebase_vectors"),
    "TASK":        ("entity_tasks",        "entities_tasks"),
    "SYSTEM":      ("entity_system",       "entities_system"),
    "UNKNOWN":     ("documents",           "documents"),   # fallback to generic docs
}


@dataclass
class ClassifiedEntity:
    """Result of semantic entity classification."""
    raw_text: str
    entity_type: str            # one of ENTITY_TYPES keys + UNKNOWN
    confidence: float           # 0.0–1.0
    matched_signals: list       # terms that fired
    db_table: str               # target physical table
    vector_collection: str      # target vector collection
    canonical_fields: dict = field(default_factory=dict)  # normalized fields
    should_deduplicate: bool = True
    metadata: dict = field(default_factory=dict)


class SemanticEntityClassifier:
    """
    Classifies incoming raw data into canonical entity buckets.

    Usage:
        clf = SemanticEntityClassifier()
        entity = clf.classify(text="User Aaron placed an order for $99")
        entity.entity_type   # → "CUSTOMER" or "TRANSACTION"
        entity.db_table      # → the right physical table
    """

    def __init__(self):
        self._compiled: dict = {}
        self._compile_patterns()

    def _compile_patterns(self):
        for entity_type, signals in ENTITY_TYPES.items():
            self._compiled[entity_type] = [s.lower() for s in signals]

    def classify(
        self,
        text: str,
        filename: str = "",
        source_type: str = "",
        metadata: dict = None,
    ) -> ClassifiedEntity:
        """
        Classify raw text into a semantic entity bucket.
        Uses keyword signal scoring across all buckets.
        """
        text_lower = (text or "").lower()
        fname_lower = (filename or "").lower()
        combined = text_lower[:2000] + " " + fname_lower  # cap text scan for speed

        scores: dict[str, float] = {}
        signals_hit: dict[str, list] = {}

        for entity_type, keywords in self._compiled.items():
            hits = [kw for kw in keywords if kw in combined]
            score = len(hits) / max(len(keywords), 1)
            scores[entity_type] = score
            signals_hit[entity_type] = hits

        # Source type overrides
        if source_type in ("academic_paper", "official_docs", "verified_tutorial"):
            scores["KNOWLEDGE"] = max(scores.get("KNOWLEDGE", 0), 0.7)
        elif source_type == "user_generated":
            scores["CUSTOMER"] = scores.get("CUSTOMER", 0) + 0.1

        # Code file extension → CODE
        if any(fname_lower.endswith(ext) for ext in [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp"]):
            scores["CODE"] = max(scores.get("CODE", 0), 0.9)

        # Best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score < 0.05:
            best_type = "UNKNOWN"
            best_score = 0.0

        db_table, vector_collection = ENTITY_SCHEMA_MAP[best_type]

        canonical = self._build_canonical(best_type, text, metadata or {})

        return ClassifiedEntity(
            raw_text=text[:500],
            entity_type=best_type,
            confidence=round(min(best_score * 2, 1.0), 3),  # scale to 0-1
            matched_signals=signals_hit.get(best_type, []),
            db_table=db_table,
            vector_collection=vector_collection,
            canonical_fields=canonical,
            metadata=metadata or {},
        )

    def _build_canonical(self, entity_type: str, text: str, metadata: dict) -> dict:
        """Extract canonical normalized fields from raw text."""
        fields = {"raw_length": len(text), "has_metadata": bool(metadata)}

        if entity_type == "CUSTOMER":
            # Try to extract email
            email = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
            if email:
                fields["email"] = email.group(0)

        elif entity_type == "TRANSACTION":
            # Try to extract monetary amount
            amount = re.search(r"[\$£€]?\s*(\d[\d,]*(?:\.\d{2})?)", text)
            if amount:
                fields["amount_str"] = amount.group(0).strip()

        elif entity_type == "CODE":
            # Count function defs
            defs = len(re.findall(r"\bdef\b|\bfunction\b|\basync def\b", text))
            fields["function_count"] = defs

        elif entity_type == "TASK":
            # Extract priority keywords
            prio = None
            for p in ["urgent", "high priority", "critical", "low priority", "medium"]:
                if p in text.lower():
                    prio = p
                    break
            if prio:
                fields["priority_hint"] = prio

        return fields


# ── Module-level classify function ─────────────────────────────────

_classifier: Optional[SemanticEntityClassifier] = None


def get_classifier() -> SemanticEntityClassifier:
    global _classifier
    if _classifier is None:
        _classifier = SemanticEntityClassifier()
    return _classifier


def classify_entity(
    text: str,
    filename: str = "",
    source_type: str = "user_generated",
    metadata: dict = None,
) -> dict:
    """
    Public API: classify raw incoming data into a canonical entity bucket.

    Returns dict with: entity_type, confidence, db_table, vector_collection,
    canonical_fields, matched_signals.
    """
    result = get_classifier().classify(
        text=text,
        filename=filename,
        source_type=source_type,
        metadata=metadata,
    )
    return {
        "entity_type": result.entity_type,
        "confidence": result.confidence,
        "db_table": result.db_table,
        "vector_collection": result.vector_collection,
        "canonical_fields": result.canonical_fields,
        "matched_signals": result.matched_signals,
        "should_deduplicate": result.should_deduplicate,
    }
