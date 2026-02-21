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
