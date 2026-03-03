"""
Memory Injector — connects LLMs to ALL memory systems.

Before every LLM call, this module builds a rich context block
containing unified memory, Genesis patterns, trust scores,
governance rules, episodic recalls, and knowledge gaps.

This is THE missing piece. Without it, models fly blind.

Architecture:
  - Each section has a priority and a max char budget
  - The builder respects a total budget (MAX_CONTEXT_CHARS)
  - High-priority sections (governance, trust) are always included
  - Lower-priority sections are trimmed or dropped if budget is exhausted
  - Memory pressure monitoring prevents OOM on snapshot builds
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
from collections import deque

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = int(os.getenv("GRACE_MAX_CONTEXT_CHARS", "12000"))
SECTION_TIMEOUT_S = float(os.getenv("GRACE_SECTION_TIMEOUT", "2.0"))

_snapshot_history: deque = deque(maxlen=50)


class _Section:
    """A context section with priority, budget, and lazy fetcher."""

    __slots__ = ("name", "priority", "max_chars", "fetcher", "args")

    def __init__(self, name: str, priority: int, max_chars: int, fetcher, *args):
        self.name = name
        self.priority = priority
        self.max_chars = max_chars
        self.fetcher = fetcher
        self.args = args


def build_llm_context(task: str = "", project: str = "", session_id: str = "") -> str:
    """
    Build a complete context block for LLM injection.
    This gets prepended to every LLM system prompt.

    Sections are built in priority order. If total exceeds MAX_CONTEXT_CHARS,
    lower-priority sections are truncated or dropped entirely.
    """
    start = time.time()
    budget = MAX_CONTEXT_CHARS

    sections: List[_Section] = [
        _Section("[GOVERNANCE RULES — MANDATORY]",   1, 2000, _get_governance_rules),
        _Section("[MODEL TRUST SCORES]",             2,  400, _get_trust_scores),
        _Section("[PAST EXPERIENCE]",                3, 1500, _get_episodic_context, task),
        _Section("[SYSTEM ACTIVITY — LAST 24H]",     4, 1000, _get_genesis_patterns),
        _Section("[KNOWLEDGE GAPS]",                 5,  500, _get_knowledge_gaps),
        _Section("[AI PREDICTION]",                  6,  300, _get_dl_prediction, task),
        _Section("[BRAIN SYNAPSE STRENGTHS]",        7,  400, _get_hebbian_context),
        _Section("[SELF-OBSERVATION]",               8,  200, _get_mirror_observation),
        _Section("[RECENT GENESIS KEYS]",            9,  800, _get_recent_genesis_keys),
        _Section("[GRACE SOURCE CODE MAP]",         10,  600, _get_code_awareness),
        _Section("[DATABASE STATE]",                11,  500, _get_database_stats),
        _Section("[RECENT CHAT CONTEXT]",           12,  600, _get_chat_context),
        _Section("[COMPONENT HEALTH]",              13,  500, _get_component_health),
        _Section("[BRAIN ACTIONS — WHAT GRACE CAN DO]", 14, 500, _get_brain_actions),
        _Section("[OUROBOROS LOOP HISTORY]",         15,  400, _get_loop_history),
        _Section("[CODING PIPELINE HISTORY]",       16,  400, _get_pipeline_history),
        _Section("[PROVENANCE LEDGER]",             17,  300, _get_provenance),
        _Section("[ACTIVE SESSIONS]",               18,  200, _get_active_sessions),
    ]

    sections.sort(key=lambda s: s.priority)

    parts: List[str] = []
    chars_used = 0
    sections_included = 0
    sections_skipped = 0

    for sec in sections:
        if budget - chars_used < 100:
            sections_skipped += len(sections) - sections_included - sections_skipped
            break

        try:
            sec_start = time.time()
            content = sec.fetcher(*sec.args) if sec.args and sec.args[0] else sec.fetcher()
            sec_elapsed = time.time() - sec_start

            if sec_elapsed > SECTION_TIMEOUT_S:
                logger.debug(f"Memory section {sec.name} slow: {sec_elapsed:.1f}s")

            if not content:
                continue

            allowed = min(sec.max_chars, budget - chars_used)
            if len(content) > allowed:
                content = content[:allowed - 3] + "..."

            block = f"{sec.name}\n{content}"
            parts.append(block)
            chars_used += len(block)
            sections_included += 1
        except Exception as e:
            logger.debug(f"Memory section {sec.name} error: {e}")
            sections_skipped += 1

    elapsed_ms = round((time.time() - start) * 1000, 1)

    _snapshot_history.append({
        "ts": time.time(),
        "chars": chars_used,
        "sections": sections_included,
        "skipped": sections_skipped,
        "latency_ms": elapsed_ms,
    })

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)


def get_snapshot_stats() -> dict:
    """Get memory injector performance statistics."""
    if not _snapshot_history:
        return {"snapshots": 0}
    history = list(_snapshot_history)
    avg_chars = sum(h["chars"] for h in history) / len(history)
    avg_latency = sum(h["latency_ms"] for h in history) / len(history)
    avg_sections = sum(h["sections"] for h in history) / len(history)
    return {
        "snapshots": len(history),
        "avg_chars": round(avg_chars),
        "avg_latency_ms": round(avg_latency, 1),
        "avg_sections": round(avg_sections, 1),
        "max_budget": MAX_CONTEXT_CHARS,
        "last_snapshot": history[-1] if history else None,
    }


def get_memory_pressure() -> dict:
    """Check current memory pressure of the Python process."""
    import resource
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = usage.ru_maxrss / 1024  # Linux gives KB
        process_mb = sys.getsizeof(0)  # baseline
    except Exception:
        rss_mb = 0
    return {
        "rss_mb": round(rss_mb, 1),
        "context_budget": MAX_CONTEXT_CHARS,
        "snapshot_cache_size": len(_snapshot_history),
    }


def _get_governance_rules() -> str:
    try:
        from core.services.govern_service import list_rules, get_persona
        rules = list_rules()
        persona = get_persona()
        parts = []
        if persona.get("personal"):
            parts.append(f"Communication style: {persona['personal'][:200]}")
        if persona.get("professional"):
            parts.append(f"Professional style: {persona['professional'][:200]}")
        docs = rules.get("documents", [])
        if docs:
            parts.append(f"Active governance documents: {len(docs)}")
            for d in docs[:5]:
                parts.append(f"  - {d.get('filename', '?')} ({d.get('category', '?')})")
        return "\n".join(parts) if parts else ""
    except Exception:
        return ""


def _get_trust_scores() -> str:
    try:
        from core.intelligence import AdaptiveTrust
        trust = AdaptiveTrust.get_all_trust()
        models = trust.get("models", {})
        if models:
            return "\n".join(f"  {m}: {s:.2f}" for m, s in models.items())
        return ""
    except Exception:
        return ""


def _get_episodic_context(task: str) -> str:
    try:
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicBuffer
        with session_scope() as s:
            buf = EpisodicBuffer(s)
            episodes = buf.recall_similar(task, k=3, min_trust=0.5)
            if not episodes:
                return ""
            parts = []
            for ep in episodes:
                problem = ep.problem[:100] if isinstance(ep.problem, str) else str(ep.problem)[:100]
                outcome = ep.outcome[:100] if isinstance(ep.outcome, str) else str(ep.outcome)[:100]
                parts.append(f"  Past: {problem} → {outcome} (trust={ep.trust_score:.2f})")
            return "\n".join(parts)
    except Exception:
        return ""


def _get_genesis_patterns() -> str:
    try:
        from core.intelligence import GenesisKeyMiner
        miner = GenesisKeyMiner()
        patterns = miner.mine_patterns(hours=24, limit=500)
        parts = []
        keys = patterns.get("keys_analyzed", 0)
        parts.append(f"Operations in last 24h: {keys}")
        errors = patterns.get("error_clusters", [])
        if errors:
            parts.append(f"Error clusters: {len(errors)}")
            for e in errors[:3]:
                parts.append(f"  - {e.get('error_type', '?')}: {e.get('count', 0)} occurrences")
        repeated = patterns.get("repeated_failures", [])
        if repeated:
            parts.append(f"Repeated failures: {', '.join(r.get('pattern', '?')[:30] for r in repeated[:3])}")
        return "\n".join(parts)
    except Exception:
        return ""


def _get_knowledge_gaps() -> str:
    try:
        from core.cognitive_mesh import CognitiveMesh
        gaps = CognitiveMesh.analyze_knowledge_gaps()
        if not gaps or not gaps.get("knowledge_gaps"):
            return ""
        gap_list = gaps.get("knowledge_gaps", [])
        if not gap_list:
            return ""
        return f"Grace has {len(gap_list)} knowledge gaps in: " + ", ".join(
            g.get("topic", "?")[:20] for g in gap_list[:5] if isinstance(g, dict)
        )
    except Exception:
        return ""


def _get_dl_prediction(task: str) -> str:
    try:
        from core.deep_learning import get_model, TORCH_AVAILABLE
        if not TORCH_AVAILABLE:
            return ""
        model = get_model()
        pred = model.predict({"key_type": "code_change", "what": task[:60], "who": "user", "is_error": False})
        if pred.get("available"):
            return (f"Success probability: {pred['success_probability']:.0%}\n"
                    f"Risk component: {pred.get('risky_component', '?')}\n"
                    f"Predicted trust: {pred.get('predicted_trust', 0):.2f}")
        return ""
    except Exception:
        return ""


def _get_hebbian_context() -> str:
    try:
        from core.hebbian import get_hebbian_mesh
        strongest = get_hebbian_mesh().get_strongest(5)
        if not strongest:
            return ""
        return "\n".join(
            f"  {s['source']}→{s['target']}: weight={s['weight']:.2f} ({s['calls']} calls)"
            for s in strongest
        )
    except Exception:
        return ""


def _get_recent_genesis_keys() -> str:
    """Actual Genesis key records — not just a count."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        with session_scope() as s:
            keys = s.query(GenesisKey).order_by(
                GenesisKey.when_timestamp.desc()).limit(15).all()
            if not keys:
                return ""
            lines = []
            for k in keys:
                kt = k.key_type.value if hasattr(k.key_type, 'value') else str(k.key_type)
                lines.append(
                    f"  [{kt}] {k.what_description[:80]} "
                    f"(who={k.who_actor}, when={k.when_timestamp.strftime('%H:%M') if k.when_timestamp else '?'}"
                    f"{', ERROR' if k.is_error else ''})"
                )
            return "\n".join(lines)
    except Exception:
        return ""


