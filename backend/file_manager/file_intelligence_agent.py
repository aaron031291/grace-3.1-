"""
Grace File Intelligence Agent

Understands file content deeply, not just formats.
Builds semantic understanding of knowledge base.

Classes:
- `FileIntelligence`
- `FileIntelligenceAgent`

Key Methods:
- `analyze_file_deeply()`
- `get_file_intelligence_agent()`
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from llm_orchestrator.factory import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class FileIntelligence:
    """Deep intelligence about a file's content."""

    content_summary: str
    extracted_entities: Dict[str, List[str]]  # {people: [], places: [], concepts: []}
    detected_topics: List[str]
    quality_score: float  # 0.0-1.0
    complexity_level: str  # beginner/intermediate/advanced
    recommended_chunk_strategy: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class FileIntelligenceAgent:
    """
    Understands file content, not just formats.
    Builds semantic understanding of knowledge base.

    Grace Principle: Self-Awareness
    - Knows what files contain, not just where they are
    - Understands meaning and context
    - Discovers relationships autonomously
    """

    def __init__(self, file_handler=None, llm_client=None):
        """
        Initialize intelligence agent.

        Args:
            file_handler: FileHandler for text extraction
            llm_client: LLM client for AI analysis (defaults to factory)
        """
        self.file_handler = file_handler
        self.llm_client = llm_client or get_llm_client()

        logger.info("[FILE-INTELLIGENCE] Agent initialized")

    def analyze_file_deeply(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> FileIntelligence:
        """
        Deep content analysis beyond format extraction.

        Args:
            file_path: Path to file
            content: Pre-extracted content (optional)

        Returns:
            FileIntelligence with complete understanding
        """
        try:
            # 1. Extract content if not provided
            if content is None:
                if self.file_handler:
                    content = self.file_handler.extract_text(file_path)
                else:
                    content = Path(file_path).read_text(encoding='utf-8', errors='ignore')

            # 2. AI-powered understanding
            summary = self._generate_summary(content)
            entities = self._extract_entities(content)
            topics = self._detect_topics(content)

            # 3. Quality assessment
            quality = self._assess_quality(content)
            complexity = self._assess_complexity(content)

            # 4. Optimal processing strategy
            chunk_strategy = self._recommend_chunking_strategy(
                file_path=file_path,
                content=content,
                complexity=complexity
            )

            # 5. Relationship hints (actual detection happens in RelationshipEngine)
            relationships = []  # Placeholder for now

            # 6. Additional metadata
            metadata = {
                'file_size': len(content),
                'line_count': content.count('\n') + 1,
                'word_count': len(content.split()),
                'analyzed_at': datetime.now().isoformat()
            }

            logger.info(
                f"[FILE-INTELLIGENCE] Analyzed {Path(file_path).name}: "
                f"quality={quality:.2f}, complexity={complexity}, "
                f"topics={len(topics)}, entities={sum(len(v) for v in entities.values())}"
            )

            return FileIntelligence(
                content_summary=summary,
                extracted_entities=entities,
                detected_topics=topics,
                quality_score=quality,
                complexity_level=complexity,
                recommended_chunk_strategy=chunk_strategy,
                relationships=relationships,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"[FILE-INTELLIGENCE] Analysis failed for {file_path}: {e}")

            # Return minimal intelligence on failure
            return FileIntelligence(
                content_summary="Analysis failed",
                extracted_entities={},
                detected_topics=[],
                quality_score=0.5,
                complexity_level="unknown",
                recommended_chunk_strategy=self._get_default_strategy(),
                relationships=[],
                metadata={'error': str(e)}
            )

    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate AI-powered content summary."""

        if not content or len(content) < 50:
            return "Content too short for summary"

        # Use LLM if available
        if self.llm_client:
            try:
                prompt = f"""Summarize the following text in 1-2 sentences (max {max_length} chars):

{content[:2000]}

Summary:"""

                response = self.llm_client.generate(
                    prompt=prompt,
                    max_tokens=100
                )

                summary = response.get('response', '').strip()
                if summary:
                    return summary[:max_length]

            except Exception as e:
                logger.debug(f"LLM summary failed, using fallback: {e}")

        # Fallback: First sentence or first N words
        sentences = content.split('.')
        if sentences and len(sentences[0]) < max_length:
            return sentences[0].strip() + '.'

        words = content.split()[:30]
        return ' '.join(words) + '...'

    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
        Extract named entities from content.

        Returns:
            Dict with entity types: {people: [], places: [], concepts: []}
        """
        entities = {
            'people': [],
            'places': [],
            'concepts': [],
            'organizations': []
        }

        # Simple rule-based extraction (can be enhanced with NER model)
        # Look for capitalized words as potential entities
        words = content.split()
        potential_entities = []

        for i, word in enumerate(words):
            # Skip first word of sentences
            if i > 0 and word[0].isupper() and len(word) > 3:
                # Clean punctuation
                clean_word = word.strip('.,!?;:')
                if clean_word and clean_word not in potential_entities:
                    potential_entities.append(clean_word)

        # Categorize (simplified - real NER would be better)
        # For now, just put in concepts
        entities['concepts'] = potential_entities[:20]  # Limit to top 20

        return entities

    def _detect_topics(self, content: str) -> List[str]:
        """
        Detect main topics in content.

        Returns:
            List of detected topics
        """
        # Simple keyword-based topic detection
        # Can be enhanced with topic modeling (LDA, etc.)

        topic_keywords = {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'react', 'node', 'typescript'],
            'data_science': ['data', 'analysis', 'machine learning', 'statistics', 'model'],
            'web_development': ['html', 'css', 'web', 'frontend', 'backend', 'api'],
            'database': ['sql', 'database', 'query', 'table', 'postgresql', 'mysql'],
            'devops': ['docker', 'kubernetes', 'ci/cd', 'deployment', 'aws'],
        }

        content_lower = content.lower()
        detected_topics = []

        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                detected_topics.append(topic)

        return detected_topics

    def _assess_quality(self, content: str) -> float:
        """
        Assess content quality.

        Returns:
            Quality score 0.0-1.0
        """
        score = 0.5  # Base score

        # Factor 1: Length (reasonable content)
        if 500 < len(content) < 50000:
            score += 0.1
        elif len(content) >= 50000:
            score += 0.05

        # Factor 2: Structure (has paragraphs)
        paragraph_count = content.count('\n\n')
        if paragraph_count > 2:
            score += 0.1

        # Factor 3: Readability (sentences)
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        if sentence_count > 5:
            score += 0.1

        # Factor 4: Vocabulary diversity
        words = content.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.3:
                score += 0.1

        # Factor 5: Not too much punctuation noise
        punct_ratio = sum(1 for c in content if c in '.,!?;:') / max(len(content), 1)
        if punct_ratio < 0.1:
            score += 0.1

        return min(score, 1.0)

    def _assess_complexity(self, content: str) -> str:
        """
        Assess content complexity level.

        Returns:
            'beginner', 'intermediate', or 'advanced'
        """
        # Simple heuristic based on vocabulary and structure
        words = content.split()

        if not words:
            return 'unknown'

        # Average word length
        avg_word_length = sum(len(w) for w in words) / len(words)

        # Sentence length
        sentences = content.split('.')
        avg_sentence_length = len(words) / max(len(sentences), 1)

        # Complexity indicators
        complex_words = sum(1 for w in words if len(w) > 10)
        complex_ratio = complex_words / len(words)

        # Determine level
        if avg_word_length < 5 and avg_sentence_length < 15:
            return 'beginner'
        elif complex_ratio > 0.15 or avg_sentence_length > 25:
            return 'advanced'
        else:
            return 'intermediate'

    def _recommend_chunking_strategy(
        self,
        file_path: str,
        content: str,
        complexity: str
    ) -> Dict[str, Any]:
        """
        Recommend optimal chunking strategy.

        Returns:
            Strategy dict with chunk_size, overlap, use_semantic, etc.
        """
        file_type = Path(file_path).suffix.lower()

        # Default strategy
        strategy = {
            'chunk_size': 512,
            'overlap': 50,
            'use_semantic': False,
            'embedding_batch_size': 32
        }

        # Adjust based on file type
        if file_type in ['.pdf', '.docx', '.txt']:
            # Documents: larger chunks for context
            strategy['chunk_size'] = 1024
            strategy['overlap'] = 100
            strategy['use_semantic'] = True  # Better for prose

        elif file_type in ['.py', '.js', '.java', '.cpp', '.c']:
            # Code: smaller chunks (function-level)
            strategy['chunk_size'] = 256
            strategy['overlap'] = 25
            strategy['use_semantic'] = False  # Structure matters more

        elif file_type in ['.md', '.rst']:
            # Markdown: section-aware
            strategy['chunk_size'] = 512
            strategy['overlap'] = 50
            strategy['use_semantic'] = True

        # Adjust based on complexity
        if complexity == 'advanced':
            # More context needed
            strategy['chunk_size'] = int(strategy['chunk_size'] * 1.5)
            strategy['overlap'] = int(strategy['overlap'] * 1.5)

        # Adjust based on content length
        if len(content) > 100000:
            # Large files: smaller batches to avoid memory issues
            strategy['embedding_batch_size'] = 16

        return strategy

    def _get_default_strategy(self) -> Dict[str, Any]:
        """Get default chunking strategy."""
        return {
            'chunk_size': 512,
            'overlap': 50,
            'use_semantic': False,
            'embedding_batch_size': 32
        }


# Singleton instance
_intelligence_agent = None


def get_file_intelligence_agent(file_handler=None, llm_client=None) -> FileIntelligenceAgent:
    """
    Get or create FileIntelligenceAgent singleton.

    Args:
        file_handler: Optional FileHandler instance
        llm_client: Optional LLM client instance

    Returns:
        FileIntelligenceAgent instance
    """
    global _intelligence_agent

    if _intelligence_agent is None:
        _intelligence_agent = FileIntelligenceAgent(
            file_handler=file_handler,
            llm_client=llm_client
        )

    return _intelligence_agent
