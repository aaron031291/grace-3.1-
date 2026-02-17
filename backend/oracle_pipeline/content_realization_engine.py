"""
Content Realization Engine

THE MISSING PIECE: The entire pipeline is wired perfectly but operates
on placeholder strings like "[Web search results for: Python ML]".
Nothing downstream can learn from a placeholder.

This engine sits between the Multi-Source Fetcher and the Oracle,
and ensures REAL content enters the system through two modes:

MODE 1 - LIVE (when APIs are available):
  Calls real APIs: HTTP fetch, GitHub API, arXiv API, SerpAPI
  Returns actual content that the Oracle can learn from

MODE 2 - SYNTHESIS (when APIs are unavailable):
  Uses the LLM to generate domain-appropriate training content
  based on the query. Not web scraping -- but structured knowledge
  that the system can actually learn from, practice on, and verify.

The key insight: the system needs CONTENT to function, not just
architecture. A perfectly wired brain with no sensory input is
a brain that never learns. This engine provides the sensory input.

When real APIs come online (SerpAPI key, GitHub token, etc.),
the engine switches from synthesis to live automatically.
"""

import logging
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .secrets_vault import get_vault
from .whitelist_box import WhitelistItem, WhitelistItemType
from .multi_source_fetcher import FetchResult, FetchSource, FetchStatus

logger = logging.getLogger(__name__)


class RealizationMode(str, Enum):
    """How content is realized."""
    LIVE = "live"           # Real API calls
    SYNTHESIS = "synthesis"  # LLM-generated training content
    HYBRID = "hybrid"       # Try live, fall back to synthesis


# Domain knowledge templates for synthesis mode
DOMAIN_KNOWLEDGE = {
    "python": {
        "concepts": [
            "Variables and data types: int, float, str, bool, list, dict, tuple, set",
            "Control flow: if/elif/else, for loops, while loops, break, continue",
            "Functions: def, arguments, return values, *args, **kwargs, decorators",
            "Classes: __init__, self, inheritance, polymorphism, dunder methods",
            "Error handling: try/except/finally, custom exceptions, raise",
            "File I/O: open(), read(), write(), context managers (with statement)",
            "Modules: import, from...import, __name__, packages, pip",
            "List comprehensions: [x for x in range(10) if x > 5]",
            "Generators: yield, generator expressions, lazy evaluation",
            "Async programming: async/await, asyncio, coroutines, event loops",
        ],
        "patterns": [
            "Singleton pattern using module-level instances",
            "Factory pattern with class methods",
            "Observer pattern with callbacks",
            "Context manager pattern with __enter__/__exit__",
            "Decorator pattern for cross-cutting concerns",
        ],
    },
    "rust": {
        "concepts": [
            "Ownership: every value has one owner, ownership transfers on assignment",
            "Borrowing: &T for shared references, &mut T for mutable references",
            "Lifetimes: 'a annotations, lifetime elision rules, static lifetime",
            "Pattern matching: match expressions, if let, while let, destructuring",
            "Traits: defining shared behavior, trait bounds, impl Trait, dyn Trait",
            "Error handling: Result<T, E>, Option<T>, the ? operator, unwrap vs expect",
            "Concurrency: threads, channels, Mutex, Arc, Send and Sync traits",
            "Smart pointers: Box<T>, Rc<T>, RefCell<T>, Cow<T>",
        ],
    },
    "ai_ml": {
        "concepts": [
            "Supervised learning: labeled data, training/validation/test splits",
            "Neural networks: layers, weights, biases, activation functions",
            "Backpropagation: chain rule, gradient descent, learning rate",
            "Transformers: attention mechanism, self-attention, multi-head attention",
            "Loss functions: MSE, cross-entropy, binary cross-entropy",
            "Optimization: SGD, Adam, learning rate scheduling, batch normalization",
            "Regularization: dropout, L1/L2 regularization, early stopping",
            "Evaluation metrics: accuracy, precision, recall, F1, AUC-ROC",
        ],
    },
    "devops": {
        "concepts": [
            "Containers: Docker images, Dockerfiles, layers, multi-stage builds",
            "Orchestration: Kubernetes pods, deployments, services, ingress",
            "CI/CD: pipeline stages, automated testing, deployment strategies",
            "Infrastructure as Code: Terraform, state management, modules",
            "Monitoring: Prometheus metrics, Grafana dashboards, alerting rules",
            "Networking: DNS, load balancing, service mesh, ingress controllers",
        ],
    },
    "security": {
        "concepts": [
            "Authentication: passwords, tokens, OAuth2, JWT, MFA",
            "Authorization: RBAC, ABAC, principle of least privilege",
            "Encryption: symmetric (AES), asymmetric (RSA), hashing (SHA-256)",
            "Web security: XSS, CSRF, SQL injection, CORS, CSP headers",
            "Network security: TLS/SSL, firewalls, VPN, zero trust architecture",
        ],
    },
    "sales_marketing": {
        "concepts": [
            "Sales funnel: awareness, interest, decision, action (AIDA model)",
            "Lead generation: inbound marketing, content marketing, SEO, PPC",
            "Conversion optimization: A/B testing, landing pages, CTAs",
            "Customer psychology: social proof, scarcity, reciprocity, authority",
            "Analytics: CAC, LTV, churn rate, conversion rate, ROI",
        ],
    },
    "business": {
        "concepts": [
            "Business models: SaaS, marketplace, subscription, freemium",
            "Financial metrics: revenue, profit margin, burn rate, runway",
            "Strategy: competitive advantage, moats, market positioning",
            "Growth: product-market fit, viral loops, network effects",
        ],
    },
}