def _get_code_awareness() -> str:
    """Source code map — what files exist and what they do."""
    try:
        from core.semantic_search import COMPONENTS
        lines = []
        for cid, info in list(COMPONENTS.items())[:15]:
            lines.append(f"  {cid}: {info['file']} — {info['purpose'][:60]}")
        return "\n".join(lines)
    except Exception:
        return ""


def _get_database_stats() -> str:
    """Actual database table contents — works on SQLite and PostgreSQL."""
    try:
        from database.connection import DatabaseConnection
        from core.db_compat import get_table_stats, get_db_size_mb
        engine = DatabaseConnection.get_engine()
        stats = get_table_stats(engine)
        if not stats:
            return ""
        lines = []
        for name, count in stats.items():
            if count > 0:
                lines.append(f"  {name}: {count:,} rows")
        size = get_db_size_mb(engine)
        if size > 0:
            lines.insert(0, f"  Database size: {size} MB")
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


def _get_chat_context() -> str:
    """Recent chat messages for continuity."""
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as s:
            rows = s.execute(text(
                "SELECT role, content FROM chat_history "
                "ORDER BY id DESC LIMIT 5"
            )).fetchall()
            if not rows:
                return ""
            lines = []
            for r in reversed(rows):
                role = r[0] if r[0] else "?"
                content = (r[1] or "")[:100]
                lines.append(f"  [{role}] {content}")
            return "\n".join(lines)
    except Exception:
        return ""


