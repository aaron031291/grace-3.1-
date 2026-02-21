"""
Dynamic Creative Optimization (DCO) Module

Real-time ad creative editing and optimization. This addresses the question:
"Are there mechanisms to edit your ad in real-time -- keywords, format,
styling, font size, position of images?"

The answer: YES, through multiple channels:

1. Meta Dynamic Creative API: Feeds multiple creative assets (headlines,
   images, descriptions, CTAs) and Meta's algorithm automatically tests
   combinations per impression. No manual A/B testing needed.

2. TikTok Symphony: AI-powered creative generation with script generation
   and video creation tools.

3. Google Responsive Ads: Automatically combines headlines and descriptions.

4. Canva Connect API: Programmatic design editing (fonts, images, layout).

5. AdCreative.ai API: AI-generated ad creatives with customizable
   text, colors, images, and positioning.

This module orchestrates all of these to give Grace the ability to
generate, test, and optimize ad creatives programmatically.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


@dataclass
class CreativeAsset:
    """A single creative asset (image, video, text, etc)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    asset_type: str = ""  # image, video, headline, body_text, description, cta
    content: str = ""
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CreativeVariation:
    """A complete ad creative variation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    platform: str = ""
    headlines: List[str] = field(default_factory=list)
    body_texts: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    videos: List[Dict[str, Any]] = field(default_factory=list)
    ctas: List[str] = field(default_factory=list)
    style: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    status: str = "draft"


@dataclass
class DynamicCreativeSpec:
    """Specification for a Meta Dynamic Creative ad."""
    campaign_objective: str = "OUTCOME_TRAFFIC"
    asset_feed: Dict[str, Any] = field(default_factory=dict)
    optimization_goal: str = "CONVERSIONS"
    platform_specs: Dict[str, Any] = field(default_factory=dict)


# Platform-specific creative specs
PLATFORM_CREATIVE_SPECS = {
    "meta": {
        "headline_limit": 5,
        "body_limit": 5,
        "description_limit": 5,
        "image_limit": 10,
        "video_limit": 10,
        "cta_options": [
            "LEARN_MORE", "SIGN_UP", "SHOP_NOW", "GET_OFFER",
            "BOOK_TRAVEL", "CONTACT_US", "DOWNLOAD", "APPLY_NOW",
        ],
        "dynamic_creative": True,
        "auto_combination": True,
    },
    "tiktok": {
        "headline_limit": 1,
        "body_limit": 1,
        "video_required": True,
        "cta_options": [
            "LEARN_MORE", "SIGN_UP", "SHOP_NOW", "DOWNLOAD",
            "CONTACT_US", "GET_QUOTE", "SUBSCRIBE",
        ],
        "symphony_available": True,
    },
    "google": {
        "headline_limit": 15,
        "description_limit": 4,
        "responsive_search_ads": True,
        "responsive_display_ads": True,
    },
    "youtube": {
        "headline_limit": 1,
        "body_limit": 2,
        "video_required": True,
        "companion_banner": True,
    },
}


class DynamicCreativeEngine:
    """Manages dynamic creative optimization across platforms."""

    def __init__(self):
        self.variations: List[CreativeVariation] = []
        self.performance_data: Dict[str, Dict] = {}

    async def generate_meta_dynamic_creative(
        self,
        headlines: List[str],
        body_texts: List[str],
        descriptions: List[str],
        image_urls: Optional[List[str]] = None,
        ctas: Optional[List[str]] = None,
        target_audience: Optional[Dict] = None,
    ) -> DynamicCreativeSpec:
        """Generate a Meta Dynamic Creative specification.

        Meta will automatically test all combinations of:
        - Up to 5 headlines
        - Up to 5 body texts
        - Up to 5 descriptions
        - Up to 10 images
        - Multiple CTAs

        The algorithm learns which combination works best for each
        audience segment and optimizes delivery in real-time.
        """
        spec = PLATFORM_CREATIVE_SPECS["meta"]
        headlines = headlines[:spec["headline_limit"]]
        body_texts = body_texts[:spec["body_limit"]]
        descriptions = descriptions[:spec["description_limit"]]

        total_combinations = len(headlines) * len(body_texts) * len(descriptions)
        if ctas:
            total_combinations *= len(ctas)
        if image_urls:
            total_combinations *= len(image_urls)

        asset_feed = {
            "titles": [{"text": h} for h in headlines],
            "bodies": [{"text": b} for b in body_texts],
            "descriptions": [{"text": d} for d in descriptions],
            "call_to_action_types": ctas or ["LEARN_MORE", "SIGN_UP"],
        }

        if image_urls:
            asset_feed["images"] = [{"url": url} for url in image_urls[:spec["image_limit"]]]

        creative_spec = DynamicCreativeSpec(
            asset_feed=asset_feed,
            platform_specs={
                "total_combinations": total_combinations,
                "platform": "meta",
                "dynamic_creative_enabled": True,
                "optimization": "Meta's algorithm will test all combinations per impression",
                "estimated_learning_period": "3-7 days",
                "minimum_budget": "Recommended: 50+ GBP for sufficient data",
            },
        )

        logger.info(
            f"Meta Dynamic Creative spec generated: "
            f"{total_combinations} possible combinations"
        )

        return creative_spec

    async def generate_creative_variations(
        self,
        pain_points: List[str],
        product_name: str,
        platform: str = "meta",
        num_headlines: int = 5,
        num_bodies: int = 3,
    ) -> CreativeVariation:
        """Auto-generate creative variations from pain points.

        Takes identified pain points and generates multiple headline/body
        combinations for the platform's DCO system to test.
        """
        headlines = []
        bodies = []
        descriptions = []

        headline_templates = [
            "Still dealing with {pain}?",
            "{pain}? Fixed.",
            "Stop wasting time on {pain}",
            "The {pain} solution you've been looking for",
            "What if {pain} wasn't a problem anymore?",
            "{product}: because {pain} shouldn't be this hard",
            "We built {product} because we got tired of {pain}",
        ]

        body_templates = [
            "We analyzed hundreds of real complaints about {pain}. Then we built {product} to solve every single one. Join the waitlist.",
            "{product} addresses {pain} at its root. Built from actual customer feedback, not guesswork. See why people are switching.",
            "Tired of {pain}? You're not alone. {product} was designed from the ground up to eliminate this problem. Try it free.",
        ]

        for i, pp in enumerate(pain_points[:num_headlines]):
            short_pain = pp[:40].rstrip(".")
            template = headline_templates[i % len(headline_templates)]
            headlines.append(
                template.format(pain=short_pain, product=product_name)
            )

        if len(headlines) < num_headlines:
            headlines.append(f"{product_name}: Built from real feedback")
            headlines.append(f"Join {product_name} — waitlist open now")

        for i, pp in enumerate(pain_points[:num_bodies]):
            template = body_templates[i % len(body_templates)]
            bodies.append(
                template.format(pain=pp[:60].rstrip("."), product=product_name)
            )

        descriptions = [
            f"Built from real customer feedback.",
            f"Join the {product_name} waitlist today.",
            f"No spam. We'll only email when it's ready.",
        ]

        variation = CreativeVariation(
            name=f"{product_name}_{platform}_dynamic",
            platform=platform,
            headlines=headlines[:num_headlines],
            body_texts=bodies[:num_bodies],
            descriptions=descriptions,
            ctas=["SIGN_UP", "LEARN_MORE"],
            style={
                "tone": "direct_honest",
                "compliance": "No false scarcity, no manipulation, factual claims only",
            },
        )

        self.variations.append(variation)
        return variation

    async def get_canva_creative_spec(
        self,
        template_type: str = "social_ad",
        text_content: Optional[Dict[str, str]] = None,
        brand_colors: Optional[List[str]] = None,
        image_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a specification for Canva Connect API.

        Canva's API allows programmatic design creation/editing:
        - Autofill designs with dynamic content
        - Bulk create personalized variations
        - Modify text, images, colors, layout elements

        Requirements: Canva API key (from canva.dev)
        """
        return {
            "platform": "canva",
            "api": "Canva Connect API",
            "endpoint": "https://api.canva.com/rest/v1/designs",
            "capabilities": {
                "autofill": "Replace template text/images with dynamic content",
                "bulk_create": "Generate multiple variations from one template",
                "edit_text": "Modify font, size, color, position of text elements",
                "edit_images": "Replace, resize, reposition images",
                "edit_layout": "Adjust element positions and sizes",
                "export": "Export as PNG, JPG, PDF, MP4 at various resolutions",
            },
            "spec": {
                "template_type": template_type,
                "text_content": text_content or {},
                "brand_colors": brand_colors or [],
                "image_urls": image_urls or [],
            },
            "setup_required": {
                "api_key": "CANVA_API_KEY",
                "docs": "https://www.canva.dev/docs/connect/",
                "note": "Canva API allows real-time font/color/image/layout editing programmatically",
            },
        }

    async def get_adcreative_ai_spec(
        self,
        headlines: List[str],
        target_platform: str = "facebook",
        brand_colors: Optional[List[str]] = None,
        logo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate specification for AdCreative.ai API.

        AdCreative.ai provides:
        - AI-generated ad creatives
        - Customizable text (headlines, punchlines, CTAs)
        - Color customization (hex format)
        - Image editing (background, logos, positioning)
        - Performance prediction scoring

        Requirements: AdCreative.ai API key
        """
        return {
            "platform": "adcreative_ai",
            "api": "AdCreative.ai API",
            "endpoint": "https://api.adcreative.ai/v1/creatives",
            "capabilities": {
                "generate": "AI generates ad creatives from text inputs",
                "customize_text": "Edit headlines, punchlines, CTAs dynamically",
                "customize_colors": "Set brand colors in hex format",
                "customize_images": "Replace background images, logos, product images",
                "performance_score": "AI predicts creative performance before running",
                "regenerate": "Modify and regenerate selected creatives",
            },
            "spec": {
                "headlines": headlines,
                "platform": target_platform,
                "brand_colors": brand_colors or [],
                "logo_url": logo_url,
            },
            "setup_required": {
                "api_key": "ADCREATIVE_API_KEY",
                "docs": "https://api-docs.adcreative.ai/",
                "note": "AI-powered creative generation with real-time text/image/color editing",
            },
        }

    async def build_creative_pipeline(
        self,
        pain_points: List[str],
        product_name: str,
        platforms: List[str],
        budget: float = 100.0,
    ) -> Dict[str, Any]:
        """Build a complete creative pipeline across all platforms.

        This is the full answer to 'can we edit ads in real time':
        each platform has different capabilities for dynamic creative.
        """
        pipeline = {
            "product": product_name,
            "platforms": {},
            "total_combinations": 0,
            "creative_tools": [],
            "timeline": [],
        }

        for platform in platforms:
            if platform in ("meta", "facebook", "instagram"):
                variation = await self.generate_creative_variations(
                    pain_points, product_name, "meta"
                )
                dco_spec = await self.generate_meta_dynamic_creative(
                    headlines=variation.headlines,
                    body_texts=variation.body_texts,
                    descriptions=variation.descriptions,
                )
                pipeline["platforms"]["meta"] = {
                    "type": "Dynamic Creative Optimization",
                    "how_it_works": (
                        "You provide up to 5 headlines, 5 body texts, 5 descriptions, "
                        "10 images, and multiple CTAs. Meta's algorithm automatically "
                        "tests EVERY combination and learns which works best for each "
                        "person seeing the ad. Real-time optimization per impression."
                    ),
                    "headlines": variation.headlines,
                    "bodies": variation.body_texts,
                    "descriptions": variation.descriptions,
                    "total_combinations": dco_spec.platform_specs["total_combinations"],
                    "real_time_editing": True,
                    "auto_optimization": True,
                    "api": "Marketing API - asset_feed_spec with dynamic creative",
                }
                pipeline["total_combinations"] += dco_spec.platform_specs["total_combinations"]

            elif platform == "tiktok":
                pipeline["platforms"]["tiktok"] = {
                    "type": "TikTok Symphony + Marketing API",
                    "how_it_works": (
                        "TikTok Symphony generates video scripts and draft videos "
                        "using AI. The Marketing API allows programmatic ad creation, "
                        "updating, and optimization. Creative Center provides trending "
                        "keyword and format insights for each industry."
                    ),
                    "capabilities": [
                        "AI script generation from pain points",
                        "AI avatar video creation",
                        "Programmatic ad create/update/pause",
                        "Trending keyword integration",
                        "Auto-bidding optimization",
                    ],
                    "real_time_editing": True,
                    "api": "TikTok Marketing API - adCreate/adUpdate",
                }

            elif platform in ("google", "youtube"):
                pipeline["platforms"]["google"] = {
                    "type": "Google Responsive Ads",
                    "how_it_works": (
                        "Google Responsive Search Ads accept up to 15 headlines "
                        "and 4 descriptions. Google's ML automatically tests combinations "
                        "and learns which performs best for each search query. "
                        "Responsive Display Ads do the same for the display network."
                    ),
                    "capabilities": [
                        "Up to 15 headlines auto-combined",
                        "Up to 4 descriptions auto-combined",
                        "Automatic format/size adaptation",
                        "ML-optimized per query/placement",
                    ],
                    "real_time_editing": True,
                    "api": "Google Ads API - ResponsiveSearchAd / ResponsiveDisplayAd",
                }

        pipeline["creative_tools"] = [
            {
                "tool": "Meta Dynamic Creative",
                "cost": "Free (part of Meta Ads)",
                "what_it_edits": "Headlines, body text, images, CTAs — auto-combined",
                "real_time": True,
                "setup": "Included with Meta ad account",
            },
            {
                "tool": "Canva Connect API",
                "cost": "Canva Pro subscription + API access",
                "what_it_edits": "Font size, font style, colors, image position, layout, text content",
                "real_time": True,
                "setup": "API key from canva.dev",
            },
            {
                "tool": "AdCreative.ai",
                "cost": "Subscription-based",
                "what_it_edits": "Full creative generation — headlines, images, colors, layouts with AI",
                "real_time": True,
                "setup": "API key from adcreative.ai",
            },
            {
                "tool": "TikTok Symphony",
                "cost": "Free with TikTok Business account",
                "what_it_edits": "Video scripts, AI avatar videos, trending format adaptation",
                "real_time": True,
                "setup": "TikTok Business account + Marketing API access",
            },
        ]

        pipeline["timeline"] = [
            {"step": 1, "action": "Generate pain-point-based copy variations (Grace does this)"},
            {"step": 2, "action": "Feed into Meta DCO / Google Responsive — platforms auto-test combinations"},
            {"step": 3, "action": "Use Canva API / AdCreative.ai for visual creative generation"},
            {"step": 4, "action": "Monitor performance via ad optimizer — auto-pause losers"},
            {"step": 5, "action": "Refresh creatives every 7-14 days to prevent fatigue"},
        ]

        return pipeline