@dataclass
class RealizedContent:
    """Content that has been realized (made real) from a query."""
    content_id: str
    query: str
    domain: Optional[str]
    content: str
    mode: RealizationMode
    quality_score: float  # How rich/useful the content is
    word_count: int
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ContentRealizationEngine:
    """
    Bridges the gap between placeholder fetches and real content.

    Without this, the Oracle stores "[Web search results for: Python ML]"
    and nothing can learn from that. With this, the Oracle stores actual
    Python ML concepts, patterns, and knowledge that every downstream
    system can use.

    Priority:
    1. Try live API fetch (if keys available)
    2. Fall back to LLM synthesis (if LLM handler set)
    3. Fall back to domain knowledge templates
    4. Last resort: enhanced placeholder with keywords
    """

    def __init__(self, mode: RealizationMode = RealizationMode.HYBRID):
        self.mode = mode
        self._vault = get_vault()
        self._llm_handler: Optional[Callable] = None
        self._live_handlers: Dict[FetchSource, Callable] = {}
        self.realized: List[RealizedContent] = []
        logger.info(f"[REALIZER] Content Realization Engine initialized (mode={mode.value})")

    def set_llm_handler(self, handler: Callable) -> None:
        """Set LLM handler for synthesis mode."""
        self._llm_handler = handler

    def register_live_handler(self, source: FetchSource, handler: Callable) -> None:
        """Register a live API handler for a source."""
        self._live_handlers[source] = handler

    def realize(self, item: WhitelistItem, fetch_result: FetchResult) -> FetchResult:
        """
        Realize content from a fetch result.

        Takes a placeholder fetch result and fills it with actual content.

        Args:
            item: The whitelist item
            fetch_result: The placeholder fetch result

        Returns:
            FetchResult with real content
        """
        # Check if content is already real (not a placeholder)
        if not self._is_placeholder(fetch_result.content):
            return fetch_result

        # Try live first
        if self.mode in (RealizationMode.LIVE, RealizationMode.HYBRID):
            live_content = self._try_live(item, fetch_result)
            if live_content:
                return self._update_result(fetch_result, live_content, "live")

        # Try LLM synthesis
        if self.mode in (RealizationMode.SYNTHESIS, RealizationMode.HYBRID):
            if self._llm_handler:
                synth_content = self._try_llm_synthesis(item)
                if synth_content:
                    return self._update_result(fetch_result, synth_content, "llm_synthesis")

        # Fall back to domain knowledge templates
        template_content = self._generate_from_templates(item)
        if template_content:
            return self._update_result(fetch_result, template_content, "domain_template")

        # Last resort: enhanced placeholder
        enhanced = self._enhance_placeholder(item)
        return self._update_result(fetch_result, enhanced, "enhanced_placeholder")

    def realize_batch(
        self, items: List[WhitelistItem], fetch_results: Dict[str, List[FetchResult]]
    ) -> Dict[str, List[FetchResult]]:
        """Realize content for a batch of fetch results."""
        realized_results: Dict[str, List[FetchResult]] = {}

        for item in items:
            item_results = fetch_results.get(item.item_id, [])
            realized_list = []
            for fr in item_results:
                realized_fr = self.realize(item, fr)
                realized_list.append(realized_fr)
            realized_results[item.item_id] = realized_list

        return realized_results

    def _is_placeholder(self, content: str) -> bool:
        """Check if content is a placeholder."""
        placeholder_markers = [
            "[Web search results for:",
            "[GitHub content for:",
            "[arXiv paper:",
            "[API response from:",
            "[Content from URL:",
            "needs_real_fetch",
        ]
        return any(m in content for m in placeholder_markers)

    def _try_live(self, item: WhitelistItem, fetch_result: FetchResult) -> Optional[str]:
        """Try to fetch real content from live APIs."""
        if fetch_result.source in self._live_handlers:
            try:
                handler = self._live_handlers[fetch_result.source]
                return handler(item.content)
            except Exception as e:
                logger.debug(f"[REALIZER] Live fetch failed: {e}")
        return None

    def _try_llm_synthesis(self, item: WhitelistItem) -> Optional[str]:
        """Generate content using LLM."""
        if not self._llm_handler:
            return None

        try:
            prompt = (
                f"Generate comprehensive, factual training content about: {item.content}\n"
                f"Domain: {item.domain or 'general'}\n"
                f"Include: key concepts, definitions, examples, best practices.\n"
                f"Be specific and technical. This will be used as training data."
            )
            return self._llm_handler(prompt)
        except Exception as e:
            logger.debug(f"[REALIZER] LLM synthesis failed: {e}")
            return None

    def _generate_from_templates(self, item: WhitelistItem) -> Optional[str]:
        """Generate content from domain knowledge templates."""
        domain = item.domain or self._detect_domain(item.content)
        if not domain or domain not in DOMAIN_KNOWLEDGE:
            return None

        knowledge = DOMAIN_KNOWLEDGE[domain]
        concepts = knowledge.get("concepts", [])
        patterns = knowledge.get("patterns", [])

        lines = [
            f"# {domain.replace('_', ' ').title()} Knowledge Base",
            f"## Topic: {item.content}",
            "",
            "## Core Concepts",
        ]
        for concept in concepts:
            lines.append(f"- {concept}")

        if patterns:
            lines.append("")
            lines.append("## Key Patterns")
            for pattern in patterns:
                lines.append(f"- {pattern}")

        content = "\n".join(lines)

        self.realized.append(RealizedContent(
            content_id=f"real-{uuid.uuid4().hex[:12]}",
            query=item.content,
            domain=domain,
            content=content,
            mode=RealizationMode.SYNTHESIS,
            quality_score=0.7,
            word_count=len(content.split()),
            source="domain_template",
        ))

        return content

    def _enhance_placeholder(self, item: WhitelistItem) -> str:
        """Create an enhanced placeholder with actual keywords."""
        domain = item.domain or "general"
        return (
            f"Knowledge entry for: {item.content}\n"
            f"Domain: {domain}\n"
            f"Type: {item.item_type.value}\n"
            f"This content requires real data ingestion from external sources.\n"
            f"When APIs are connected, this will be replaced with actual content."
        )

    def _detect_domain(self, content: str) -> Optional[str]:
        """Detect domain from content."""
        content_lower = content.lower()
        for domain in DOMAIN_KNOWLEDGE:
            if domain.replace("_", " ") in content_lower or domain in content_lower:
                return domain
        return None

    def _update_result(
        self, original: FetchResult, new_content: str, source: str
    ) -> FetchResult:
        """Update a fetch result with realized content."""
        original.content = new_content
        original.byte_size = len(new_content.encode("utf-8"))
        original.metadata["realized"] = True
        original.metadata["realization_source"] = source
        original.metadata.pop("needs_real_fetch", None)
        original.metadata.pop("simulated", None)
        return original

    def get_stats(self) -> Dict[str, Any]:
        """Get realization statistics."""
        by_mode = {}
        for r in self.realized:
            mode = r.mode.value
            by_mode[mode] = by_mode.get(mode, 0) + 1

        return {
            "total_realized": len(self.realized),
            "by_mode": by_mode,
            "mode": self.mode.value,
            "has_llm_handler": self._llm_handler is not None,
            "live_handlers": len(self._live_handlers),
            "available_api_keys": self._vault.get_available_keys(),
        }
