"""
Settings Configuration Guide

This module provides centralized configuration management for the Grace application.
All settings are loaded from the .env file at backend/.env
"""

# ============================================================================

# USAGE EXAMPLES

# ============================================================================

# 1. Import and use settings in any module:

# ============================================================================

from settings import settings

# Access individual settings

print(settings.OLLAMA_URL)
print(settings.EMBEDDING_DEFAULT)
print(settings.EMBEDDING_DEVICE)

# Print all settings

print(settings)

# Get settings as dictionary

config_dict = settings.to_dict()

# Validate settings

try:
settings.validate()
print("✓ All settings are valid")
except ValueError as e:
print(f"✗ Settings validation failed: {e}")

# 2. Use settings in Ollama module:

# ============================================================================

from ollama.client import get_ollama_client
from settings import settings

# Automatically uses OLLAMA_URL from settings

client = get_ollama_client()

# Or explicitly pass URL

client = get_ollama_client(base_url="http://custom:11434")

# 3. Use settings in Embedding module:

# ============================================================================

from embedding.embedder import EmbeddingModel
from settings import settings

# Automatically uses EMBEDDING_DEFAULT and EMBEDDING_DEVICE from settings

model = EmbeddingModel()

# Or explicitly override

model = EmbeddingModel(
device="cpu",
normalize_embeddings=False
)

# ============================================================================

# ENVIRONMENT VARIABLES (.env file)

# ============================================================================

"""
OLLAMA Configuration:
OLLAMA_URL - URL of Ollama service (default: http://localhost:11434)
OLLAMA_LLM_DEFAULT - Default LLM model (default: mistral:7b)

Embedding Configuration:
EMBEDDING_DEFAULT - Default embedding model name (default: qwen_4b)
EMBEDDING_DEVICE - Device to use: 'cuda' or 'cpu' (default: cuda)
EMBEDDING_NORMALIZE - Normalize embeddings: 'true' or 'false' (default: true)

Application Configuration:
DEBUG - Enable debug mode: 'true' or 'false' (default: false)
LOG_LEVEL - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

# ============================================================================

# SETTINGS CLASS ATTRIBUTES

# ============================================================================

"""
Settings.OLLAMA_URL - URL to connect to Ollama service
Settings.OLLAMA_LLM_DEFAULT - Default LLM model to use
Settings.EMBEDDING_DEFAULT - Default embedding model name
Settings.EMBEDDING_MODEL_PATH - Full path to embedding model directory
Settings.EMBEDDING_DEVICE - Device for embedding (cuda/cpu)
Settings.EMBEDDING_NORMALIZE - Whether to normalize embeddings
Settings.DEBUG - Debug mode flag
Settings.LOG_LEVEL - Application logging level

Class Methods:
Settings.validate() - Validates all settings
Settings.to_dict() - Returns settings as dictionary
Settings.**repr**() - String representation
"""

# ============================================================================

# VALIDATION

# ============================================================================

"""
Settings are automatically validated when the module is imported.

The following validations are performed:
✓ OLLAMA_URL is set
✓ OLLAMA_LLM_DEFAULT is set
✓ EMBEDDING_DEFAULT is set
✓ Embedding model path exists on disk
✓ EMBEDDING_DEVICE is either 'cuda' or 'cpu'

If any validation fails, a warning is printed but the application continues
with default values.
"""
