"""
Reporting Engine — Holistic Daily/Weekly System Intelligence Reports

Generates comprehensive reports covering every domain in Grace:
  - Trust scores: up/down trends per component
  - Self-learning: what was learned, knowledge expansion metrics
  - Self-healing: what broke, how it was fixed, recovery times
  - Coding agent: generation success rates, quality trends
  - Governance: compliance status, rule enforcement stats
  - LLM usage: costs, latency, error rates by provider
  - Memory: growth across all 5 memory systems
  - Consensus: roundtable runs, agreement rates
  - Genesis Keys: activity volumes, error patterns
  - Integration health: component citizenship, connectivity

Reports are:
  - Generated daily (auto) or on-demand
  - Stored as files in data/reports/ for history
  - Written in NLP (natural language) for human consumption
  - Include what improved, what degraded, problems, solutions, and next steps
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"


def _get_db():
    try:
        from database.session import SessionLocal, initialize_session_factory
        if SessionLocal is None:
            initialize_session_factory()
            from database.session import SessionLocal as SL
            return SL()
        return SessionLocal()
    except Exception:
        return None


def generate_report(period: str = "daily", days: int = 1) -> Dict[str, Any]:
    """
    Generate a holistic system report.
    period: 'daily', 'weekly', 'monthly'
    days: how many days to look back
    """
    if period == "weekly":
        days = 7
    elif period == "monthly":
        days = 30

    cutoff = datetime.utcnow() - timedelta(days=days)
    report = {
        "report_id": f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "period": period,
        "days_covered": days,
        "generated_at": datetime.utcnow().isoformat(),
        "cutoff": cutoff.isoformat(),
        "sections": {},
        "summary": {},
        "nlp_report": "",
    }

    # Collect data from all domains
    report["sections"]["trust"] = _report_trust()
    report["sections"]["learning"] = _report_learning(cutoff)
    report["sections"]["healing"] = _report_healing(cutoff)
    report["sections"]["llm_usage"] = _report_llm_usage(cutoff)
    report["sections"]["genesis_keys"] = _report_genesis_keys(cutoff)
    report["sections"]["memory"] = _report_memory()
    report["sections"]["integration"] = _report_integration()
    report["sections"]["documents"] = _report_documents(cutoff)
    report["sections"]["flash_cache"] = _report_flash_cache()
    report["sections"]["consensus"] = _report_consensus()

    # Build summary
    report["summary"] = _build_summary(report["sections"])

    # Generate NLP report
    report["nlp_report"] = _generate_nlp_report(report)

    # Save report
    _save_report(report)

    return report


def _report_trust() -> Dict[str, Any]:
    """Trust Engine metrics."""
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        dashboard = te.get_dashboard()
        return {
            "overall_trust": dashboard.get("overall_trust", 0),
            "component_count": dashboard.get("component_count", 0),
            "components": dashboard.get("components", {}),
            "status": "active",
        }
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


def _report_learning(cutoff: datetime) -> Dict[str, Any]:
    """Learning system metrics."""
    db = _get_db()
    if not db:
        return {"status": "db_unavailable"}
    try:
        from sqlalchemy import text
        total = db.execute(text("SELECT COUNT(*) FROM learning_examples")).scalar() or 0
        recent = db.execute(text(
            "SELECT COUNT(*) FROM learning_examples WHERE created_at >= :c"
        ), {"c": cutoff}).scalar() or 0
        avg_trust = db.execute(text("SELECT AVG(trust_score) FROM learning_examples")).scalar() or 0
        patterns = db.execute(text("SELECT COUNT(*) FROM learning_patterns")).scalar() or 0
        procedures = db.execute(text("SELECT COUNT(*) FROM procedures")).scalar() or 0
        episodes = db.execute(text("SELECT COUNT(*) FROM episodes")).scalar() or 0

        return {
            "total_examples": total,
            "new_examples": recent,
            "avg_trust": round(avg_trust, 3),
            "patterns": patterns,
            "procedures": procedures,
            "episodes": episodes,
            "status": "active",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def _report_healing(cutoff: datetime) -> Dict[str, Any]:
    """Immune system / healing metrics."""
    try:
        from cognitive.immune_system import GraceImmuneSystem
        immune = GraceImmuneSystem()
        playbook = immune.get_healing_playbook()
        total = len(playbook)
        successful = sum(1 for r in playbook if r.get("success"))
        return {
            "total_healing_actions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": round(successful / total, 3) if total else 0,
            "status": "active",
        }
    except Exception:
        return {"status": "unavailable", "total_healing_actions": 0}


def _report_llm_usage(cutoff: datetime) -> Dict[str, Any]:
    """LLM usage and costs."""
    try:
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        stats = get_llm_usage_stats()
        return {
            "total_calls": stats.get("total_calls", 0),
            "total_errors": stats.get("total_errors", 0),
            "avg_latency_ms": stats.get("avg_latency_ms", 0),
            "error_rate": stats.get("error_rate", 0),
            "by_provider": stats.get("by_provider", {}),
            "status": "active",
        }
    except Exception:
        return {"status": "unavailable"}


def _report_genesis_keys(cutoff: datetime) -> Dict[str, Any]:
    """Genesis Key activity."""
    db = _get_db()
    if not db:
        return {"status": "db_unavailable"}
    try:
        from sqlalchemy import text
        total = db.execute(text("SELECT COUNT(*) FROM genesis_key")).scalar() or 0
        recent = db.execute(text(
            "SELECT COUNT(*) FROM genesis_key WHERE when_timestamp >= :c"
        ), {"c": cutoff}).scalar() or 0

        by_type = {}
        try:
            rows = db.execute(text(
                "SELECT key_type, COUNT(*) FROM genesis_key WHERE when_timestamp >= :c GROUP BY key_type"
            ), {"c": cutoff}).fetchall()
            by_type = {r[0]: r[1] for r in rows}
        except Exception:
            pass

        errors = 0
        try:
            errors = db.execute(text(
                "SELECT COUNT(*) FROM genesis_key WHERE is_error = 1 AND when_timestamp >= :c"
            ), {"c": cutoff}).scalar() or 0
        except Exception:
            pass

        return {
            "total_keys": total,
            "recent_keys": recent,
            "errors": errors,
            "by_type": by_type,
            "status": "active",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def _report_memory() -> Dict[str, Any]:
    """Unified memory statistics."""
    try:
        from cognitive.unified_memory import get_unified_memory
        return get_unified_memory().get_stats()
    except Exception:
        return {"status": "unavailable"}


def _report_integration() -> Dict[str, Any]:
    """Integration health."""
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        health = orch.check_integration_health()
        return {
            "total_components": health.get("total", 0),
            "healthy": health.get("healthy", 0),
            "broken": health.get("broken", 0),
            "health_percent": health.get("health_percent", 0),
            "status": "active",
        }
    except Exception:
        return {"status": "unavailable"}


def _report_documents(cutoff: datetime) -> Dict[str, Any]:
    """Document library metrics."""
    db = _get_db()
    if not db:
        return {"status": "db_unavailable"}
    try:
        from sqlalchemy import text
        total = db.execute(text("SELECT COUNT(*) FROM documents")).scalar() or 0
        recent = db.execute(text(
            "SELECT COUNT(*) FROM documents WHERE created_at >= :c"
        ), {"c": cutoff}).scalar() or 0
        total_size = db.execute(text("SELECT SUM(file_size) FROM documents")).scalar() or 0
        return {
            "total_documents": total,
            "new_documents": recent,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
            "status": "active",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def _report_flash_cache() -> Dict[str, Any]:
    """Flash cache statistics."""
    try:
        from cognitive.flash_cache import get_flash_cache
        return get_flash_cache().stats()
    except Exception:
        return {"status": "unavailable"}


def _report_consensus() -> Dict[str, Any]:
    """Consensus engine status."""
    try:
        from cognitive.consensus_engine import get_available_models, get_batch_queue
        models = get_available_models()
        queue = get_batch_queue()
        return {
            "available_models": len([m for m in models if m["available"]]),
            "total_models": len(models),
            "batch_queue_pending": sum(1 for q in queue if q.get("status") == "queued"),
            "batch_queue_completed": sum(1 for q in queue if q.get("status") == "completed"),
            "status": "active",
        }
    except Exception:
        return {"status": "unavailable"}


def _build_summary(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Build high-level summary from all sections."""
    improvements = []
    problems = []
    metrics = {}

    trust = sections.get("trust", {})
    if isinstance(trust.get("overall_trust"), (int, float)):
        metrics["trust_score"] = trust["overall_trust"]
        if trust["overall_trust"] >= 70:
            improvements.append("Trust score is healthy")
        else:
            problems.append(f"Trust score is low: {trust['overall_trust']}")

    learning = sections.get("learning", {})
    if learning.get("new_examples", 0) > 0:
        improvements.append(f"Learned {learning['new_examples']} new examples")
    metrics["total_knowledge"] = learning.get("total_examples", 0)

    healing = sections.get("healing", {})
    if healing.get("success_rate", 0) >= 0.8:
        improvements.append(f"Healing success rate: {healing['success_rate']*100:.0f}%")
    elif healing.get("total_healing_actions", 0) > 0:
        problems.append(f"Healing success rate: {healing.get('success_rate', 0)*100:.0f}%")

    llm = sections.get("llm_usage", {})
    if llm.get("error_rate", 0) > 0.1:
        problems.append(f"LLM error rate: {llm['error_rate']*100:.1f}%")
    metrics["llm_calls"] = llm.get("total_calls", 0)

    integration = sections.get("integration", {})
    metrics["integration_health"] = integration.get("health_percent", 0)
    if integration.get("broken", 0) > 0:
        problems.append(f"{integration['broken']} broken integrations")

    genesis = sections.get("genesis_keys", {})
    metrics["genesis_keys_today"] = genesis.get("recent_keys", 0)
    if genesis.get("errors", 0) > 5:
        problems.append(f"{genesis['errors']} genesis key errors")

    return {
        "improvements": improvements,
        "problems": problems,
        "metrics": metrics,
        "health_score": _calculate_health_score(sections),
    }


