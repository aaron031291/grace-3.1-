"""
Whitelist Box - Bulk Human Input Acceptance

The Whitelist Box is where humans put in:
- Links / URLs / API endpoints
- Authority figures (Tony Robbins, Alex Hormozi, etc.)
- Study materials, domains, code repos
- Science papers, documentation
- Bullet point lists of topics
- GitHub repos, arXiv papers
- File uploads (documents, code, data)

Accepts ALL parameter types. Bulk submission of 50+ items at once.
Everything submitted gets 100% trust because it's deterministic
(the user explicitly asked for it).
"""

import logging
import uuid
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WhitelistItemType(str, Enum):
    """Types of whitelist items."""
    URL = "url"
    GITHUB_REPO = "github_repo"
    ARXIV_PAPER = "arxiv_paper"
    AUTHORITY_FIGURE = "authority_figure"
    TOPIC = "topic"
    DOMAIN = "domain"
    CODE = "code"
    DOCUMENTATION = "documentation"
    FILE_UPLOAD = "file_upload"
    API_ENDPOINT = "api_endpoint"
    SEARCH_QUERY = "search_query"
    STUDY_MATERIAL = "study_material"
    SCIENCE_PAPER = "science_paper"
    BULLET_LIST = "bullet_list"
    RAW_TEXT = "raw_text"


@dataclass
class WhitelistItem:
    """A single item in the whitelist box."""
    item_id: str
    item_type: WhitelistItemType
    content: str
    label: Optional[str] = None
    domain: Optional[str] = None
    priority: int = 5  # 1-10
    trust_score: float = 1.0  # User-submitted = 100% trust
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, fetching, ingested, failed
    fetch_result: Optional[Dict[str, Any]] = None


