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


class Settings:
    """Application settings loaded from environment variables."""
    
    # ==================== Ollama Configuration ====================
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_LLM_DEFAULT: str = os.getenv("OLLAMA_LLM_DEFAULT", "mistral:7b")
    
    # ==================== Embedding Configuration ====================
    EMBEDDING_DEFAULT: str = os.getenv("EMBEDDING_DEFAULT", "qwen_4b")
    EMBEDDING_MODEL_PATH: str = str(BACKEND_DIR / "models" / "embedding" / EMBEDDING_DEFAULT)
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cuda")  # cuda or cpu
    EMBEDDING_NORMALIZE: bool = os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
    
    # ==================== Database Configuration ====================
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "0")) or None
    DATABASE_USER: str = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "grace")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "grace.db"))
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # ==================== Qdrant Configuration ====================
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")
    QDRANT_TIMEOUT: int = int(os.getenv("QDRANT_TIMEOUT", "30"))
    
    # ==================== Ingestion Configuration ====================
    INGESTION_CHUNK_SIZE: int = int(os.getenv("INGESTION_CHUNK_SIZE", "1024"))
    INGESTION_CHUNK_OVERLAP: int = int(os.getenv("INGESTION_CHUNK_OVERLAP", "50"))
    
    # ==================== Application Configuration ====================
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_NUM_PREDICT: int = int(os.getenv("MAX_NUM_PREDICT", "2048"))
    
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
        
        # Validate Ollama settings
        if not cls.OLLAMA_URL:
            errors.append("OLLAMA_URL is not set")
        if not cls.OLLAMA_LLM_DEFAULT:
            errors.append("OLLAMA_LLM_DEFAULT is not set")
        
        # Validate Embedding settings
        if not cls.EMBEDDING_DEFAULT:
            errors.append("EMBEDDING_DEFAULT is not set")
        if not Path(cls.EMBEDDING_MODEL_PATH).exists():
            errors.append(f"Embedding model path does not exist: {cls.EMBEDDING_MODEL_PATH}")
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
            "DEBUG": cls.DEBUG,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "MAX_NUM_PREDICT": cls.MAX_NUM_PREDICT,
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
    print(f"⚠ Warning: {e}")
    print("Using default values for missing settings")


if __name__ == "__main__":
    # Display settings when run directly
    print(Settings)
    print("\nDetailed Settings:")
    for key, value in Settings.to_dict().items():
        print(f"  {key}: {value}")
