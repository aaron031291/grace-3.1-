"""
Data connectors for external platforms and APIs.

Each connector follows a common interface (BaseConnector) but implements
platform-specific logic. Connectors that lack API credentials gracefully
degrade rather than crash.
"""

from .base import BaseConnector, ConnectorRegistry
from .google_analytics import GoogleAnalyticsConnector
from .shopify_connector import ShopifyConnector
from .amazon_connector import AmazonConnector
from .meta_connector import MetaConnector
from .tiktok_connector import TikTokConnector
from .serpapi_connector import SerpAPIConnector
from .web_scraping_connector import WebScrapingConnector
from .junglescout_connector import JungleScoutConnector
from .youtube_connector import YouTubeConnector
from .instagram_connector import InstagramConnector
from .email_marketing_connector import EmailMarketingConnector
from .crypto_connector import CryptoFinanceConnector
