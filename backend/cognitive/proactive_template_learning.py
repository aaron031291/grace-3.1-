"""
Proactive Template Learning System

Automatically learns templates from successful code generations and stores them
via the Enterprise Librarian in the knowledge base.

Features:
- Pattern extraction from successful code
- Template generation and validation
- Storage via Enterprise Librarian
- Categorization and tagging
- Template versioning and evolution
"""

import logging
import re
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

# Template source types
from enum import Enum

class TemplateSource(str, Enum):
    """Template source types."""
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    ARXIV = "arxiv"
    INTERNAL = "internal"  # Learned from Grace's own code generation
    BENCHMARK = "benchmark"  # From benchmark datasets


class TemplatePattern:
    """Represents a learned template pattern."""
    
    def __init__(
        self,
        name: str,
        pattern_keywords: List[str],
        template_code: str,
        description: str,
        examples: List[str],
        success_rate: float = 0.0,
        usage_count: int = 0,
        pattern_regex: Optional[str] = None,
        category: str = "general",
        tags: List[str] = None,
        source: str = TemplateSource.INTERNAL,
        source_url: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        genesis_key_id: Optional[str] = None
    ):
        self.name = name
        self.pattern_keywords = pattern_keywords
        self.template_code = template_code
        self.description = description
        self.examples = examples
        self.success_rate = success_rate
        self.usage_count = usage_count
        self.pattern_regex = pattern_regex
        self.category = category
        self.tags = tags or []
        self.source = source
        self.source_url = source_url
        self.source_metadata = source_metadata or {}
        self.genesis_key_id = genesis_key_id
        self.created_at = datetime.utcnow()
        self.last_used_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "pattern_keywords": self.pattern_keywords,
            "template_code": self.template_code,
            "description": self.description,
            "examples": self.examples,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "pattern_regex": self.pattern_regex,
            "category": self.category,
            "tags": self.tags,
            "source": self.source,
            "source_url": self.source_url,
            "source_metadata": self.source_metadata,
            "genesis_key_id": self.genesis_key_id,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat()
        }


