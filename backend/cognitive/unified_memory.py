"""
Unified Memory — Single access point for ALL Grace memory systems.

This is the ONE entry point for memory. All other memory modules are internal;
callers should use only:

  from cognitive.unified_memory import get_unified_memory
  mem = get_unified_memory()

Unified memory combines:
  - Episodic Memory (concrete past experiences) — via cognitive.episodic_memory
  - Procedural Memory (learned skills) — via cognitive.procedural_memory
  - Learning Memory (training examples + patterns) — via cognitive.learning_memory
  - Memory Mesh (integration) — via cognitive.memory_mesh_integration when session+kb_path available
  - Magma (graph-based context) — via cognitive.magma_bridge
  - Flash Cache (external reference cache) — via cognitive.flash_cache

All storage and recall go through the same session-based backends (EpisodicBuffer,
LearningMemoryManager, ProceduralRepository) so there is one code path and one schema.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Default knowledge base path when not provided (e.g. for singleton)
_DEFAULT_KB_PATH = Path(os.environ.get("GRACE_KNOWLEDGE_BASE_PATH", "."))


def _get_session():
    """Get a DB session. Caller must close it (or use as context)."""
    try:
        from database.session import SessionLocal
        if SessionLocal is None:
            from database.session import initialize_session_factory
            initialize_session_factory()
            from database.session import SessionLocal as SL
            return SL()
        return SessionLocal()
    except Exception as e:
        logger.debug(f"Session not available: {e}")
        return None


def _coerce_dict(val) -> dict:
    """Coerce to dict for episode action/outcome."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            import json
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {"raw": val}
        except Exception:
            return {"raw": val}
    return {"raw": str(val)}