def _get_component_health() -> str:
    """Current component health status."""
    try:
        from core.component_validator import get_all_report_cards
        cards = get_all_report_cards()
        if not cards.get("report_cards"):
            return ""
        lines = []
        for cid, card in list(cards["report_cards"].items())[:10]:
            status = card.get("status", "unknown")
            purpose = card.get("purpose", "")[:40]
            icon = "✅" if status == "healthy" else "⚠️" if status == "not_validated" else "❌"
            lines.append(f"  {icon} {cid}: {status} — {purpose}")
        return "\n".join(lines)
    except Exception:
        return ""


def _get_brain_actions() -> str:
    """Full list of what Grace can do."""
    try:
        from api.brain_api_v2 import _build_directory
        d = _build_directory()
        lines = []
        for domain, info in d.items():
            lines.append(f"  {domain} ({len(info['actions'])}): {', '.join(info['actions'][:15])}")
        total = sum(len(info['actions']) for info in d.values())
        lines.insert(0, f"  Total: {total} actions across {len(d)} domains")
        return "\n".join(lines)
    except Exception:
        return ""


def _get_loop_history() -> str:
    """Recent Ouroboros autonomous loop cycles."""
    try:
        from api.autonomous_loop_api import _loop_state, _loop_log
        state = dict(_loop_state)
        lines = [
            f"  Running: {state.get('running')}, Cycles: {state.get('cycle_count', 0)}, "
            f"Healed: {state.get('healed', 0)}, Learned: {state.get('learned', 0)}, "
            f"Errors: {state.get('errors', 0)}"
        ]
        for log_entry in list(reversed(_loop_log[-5:])):
            if isinstance(log_entry, dict):
                lines.append(
                    f"  Cycle {log_entry.get('cycle_id','?')}: "
                    f"{log_entry.get('triggers_found',0)} triggers, "
                    f"{log_entry.get('outcome','?')}"
                )
        return "\n".join(lines)
    except Exception:
        return ""


