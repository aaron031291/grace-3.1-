import logging
import ast
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

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

    def __init__(self, file_handler=None, ollama_client=None):
        """
        Initialize intelligence agent.

        Args:
            file_handler: FileHandler for text extraction
            ollama_client: OllamaClient for AI analysis
        """
        self.file_handler = file_handler
        self.ollama_client = ollama_client

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

            # 5. Extract file relationships using AST analysis
            relationships = self._analyze_file_relationships(file_path, content)

            # 6. Additional metadata
            metadata = {
                'file_size': len(content),
                'line_count': content.count('\n') + 1,
                'word_count': len(content.split()),
                'analyzed_at': datetime.utcnow().isoformat()
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
        if self.ollama_client:
            try:
                prompt = f"""Summarize the following text in 1-2 sentences (max {max_length} chars):

{content[:2000]}

Summary:"""

                response = self.ollama_client.generate(
                    model="qwen2.5:latest",
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

    def _analyze_file_relationships(
        self,
        file_path: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze file relationships using AST parsing.

        Extracts:
        - Import relationships (what files/modules this file imports)
        - Export relationships (what this file exports)
        - Dependency relationships (external packages used)
        - Call relationships (function/method calls)
        - Inheritance relationships (class hierarchies)

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of relationship dictionaries
        """
        relationships = []
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.py':
            relationships = self._analyze_python_relationships(file_path, content)

        return relationships

    def _analyze_python_relationships(
        self,
        file_path: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze Python file relationships using AST.

        Args:
            file_path: Path to the Python file
            content: File content

        Returns:
            List of relationship dictionaries
        """
        relationships = []

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logger.debug(f"[FILE-INTELLIGENCE] Syntax error parsing {file_path}: {e}")
            return relationships
        except Exception as e:
            logger.debug(f"[FILE-INTELLIGENCE] Failed to parse {file_path}: {e}")
            return relationships

        # Extract imports
        relationships.extend(self._extract_imports(file_path, tree))

        # Extract exports (top-level definitions)
        relationships.extend(self._extract_exports(file_path, tree))

        # Extract function/method calls
        relationships.extend(self._extract_calls(file_path, tree))

        # Extract class inheritance
        relationships.extend(self._extract_inheritance(file_path, tree))

        return relationships

    def _extract_imports(
        self,
        file_path: str,
        tree: ast.AST
    ) -> List[Dict[str, Any]]:
        """Extract import relationships from AST."""
        relationships = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    relationships.append({
                        "type": "imports",
                        "source": file_path,
                        "target": alias.name,
                        "details": {
                            "imported_names": [alias.asname or alias.name],
                            "line": node.lineno,
                            "import_type": "module"
                        }
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imported_names = [
                    alias.asname or alias.name for alias in node.names
                ]
                relationships.append({
                    "type": "imports",
                    "source": file_path,
                    "target": module,
                    "details": {
                        "imported_names": imported_names,
                        "line": node.lineno,
                        "import_type": "from",
                        "level": node.level  # relative import level
                    }
                })

                # Track external dependencies (stdlib vs third-party)
                if node.level == 0 and module:
                    top_level_module = module.split('.')[0]
                    if not self._is_local_module(file_path, top_level_module):
                        relationships.append({
                            "type": "dependency",
                            "source": file_path,
                            "target": top_level_module,
                            "details": {
                                "full_module": module,
                                "imported_names": imported_names,
                                "line": node.lineno
                            }
                        })

        return relationships

    def _extract_exports(
        self,
        file_path: str,
        tree: ast.AST
    ) -> List[Dict[str, Any]]:
        """Extract exported definitions (top-level functions/classes)."""
        relationships = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                is_private = node.name.startswith('_')
                relationships.append({
                    "type": "exports",
                    "source": file_path,
                    "target": node.name,
                    "details": {
                        "kind": "function",
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "is_private": is_private,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    }
                })

            elif isinstance(node, ast.ClassDef):
                is_private = node.name.startswith('_')
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                relationships.append({
                    "type": "exports",
                    "source": file_path,
                    "target": node.name,
                    "details": {
                        "kind": "class",
                        "is_private": is_private,
                        "line": node.lineno,
                        "methods": methods
                    }
                })

        return relationships

    def _extract_calls(
        self,
        file_path: str,
        tree: ast.AST
    ) -> List[Dict[str, Any]]:
        """Extract function/method call relationships."""
        relationships = []
        seen_calls: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_info = self._get_call_info(node)
                if call_info:
                    call_key = f"{call_info['name']}:{call_info.get('attribute', '')}"
                    if call_key not in seen_calls:
                        seen_calls.add(call_key)
                        relationships.append({
                            "type": "calls",
                            "source": file_path,
                            "target": call_info['name'],
                            "details": {
                                "function": call_info.get('attribute') or call_info['name'],
                                "line": node.lineno,
                                "is_method": call_info.get('is_method', False)
                            }
                        })

        return relationships

    def _get_call_info(self, node: ast.Call) -> Optional[Dict[str, Any]]:
        """Extract call information from a Call node."""
        if isinstance(node.func, ast.Name):
            return {
                "name": node.func.id,
                "is_method": False
            }
        elif isinstance(node.func, ast.Attribute):
            # Get the base object name
            base = node.func.value
            if isinstance(base, ast.Name):
                return {
                    "name": base.id,
                    "attribute": node.func.attr,
                    "is_method": True
                }
            elif isinstance(base, ast.Attribute):
                # Nested attribute access (e.g., a.b.c())
                parts = []
                current = base
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                parts.reverse()
                return {
                    "name": ".".join(parts),
                    "attribute": node.func.attr,
                    "is_method": True
                }
        return None

    def _extract_inheritance(
        self,
        file_path: str,
        tree: ast.AST
    ) -> List[Dict[str, Any]]:
        """Extract class inheritance relationships."""
        relationships = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.bases:
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle module.ClassName
                        parts = []
                        current = base
                        while isinstance(current, ast.Attribute):
                            parts.append(current.attr)
                            current = current.value
                        if isinstance(current, ast.Name):
                            parts.append(current.id)
                        parts.reverse()
                        base_names.append(".".join(parts))

                if base_names:
                    relationships.append({
                        "type": "inheritance",
                        "source": file_path,
                        "target": node.name,
                        "details": {
                            "child_class": node.name,
                            "parent_classes": base_names,
                            "line": node.lineno
                        }
                    })

        return relationships

    def _is_local_module(self, file_path: str, module_name: str) -> bool:
        """Check if a module is local to the project."""
        # Common standard library modules (subset)
        stdlib_modules = {
            'os', 'sys', 'typing', 'pathlib', 'datetime', 'json', 'logging',
            'ast', 're', 'collections', 'itertools', 'functools', 'dataclasses',
            'abc', 'io', 'time', 'math', 'random', 'hashlib', 'base64',
            'urllib', 'http', 'socket', 'threading', 'multiprocessing',
            'subprocess', 'shutil', 'tempfile', 'glob', 'fnmatch', 'pickle',
            'copy', 'enum', 'contextlib', 'traceback', 'warnings', 'inspect',
            'importlib', 'unittest', 'pytest', 'asyncio', 'concurrent'
        }

        if module_name in stdlib_modules:
            return True

        # Check if module exists in the same directory or parent
        file_dir = Path(file_path).parent
        potential_module = file_dir / f"{module_name}.py"
        potential_package = file_dir / module_name / "__init__.py"

        return potential_module.exists() or potential_package.exists()

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


def get_file_intelligence_agent(file_handler=None, ollama_client=None) -> FileIntelligenceAgent:
    """
    Get or create FileIntelligenceAgent singleton.

    Args:
        file_handler: Optional FileHandler instance
        ollama_client: Optional OllamaClient instance

    Returns:
        FileIntelligenceAgent instance
    """
    global _intelligence_agent

    if _intelligence_agent is None:
        _intelligence_agent = FileIntelligenceAgent(
            file_handler=file_handler,
            ollama_client=ollama_client
        )

    return _intelligence_agent
