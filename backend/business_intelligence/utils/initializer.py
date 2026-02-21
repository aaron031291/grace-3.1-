"""
BI System Initializer

Sets up the entire Business Intelligence system:
- Loads configuration from environment (or secrets vault)
- Initializes and registers all connectors
- Creates engine instances (including LLM reasoning)
- Provides a single entry point for the GRACE backend
"""

import logging
from typing import Optional

from business_intelligence.config import BIConfig
from business_intelligence.connectors.base import ConnectorRegistry
from business_intelligence.connectors.google_analytics import GoogleAnalyticsConnector
from business_intelligence.connectors.shopify_connector import ShopifyConnector
from business_intelligence.connectors.amazon_connector import AmazonConnector
from business_intelligence.connectors.meta_connector import MetaConnector
from business_intelligence.connectors.tiktok_connector import TikTokConnector
from business_intelligence.connectors.serpapi_connector import SerpAPIConnector
from business_intelligence.connectors.web_scraping_connector import WebScrapingConnector
from business_intelligence.connectors.junglescout_connector import JungleScoutConnector
from business_intelligence.connectors.youtube_connector import YouTubeConnector
from business_intelligence.connectors.instagram_connector import InstagramConnector
from business_intelligence.synthesis.intelligence_engine import IntelligenceEngine
from business_intelligence.synthesis.reasoning_engine import BIReasoningEngine
from business_intelligence.campaigns.waitlist_manager import WaitlistManager
from business_intelligence.campaigns.campaign_manager import CampaignManager
from business_intelligence.campaigns.ad_copy_generator import AdCopyGenerator
from business_intelligence.campaigns.validation_engine import ValidationEngine
from business_intelligence.campaigns.lookalike_engine import LookalikeEngine
from business_intelligence.campaigns.ad_optimizer import AdOptimizer
from business_intelligence.campaigns.dynamic_creative import DynamicCreativeEngine
from business_intelligence.customer_intelligence.archetype_engine import ArchetypeEngine
from business_intelligence.customer_intelligence.pattern_analyzer import CrossPatternAnalyzer
from business_intelligence.product_discovery.product_ideation import ProductIdeationEngine
from business_intelligence.product_discovery.niche_finder import NicheFinder
from business_intelligence.historical.data_store import HistoricalDataStore
from business_intelligence.utils.secrets_vault import SecretsVault

logger = logging.getLogger(__name__)


class BISystem:
    """Top-level Business Intelligence System facade.

    Provides a single access point for all BI capabilities.
    Initialize once at application startup and inject into API routes.
    """

    def __init__(self, config: Optional[BIConfig] = None):
        self.config = config or BIConfig.from_env()
        self._initialized = False

        self.intelligence_engine: Optional[IntelligenceEngine] = None
        self.reasoning_engine: Optional[BIReasoningEngine] = None
        self.waitlist_manager: Optional[WaitlistManager] = None
        self.campaign_manager: Optional[CampaignManager] = None
        self.ad_copy_generator: Optional[AdCopyGenerator] = None
        self.validation_engine: Optional[ValidationEngine] = None
        self.lookalike_engine: Optional[LookalikeEngine] = None
        self.ad_optimizer: Optional[AdOptimizer] = None
        self.dynamic_creative: Optional[DynamicCreativeEngine] = None
        self.archetype_engine: Optional[ArchetypeEngine] = None
        self.pattern_analyzer: Optional[CrossPatternAnalyzer] = None
        self.product_ideation: Optional[ProductIdeationEngine] = None
        self.niche_finder: Optional[NicheFinder] = None
        self.data_store: Optional[HistoricalDataStore] = None
        self.secrets_vault: Optional[SecretsVault] = None

    def initialize(self):
        """Initialize all BI subsystems."""
        if self._initialized:
            return

        logger.info("Initializing Business Intelligence System...")

        self.secrets_vault = SecretsVault()
        if self.secrets_vault._initialized:
            self.secrets_vault.load_secrets_to_env(category="api_key")
            self.config = BIConfig.from_env()
            logger.info("Loaded API keys from secrets vault")

        ConnectorRegistry.reset()
        self._register_connectors()

        self.intelligence_engine = IntelligenceEngine(self.config)
        self.reasoning_engine = BIReasoningEngine()
        self.waitlist_manager = WaitlistManager(
            validation_threshold=self.config.min_waitlist_for_validation
        )
        self.campaign_manager = CampaignManager()
        self.ad_copy_generator = AdCopyGenerator()
        self.validation_engine = ValidationEngine(
            waitlist_manager=self.waitlist_manager,
            campaign_manager=self.campaign_manager,
            min_signups=self.config.min_waitlist_for_validation,
            target_cpa=self.config.target_cpa,
        )
        self.lookalike_engine = LookalikeEngine()
        self.ad_optimizer = AdOptimizer(
            target_cpa=self.config.target_cpa,
        )
        self.dynamic_creative = DynamicCreativeEngine()
        self.archetype_engine = ArchetypeEngine(
            min_cluster_size=self.config.pain_point_cluster_min_size
        )
        self.pattern_analyzer = CrossPatternAnalyzer()
        self.product_ideation = ProductIdeationEngine()
        self.niche_finder = NicheFinder()
        self.data_store = HistoricalDataStore(
            retention_days=self.config.historical_retention_days
        )

        self._initialized = True

        active = ConnectorRegistry.get_active()
        total = len(ConnectorRegistry.get_all())
        logger.info(
            f"BI System initialized. "
            f"{len(active)}/{total} connectors active. "
            f"LLM reasoning: {'available' if self.reasoning_engine else 'unavailable'}. "
            f"Secrets vault: {'active' if self.secrets_vault._initialized else 'inactive'}. "
            f"Ready for intelligence collection."
        )

    def _register_connectors(self):
        """Register all data connectors from config."""
        connector_map = {
            "google_analytics": GoogleAnalyticsConnector,
            "shopify": ShopifyConnector,
            "amazon": AmazonConnector,
            "meta": MetaConnector,
            "tiktok": TikTokConnector,
            "serpapi": SerpAPIConnector,
            "jungle_scout": JungleScoutConnector,
            "youtube": YouTubeConnector,
            "instagram": InstagramConnector,
            "web_scraping": WebScrapingConnector,
        }

        for name, connector_class in connector_map.items():
            config = self.config.connectors.get(name)
            if config:
                connector = connector_class(config)
            else:
                from business_intelligence.config import ConnectorConfig
                connector = connector_class(ConnectorConfig(name=name))

            ConnectorRegistry.register(name, connector)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def get_status(self) -> dict:
        """Get overall system status."""
        return {
            "initialized": self._initialized,
            "connectors": self.config.get_status_report(),
            "active_connectors": len(ConnectorRegistry.get_active()),
            "total_connectors": len(ConnectorRegistry.get_all()),
            "reasoning_engine": "available" if self.reasoning_engine else "unavailable",
            "secrets_vault": self.secrets_vault.get_status() if self.secrets_vault else {"initialized": False},
        }


_bi_system: Optional[BISystem] = None


def get_bi_system() -> BISystem:
    """Get or create the global BI system instance."""
    global _bi_system
    if _bi_system is None:
        _bi_system = BISystem()
        _bi_system.initialize()
    return _bi_system
