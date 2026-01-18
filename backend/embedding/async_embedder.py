import asyncio
import logging
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
logger = logging.getLogger(__name__)

class AsyncBatchEmbedder:
    """
    Asynchronous wrapper for batch embedding generation.

    Features:
    - Thread pool for parallel processing
    - Batch optimization
    - Automatic retry logic
    - Non-blocking async interface
    """

    def __init__(
        self,
        embedder,
        max_workers: int = 4,
        batch_size: int = 32
    ):
        """
        Initialize async embedder.

        Args:
            embedder: Base EmbeddingModel instance
            max_workers: Number of worker threads
            batch_size: Batch size for embedding generation
        """
        self.embedder = embedder
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        logger.info(
            f"[ASYNC-EMBEDDER] Initialized with {max_workers} workers, "
            f"batch_size={batch_size}"
        )

    async def embed_single_async(self, text: str) -> List[float]:
        """
        Asynchronously embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embeddings = await self.embed_batch_async([text])
        return embeddings[0]

    async def embed_batch_async(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Asynchronously embed a batch of texts.

        Args:
            texts: List of texts to embed
            batch_size: Override default batch size

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        batch_size = batch_size or self.batch_size

        # Get event loop
        loop = asyncio.get_event_loop()

        # Run embedding in thread pool to avoid blocking
        embeddings = await loop.run_in_executor(
            self.executor,
            self._embed_batch_sync,
            texts,
            batch_size
        )

        return embeddings

    def _embed_batch_sync(
        self,
        texts: List[str],
        batch_size: int
    ) -> List[List[float]]:
        """
        Synchronous batch embedding (runs in thread pool).

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        try:
            # Use embedder's native batch processing
            embeddings = self.embedder.embed_text(
                texts,
                batch_size=batch_size
            )

            logger.debug(
                f"[ASYNC-EMBEDDER] Embedded {len(texts)} texts "
                f"in batches of {batch_size}"
            )

            return embeddings

        except Exception as e:
            logger.error(f"[ASYNC-EMBEDDER] Error embedding batch: {e}")
            raise

    async def embed_parallel_batches(
        self,
        text_groups: List[List[str]],
        batch_size: Optional[int] = None
    ) -> List[List[List[float]]]:
        """
        Embed multiple batches in parallel.

        Args:
            text_groups: List of text batches to embed
            batch_size: Batch size for each group

        Returns:
            List of embedding batches (one per group)
        """
        tasks = [
            self.embed_batch_async(group, batch_size)
            for group in text_groups
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        embeddings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"[ASYNC-EMBEDDER] Error in batch {i}: {result}"
                )
                # Return empty embeddings for failed batch
                embeddings.append([])
            else:
                embeddings.append(result)

        return embeddings

    async def embed_with_retry(
        self,
        texts: List[str],
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> List[List[float]]:
        """
        Embed texts with automatic retry on failure.

        Args:
            texts: List of texts to embed
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)

        Returns:
            List of embedding vectors
        """
        for attempt in range(max_retries):
            try:
                embeddings = await self.embed_batch_async(texts)
                return embeddings

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[ASYNC-EMBEDDER] Retry {attempt + 1}/{max_retries} "
                        f"after error: {e}"
                    )
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(
                        f"[ASYNC-EMBEDDER] Failed after {max_retries} retries"
                    )
                    raise

    def shutdown(self):
        """Shutdown the thread pool executor"""
        self.executor.shutdown(wait=True)
        logger.info("[ASYNC-EMBEDDER] Executor shutdown complete")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.shutdown()


# ================================================================
# ASYNC RETRIEVAL HELPER
# ================================================================

class AsyncSemanticSearch:
    """
    Async wrapper for semantic search operations.

    Combines async embedding with vector DB search.
    """

    def __init__(
        self,
        embedder: AsyncBatchEmbedder,
        vector_db_client
    ):
        """
        Initialize async semantic search.

        Args:
            embedder: AsyncBatchEmbedder instance
            vector_db_client: Qdrant client
        """
        self.embedder = embedder
        self.vector_db = vector_db_client

    async def search_single(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Asynchronously search for similar vectors.

        Args:
            query: Query text
            collection_name: Vector DB collection
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        # Generate embedding async
        query_embedding = await self.embedder.embed_single_async(query)

        # Search vector DB (could be made async if client supports it)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self.vector_db.search_vectors,
            collection_name,
            query_embedding,
            limit,
            score_threshold
        )

        return results

    async def search_batch(
        self,
        queries: List[str],
        collection_name: str = "documents",
        limit: int = 5
    ) -> List[List[Dict]]:
        """
        Search for multiple queries in parallel.

        Args:
            queries: List of query texts
            collection_name: Vector DB collection
            limit: Maximum results per query

        Returns:
            List of result lists (one per query)
        """
        # Generate all embeddings in batch
        embeddings = await self.embedder.embed_batch_async(queries)

        # Search in parallel
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None,
                self.vector_db.search_vectors,
                collection_name,
                emb,
                limit,
                0.3
            )
            for emb in embeddings
        ]

        results = await asyncio.gather(*tasks)
        return results


# ================================================================
# FACTORY FUNCTIONS
# ================================================================

def create_async_embedder(
    base_embedder,
    max_workers: int = 4,
    batch_size: int = 32
) -> AsyncBatchEmbedder:
    """
    Create async embedder from base embedder.

    Args:
        base_embedder: Base EmbeddingModel instance
        max_workers: Number of worker threads
        batch_size: Batch size for processing

    Returns:
        AsyncBatchEmbedder instance
    """
    return AsyncBatchEmbedder(
        embedder=base_embedder,
        max_workers=max_workers,
        batch_size=batch_size
    )


def create_async_semantic_search(
    embedder: AsyncBatchEmbedder,
    vector_db_client
) -> AsyncSemanticSearch:
    """
    Create async semantic search helper.

    Args:
        embedder: AsyncBatchEmbedder instance
        vector_db_client: Qdrant client

    Returns:
        AsyncSemanticSearch instance
    """
    return AsyncSemanticSearch(
        embedder=embedder,
        vector_db_client=vector_db_client
    )
