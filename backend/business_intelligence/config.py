"""
Business Intelligence System Configuration

Central configuration for all BI modules. API keys are loaded from environment
variables. The system operates in degraded mode when keys are missing -- connectors
that lack credentials are disabled rather than crashing the whole pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class BIPhase(Enum):
    COLLECT = "collect"
    SYNTHESIZE = "synthesize"
    IDENTIFY = "identify"
    VALIDATE = "validate"
    BUILD = "build"
    SCALE = "scale"


class ConnectorStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ConnectorConfig:
    name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_per_minute: int = 60
    enabled: bool = True
    extra: Dict = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.api_key or self.access_token)


@dataclass
class BIConfig:
    """Master configuration for the BI system."""

    # Data retention
    historical_retention_days: int = 365
    snapshot_interval_hours: int = 24

    # Synthesis
    min_data_points_for_trend: int = 7
    confidence_threshold: float = 0.65
    opportunity_score_threshold: float = 0.70

    # Market research
    max_reviews_per_product: int = 500
    negative_review_weight: float = 1.5
    pain_point_cluster_min_size: int = 3

    # Campaign validation
    min_waitlist_for_validation: int = 500
    max_initial_ad_spend: float = 200.0
    target_cpa: float = 5.0

    # Customer intelligence - GDPR compliance
    require_consent_for_tracking: bool = True
    anonymize_after_days: int = 90
    prohibited_data_fields: List[str] = field(default_factory=lambda: [
        "social_security", "passport", "credit_card_full",
        "medical_records", "biometric_data"
    ])

    # Connector configs
    connectors: Dict[str, ConnectorConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "BIConfig":
        config = cls()

        config.connectors = {
            "google_analytics": ConnectorConfig(
                name="Google Analytics",
                api_key=os.getenv("GA_API_KEY"),
                extra={
                    "property_id": os.getenv("GA_PROPERTY_ID"),
                    "credentials_path": os.getenv("GA_CREDENTIALS_PATH"),
                }
            ),
            "shopify": ConnectorConfig(
                name="Shopify",
                api_key=os.getenv("SHOPIFY_API_KEY"),
                api_secret=os.getenv("SHOPIFY_API_SECRET"),
                access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
                base_url=os.getenv("SHOPIFY_STORE_URL"),
            ),
            "amazon": ConnectorConfig(
                name="Amazon Product Advertising",
                api_key=os.getenv("AMAZON_ACCESS_KEY"),
                api_secret=os.getenv("AMAZON_SECRET_KEY"),
                extra={
                    "partner_tag": os.getenv("AMAZON_PARTNER_TAG"),
                    "marketplace": os.getenv("AMAZON_MARKETPLACE", "www.amazon.co.uk"),
                }
            ),
            "meta": ConnectorConfig(
                name="Meta Marketing",
                access_token=os.getenv("META_ACCESS_TOKEN"),
                extra={
                    "app_id": os.getenv("META_APP_ID"),
                    "app_secret": os.getenv("META_APP_SECRET"),
                    "ad_account_id": os.getenv("META_AD_ACCOUNT_ID"),
                }
            ),
            "instagram": ConnectorConfig(
                name="Instagram Graph",
                access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN"),
                extra={
                    "business_account_id": os.getenv("INSTAGRAM_BUSINESS_ID"),
                }
            ),
            "tiktok": ConnectorConfig(
                name="TikTok Business",
                access_token=os.getenv("TIKTOK_ACCESS_TOKEN"),
                extra={
                    "advertiser_id": os.getenv("TIKTOK_ADVERTISER_ID"),
                }
            ),
            "serpapi": ConnectorConfig(
                name="SerpAPI",
                api_key=os.getenv("SERPAPI_KEY"),
            ),
            "youtube": ConnectorConfig(
                name="YouTube Analytics",
                api_key=os.getenv("YOUTUBE_API_KEY"),
                access_token=os.getenv("YOUTUBE_OAUTH_TOKEN"),
                extra={
                    "channel_id": os.getenv("YOUTUBE_CHANNEL_ID"),
                }
            ),
        }

        retention = os.getenv("BI_RETENTION_DAYS")
        if retention:
            config.historical_retention_days = int(retention)

        return config

    def get_active_connectors(self) -> Dict[str, ConnectorConfig]:
        return {
            k: v for k, v in self.connectors.items()
            if v.is_configured
        }

    def get_status_report(self) -> Dict:
        report = {}
        for name, conn in self.connectors.items():
            if conn.is_configured:
                status = ConnectorStatus.ACTIVE
            elif conn.enabled:
                status = ConnectorStatus.DEGRADED
            else:
                status = ConnectorStatus.DISABLED
            report[name] = {
                "name": conn.name,
                "status": status.value,
                "configured": conn.is_configured,
            }
        return report
