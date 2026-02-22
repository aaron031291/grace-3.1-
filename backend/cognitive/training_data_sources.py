"""
Training Data Source Registry

Defines all external data sources Grace can learn from.
The Oracle and training pipeline use this to discover, fetch,
and ingest knowledge from GitHub repos, APIs, and websites.

Each source has:
- URL and access method (git clone, API, scrape)
- Trust score (how reliable the source is)
- Category (what domain it covers)
- Priority (what order to ingest)
- Auto-refresh interval (how often to re-check)

Classes:
- `SourceType`
- `SourceCategory`
- `DataSource`
- `TrainingDataSourceRegistry`

Key Methods:
- `get_by_priority()`
- `get_by_category()`
- `get_by_type()`
- `get_github_repos()`
- `get_apis()`
- `get_websites()`
- `get_unfetched()`
- `get_stale()`
- `mark_fetched()`
- `get_stats()`
- `to_dict()`
- `get_training_source_registry()`

Database Tables:
None (no DB tables)

Connects To:
Self-contained
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    GITHUB_REPO = "github_repo"
    API = "api"
    WEBSITE = "website"
    DOCUMENTATION = "documentation"
    DATASET = "dataset"


class SourceCategory(str, Enum):
    AI_ML = "ai_ml"
    LLM = "llm"
    RAG = "rag"
    AGENTS = "agents"
    NEURO_SYMBOLIC = "neuro_symbolic"
    CODE_GENERATION = "code_generation"
    SOFTWARE_ENGINEERING = "software_engineering"
    DEVOPS = "devops"
    SECURITY = "security"
    WEB_DEV = "web_dev"
    ALGORITHMS = "algorithms"
    SYSTEM_DESIGN = "system_design"
    SELF_IMPROVING = "self_improving"


@dataclass
class DataSource:
    """A registered training data source."""
    name: str
    url: str
    source_type: SourceType
    category: SourceCategory
    trust_score: float = 0.8
    priority: int = 5  # 1=highest, 10=lowest
    description: str = ""
    access_method: str = "git_clone"  # git_clone, api_fetch, scrape, download
    api_key_required: bool = False
    free_tier: bool = True
    auto_refresh_hours: int = 168  # Weekly by default
    readme_path: str = "README.md"
    last_fetched: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# THE COMPLETE SOURCE REGISTRY
# ============================================================================

TRAINING_SOURCES: List[DataSource] = [
    # ======================== AI/ML FOUNDATIONS ========================
    DataSource("scikit-learn", "https://github.com/scikit-learn/scikit-learn", SourceType.GITHUB_REPO, SourceCategory.AI_ML, 0.95, 2, "Industry-standard ML library"),
    DataSource("XGBoost", "https://github.com/dmlc/xgboost", SourceType.GITHUB_REPO, SourceCategory.AI_ML, 0.90, 3, "Gradient boosting framework"),
    DataSource("LightGBM", "https://github.com/microsoft/LightGBM", SourceType.GITHUB_REPO, SourceCategory.AI_ML, 0.90, 3, "Microsoft fast gradient boosting"),

    # ======================== DEEP LEARNING ========================
    DataSource("PyTorch", "https://github.com/pytorch/pytorch", SourceType.GITHUB_REPO, SourceCategory.AI_ML, 0.95, 1, "Primary deep learning framework"),
    DataSource("Hugging Face Transformers", "https://github.com/huggingface/transformers", SourceType.GITHUB_REPO, SourceCategory.LLM, 0.95, 1, "THE library for pretrained models"),
    DataSource("JAX", "https://github.com/google/jax", SourceType.GITHUB_REPO, SourceCategory.AI_ML, 0.90, 3, "Google composable transformations"),

    # ======================== LARGE LANGUAGE MODELS ========================
    DataSource("Llama", "https://github.com/meta-llama/llama", SourceType.GITHUB_REPO, SourceCategory.LLM, 0.90, 2, "Meta open LLM"),
    DataSource("Ollama", "https://github.com/ollama/ollama", SourceType.GITHUB_REPO, SourceCategory.LLM, 0.90, 1, "Grace's LLM runtime"),
    DataSource("vLLM", "https://github.com/vllm-project/vllm", SourceType.GITHUB_REPO, SourceCategory.LLM, 0.85, 3, "High-throughput LLM serving"),
    DataSource("LangChain", "https://github.com/langchain-ai/langchain", SourceType.GITHUB_REPO, SourceCategory.LLM, 0.85, 2, "LLM application framework"),
    DataSource("LlamaIndex", "https://github.com/run-llama/llama_index", SourceType.GITHUB_REPO, SourceCategory.RAG, 0.85, 2, "Data framework for LLM apps"),
    DataSource("DeepSeek-Coder", "https://github.com/deepseek-ai/DeepSeek-Coder", SourceType.GITHUB_REPO, SourceCategory.CODE_GENERATION, 0.90, 1, "Grace's primary code model"),

    # ======================== RAG & VECTOR SEARCH ========================
    DataSource("Qdrant", "https://github.com/qdrant/qdrant", SourceType.GITHUB_REPO, SourceCategory.RAG, 0.90, 1, "Grace's vector database"),
    DataSource("FAISS", "https://github.com/facebookresearch/faiss", SourceType.GITHUB_REPO, SourceCategory.RAG, 0.90, 3, "Facebook similarity search"),
    DataSource("sentence-transformers", "https://github.com/UKPLab/sentence-transformers", SourceType.GITHUB_REPO, SourceCategory.RAG, 0.90, 2, "Embedding models"),

    # ======================== AI AGENTS ========================
    DataSource("AutoGPT", "https://github.com/Significant-Gravitas/AutoGPT", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.80, 2, "Autonomous AI agent"),
    DataSource("MetaGPT", "https://github.com/geekan/MetaGPT", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.80, 2, "Multi-agent framework"),
    DataSource("CrewAI", "https://github.com/crewAIInc/crewAI", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.80, 3, "AI agent orchestration"),
    DataSource("SWE-agent", "https://github.com/princeton-nlp/SWE-agent", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.85, 2, "Software engineering agent"),
    DataSource("Aider", "https://github.com/paul-gauthier/aider", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.85, 2, "AI pair programming"),
    DataSource("OpenDevin", "https://github.com/OpenDevin/OpenDevin", SourceType.GITHUB_REPO, SourceCategory.AGENTS, 0.80, 3, "Open-source coding agent"),

    # ======================== NEURO-SYMBOLIC ========================
    DataSource("Logic Tensor Networks", "https://github.com/logictensornetworks/logictensornetworks", SourceType.GITHUB_REPO, SourceCategory.NEURO_SYMBOLIC, 0.80, 4, "Neural + symbolic logic"),

    # ======================== SELF-IMPROVING SYSTEMS ========================
    DataSource("Voyager", "https://github.com/MineDojo/Voyager", SourceType.GITHUB_REPO, SourceCategory.SELF_IMPROVING, 0.85, 2, "LLM-powered continuous learning agent"),
    DataSource("BabyAGI", "https://github.com/yoheinakajima/babyagi", SourceType.GITHUB_REPO, SourceCategory.SELF_IMPROVING, 0.80, 3, "Task-driven autonomous agent"),

    # ======================== SOFTWARE ENGINEERING ========================
    DataSource("The Algorithms Python", "https://github.com/TheAlgorithms/Python", SourceType.GITHUB_REPO, SourceCategory.ALGORITHMS, 0.90, 1, "Every algorithm in Python"),
    DataSource("system-design-primer", "https://github.com/donnemartin/system-design-primer", SourceType.GITHUB_REPO, SourceCategory.SYSTEM_DESIGN, 0.90, 1, "Complete system design guide"),
    DataSource("coding-interview-university", "https://github.com/jwasham/coding-interview-university", SourceType.GITHUB_REPO, SourceCategory.ALGORITHMS, 0.85, 2, "CS fundamentals masterclass"),
    DataSource("build-your-own-x", "https://github.com/codecrafters-io/build-your-own-x", SourceType.GITHUB_REPO, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 2, "Build everything from scratch"),
    DataSource("awesome-python", "https://github.com/vinta/awesome-python", SourceType.GITHUB_REPO, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 3, "Curated Python libraries"),
    DataSource("Google Eng Practices", "https://github.com/google/eng-practices", SourceType.GITHUB_REPO, SourceCategory.SOFTWARE_ENGINEERING, 0.90, 1, "Code review and engineering standards"),
    DataSource("OWASP Cheat Sheets", "https://github.com/OWASP/CheatSheetSeries", SourceType.GITHUB_REPO, SourceCategory.SECURITY, 0.90, 1, "Security best practices"),

    # ======================== CODE QUALITY ========================
    DataSource("ruff", "https://github.com/astral-sh/ruff", SourceType.GITHUB_REPO, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 3, "Fast Python linter"),
    DataSource("pytest", "https://github.com/pytest-dev/pytest", SourceType.GITHUB_REPO, SourceCategory.SOFTWARE_ENGINEERING, 0.90, 2, "Python testing framework"),

    # ======================== WEB DEVELOPMENT ========================
    DataSource("FastAPI", "https://github.com/tiangolo/fastapi", SourceType.GITHUB_REPO, SourceCategory.WEB_DEV, 0.90, 1, "Grace's web framework"),
    DataSource("React", "https://github.com/facebook/react", SourceType.GITHUB_REPO, SourceCategory.WEB_DEV, 0.90, 2, "Grace's frontend framework"),

    # ======================== APIS (Free) ========================
    DataSource("GitHub API", "https://api.github.com", SourceType.API, SourceCategory.SOFTWARE_ENGINEERING, 0.90, 2, "Public repos, code search, trending", access_method="api_fetch", metadata={"rate_limit": "5000/hr with token"}),
    DataSource("Stack Exchange API", "https://api.stackexchange.com/2.3", SourceType.API, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 2, "Stack Overflow Q&A", access_method="api_fetch", metadata={"rate_limit": "10000/day with key"}),
    DataSource("PyPI API", "https://pypi.org/pypi", SourceType.API, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 4, "Python package metadata", access_method="api_fetch"),
    DataSource("npm Registry", "https://registry.npmjs.org", SourceType.API, SourceCategory.WEB_DEV, 0.85, 4, "JS package metadata", access_method="api_fetch"),

    # ======================== WEBSITES (Scrape) ========================
    DataSource("DevDocs.io", "https://devdocs.io", SourceType.WEBSITE, SourceCategory.SOFTWARE_ENGINEERING, 0.90, 1, "400+ language/framework docs", access_method="scrape"),
    DataSource("MDN Web Docs", "https://developer.mozilla.org", SourceType.DOCUMENTATION, SourceCategory.WEB_DEV, 0.95, 1, "Gold standard web docs", access_method="scrape"),
    DataSource("Real Python", "https://realpython.com", SourceType.WEBSITE, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 3, "In-depth Python tutorials", access_method="scrape"),
    DataSource("Refactoring Guru", "https://refactoring.guru", SourceType.WEBSITE, SourceCategory.SOFTWARE_ENGINEERING, 0.85, 3, "Design patterns & refactoring", access_method="scrape"),
    DataSource("Papers With Code", "https://paperswithcode.com", SourceType.WEBSITE, SourceCategory.AI_ML, 0.85, 3, "ML papers with implementations", access_method="scrape"),
    DataSource("freeCodeCamp", "https://freecodecamp.org/news", SourceType.WEBSITE, SourceCategory.SOFTWARE_ENGINEERING, 0.80, 4, "Thousands of free tutorials", access_method="scrape"),
    DataSource("Patterns.dev", "https://patterns.dev", SourceType.WEBSITE, SourceCategory.WEB_DEV, 0.85, 3, "Modern web design patterns", access_method="scrape"),
]


class TrainingDataSourceRegistry:
    """
    Registry and manager for all training data sources.

    The Oracle and training pipeline use this to:
    - Discover what sources are available
    - Prioritize what to fetch first
    - Track what's been fetched and when
    - Schedule re-fetches for freshness
    """

    def __init__(self):
        self.sources = {s.name: s for s in TRAINING_SOURCES}

    def get_by_priority(self, limit: int = 10) -> List[DataSource]:
        """Get top priority sources."""
        return sorted(self.sources.values(), key=lambda s: s.priority)[:limit]

    def get_by_category(self, category: SourceCategory) -> List[DataSource]:
        """Get all sources in a category."""
        return [s for s in self.sources.values() if s.category == category]

    def get_by_type(self, source_type: SourceType) -> List[DataSource]:
        """Get all sources of a type."""
        return [s for s in self.sources.values() if s.source_type == source_type]

    def get_github_repos(self) -> List[DataSource]:
        """Get all GitHub repos for cloning."""
        return self.get_by_type(SourceType.GITHUB_REPO)

    def get_apis(self) -> List[DataSource]:
        """Get all API sources."""
        return self.get_by_type(SourceType.API)

    def get_websites(self) -> List[DataSource]:
        """Get all scrapeable websites."""
        return [s for s in self.sources.values()
                if s.source_type in (SourceType.WEBSITE, SourceType.DOCUMENTATION)]

    def get_unfetched(self) -> List[DataSource]:
        """Get sources that haven't been fetched yet."""
        return [s for s in self.sources.values() if s.last_fetched is None]

    def get_stale(self, max_hours: int = 168) -> List[DataSource]:
        """Get sources that need refreshing."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_hours)
        return [s for s in self.sources.values()
                if s.last_fetched is None or s.last_fetched < cutoff]

    def mark_fetched(self, name: str):
        """Mark a source as fetched."""
        if name in self.sources:
            self.sources[name].last_fetched = datetime.now()

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_sources": len(self.sources),
            "github_repos": len(self.get_github_repos()),
            "apis": len(self.get_apis()),
            "websites": len(self.get_websites()),
            "unfetched": len(self.get_unfetched()),
            "categories": {cat.value: len(self.get_by_category(cat)) for cat in SourceCategory},
            "avg_trust_score": round(
                sum(s.trust_score for s in self.sources.values()) / max(len(self.sources), 1), 2
            ),
        }

    def to_dict(self) -> List[Dict[str, Any]]:
        """Export all sources as dicts."""
        return [
            {
                "name": s.name,
                "url": s.url,
                "type": s.source_type.value,
                "category": s.category.value,
                "trust": s.trust_score,
                "priority": s.priority,
                "description": s.description,
                "access_method": s.access_method,
                "fetched": s.last_fetched.isoformat() if s.last_fetched else None,
            }
            for s in sorted(self.sources.values(), key=lambda s: s.priority)
        ]


_registry: Optional[TrainingDataSourceRegistry] = None

def get_training_source_registry() -> TrainingDataSourceRegistry:
    """Get the training source registry singleton."""
    global _registry
    if _registry is None:
        _registry = TrainingDataSourceRegistry()
    return _registry
