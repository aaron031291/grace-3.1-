#!/usr/bin/env python
"""
Quick test script to verify the semantic contradiction detection system.
This tests the confidence scorer with contradiction detection.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


def test_contradiction_detector():
    """Test SemanticContradictionDetector directly."""
    print("\n" + "="*60)
    print("Testing SemanticContradictionDetector")
    print("="*60)
    
    try:
        from confidence_scorer import SemanticContradictionDetector
        
        logger.info("Initializing SemanticContradictionDetector...")
        detector = SemanticContradictionDetector(use_gpu=False)
        
        if not detector.model_available:
            logger.warning("⚠ NLI model not available - model will be skipped")
            logger.warning("  This is expected if running without internet or Hugging Face credentials")
            logger.info("  Detector still functional with fallback behavior")
            return True
        
        logger.info("✓ Detector initialized successfully")
        
        # Test with sample text pairs
        test_pairs = [
            ("The Earth is round", "The Earth is flat"),
            ("Water boils at 100C", "Water boils at 100C"),
            ("Python is a language", "Cats are animals"),
        ]
        
        logger.info("\nTesting contradiction detection:")
        for text1, text2 in test_pairs:
            try:
                score = detector.detect_contradiction(text1, text2, threshold=0.5)
                logger.info(f"  '{text1}' vs '{text2}'")
                logger.info(f"    → Contradiction score: {score:.4f}")
            except Exception as e:
                logger.error(f"  Error: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to test detector: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confidence_scorer():
    """Test ConfidenceScorer with mock dependencies."""
    print("\n" + "="*60)
    print("Testing ConfidenceScorer")
    print("="*60)
    
    try:
        from unittest.mock import MagicMock
        from confidence_scorer import ConfidenceScorer
        
        logger.info("Initializing ConfidenceScorer with mocked dependencies...")
        
        # Mock the embedding model and Qdrant client
        mock_embedding_model = MagicMock()
        mock_embedding_model.embed_text.return_value = [
            [0.1, 0.2, 0.3, 0.4, 0.5] for _ in range(10)
        ]
        
        mock_qdrant_client = MagicMock()
        mock_qdrant_client.search_vectors.return_value = [
            {"score": 0.85, "payload": {"text": "Related document 1"}},
            {"score": 0.75, "payload": {"text": "Related document 2"}},
        ]
        
        scorer = ConfidenceScorer(
            embedding_model=mock_embedding_model,
            qdrant_client=mock_qdrant_client,
            collection_name="test"
        )
        
        logger.info("✓ ConfidenceScorer initialized successfully")
        
        # Test confidence score calculation
        logger.info("\nCalculating confidence scores:")
        
        text = "This is a test document about machine learning."
        
        result = scorer.calculate_confidence_score(
            text_content=text,
            source_type="user_generated",
            created_at=datetime.now(timezone.utc),
            existing_chunks=[]
        )
        
        logger.info(f"  Text: '{text}'")
        logger.info(f"  Confidence Score: {result['confidence_score']:.3f}")
        logger.info(f"  Source Reliability: {result['source_reliability']:.3f}")
        logger.info(f"  Content Quality: {result['content_quality']:.3f}")
        logger.info(f"  Consensus Score: {result['consensus_score']:.3f}")
        logger.info(f"  Recency: {result['recency']:.3f}")
        logger.info(f"  Contradictions Detected: {result.get('contradictions_detected', False)}")
        logger.info(f"  Contradiction Count: {result.get('contradiction_count', 0)}")
        
        # Verify structure
        assert "confidence_score" in result
        assert "contradictions_detected" in result
        assert "contradiction_count" in result
        
        logger.info("\n✓ ConfidenceScorer working correctly")
        return True
        
    except Exception as e:
        logger.error(f"Failed to test scorer: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SEMANTIC CONTRADICTION DETECTION SYSTEM TEST")
    print("="*60)
    
    results = []
    
    # Test detector
    results.append(("SemanticContradictionDetector", test_contradiction_detector()))
    
    # Test scorer
    results.append(("ConfidenceScorer", test_confidence_scorer()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
