"""
Settings module that loads configuration from environment variables.
Provides centralized configuration for the application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Get the backend directory
BACKEND_DIR = Path(__file__).parent

# Load environment variables from .env file
ENV_FILE = BACKEND_DIR / ".env"
load_dotenv(ENV_FILE)

# Module-level constants
KNOWLEDGE_BASE_PATH = str(BACKEND_DIR / "knowledge_base")


class Settings:
    """Application settings loaded from environment variables."""
    
    # ==================== Ollama Configuration ====================
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_LLM_DEFAULT: str = os.getenv("OLLAMA_LLM_DEFAULT", "qwen3.5:35b")
    
    # ==================== Embedding Configuration ====================
    EMBEDDING_DEFAULT: str = os.getenv("EMBEDDING_DEFAULT", "all-MiniLM-L6-v2")
    EMBEDDING_MODEL_PATH: str = str(BACKEND_DIR / "models" / "embedding" / EMBEDDING_DEFAULT)
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cuda")  # cuda or cpu
    EMBEDDING_NORMALIZE: bool = os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
    
    # ==================== Lightweight Mode & Component Disabling ====================
    LIGHTWEIGHT_MODE: bool = os.getenv("LIGHTWEIGHT_MODE", "false").lower() == "true"
    SKIP_EMBEDDING_LOAD: bool = os.getenv("SKIP_EMBEDDING_LOAD", "false").lower() == "true"
    SKIP_QDRANT_CHECK: bool = os.getenv("SKIP_QDRANT_CHECK", "false").lower() == "true"
    SKIP_OLLAMA_CHECK: bool = os.getenv("SKIP_OLLAMA_CHECK", "false").lower() == "true"
    SKIP_AUTO_INGESTION: bool = os.getenv("SKIP_AUTO_INGESTION", "false").lower() == "true"
    HEALING_SIMULATION_MODE: bool = os.getenv("HEALING_SIMULATION_MODE", "false").lower() == "true"
    
    # ==================== Error Handling Configuration ====================
    SUPPRESS_INGESTION_ERRORS: bool = os.getenv("SUPPRESS_INGESTION_ERRORS", "false").lower() == "true"
    
    # ==================== Genesis Key Tracking ====================
    DISABLE_GENESIS_TRACKING: bool = os.getenv("DISABLE_GENESIS_TRACKING", "false").lower() == "true"
    
    # ==================== Database Configuration ====================
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "postgresql")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "0")) or None
    DATABASE_USER: str = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "grace")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "grace.db"))
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DATABASE_SSLMODE: str = os.getenv("DATABASE_SSLMODE", "").strip() or ""
    
    # ==================== Qdrant Configuration ====================
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")
    QDRANT_TIMEOUT: int = int(os.getenv("QDRANT_TIMEOUT", "30"))
    
    # ==================== Ingestion Configuration ====================
    INGESTION_CHUNK_SIZE: int = int(os.getenv("INGESTION_CHUNK_SIZE", "512"))
    INGESTION_CHUNK_OVERLAP: int = int(os.getenv("INGESTION_CHUNK_OVERLAP", "50"))

    # ==================== Librarian System Configuration ====================
    LIBRARIAN_AUTO_PROCESS: bool = os.getenv("LIBRARIAN_AUTO_PROCESS", "true").lower() == "true"
    LIBRARIAN_USE_AI: bool = os.getenv("LIBRARIAN_USE_AI", "true").lower() == "true"
    LIBRARIAN_DETECT_RELATIONSHIPS: bool = os.getenv("LIBRARIAN_DETECT_RELATIONSHIPS", "true").lower() == "true"
    LIBRARIAN_AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("LIBRARIAN_AI_CONFIDENCE_THRESHOLD", "0.6"))
    LIBRARIAN_SIMILARITY_THRESHOLD: float = float(os.getenv("LIBRARIAN_SIMILARITY_THRESHOLD", "0.7"))
    LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES: int = int(os.getenv("LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES", "20"))
    LIBRARIAN_AI_MODEL: str = os.getenv("LIBRARIAN_AI_MODEL", "mistral:7b")

    # ==================== Application Configuration ====================
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_NUM_PREDICT: int = int(os.getenv("MAX_NUM_PREDICT", "512"))

    # ==================== Component Control Flags (deduplicated) ====================
    DISABLE_CONTINUOUS_LEARNING: bool = os.getenv("DISABLE_CONTINUOUS_LEARNING", "false").lower() == "true"
    DISABLE_PROACTIVE_HEALING: bool = os.getenv("DISABLE_PROACTIVE_HEALING", "false").lower() == "true"
    DISABLE_SPINDLE_DAEMON: bool = os.getenv("DISABLE_SPINDLE_DAEMON", "false").lower() == "true"

    # ==================== Error Handling (deduplicated) ====================
    SUPPRESS_GENESIS_ERRORS: bool = os.getenv("SUPPRESS_GENESIS_ERRORS", "false").lower() == "true"
    SUPPRESS_QDRANT_ERRORS: bool = os.getenv("SUPPRESS_QDRANT_ERRORS", "false").lower() == "true"
    SUPPRESS_EMBEDDING_ERRORS: bool = os.getenv("SUPPRESS_EMBEDDING_ERRORS", "false").lower() == "true"

    # ==================== Ingestion Configuration ====================
    EXCLUDE_GENESIS_FROM_INGESTION: bool = os.getenv("EXCLUDE_GENESIS_FROM_INGESTION", "true").lower() == "true"

    # ==================== Consensus Engine ====================
    CONSENSUS_BATCH_SCHEDULE: str = os.getenv("CONSENSUS_BATCH_SCHEDULE", "daily")
    CONSENSUS_MAX_BATCH_SIZE: int = int(os.getenv("CONSENSUS_MAX_BATCH_SIZE", "5"))

    # ==================== SerpAPI Configuration ====================
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    SERPAPI_ENABLED: bool = os.getenv("SERPAPI_ENABLED", "true").lower() == "true"
    SERPAPI_MAX_RESULTS: int = int(os.getenv("SERPAPI_MAX_RESULTS", "5"))
    SERPAPI_AUTO_SCRAPE: bool = os.getenv("SERPAPI_AUTO_SCRAPE", "true").lower() == "true"

    # ==================== Knowledge gap external sources (software engineering) ====================
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")  # Optional; higher rate limit when set
    GAP_FILL_GITHUB: bool = os.getenv("GAP_FILL_GITHUB", "true").lower() == "true"
    GAP_FILL_STACKOVERFLOW: bool = os.getenv("GAP_FILL_STACKOVERFLOW", "true").lower() == "true"
    GAP_FILL_ARXIV: bool = os.getenv("GAP_FILL_ARXIV", "true").lower() == "true"
    GAP_FILL_WIKIPEDIA: bool = os.getenv("GAP_FILL_WIKIPEDIA", "true").lower() == "true"
    GAP_FILL_HACKERNEWS: bool = os.getenv("GAP_FILL_HACKERNEWS", "true").lower() == "true"
    GAP_FILL_DEVTO: bool = os.getenv("GAP_FILL_DEVTO", "true").lower() == "true"
    GAP_FILL_PYPI: bool = os.getenv("GAP_FILL_PYPI", "true").lower() == "true"
    GAP_FILL_MDN: bool = os.getenv("GAP_FILL_MDN", "true").lower() == "true"
    GAP_FILL_SEMANTIC_SCHOLAR: bool = os.getenv("GAP_FILL_SEMANTIC_SCHOLAR", "true").lower() == "true"
    GAP_FILL_NPM: bool = os.getenv("GAP_FILL_NPM", "true").lower() == "true"
    GAP_FILL_IETF_RFC: bool = os.getenv("GAP_FILL_IETF_RFC", "true").lower() == "true"
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")  # Optional; higher rate limit

    # ==================== LLM Provider Configuration ====================
    # LLM_PROVIDER: 'ollama', 'openai', or 'kimi'
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").lower()
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")

    # ==================== Kimi 2.5 (Moonshot AI) Configuration ====================
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
    KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
    KIMI_MODEL: str = os.getenv("KIMI_MODEL", "kimi-k2.5")

    # ==================== Opus (Anthropic Claude) Configuration ====================
    OPUS_API_KEY: str = os.getenv("OPUS_API_KEY", "")
    OPUS_BASE_URL: str = os.getenv("OPUS_BASE_URL", "https://api.anthropic.com/v1")
    OPUS_MODEL: str = os.getenv("OPUS_MODEL", "claude-sonnet-4-20250514")

    # ==================== Local Model Configuration (per-task) ====================
    # Code: Qwen3.5 (35B MoE, 3B active, 256K ctx) or Qwen3-Coder (30B MoE, agentic).
    # Reason: Qwen3.5 (unified vision-language, thinking mode).
    # Fast: Qwen3.5:9b (small MoE for low-latency).
    # Document: Qwen3.5 (multimodal, vision+text).
    OLLAMA_MODEL_CODE: str = os.getenv("OLLAMA_MODEL_CODE", "qwen3.5:35b")
    OLLAMA_MODEL_REASON: str = os.getenv("OLLAMA_MODEL_REASON", "qwen3.5:35b")
    OLLAMA_MODEL_FAST: str = os.getenv("OLLAMA_MODEL_FAST", "qwen3.5:9b")
    OLLAMA_MODEL_DOCUMENT: str = os.getenv("OLLAMA_MODEL_DOCUMENT", "qwen3.5:35b")

    # ==================== Knowledge Base Configuration ====================
    KNOWLEDGE_BASE_PATH: str = str(BACKEND_DIR / "knowledge_base")
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required settings are properly configured.
        
        Returns:
            bool: True if all settings are valid
            
        Raises:
            ValueError: If required settings are missing or invalid
        """
        errors = []
        
        # Validate LLM Provider settings
        if cls.LLM_PROVIDER == "openai":
            if not cls.LLM_API_KEY:
                errors.append("LLM_API_KEY is required when LLM_PROVIDER is 'openai'")
            if not cls.LLM_MODEL:
                # Default to gpt-4o if not specified
                cls.LLM_MODEL = "gpt-4o"
        elif cls.LLM_PROVIDER == "ollama":
            if not cls.OLLAMA_URL:
                errors.append("OLLAMA_URL is not set")
            # If LLM_MODEL is not set, use OLLAMA_LLM_DEFAULT
            if not cls.LLM_MODEL:
                cls.LLM_MODEL = cls.OLLAMA_LLM_DEFAULT
        elif cls.LLM_PROVIDER == "runpod":
            if not os.getenv("RUNPOD_API_KEY") or not os.getenv("RUNPOD_ENDPOINT_ID"):
                errors.append("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID are required when LLM_PROVIDER is 'runpod'")
            if not cls.LLM_MODEL:
                cls.LLM_MODEL = os.getenv("RUNPOD_MODEL", "Mistral-7B-Instruct-v0.3")
        else:
            errors.append(f"Unsupported LLM_PROVIDER: '{cls.LLM_PROVIDER}'. Must be 'ollama', 'openai', or 'runpod'")

        # Validate Ollama settings (only if using ollama)
        if cls.LLM_PROVIDER == "ollama":
            if not cls.OLLAMA_URL:
                errors.append("OLLAMA_URL is not set")
            if not cls.OLLAMA_LLM_DEFAULT:
                errors.append("OLLAMA_LLM_DEFAULT is not set")
        
        # Validate Embedding settings
        if not cls.EMBEDDING_DEFAULT:
            errors.append("EMBEDDING_DEFAULT is not set")
        # Note: Don't validate EMBEDDING_MODEL_PATH existence - SentenceTransformer
        # will fall back to HuggingFace cache (~/.cache/torch/sentence_transformers/)
        # if local path doesn't exist
        if cls.EMBEDDING_DEVICE not in ["cuda", "cpu"]:
            errors.append(f"EMBEDDING_DEVICE must be 'cuda' or 'cpu', got '{cls.EMBEDDING_DEVICE}'")
        
        if errors:
            raise ValueError("Settings validation failed:\n  - " + "\n  - ".join(errors))
        
        return True
    
    @classmethod
    def to_dict(cls) -> dict:
        """Get all settings as a dictionary."""
        return {
            "OLLAMA_URL": cls.OLLAMA_URL,
            "OLLAMA_LLM_DEFAULT": cls.OLLAMA_LLM_DEFAULT,
            "EMBEDDING_DEFAULT": cls.EMBEDDING_DEFAULT,
            "EMBEDDING_MODEL_PATH": cls.EMBEDDING_MODEL_PATH,
            "EMBEDDING_DEVICE": cls.EMBEDDING_DEVICE,
            "EMBEDDING_NORMALIZE": cls.EMBEDDING_NORMALIZE,
            "DATABASE_TYPE": cls.DATABASE_TYPE,
            "DATABASE_HOST": cls.DATABASE_HOST,
            "DATABASE_PORT": cls.DATABASE_PORT,
            "DATABASE_USER": cls.DATABASE_USER,
            "DATABASE_NAME": cls.DATABASE_NAME,
            "DATABASE_PATH": cls.DATABASE_PATH,
            "DATABASE_ECHO": cls.DATABASE_ECHO,
            "QDRANT_HOST": cls.QDRANT_HOST,
            "QDRANT_PORT": cls.QDRANT_PORT,
            "QDRANT_COLLECTION_NAME": cls.QDRANT_COLLECTION_NAME,
            "QDRANT_TIMEOUT": cls.QDRANT_TIMEOUT,
            "INGESTION_CHUNK_SIZE": cls.INGESTION_CHUNK_SIZE,
            "INGESTION_CHUNK_OVERLAP": cls.INGESTION_CHUNK_OVERLAP,
            "LIBRARIAN_AUTO_PROCESS": cls.LIBRARIAN_AUTO_PROCESS,
            "LIBRARIAN_USE_AI": cls.LIBRARIAN_USE_AI,
            "LIBRARIAN_DETECT_RELATIONSHIPS": cls.LIBRARIAN_DETECT_RELATIONSHIPS,
            "LIBRARIAN_AI_CONFIDENCE_THRESHOLD": cls.LIBRARIAN_AI_CONFIDENCE_THRESHOLD,
            "LIBRARIAN_SIMILARITY_THRESHOLD": cls.LIBRARIAN_SIMILARITY_THRESHOLD,
            "LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES": cls.LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES,
            "LIBRARIAN_AI_MODEL": cls.LIBRARIAN_AI_MODEL,
            "DEBUG": cls.DEBUG,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "MAX_NUM_PREDICT": cls.MAX_NUM_PREDICT,
            "SKIP_QDRANT_CHECK": cls.SKIP_QDRANT_CHECK,
            "SKIP_OLLAMA_CHECK": cls.SKIP_OLLAMA_CHECK,
            "SKIP_AUTO_INGESTION": cls.SKIP_AUTO_INGESTION,
            "SKIP_EMBEDDING_LOAD": cls.SKIP_EMBEDDING_LOAD,
            "LIGHTWEIGHT_MODE": cls.LIGHTWEIGHT_MODE,
            "HEALING_SIMULATION_MODE": cls.HEALING_SIMULATION_MODE,
            "DISABLE_GENESIS_TRACKING": cls.DISABLE_GENESIS_TRACKING,
            "SUPPRESS_INGESTION_ERRORS": cls.SUPPRESS_INGESTION_ERRORS,
        }
    
    @classmethod
    def __repr__(cls) -> str:
        """String representation of settings."""
        settings = cls.to_dict()
        lines = ["Settings Configuration:"]
        for key, value in settings.items():
            # Mask sensitive values
            if "URL" in key or "PATH" in key:
                lines.append(f"  {key}: {value}")
            else:
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)


# Create a singleton instance
settings = Settings()

# Validate settings on module load
try:
    Settings.validate()
except ValueError as e:
    print(f"[WARN] Warning: {e}")
    print("Using default values for missing settings")


if __name__ == "__main__":
    # Display settings when run directly
    print(Settings)
    print("\nDetailed Settings:")
    for key, value in Settings.to_dict().items():
        print(f"  {key}: {value}")
