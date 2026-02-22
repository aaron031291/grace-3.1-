"""
Business Intelligence API Routes

FastAPI routes exposing the BI system capabilities to the GRACE frontend
and external consumers. This is the interface between Grace's intelligence
engine and the outside world.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from business_intelligence.utils.initializer import get_bi_system

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bi", tags=["Business Intelligence"])


# ==================== Request/Response Models ====================

class ResearchRequest(BaseModel):
    niche: str = Field(..., description="Market niche to research")
    keywords: List[str] = Field(..., description="Keywords for data collection")
    depth: str = Field("standard", description="Research depth: quick, standard, deep")


class IntelligenceCycleRequest(BaseModel):
    niches: List[str] = Field(..., description="Niches to investigate")
    keywords: Dict[str, List[str]] = Field(..., description="Keywords per niche")
    force_collection: bool = Field(False, description="Force data collection even if recent data exists")


class WaitlistSignupRequest(BaseModel):
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(None, description="Name (optional)")
    source_campaign: str = Field("", description="Source campaign identifier")
    source_platform: str = Field("", description="Source platform (facebook, tiktok, etc)")
    interests: List[str] = Field(default_factory=list, description="Areas of interest")
    consent_given: bool = Field(False, description="Explicit consent for data collection")
    consent_text: str = Field("", description="Consent statement shown to user")


class CampaignPlanRequest(BaseModel):
    name: str = Field(..., description="Campaign name")
    platforms: List[str] = Field(..., description="Target platforms")
    daily_budget: float = Field(10.0, description="Daily budget in GBP")
    total_budget: float = Field(100.0, description="Total budget in GBP")
    duration_days: int = Field(7, description="Campaign duration in days")
    landing_page_url: str = Field("", description="Landing page URL")


class CampaignResultRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    platform: str = Field(..., description="Platform name")
    impressions: int = Field(0)
    clicks: int = Field(0)
    conversions: int = Field(0)
    signups: int = Field(0)
    ad_spend: float = Field(0.0)
    ad_copy_variant: str = Field("")


class AdCopyRequest(BaseModel):
    opportunity_id: Optional[str] = Field(None, description="Opportunity ID to generate copy for")
    niche: str = Field(..., description="Target niche")
    pain_points: List[str] = Field(default_factory=list, description="Pain points to address")
    platform: str = Field("facebook", description="Target platform")
    num_variants: int = Field(3, description="Number of A/B variants")


class KnowledgeRequest(BaseModel):
    topic: str = Field(..., description="Topic Grace needs more knowledge about")
    reason: str = Field(..., description="Why this knowledge is needed")


class NicheSearchRequest(BaseModel):
    keywords: List[str] = Field(..., description="Keywords to search for niches")
    max_results: int = Field(10, description="Maximum niches to return")


# ==================== System Status ====================

@router.get("/status")
async def get_bi_status():
    """Get the current status of the BI system."""
    try:
        bi = get_bi_system()
        system_status = bi.get_status()

        if bi.intelligence_engine:
            engine_status = await bi.intelligence_engine.get_status()
            system_status["intelligence"] = engine_status

        if bi.waitlist_manager:
            waitlist_stats = await bi.waitlist_manager.get_stats()
            system_status["waitlist"] = {
                "total_signups": waitlist_stats.active_signups,
                "validation_reached": waitlist_stats.validation_reached,
                "threshold": waitlist_stats.validation_threshold,
            }

        return system_status

    except Exception as e:
        logger.error(f"Failed to get BI status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors")
async def get_connector_status():
    """Get status of all data connectors."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        return ConnectorRegistry.health_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Intelligence Engine ====================

@router.post("/intelligence/cycle")
async def run_intelligence_cycle(
    request: IntelligenceCycleRequest,
    background_tasks: BackgroundTasks,
):
    """Run a full intelligence collection and analysis cycle."""
    try:
        bi = get_bi_system()
        snapshot = await bi.intelligence_engine.run_intelligence_cycle(
            niches=request.niches,
            keywords=request.keywords,
            force_collection=request.force_collection,
        )

        if bi.data_store:
            await bi.data_store.save_snapshot(snapshot)

        return {
            "status": "completed",
            "phase": snapshot.phase,
            "data_points": snapshot.data_points_collected,
            "niches": snapshot.active_niches,
            "opportunities": len(snapshot.top_opportunities),
            "pain_points": len(snapshot.top_pain_points),
            "summary": snapshot.summary,
            "recommendations": snapshot.recommendations,
        }

    except Exception as e:
        logger.error(f"Intelligence cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/snapshot")
async def get_latest_snapshot():
    """Get the latest intelligence snapshot."""
    try:
        bi = get_bi_system()
        if bi.intelligence_engine:
            return await bi.intelligence_engine.get_status()
        return {"message": "Intelligence engine not initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intelligence/knowledge-request")
