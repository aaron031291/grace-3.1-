"""
Core data models for the Business Intelligence system.

These models represent the fundamental data structures that flow through
the entire BI pipeline -- from collection through synthesis to action.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class Sentiment(Enum):
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class DataSource(Enum):
    GOOGLE_ANALYTICS = "google_analytics"
    SHOPIFY = "shopify"
    AMAZON = "amazon"
    META = "meta"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    SERPAPI = "serpapi"
    WEB_SCRAPE = "web_scrape"
    MANUAL = "manual"
    FORUM = "forum"
    REVIEW_SITE = "review_site"


class OpportunityType(Enum):
    PRODUCT_IMPROVEMENT = "product_improvement"
    UNDERSERVED_NICHE = "underserved_niche"
    PRICING_GAP = "pricing_gap"
    FEATURE_GAP = "feature_gap"
    SERVICE_GAP = "service_gap"
    CONTENT_GAP = "content_gap"
    AUTOMATION_OPPORTUNITY = "automation_opportunity"


class ProductType(Enum):
    SAAS = "saas"
    ONLINE_COURSE = "online_course"
    EBOOK_PDF = "ebook_pdf"
    PHYSICAL_PRODUCT = "physical_product"
    AI_AUTOMATION = "ai_automation"
    CONSULTING_SERVICE = "consulting_service"
    TEMPLATE_TOOLKIT = "template_toolkit"
    COMMUNITY_MEMBERSHIP = "community_membership"


@dataclass
class MarketDataPoint:
    """A single data point collected from any source."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: DataSource = DataSource.MANUAL
    category: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    niche: str = ""
    keywords: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class KeywordMetric:
    """Search keyword performance data."""
    keyword: str = ""
    search_volume: int = 0
    competition: float = 0.0
    cpc: float = 0.0
    trend_direction: str = "stable"
    trend_percentage: float = 0.0
    related_keywords: List[str] = field(default_factory=list)
    source: DataSource = DataSource.SERPAPI
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrafficSource:
    """Traffic source analytics data."""
    source_name: str = ""
    medium: str = ""
    sessions: int = 0
    users: int = 0
    bounce_rate: float = 0.0
    conversion_rate: float = 0.0
    revenue: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReviewAnalysis:
    """Analysis of a product review."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str = ""
    product_name: str = ""
    platform: str = ""
    rating: float = 0.0
    review_text: str = ""
    sentiment: Sentiment = Sentiment.NEUTRAL
    pain_points_extracted: List[str] = field(default_factory=list)
    feature_requests: List[str] = field(default_factory=list)
    praise_points: List[str] = field(default_factory=list)
    reviewer_demographics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: DataSource = DataSource.AMAZON


@dataclass
class PainPoint:
    """A validated customer pain point extracted from market data."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    category: str = ""
    niche: str = ""
    severity: float = 0.0  # 0-1 scale
    frequency: int = 0
    sources: List[DataSource] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    affected_demographics: List[str] = field(default_factory=list)
    existing_solutions: List[str] = field(default_factory=list)
    solution_gaps: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def pain_score(self) -> float:
        return self.severity * min(self.frequency / 10, 1.0)


@dataclass
class CompetitorProduct:
    """A competitor's product in a given market."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    company: str = ""
    platform: str = ""
    url: str = ""
    price: float = 0.0
    currency: str = "GBP"
    rating: float = 0.0
    review_count: int = 0
    category: str = ""
    features: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    negative_review_themes: List[str] = field(default_factory=list)
    market_share_estimate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MarketOpportunity:
    """A scored market opportunity identified by the synthesis engine."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    niche: str = ""
    opportunity_type: OpportunityType = OpportunityType.UNDERSERVED_NICHE
    pain_points: List[PainPoint] = field(default_factory=list)
    competitors: List[CompetitorProduct] = field(default_factory=list)
    estimated_market_size: float = 0.0
    confidence_score: float = 0.0
    opportunity_score: float = 0.0
    recommended_product_types: List[ProductType] = field(default_factory=list)
    entry_barriers: List[str] = field(default_factory=list)
    time_to_market_days: int = 0
    estimated_initial_investment: float = 0.0
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def viability_score(self) -> float:
        if not self.pain_points:
            return 0.0
        avg_pain = sum(p.pain_score for p in self.pain_points) / len(self.pain_points)
        barrier_penalty = min(len(self.entry_barriers) * 0.1, 0.5)
        return min(1.0, (avg_pain * 0.4 + self.confidence_score * 0.3 +
                         self.opportunity_score * 0.3) - barrier_penalty)


@dataclass
class CustomerArchetype:
    """A customer archetype derived from data analysis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    age_range: str = ""
    demographics: Dict[str, Any] = field(default_factory=dict)
    pain_points: List[str] = field(default_factory=list)
    buying_motivations: List[str] = field(default_factory=list)
    preferred_channels: List[str] = field(default_factory=list)
    price_sensitivity: float = 0.5  # 0 = price insensitive, 1 = very price sensitive
    lifetime_value_estimate: float = 0.0
    acquisition_cost_estimate: float = 0.0
    sample_size: int = 0
    confidence: float = 0.0
    consent_verified: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CampaignResult:
    """Results from a validation campaign."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    campaign_name: str = ""
    platform: str = ""
    ad_spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    signups: int = 0
    cost_per_click: float = 0.0
    cost_per_acquisition: float = 0.0
    conversion_rate: float = 0.0
    target_audience: Dict[str, Any] = field(default_factory=dict)
    ad_copy_used: str = ""
    landing_page_url: str = ""
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    ab_variant: str = ""
    notes: str = ""

    @property
    def roi_indicator(self) -> float:
        if self.ad_spend == 0:
            return 0.0
        return self.signups / self.ad_spend


@dataclass
class WaitlistEntry:
    """A person on the product waitlist. GDPR-compliant data only."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    name: Optional[str] = None
    source_campaign: str = ""
    source_platform: str = ""
    signup_date: datetime = field(default_factory=datetime.utcnow)
    interests: List[str] = field(default_factory=list)
    consent_given: bool = False
    consent_timestamp: Optional[datetime] = None
    consent_text: str = ""
    opted_out: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductConcept:
    """A product concept generated from market intelligence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    product_type: ProductType = ProductType.SAAS
    target_niche: str = ""
    target_archetypes: List[str] = field(default_factory=list)
    pain_points_addressed: List[PainPoint] = field(default_factory=list)
    key_features: List[str] = field(default_factory=list)
    unique_value_proposition: str = ""
    pricing_model: str = ""
    estimated_price: float = 0.0
    currency: str = "GBP"
    competitive_advantages: List[str] = field(default_factory=list)
    estimated_development_days: int = 0
    validation_status: str = "concept"
    validation_score: float = 0.0
    supporting_opportunity: Optional[MarketOpportunity] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IntelligenceSnapshot:
    """A point-in-time snapshot of the entire intelligence state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data_points_collected: int = 0
    active_niches: List[str] = field(default_factory=list)
    top_opportunities: List[MarketOpportunity] = field(default_factory=list)
    top_pain_points: List[PainPoint] = field(default_factory=list)
    active_campaigns: List[CampaignResult] = field(default_factory=list)
    waitlist_size: int = 0
    archetypes_identified: List[CustomerArchetype] = field(default_factory=list)
    product_concepts: List[ProductConcept] = field(default_factory=list)
    connectors_status: Dict[str, str] = field(default_factory=dict)
    phase: str = "collect"
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