class UnifiedMemory:
    """Single interface for all Grace memory systems. Use get_unified_memory() to get the singleton."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "UnifiedMemory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Store (delegate to session-based backends) ────────────────────────

    def store_episode(
        self,
        problem: str,
        action: str,
        outcome: str,
        trust: float = 0.5,
        source: str = "system"
    ) -> bool:
        """Store a concrete experience. Uses EpisodicBuffer."""
        session = _get_session()
        if not session:
            return False
        try:
            from cognitive.episodic_memory import EpisodicBuffer
            buf = EpisodicBuffer(session)
            buf.record_episode(
                problem=problem[:2000] if problem else "",
                action=_coerce_dict(action),
                outcome=_coerce_dict(outcome),
                trust_score=trust,
                source=source or "system",
            )
            try:
                from cognitive.magma_bridge import store_decision
                store_decision(problem[:200], str(action)[:200], str(outcome)[:200])
            except Exception:
                pass
            return True
        except Exception as e:
            logger.debug(f"Store episode failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def store_learning(
        self,
        input_ctx: str,
        expected: str,
        actual: str = "",
        trust: float = 0.5,
        source: str = "system",
        example_type: str = "general"
    ) -> bool:
        """Store a learning example. Uses LearningMemoryManager."""
        session = _get_session()
        if not session:
            return False
        try:
            from cognitive.learning_memory import LearningMemoryManager
            mgr = LearningMemoryManager(session, _DEFAULT_KB_PATH)
            learning_data = {
                "context": _coerce_dict(input_ctx),
                "expected": _coerce_dict(expected),
                "actual": _coerce_dict(actual) if actual else _coerce_dict(expected),
            }
            mgr.ingest_learning_data(
                learning_type=example_type,
                learning_data=learning_data,
                source=source or "system",
            )
            return True
        except Exception as e:
            logger.debug(f"Store learning failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def store_procedure(
        self,
        name: str,
        goal: str,
        steps: str,
        trust: float = 0.5,
        proc_type: str = "general"
    ) -> bool:
        """Store a learned skill/procedure. Uses ProceduralRepository."""
        session = _get_session()
        if not session:
            return False
        try:
            from cognitive.procedural_memory import ProceduralRepository
            repo = ProceduralRepository(session)
            procedure = repo.create_procedure(
                goal=goal[:2000] if goal else name,
                action_sequence=[{"raw": steps[:5000] if steps else ""}],
                preconditions={},
                procedure_type=proc_type or "general",
            )
            procedure.trust_score = trust
            procedure.success_rate = 0.5
            session.commit()
            return True
        except Exception as e:
            logger.debug(f"Store procedure failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    # ── Recall (delegate to session-based backends) ────────────────────────

    def recall_episodes(
        self,
        query: str = "",
        limit: int = 10,
        min_trust: float = 0.0
    ) -> List[dict]:
        """Recall past experiences. Uses EpisodicBuffer when query given, else recent list."""
        session = _get_session()
        if not session:
            return []
        try:
            from cognitive.episodic_memory import EpisodicBuffer, Episode
            buf = EpisodicBuffer(session)
            if query and query.strip():
                episodes = buf.recall_similar(problem=query, k=limit, min_trust=min_trust)
            else:
                episodes = (
                    session.query(Episode)
                    .filter(Episode.trust_score >= min_trust)
                    .order_by(Episode.timestamp.desc())
                    .limit(limit)
                    .all()
                )
            out = []
            for e in episodes:
                ts = getattr(e, "timestamp", None) or getattr(e, "created_at", None)
                out.append({
                    "problem": getattr(e, "problem", "") or "",
                    "action": getattr(e, "action", "") or "",
                    "outcome": getattr(e, "outcome", "") or "",
                    "trust": getattr(e, "trust_score", 0) or 0,
                    "source": getattr(e, "source", "") or "",
                    "created_at": ts.isoformat() if hasattr(ts, "isoformat") and ts else None,
                })
            return out
        except Exception as e:
            logger.debug(f"Recall episodes failed: {e}")
            return []
        finally:
            session.close()

    def recall_learnings(
        self,
        query: str = "",
        limit: int = 10,
        min_trust: float = 0.0
    ) -> List[dict]:
        """Recall learning examples. Uses LearningExample via session."""
        session = _get_session()
        if not session:
            return []
        try:
            from cognitive.learning_memory import LearningExample
            q = session.query(LearningExample).filter(LearningExample.trust_score >= min_trust)
            if query and query.strip():
                q = q.filter(LearningExample.input_context.contains(query))
            rows = q.order_by(LearningExample.created_at.desc()).limit(limit).all()
            out = []
            for r in rows:
                ic = getattr(r, "input_context", "") or "{}"
                eo = getattr(r, "expected_output", "") or "{}"
                if isinstance(ic, str) and len(ic) > 300:
                    ic = ic[:300] + "..."
                if isinstance(eo, str) and len(eo) > 300:
                    eo = eo[:300] + "..."
                out.append({
                    "input": ic,
                    "expected": eo,
                    "trust": getattr(r, "trust_score", 0) or 0,
                    "source": getattr(r, "source", "") or "",
                    "type": getattr(r, "example_type", "") or "",
                })
            return out
        except Exception as e:
            logger.debug(f"Recall learnings failed: {e}")
            return []
        finally:
            session.close()

    def recall_procedures(
        self,
        query: str = "",
        limit: int = 10,
        min_trust: float = 0.0
    ) -> List[dict]:
        """Recall learned procedures. Uses Procedure via session."""
        session = _get_session()
        if not session:
            return []
        try:
            from cognitive.procedural_memory import Procedure
            q = session.query(Procedure).filter(Procedure.trust_score >= min_trust)
            if query and query.strip():
                q = q.filter(Procedure.goal.contains(query))
            rows = q.order_by(Procedure.trust_score.desc()).limit(limit).all()
            out = []
            for r in rows:
                steps = getattr(r, "steps", None)
                steps_str = steps[:300] if isinstance(steps, str) else (str(steps)[:300] if steps else "")
                out.append({
                    "name": getattr(r, "name", "") or "",
                    "goal": getattr(r, "goal", "") or "",
                    "steps": steps_str,
                    "trust": getattr(r, "trust_score", 0) or 0,
                    "success_rate": getattr(r, "success_rate", 0) or 0,
                    "usage_count": getattr(r, "usage_count", 0) or 0,
                })
            return out
        except Exception as e:
            logger.debug(f"Recall procedures failed: {e}")
            return []
        finally:
            session.close()

    def search_all(
        self,
        query: str,
        limit: int = 20,
        min_trust: float = 0.0
    ) -> Dict[str, Any]:
        """Search across ALL memory systems at once."""
        results = {
            "episodes": self.recall_episodes(query, limit=limit // 4 or 3, min_trust=min_trust),
            "learnings": self.recall_learnings(query, limit=limit // 4 or 3, min_trust=min_trust),
            "procedures": self.recall_procedures(query, limit=limit // 4 or 3, min_trust=min_trust),
        }

        try:
            from cognitive.magma_bridge import query_context
            ctx = query_context(query[:200])
            results["magma"] = [{"context": ctx[:500]}] if ctx else []
        except Exception:
            results["magma"] = []

        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.search(query, limit=limit // 4 or 3, min_trust=min_trust)
            results["flash_cache"] = [
                {
                    "name": r.get("source_name", ""),
                    "uri": r.get("source_uri", ""),
                    "trust": r.get("trust_score", 0),
                }
                for r in refs
            ]
        except Exception:
            results["flash_cache"] = []

        results["total"] = sum(
            len(v) for k, v in results.items()
            if k != "total" and isinstance(v, list)
        )
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across all memory systems (ORM-based counts)."""
        stats = {}
        session = _get_session()
        if session:
            try:
                from cognitive.learning_memory import LearningExample, LearningPattern
                from cognitive.episodic_memory import Episode
                from cognitive.procedural_memory import Procedure
                from sqlalchemy import func
                for name, model in [
                    ("learning_examples", LearningExample),
                    ("episodes", Episode),
                    ("procedures", Procedure),
                    ("learning_patterns", LearningPattern),
                ]:
                    try:
                        count = session.query(model).count()
                        if hasattr(model, "trust_score"):
                            avg = session.query(func.avg(model.trust_score)).scalar() or 0
                        else:
                            avg = 0
                        stats[name] = {"count": count, "avg_trust": round(float(avg), 3)}
                    except Exception:
                        stats[name] = {"count": 0, "avg_trust": 0}
            except Exception:
                pass
            finally:
                session.close()

        try:
            from cognitive.flash_cache import get_flash_cache
            fc_stats = get_flash_cache().stats()
            stats["flash_cache"] = {"entries": fc_stats.get("total_entries", 0)}
        except Exception:
            stats["flash_cache"] = {"entries": 0}

        try:
            from cognitive.magma_bridge import get_stats as magma_stats
            stats["magma"] = magma_stats()
        except Exception:
            stats["magma"] = {}

        return stats


def get_unified_memory() -> UnifiedMemory:
    """Return the singleton UnifiedMemory instance. This is THE entry point for all Grace memory."""
    return UnifiedMemory.get_instance()