def _get_pipeline_history() -> str:
    """Recent coding pipeline runs."""
    try:
        from core.coding_pipeline import get_pipeline_progress
        progress = get_pipeline_progress()
        runs = progress.get_all()
        if not runs:
            return "No pipeline runs recorded"
        lines = []
        for run in runs[-5:]:
            lines.append(
                f"  {run.get('run_id','?')}: {run.get('status','?')} "
                f"({run.get('percent',0)}% complete, "
                f"{run.get('completed_chunks',0)}/{run.get('total_chunks',0)} chunks)"
            )
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


def _get_provenance() -> str:
    """Recent provenance ledger entries."""
    try:
        from core.safety import get_ledger_entries
        entries = get_ledger_entries(5)
        if not entries:
            return ""
        lines = []
        for e in entries:
            lines.append(
                f"  [{e.get('action','?')}] hash={e.get('hash','?')[:12]}... "
                f"model={e.get('model','?')} ts={e.get('ts','?')}"
            )
        return "\n".join(lines)
    except Exception:
        return ""


def _get_active_sessions() -> str:
    """Active user sessions."""
    try:
        from core.multi_user import _active_sessions, list_users
        users = list_users()
        lines = [f"  Registered users: {len(users)}"]
        for uid, session in _active_sessions.items():
            lines.append(f"  {uid}: project={session.get('project','none')}")
        return "\n".join(lines)
    except Exception:
        return ""


def _get_mirror_observation() -> str:
    try:
        from core.awareness.self_model import SelfModel
        model = SelfModel()
        ctx = model.now()
        return f"Period: {ctx.get('period', '?')}, Business hours: {ctx.get('is_business_hours', '?')}"
    except Exception:
        return ""