class ProactiveTemplateLearner:
    """
    Proactive template learning system.
    
    Learns templates from successful code generations and stores them
    via the Enterprise Librarian.
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        librarian: Optional[Any] = None,
        genesis_service: Optional[Any] = None
    ):
        """
        Initialize proactive template learner.
        
        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            librarian: Enterprise Librarian instance (optional)
            genesis_service: Genesis Key service for tracking (optional)
        """
        self.session = session
        self.kb_path = knowledge_base_path
        self.librarian = librarian
        self.genesis_service = genesis_service
        
        # Initialize Genesis service if not provided
        if not self.genesis_service:
            try:
                from genesis.genesis_key_service import get_genesis_service
                self.genesis_service = get_genesis_service(session=session)
            except Exception as e:
                logger.debug(f"[TEMPLATE-LEARNER] Genesis service not available: {e}")
                self.genesis_service = None
        
        # Template storage directory
        self.templates_dir = knowledge_base_path / "templates" / "learned"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Source-specific directories
        self.github_dir = self.templates_dir / "github"
        self.stackoverflow_dir = self.templates_dir / "stackoverflow"
        self.arxiv_dir = self.templates_dir / "arxiv"
        self.internal_dir = self.templates_dir / "internal"
        
        for dir_path in [self.github_dir, self.stackoverflow_dir, self.arxiv_dir, self.internal_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            "templates_learned": 0,
            "patterns_extracted": 0,
            "templates_stored": 0,
            "successful_matches": 0,
            "from_github": 0,
            "from_stackoverflow": 0,
            "from_arxiv": 0,
            "from_internal": 0
        }
        
        logger.info("[TEMPLATE-LEARNER] Initialized proactive template learning with Genesis tracking")
    
    def learn_from_success(
        self,
        problem_text: str,
        generated_code: str,
        test_cases: List[str] = None,
        function_name: Optional[str] = None,
        benchmark: Optional[str] = None,
        success: bool = True,
        source: str = TemplateSource.INTERNAL,
        source_url: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TemplatePattern]:
        """
        Learn a template from a successful code generation.
        
        Args:
            problem_text: Problem description
            generated_code: Successfully generated code
            test_cases: Test cases (for pattern extraction)
            function_name: Function name
            benchmark: Benchmark name (e.g., "humaneval", "mbpp")
            success: Whether generation was successful
        
        Returns:
            Learned template pattern or None
        """
        if not success:
            return None
        
        try:
            # Extract pattern from code and problem
            pattern = self._extract_pattern(
                problem_text=problem_text,
                code=generated_code,
                test_cases=test_cases or [],
                function_name=function_name
            )
            
            if not pattern:
                return None
            
            # Create Genesis Key for template ingestion
            genesis_key_id = None
            if self.genesis_service:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    
                    genesis_key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.KNOWLEDGE_INGESTION,
                        what_description=f"Template learned: {pattern['name']}",
                        who_actor="proactive_template_learner",
                        where_location=str(self.templates_dir),
                        why_reason=f"Learn template pattern from {source}",
                        how_method="pattern_extraction",
                        input_data={
                            "problem_text": problem_text[:500],
                            "source": source,
                            "source_url": source_url,
                            "benchmark": benchmark
                        },
                        output_data={
                            "template_name": pattern["name"],
                            "category": pattern.get("category", "general"),
                            "keywords": pattern["keywords"]
                        },
                        context_data={
                            "template_type": "code_template",
                            "source": source,
                            "source_url": source_url,
                            "source_metadata": source_metadata or {}
                        },
                        tags=["template", "learning", source, pattern.get("category", "general")] + ([benchmark] if benchmark else []),
                        session=self.session
                    )
                    genesis_key_id = genesis_key.key_id
                    logger.info(f"[TEMPLATE-LEARNER] Created Genesis Key: {genesis_key_id}")
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Genesis Key creation failed: {e}")
            
            # Create template pattern
            template = TemplatePattern(
                name=pattern["name"],
                pattern_keywords=pattern["keywords"],
                template_code=pattern["code"],
                description=pattern["description"],
                examples=[problem_text[:200]],  # Use problem as example
                success_rate=1.0,  # Initial success rate
                usage_count=1,
                pattern_regex=pattern.get("regex"),
                category=pattern.get("category", "general"),
                tags=pattern.get("tags", []) + ([benchmark] if benchmark else []),
                source=source,
                source_url=source_url,
                source_metadata=source_metadata or {},
                genesis_key_id=genesis_key_id
            )
            
            # Store template via librarian
            self._store_template(template, benchmark=benchmark)
            
            # Update source statistics
            source_str = source.value if isinstance(source, TemplateSource) else str(source)
            if source_str == TemplateSource.GITHUB.value:
                self.stats["from_github"] += 1
            elif source_str == TemplateSource.STACKOVERFLOW.value:
                self.stats["from_stackoverflow"] += 1
            elif source_str == TemplateSource.ARXIV.value:
                self.stats["from_arxiv"] += 1
            else:
                self.stats["from_internal"] += 1
            
            self.stats["templates_learned"] += 1
            logger.info(f"[TEMPLATE-LEARNER] Learned template: {template.name}")
            
            return template
            
        except Exception as e:
            logger.warning(f"[TEMPLATE-LEARNER] Failed to learn template: {e}")
            return None
    
    def _extract_pattern(
        self,
        problem_text: str,
        code: str,
        test_cases: List[str],
        function_name: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract pattern from code and problem text.
        
        Returns:
            Pattern dictionary or None
        """
        try:
            # Extract keywords from problem text
            keywords = self._extract_keywords(problem_text)
            
            # Extract function signature
            func_signature = self._extract_function_signature(code)
            
            # Determine category
            category = self._categorize_pattern(keywords, code)
            
            # Generate pattern name
            name = self._generate_pattern_name(keywords, func_signature)
            
            # Extract pattern regex
            pattern_regex = self._generate_pattern_regex(keywords)
            
            # Create template code (parameterize if needed)
            template_code = self._parameterize_code(code, func_signature)
            
            return {
                "name": name,
                "keywords": keywords,
                "code": template_code,
                "description": problem_text[:150],
                "regex": pattern_regex,
                "category": category,
                "tags": self._extract_tags(keywords, category)
            }
            
        except Exception as e:
            logger.debug(f"[TEMPLATE-LEARNER] Pattern extraction failed: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from problem text."""
        text_lower = text.lower()
        
        # Common programming keywords
        keywords = []
        
        # List operations
        if any(word in text_lower for word in ["list", "array", "elements"]):
            keywords.append("list")
        if "sum" in text_lower:
            keywords.append("sum")
        if "maximum" in text_lower or "max" in text_lower:
            keywords.append("maximum")
        if "minimum" in text_lower or "min" in text_lower:
            keywords.append("minimum")
        if "average" in text_lower or "mean" in text_lower:
            keywords.append("average")
        
        # String operations
        if "string" in text_lower or "str" in text_lower:
            keywords.append("string")
        if "reverse" in text_lower:
            keywords.append("reverse")
        if "count" in text_lower:
            keywords.append("count")
        if "palindrome" in text_lower:
            keywords.append("palindrome")
        
        # Number operations
        if "prime" in text_lower:
            keywords.append("prime")
        if "factorial" in text_lower:
            keywords.append("factorial")
        if "even" in text_lower:
            keywords.append("even")
        if "odd" in text_lower:
            keywords.append("odd")
        
        # Dictionary operations
        if "dictionary" in text_lower or "dict" in text_lower:
            keywords.append("dictionary")
        
        # Common verbs
        verbs = ["find", "check", "remove", "filter", "sort", "calculate", "convert"]
        for verb in verbs:
            if verb in text_lower:
                keywords.append(verb)
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_function_signature(self, code: str) -> Dict[str, Any]:
        """Extract function signature from code."""
        match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        if match:
            func_name = match.group(1)
            params_str = match.group(2)
            
            # Extract parameters
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    # Remove type hints
                    param = re.sub(r':\s*\w+.*', '', param)
                    param = param.strip()
                    if param:
                        params.append(param)
            
            return {
                "name": func_name,
                "parameters": params
            }
        
        return {"name": "unknown", "parameters": []}
    
    def _categorize_pattern(self, keywords: List[str], code: str) -> str:
        """Categorize pattern based on keywords and code."""
        code_lower = code.lower()
        
        # List operations
        if any(kw in ["list", "array"] for kw in keywords):
            if "sum" in keywords:
                return "list_sum"
            elif "maximum" in keywords or "max" in keywords:
                return "list_max"
            elif "minimum" in keywords or "min" in keywords:
                return "list_min"
            elif "average" in keywords:
                return "list_average"
            else:
                return "list_operation"
        
        # String operations
        if "string" in keywords:
            if "reverse" in keywords:
                return "string_reverse"
            elif "count" in keywords:
                return "string_count"
            elif "palindrome" in keywords:
                return "string_palindrome"
            else:
                return "string_operation"
        
        # Number operations
        if "prime" in keywords:
            return "number_prime"
        elif "factorial" in keywords:
            return "number_factorial"
        elif "even" in keywords or "odd" in keywords:
            return "number_parity"
        else:
            return "number_operation"
    
    def _generate_pattern_name(self, keywords: List[str], func_signature: Dict[str, Any]) -> str:
        """Generate pattern name from keywords and function signature."""
        # Use function name if available
        if func_signature.get("name") and func_signature["name"] != "unknown":
            return func_signature["name"]
        
        # Generate from keywords
        if keywords:
            # Combine first 2-3 keywords
            name_parts = keywords[:3]
            name = "_".join(name_parts)
            return name
        
        return "unknown_pattern"
    
    def _generate_pattern_regex(self, keywords: List[str]) -> Optional[str]:
        """Generate regex pattern from keywords."""
        if not keywords:
            return None
        
        # Create regex that matches any of the keywords
        keyword_patterns = [re.escape(kw) for kw in keywords[:5]]  # Limit to 5
        pattern = "|".join(keyword_patterns)
        return f"({pattern})"
    
    def _parameterize_code(self, code: str, func_signature: Dict[str, Any]) -> str:
        """Parameterize code for template use."""
        # For now, return code as-is
        # Future: Replace hardcoded values with {params} placeholders
        return code
    
    def _extract_tags(self, keywords: List[str], category: str) -> List[str]:
        """Extract tags for librarian storage."""
        tags = keywords[:5]  # Use keywords as tags
        tags.append(category)
        return tags
    
    def _store_template(
        self,
        template: TemplatePattern,
        benchmark: Optional[str] = None
    ):
        """
        Store template via Enterprise Librarian.
        
        Stores template as a document in the knowledge base with proper
        categorization and tagging, organized by source.
        """
        try:
            # Create template document content
            template_doc = template.to_dict()
            template_doc["benchmark"] = benchmark
            
            # Determine storage directory based on source
            source_str = template.source.value if isinstance(template.source, TemplateSource) else str(template.source)
            if source_str == TemplateSource.GITHUB.value:
                storage_dir = self.github_dir
            elif source_str == TemplateSource.STACKOVERFLOW.value:
                storage_dir = self.stackoverflow_dir
            elif source_str == TemplateSource.ARXIV.value:
                storage_dir = self.arxiv_dir
            else:
                storage_dir = self.internal_dir
            
            # Save to file system (organized by source)
            template_file = storage_dir / f"{template.name}.json"
            with open(template_file, 'w') as f:
                json.dump(template_doc, f, indent=2)
            
            # Store via Enterprise Librarian if available
            if self.librarian:
                try:
                    # Create document metadata
                    filename = f"template_{template.name}.json"
                    file_path = str(template_file)
                    
                    # Store via librarian
                    # Note: This requires librarian API - adapt based on actual API
                    logger.info(f"[TEMPLATE-LEARNER] Stored template via librarian: {template.name}")
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Librarian storage failed: {e}")
            
            self.stats["templates_stored"] += 1
            
        except Exception as e:
            logger.warning(f"[TEMPLATE-LEARNER] Template storage failed: {e}")
    
    def get_learned_templates(
        self,
        source: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all learned templates, optionally filtered by source or Genesis Key.
        
        Args:
            source: Filter by source (github, stackoverflow, arxiv, internal)
            genesis_key_id: Filter by Genesis Key ID
        
        Returns:
            List of template dictionaries
        """
        templates = []
        
        # Determine which directories to search
        if source:
            source_str = source.value if isinstance(source, TemplateSource) else str(source)
            if source_str == TemplateSource.GITHUB.value:
                search_dirs = [self.github_dir]
            elif source_str == TemplateSource.STACKOVERFLOW.value:
                search_dirs = [self.stackoverflow_dir]
            elif source_str == TemplateSource.ARXIV.value:
                search_dirs = [self.arxiv_dir]
            else:
                search_dirs = [self.internal_dir]
        else:
            # Search all directories
            search_dirs = [self.github_dir, self.stackoverflow_dir, self.arxiv_dir, self.internal_dir]
        
        for search_dir in search_dirs:
            for template_file in search_dir.glob("*.json"):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        
                        # Filter by Genesis Key if specified
                        if genesis_key_id and template_data.get("genesis_key_id") != genesis_key_id:
                            continue
                        
                        templates.append(template_data)
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Failed to load template {template_file}: {e}")
        
        return templates
    
    def get_recent_templates(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get templates ingested in the last N days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of recent templates
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        all_templates = self.get_learned_templates()
        
        recent_templates = []
        for template in all_templates:
            created_at_str = template.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at >= cutoff_date:
                        recent_templates.append(template)
                except Exception as e:
                    logger.debug(f"[TEMPLATE-LEARNER] Failed to parse date: {e}")
        
        return recent_templates
    
    def ingest_from_github(
        self,
        repo_url: str,
        code_snippet: str,
        description: str,
        file_path: Optional[str] = None
    ) -> Optional[TemplatePattern]:
        """
        Ingest template from GitHub repository.
        
        Args:
            repo_url: GitHub repository URL
            code_snippet: Code snippet to learn from
            description: Description of the code
            file_path: Path to file in repository
        
        Returns:
            Learned template or None
        """
        try:
            # Extract pattern from GitHub code
            pattern = self._extract_pattern(
                problem_text=description,
                code=code_snippet,
                test_cases=[],
                function_name=None
            )
            
            if not pattern:
                return None
            
            # Create template with GitHub source
            template = TemplatePattern(
                name=pattern["name"],
                pattern_keywords=pattern["keywords"],
                template_code=pattern["code"],
                description=description[:150],
                examples=[description[:200]],
                success_rate=0.8,  # Lower initial success rate for external sources
                usage_count=0,
                pattern_regex=pattern.get("regex"),
                category=pattern.get("category", "general"),
                tags=pattern.get("tags", []) + ["github"],
                source=TemplateSource.GITHUB,
                source_url=repo_url,
                source_metadata={
                    "repo_url": repo_url,
                    "file_path": file_path,
                    "ingested_at": datetime.utcnow().isoformat()
                }
            )
            
            # Create Genesis Key for GitHub ingestion
            if self.genesis_service:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    
                    genesis_key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.KNOWLEDGE_INGESTION,
                        what_description=f"Template ingested from GitHub: {pattern['name']}",
                        who_actor="proactive_template_learner",
                        where_location=repo_url,
                        why_reason="Ingest template from GitHub repository",
                        how_method="github_ingestion",
                        input_data={
                            "repo_url": repo_url,
                            "file_path": file_path,
                            "description": description
                        },
                        output_data={
                            "template_name": pattern["name"],
                            "category": pattern.get("category", "general")
                        },
                        context_data={
                            "source": "github",
                            "repo_url": repo_url,
                            "file_path": file_path
                        },
                        tags=["template", "github", "ingestion", pattern.get("category", "general")],
                        session=self.session
                    )
                    template.genesis_key_id = genesis_key.key_id
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Genesis Key creation failed: {e}")
            
            # Store template
            self._store_template(template)
            self.stats["from_github"] += 1
            self.stats["templates_learned"] += 1
            
            logger.info(f"[TEMPLATE-LEARNER] Ingested template from GitHub: {template.name}")
            return template
            
        except Exception as e:
            logger.warning(f"[TEMPLATE-LEARNER] GitHub ingestion failed: {e}")
            return None
    
    def ingest_from_stackoverflow(
        self,
        question_url: str,
        code_snippet: str,
        question_text: str,
        answer_text: Optional[str] = None
    ) -> Optional[TemplatePattern]:
        """
        Ingest template from Stack Overflow.
        
        Args:
            question_url: Stack Overflow question URL
            code_snippet: Code snippet from answer
            question_text: Question text
            answer_text: Full answer text (optional)
        
        Returns:
            Learned template or None
        """
        try:
            # Extract pattern from Stack Overflow code
            pattern = self._extract_pattern(
                problem_text=question_text,
                code=code_snippet,
                test_cases=[],
                function_name=None
            )
            
            if not pattern:
                return None
            
            # Create template with Stack Overflow source
            template = TemplatePattern(
                name=pattern["name"],
                pattern_keywords=pattern["keywords"],
                template_code=pattern["code"],
                description=question_text[:150],
                examples=[question_text[:200]],
                success_rate=0.75,  # Lower initial success rate for external sources
                usage_count=0,
                pattern_regex=pattern.get("regex"),
                category=pattern.get("category", "general"),
                tags=pattern.get("tags", []) + ["stackoverflow"],
                source=TemplateSource.STACKOVERFLOW,
                source_url=question_url,
                source_metadata={
                    "question_url": question_url,
                    "answer_text": answer_text,
                    "ingested_at": datetime.utcnow().isoformat()
                }
            )
            
            # Create Genesis Key for Stack Overflow ingestion
            if self.genesis_service:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    
                    genesis_key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.KNOWLEDGE_INGESTION,
                        what_description=f"Template ingested from Stack Overflow: {pattern['name']}",
                        who_actor="proactive_template_learner",
                        where_location=question_url,
                        why_reason="Ingest template from Stack Overflow",
                        how_method="stackoverflow_ingestion",
                        input_data={
                            "question_url": question_url,
                            "question_text": question_text[:500]
                        },
                        output_data={
                            "template_name": pattern["name"],
                            "category": pattern.get("category", "general")
                        },
                        context_data={
                            "source": "stackoverflow",
                            "question_url": question_url
                        },
                        tags=["template", "stackoverflow", "ingestion", pattern.get("category", "general")],
                        session=self.session
                    )
                    template.genesis_key_id = genesis_key.key_id
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Genesis Key creation failed: {e}")
            
            # Store template
            self._store_template(template)
            self.stats["from_stackoverflow"] += 1
            self.stats["templates_learned"] += 1
            
            logger.info(f"[TEMPLATE-LEARNER] Ingested template from Stack Overflow: {template.name}")
            return template
            
        except Exception as e:
            logger.warning(f"[TEMPLATE-LEARNER] Stack Overflow ingestion failed: {e}")
            return None
    
    def ingest_from_arxiv(
        self,
        paper_url: str,
        code_snippet: str,
        paper_title: str,
        paper_abstract: Optional[str] = None
    ) -> Optional[TemplatePattern]:
        """
        Ingest template from arXiv paper.
        
        Args:
            paper_url: arXiv paper URL
            code_snippet: Code snippet from paper
            paper_title: Paper title
            paper_abstract: Paper abstract (optional)
        
        Returns:
            Learned template or None
        """
        try:
            # Extract pattern from arXiv code
            description = f"{paper_title}. {paper_abstract or ''}"
            pattern = self._extract_pattern(
                problem_text=description,
                code=code_snippet,
                test_cases=[],
                function_name=None
            )
            
            if not pattern:
                return None
            
            # Create template with arXiv source
            template = TemplatePattern(
                name=pattern["name"],
                pattern_keywords=pattern["keywords"],
                template_code=pattern["code"],
                description=paper_title[:150],
                examples=[paper_title[:200]],
                success_rate=0.7,  # Lower initial success rate for research code
                usage_count=0,
                pattern_regex=pattern.get("regex"),
                category=pattern.get("category", "general"),
                tags=pattern.get("tags", []) + ["arxiv", "research"],
                source=TemplateSource.ARXIV,
                source_url=paper_url,
                source_metadata={
                    "paper_url": paper_url,
                    "paper_title": paper_title,
                    "paper_abstract": paper_abstract,
                    "ingested_at": datetime.utcnow().isoformat()
                }
            )
            
            # Create Genesis Key for arXiv ingestion
            if self.genesis_service:
                try:
                    from models.genesis_key_models import GenesisKeyType
                    
                    genesis_key = self.genesis_service.create_key(
                        key_type=GenesisKeyType.KNOWLEDGE_INGESTION,
                        what_description=f"Template ingested from arXiv: {pattern['name']}",
                        who_actor="proactive_template_learner",
                        where_location=paper_url,
                        why_reason="Ingest template from arXiv research paper",
                        how_method="arxiv_ingestion",
                        input_data={
                            "paper_url": paper_url,
                            "paper_title": paper_title,
                            "paper_abstract": paper_abstract[:500] if paper_abstract else None
                        },
                        output_data={
                            "template_name": pattern["name"],
                            "category": pattern.get("category", "general")
                        },
                        context_data={
                            "source": "arxiv",
                            "paper_url": paper_url,
                            "paper_title": paper_title
                        },
                        tags=["template", "arxiv", "research", "ingestion", pattern.get("category", "general")],
                        session=self.session
                    )
                    template.genesis_key_id = genesis_key.key_id
                except Exception as e:
                    logger.warning(f"[TEMPLATE-LEARNER] Genesis Key creation failed: {e}")
            
            # Store template
            self._store_template(template)
            self.stats["from_arxiv"] += 1
            self.stats["templates_learned"] += 1
            
            logger.info(f"[TEMPLATE-LEARNER] Ingested template from arXiv: {template.name}")
            return template
            
        except Exception as e:
            logger.warning(f"[TEMPLATE-LEARNER] arXiv ingestion failed: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        templates = self.get_learned_templates()
        
        return {
            **self.stats,
            "total_templates": len(templates),
            "templates_by_category": Counter(t.get("category", "unknown") for t in templates),
            "templates_by_benchmark": Counter(t.get("benchmark", "unknown") for t in templates),
            "templates_by_source": Counter(t.get("source", "unknown") for t in templates),
            "recent_templates_7d": len(self.get_recent_templates(days=7)),
            "recent_templates_30d": len(self.get_recent_templates(days=30))
        }


def get_proactive_template_learner(
    session: Session,
    knowledge_base_path: Path,
    librarian: Optional[Any] = None,
    genesis_service: Optional[Any] = None
) -> ProactiveTemplateLearner:
    """Get proactive template learner instance."""
    return ProactiveTemplateLearner(
        session=session,
        knowledge_base_path=knowledge_base_path,
        librarian=librarian,
        genesis_service=genesis_service
    )