async def request_knowledge(request: KnowledgeRequest):
    """Grace requests additional knowledge or documents."""
    try:
        bi = get_bi_system()
        result = await bi.intelligence_engine.add_knowledge_request(
            topic=request.topic,
            reason=request.reason,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Market Research ====================

@router.post("/research")
async def run_market_research(request: ResearchRequest):
    """Run market research on a specific niche."""
    try:
        bi = get_bi_system()
        orchestrator = bi.intelligence_engine.research_orchestrator

        report = await orchestrator.run_research(
            niche=request.niche,
            keywords=request.keywords,
            depth=request.depth,
        )

        if bi.data_store and report.pain_points:
            await bi.data_store.save_pain_points(
                report.pain_points, request.niche
            )

        return {
            "niche": report.niche,
            "status": report.status,
            "data_points": report.total_data_points,
            "sources_used": report.data_sources_used,
            "pain_points": len(report.pain_points),
            "pain_point_clusters": report.pain_point_clusters[:5],
            "competitors_found": report.competitors_found,
            "competitor_landscape": report.competitor_landscape,
            "opportunities": [
                {
                    "title": o.title,
                    "type": o.opportunity_type.value,
                    "score": o.opportunity_score,
                    "confidence": o.confidence_score,
                }
                for o in report.opportunities[:5]
            ],
            "recommendations": report.recommendations,
            "grace_confidence": report.grace_confidence,
            "grace_summary": report.grace_summary,
            "grace_concerns": report.grace_concerns,
            "next_actions": report.next_actions,
        }

    except Exception as e:
        logger.error(f"Market research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/quick-scan")
async def quick_scan(request: ResearchRequest):
    """Run a quick market scan (faster, less thorough)."""
    try:
        bi = get_bi_system()
        orchestrator = bi.intelligence_engine.research_orchestrator
        result = await orchestrator.quick_scan(
            niche=request.niche,
            keywords=request.keywords,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Niche Discovery ====================

@router.post("/niches/find")
async def find_niches(request: NicheSearchRequest):
    """Find profitable niches based on keywords."""
    try:
        bi = get_bi_system()
        from business_intelligence.connectors.base import ConnectorRegistry

        data_points = await ConnectorRegistry.collect_all(
            keywords=request.keywords
        )

        from business_intelligence.market_research.pain_point_engine import PainPointEngine
        pp_engine = PainPointEngine()
        pain_points = await pp_engine.extract_pain_points(data_points)

        niches = await bi.niche_finder.find_niches(
            data_points=data_points,
            pain_points=pain_points,
        )

        return {
            "keywords_searched": request.keywords,
            "data_points_collected": len(data_points),
            "pain_points_found": len(pain_points),
            "niches": [
                {
                    "name": n.name,
                    "score": n.overall_score,
                    "pain_point_density": n.pain_point_density,
                    "competition": n.competition_level,
                    "trend": n.trend_direction,
                    "grace_advantage": n.grace_advantage,
                    "recommended_products": [p.value for p in n.recommended_products],
                    "rationale": n.rationale,
                }
                for n in niches[:request.max_results]
            ],
        }

    except Exception as e:
        logger.error(f"Niche finding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Campaign Management ====================

@router.post("/campaigns/plan")
async def create_campaign_plan(request: CampaignPlanRequest):
    """Create a campaign plan (requires human approval)."""
    try:
        bi = get_bi_system()
        plan = await bi.campaign_manager.create_campaign_plan(
            name=request.name,
            platforms=request.platforms,
            daily_budget=request.daily_budget,
            total_budget=request.total_budget,
            duration_days=request.duration_days,
            landing_page_url=request.landing_page_url,
        )

        return {
            "campaign_id": plan.id,
            "name": plan.name,
            "status": plan.status,
            "requires_approval": plan.requires_approval,
            "daily_budget": plan.daily_budget,
            "total_budget": plan.total_budget,
            "platforms": plan.platforms,
            "message": "Campaign plan created. Requires human approval before execution.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    """Approve a campaign plan for execution."""
    try:
        bi = get_bi_system()
        result = await bi.campaign_manager.approve_campaign(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/record-result")
async def record_campaign_result(request: CampaignResultRequest):
    """Record campaign performance results."""
    try:
        bi = get_bi_system()
        result = await bi.campaign_manager.record_result(
            campaign_id=request.campaign_id,
            platform=request.platform,
            impressions=request.impressions,
            clicks=request.clicks,
            conversions=request.conversions,
            signups=request.signups,
            ad_spend=request.ad_spend,
            ad_copy_variant=request.ad_copy_variant,
        )

        if bi.data_store:
            await bi.data_store.save_campaign_results([result])

        return {
            "campaign": result.campaign_name,
            "platform": result.platform,
            "spend": result.ad_spend,
            "signups": result.signups,
            "cpc": result.cost_per_click,
            "cpa": result.cost_per_acquisition,
            "ctr": result.conversion_rate,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/summary")
async def get_campaign_summary():
    """Get summary of all campaigns."""
    try:
        bi = get_bi_system()
        return await bi.campaign_manager.get_campaign_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}/ab-results")
async def get_ab_results(campaign_id: str):
    """Get A/B test results for a campaign."""
    try:
        bi = get_bi_system()
        return await bi.campaign_manager.analyze_ab_results(campaign_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Ad Copy ====================

@router.post("/ads/generate")
async def generate_ad_copy(request: AdCopyRequest):
    """Generate ad copy variants for A/B testing."""
    try:
        bi = get_bi_system()

        from business_intelligence.models.data_models import MarketOpportunity, PainPoint
        pain_points = [
            PainPoint(description=pp, severity=0.7)
            for pp in request.pain_points
        ]
        opportunity = MarketOpportunity(
            title=request.niche,
            niche=request.niche,
            pain_points=pain_points,
        )

        copies = await bi.ad_copy_generator.generate_copy(
            opportunity=opportunity,
            platform=request.platform,
            num_variants=request.num_variants,
        )

        return {
            "niche": request.niche,
            "platform": request.platform,
            "variants": [
                {
                    "variant": c.ab_variant,
                    "headline": c.headline,
                    "primary_text": c.primary_text,
                    "description": c.description,
                    "cta": c.call_to_action,
                    "target_pain_point": c.target_pain_point,
                    "character_counts": c.character_counts,
                    "compliance_notes": c.compliance_notes,
                }
                for c in copies
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ads/landing-page-copy")
async def generate_landing_page(request: AdCopyRequest):
    """Generate landing page copy for waitlist collection."""
    try:
        bi = get_bi_system()

        from business_intelligence.models.data_models import MarketOpportunity, PainPoint
        opportunity = MarketOpportunity(
            title=request.niche,
            niche=request.niche,
            pain_points=[
                PainPoint(description=pp) for pp in request.pain_points
            ],
        )

        copy = await bi.ad_copy_generator.generate_landing_page_copy(opportunity)
        return copy

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Waitlist ====================

@router.post("/waitlist/signup")
async def waitlist_signup(request: WaitlistSignupRequest):
    """Add a signup to the product waitlist."""
    try:
        bi = get_bi_system()
        result = await bi.waitlist_manager.add_signup(
            email=request.email,
            name=request.name,
            source_campaign=request.source_campaign,
            source_platform=request.source_platform,
            interests=request.interests,
            consent_given=request.consent_given,
            consent_text=request.consent_text,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/waitlist/opt-out")
async def waitlist_opt_out(email: str):
    """Opt out of the waitlist."""
    try:
        bi = get_bi_system()
        return await bi.waitlist_manager.opt_out(email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/waitlist/stats")
async def get_waitlist_stats():
    """Get waitlist statistics."""
    try:
        bi = get_bi_system()
        stats = await bi.waitlist_manager.get_stats()
        return {
            "total_signups": stats.total_signups,
            "active_signups": stats.active_signups,
            "opted_out": stats.opted_out,
            "today": stats.signups_today,
            "this_week": stats.signups_this_week,
            "this_month": stats.signups_this_month,
            "by_platform": stats.by_source_platform,
            "by_campaign": stats.by_source_campaign,
            "top_interests": stats.top_interests,
            "growth_rate": stats.growth_rate,
            "validation_threshold": stats.validation_threshold,
            "validation_reached": stats.validation_reached,
            "days_to_threshold": stats.days_to_threshold,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Validation ====================

@router.get("/validation/evaluate")
async def evaluate_validation():
    """Evaluate whether demand has been validated (go/no-go)."""
    try:
        bi = get_bi_system()
        verdict = await bi.validation_engine.evaluate()
        return {
            "status": verdict.status,
            "confidence": verdict.confidence,
            "overall_score": verdict.overall_score,
            "scores": {
                "waitlist": verdict.waitlist_score,
                "campaign": verdict.campaign_score,
                "market": verdict.market_score,
            },
            "reasons": verdict.reasons,
            "recommendations": verdict.recommendations,
            "blockers": verdict.blockers,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Customer Intelligence ====================

@router.get("/customers/archetypes")
async def get_customer_archetypes():
    """Get customer archetypes built from waitlist data."""
    try:
        bi = get_bi_system()
        archetypes = await bi.archetype_engine.build_archetypes(
            waitlist_entries=bi.waitlist_manager.entries,
            campaign_results=bi.campaign_manager.results,
        )

        return {
            "archetypes": [
                {
                    "name": a.name,
                    "description": a.description,
                    "sample_size": a.sample_size,
                    "confidence": a.confidence,
                    "channels": a.preferred_channels,
                    "pain_points": a.pain_points,
                    "acquisition_cost": a.acquisition_cost_estimate,
                }
                for a in archetypes
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/targeting")
async def get_targeting_recommendations():
    """Get ad targeting recommendations based on customer archetypes."""
    try:
        bi = get_bi_system()
        return {"recommendations": await bi.archetype_engine.get_targeting_recommendations()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/cross-patterns")
async def get_cross_patterns():
    """Find cross-domain patterns between customer segments."""
    try:
        bi = get_bi_system()
        return await bi.archetype_engine.find_cross_domain_patterns()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Product Discovery ====================

@router.post("/products/ideate")
async def ideate_products(request: ResearchRequest):
    """Generate product concepts for a niche."""
    try:
        bi = get_bi_system()

        orchestrator = bi.intelligence_engine.research_orchestrator
        report = await orchestrator.run_research(
            niche=request.niche,
            keywords=request.keywords,
            depth="quick",
        )

        concepts = await bi.product_ideation.generate_concepts(
            opportunities=report.opportunities,
        )

        return {
            "niche": request.niche,
            "opportunities_found": len(report.opportunities),
            "products": [
                {
                    "name": c.name,
                    "type": c.product_type.value,
                    "description": c.description,
                    "price": c.estimated_price,
                    "currency": c.currency,
                    "pricing_model": c.pricing_model,
                    "features": c.key_features[:5],
                    "uvp": c.unique_value_proposition,
                    "advantages": c.competitive_advantages[:3],
                    "development_days": c.estimated_development_days,
                    "validation_score": c.validation_score,
                }
                for c in concepts
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products/ladder")
async def generate_product_ladder(request: ResearchRequest):
    """Generate a product ladder (free -> low -> mid -> high ticket)."""
    try:
        bi = get_bi_system()
        from business_intelligence.models.data_models import MarketOpportunity, PainPoint

        opportunity = MarketOpportunity(
            title=request.niche,
            niche=request.niche,
            pain_points=[PainPoint(description=kw) for kw in request.keywords],
        )

        ladder = await bi.product_ideation.generate_product_ladder(
            niche=request.niche,
            opportunity=opportunity,
        )

        return {
            "niche": request.niche,
            "ladder": [
                {
                    "tier": idx,
                    "name": c.name,
                    "type": c.product_type.value,
                    "price": c.estimated_price,
                    "pricing_model": c.pricing_model,
                    "description": c.description[:200],
                    "features": c.key_features[:3],
                }
                for idx, c in enumerate(ladder)
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Historical Data ====================

@router.get("/history/timeline")
async def get_intelligence_timeline(days: int = 90):
    """Get the historical intelligence timeline."""
    try:
        bi = get_bi_system()
        return await bi.data_store.get_timeline(days_back=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/snapshots")
async def get_historical_snapshots(days: int = 30):
    """Get historical intelligence snapshots."""
    try:
        bi = get_bi_system()
        snapshots = await bi.data_store.load_snapshots(days_back=days)
        return {"count": len(snapshots), "snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/cleanup")
async def cleanup_old_data():
    """Clean up data older than retention period."""
    try:
        bi = get_bi_system()
        result = await bi.data_store.cleanup_old_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Lookalike Audiences ====================

class LookalikeRequest(BaseModel):
    platform: str = Field("meta", description="Platform (meta, tiktok, google)")
    audience_percentage: float = Field(1.0, description="Audience size as % of country population")
    country: str = Field("GB", description="Target country code")
    archetype_filter: Optional[str] = Field(None, description="Filter by customer archetype")
    name: str = Field("", description="Custom audience name")


@router.post("/lookalike/prepare-seed")
async def prepare_seed_audience(archetype_filter: Optional[str] = None):
    """Prepare a seed audience from waitlist data for lookalike creation."""
    try:
        bi = get_bi_system()
        result = await bi.lookalike_engine.prepare_seed_audience(
            entries=bi.waitlist_manager.entries,
            archetype_filter=archetype_filter,
        )
        if "hashed_emails" in result:
            result["hashed_emails_count"] = len(result["hashed_emails"])
            del result["hashed_emails"]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lookalike/create")
async def create_lookalike_audience(request: LookalikeRequest):
    """Create a lookalike audience definition (requires human approval to upload)."""
    try:
        bi = get_bi_system()
        seed = await bi.lookalike_engine.prepare_seed_audience(
            entries=bi.waitlist_manager.entries,
            archetype_filter=request.archetype_filter,
        )

        if seed.get("status") != "ready":
            return seed

        audience = await bi.lookalike_engine.create_lookalike_audience(
            seed_data=seed,
            platform=request.platform,
            audience_percentage=request.audience_percentage,
            country=request.country,
            name=request.name,
        )

        return {
            "audience_id": audience.id,
            "name": audience.name,
            "platform": audience.platform,
            "seed_size": audience.seed_size,
            "audience_percentage": audience.audience_percentage,
            "estimated_reach": audience.estimated_reach,
            "country": audience.country,
            "status": audience.status,
            "notes": audience.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lookalike/strategy")
async def get_lookalike_strategy(budget: float = 200.0):
    """Get recommended lookalike audience strategy."""
    try:
        bi = get_bi_system()
        seed_size = sum(
            1 for e in bi.waitlist_manager.entries
            if e.consent_given and not e.opted_out
        )
        archetypes = bi.archetype_engine.archetypes if bi.archetype_engine else []

        return await bi.lookalike_engine.recommend_audience_strategy(
            seed_size=seed_size,
            budget=budget,
            archetypes=archetypes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Traffic Strategy ====================

@router.get("/traffic/strategy")
async def get_traffic_strategy(
    budget: float = 200.0,
    niche: str = "general",
):
    """Get complete traffic acquisition strategy."""
    try:
        bi = get_bi_system()
        seed_size = sum(
            1 for e in bi.waitlist_manager.entries
            if e.consent_given and not e.opted_out
        )

        strategy = await bi.lookalike_engine.generate_traffic_strategy(
            budget=budget,
            niche=niche,
            seed_size=seed_size,
            archetypes=bi.archetype_engine.archetypes if bi.archetype_engine else None,
        )

        return {
            "total_budget": strategy.total_estimated_budget,
            "estimated_monthly_reach": strategy.estimated_monthly_reach,
            "paid_channels": strategy.paid_channels,
            "organic_channels": strategy.organic_channels,
            "owned_channels": strategy.owned_channels,
            "priority_order": strategy.priority_order,
            "timeline": strategy.timeline,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Ad Optimization ====================

@router.post("/ads/optimize")
async def optimize_ads():
    """Run real-time ad optimization analysis."""
    try:
        bi = get_bi_system()
        results = bi.campaign_manager.results
        if not results:
            return {"message": "No campaign results to optimize. Record results first."}

        analysis = await bi.ad_optimizer.analyze_performance(results)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ads/optimization-dashboard")
async def get_optimization_dashboard():
    """Get the ad optimization dashboard."""
    try:
        bi = get_bi_system()
        return await bi.ad_optimizer.get_optimization_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LLM Reasoning ====================

class ReasoningRequest(BaseModel):
    niche: str = Field("", description="Market niche for reasoning")
    task: str = Field("market_analysis", description="Reasoning task type")


@router.post("/reasoning/market")
async def reason_about_market(request: ReasoningRequest):
    """Have Grace reason about market data using LLM + hallucination guards."""
    try:
        bi = get_bi_system()
        state = bi.intelligence_engine.state

        market_data = {
            "total_data_points": len(state.all_data_points),
            "sources": list(set(dp.source.value for dp in state.all_data_points)),
        }
        pain_points = [
            {"description": pp.description[:100], "severity": pp.severity, "category": pp.category}
            for pp in state.all_pain_points[:10]
        ]
        competitors = []
        for report in state.research_reports:
            if report.competitor_landscape:
                competitors = report.competitor_landscape.get("recommendations", [])

        result = await bi.reasoning_engine.reason_about_market(
            market_data=market_data,
            pain_points=pain_points,
            competitors=competitors,
            niche=request.niche or (state.niches_under_investigation[0] if state.niches_under_investigation else ""),
        )

        return {
            "task": result.task,
            "reasoning": result.reasoning,
            "recommendations": result.recommendations,
            "confidence": result.confidence,
            "verified": result.verification_passed,
            "warnings": result.warnings,
            "model": result.model_used,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reasoning/product-strategy")
async def reason_about_product():
    """Have Grace reason about what product to build."""
    try:
        bi = get_bi_system()
        state = bi.intelligence_engine.state

        pain_points = [
            {"description": pp.description[:100], "severity": pp.severity, "category": pp.category}
            for pp in state.all_pain_points[:10]
        ]

        archetypes = [
            {"name": a.name, "pain_points": a.pain_points, "channels": a.preferred_channels}
            for a in (bi.archetype_engine.archetypes if bi.archetype_engine else [])
        ]

        opportunities = [
            {"title": s.opportunity.title, "score": s.total_score, "verdict": s.verdict}
            for s in state.scored_opportunities[:5]
        ]

        result = await bi.reasoning_engine.reason_about_product_strategy(
            pain_points=pain_points,
            archetypes=archetypes,
            opportunities=opportunities,
        )

        return {
            "reasoning": result.reasoning,
            "recommendations": result.recommendations,
            "confidence": result.confidence,
            "verified": result.verification_passed,
            "warnings": result.warnings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reasoning/briefing")
async def get_grace_briefing():
    """Get Grace's daily business intelligence briefing."""
    try:
        bi = get_bi_system()
        state_dict = await bi.intelligence_engine.get_status()

        result = await bi.reasoning_engine.generate_grace_briefing(state_dict)

        return {
            "briefing": result.reasoning,
            "recommendations": result.recommendations,
            "confidence": result.confidence,
            "verified": result.verification_passed,
            "warnings": result.warnings,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reasoning/history")
async def get_reasoning_history(limit: int = 10):
    """Get recent LLM reasoning history."""
    try:
        bi = get_bi_system()
        return {"history": bi.reasoning_engine.get_reasoning_history(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Secrets Vault ====================

class SecretStoreRequest(BaseModel):
    key: str = Field(..., description="Secret key name (e.g. SHOPIFY_API_KEY)")
    value: str = Field(..., description="Secret value")
    category: str = Field("api_key", description="Category (api_key, customer_data)")


@router.post("/vault/store")
async def store_secret(request: SecretStoreRequest):
    """Store a secret in the encrypted vault."""
    try:
        bi = get_bi_system()
        if not bi.secrets_vault or not bi.secrets_vault._initialized:
            raise HTTPException(
                status_code=400,
                detail="Vault not initialized. Set BI_VAULT_PASSPHRASE environment variable.",
            )
        success = bi.secrets_vault.store(
            key=request.key,
            value=request.value,
            category=request.category,
        )
        return {"status": "stored" if success else "failed", "key": request.key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/keys")
async def list_vault_keys():
    """List all keys in the vault (values are NOT exposed)."""
    try:
        bi = get_bi_system()
        if not bi.secrets_vault or not bi.secrets_vault._initialized:
            return {"status": "vault_not_initialized", "keys": []}
        return {"keys": bi.secrets_vault.list_keys()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vault/{key}")
async def delete_secret(key: str):
    """Delete a secret from the vault."""
    try:
        bi = get_bi_system()
        if not bi.secrets_vault:
            raise HTTPException(status_code=400, detail="Vault not initialized")
        success = bi.secrets_vault.delete(key)
        return {"status": "deleted" if success else "not_found", "key": key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/status")
async def get_vault_status():
    """Get secrets vault status."""
    try:
        bi = get_bi_system()
        if bi.secrets_vault:
            return bi.secrets_vault.get_status()
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Jungle Scout ====================

class JungleScoutRequest(BaseModel):
    keyword: str = Field(..., description="Keyword to research")
    marketplace: str = Field("us", description="Amazon marketplace (us, uk, de, etc)")


@router.post("/amazon/keyword-research")
async def amazon_keyword_research(request: JungleScoutRequest):
    """Research Amazon keywords via Jungle Scout."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        js = ConnectorRegistry.get("jungle_scout")
        if not js or not js.is_available:
            return {
                "status": "not_configured",
                "message": "Jungle Scout not configured. Set JUNGLESCOUT_API_KEY and JUNGLESCOUT_API_NAME.",
            }

        data = await js.keyword_research(
            search_terms=request.keyword,
            marketplace=request.marketplace,
        )
        return data or {"message": "No keyword data found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/amazon/product-database")
async def amazon_product_search(request: JungleScoutRequest):
    """Search Amazon product database via Jungle Scout."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        js = ConnectorRegistry.get("jungle_scout")
        if not js or not js.is_available:
            return {
                "status": "not_configured",
                "message": "Jungle Scout not configured. Set JUNGLESCOUT_API_KEY.",
            }

        data = await js.product_database(
            keywords=request.keyword,
            marketplace=request.marketplace,
        )
        return data or {"message": "No product data found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/amazon/niche-analysis")
async def amazon_niche_analysis(request: JungleScoutRequest):
    """Get Amazon niche opportunity analysis via Jungle Scout."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        js = ConnectorRegistry.get("jungle_scout")
        if not js or not js.is_available:
            return {
                "status": "not_configured",
                "message": "Jungle Scout not configured.",
            }

        data = await js.niche_analysis(
            keyword=request.keyword,
            marketplace=request.marketplace,
        )
        return data or {"message": "No niche data found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== YouTube ====================

class YouTubeRequest(BaseModel):
    keyword: str = Field(..., description="Search keyword")
    max_results: int = Field(20, description="Maximum results")


@router.post("/youtube/search")
async def youtube_search(request: YouTubeRequest):
    """Search YouTube for videos in a niche."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        yt = ConnectorRegistry.get("youtube")
        if not yt or not yt.is_available:
            return {
                "status": "not_configured",
                "message": "YouTube API not configured. Set YOUTUBE_API_KEY.",
                "setup": "Get API key from console.cloud.google.com (YouTube Data API v3)",
            }

        videos = await yt.search_videos(request.keyword, max_results=request.max_results)
        return {"keyword": request.keyword, "results": len(videos), "videos": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/niche-analysis")
async def youtube_niche_analysis(request: YouTubeRequest):
    """Analyze YouTube content landscape for a niche."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        yt = ConnectorRegistry.get("youtube")
        if not yt or not yt.is_available:
            return {"status": "not_configured", "message": "YouTube API not configured."}

        analysis = await yt.analyze_niche_content(request.keyword, max_videos=request.max_results)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/youtube/channel-analytics")
async def youtube_channel_analytics(days: int = 30):
    """Get analytics for our YouTube channel (requires OAuth)."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        from datetime import timedelta
        yt = ConnectorRegistry.get("youtube")
        if not yt or not yt.is_available:
            return {"status": "not_configured", "message": "YouTube API not configured."}

        analytics = await yt.get_channel_analytics(
            date_from=datetime.utcnow() - timedelta(days=days),
        )
        return analytics or {"message": "No analytics data. Ensure YOUTUBE_OAUTH_TOKEN and YOUTUBE_CHANNEL_ID are set."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/youtube/demographics")
async def youtube_demographics():
    """Get audience demographics for our YouTube channel."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        yt = ConnectorRegistry.get("youtube")
        if not yt or not yt.is_available:
            return {"status": "not_configured"}

        return await yt.get_audience_demographics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Instagram ====================

@router.get("/instagram/insights")
async def instagram_account_insights(days: int = 30):
    """Get Instagram account-level insights."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        from datetime import timedelta
        ig = ConnectorRegistry.get("instagram")
        if not ig or not ig.is_available:
            return {
                "status": "not_configured",
                "message": "Instagram Graph API not configured. Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID.",
                "setup": "Requires Instagram Business Account + Meta Developer App",
            }

        insights = await ig.get_account_insights(
            since=datetime.utcnow() - timedelta(days=days),
        )
        return insights or {"message": "No insights data available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/demographics")
async def instagram_demographics():
    """Get Instagram audience demographics."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        ig = ConnectorRegistry.get("instagram")
        if not ig or not ig.is_available:
            return {"status": "not_configured"}

        return await ig.get_audience_demographics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/media")
async def instagram_recent_media(limit: int = 25):
    """Get recent Instagram posts with performance data."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        ig = ConnectorRegistry.get("instagram")
        if not ig or not ig.is_available:
            return {"status": "not_configured"}

        media = await ig.get_recent_media(limit=limit)
        return {"count": len(media), "media": media}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HashtagRequest(BaseModel):
    hashtag: str = Field(..., description="Hashtag to research (without #)")


@router.post("/instagram/hashtag")
async def instagram_hashtag_research(request: HashtagRequest):
    """Research an Instagram hashtag's volume and reach."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        ig = ConnectorRegistry.get("instagram")
        if not ig or not ig.is_available:
            return {"status": "not_configured"}

        return await ig.search_hashtag(request.hashtag)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Dynamic Creative Optimization ====================

class DynamicCreativeRequest(BaseModel):
    pain_points: List[str] = Field(..., description="Pain points to address in creatives")
    product_name: str = Field(..., description="Product name")
    platforms: List[str] = Field(default_factory=lambda: ["meta"], description="Target platforms")
    budget: float = Field(100.0, description="Total creative budget")


@router.post("/creative/pipeline")
async def build_creative_pipeline(request: DynamicCreativeRequest):
    """Build a complete dynamic creative pipeline across platforms.

    Returns platform-specific creative specs with real-time editing capabilities.
    """
    try:
        bi = get_bi_system()
        pipeline = await bi.dynamic_creative.build_creative_pipeline(
            pain_points=request.pain_points,
            product_name=request.product_name,
            platforms=request.platforms,
            budget=request.budget,
        )
        return pipeline
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/creative/meta-dco")
async def generate_meta_dco(request: DynamicCreativeRequest):
    """Generate Meta Dynamic Creative Optimization spec.

    Provides multiple headlines/bodies/images that Meta auto-tests
    in every combination per impression.
    """
    try:
        bi = get_bi_system()
        variation = await bi.dynamic_creative.generate_creative_variations(
            pain_points=request.pain_points,
            product_name=request.product_name,
            platform="meta",
        )
        dco = await bi.dynamic_creative.generate_meta_dynamic_creative(
            headlines=variation.headlines,
            body_texts=variation.body_texts,
            descriptions=variation.descriptions,
        )
        return {
            "variation": {
                "headlines": variation.headlines,
                "body_texts": variation.body_texts,
                "descriptions": variation.descriptions,
                "ctas": variation.ctas,
            },
            "dco_spec": {
                "asset_feed": dco.asset_feed,
                "total_combinations": dco.platform_specs.get("total_combinations", 0),
                "optimization": dco.platform_specs,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/creative/tools")
async def list_creative_tools():
    """List available creative editing tools and their capabilities."""
    return {
        "tools": [
            {
                "name": "Meta Dynamic Creative",
                "cost": "Free (part of Meta Ads)",
                "real_time_editing": True,
                "edits": ["Headlines", "Body text", "Images", "Videos", "CTAs"],
                "auto_optimization": True,
                "setup": "Included with any Meta ad account",
                "api": "Marketing API asset_feed_spec",
            },
            {
                "name": "Canva Connect API",
                "cost": "Canva Pro + API access",
                "real_time_editing": True,
                "edits": ["Font size", "Font style", "Colors", "Image position", "Layout", "Text content", "Background"],
                "auto_optimization": False,
                "setup": "API key from canva.dev — Set CANVA_API_KEY",
                "api": "REST API + Apps SDK",
            },
            {
                "name": "AdCreative.ai",
                "cost": "Subscription (from $29/mo)",
                "real_time_editing": True,
                "edits": ["Full creative generation", "Headlines", "Punchlines", "CTAs", "Colors (hex)", "Background images", "Logo placement"],
                "auto_optimization": True,
                "setup": "API key from adcreative.ai — Set ADCREATIVE_API_KEY",
                "api": "REST API",
            },
            {
                "name": "TikTok Symphony",
                "cost": "Free with TikTok Business",
                "real_time_editing": True,
                "edits": ["Video scripts", "AI avatar videos", "Trending format adaptation", "Music selection"],
                "auto_optimization": True,
                "setup": "TikTok Business account + Marketing API",
                "api": "Marketing API + Creative Center",
            },
            {
                "name": "Google Responsive Ads",
                "cost": "Free (part of Google Ads)",
                "real_time_editing": True,
                "edits": ["Up to 15 headlines auto-combined", "Up to 4 descriptions", "Auto format/size"],
                "auto_optimization": True,
                "setup": "Google Ads account",
                "api": "Google Ads API",
            },
        ],
        "summary": (
            "YES — you can edit ads in real-time. Meta DCO auto-tests headline/image/CTA combinations. "
            "Canva API edits fonts, image positions, layouts programmatically. "
            "AdCreative.ai generates full creatives with AI. "
            "All of these can be driven by Grace's BI data."
        ),
    }


# ==================== Recursive Intelligence Loops ====================

@router.post("/loops/run")
async def run_recursive_loops():
    """Run all recursive intelligence loops.

    Each loop feeds outputs back as inputs, compounding intelligence:
    Research->Validate->Refine, Customer->Target->Acquire,
    Pain->Product->Feedback, Content->Engage->Discover,
    Price->Test->Optimize, Compete->Monitor->Adapt,
    Sentiment->Predict->Act.
    """
    try:
        bi = get_bi_system()
        state = bi.intelligence_engine.state

        results = await bi.recursive_loops.run_all_loops(
            data_points=state.all_data_points,
            pain_points=state.all_pain_points,
            opportunities=[s.opportunity for s in state.scored_opportunities],
            archetypes=bi.archetype_engine.archetypes if bi.archetype_engine else [],
            campaign_results=bi.campaign_manager.results,
            waitlist_entries=bi.waitlist_manager.entries,
            product_concepts=state.product_concepts,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loops/knowledge")
async def get_knowledge_summary():
    """Get accumulated knowledge from all recursive loops."""
    try:
        bi = get_bi_system()
        return bi.recursive_loops.get_knowledge_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Content Engine ====================

class ContentRequest(BaseModel):
    niche: str = Field(..., description="Target niche")
    pain_points: List[str] = Field(default_factory=list, description="Pain points to address")
    keywords: List[str] = Field(default_factory=list, description="Target keywords")
    product_name: str = Field("", description="Product name if applicable")
    content_type: str = Field("all", description="blog, social, email, course, calendar, or all")
    count: int = Field(5, description="Number of pieces to generate")


@router.post("/content/generate")
async def generate_content(request: ContentRequest):
    """Generate data-driven content from BI intelligence."""
    try:
        bi = get_bi_system()
        from business_intelligence.models.data_models import PainPoint
        pps = [PainPoint(description=p, severity=0.7) for p in request.pain_points]
        results = {}

        if request.content_type in ("blog", "all"):
            results["blog_outlines"] = [
                {"title": c.title, "outline": c.outline, "keywords": c.target_keywords,
                 "seo_notes": c.seo_notes, "word_count": c.estimated_word_count}
                for c in await bi.content_engine.generate_blog_outlines(pps, request.keywords or [request.niche], count=request.count)
            ]

        if request.content_type in ("social", "all"):
            results["social_posts"] = [
                {"platform": c.target_platform, "hook": c.title, "thread": c.outline, "cta": c.cta}
                for c in await bi.content_engine.generate_social_posts(pps, request.product_name, count=request.count)
            ]

        if request.content_type in ("email", "all"):
            results["email_sequence"] = [
                {"subject": c.title, "outline": c.outline, "cta": c.cta}
                for c in await bi.content_engine.generate_email_sequence(pps)
            ]

        if request.content_type in ("course", "all"):
            course = await bi.content_engine.generate_course_outline(request.niche, pps, request.keywords)
            results["course"] = {"title": course.title, "modules": course.outline, "word_count": course.estimated_word_count}

        if request.content_type == "calendar":
            cal = await bi.content_engine.generate_content_calendar(pps, request.niche, request.keywords)
            results["calendar"] = {"weeks": cal.duration_weeks, "posts_per_week": cal.posts_per_week,
                                   "total_pieces": len(cal.pieces), "platforms": cal.platforms}

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Financial Modeling ====================

class FinancialRequest(BaseModel):
    niche: str = Field(..., description="Target niche")
    product_type: str = Field("saas", description="Product type")
    price: float = Field(29.0, description="Product price in GBP")
    monthly_budget: float = Field(500.0, description="Monthly ad budget")
    monthly_new_customers: int = Field(50, description="Expected monthly new customers")


@router.post("/financial/model")
async def build_financial_model(request: FinancialRequest):
    """Build a financial model for a product concept."""
    try:
        bi = get_bi_system()
        from business_intelligence.models.data_models import ProductConcept, ProductType

        type_map = {"saas": ProductType.SAAS, "course": ProductType.ONLINE_COURSE,
                    "ebook": ProductType.EBOOK_PDF, "ai": ProductType.AI_AUTOMATION,
                    "community": ProductType.COMMUNITY_MEMBERSHIP, "template": ProductType.TEMPLATE_TOOLKIT}

        concept = ProductConcept(
            name=f"{request.niche} Product",
            product_type=type_map.get(request.product_type, ProductType.SAAS),
            estimated_price=request.price,
            target_niche=request.niche,
        )

        plan = await bi.financial_modeler.build_financial_plan(
            product=concept,
            campaign_results=bi.campaign_manager.results or None,
            monthly_budget=request.monthly_budget,
        )

        dashboard = await bi.frontend_bridge.get_financial_dashboard(plan)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Untapped Intelligence ====================

@router.post("/intelligence/untapped")
async def run_untapped_intelligence():
    """Run untapped intelligence analyses -- patterns most BI systems miss."""
    try:
        bi = get_bi_system()
        state = bi.intelligence_engine.state

        competitors = []
        for report in state.research_reports:
            if report.competitor_landscape:
                competitors_data = report.competitor_landscape
                break

        from business_intelligence.models.data_models import CompetitorProduct
        results = await bi.untapped_intel.analyze_all(
            data_points=state.all_data_points,
            pain_points=state.all_pain_points,
            competitors=[],
            waitlist=bi.waitlist_manager.entries,
            campaigns=bi.campaign_manager.results,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Frontend Dashboard ====================

@router.get("/dashboard")
async def get_bi_dashboard():
    """Get complete BI dashboard data for the frontend.

    Returns a single payload with all widgets the React frontend needs.
    """
    try:
        bi = get_bi_system()
        return await bi.frontend_bridge.get_dashboard_data(bi)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/loops")
async def get_loop_dashboard():
    """Get recursive loops dashboard for frontend."""
    try:
        bi = get_bi_system()
        knowledge = bi.recursive_loops.get_knowledge_summary()
        return await bi.frontend_bridge.get_loop_dashboard(knowledge)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GRACE Backbone Integration ====================

@router.get("/grace/integration-status")
async def get_grace_integration_status():
    """Get status of BI system's integration with all GRACE subsystems.

    Shows which GRACE systems (Genesis, KPIs, MAGMA, Telemetry, Learning)
    are connected to the BI pipeline.
    """
    try:
        bi = get_bi_system()
        if bi.grace_integration:
            return bi.grace_integration.get_integration_status()
        return {"initialized": False, "message": "GRACE integration not initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grace/sensor-data")
async def get_bi_sensor_data():
    """Get BI health data for GRACE's Diagnostic Machine sensors."""
    try:
        bi = get_bi_system()
        if bi.grace_integration:
            return bi.grace_integration.get_bi_sensor_data()
        return {"health": "unknown"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grace/operations")
async def get_tracked_operations(limit: int = 50):
    """Get recent BI operations tracked via Genesis Keys."""
    try:
        bi = get_bi_system()
        if not bi.grace_integration:
            return {"operations": []}

        ops = bi.grace_integration.operations[-limit:]
        return {
            "total": len(bi.grace_integration.operations),
            "showing": len(ops),
            "operations": [
                {
                    "id": op.operation_id,
                    "type": op.operation_type,
                    "module": op.module,
                    "description": op.description,
                    "genesis_key": op.genesis_key_id,
                    "success": op.success,
                    "duration_ms": op.duration_ms,
                    "timestamp": op.timestamp.isoformat(),
                    "magma_ingested": op.magma_ingested,
                    "error": op.error,
                }
                for op in reversed(ops)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Cognitive Bridge ====================

@router.get("/cognitive/status")
async def get_cognitive_bridge_status():
    """Get status of BI's deep cognitive integration.

    Shows connection to: OODA loops, episodic memory, contradiction detector,
    causal inference, decision logger, confidence scorer, Layer 1 message bus,
    mirror self-modeling, predictive context, Oracle/ML, cognitive engine.
    """
    try:
        bi = get_bi_system()
        if bi.cognitive_bridge:
            return bi.cognitive_bridge.get_status()
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cognitive/behavioral-patterns")
async def get_bi_behavioral_patterns():
    """Get Mirror Self-Modeling analysis of BI behavioral patterns."""
    try:
        bi = get_bi_system()
        if bi.cognitive_bridge:
            return bi.cognitive_bridge.get_bi_behavioral_patterns()
        return {"patterns": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cognitive/decisions")
async def get_bi_decisions(limit: int = 20):
    """Get BI decisions tracked through OODA loops."""
    try:
        bi = get_bi_system()
        if not bi.cognitive_bridge:
            return {"decisions": []}

        decisions = bi.cognitive_bridge.decisions[-limit:]
        return {
            "total": len(bi.cognitive_bridge.decisions),
            "decisions": [
                {
                    "id": d.decision_id,
                    "type": d.decision_type,
                    "module": d.module,
                    "problem": d.problem,
                    "confidence": d.confidence,
                    "contradictions": len(d.contradictions_found),
                    "causal_chains": len(d.causal_chains),
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in reversed(decisions)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CausalQueryRequest(BaseModel):
    observation: str = Field(..., description="Market observation to reason about causally")
    context: List[str] = Field(default_factory=list, description="Supporting context")


@router.post("/cognitive/causal-reasoning")
async def causal_market_reasoning(request: CausalQueryRequest):
    """Use MAGMA's causal inference for market reasoning.

    Example: 'Why are competitors ratings dropping?'
    """
    try:
        bi = get_bi_system()
        if not bi.cognitive_bridge:
            return {"status": "unavailable"}

        return await bi.cognitive_bridge.infer_market_causality(
            observation=request.observation,
            context=request.context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cognitive/pre-fetch-context")
async def pre_fetch_market_context(request: ResearchRequest):
    """Pre-fetch related market knowledge before reasoning.

    Predictive Context Loader identifies related topics and pre-loads them.
    """
    try:
        bi = get_bi_system()
        if not bi.cognitive_bridge:
            return {"status": "unavailable"}

        return await bi.cognitive_bridge.pre_fetch_market_context(
            niche=request.niche,
            keywords=request.keywords,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cognitive/confidence-score")
async def score_bi_confidence(
    data_sources: int = 3,
    data_points: int = 50,
    contradictions: int = 0,
    validated: bool = False,
):
    """Score BI data confidence using GRACE's confidence pipeline."""
    try:
        bi = get_bi_system()
        if not bi.cognitive_bridge:
            return {"confidence": 0.5, "note": "Cognitive bridge unavailable"}

        score = await bi.cognitive_bridge.score_bi_confidence(
            data_sources=data_sources,
            data_points=data_points,
            contradictions=contradictions,
            validated_by_campaign=validated,
        )
        return {"confidence": score, "data_sources": data_sources,
                "data_points": data_points, "contradictions": contradictions,
                "campaign_validated": validated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ML Intelligence ====================

@router.get("/ml/status")
async def get_ml_bridge_status():
    """Get ML Intelligence connection status (Neural Trust, Bandits, Meta-Learning, etc)."""
    try:
        bi = get_bi_system()
        if bi.ml_bridge:
            return bi.ml_bridge.get_status()
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/optimal-data-collection")
async def get_optimal_data_collection():
    """Active Learning: identify which data to collect next for maximum insight."""
    try:
        bi = get_bi_system()
        from business_intelligence.connectors.base import ConnectorRegistry
        all_connectors = ConnectorRegistry.get_all()
        current_data = {}
        for name, conn in all_connectors.items():
            current_data[name] = conn.health.total_data_points

        available = list(all_connectors.keys())
        return await bi.ml_bridge.identify_optimal_data_collection(current_data, available)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Universal Knowledge Library ====================

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    max_per_source: int = Field(5, description="Max results per knowledge source")


@router.post("/knowledge/search-all")
async def search_all_knowledge(request: KnowledgeSearchRequest):
    """Search ALL knowledge sources simultaneously.

    Queries OpenAlex (250M papers), Semantic Scholar (200M papers),
    Wikipedia (6M articles), Open Library (millions of books),
    and Google Knowledge Graph in parallel.
    """
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        return await kl.search_all(request.query, request.max_per_source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/domain")
async def get_domain_knowledge(request: KnowledgeSearchRequest):
    """Get comprehensive knowledge about a domain/industry.

    Combines Wikipedia overview, research trends, academic papers,
    and books for deep domain understanding.
    """
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        return await kl.get_domain_knowledge(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/papers")
async def search_academic_papers(request: KnowledgeSearchRequest):
    """Search academic papers via OpenAlex (250M+ works, free)."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        return {"papers": await kl.search_papers(request.query, request.max_per_source)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/wikipedia")
async def search_wikipedia(request: KnowledgeSearchRequest):
    """Search Wikipedia for background knowledge."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        articles = await kl.search_wikipedia(request.query, request.max_per_source)
        if articles:
            articles[0]["summary"] = await kl.get_wikipedia_summary(articles[0]["title"])
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/books")
async def search_books(request: KnowledgeSearchRequest):
    """Search Open Library for books (millions of titles, free)."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        return {"books": await kl.search_books(request.query, request.max_per_source)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/research-trends")
async def get_research_trends(request: KnowledgeSearchRequest):
    """Get research publication trends for a topic over time."""
    try:
        from business_intelligence.connectors.base import ConnectorRegistry
        kl = ConnectorRegistry.get("knowledge_library")
        if not kl:
            return {"status": "not_configured"}

        return await kl.get_research_trends(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Integrity & Accountability ====================

@router.get("/integrity/status")
async def get_integrity_status():
    """Get status of honesty/integrity/accountability systems.

    Shows connections to: Governance (Constitutional AI), Hallucination Guard
    (6-layer), Confidence Scorer, Contradiction Detector, 12 Cognitive
    Invariants, Trust-Aware Retrieval.
    """
    try:
        bi = get_bi_system()
        if bi.integrity_bridge:
            return bi.integrity_bridge.get_status()
        return {"initialized": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IntegrityCheckRequest(BaseModel):
    output: Dict[str, Any] = Field(..., description="BI output to check")
    output_type: str = Field("recommendation", description="Type of output")


@router.post("/integrity/check")
async def run_integrity_check(request: IntegrityCheckRequest):
    """Run full integrity check on a BI output.

    Checks: Constitutional compliance, hallucination guard,
    manipulation detection, transparency, confidence calibration.
    """
    try:
        bi = get_bi_system()
        if not bi.integrity_bridge:
            return {"status": "unavailable"}

        return await bi.integrity_bridge.run_full_integrity_check(
            bi_output=request.output,
            output_type=request.output_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrity/honesty-report")
async def get_honesty_report():
    """Get Grace's honesty report -- what she knows, doesn't know, and why.

    Grace explicitly states her data gaps, confidence levels, known risks,
    and unknown unknowns. Full transparency.
    """
    try:
        bi = get_bi_system()
        if not bi.integrity_bridge:
            return {"status": "unavailable"}

        from business_intelligence.connectors.base import ConnectorRegistry
        state = bi.intelligence_engine.state if bi.intelligence_engine else None

        return await bi.integrity_bridge.generate_honesty_report(
            data_points=len(state.all_data_points) if state else 0,
            sources_active=len(ConnectorRegistry.get_active()),
            sources_total=len(ConnectorRegistry.get_all()),
            pain_points=len(state.all_pain_points) if state else 0,
            opportunities=len(state.scored_opportunities) if state else 0,
            confidence=state.scored_opportunities[0].total_score if state and state.scored_opportunities else 0.0,
            concerns=[n for n in (state.grace_notes[-5:] if state else [])],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrity/accountability")
async def get_accountability_report():
    """Get accountability report -- how accurate have Grace's BI predictions been?

    Tracks: predictions made, outcomes recorded, accuracy scores,
    calibration error, overconfident/underconfident analysis.
    """
    try:
        bi = get_bi_system()
        if not bi.integrity_bridge:
            return {"status": "unavailable"}

        return await bi.integrity_bridge.get_accountability_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PredictionRecord(BaseModel):
    prediction: str = Field(..., description="What Grace predicted")
    confidence: float = Field(..., description="Confidence level 0-1")
    module: str = Field("general", description="Which BI module made the prediction")


@router.post("/integrity/record-prediction")
async def record_prediction(request: PredictionRecord):
    """Record a BI prediction for future accountability tracking."""
    try:
        bi = get_bi_system()
        if not bi.integrity_bridge:
            return {"status": "unavailable"}

        prediction_id = await bi.integrity_bridge.record_prediction(
            prediction=request.prediction,
            confidence=request.confidence,
            module=request.module,
        )
        return {"prediction_id": prediction_id, "status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OutcomeRecord(BaseModel):
    prediction_id: str = Field(..., description="ID of the prediction to evaluate")
    actual_outcome: str = Field(..., description="What actually happened")
    accuracy: float = Field(..., description="How accurate was the prediction 0-1")


@router.post("/integrity/record-outcome")
async def record_outcome(request: OutcomeRecord):
    """Record the actual outcome of a prediction for accountability."""
    try:
        bi = get_bi_system()
        if not bi.integrity_bridge:
            return {"status": "unavailable"}

        return await bi.integrity_bridge.record_outcome(
            prediction_id=request.prediction_id,
            actual_outcome=request.actual_outcome,
            accuracy=request.accuracy,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