def _calculate_health_score(sections: Dict[str, Any]) -> float:
    """Calculate overall system health 0-100."""
    score = 50.0  # Base

    trust = sections.get("trust", {})
    if isinstance(trust.get("overall_trust"), (int, float)):
        score += (trust["overall_trust"] - 50) * 0.2

    integration = sections.get("integration", {})
    score += (integration.get("health_percent", 50) - 50) * 0.3

    healing = sections.get("healing", {})
    if healing.get("total_healing_actions", 0) > 0:
        score += (healing.get("success_rate", 0.5) - 0.5) * 20

    llm = sections.get("llm_usage", {})
    score -= llm.get("error_rate", 0) * 30

    return max(0, min(100, round(score, 1)))


def _generate_nlp_report(report: Dict[str, Any]) -> str:
    """Generate natural language report for human consumption."""
    summary = report["summary"]
    sections = report["sections"]
    period = report["period"]
    health = summary.get("health_score", 50)

    lines = []
    lines.append(f"# Grace System Report — {period.title()}")
    lines.append(f"Generated: {report['generated_at'][:19]}")
    lines.append(f"Overall Health Score: {health}/100\n")

    # What's going well
    if summary.get("improvements"):
        lines.append("## What's Improved")
        for imp in summary["improvements"]:
            lines.append(f"  + {imp}")
        lines.append("")

    # Problems
    if summary.get("problems"):
        lines.append("## Problems & Areas for Attention")
        for prob in summary["problems"]:
            lines.append(f"  - {prob}")
        lines.append("")

    # Key metrics
    lines.append("## Key Metrics")
    for key, val in summary.get("metrics", {}).items():
        nice_key = key.replace("_", " ").title()
        lines.append(f"  {nice_key}: {val}")
    lines.append("")

    # Domain details
    learning = sections.get("learning", {})
    if learning.get("status") == "active":
        lines.append("## Learning & Knowledge")
        lines.append(f"  Total knowledge base: {learning.get('total_examples', 0)} examples")
        lines.append(f"  New this period: {learning.get('new_examples', 0)}")
        lines.append(f"  Patterns extracted: {learning.get('patterns', 0)}")
        lines.append(f"  Procedures learned: {learning.get('procedures', 0)}")
        lines.append(f"  Episodic memories: {learning.get('episodes', 0)}")
        lines.append("")

    llm = sections.get("llm_usage", {})
    if llm.get("status") == "active":
        lines.append("## LLM Usage")
        lines.append(f"  Total calls: {llm.get('total_calls', 0)}")
        lines.append(f"  Avg latency: {llm.get('avg_latency_ms', 0):.0f}ms")
        lines.append(f"  Error rate: {llm.get('error_rate', 0)*100:.1f}%")
        for prov, stats in llm.get("by_provider", {}).items():
            lines.append(f"    {prov}: {stats.get('calls', 0)} calls, {stats.get('errors', 0)} errors")
        lines.append("")

    integration = sections.get("integration", {})
    if integration.get("status") == "active":
        lines.append("## Integration Health")
        lines.append(f"  Components: {integration.get('healthy', 0)}/{integration.get('total_components', 0)} healthy")
        lines.append(f"  Health: {integration.get('health_percent', 0)}%")
        lines.append("")

    genesis = sections.get("genesis_keys", {})
    if genesis.get("status") == "active":
        lines.append("## Activity (Genesis Keys)")
        lines.append(f"  Total keys: {genesis.get('total_keys', 0)}")
        lines.append(f"  This period: {genesis.get('recent_keys', 0)}")
        lines.append(f"  Errors: {genesis.get('errors', 0)}")
        lines.append("")

    lines.append("---")
    lines.append("Report generated by Grace Reporting Engine")

    return "\n".join(lines)


