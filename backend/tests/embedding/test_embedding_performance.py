"""
Tests for embedding model performance and similarity calculations.
"""

import unittest
import numpy as np
import torch
import time
from pathlib import Path
from embedding import EmbeddingModel


class TestEmbeddingModel(unittest.TestCase):
    """Test cases for embedding model performance, similarity, and advanced features."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class fixtures - load model once for all tests."""
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA not available - GPU required for tests")
        
        backend_dir = Path(__file__).parent.parent.parent
        cls.model_path = str(backend_dir / "models" / "embedding" / "qwen_4b")
        
        print("\n" + "=" * 80)
        print("LOADING EMBEDDING MODEL")
        print("=" * 80)
        start_time = time.time()
        cls.model = EmbeddingModel(model_path=cls.model_path, device="cuda")
        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f} seconds")
        print("=" * 80 + "\n")
        
        cls.test_times = {}
    
    @classmethod
    def tearDownClass(cls):
        """Tear down class fixtures - unload model."""
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        
        if cls.test_times:
            total_time = sum(cls.test_times.values())
            print(f"\n{'Test Name':<50} {'Time (ms)':<15}")
            print("-" * 65)
            for test_name, elapsed in sorted(cls.test_times.items(), key=lambda x: x[1], reverse=True):
                print(f"{test_name:<50} {elapsed*1000:>10.2f} ms")
            print("-" * 65)
            print(f"{'TOTAL':<50} {total_time*1000:>10.2f} ms")
        
        print("\nUnloading model...")
        start_time = time.time()
        cls.model.unload_model()
        unload_time = time.time() - start_time
        print(f"Model unloaded in {unload_time:.2f} seconds")
        print("=" * 80 + "\n")
    
    def setUp(self):
        """Set up for each test."""
        self.test_start_time = time.time()
    
    def tearDown(self):
        """Tear down for each test - log timing."""
        elapsed = time.time() - self.test_start_time
        test_name = self._testMethodName
        self.__class__.test_times[test_name] = elapsed
        print(f"  {test_name}: {elapsed*1000:.2f} ms")
    
    def test_single_text_embedding_shape(self):
        """Test that single text embedding has correct shape."""
        embedding = self.model.embed_text("Hello world")
        
        self.assertEqual(len(embedding.shape), 1)
        self.assertEqual(embedding.shape[0], 2560)  # Qwen 4B embedding dimension
    
    def test_multiple_texts_embedding_shape(self):
        """Test that multiple texts embedding has correct shape."""
        texts = ["Hello", "World", "Testing"]
        embeddings = self.model.embed_text(texts)
        
        self.assertEqual(len(embeddings.shape), 2)
        self.assertEqual(embeddings.shape[0], 3)  # Number of texts
        self.assertEqual(embeddings.shape[1], 2560)  # Embedding dimension
    
    def test_embedding_dimension_consistency(self):
        """Test that embedding dimension is consistent across calls."""
        dim1 = self.model.embed_text("test1").shape[0]
        dim2 = self.model.embed_text("test2").shape[0]
        
        self.assertEqual(dim1, dim2)
        self.assertEqual(dim1, 2560)
    
    # ==================== Normalization Tests ====================
    
    def test_embeddings_are_normalized(self):
        """Test that embeddings are normalized when normalize_embeddings=True."""
        embedding = self.model.embed_text("test text", normalize=True)
        
        # L2 norm should be close to 1
        norm = np.linalg.norm(embedding)
        print(f"\n    Normalization Test:")
        print(f"      L2 norm of embedding: {norm:.6f}")
        print(f"      Expected: 1.0")
        print(f"      Difference: {abs(norm - 1.0):.6f}")
        
        self.assertAlmostEqual(norm, 1.0, places=5) 
    
    def test_embedding_numpy_output(self):
        """Test that numpy output format is correct."""
        embedding = self.model.embed_text("test", convert_to_numpy=True)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.dtype, np.float32)
    
    # ==================== Consistency Tests ====================
    
    def test_identical_texts_produce_identical_embeddings(self):
        """Test that identical texts produce identical embeddings."""
        text = "The same text repeated"
        embedding1 = self.model.embed_text(text)
        embedding2 = self.model.embed_text(text)
        
        # Should be identical
        np.testing.assert_array_almost_equal(embedding1, embedding2)
    
    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        embedding1 = self.model.embed_text("Python programming")
        embedding2 = self.model.embed_text("Java programming")
        
        # Should be different but related (both about programming)
        self.assertFalse(np.allclose(embedding1, embedding2))
    
    # ==================== Batch Processing Tests ====================
    
    def test_batch_processing_consistency(self):
        """Test that batch processing gives same results as individual processing."""
        texts = ["Hello", "World", "Test"]
        
        # Batch embedding
        batch_embeddings = self.model.embed_text(texts, batch_size=32)
        
        # Individual embeddings
        individual_embeddings = np.array([
            self.model.embed_text(text) for text in texts
        ])
        
        # Should be very close
        np.testing.assert_array_almost_equal(batch_embeddings, individual_embeddings, decimal=5)
    
    def test_batch_size_parameter(self):
        """Test that different batch sizes work correctly."""
        texts = ["Hello", "World", "Test", "Batch", "Size"]
        
        embeddings_bs1 = self.model.embed_text(texts, batch_size=1)
        embeddings_bs2 = self.model.embed_text(texts, batch_size=2)
        embeddings_bs5 = self.model.embed_text(texts, batch_size=5)
        
        # All should produce same results
        np.testing.assert_array_almost_equal(embeddings_bs1, embeddings_bs2, decimal=5)
        np.testing.assert_array_almost_equal(embeddings_bs2, embeddings_bs5, decimal=5)
    
    # ==================== Similarity Tests ====================
    
    def test_similarity_identical_texts(self):
        """Test that identical texts have similarity close to 1.0."""
        text = "The quick brown fox"
        similarity = self.model.similarity(text, text)
        
        self.assertAlmostEqual(similarity, 1.0, places=5)
    
    def test_similarity_very_different_texts(self):
        """Test that very different texts have lower similarity."""
        similarity_diff = self.model.similarity(
            "Python is a programming language",
            "The cat sat on the mat"
        )
        
        # Similar semantic texts
        similarity_same = self.model.similarity(
            "Python is a programming language",
            "Java is a programming language"
        )
        
        # Similar semantic texts should have higher similarity
        print(f"\n    Semantic Understanding Test:")
        print(f"      Programming vs Programming: {similarity_same:.4f}")
        print(f"      Programming vs Animal:     {similarity_diff:.4f}")
        print(f"      Difference:                {similarity_same - similarity_diff:.4f}")
        print(f"      ✓ Model correctly distinguished related documents" if similarity_same > similarity_diff else "      ✗ Failed to distinguish")
        
        self.assertGreater(similarity_same, similarity_diff)
    
    def test_similarity_semantically_related(self):
        """Test that semantically related texts have higher similarity."""
        similarity_related = self.model.similarity(
            "machine learning models",
            "artificial intelligence algorithms"
        )
        
        similarity_unrelated = self.model.similarity(
            "machine learning models",
            "The weather is sunny today"
        )
        
        print(f"\n    Semantic Relatedness Test:")
        print(f"      ML vs AI:           {similarity_related:.4f}")
        print(f"      ML vs Weather:      {similarity_unrelated:.4f}")
        print(f"      Difference:         {similarity_related - similarity_unrelated:.4f}")
        print(f"      ✓ Model correctly identified semantic similarity" if similarity_related > similarity_unrelated else "      ✗ Failed to identify similarity")
        
        self.assertGreater(similarity_related, similarity_unrelated)
    
    def test_similarity_cosine_metric(self):
        """Test cosine similarity metric."""
        similarity = self.model.similarity(
            "Hello world",
            "Hello there",
            metric="cosine"
        )
        
        # Should return a float between -1 and 1
        self.assertIsInstance(similarity, (float, np.floating))
        self.assertGreaterEqual(similarity, -1.0)
        self.assertLessEqual(similarity, 1.0)
    
    def test_similarity_euclidean_metric(self):
        """Test euclidean similarity metric."""
        similarity = self.model.similarity(
            "Hello world",
            "Hello there",
            metric="euclidean"
        )
        
        # Should return a number
        self.assertIsInstance(similarity, (float, np.floating))
    
    def test_similarity_symmetry(self):
        """Test that similarity is symmetric."""
        text1 = "The quick brown fox"
        text2 = "A fast brown fox"
        
        sim_12 = self.model.similarity(text1, text2)
        sim_21 = self.model.similarity(text2, text1)
        
        self.assertAlmostEqual(sim_12, sim_21, places=5)
    
    def test_similarity_list_inputs(self):
        """Test similarity calculation with list inputs."""
        texts1 = ["Hello", "Good morning", "Hi"]
        texts2 = ["Hi there", "Morning", "Greetings"]
        
        similarities = self.model.similarity(texts1, texts2)
        
        # Should return a 2D array
        self.assertEqual(len(similarities.shape), 2)
        self.assertEqual(similarities.shape[0], len(texts1))
        self.assertEqual(similarities.shape[1], len(texts2))
    
    # ==================== Most Similar Tests ====================
    
    def test_most_similar_ranking(self):
        """Test that most_similar returns results ranked by similarity."""
        query = "machine learning"
        candidates = [
            "deep neural networks",
            "the weather today",
            "artificial intelligence",
            "a cat sleeping",
            "supervised learning algorithms"
        ]
        
        results = self.model.most_similar(query, candidates, top_k=3)
        
        # Should return 3 results
        self.assertEqual(len(results), 3)
        
        # Results should be sorted by similarity (descending)
        similarities = [score for _, score in results]
        self.assertEqual(similarities, sorted(similarities, reverse=True))
        
        # Top results should be semantically related to query
        for candidate, score in results:
            self.assertIn(candidate, candidates)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
        
        print(f"\n    Most Similar Ranking Test:")
        print(f"      Query: '{query}'")
        print(f"      All candidates: {candidates}")
        print(f"      Top 3 results:")
        for i, (candidate, score) in enumerate(results, 1):
            print(f"        {i}. '{candidate}': {score:.4f}")
        
        # Verify semantic correctness
        top_candidate = results[0][0].lower()
        if any(word in top_candidate for word in ["learning", "algorithm", "intelligence", "neural"]):
            print(f"      ✓ Model correctly ranked semantically related documents")
        else:
            print(f"      ✗ Model failed to rank related documents correctly")
    
    def test_most_similar_top_k(self):
        """Test that top_k parameter works correctly."""
        query = "test"
        candidates = ["a", "b", "c", "d", "e"]
        
        results_k1 = self.model.most_similar(query, candidates, top_k=1)
        results_k3 = self.model.most_similar(query, candidates, top_k=3)
        results_k5 = self.model.most_similar(query, candidates, top_k=5)
        
        self.assertEqual(len(results_k1), 1)
        self.assertEqual(len(results_k3), 3)
        self.assertEqual(len(results_k5), 5)
    
    def test_most_similar_with_instruction(self):
        """Test most_similar with instruction parameter."""
        query = "python"
        candidates = ["java programming", "python code", "ruby script"]
        
        results = self.model.most_similar(
            query,
            candidates,
            top_k=2,
            instruction="Represent this programming text"
        )
        
        self.assertEqual(len(results), 2)
        # Results should contain candidates
        for candidate, _ in results:
            self.assertIn(candidate, candidates)
    
    # ==================== Advanced Features Tests ====================
    
    def test_embed_with_scores(self):
        """Test embed_with_scores returns embeddings and norms."""
        texts = ["Hello", "World", "Test"]
        embeddings, norms = self.model.embed_with_scores(texts)
        
        # Check embeddings shape
        self.assertEqual(embeddings.shape[0], 3)
        self.assertEqual(embeddings.shape[1], 2560)
        
        # Check norms
        self.assertEqual(len(norms), 3)
        for norm in norms:
            self.assertIsInstance(norm, (float, np.floating))
            self.assertGreater(norm, 0)
    
    def test_cluster_texts(self):
        """Test text clustering functionality."""
        texts = [
            "Python programming",
            "Java code",
            "The cat sat on mat",
            "A dog in the house",
            "Machine learning models",
            "Deep neural networks"
        ]
        
        clusters = self.model.cluster_texts(texts, num_clusters=3)
        
        # Should return a list of clusters
        self.assertIsInstance(clusters, list)
        
        # Each cluster should be a list of indices
        for cluster in clusters:
            self.assertIsInstance(cluster, list)
            for idx in cluster:
                self.assertGreaterEqual(idx, 0)
                self.assertLess(idx, len(texts))
        
        # All indices should be covered
        all_indices = set()
        for cluster in clusters:
            all_indices.update(cluster)
        self.assertEqual(len(all_indices), len(texts))
        
        print(f"\n    Clustering Quality Test:")
        print(f"      Input texts: {texts}")
        print(f"      Number of clusters: {len(clusters)}")
        for i, cluster in enumerate(clusters):
            cluster_texts = [texts[idx] for idx in cluster]
            print(f"\n      Cluster {i+1}: {cluster_texts}")
        
        # Verify semantic clustering
        programming_cluster_found = False
        animal_cluster_found = False
        ml_cluster_found = False
        
        for cluster in clusters:
            cluster_texts = [texts[idx].lower() for idx in cluster]
            cluster_str = " ".join(cluster_texts)
            
            if "python" in cluster_str and "java" in cluster_str and "code" in cluster_str:
                programming_cluster_found = True
            if "cat" in cluster_str and "dog" in cluster_str:
                animal_cluster_found = True
            if "learning" in cluster_str and "neural" in cluster_str:
                ml_cluster_found = True
        
        print(f"\n      Semantic Quality Metrics:")
        print(f"        Programming cluster found: {'✓' if programming_cluster_found else '✗'}")
        print(f"        Animal cluster found: {'✓' if animal_cluster_found else '✗'}")
        print(f"        ML cluster found: {'✓' if ml_cluster_found else '✗'}")


if __name__ == "__main__":
    unittest.main()
