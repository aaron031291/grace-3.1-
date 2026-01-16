"""
Web scraping module for Grace.

This module provides functionality for scraping web content with depth control
using the trafilatura library.
"""

from .service import WebScrapingService
from .url_validator import URLValidator
from .models import ScrapingJob, ScrapedPage

__all__ = [
    'WebScrapingService',
    'URLValidator',
    'ScrapingJob',
    'ScrapedPage',
]
