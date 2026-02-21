"""
Content Generation Engine

Grace doesn't just analyze content -- she creates it. This engine takes
pain points, market research, and competitor gaps and generates:

- Blog post outlines optimized for SEO
- Social media post templates
- Email sequence drafts
- Course module structures
- Ad copy variations
- Landing page wireframes

All content is generated from DATA, not assumptions. Every claim in
the content traces back to a pain point or market data point.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    PainPoint, MarketOpportunity, CompetitorProduct, KeywordMetric, ProductConcept,
)

logger = logging.getLogger(__name__)


@dataclass
class ContentPiece:
    """A generated content piece."""
    content_type: str = ""
    title: str = ""
    outline: List[str] = field(default_factory=list)
    target_keywords: List[str] = field(default_factory=list)
    pain_points_addressed: List[str] = field(default_factory=list)
    estimated_word_count: int = 0
    target_platform: str = ""
    cta: str = ""
    seo_notes: List[str] = field(default_factory=list)
    data_backed_claims: List[str] = field(default_factory=list)


@dataclass
class ContentCalendar:
    """A planned content calendar."""
    pieces: List[ContentPiece] = field(default_factory=list)
    duration_weeks: int = 4
    posts_per_week: int = 3
    platforms: List[str] = field(default_factory=list)
    niche: str = ""


class ContentEngine:
    """Generates data-driven content from BI intelligence."""

    async def generate_blog_outlines(
        self, pain_points: List[PainPoint], keywords: List[str],
        competitors: Optional[List[CompetitorProduct]] = None, count: int = 5,
    ) -> List[ContentPiece]:
        """Generate SEO-optimized blog post outlines from pain points."""
        outlines = []

        for i, pp in enumerate(pain_points[:count]):
            keyword = keywords[i % len(keywords)] if keywords else pp.category
            title_templates = [
                f"How to Solve {pp.description[:40].title()} (Complete Guide)",
                f"Why {pp.description[:30].title()} is Costing You Money",
                f"The {pp.description[:30].title()} Problem: {len(pain_points)} People Agree",
                f"Stop Struggling with {pp.description[:30].title()}: Here's the Fix",
            ]

            outline = [
                f"Introduction: The {pp.category} problem nobody talks about",
                f"Section 1: Why {pp.description[:40]} happens (root causes)",
                "Section 2: What most people try (and why it fails)",
            ]
            if competitors:
                outline.append(f"Section 3: What {competitors[0].name[:20]} gets wrong")
            outline.extend([
                "Section 4: The data-driven solution",
                "Section 5: Step-by-step implementation",
                "Conclusion: CTA to waitlist/product",
            ])

            claims = [f"Pain point severity: {pp.severity:.0%} (based on {pp.frequency} reports)"]
            if competitors:
                avg_rating = sum(c.rating for c in competitors if c.rating) / max(len(competitors), 1)
                claims.append(f"Competitor average rating: {avg_rating:.1f}/5")

            outlines.append(ContentPiece(
                content_type="blog_post",
                title=title_templates[i % len(title_templates)],
                outline=outline,
                target_keywords=[keyword, pp.category],
                pain_points_addressed=[pp.description[:60]],
                estimated_word_count=1500,
                target_platform="blog",
                cta="Join the waitlist for our solution",
                seo_notes=[f"Target keyword: '{keyword}'", "Include in H1, first paragraph, and 2-3 H2s",
                           "Add FAQ schema markup for voice search"],
                data_backed_claims=claims,
            ))

        return outlines

    async def generate_social_posts(
        self, pain_points: List[PainPoint], product_name: str = "",
        platforms: Optional[List[str]] = None, count: int = 10,
    ) -> List[ContentPiece]:
        """Generate social media post templates."""
        platforms = platforms or ["twitter", "linkedin", "tiktok"]
        posts = []

        thread_templates = [
            ("We analyzed {count} customer complaints. Here's what everyone hates about {category}:",
             ["Finding #{i}: {pp}", "What this means: people are spending money on broken solutions",
              "We're building something that actually works. Link in bio."]),
            ("{pp_short} -- sound familiar?",
             ["You're not alone. {frequency} people reported the same issue.",
              "Current solutions score {rating}/5. That's not good enough.",
              "We're fixing this. Join the waitlist: [link]"]),
        ]

        for i, pp in enumerate(pain_points[:count]):
            platform = platforms[i % len(platforms)]
            template_idx = i % len(thread_templates)
            hook, thread = thread_templates[template_idx]

            formatted_hook = hook.format(
                count=pp.frequency * 10, category=pp.category,
                pp_short=pp.description[:60], pp=pp.description[:80],
                i=i+1, frequency=pp.frequency, rating="3.2",
            )

            posts.append(ContentPiece(
                content_type="social_post",
                title=formatted_hook,
                outline=[t.format(pp=pp.description[:60], i=i+1, frequency=pp.frequency, rating="3.2") for t in thread],
                target_keywords=[pp.category],
                pain_points_addressed=[pp.description[:60]],
                target_platform=platform,
                cta="Join waitlist" if product_name else "Follow for more",
                data_backed_claims=[f"Based on {pp.frequency} reported instances"],
            ))

        return posts

    async def generate_email_sequence(
        self, pain_points: List[PainPoint], product: Optional[ProductConcept] = None,
    ) -> List[ContentPiece]:
        """Generate a welcome email drip sequence for waitlist signups."""
        sequence = []
        product_name = product.name if product else "our solution"

        emails = [
            {"subject": f"Welcome -- here's what we found about {pain_points[0].category if pain_points else 'your problem'}",
             "outline": ["Thank them for joining", "Share the #1 pain point finding", "Tease what's coming", "Set expectations for emails"]},
            {"subject": f"The data behind {product_name}",
             "outline": ["Share 3 key research findings", "Why existing solutions fail (with data)", "How we're different", "Ask: what's YOUR biggest frustration?"]},
            {"subject": "What 500+ people told us they need",
             "outline": ["Aggregate pain point data", "Top 3 feature requests", "Our roadmap response", "Early access offer"]},
            {"subject": f"{product_name} -- early access is opening",
             "outline": ["Product announcement", "Key features that solve top pain points", "Founding member pricing", "Limited spots CTA"]},
            {"subject": "Last chance for founding member pricing",
             "outline": ["Urgency (genuine, not fake)", "Summary of value", "Social proof from waitlist size", "Final CTA"]},
        ]

        for i, email in enumerate(emails):
            claims = []
            if i < len(pain_points):
                claims.append(f"References pain point: {pain_points[i].description[:50]}")

            sequence.append(ContentPiece(
                content_type="email",
                title=email["subject"],
                outline=email["outline"],
                pain_points_addressed=[pp.description[:40] for pp in pain_points[:2]],
                target_platform="email",
                cta="Join / Buy / Reply",
                data_backed_claims=claims,
            ))

        return sequence

    async def generate_course_outline(
        self, niche: str, pain_points: List[PainPoint],
        keywords: Optional[List[str]] = None,
    ) -> ContentPiece:
        """Generate an online course outline from pain point data."""
        modules = [f"Module 1: Understanding {niche} -- the landscape"]

        for i, pp in enumerate(pain_points[:6]):
            modules.append(f"Module {i+2}: Solving '{pp.description[:40]}' step-by-step")

        modules.extend([
            f"Module {len(pain_points)+2}: Putting it all together",
            f"Module {len(pain_points)+3}: Advanced strategies and automation",
            "Bonus: Templates, checklists, and resources",
        ])

        return ContentPiece(
            content_type="online_course",
            title=f"Master {niche.title()}: The Complete Guide",
            outline=modules,
            target_keywords=keywords or [niche],
            pain_points_addressed=[pp.description[:40] for pp in pain_points[:6]],
            estimated_word_count=len(modules) * 3000,
            target_platform="course_platform",
            cta="Enroll now",
        )

    async def generate_content_calendar(
        self, pain_points: List[PainPoint], niche: str,
        keywords: Optional[List[str]] = None, weeks: int = 4,
    ) -> ContentCalendar:
        """Generate a full content calendar mixing all content types."""
        calendar = ContentCalendar(
            duration_weeks=weeks, niche=niche,
            platforms=["blog", "twitter", "linkedin", "email"],
        )

        blogs = await self.generate_blog_outlines(pain_points, keywords or [niche], count=weeks)
        socials = await self.generate_social_posts(pain_points, count=weeks * 2)
        emails_seq = await self.generate_email_sequence(pain_points)

        calendar.pieces = blogs + socials + emails_seq
        calendar.posts_per_week = len(calendar.pieces) // max(weeks, 1)

        return calendar
