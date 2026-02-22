"""
Financial Modeling Module

Projects revenue, unit economics, break-even timelines, and
profitability from BI data. Turns opportunity scores into
actual financial projections.

Inputs:
- Product pricing (from ideation engine)
- Customer acquisition cost (from campaign data)
- Market size estimates (from research)
- Conversion rates (from validation data)
- Competitor pricing (from competitor analysis)
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    MarketOpportunity, ProductConcept, CampaignResult, CustomerArchetype, ProductType,
)

logger = logging.getLogger(__name__)


@dataclass
class UnitEconomics:
    """Unit economics for a product."""
    product_name: str = ""
    price: float = 0.0
    cac: float = 0.0  # customer acquisition cost
    ltv: float = 0.0  # lifetime value
    ltv_cac_ratio: float = 0.0
    gross_margin: float = 0.0
    payback_period_months: float = 0.0
    monthly_churn_rate: float = 0.05
    viable: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class RevenueProjection:
    """Revenue projection over time."""
    months: List[int] = field(default_factory=list)
    mrr: List[float] = field(default_factory=list)  # monthly recurring revenue
    arr: List[float] = field(default_factory=list)  # annual run rate
    customers: List[int] = field(default_factory=list)
    cumulative_revenue: List[float] = field(default_factory=list)
    cumulative_cost: List[float] = field(default_factory=list)
    break_even_month: Optional[int] = None
    year_1_revenue: float = 0.0
    year_1_profit: float = 0.0


@dataclass
class FinancialPlan:
    """Complete financial plan for a product concept."""
    product: str = ""
    unit_economics: Optional[UnitEconomics] = None
    projection: Optional[RevenueProjection] = None
    scenarios: Dict[str, RevenueProjection] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


RECURRING_TYPES = {ProductType.SAAS, ProductType.COMMUNITY_MEMBERSHIP, ProductType.AI_AUTOMATION}
COGS_ESTIMATES = {
    ProductType.SAAS: 0.15,
    ProductType.ONLINE_COURSE: 0.05,
    ProductType.EBOOK_PDF: 0.02,
    ProductType.AI_AUTOMATION: 0.20,
    ProductType.TEMPLATE_TOOLKIT: 0.03,
    ProductType.COMMUNITY_MEMBERSHIP: 0.10,
    ProductType.PHYSICAL_PRODUCT: 0.40,
    ProductType.CONSULTING_SERVICE: 0.30,
}


class FinancialModeler:
    """Projects financial outcomes from BI data."""

    async def calculate_unit_economics(
        self, product: ProductConcept,
        campaign_results: Optional[List[CampaignResult]] = None,
        avg_retention_months: float = 12.0,
    ) -> UnitEconomics:
        """Calculate unit economics for a product concept."""
        price = product.estimated_price
        is_recurring = product.product_type in RECURRING_TYPES
        cogs_rate = COGS_ESTIMATES.get(product.product_type, 0.10)

        cac = 5.0
        if campaign_results:
            total_spend = sum(cr.ad_spend for cr in campaign_results)
            total_signups = sum(cr.signups for cr in campaign_results)
            if total_signups > 0:
                cac = total_spend / total_signups

        if is_recurring:
            monthly_churn = 1 / avg_retention_months
            ltv = price * avg_retention_months * (1 - cogs_rate)
        else:
            ltv = price * (1 - cogs_rate)
            monthly_churn = 0.0
            repeat_purchase_factor = 1.3
            ltv *= repeat_purchase_factor

        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        gross_margin = (1 - cogs_rate) * 100

        if is_recurring and cac > 0:
            monthly_revenue = price * (1 - cogs_rate)
            payback = cac / monthly_revenue if monthly_revenue > 0 else 0
        else:
            payback = 0

        viable = ltv_cac_ratio >= 3.0
        notes = []
        if ltv_cac_ratio >= 5:
            notes.append("Excellent unit economics. Scale aggressively.")
        elif ltv_cac_ratio >= 3:
            notes.append("Healthy unit economics. Proceed with confidence.")
        elif ltv_cac_ratio >= 1:
            notes.append("Marginal. Optimize CAC or increase price before scaling.")
        else:
            notes.append("Unsustainable. Must reduce CAC or significantly increase LTV.")

        if cac > price:
            notes.append(f"WARNING: CAC ({cac:.2f}) exceeds price ({price:.2f}). Unprofitable on first sale.")

        return UnitEconomics(
            product_name=product.name, price=price, cac=round(cac, 2),
            ltv=round(ltv, 2), ltv_cac_ratio=round(ltv_cac_ratio, 2),
            gross_margin=round(gross_margin, 1), payback_period_months=round(payback, 1),
            monthly_churn_rate=round(monthly_churn, 3), viable=viable, notes=notes,
        )

    async def project_revenue(
        self, product: ProductConcept, unit_economics: UnitEconomics,
        monthly_new_customers: int = 50, months: int = 12,
        monthly_ad_budget: float = 500.0,
    ) -> RevenueProjection:
        """Project revenue over time."""
        is_recurring = product.product_type in RECURRING_TYPES
        projection = RevenueProjection()
        active_customers = 0
        cum_revenue = 0.0
        cum_cost = 0.0

        for month in range(1, months + 1):
            active_customers += monthly_new_customers
            if is_recurring:
                churned = int(active_customers * unit_economics.monthly_churn_rate)
                active_customers -= churned

            if is_recurring:
                monthly_revenue = active_customers * product.estimated_price
            else:
                monthly_revenue = monthly_new_customers * product.estimated_price

            monthly_cost = monthly_ad_budget + (monthly_new_customers * unit_economics.cac * 0.5)
            cogs = monthly_revenue * COGS_ESTIMATES.get(product.product_type, 0.10)
            monthly_cost += cogs

            cum_revenue += monthly_revenue
            cum_cost += monthly_cost

            projection.months.append(month)
            projection.mrr.append(round(monthly_revenue, 2))
            projection.arr.append(round(monthly_revenue * 12, 2))
            projection.customers.append(active_customers)
            projection.cumulative_revenue.append(round(cum_revenue, 2))
            projection.cumulative_cost.append(round(cum_cost, 2))

            if projection.break_even_month is None and cum_revenue > cum_cost:
                projection.break_even_month = month

        projection.year_1_revenue = cum_revenue
        projection.year_1_profit = cum_revenue - cum_cost

        return projection

    async def build_financial_plan(
        self, product: ProductConcept,
        campaign_results: Optional[List[CampaignResult]] = None,
        monthly_budget: float = 500.0,
    ) -> FinancialPlan:
        """Build a complete financial plan with scenarios."""
        ue = await self.calculate_unit_economics(product, campaign_results)

        base = await self.project_revenue(product, ue, monthly_new_customers=50, monthly_ad_budget=monthly_budget)
        conservative = await self.project_revenue(product, ue, monthly_new_customers=20, monthly_ad_budget=monthly_budget * 0.5)
        optimistic = await self.project_revenue(product, ue, monthly_new_customers=100, monthly_ad_budget=monthly_budget * 1.5)

        recs = []
        if ue.viable:
            recs.append(f"Unit economics are viable (LTV:CAC = {ue.ltv_cac_ratio:.1f}x). Proceed to build.")
        else:
            recs.append(f"Unit economics need work (LTV:CAC = {ue.ltv_cac_ratio:.1f}x). Target 3x+.")
            if ue.cac > ue.price * 0.3:
                recs.append("Reduce CAC: optimize ad targeting, improve organic channels, build referral program.")
            recs.append("Increase LTV: add upsells, reduce churn, increase pricing.")

        if base.break_even_month:
            recs.append(f"Break-even projected at month {base.break_even_month}.")
        else:
            recs.append("No break-even within 12 months in base case. Review pricing or costs.")

        risks = []
        if ue.cac > 15:
            risks.append("High CAC risk: customer acquisition expensive")
        if ue.monthly_churn_rate > 0.10:
            risks.append("High churn risk: review product-market fit")
        if not campaign_results:
            risks.append("CAC is estimated, not measured. Run ads to validate.")

        return FinancialPlan(
            product=product.name, unit_economics=ue, projection=base,
            scenarios={"conservative": conservative, "base": base, "optimistic": optimistic},
            recommendations=recs, risks=risks,
        )
