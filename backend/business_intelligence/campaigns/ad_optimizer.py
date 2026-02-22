"""
Real-Time Ad Optimization Engine

Monitors campaign performance in real-time and makes optimization
decisions:
- Pause underperforming ads automatically
- Shift budget to winning variants
- Adjust bidding strategies based on CPA trends
- Detect audience fatigue
- Recommend new creative rotations

The key constraint: Grace can RECOMMEND changes but campaigns
that involve spending money require human approval to execute.
Grace can auto-pause (save money) but cannot auto-scale (spend money).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from business_intelligence.models.data_models import CampaignResult

logger = logging.getLogger(__name__)


@dataclass
class OptimizationAction:
    """A recommended optimization action."""
    action_type: str = ""  # pause, scale, adjust_bid, rotate_creative, retarget
    campaign_id: str = ""
    variant: str = ""
    platform: str = ""
    reason: str = ""
    expected_impact: str = ""
    requires_approval: bool = True
    urgency: str = "normal"  # low, normal, high, critical
    auto_executable: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceAlert:
    """An alert about campaign performance."""
    alert_type: str = ""  # budget_exceeded, cpa_spike, fatigue, opportunity
    severity: str = "info"  # info, warning, critical
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


CPA_SPIKE_THRESHOLD = 2.0  # 2x target CPA triggers alert
FATIGUE_THRESHOLD = 0.5  # 50% drop in CTR indicates fatigue
MIN_DATA_POINTS = 5  # minimum results before optimizing


class AdOptimizer:
    """Real-time ad campaign optimization engine."""

    def __init__(self, target_cpa: float = 5.0, max_daily_budget: float = 50.0):
        self.target_cpa = target_cpa
        self.max_daily_budget = max_daily_budget
        self.performance_history: List[CampaignResult] = []
        self.alerts: List[PerformanceAlert] = []
        self.actions_taken: List[OptimizationAction] = []

    async def analyze_performance(
        self,
        results: List[CampaignResult],
    ) -> Dict[str, Any]:
        """Analyze current campaign performance and generate recommendations."""
        self.performance_history.extend(results)

        analysis = {
            "timestamp": datetime.utcnow().isoformat(),
            "campaigns_analyzed": len(results),
            "alerts": [],
            "optimizations": [],
            "summary": {},
        }

        alerts = self._check_alerts(results)
        analysis["alerts"] = [
            {
                "type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
            }
            for a in alerts
        ]
        self.alerts.extend(alerts)

        optimizations = await self._generate_optimizations(results)
        analysis["optimizations"] = [
            {
                "action": o.action_type,
                "campaign": o.campaign_id,
                "variant": o.variant,
                "reason": o.reason,
                "impact": o.expected_impact,
                "requires_approval": o.requires_approval,
                "urgency": o.urgency,
            }
            for o in optimizations
        ]
        self.actions_taken.extend(optimizations)

        analysis["summary"] = self._build_summary(results)

        return analysis

    def _check_alerts(self, results: List[CampaignResult]) -> List[PerformanceAlert]:
        """Check for performance alerts."""
        alerts = []

        for r in results:
            if r.cost_per_acquisition > self.target_cpa * CPA_SPIKE_THRESHOLD and r.signups > 0:
                alerts.append(PerformanceAlert(
                    alert_type="cpa_spike",
                    severity="warning",
                    message=(
                        f"CPA spike on {r.platform}/{r.ab_variant}: "
                        f"{r.cost_per_acquisition:.2f} GBP "
                        f"(target: {self.target_cpa:.2f} GBP)"
                    ),
                    data={
                        "campaign": r.campaign_name,
                        "cpa": r.cost_per_acquisition,
                        "target": self.target_cpa,
                    },
                ))

            if r.ad_spend > self.max_daily_budget:
                alerts.append(PerformanceAlert(
                    alert_type="budget_exceeded",
                    severity="critical",
                    message=(
                        f"Daily budget exceeded on {r.platform}: "
                        f"{r.ad_spend:.2f} GBP (max: {self.max_daily_budget:.2f})"
                    ),
                    data={"spend": r.ad_spend, "max": self.max_daily_budget},
                ))

        variant_groups: Dict[str, List[CampaignResult]] = defaultdict(list)
        for r in results:
            key = f"{r.campaign_name}_{r.ab_variant}"
            variant_groups[key].append(r)

        for key, group in variant_groups.items():
            if len(group) >= 3:
                ctrs = [r.conversion_rate for r in group if r.conversion_rate > 0]
                if len(ctrs) >= 3:
                    recent_ctr = sum(ctrs[-2:]) / len(ctrs[-2:])
                    earlier_ctr = sum(ctrs[:2]) / len(ctrs[:2])
                    if earlier_ctr > 0 and recent_ctr < earlier_ctr * FATIGUE_THRESHOLD:
                        alerts.append(PerformanceAlert(
                            alert_type="fatigue",
                            severity="warning",
                            message=f"Audience fatigue detected for {key}. CTR dropped {((earlier_ctr - recent_ctr) / earlier_ctr * 100):.0f}%.",
                            data={"variant": key, "ctr_drop": earlier_ctr - recent_ctr},
                        ))

        return alerts

    async def _generate_optimizations(
        self, results: List[CampaignResult]
    ) -> List[OptimizationAction]:
        """Generate optimization actions based on performance data."""
        optimizations = []

        if len(results) < MIN_DATA_POINTS:
            return optimizations

        variant_performance: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"spend": 0, "signups": 0, "clicks": 0, "impressions": 0}
        )

        for r in results:
            key = r.ab_variant or "default"
            variant_performance[key]["spend"] += r.ad_spend
            variant_performance[key]["signups"] += r.signups
            variant_performance[key]["clicks"] += r.clicks
            variant_performance[key]["impressions"] += r.impressions

        variant_cpas = {}
        for variant, perf in variant_performance.items():
            if perf["signups"] > 0:
                variant_cpas[variant] = perf["spend"] / perf["signups"]
            elif perf["spend"] > 20:
                variant_cpas[variant] = float("inf")

        if len(variant_cpas) >= 2:
            best = min(variant_cpas, key=variant_cpas.get)
            worst = max(variant_cpas, key=variant_cpas.get)

            if variant_cpas[worst] > self.target_cpa * 2:
                optimizations.append(OptimizationAction(
                    action_type="pause",
                    variant=worst,
                    reason=f"CPA too high: {variant_cpas[worst]:.2f} GBP (target: {self.target_cpa:.2f})",
                    expected_impact=f"Save ~{variant_performance[worst]['spend']:.2f} GBP in wasted spend",
                    requires_approval=False,
                    auto_executable=True,
                    urgency="high",
                ))

            if variant_cpas[best] < self.target_cpa:
                optimizations.append(OptimizationAction(
                    action_type="scale",
                    variant=best,
                    reason=f"Best performer at {variant_cpas[best]:.2f} GBP CPA",
                    expected_impact="Increase signups while maintaining CPA",
                    requires_approval=True,
                    urgency="normal",
                ))

        platform_performance: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"spend": 0, "signups": 0}
        )
        for r in results:
            platform_performance[r.platform]["spend"] += r.ad_spend
            platform_performance[r.platform]["signups"] += r.signups

        for platform, perf in platform_performance.items():
            if perf["signups"] > 0:
                cpa = perf["spend"] / perf["signups"]
                if cpa < self.target_cpa * 0.5:
                    optimizations.append(OptimizationAction(
                        action_type="scale",
                        platform=platform,
                        reason=f"{platform} CPA ({cpa:.2f}) is well under target. Opportunity to scale.",
                        expected_impact="More signups at efficient cost",
                        requires_approval=True,
                        urgency="normal",
                    ))

        fatigue_alerts = [a for a in self.alerts if a.alert_type == "fatigue"]
        for alert in fatigue_alerts[-3:]:
            optimizations.append(OptimizationAction(
                action_type="rotate_creative",
                variant=alert.data.get("variant", ""),
                reason=alert.message,
                expected_impact="Restore CTR by showing fresh creative",
                requires_approval=True,
                urgency="high",
            ))

        return optimizations

    def _build_summary(self, results: List[CampaignResult]) -> Dict[str, Any]:
        """Build performance summary."""
        if not results:
            return {}

        total_spend = sum(r.ad_spend for r in results)
        total_signups = sum(r.signups for r in results)
        total_clicks = sum(r.clicks for r in results)
        total_impressions = sum(r.impressions for r in results)

        return {
            "total_spend": round(total_spend, 2),
            "total_signups": total_signups,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "overall_cpa": round(total_spend / total_signups, 2) if total_signups > 0 else 0,
            "overall_ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
            "cpa_vs_target": round(
                (total_spend / total_signups / self.target_cpa * 100) if total_signups > 0 else 0, 1
            ),
            "active_alerts": len([a for a in self.alerts if a.severity in ("warning", "critical")]),
            "pending_optimizations": len([
                a for a in self.actions_taken
                if a.requires_approval
            ]),
        }

    async def get_optimization_dashboard(self) -> Dict[str, Any]:
        """Get the current optimization state for the dashboard."""
        return {
            "target_cpa": self.target_cpa,
            "max_daily_budget": self.max_daily_budget,
            "total_results_tracked": len(self.performance_history),
            "active_alerts": [
                {"type": a.alert_type, "severity": a.severity, "message": a.message}
                for a in self.alerts[-10:]
            ],
            "recent_optimizations": [
                {
                    "action": o.action_type,
                    "variant": o.variant,
                    "reason": o.reason,
                    "urgency": o.urgency,
                    "approved": not o.requires_approval,
                }
                for o in self.actions_taken[-10:]
            ],
            "summary": self._build_summary(self.performance_history[-20:]),
        }
