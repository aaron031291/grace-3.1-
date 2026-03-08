"""
Central KPI recording for brains and components.

Every brain action and key component action should flow through here so that:
- Governance engine gets record_kpi (for compliance/dashboard)
- ML KPI tracker gets increment_kpi (for trust scores and health)

All recording is best-effort: failures are logged and never raise.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def record_brain_kpi(brain: str, action: str, ok: bool) -> None:
    """
    Record a brain action to both governance KPIs and ML KPI tracker.

    Call after every brain request (HTTP or call_brain) so KPIs stay in sync.
    """
    try:
        from core.governance_engine import record_kpi
        record_kpi("brain", f"{brain}/{action}", passed=ok)
    except Exception as e:
        logger.debug("KPI recorder: governance record_kpi failed: %s", e)

    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if tracker:
            comp = f"brain_{brain}"
            tracker.increment_kpi(comp, "requests", 1.0)
            tracker.increment_kpi(comp, "successes" if ok else "failures", 1.0)
    except Exception as e:
        logger.debug("KPI recorder: ML tracker increment failed: %s", e)


def record_component_kpi(component: str, metric: str, value: float = 1.0,
                         success: Optional[bool] = None) -> None:
    """
    Record a component-level KPI (e.g. retrieval, ingestion, learning).

    Use for components that are not exclusively invoked via brain so they
    still contribute to system trust and dashboards.
    """
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if tracker:
            tracker.increment_kpi(component, metric, value)
            if success is not None:
                tracker.increment_kpi(component, "successes" if success else "failures", 1.0)
    except Exception as e:
        logger.debug("KPI recorder: component increment failed: %s", e)
