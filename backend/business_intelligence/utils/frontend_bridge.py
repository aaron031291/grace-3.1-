"""
Frontend Bridge

Transforms BI engine outputs into frontend-ready data structures.
Every BI module produces raw data -- this layer formats it for
GRACE's React frontend with widget-ready payloads.

This ensures the frontend can render BI dashboards without
complex data transformation on the client side.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BIFrontendBridge:
    """Transforms BI data into frontend-consumable formats."""

    async def get_dashboard_data(self, bi_system) -> Dict[str, Any]:
        """Get complete BI dashboard data for the frontend.

        Returns a single payload with all widgets the frontend needs.
        """
        status = bi_system.get_status()
        engine_status = await bi_system.intelligence_engine.get_status() if bi_system.intelligence_engine else {}

        waitlist_stats = None
        if bi_system.waitlist_manager:
            ws = await bi_system.waitlist_manager.get_stats()
            waitlist_stats = {
                "active": ws.active_signups,
                "target": ws.validation_threshold,
                "progress_pct": round(ws.active_signups / max(ws.validation_threshold, 1) * 100, 1),
                "reached": ws.validation_reached,
                "growth_rate": ws.growth_rate,
                "by_platform": ws.by_source_platform,
                "days_to_target": ws.days_to_threshold,
            }

        campaign_summary = None
        if bi_system.campaign_manager:
            cs = await bi_system.campaign_manager.get_campaign_summary()
            campaign_summary = cs

        optimization = None
        if bi_system.ad_optimizer:
            optimization = await bi_system.ad_optimizer.get_optimization_dashboard()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "widgets": {
                "system_status": {
                    "type": "status_card",
                    "phase": engine_status.get("phase", "initializing"),
                    "total_cycles": engine_status.get("total_cycles", 0),
                    "active_connectors": status.get("active_connectors", 0),
                    "total_connectors": status.get("total_connectors", 0),
                },
                "data_collection": {
                    "type": "metric_card",
                    "data_points": engine_status.get("data_points", 0),
                    "pain_points": engine_status.get("pain_points", 0),
                    "opportunities": engine_status.get("opportunities", 0),
                    "trend_signals": engine_status.get("trend_signals", 0),
                },
                "connectors": {
                    "type": "connector_grid",
                    "connectors": engine_status.get("connectors", {}),
                },
                "waitlist": {
                    "type": "progress_bar",
                    "data": waitlist_stats,
                },
                "campaigns": {
                    "type": "campaign_table",
                    "data": campaign_summary,
                },
                "opportunities": {
                    "type": "opportunity_list",
                    "data": engine_status.get("top_opportunities", []),
                },
                "ad_optimization": {
                    "type": "optimization_panel",
                    "data": optimization,
                },
                "grace_notes": {
                    "type": "activity_feed",
                    "notes": engine_status.get("grace_notes", []),
                },
                "summary": {
                    "type": "text_block",
                    "text": engine_status.get("summary", "System initializing..."),
                },
            },
        }

    async def get_research_dashboard(self, report) -> Dict[str, Any]:
        """Format a research report for frontend rendering."""
        return {
            "widgets": {
                "header": {
                    "type": "research_header",
                    "niche": report.niche,
                    "confidence": report.grace_confidence,
                    "status": report.status,
                    "data_points": report.total_data_points,
                    "sources": report.data_sources_used,
                },
                "pain_points": {
                    "type": "pain_point_chart",
                    "clusters": report.pain_point_clusters[:5],
                    "total": len(report.pain_points),
                },
                "competitors": {
                    "type": "competitor_table",
                    "landscape": report.competitor_landscape,
                    "count": report.competitors_found,
                },
                "opportunities": {
                    "type": "opportunity_cards",
                    "items": [
                        {
                            "title": o.title,
                            "type": o.opportunity_type.value,
                            "score": o.opportunity_score,
                            "confidence": o.confidence_score,
                        }
                        for o in report.opportunities[:5]
                    ],
                },
                "grace_assessment": {
                    "type": "assessment_card",
                    "confidence": report.grace_confidence,
                    "summary": report.grace_summary,
                    "concerns": report.grace_concerns,
                    "next_actions": report.next_actions,
                },
                "recommendations": {
                    "type": "action_list",
                    "items": report.recommendations,
                },
            },
        }

    async def get_financial_dashboard(self, plan) -> Dict[str, Any]:
        """Format financial plan for frontend charts."""
        projection = plan.projection
        return {
            "widgets": {
                "unit_economics": {
                    "type": "metric_grid",
                    "metrics": {
                        "Price": f"£{plan.unit_economics.price:.2f}",
                        "CAC": f"£{plan.unit_economics.cac:.2f}",
                        "LTV": f"£{plan.unit_economics.ltv:.2f}",
                        "LTV:CAC": f"{plan.unit_economics.ltv_cac_ratio:.1f}x",
                        "Margin": f"{plan.unit_economics.gross_margin:.0f}%",
                        "Viable": plan.unit_economics.viable,
                    },
                },
                "revenue_chart": {
                    "type": "line_chart",
                    "x": projection.months if projection else [],
                    "series": {
                        "MRR": projection.mrr if projection else [],
                        "Cumulative Revenue": projection.cumulative_revenue if projection else [],
                        "Cumulative Cost": projection.cumulative_cost if projection else [],
                    },
                    "break_even": projection.break_even_month if projection else None,
                },
                "scenarios": {
                    "type": "scenario_comparison",
                    "scenarios": {
                        name: {
                            "year_1_revenue": f"£{s.year_1_revenue:,.0f}",
                            "year_1_profit": f"£{s.year_1_profit:,.0f}",
                            "break_even_month": s.break_even_month,
                            "final_mrr": s.mrr[-1] if s.mrr else 0,
                        }
                        for name, s in plan.scenarios.items()
                    },
                },
                "risks": {"type": "risk_list", "items": plan.risks},
                "recommendations": {"type": "action_list", "items": plan.recommendations},
            },
        }

    async def get_loop_dashboard(self, loop_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format recursive loop results for frontend."""
        return {
            "widgets": {
                "cycle_info": {
                    "type": "cycle_header",
                    "cycle_number": loop_results.get("cycle_number", 0),
                    "loops_executed": loop_results.get("loops_executed", 0),
                    "confidence": loop_results.get("overall_confidence", 0),
                },
                "loop_results": {
                    "type": "loop_accordion",
                    "loops": {
                        name: {
                            "insights": result.get("insights", []),
                            "refinements": result.get("refinements", []),
                        }
                        for name, result in loop_results.get("loop_results", {}).items()
                    },
                },
                "cross_loop": {
                    "type": "insight_list",
                    "items": loop_results.get("cross_loop_insights", []),
                },
                "knowledge_growth": {
                    "type": "metric_card",
                    "cumulative_insights": loop_results.get("cumulative_insights", 0),
                    "knowledge_nodes": loop_results.get("knowledge_nodes", 0),
                },
                "confidence_chart": {
                    "type": "sparkline",
                    "data": loop_results.get("confidence_trend", []),
                },
            },
        }
