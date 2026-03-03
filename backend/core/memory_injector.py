"""
Memory Injector — connects LLMs to ALL memory systems.

Before every LLM call, this module builds a rich context block
containing unified memory, Genesis patterns, trust scores,
governance rules, episodic recalls, and knowledge gaps.

This is THE missing piece. Without it, models fly blind.
"""

import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 12000


def build_llm_context(task: str = "", project: str = "", session_id: str = "") -> str:
    """
    Build a complete context block for LLM injection.
    This gets prepended to every LLM system prompt.
    """
    parts = []
    char_budget = MAX_CONTEXT_CHARS

    # 1. Governance rules (highest priority — these are LAW)
    rules = _get_governance_rules()
    if rules:
        parts.append(f"[GOVERNANCE RULES — MANDATORY]\n{rules[:2000]}")
        char_budget -= min(len(rules), 2000)

    # 2. Trust scores (which models are reliable right now)
    trust = _get_trust_scores()
    if trust:
        parts.append(f"[MODEL TRUST SCORES]\n{trust}")
        char_budget -= len(trust)

    # 3. Episodic memory (similar past problems and what worked)
    if task:
        episodes = _get_episodic_context(task)
        if episodes:
            parts.append(f"[PAST EXPERIENCE]\n{episodes[:1500]}")
            char_budget -= min(len(episodes), 1500)

    # 4. Genesis key patterns (what happened in last 24h)
    patterns = _get_genesis_patterns()
    if patterns:
        parts.append(f"[SYSTEM ACTIVITY — LAST 24H]\n{patterns[:1000]}")
        char_budget -= min(len(patterns), 1000)

    # 5. Knowledge gaps (what Grace doesn't know yet)
    gaps = _get_knowledge_gaps()
    if gaps:
        parts.append(f"[KNOWLEDGE GAPS]\n{gaps[:500]}")
        char_budget -= min(len(gaps), 500)

    # 6. DL model prediction (success probability for this task)
    if task:
        prediction = _get_dl_prediction(task)
        if prediction:
            parts.append(f"[AI PREDICTION]\n{prediction}")

    # 7. Hebbian weights (strongest brain connections)
    hebbian = _get_hebbian_context()
    if hebbian:
        parts.append(f"[BRAIN SYNAPSE STRENGTHS]\n{hebbian}")

    # 8. Self-mirror observation
    mirror = _get_mirror_observation()
    if mirror:
        parts.append(f"[SELF-OBSERVATION]\n{mirror}")

    # 9. Recent Genesis keys (actual records, not just count)
    recent_keys = _get_recent_genesis_keys()
    if recent_keys:
        parts.append(f"[RECENT GENESIS KEYS]\n{recent_keys}")

    # 10. Source code awareness (component registry)
    code_awareness = _get_code_awareness()
    if code_awareness:
        parts.append(f"[GRACE SOURCE CODE MAP]\n{code_awareness}")

    # 11. Database table stats
    db_stats = _get_database_stats()
    if db_stats:
        parts.append(f"[DATABASE STATE]\n{db_stats}")

    # 12. Chat history context
    chat_ctx = _get_chat_context()
    if chat_ctx:
        parts.append(f"[RECENT CHAT CONTEXT]\n{chat_ctx}")

    # 13. Component health
    health = _get_component_health()
    if health:
        parts.append(f"[COMPONENT HEALTH]\n{health}")

    # 14. Brain action list (what Grace can do)
    actions = _get_brain_actions()
    if actions:
        parts.append(f"[BRAIN ACTIONS — WHAT GRACE CAN DO]\n{actions}")

    # 15. Ouroboros loop history
    loop_history = _get_loop_history()
    if loop_history:
        parts.append(f"[OUROBOROS LOOP HISTORY]\n{loop_history}")

    # 16. Pipeline run history
    pipeline_history = _get_pipeline_history()
    if pipeline_history:
        parts.append(f"[CODING PIPELINE HISTORY]\n{pipeline_history}")

    # 17. Provenance ledger
    provenance = _get_provenance()
    if provenance:
        parts.append(f"[PROVENANCE LEDGER]\n{provenance}")

    # 18. Active sessions
    sessions = _get_active_sessions()
    if sessions:
        parts.append(f"[ACTIVE SESSIONS]\n{sessions}")

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)


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
    """Actual database table contents."""
    try:
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).parent.parent / "data" / "grace.db"
        if not db_path.exists():
            return ""
        conn = sqlite3.connect(str(db_path), timeout=3)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        lines = []
        for t in tables:
            name = t[0]
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if count > 0:
                lines.append(f"  {name}: {count:,} rows")
        conn.close()
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