@dataclass
class BulkSubmissionResult:
    """Result of a bulk whitelist submission."""
    submission_id: str
    total_items: int
    accepted: int
    rejected: int
    items: List[WhitelistItem]
    rejected_items: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WhitelistBox:
    """
    Bulk input acceptance box for human-curated learning sources.

    Accepts 50+ items at once. Parses bullet points, URLs, names,
    topics, code, files -- everything. Assigns 100% trust to all
    user-submitted content because it's deterministic.

    Features:
    - Auto-detect item type from content
    - Parse bullet point lists into individual items
    - Validate URLs, GitHub repos, arXiv IDs
    - Tag and categorize automatically
    - Support batch submission of 50+ items
    - Track submission status per item
    """

    MAX_BATCH_SIZE = 200
    GITHUB_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/[\w.-]+/[\w.-]+", re.IGNORECASE
    )
    ARXIV_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/[\d.]+", re.IGNORECASE
    )
    URL_PATTERN = re.compile(
        r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE
    )

    def __init__(self):
        self.items: Dict[str, WhitelistItem] = {}
        self.submissions: List[BulkSubmissionResult] = []
        logger.info("[WHITELIST-BOX] Initialized - ready for bulk input")

    def submit_bulk(
        self,
        raw_input: str,
        default_domain: Optional[str] = None,
        default_priority: int = 5,
        extra_tags: Optional[List[str]] = None,
    ) -> BulkSubmissionResult:
        """
        Submit bulk input. Parses text into individual items.

        Accepts:
        - Newline-separated items
        - Bullet point lists (-, *, 1.)
        - Comma-separated items
        - Mixed URLs, names, topics

        Args:
            raw_input: Raw text input (can be bullet points, URLs, etc.)
            default_domain: Default domain to assign
            default_priority: Default priority (1-10)
            extra_tags: Extra tags to add to all items

        Returns:
            BulkSubmissionResult
        """
        lines = self._parse_lines(raw_input)
        accepted_items: List[WhitelistItem] = []
        rejected_items: List[Dict[str, Any]] = []

        for line in lines:
            line = line.strip()
            if not line or len(line) < 2:
                continue

            if len(accepted_items) >= self.MAX_BATCH_SIZE:
                rejected_items.append({
                    "content": line,
                    "reason": f"Batch limit ({self.MAX_BATCH_SIZE}) reached",
                })
                continue

            try:
                item = self._create_item(
                    line, default_domain, default_priority, extra_tags
                )
                accepted_items.append(item)
                self.items[item.item_id] = item
            except Exception as e:
                rejected_items.append({"content": line, "reason": str(e)})

        result = BulkSubmissionResult(
            submission_id=f"sub-{uuid.uuid4().hex[:12]}",
            total_items=len(accepted_items) + len(rejected_items),
            accepted=len(accepted_items),
            rejected=len(rejected_items),
            items=accepted_items,
            rejected_items=rejected_items,
        )

        self.submissions.append(result)

        logger.info(
            f"[WHITELIST-BOX] Bulk submission: {result.accepted} accepted, "
            f"{result.rejected} rejected out of {result.total_items}"
        )

        return result

    def submit_items(
        self,
        items: List[Dict[str, Any]],
        default_domain: Optional[str] = None,
    ) -> BulkSubmissionResult:
        """
        Submit structured items directly.

        Args:
            items: List of dicts with at least 'content' key
            default_domain: Default domain

        Returns:
            BulkSubmissionResult
        """
        accepted: List[WhitelistItem] = []
        rejected: List[Dict[str, Any]] = []

        for item_data in items:
            content = item_data.get("content", "")
            if not content or len(content) < 2:
                rejected.append({"content": content, "reason": "Empty or too short"})
                continue

            item_type_str = item_data.get("type")
            if item_type_str:
                try:
                    item_type = WhitelistItemType(item_type_str)
                except ValueError:
                    item_type = self._detect_type(content)
            else:
                item_type = self._detect_type(content)

            item = WhitelistItem(
                item_id=f"wli-{uuid.uuid4().hex[:12]}",
                item_type=item_type,
                content=content,
                label=item_data.get("label"),
                domain=item_data.get("domain", default_domain),
                priority=item_data.get("priority", 5),
                tags=item_data.get("tags", []),
                metadata=item_data.get("metadata", {}),
            )
            accepted.append(item)
            self.items[item.item_id] = item

        result = BulkSubmissionResult(
            submission_id=f"sub-{uuid.uuid4().hex[:12]}",
            total_items=len(items),
            accepted=len(accepted),
            rejected=len(rejected),
            items=accepted,
            rejected_items=rejected,
        )
        self.submissions.append(result)
        return result

    def _parse_lines(self, raw_input: str) -> List[str]:
        """Parse raw input into individual lines/items."""
        lines = []
        for line in raw_input.split("\n"):
            line = line.strip()
            # Remove bullet markers
            line = re.sub(r"^[-*•]\s*", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            line = line.strip()
            if line:
                # Check if comma-separated (but not URLs with commas)
                if "," in line and not self.URL_PATTERN.search(line):
                    parts = [p.strip() for p in line.split(",") if p.strip()]
                    if len(parts) > 1 and all(len(p) > 2 for p in parts):
                        lines.extend(parts)
                        continue
                lines.append(line)
        return lines

    def _create_item(
        self,
        content: str,
        domain: Optional[str],
        priority: int,
        extra_tags: Optional[List[str]],
    ) -> WhitelistItem:
        """Create a whitelist item from content string."""
        item_type = self._detect_type(content)
        tags = list(extra_tags or [])
        tags.append(item_type.value)
        label = self._generate_label(content, item_type)

        # Auto-detect domain if not provided
        if domain is None:
            domain = self._detect_domain(content)

        return WhitelistItem(
            item_id=f"wli-{uuid.uuid4().hex[:12]}",
            item_type=item_type,
            content=content,
            label=label,
            domain=domain,
            priority=priority,
            tags=tags,
        )

    def _detect_type(self, content: str) -> WhitelistItemType:
        """Auto-detect the type of a whitelist item."""
        content_lower = content.lower().strip()

        if self.GITHUB_PATTERN.search(content):
            return WhitelistItemType.GITHUB_REPO
        if self.ARXIV_PATTERN.search(content):
            return WhitelistItemType.ARXIV_PAPER
        if self.URL_PATTERN.search(content):
            return WhitelistItemType.URL
        if content_lower.startswith("api:") or "endpoint" in content_lower:
            return WhitelistItemType.API_ENDPOINT
        if any(kw in content_lower for kw in ["def ", "class ", "import ", "function ", "```"]):
            return WhitelistItemType.CODE
        if any(kw in content_lower for kw in [".pdf", ".doc", ".txt", ".md", "upload"]):
            return WhitelistItemType.FILE_UPLOAD
        if any(kw in content_lower for kw in ["study", "course", "textbook", "tutorial", "learn"]):
            return WhitelistItemType.STUDY_MATERIAL
        if any(kw in content_lower for kw in ["paper", "research", "journal", "doi:", "abstract"]):
            return WhitelistItemType.SCIENCE_PAPER
        if any(kw in content_lower for kw in [
            "tony robbins", "alex hormozi", "elon musk", "sam altman",
            "andrew ng", "andrej karpathy", "author:", "by ",
        ]):
            return WhitelistItemType.AUTHORITY_FIGURE
        if any(kw in content_lower for kw in [
            "python", "rust", "javascript", "kubernetes", "docker",
            "machine learning", "ai", "quantum", "blockchain",
        ]):
            return WhitelistItemType.DOMAIN
        if len(content.split()) <= 5:
            return WhitelistItemType.TOPIC

        return WhitelistItemType.RAW_TEXT

    def _detect_domain(self, content: str) -> Optional[str]:
        """Auto-detect domain from content."""
        content_lower = content.lower()
        domain_keywords = {
            "python": ["python", "django", "flask", "fastapi", "pip"],
            "javascript": ["javascript", "nodejs", "react", "vue", "npm"],
            "rust": ["rust", "cargo", "tokio", "wasm"],
            "ai_ml": ["machine learning", "deep learning", "neural", "ai ", "llm", "transformer"],
            "devops": ["kubernetes", "docker", "ci/cd", "terraform", "ansible"],
            "security": ["security", "encryption", "vulnerability", "auth"],
            "sales_marketing": ["sales", "marketing", "advertising", "funnel", "conversion"],
            "science": ["quantum", "physics", "biology", "chemistry", "research"],
            "business": ["business", "startup", "entrepreneur", "revenue", "growth"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return domain
        return None

    def _generate_label(self, content: str, item_type: WhitelistItemType) -> str:
        """Generate a human-readable label."""
        if item_type == WhitelistItemType.URL:
            return content[:80]
        if item_type == WhitelistItemType.GITHUB_REPO:
            match = self.GITHUB_PATTERN.search(content)
            return match.group(0) if match else content[:80]
        words = content.split()[:8]
        return " ".join(words)

    def get_pending_items(self) -> List[WhitelistItem]:
        """Get all items pending processing."""
        return [i for i in self.items.values() if i.status == "pending"]

    def get_items_by_type(self, item_type: WhitelistItemType) -> List[WhitelistItem]:
        """Get items filtered by type."""
        return [i for i in self.items.values() if i.item_type == item_type]

    def get_items_by_domain(self, domain: str) -> List[WhitelistItem]:
        """Get items filtered by domain."""
        return [i for i in self.items.values() if i.domain == domain]

    def mark_item_status(self, item_id: str, status: str, result: Optional[Dict] = None) -> bool:
        """Update item status."""
        if item_id in self.items:
            self.items[item_id].status = status
            if result:
                self.items[item_id].fetch_result = result
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get whitelist box statistics."""
        items = list(self.items.values())
        by_type = {}
        for t in WhitelistItemType:
            count = sum(1 for i in items if i.item_type == t)
            if count > 0:
                by_type[t.value] = count
        by_status = {}
        for status in ["pending", "fetching", "ingested", "failed"]:
            count = sum(1 for i in items if i.status == status)
            if count > 0:
                by_status[status] = count

        return {
            "total_items": len(items),
            "total_submissions": len(self.submissions),
            "by_type": by_type,
            "by_status": by_status,
        }
