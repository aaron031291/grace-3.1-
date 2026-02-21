"""
Campaign & Validation Module

Manages the demand validation loop: create ad copy, run small campaigns,
collect waitlist signups, analyze results, and determine if there's
enough demand to justify building the product.
"""

from .ad_copy_generator import AdCopyGenerator
from .waitlist_manager import WaitlistManager
from .campaign_manager import CampaignManager
from .validation_engine import ValidationEngine
