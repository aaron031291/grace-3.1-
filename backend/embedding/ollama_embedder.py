"""
Ollama Embeddings - Fast embedding generation using local Ollama.

Uses the already-running Ollama instance for embeddings.
3 seconds per text vs loading a separate embedding model.

Drop-in replacement for EmbeddingModel when the full model isn't available.
"""

import logging
import requests
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"


class OllamaEmbedder:
    """
    Generate embeddings using Ollama's built-in embedding endpoint.

    Works with any model Ollama has loaded (llama3.2:1b gives 2048 dim).
    """

    def __init__(self, model: str = "llama3.2:1b", base_url: str = OLLAMA_URL):
        self.model = model
        self.base_url = base_url
        self._dimension = None

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = []
        for text in texts:
            try:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text[:8000]},
                    timeout=30,
                )
                if resp.status_code == 200:
                    emb = resp.json().get("embedding", [])
                    embeddings.append(emb)
                    if not self._dimension:
                        self._dimension = len(emb)
                else:
                    embeddings.append([0.0] * (self._dimension or 2048))
            except Exception as e:
                logger.warning(f"Ollama embedding failed: {e}")
                embeddings.append([0.0] * (self._dimension or 2048))
        return embeddings

    @property
    def dimension(self) -> int:
        if not self._dimension:
            try:
                test = self.embed_text(["test"])
                self._dimension = len(test[0])
            except Exception:
                self._dimension = 2048
        return self._dimension

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


_ollama_embedder: Optional[OllamaEmbedder] = None


def get_ollama_embedder(model: str = "llama3.2:1b") -> OllamaEmbedder:
    global _ollama_embedder
    if _ollama_embedder is None:
        _ollama_embedder = OllamaEmbedder(model=model)
    return _ollama_embedder
