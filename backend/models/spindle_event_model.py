"""
SQLAlchemy model for persistent Spindle event storage.

Append-only event log backed by PostgreSQL. Every Spindle event
(SAT checks, healing actions, document processing, etc.) is
written once and never updated or deleted.
"""

from sqlalchemy import Column, BigInteger, DateTime, Integer, String, JSON, Index
from sqlalchemy.sql import func

from backend.database.base import BaseModel


class SpindleEvent(BaseModel):
    """Append-only Spindle event record."""
    __tablename__ = "spindle_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id = Column(BigInteger, nullable=False, unique=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_type = Column(String(50), nullable=False)   # "user_text", "document", "system", "healing"
    topic = Column(String(200), nullable=False)
    input_hash = Column(String(64))                     # SHA-256 of input for dedup
    spindle_mask = Column(String(100))                  # hex of the 256-bit mask
    proof_hash = Column(String(16))                     # links to SpindleProof.constraint_hash
    result = Column(String(20))                         # "SAT", "UNSAT", "EXECUTED", "FAILED"
    payload = Column(JSON)                              # full event data
    source = Column(String(100))                        # component that emitted

    __table_args__ = (
        Index("idx_spindle_events_topic", "topic"),
        Index("idx_spindle_events_source_type", "source_type"),
        Index("idx_spindle_events_timestamp", "timestamp"),
        Index("idx_spindle_events_sequence", "sequence_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<SpindleEvent(id={self.id}, seq={self.sequence_id}, "
            f"topic={self.topic}, result={self.result})>"
        )
