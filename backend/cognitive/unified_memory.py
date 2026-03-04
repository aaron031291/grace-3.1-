"""
Unified Memory Interface — Single access point for all memory systems.

Combines:
  - Episodic Memory (concrete past experiences)
  - Procedural Memory (learned skills)
  - Learning Memory (training examples + patterns)
  - Memory Mesh (integration layer)
  - Magma Memory (graph-based: semantic, temporal, causal)
  - Flash Cache (external reference cache)

Every memory system in Grace is accessible through this single interface.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _get_db():
    try:
        from database.session import SessionLocal
        if SessionLocal is None:
            from database.session import initialize_session_factory
            initialize_session_factory()
            from database.session import SessionLocal as SL
            return SL()
        return SessionLocal()
    except Exception:
        return None


class UnifiedMemory:
    """Single interface for all Grace memory systems."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "UnifiedMemory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Store Operations ──────────────────────────────────────────────

    def store_episode(self, problem: str, action: str, outcome: str,
                      trust: float = 0.5, source: str = "system") -> bool:
        """Store a concrete experience."""
        db = _get_db()
        if not db:
            return False
        try:
            from sqlalchemy import text
            db.execute(text(
                "INSERT INTO episodes (problem, action, outcome, trust_score, source, created_at, updated_at) "
                "VALUES (:p, :a, :o, :t, :s, :now, :now)"
            ), {"p": problem[:2000], "a": action[:2000], "o": outcome[:2000],
                "t": trust, "s": source, "now": datetime.now(timezone.utc)})
            db.commit()

            try:
                from cognitive.magma_bridge import store_decision
                store_decision(problem[:200], action[:200], outcome[:200])
            except Exception:
                pass

            return True
        except Exception as e:
            logger.debug(f"Store episode failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def store_learning(self, input_ctx: str, expected: str, actual: str = "",
                       trust: float = 0.5, source: str = "system",
                       example_type: str = "general") -> bool:
        """Store a learning example."""
        db = _get_db()
        if not db:
            return False
        try:
            from sqlalchemy import text
            db.execute(text(
                "INSERT INTO learning_examples (example_type, input_context, expected_output, actual_output, "
                "trust_score, source, source_reliability, content_quality, consensus_score, recency_score, "
                "created_at, updated_at) VALUES (:et, :ic, :eo, :ao, :ts, :src, :sr, :cq, :cs, :rs, :now, :now)"
            ), {"et": example_type, "ic": input_ctx[:5000], "eo": expected[:5000],
                "ao": actual[:5000], "ts": trust, "src": source,
                "sr": 0.5, "cq": 0.5, "cs": 0.5, "rs": 1.0,
                "now": datetime.now(timezone.utc)})
            db.commit()
            return True
        except Exception as e:
            logger.debug(f"Store learning failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def store_procedure(self, name: str, goal: str, steps: str,
                        trust: float = 0.5, proc_type: str = "general") -> bool:
        """Store a learned skill/procedure."""
        db = _get_db()
        if not db:
            return False
        try:
            from sqlalchemy import text
            db.execute(text(
                "INSERT INTO procedures (name, goal, procedure_type, steps, trust_score, "
                "success_rate, usage_count, created_at, updated_at) "
                "VALUES (:n, :g, :pt, :s, :ts, :sr, 0, :now, :now)"
            ), {"n": name, "g": goal[:2000], "pt": proc_type, "s": steps[:5000],
                "ts": trust, "sr": 0.5, "now": datetime.now(timezone.utc)})
            db.commit()
            return True
        except Exception as e:
            logger.debug(f"Store procedure failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    # ── Query Operations ──────────────────────────────────────────────

    def recall_episodes(self, query: str = "", limit: int = 10,
                        min_trust: float = 0.0) -> List[dict]:
        """Recall past experiences, optionally filtered by keyword."""
        db = _get_db()
        if not db:
            return []
        try:
            from sqlalchemy import text
            if query:
                rows = db.execute(text(
                    "SELECT problem, action, outcome, trust_score, source, created_at "
                    "FROM episodes WHERE trust_score >= :mt AND "
                    "(problem LIKE :q OR action LIKE :q OR outcome LIKE :q) "
                    "ORDER BY trust_score DESC LIMIT :lim"
                ), {"mt": min_trust, "q": f"%{query}%", "lim": limit}).fetchall()
            else:
                rows = db.execute(text(
                    "SELECT problem, action, outcome, trust_score, source, created_at "
                    "FROM episodes WHERE trust_score >= :mt "
                    "ORDER BY created_at DESC LIMIT :lim"
                ), {"mt": min_trust, "lim": limit}).fetchall()
            return [
                {"problem": r[0], "action": r[1], "outcome": r[2],
                 "trust": r[3], "source": r[4],
                 "created_at": r[5].isoformat() if r[5] else None}
                for r in rows
            ]
        except Exception:
            return []
        finally:
            db.close()

    def recall_learnings(self, query: str = "", limit: int = 10,
                         min_trust: float = 0.0) -> List[dict]:
        """Recall learning examples."""
        db = _get_db()
        if not db:
            return []
        try:
            from sqlalchemy import text
            if query:
                rows = db.execute(text(
                    "SELECT input_context, expected_output, trust_score, source, example_type "
                    "FROM learning_examples WHERE trust_score >= :mt AND "
                    "input_context LIKE :q ORDER BY trust_score DESC LIMIT :lim"
                ), {"mt": min_trust, "q": f"%{query}%", "lim": limit}).fetchall()
            else:
                rows = db.execute(text(
                    "SELECT input_context, expected_output, trust_score, source, example_type "
                    "FROM learning_examples WHERE trust_score >= :mt "
                    "ORDER BY created_at DESC LIMIT :lim"
                ), {"mt": min_trust, "lim": limit}).fetchall()
            return [
                {"input": (r[0] or "")[:300], "expected": (r[1] or "")[:300],
                 "trust": r[2], "source": r[3], "type": r[4]}
                for r in rows
            ]
        except Exception:
            return []
        finally:
            db.close()

    def recall_procedures(self, query: str = "", limit: int = 10,
                          min_trust: float = 0.0) -> List[dict]:
        """Recall learned procedures/skills."""
        db = _get_db()
        if not db:
            return []
        try:
            from sqlalchemy import text
            rows = db.execute(text(
                "SELECT name, goal, steps, trust_score, success_rate, usage_count "
                "FROM procedures WHERE trust_score >= :mt "
                "ORDER BY trust_score DESC LIMIT :lim"
            ), {"mt": min_trust, "lim": limit}).fetchall()
            return [
                {"name": r[0], "goal": r[1], "steps": (r[2] or "")[:300],
                 "trust": r[3], "success_rate": r[4], "usage_count": r[5]}
                for r in rows
            ]
        except Exception:
            return []
        finally:
            db.close()

    def search_all(self, query: str, limit: int = 20,
                   min_trust: float = 0.0) -> Dict[str, List[dict]]:
        """Search across ALL memory systems at once."""
        results = {
            "episodes": self.recall_episodes(query, limit=limit // 4 or 3, min_trust=min_trust),
            "learnings": self.recall_learnings(query, limit=limit // 4 or 3, min_trust=min_trust),
            "procedures": self.recall_procedures(query, limit=limit // 4 or 3, min_trust=min_trust),
        }

        # Magma graph memory
        results["magma"] = []
        try:
            from cognitive.magma_bridge import query_context
            ctx = query_context(query[:200])
            if ctx:
                results["magma"] = [{"context": ctx[:500]}]
        except Exception:
            pass

        # Flash cache references
        try:
            from cognitive.flash_cache import get_flash_cache
            fc = get_flash_cache()
            refs = fc.search(query, limit=limit // 4 or 3, min_trust=min_trust)
            results["flash_cache"] = [
                {"name": r.get("source_name", ""), "uri": r.get("source_uri", ""),
                 "trust": r.get("trust_score", 0)}
                for r in refs
            ]
        except Exception:
            results["flash_cache"] = []

        results["total"] = sum(len(v) for v in results.values())
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across all memory systems."""
        stats = {}
        db = _get_db()
        if db:
            try:
                from sqlalchemy import text
                for table in ["learning_examples", "episodes", "procedures", "learning_patterns"]:
                    try:
                        count = db.execute(text(f"SELECT COUNT(*) FROM [{table}]")).scalar() or 0
                        avg_trust = db.execute(text(f"SELECT AVG(trust_score) FROM [{table}]")).scalar() or 0
                        stats[table] = {"count": count, "avg_trust": round(avg_trust, 3)}
                    except Exception:
                        stats[table] = {"count": 0, "avg_trust": 0}
            except Exception:
                pass
            finally:
                db.close()

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
    return UnifiedMemory.get_instance()
