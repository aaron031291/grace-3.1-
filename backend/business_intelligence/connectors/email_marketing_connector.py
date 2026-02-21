"""
Email Marketing Connector

Integrates with SendGrid, Mailchimp, and ConvertKit APIs for:
- Sending drip email sequences to waitlist/customers
- Tracking open rates, click rates, unsubscribes
- Segmenting audiences based on behavior
- A/B testing email subject lines and content
- Feeding engagement data back into the BI loop

The email list is the single most valuable owned asset.
Every paid ad click should end with an email capture.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import MarketDataPoint, KeywordMetric, DataSource

logger = logging.getLogger(__name__)


class EmailMarketingConnector(BaseConnector):
    connector_name = "email_marketing"
    connector_version = "1.0.0"

    SENDGRID_API = "https://api.sendgrid.com/v3"
    MAILCHIMP_API = "https://us1.api.mailchimp.com/3.0"
    CONVERTKIT_API = "https://api.convertkit.com/v3"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.provider = config.extra.get("provider", "sendgrid")
        self.api_key = config.api_key
        self.list_id = config.extra.get("list_id")

    async def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            import aiohttp
            if self.provider == "sendgrid":
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.SENDGRID_API}/marketing/lists",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        return resp.status == 200
            return False
        except Exception as e:
            logger.error(f"Email marketing connection test failed: {e}")
            return False

    async def add_contact(
        self, email: str, first_name: str = "", tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Add a contact to the email list."""
        if not self.api_key:
            return {"status": "not_configured"}

        try:
            import aiohttp
            if self.provider == "sendgrid":
                contact = {"email": email}
                if first_name:
                    contact["first_name"] = first_name
                if custom_fields:
                    contact["custom_fields"] = custom_fields

                payload: Dict[str, Any] = {"contacts": [contact]}
                if self.list_id:
                    payload["list_ids"] = [self.list_id]

                async with aiohttp.ClientSession() as session:
                    async with session.put(
                        f"{self.SENDGRID_API}/marketing/contacts",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        return {"status": "added" if resp.status in (200, 202) else "error", "code": resp.status}
        except Exception as e:
            logger.error(f"Failed to add contact: {e}")
            return {"status": "error", "message": str(e)}

    async def send_email(
        self, to_email: str, subject: str, html_content: str,
        from_email: str = "", from_name: str = "Grace",
    ) -> Dict[str, Any]:
        """Send a single email via SendGrid."""
        if not self.api_key:
            return {"status": "not_configured"}

        try:
            import aiohttp
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email or "noreply@grace.ai", "name": from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.SENDGRID_API}/mail/send",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return {"status": "sent" if resp.status == 202 else "error", "code": resp.status}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_campaign_stats(self) -> List[Dict[str, Any]]:
        """Get email campaign statistics."""
        if not self.api_key:
            return []
        try:
            import aiohttp
            if self.provider == "sendgrid":
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.SENDGRID_API}/marketing/stats/automations",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            return (await resp.json()).get("results", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get email stats: {e}")
            return []

    async def collect_market_data(self, keywords, niche="", date_from=None, date_to=None):
        if not self.config.is_configured:
            return [MarketDataPoint(
                source=DataSource.MANUAL, category="system", metric_name="connector_status",
                metric_value=0.0, unit="status", niche=niche, keywords=keywords, confidence=0.0,
                metadata={"message": "Email marketing not configured. Set EMAIL_MARKETING_API_KEY.", "provider": self.provider},
            )]

        stats = await self.get_campaign_stats()
        data_points = []
        for stat in stats:
            metrics = stat.get("stats", {})
            data_points.append(MarketDataPoint(
                source=DataSource.MANUAL, category="email_performance",
                metric_name="campaign_stats", metric_value=float(metrics.get("delivered", 0)),
                unit="emails", niche=niche, keywords=keywords,
                metadata={"opens": metrics.get("opens", 0), "clicks": metrics.get("clicks", 0),
                           "unsubscribes": metrics.get("unsubscribes", 0),
                           "open_rate": metrics.get("open_rate", 0), "click_rate": metrics.get("click_rate", 0)},
            ))
        return data_points or [MarketDataPoint(source=DataSource.MANUAL, category="email_performance",
            metric_name="no_data", metric_value=0, niche=niche, keywords=keywords)]

    async def collect_keyword_metrics(self, keywords):
        return []
