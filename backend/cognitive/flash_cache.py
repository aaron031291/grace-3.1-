"""
FlashCache — Reference-Based Intelligent Caching Layer

Instead of downloading and storing full content from external sources, FlashCache
stores lightweight metadata (keywords, summary, validation status, trust score)
alongside the source URI. Content is streamed on demand from the original source.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │                     FlashCache                          │
  │                                                         │
  │  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐│
  │  │ SQLite   │  │ In-Memory  │  │  Keyword Inverted    ││
  │  │ Store    │  │ LRU Cache  │  │  Index               ││
  │  └──────────┘  └────────────┘  └──────────────────────┘│
  │                                                         │
  │  ┌──────────────────────────────────────────────────────┐│
  │  │ Source Registry (API, Web, Search, Internal)         ││
  │  └──────────────────────────────────────────────────────┘│
  │                                                         │
  │  Capabilities:                                          │
  │  • register(uri, keywords, summary) → fast lookup       │
  │  • lookup(keyword) → matching entries without download   │
  │  • stream(entry_id) → fetch content from source on demand│
  │  • predict_keywords(topic) → pre-discover related refs   │
  │  • validate(entry_id) → verify source still accessible   │
  └─────────────────────────────────────────────────────────┘

Benefits:
  - No redundant downloads — source URI is the reference, content is fetched once
  - Fast keyword lookup — inverted index over all cached references
  - Pre-emptive keyword discovery — scan sources for relevant terms ahead of time
  - Trust-scored references — validated entries get higher priority
  - TTL-based freshness — stale entries re-validated automatically
  - Works across all data sources: APIs, web, search, internal knowledge
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 72
LRU_MAX_SIZE = 10_000
KEYWORD_BATCH_SIZE = 50


def _get_cache_db_path() -> str:
    base = Path(__file__).parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "flash_cache.db")


class FlashCacheEntry:
    """A single cached reference."""

    __slots__ = (
        "id", "source_uri", "source_type", "source_name",
        "keywords", "summary", "content_hash",
        "headers", "auth_type",
        "trust_score", "validation_status",
        "access_count", "last_accessed", "created_at", "ttl_hours",
        "metadata",
    )

    def __init__(self, **kwargs):
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot))

    def to_dict(self) -> dict:
        return {s: getattr(self, s, None) for s in self.__slots__}

    @property
    def is_stale(self) -> bool:
        if not self.last_accessed or not self.ttl_hours:
            return False
        try:
            last = datetime.fromisoformat(self.last_accessed)
            return datetime.now(timezone.utc) - last > timedelta(hours=self.ttl_hours)
        except Exception:
            return False


class FlashCache:
    """
    The core cache engine.

    Thread-safe, backed by SQLite for persistence and an in-memory LRU
    for hot lookups. Keyword inverted index enables sub-millisecond
    keyword → entries resolution.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = None):
        self._db_path = db_path or _get_cache_db_path()
        self._lru: OrderedDict[str, FlashCacheEntry] = OrderedDict()
        self._keyword_index: Dict[str, Set[str]] = {}  # keyword → set of entry IDs
        self._db_lock = threading.Lock()
        self._init_db()
        self._load_keyword_index()

    @classmethod
    def get_instance(cls) -> "FlashCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Database ──────────────────────────────────────────────────────

    def _init_db(self):
        with self._db_lock:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flash_entries (
                    id TEXT PRIMARY KEY,
                    source_uri TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'web',
                    source_name TEXT DEFAULT '',
                    keywords TEXT DEFAULT '[]',
                    summary TEXT DEFAULT '',
                    content_hash TEXT DEFAULT '',
                    headers TEXT DEFAULT '{}',
                    auth_type TEXT DEFAULT 'none',
                    trust_score REAL DEFAULT 0.5,
                    validation_status TEXT DEFAULT 'unvalidated',
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    created_at TEXT,
                    ttl_hours INTEGER DEFAULT 72,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_flash_source_uri
                ON flash_entries(source_uri)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_flash_source_type
                ON flash_entries(source_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_flash_trust
                ON flash_entries(trust_score DESC)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flash_keywords (
                    keyword TEXT NOT NULL,
                    entry_id TEXT NOT NULL,
                    relevance REAL DEFAULT 1.0,
                    PRIMARY KEY (keyword, entry_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_flash_kw
                ON flash_keywords(keyword)
            """)
            conn.commit()
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        return conn

    # ── Core Operations ───────────────────────────────────────────────

    def register(
        self,
        source_uri: str,
        source_type: str = "web",
        source_name: str = "",
        keywords: List[str] = None,
        summary: str = "",
        content_hash: str = "",
        headers: Dict[str, str] = None,
        auth_type: str = "none",
        trust_score: float = 0.5,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """
        Register a source reference in the flash cache.
        Returns the entry ID.

        Does NOT download the content — only stores the URI and metadata.
        """
        entry_id = hashlib.sha256(source_uri.encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat()
        kw_list = [k.lower().strip() for k in (keywords or []) if k.strip()]

        entry = FlashCacheEntry(
            id=entry_id,
            source_uri=source_uri,
            source_type=source_type,
            source_name=source_name or source_uri.split("/")[-1][:50],
            keywords=kw_list,
            summary=summary[:2000] if summary else "",
            content_hash=content_hash,
            headers=headers or {},
            auth_type=auth_type,
            trust_score=trust_score,
            validation_status="unvalidated",
            access_count=0,
            last_accessed=now,
            created_at=now,
            ttl_hours=ttl_hours,
            metadata=metadata or {},
        )

        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO flash_entries
                    (id, source_uri, source_type, source_name, keywords, summary,
                     content_hash, headers, auth_type, trust_score, validation_status,
                     access_count, last_accessed, created_at, ttl_hours, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry_id, source_uri, source_type, source_name,
                    json.dumps(kw_list), summary[:2000],
                    content_hash, json.dumps(headers or {}),
                    auth_type, trust_score, "unvalidated",
                    0, now, now, ttl_hours, json.dumps(metadata or {}),
                ))

                # Update keyword index
                conn.execute("DELETE FROM flash_keywords WHERE entry_id = ?", (entry_id,))
                for kw in kw_list:
                    conn.execute(
                        "INSERT OR REPLACE INTO flash_keywords (keyword, entry_id, relevance) VALUES (?, ?, ?)",
                        (kw, entry_id, 1.0),
                    )

                conn.commit()
            finally:
                conn.close()

        # Update in-memory
        self._lru[entry_id] = entry
        self._lru.move_to_end(entry_id)
        if len(self._lru) > LRU_MAX_SIZE:
            self._lru.popitem(last=False)

        for kw in kw_list:
            if kw not in self._keyword_index:
                self._keyword_index[kw] = set()
            self._keyword_index[kw].add(entry_id)

        return entry_id

    def lookup(
        self,
        keyword: str = None,
        keywords: List[str] = None,
        source_type: str = None,
        min_trust: float = 0.0,
        limit: int = 50,
    ) -> List[dict]:
        """
        Fast keyword lookup. Returns matching entries WITHOUT downloading content.

        If multiple keywords are given, returns entries matching ANY of them,
        ranked by how many keywords they match and their trust score.
        """
        kw_list = []
        if keyword:
            kw_list.append(keyword.lower().strip())
        if keywords:
            kw_list.extend([k.lower().strip() for k in keywords])

        if not kw_list and not source_type:
            return self._list_recent(limit, min_trust)

        # Score entries by keyword match count
        entry_scores: Dict[str, int] = {}
        for kw in kw_list:
            matching_ids = self._keyword_index.get(kw, set())
            if not matching_ids:
                matching_ids = self._keyword_search_db(kw)
            for eid in matching_ids:
                entry_scores[eid] = entry_scores.get(eid, 0) + 1

        # Fetch entries and filter
        results = []
        for eid, match_count in sorted(entry_scores.items(), key=lambda x: -x[1]):
            entry = self._get_entry(eid)
            if not entry:
                continue
            if source_type and entry.source_type != source_type:
                continue
            if entry.trust_score < min_trust:
                continue
            d = entry.to_dict()
            d["match_count"] = match_count
            results.append(d)
            if len(results) >= limit:
                break

        return results

    def search(
        self,
        query: str,
        source_type: str = None,
        min_trust: float = 0.0,
        limit: int = 50,
    ) -> List[dict]:
        """
        Full-text search across keywords, summaries, and source names.
        More flexible than lookup — splits query into tokens and does fuzzy matching.
        """
        tokens = [t.lower().strip() for t in query.split() if len(t.strip()) >= 2]
        if not tokens:
            return []

        # First try keyword index
        results = self.lookup(keywords=tokens, source_type=source_type, min_trust=min_trust, limit=limit)

        if len(results) < limit:
            # Fall back to summary/name search in DB
            with self._db_lock:
                conn = self._get_conn()
                try:
                    conditions = []
                    params = []
                    for token in tokens[:10]:
                        conditions.append("(LOWER(summary) LIKE ? OR LOWER(source_name) LIKE ? OR LOWER(keywords) LIKE ?)")
                        params.extend([f"%{token}%", f"%{token}%", f"%{token}%"])

                    if source_type:
                        conditions.append("source_type = ?")
                        params.append(source_type)
                    conditions.append("trust_score >= ?")
                    params.append(min_trust)

                    where = " AND ".join(conditions)
                    rows = conn.execute(
                        f"SELECT * FROM flash_entries WHERE {where} ORDER BY trust_score DESC, access_count DESC LIMIT ?",
                        params + [limit]
                    ).fetchall()

                    seen = {r["id"] for r in results}
                    for row in rows:
                        if row["id"] not in seen:
                            entry = self._row_to_entry(row)
                            d = entry.to_dict()
                            d["match_count"] = 0
                            results.append(d)
                            seen.add(row["id"])
                finally:
                    conn.close()

        return results[:limit]

    def stream_content(self, entry_id: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch content from the original source on demand.
        This is the only time actual data is downloaded.
        Updates access count and last_accessed timestamp.
        """
        entry = self._get_entry(entry_id)
        if not entry:
            return {"error": "Entry not found", "entry_id": entry_id}

        import requests

        try:
            headers = entry.headers if isinstance(entry.headers, dict) else json.loads(entry.headers or "{}")

            if entry.auth_type == "bearer" and headers.get("Authorization"):
                pass  # already set
            headers.setdefault("User-Agent", "Grace/FlashCache/1.0")
            headers.setdefault("Accept", "application/json, text/html, */*")

            resp = requests.get(entry.source_uri, headers=headers, timeout=timeout, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")

            # Stream the response — read in chunks, don't hold entire body in memory
            chunks = []
            total = 0
            max_bytes = 10 * 1024 * 1024  # 10 MB max for streaming read
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    break

            raw = b"".join(chunks)

            # Try to parse as JSON
            data = None
            text = None
            if "json" in content_type:
                try:
                    data = json.loads(raw)
                except Exception:
                    text = raw.decode("utf-8", errors="replace")
            elif "text" in content_type or "html" in content_type:
                text = raw.decode("utf-8", errors="replace")
            else:
                text = raw.decode("utf-8", errors="replace")

            # Update access stats
            self._touch(entry_id)

            # Update content hash for change detection
            new_hash = hashlib.sha256(raw).hexdigest()
            changed = entry.content_hash and entry.content_hash != new_hash
            self._update_hash(entry_id, new_hash)

            result = {
                "entry_id": entry_id,
                "source_uri": entry.source_uri,
                "content_type": content_type,
                "size": total,
                "changed_since_last": changed,
                "trust_score": entry.trust_score,
            }
            if data is not None:
                result["data"] = data
            if text is not None:
                result["text"] = text[:50000]

            return result

        except requests.exceptions.RequestException as e:
            self._mark_validation(entry_id, "unreachable")
            return {
                "entry_id": entry_id,
                "source_uri": entry.source_uri,
                "error": str(e),
                "validation_status": "unreachable",
            }

    def validate(self, entry_id: str) -> Dict[str, Any]:
        """
        Check if source is still accessible without downloading full content.
        Uses HEAD request for efficiency.
        """
        entry = self._get_entry(entry_id)
        if not entry:
            return {"valid": False, "reason": "not_found"}

        import requests

        try:
            headers = entry.headers if isinstance(entry.headers, dict) else json.loads(entry.headers or "{}")
            headers.setdefault("User-Agent", "Grace/FlashCache/1.0")

            resp = requests.head(entry.source_uri, headers=headers, timeout=10, allow_redirects=True)

            if resp.status_code < 400:
                self._mark_validation(entry_id, "validated")
                return {
                    "valid": True,
                    "entry_id": entry_id,
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "content_length": resp.headers.get("Content-Length"),
                }
            else:
                self._mark_validation(entry_id, "http_error")
                return {
                    "valid": False,
                    "entry_id": entry_id,
                    "status_code": resp.status_code,
                    "reason": f"HTTP {resp.status_code}",
                }
        except Exception as e:
            self._mark_validation(entry_id, "unreachable")
            return {"valid": False, "entry_id": entry_id, "reason": str(e)}

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """
        Extract keywords from text for indexing.
        Uses a simple TF-based approach — fast and deterministic.
        """
        import re

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "when", "where", "why", "how", "all", "each",
            "every", "both", "few", "more", "most", "other", "some", "such", "no",
            "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "because", "but", "and", "or", "if", "while", "about", "up",
            "it", "its", "this", "that", "these", "those", "i", "me", "my",
            "we", "our", "you", "your", "he", "him", "his", "she", "her",
            "they", "them", "their", "what", "which", "who", "whom",
        }

        words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}', text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if w not in stop_words and len(w) >= 3:
                freq[w] = freq.get(w, 0) + 1

        sorted_words = sorted(freq.items(), key=lambda x: -x[1])
        return [w for w, _ in sorted_words[:max_keywords]]

    def predict_keywords(self, topic: str, depth: int = 2) -> List[dict]:
        """
        Pre-emptive keyword discovery. Given a topic, find related cached
        references that the user might need next.

        Uses keyword co-occurrence: if topic keywords appear alongside other
        keywords in cached entries, those co-occurring keywords are likely relevant.
        """
        topic_kws = self.extract_keywords(topic)
        if not topic_kws:
            return []

        # Find entries matching topic keywords
        direct_entries = self.lookup(keywords=topic_kws, limit=100)

        # Collect co-occurring keywords
        co_keywords: Dict[str, int] = {}
        for entry in direct_entries:
            entry_kws = entry.get("keywords", [])
            if isinstance(entry_kws, str):
                try:
                    entry_kws = json.loads(entry_kws)
                except Exception:
                    entry_kws = []
            for kw in entry_kws:
                if kw not in topic_kws:
                    co_keywords[kw] = co_keywords.get(kw, 0) + 1

        # If depth > 1, expand from co-occurring keywords
        if depth > 1 and co_keywords:
            top_co = sorted(co_keywords.items(), key=lambda x: -x[1])[:10]
            for kw, _ in top_co:
                expanded = self.lookup(keyword=kw, limit=20)
                for entry in expanded:
                    entry_kws = entry.get("keywords", [])
                    if isinstance(entry_kws, str):
                        try:
                            entry_kws = json.loads(entry_kws)
                        except Exception:
                            entry_kws = []
                    for k in entry_kws:
                        if k not in topic_kws:
                            co_keywords[k] = co_keywords.get(k, 0) + 1

        # Return ranked predictions
        ranked = sorted(co_keywords.items(), key=lambda x: -x[1])[:30]
        return [{"keyword": kw, "relevance": count, "source_count": count} for kw, count in ranked]

    def update_trust(self, entry_id: str, trust_delta: float):
        """Adjust trust score for an entry (positive or negative)."""
        entry = self._get_entry(entry_id)
        if not entry:
            return
        new_trust = max(0.0, min(1.0, entry.trust_score + trust_delta))
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE flash_entries SET trust_score = ? WHERE id = ?",
                    (new_trust, entry_id)
                )
                conn.commit()
            finally:
                conn.close()
        if entry_id in self._lru:
            self._lru[entry_id].trust_score = new_trust

    def remove(self, entry_id: str) -> bool:
        """Remove an entry from the cache."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM flash_entries WHERE id = ?", (entry_id,))
                conn.execute("DELETE FROM flash_keywords WHERE entry_id = ?", (entry_id,))
                conn.commit()
            finally:
                conn.close()

        self._lru.pop(entry_id, None)
        for kw, ids in self._keyword_index.items():
            ids.discard(entry_id)
        return True

    def stats(self) -> dict:
        """Cache statistics."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                total = conn.execute("SELECT COUNT(*) FROM flash_entries").fetchone()[0]
                by_type = dict(conn.execute(
                    "SELECT source_type, COUNT(*) FROM flash_entries GROUP BY source_type"
                ).fetchall())
                by_status = dict(conn.execute(
                    "SELECT validation_status, COUNT(*) FROM flash_entries GROUP BY validation_status"
                ).fetchall())
                avg_trust = conn.execute(
                    "SELECT AVG(trust_score) FROM flash_entries"
                ).fetchone()[0] or 0
                total_accesses = conn.execute(
                    "SELECT SUM(access_count) FROM flash_entries"
                ).fetchone()[0] or 0
                unique_keywords = conn.execute(
                    "SELECT COUNT(DISTINCT keyword) FROM flash_keywords"
                ).fetchone()[0]
                stale = conn.execute(
                    "SELECT COUNT(*) FROM flash_entries WHERE validation_status = 'unreachable'"
                ).fetchone()[0]

                return {
                    "total_entries": total,
                    "by_type": by_type,
                    "by_validation_status": by_status,
                    "avg_trust_score": round(avg_trust, 3),
                    "total_accesses": total_accesses,
                    "unique_keywords": unique_keywords,
                    "stale_entries": stale,
                    "lru_size": len(self._lru),
                    "keyword_index_size": len(self._keyword_index),
                }
            finally:
                conn.close()

    def cleanup_stale(self, max_age_hours: int = None) -> int:
        """Remove entries older than their TTL that are unreachable."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                now = datetime.now(timezone.utc)
                rows = conn.execute(
                    "SELECT id, last_accessed, ttl_hours, validation_status FROM flash_entries"
                ).fetchall()
                to_delete = []
                for row in rows:
                    try:
                        last = datetime.fromisoformat(row["last_accessed"])
                        ttl = row["ttl_hours"] or DEFAULT_TTL_HOURS
                        if max_age_hours:
                            ttl = max_age_hours
                        if now - last > timedelta(hours=ttl) and row["validation_status"] == "unreachable":
                            to_delete.append(row["id"])
                    except Exception:
                        continue

                for eid in to_delete:
                    conn.execute("DELETE FROM flash_entries WHERE id = ?", (eid,))
                    conn.execute("DELETE FROM flash_keywords WHERE entry_id = ?", (eid,))
                    self._lru.pop(eid, None)

                conn.commit()
                return len(to_delete)
            finally:
                conn.close()

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_entry(self, entry_id: str) -> Optional[FlashCacheEntry]:
        """Get entry from LRU or DB."""
        if entry_id in self._lru:
            self._lru.move_to_end(entry_id)
            return self._lru[entry_id]

        with self._db_lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM flash_entries WHERE id = ?", (entry_id,)
                ).fetchone()
                if row:
                    entry = self._row_to_entry(row)
                    self._lru[entry_id] = entry
                    if len(self._lru) > LRU_MAX_SIZE:
                        self._lru.popitem(last=False)
                    return entry
            finally:
                conn.close()
        return None

    def _row_to_entry(self, row) -> FlashCacheEntry:
        kw = row["keywords"]
        if isinstance(kw, str):
            try:
                kw = json.loads(kw)
            except Exception:
                kw = []

        hdrs = row["headers"]
        if isinstance(hdrs, str):
            try:
                hdrs = json.loads(hdrs)
            except Exception:
                hdrs = {}

        meta = row["metadata"]
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        return FlashCacheEntry(
            id=row["id"],
            source_uri=row["source_uri"],
            source_type=row["source_type"],
            source_name=row["source_name"],
            keywords=kw,
            summary=row["summary"],
            content_hash=row["content_hash"],
            headers=hdrs,
            auth_type=row["auth_type"],
            trust_score=row["trust_score"],
            validation_status=row["validation_status"],
            access_count=row["access_count"],
            last_accessed=row["last_accessed"],
            created_at=row["created_at"],
            ttl_hours=row["ttl_hours"],
            metadata=meta,
        )

    def _touch(self, entry_id: str):
        """Update access count and timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE flash_entries SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                    (now, entry_id)
                )
                conn.commit()
            finally:
                conn.close()
        if entry_id in self._lru:
            self._lru[entry_id].access_count = (self._lru[entry_id].access_count or 0) + 1
            self._lru[entry_id].last_accessed = now

    def _update_hash(self, entry_id: str, content_hash: str):
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE flash_entries SET content_hash = ? WHERE id = ?",
                    (content_hash, entry_id)
                )
                conn.commit()
            finally:
                conn.close()
        if entry_id in self._lru:
            self._lru[entry_id].content_hash = content_hash

    def _mark_validation(self, entry_id: str, status: str):
        with self._db_lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE flash_entries SET validation_status = ? WHERE id = ?",
                    (status, entry_id)
                )
                conn.commit()
            finally:
                conn.close()
        if entry_id in self._lru:
            self._lru[entry_id].validation_status = status

    def _keyword_search_db(self, keyword: str) -> Set[str]:
        """Search keyword index in DB for fuzzy match."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT entry_id FROM flash_keywords WHERE keyword LIKE ?",
                    (f"%{keyword}%",)
                ).fetchall()
                ids = {r["entry_id"] for r in rows}
                # Update in-memory index
                if ids:
                    if keyword not in self._keyword_index:
                        self._keyword_index[keyword] = set()
                    self._keyword_index[keyword].update(ids)
                return ids
            finally:
                conn.close()

    def _list_recent(self, limit: int, min_trust: float) -> List[dict]:
        """List most recently accessed entries."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT * FROM flash_entries WHERE trust_score >= ? ORDER BY last_accessed DESC LIMIT ?",
                    (min_trust, limit)
                ).fetchall()
                return [self._row_to_entry(r).to_dict() for r in rows]
            finally:
                conn.close()

    def _load_keyword_index(self):
        """Load keyword index into memory on startup."""
        with self._db_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute("SELECT keyword, entry_id FROM flash_keywords").fetchall()
                for row in rows:
                    kw = row["keyword"]
                    eid = row["entry_id"]
                    if kw not in self._keyword_index:
                        self._keyword_index[kw] = set()
                    self._keyword_index[kw].add(eid)
            finally:
                conn.close()


def get_flash_cache() -> FlashCache:
    """Get the singleton FlashCache instance."""
    return FlashCache.get_instance()
