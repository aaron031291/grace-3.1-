"""
Spindle Event Store — persistent, append-only event log.

Writes every Spindle event to PostgreSQL via SQLAlchemy.  If the
database is unavailable the store falls back to an in-memory list
so the rest of the system keeps running.

Usage:
    from backend.cognitive.spindle_event_store import get_event_store

    store = get_event_store()
    store.append("healing.started", source_type="healing", payload={...})
"""

import hashlib
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thread-safe monotonic sequence counter
# ---------------------------------------------------------------------------

class _SequenceCounter:
    """Process-local monotonic counter (survives DB fallback mode)."""

    def __init__(self, start: int = 0):
        self._value = start
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    @property
    def current(self) -> int:
        with self._lock:
            return self._value

    def sync(self, value: int) -> None:
        """Set the counter to at least *value* (used after DB recovery)."""
        with self._lock:
            if value > self._value:
                self._value = value


# ---------------------------------------------------------------------------
# SpindleEventStore
# ---------------------------------------------------------------------------

class SpindleEventStore:
    """Persistent, append-only event store backed by PostgreSQL."""

    def __init__(self):
        self._seq = _SequenceCounter()
        self._fallback: List[Dict[str, Any]] = []
        self._fallback_lock = threading.Lock()
        self._db_available: Optional[bool] = None  # None = not yet probed
        self._write_queue: queue.Queue = queue.Queue(maxsize=50000)
        self._flush_thread: Optional[threading.Thread] = None
        self._flush_running = False

    # -- helpers -------------------------------------------------------------

    def _get_session_scope(self):
        """Lazy import to avoid circular imports at module level."""
        from backend.database.session import session_scope
        return session_scope

    def _get_model(self):
        from backend.models.spindle_event_model import SpindleEvent
        return SpindleEvent

    def _probe_db(self) -> bool:
        """Check DB reachability once; cache result."""
        if self._db_available is not None:
            return self._db_available
        try:
            session_scope = self._get_session_scope()
            with session_scope() as session:
                session.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            self._db_available = True
            self._sync_sequence_from_db()
        except Exception as exc:
            logger.warning(
                "[SpindleEventStore] DB unavailable — falling back to "
                "in-memory log: %s", exc,
            )
            self._db_available = False
        return self._db_available

    def _sync_sequence_from_db(self) -> None:
        """Set the in-process counter to max(sequence_id) from the table."""
        try:
            from sqlalchemy import func as sa_func
            SpindleEvent = self._get_model()
            session_scope = self._get_session_scope()
            with session_scope() as session:
                max_seq = session.query(
                    sa_func.max(SpindleEvent.sequence_id)
                ).scalar()
                if max_seq is not None:
                    self._seq.sync(max_seq)
        except Exception as exc:
            logger.warning("[SpindleEventStore] Could not sync sequence: %s", exc)

    @staticmethod
    def _hash_input(payload: Optional[Dict]) -> Optional[str]:
        if not payload:
            return None
        raw = str(sorted(payload.items())).encode()
        return hashlib.sha256(raw).hexdigest()

    # -- public API ----------------------------------------------------------

    def append(
        self,
        topic: str,
        source_type: str,
        payload: Optional[Dict[str, Any]] = None,
        proof_hash: Optional[str] = None,
        spindle_mask: Optional[str] = None,
        result: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        """
        Append an event.  Returns the assigned sequence_id.

        This is the **only** write method — no updates, no deletes.
        """
        seq = self._seq.next()
        now = datetime.now(timezone.utc)
        input_hash = self._hash_input(payload)

        if self._probe_db():
            try:
                SpindleEvent = self._get_model()
                session_scope = self._get_session_scope()
                with session_scope() as session:
                    event = SpindleEvent(
                        sequence_id=seq,
                        timestamp=now,
                        source_type=source_type,
                        topic=topic,
                        input_hash=input_hash,
                        spindle_mask=spindle_mask,
                        proof_hash=proof_hash,
                        result=result,
                        payload=payload,
                        source=source,
                    )
                    session.add(event)
                return seq
            except Exception as exc:
                logger.error(
                    "[SpindleEventStore] DB write failed — storing in memory: %s",
                    exc,
                )
                self._db_available = False

        # Fallback: keep in memory
        with self._fallback_lock:
            self._fallback.append({
                "sequence_id": seq,
                "timestamp": now.isoformat(),
                "source_type": source_type,
                "topic": topic,
                "input_hash": input_hash,
                "spindle_mask": spindle_mask,
                "proof_hash": proof_hash,
                "result": result,
                "payload": payload,
                "source": source,
            })
        return seq

    def query(
        self,
        topic: Optional[str] = None,
        source_type: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Read events with optional filters."""
        if self._probe_db():
            try:
                SpindleEvent = self._get_model()
                session_scope = self._get_session_scope()
                with session_scope() as session:
                    q = session.query(SpindleEvent)
                    if topic:
                        q = q.filter(SpindleEvent.topic == topic)
                    if source_type:
                        q = q.filter(SpindleEvent.source_type == source_type)
                    if after:
                        q = q.filter(SpindleEvent.timestamp > after)
                    if before:
                        q = q.filter(SpindleEvent.timestamp < before)
                    q = q.order_by(SpindleEvent.sequence_id.asc()).limit(limit)
                    return [row.to_dict() for row in q.all()]
            except Exception as exc:
                logger.error("[SpindleEventStore] DB query failed: %s", exc)

        # Fallback: filter in-memory list
        with self._fallback_lock:
            results = list(self._fallback)
        if topic:
            results = [e for e in results if e["topic"] == topic]
        if source_type:
            results = [e for e in results if e["source_type"] == source_type]
        return results[:limit]

    def replay(self, after_sequence: int = 0) -> List[Dict[str, Any]]:
        """Replay all events after a given sequence number."""
        if self._probe_db():
            try:
                SpindleEvent = self._get_model()
                session_scope = self._get_session_scope()
                with session_scope() as session:
                    rows = (
                        session.query(SpindleEvent)
                        .filter(SpindleEvent.sequence_id > after_sequence)
                        .order_by(SpindleEvent.sequence_id.asc())
                        .all()
                    )
                    return [row.to_dict() for row in rows]
            except Exception as exc:
                logger.error("[SpindleEventStore] DB replay failed: %s", exc)

        with self._fallback_lock:
            return [
                e for e in self._fallback
                if e["sequence_id"] > after_sequence
            ]

    def get_sequence(self) -> int:
        """Return the current (latest) sequence number."""
        return self._seq.current

    # -- async / background flush -------------------------------------------

    def append_async(
        self,
        topic: str,
        source_type: str,
        payload: Optional[Dict[str, Any]] = None,
        proof_hash: Optional[str] = None,
        spindle_mask: Optional[str] = None,
        result: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        """
        Non-blocking append. Queues the event for background flush.
        Returns the assigned sequence_id immediately.
        """
        seq = self._seq.next()
        now = datetime.now(timezone.utc)
        input_hash = self._hash_input(payload)

        event_data = {
            "sequence_id": seq,
            "timestamp": now,
            "source_type": source_type,
            "topic": topic,
            "input_hash": input_hash,
            "spindle_mask": spindle_mask,
            "proof_hash": proof_hash,
            "result": result,
            "payload": payload,
            "source": source,
        }

        try:
            self._write_queue.put_nowait(event_data)
        except queue.Full:
            logger.warning("[SpindleEventStore] Write queue full, falling back to sync append")
            return self.append(topic, source_type, payload, proof_hash, spindle_mask, result, source)

        return seq

    def start_background_flush(self):
        """Start the background thread that flushes queued events to DB."""
        if self._flush_thread is not None and self._flush_thread.is_alive():
            return
        self._flush_running = True
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="spindle-event-flush"
        )
        self._flush_thread.start()
        logger.info("[SpindleEventStore] Background flush thread started")

    def stop_background_flush(self):
        """Stop the background flush thread."""
        self._flush_running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
            self._flush_thread = None

    def _flush_loop(self):
        """Background loop: drain write queue and batch-insert to DB."""
        while self._flush_running:
            batch = []
            try:
                # Drain up to 100 events per flush cycle
                while len(batch) < 100:
                    try:
                        event_data = self._write_queue.get_nowait()
                        batch.append(event_data)
                    except queue.Empty:
                        break

                if batch:
                    self._flush_batch(batch)
            except Exception as e:
                logger.error("[SpindleEventStore] Flush error: %s", e)
                # Store failed batch in fallback
                with self._fallback_lock:
                    for item in batch:
                        item["timestamp"] = item["timestamp"].isoformat() if hasattr(item["timestamp"], "isoformat") else str(item["timestamp"])
                        self._fallback.append(item)

            time.sleep(0.5)

        # Final drain on shutdown
        self._drain_remaining()

    def _flush_batch(self, batch: List[Dict[str, Any]]):
        """Write a batch of events to DB in a single transaction."""
        if not self._probe_db():
            # Fallback to in-memory
            with self._fallback_lock:
                for item in batch:
                    item["timestamp"] = item["timestamp"].isoformat() if hasattr(item["timestamp"], "isoformat") else str(item["timestamp"])
                    self._fallback.append(item)
            return

        try:
            SpindleEvent = self._get_model()
            session_scope = self._get_session_scope()
            with session_scope() as session:
                for item in batch:
                    event = SpindleEvent(**item)
                    session.add(event)
            logger.debug("[SpindleEventStore] Flushed %d events to DB", len(batch))
        except Exception as e:
            logger.error("[SpindleEventStore] Batch write failed: %s", e)
            self._db_available = False
            with self._fallback_lock:
                for item in batch:
                    item["timestamp"] = item["timestamp"].isoformat() if hasattr(item["timestamp"], "isoformat") else str(item["timestamp"])
                    self._fallback.append(item)

    def _drain_remaining(self):
        """Drain any remaining events on shutdown."""
        batch = []
        while not self._write_queue.empty():
            try:
                batch.append(self._write_queue.get_nowait())
            except queue.Empty:
                break
        if batch:
            self._flush_batch(batch)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_store: Optional[SpindleEventStore] = None
_store_lock = threading.Lock()


def get_event_store() -> SpindleEventStore:
    """Return (or create) the singleton SpindleEventStore."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = SpindleEventStore()
    return _store


# ---------------------------------------------------------------------------
# Bridge: cognitive event_bus  →  persistent store
# ---------------------------------------------------------------------------

def bridge_to_event_bus() -> None:
    """
    Subscribe to the cognitive event bus ``*`` topic and persist every
    event into the SpindleEventStore.

    Safe to call multiple times — only the first call registers the
    handler.
    """
    if getattr(bridge_to_event_bus, "_registered", False):
        return

    from backend.cognitive.event_bus import subscribe, Event

    store = get_event_store()

    def _persist(event: Event) -> None:
        try:
            store.append(
                topic=event.topic,
                source_type="system",
                payload=event.data,
                source=event.source,
            )
        except Exception as exc:
            logger.warning(
                "[SpindleEventStore] bridge persist failed for %s: %s",
                event.topic, exc,
            )

    subscribe("*", _persist)
    bridge_to_event_bus._registered = True  # type: ignore[attr-defined]
    logger.info("[SpindleEventStore] Bridge to cognitive event_bus registered.")