def _save_report(report: Dict[str, Any]):
    """Save report to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rid = report["report_id"]

    # Save JSON
    (REPORTS_DIR / f"{rid}.json").write_text(json.dumps(report, indent=2, default=str))

    # Save NLP text
    (REPORTS_DIR / f"{rid}.txt").write_text(report["nlp_report"])

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Report generated: {report['period']} (health: {report['summary'].get('health_score', 0)})",
            how="reporting_engine.generate_report",
            output_data={
                "report_id": rid,
                "health_score": report["summary"].get("health_score", 0),
                "improvements": len(report["summary"].get("improvements", [])),
                "problems": len(report["summary"].get("problems", [])),
            },
            tags=["report", report["period"]],
        )
    except Exception:
        pass


def list_reports(limit: int = 20) -> List[Dict[str, Any]]:
    """List available reports."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for f in sorted(REPORTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(f.read_text())
            reports.append({
                "report_id": data.get("report_id"),
                "period": data.get("period"),
                "generated_at": data.get("generated_at"),
                "health_score": data.get("summary", {}).get("health_score", 0),
                "improvements": len(data.get("summary", {}).get("improvements", [])),
                "problems": len(data.get("summary", {}).get("problems", [])),
            })
        except Exception:
            pass
    return reports


def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific report."""
    path = REPORTS_DIR / f"{report_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None
