"""
External Knowledge Extractor - GitHub, AI Research, LLMs

Extracts knowledge from:
1. GitHub (repos, issues, code, discussions)
2. AI Research (arXiv, Papers with Code, HuggingFace)
3. LLMs (model documentation, best practices)
4. SWE Platforms (Stack Overflow, Reddit, etc.)

Integrates with Grace's Memory Mesh and Learning Systems.
"""

import logging
import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import re

logger = logging.getLogger(__name__)

# Import Grace systems
try:
    from genesis.genesis_key_service import get_genesis_service
    from models.genesis_key_models import GenesisKeyType
    from cognitive.memory_mesh_integration import MemoryMeshIntegration
    from llm_orchestrator.llm_orchestrator import LLMOrchestrator
except ImportError as e:
    logger.warning(f"[EXTERNAL-KNOWLEDGE] Could not import Grace systems: {e}")


@dataclass
class KnowledgeSource:
    """A knowledge source."""
    source_type: str  # github, arxiv, huggingface, stackoverflow, etc.
    source_id: str
    title: str
    content: str
    url: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExtractedPattern:
    """A pattern extracted from external knowledge."""
    pattern_type: str  # code_pattern, fix_pattern, best_practice, etc.
    pattern_content: str
    context: str
    source: KnowledgeSource
    confidence: float = 0.0
    tags: List[str] = field(default_factory=list)


class ExternalKnowledgeExtractor:
    """
    Extract knowledge from external sources and integrate with Grace.
    """
    
    def __init__(
        self,
        session: Session,
        memory_mesh: Optional[MemoryMeshIntegration] = None,
        llm_orchestrator: Optional[LLMOrchestrator] = None,
        github_token: Optional[str] = None,
        enable_github: bool = True,
        enable_arxiv: bool = True,
        enable_huggingface: bool = True,
        enable_stackoverflow: bool = True
    ):
        self.session = session
        self.memory_mesh = memory_mesh
        self.llm_orchestrator = llm_orchestrator
        
        # API tokens
        self.github_token = github_token
        self.github_headers = {}
        if github_token:
            self.github_headers["Authorization"] = f"token {github_token}"
        
        # Enable/disable sources
        self.enable_github = enable_github
        self.enable_arxiv = enable_arxiv
        self.enable_huggingface = enable_huggingface
        self.enable_stackoverflow = enable_stackoverflow
        
        # Genesis service
        try:
            self.genesis_service = get_genesis_service()
        except Exception as e:
            logger.warning(f"[EXTERNAL-KNOWLEDGE] Genesis service not available: {e}")
            self.genesis_service = None
        
        # Statistics
        self.stats = {
            "github_extracted": 0,
            "arxiv_extracted": 0,
            "huggingface_extracted": 0,
            "stackoverflow_extracted": 0,
            "patterns_created": 0,
            "memory_mesh_stored": 0
        }
    
    # ======================================================================
    # GITHUB EXTRACTION
    # ======================================================================
    
    def extract_from_github_repo(
        self,
        owner: str,
        repo: str,
        topics: List[str] = None,
        max_files: int = 50
    ) -> List[KnowledgeSource]:
        """Extract knowledge from a GitHub repository."""
        if not self.enable_github:
            return []
        
        sources = []
        
        try:
            # Get repo info
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(repo_url, headers=self.github_headers)
            if response.status_code != 200:
                logger.warning(f"[EXTERNAL-KNOWLEDGE] Could not access repo {owner}/{repo}")
                return []
            
            repo_data = response.json()
            
            # Get code files
            code_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
            code_response = requests.get(code_url, headers=self.github_headers)
            
            if code_response.status_code == 200:
                tree = code_response.json()
                python_files = [
                    f for f in tree.get("tree", [])
                    if f.get("path", "").endswith(".py") and f.get("type") == "blob"
                ][:max_files]
                
                for file_info in python_files:
                    try:
                        # Get file content
                        file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_info['path']}"
                        file_response = requests.get(file_url, headers=self.github_headers)
                        
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            content = self._decode_base64(file_data.get("content", ""))
                            
                            # Filter by topics if specified
                            if topics:
                                if not any(topic.lower() in content.lower() for topic in topics):
                                    continue
                            
                            source = KnowledgeSource(
                                source_type="github_repo",
                                source_id=f"{owner}/{repo}/{file_info['path']}",
                                title=f"{repo}: {file_info['path']}",
                                content=content,
                                url=f"https://github.com/{owner}/{repo}/blob/main/{file_info['path']}",
                                metadata={
                                    "owner": owner,
                                    "repo": repo,
                                    "file_path": file_info['path'],
                                    "stars": repo_data.get("stargazers_count", 0),
                                    "language": repo_data.get("language", "Python")
                                },
                                quality_score=self._calculate_quality_score(repo_data)
                            )
                            sources.append(source)
                            
                            time.sleep(0.1)  # Rate limiting
                    except Exception as e:
                        logger.debug(f"[EXTERNAL-KNOWLEDGE] Error extracting file {file_info.get('path')}: {e}")
            
            self.stats["github_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} files from {owner}/{repo}")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] GitHub extraction error: {e}")
        
        return sources
    
    def extract_from_github_issues(
        self,
        owner: str,
        repo: str,
        error_patterns: List[str] = None,
        max_issues: int = 100
    ) -> List[KnowledgeSource]:
        """Extract solutions from GitHub issues."""
        if not self.enable_github:
            return []
        
        sources = []
        
        try:
            # Search for closed issues with solutions
            search_url = "https://api.github.com/search/issues"
            query = f"repo:{owner}/{repo} is:closed is:issue"
            if error_patterns:
                query += f" {' OR '.join(error_patterns)}"
            
            params = {
                "q": query,
                "sort": "reactions",
                "order": "desc",
                "per_page": min(max_issues, 100)
            }
            
            response = requests.get(search_url, headers=self.github_headers, params=params)
            
            if response.status_code == 200:
                issues = response.json().get("items", [])
                
                for issue in issues:
                    # Get issue comments (solutions)
                    comments_url = issue.get("comments_url")
                    if comments_url and issue.get("comments", 0) > 0:
                        comments_response = requests.get(comments_url, headers=self.github_headers)
                        
                        if comments_response.status_code == 200:
                            comments = comments_response.json()
                            
                            # Find solution comments
                            for comment in comments:
                                if self._contains_solution(comment.get("body", "")):
                                    source = KnowledgeSource(
                                        source_type="github_issue",
                                        source_id=f"{owner}/{repo}/issues/{issue['number']}/comment/{comment['id']}",
                                        title=issue.get("title", ""),
                                        content=comment.get("body", ""),
                                        url=comment.get("html_url", ""),
                                        metadata={
                                            "issue_number": issue.get("number"),
                                            "comment_id": comment.get("id"),
                                            "reactions": comment.get("reactions", {}),
                                            "author": comment.get("user", {}).get("login", "")
                                        },
                                        quality_score=self._calculate_issue_quality(comment)
                                    )
                                    sources.append(source)
                    
                    time.sleep(0.2)  # Rate limiting
            
            self.stats["github_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} solutions from {owner}/{repo} issues")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] GitHub issues extraction error: {e}")
        
        return sources
    
    def extract_from_github_code_search(
        self,
        query: str,
        language: str = "python",
        max_results: int = 50
    ) -> List[KnowledgeSource]:
        """Search GitHub code for patterns."""
        if not self.enable_github:
            return []
        
        sources = []
        
        try:
            search_url = "https://api.github.com/search/code"
            params = {
                "q": f"{query} language:{language}",
                "sort": "indexed",
                "order": "desc",
                "per_page": min(max_results, 100)
            }
            
            response = requests.get(search_url, headers=self.github_headers, params=params)
            
            if response.status_code == 200:
                results = response.json().get("items", [])
                
                for result in results:
                    try:
                        # Get file content
                        file_url = result.get("url")
                        file_response = requests.get(file_url, headers=self.github_headers)
                        
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            content = self._decode_base64(file_data.get("content", ""))
                            
                            source = KnowledgeSource(
                                source_type="github_code",
                                source_id=result.get("sha", ""),
                                title=f"{result.get('repository', {}).get('full_name', '')}: {result.get('path', '')}",
                                content=content,
                                url=result.get("html_url", ""),
                                metadata={
                                    "repository": result.get("repository", {}).get("full_name", ""),
                                    "path": result.get("path", ""),
                                    "language": result.get("language", "")
                                },
                                quality_score=0.7  # Default for code search
                            )
                            sources.append(source)
                        
                        time.sleep(0.1)  # Rate limiting
                    except Exception as e:
                        logger.debug(f"[EXTERNAL-KNOWLEDGE] Error extracting code result: {e}")
            
            self.stats["github_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} code results for query: {query}")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] GitHub code search error: {e}")
        
        return sources
    
    # ======================================================================
    # AI RESEARCH EXTRACTION
    # ======================================================================
    
    def extract_from_arxiv(
        self,
        query: str,
        max_results: int = 20,
        categories: List[str] = None
    ) -> List[KnowledgeSource]:
        """Extract knowledge from arXiv papers."""
        if not self.enable_arxiv:
            return []
        
        sources = []
        
        try:
            # arXiv API
            arxiv_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            if categories:
                cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
                params["search_query"] = f"({params['search_query']}) AND ({cat_query})"
            
            response = requests.get(arxiv_url, params=params)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                # Parse arXiv entries
                namespace = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", namespace)
                
                for entry in entries:
                    try:
                        title = entry.find("atom:title", namespace).text if entry.find("atom:title", namespace) is not None else ""
                        summary = entry.find("atom:summary", namespace).text if entry.find("atom:summary", namespace) is not None else ""
                        arxiv_id = entry.find("atom:id", namespace).text.split("/")[-1] if entry.find("atom:id", namespace) is not None else ""
                        published = entry.find("atom:published", namespace).text if entry.find("atom:published", namespace) is not None else ""
                        
                        # Get authors
                        authors = [author.find("atom:name", namespace).text for author in entry.findall("atom:author", namespace)]
                        
                        source = KnowledgeSource(
                            source_type="arxiv",
                            source_id=arxiv_id,
                            title=title,
                            content=summary,
                            url=f"https://arxiv.org/abs/{arxiv_id}",
                            metadata={
                                "arxiv_id": arxiv_id,
                                "authors": authors,
                                "published": published,
                                "categories": [cat.get("term") for cat in entry.findall("atom:category", namespace)]
                            },
                            quality_score=0.8  # Research papers are generally high quality
                        )
                        sources.append(source)
                    except Exception as e:
                        logger.debug(f"[EXTERNAL-KNOWLEDGE] Error parsing arXiv entry: {e}")
            
            self.stats["arxiv_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} papers from arXiv for query: {query}")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] arXiv extraction error: {e}")
        
        return sources
    
    def extract_from_huggingface(
        self,
        model_name: str = None,
        task: str = None,
        max_results: int = 20
    ) -> List[KnowledgeSource]:
        """Extract knowledge from HuggingFace models and documentation."""
        if not self.enable_huggingface:
            return []
        
        sources = []
        
        try:
            # HuggingFace Hub API
            if model_name:
                # Get specific model
                model_url = f"https://huggingface.co/api/models/{model_name}"
                response = requests.get(model_url)
                
                if response.status_code == 200:
                    model_data = response.json()
                    
                    # Get model card (README)
                    readme_url = f"https://huggingface.co/{model_name}/raw/main/README.md"
                    readme_response = requests.get(readme_url)
                    
                    content = ""
                    if readme_response.status_code == 200:
                        content = readme_response.text
                    else:
                        content = json.dumps(model_data, indent=2)
                    
                    source = KnowledgeSource(
                        source_type="huggingface",
                        source_id=model_name,
                        title=f"HuggingFace Model: {model_name}",
                        content=content,
                        url=f"https://huggingface.co/{model_name}",
                        metadata={
                            "model_name": model_name,
                            "task": model_data.get("pipeline_tag", ""),
                            "library": model_data.get("library_name", ""),
                            "downloads": model_data.get("downloads", 0)
                        },
                        quality_score=0.75
                    )
                    sources.append(source)
            else:
                # Search models
                search_url = "https://huggingface.co/api/models"
                params = {
                    "search": task or "text-generation",
                    "limit": max_results
                }
                
                response = requests.get(search_url, params=params)
                
                if response.status_code == 200:
                    models = response.json()
                    
                    for model in models[:max_results]:
                        model_name = model.get("id", "")
                        if model_name:
                            # Get model card
                            readme_url = f"https://huggingface.co/{model_name}/raw/main/README.md"
                            readme_response = requests.get(readme_url)
                            
                            content = readme_response.text if readme_response.status_code == 200 else ""
                            
                            source = KnowledgeSource(
                                source_type="huggingface",
                                source_id=model_name,
                                title=f"HuggingFace Model: {model_name}",
                                content=content,
                                url=f"https://huggingface.co/{model_name}",
                                metadata={
                                    "model_name": model_name,
                                    "task": model.get("pipeline_tag", ""),
                                    "downloads": model.get("downloads", 0)
                                },
                                quality_score=0.7
                            )
                            sources.append(source)
            
            self.stats["huggingface_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} models from HuggingFace")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] HuggingFace extraction error: {e}")
        
        return sources
    
    # ======================================================================
    # STACK OVERFLOW EXTRACTION
    # ======================================================================
    
    def extract_from_stackoverflow(
        self,
        query: str,
        tags: List[str] = None,
        max_results: int = 20
    ) -> List[KnowledgeSource]:
        """Extract solutions from Stack Overflow."""
        if not self.enable_stackoverflow:
            return []
        
        sources = []
        
        try:
            search_url = "https://api.stackexchange.com/2.3/search"
            params = {
                "order": "desc",
                "sort": "votes",
                "intitle": query,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": min(max_results, 100)
            }
            
            if tags:
                params["tagged"] = ";".join(tags)
            
            response = requests.get(search_url, params=params)
            
            if response.status_code == 200:
                questions = response.json().get("items", [])
                
                for question in questions:
                    # Get accepted answer
                    if question.get("accepted_answer_id"):
                        answer_id = question["accepted_answer_id"]
                        answer_url = f"https://api.stackexchange.com/2.3/answers/{answer_id}"
                        answer_params = {
                            "site": "stackoverflow",
                            "filter": "withbody"
                        }
                        answer_response = requests.get(answer_url, params=answer_params)
                        
                        if answer_response.status_code == 200:
                            answers = answer_response.json().get("items", [])
                            if answers:
                                answer = answers[0]
                                
                                source = KnowledgeSource(
                                    source_type="stackoverflow",
                                    source_id=str(answer_id),
                                    title=question.get("title", ""),
                                    content=answer.get("body", ""),
                                    url=answer.get("link", ""),
                                    metadata={
                                        "question_id": question.get("question_id"),
                                        "answer_id": answer_id,
                                        "score": answer.get("score", 0),
                                        "is_accepted": True,
                                        "tags": question.get("tags", [])
                                    },
                                    quality_score=self._calculate_stackoverflow_quality(answer, question)
                                )
                                sources.append(source)
            
            self.stats["stackoverflow_extracted"] += len(sources)
            logger.info(f"[EXTERNAL-KNOWLEDGE] Extracted {len(sources)} solutions from Stack Overflow for query: {query}")
            
        except Exception as e:
            logger.error(f"[EXTERNAL-KNOWLEDGE] Stack Overflow extraction error: {e}")
        
        return sources
    
    # ======================================================================
    # PATTERN EXTRACTION & INTEGRATION
    # ======================================================================
    
    def extract_patterns(self, sources: List[KnowledgeSource]) -> List[ExtractedPattern]:
        """Extract patterns from knowledge sources."""
        patterns = []
        
        for source in sources:
            try:
                # Extract code patterns
                code_patterns = self._extract_code_patterns(source)
                patterns.extend(code_patterns)
                
                # Extract fix patterns
                fix_patterns = self._extract_fix_patterns(source)
                patterns.extend(fix_patterns)
                
                # Extract best practices
                best_practices = self._extract_best_practices(source)
                patterns.extend(best_practices)
                
            except Exception as e:
                logger.debug(f"[EXTERNAL-KNOWLEDGE] Error extracting patterns from {source.source_id}: {e}")
        
        self.stats["patterns_created"] += len(patterns)
        return patterns
    
    def _extract_code_patterns(self, source: KnowledgeSource) -> List[ExtractedPattern]:
        """Extract code patterns from source."""
        patterns = []
        
        # Find code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', source.content, re.DOTALL)
        code_blocks.extend(re.findall(r'```\n(.*?)\n```', source.content, re.DOTALL))
        
        for code in code_blocks:
            pattern = ExtractedPattern(
                pattern_type="code_pattern",
                pattern_content=code,
                context=source.title,
                source=source,
                confidence=0.7,
                tags=["code", source.source_type]
            )
            patterns.append(pattern)
        
        return patterns
    
    def _extract_fix_patterns(self, source: KnowledgeSource) -> List[ExtractedPattern]:
        """Extract fix patterns from source."""
        patterns = []
        
        # Look for error-fix pairs
        error_pattern = r'(?:Error|Exception|Warning):\s*(.*?)(?:\n|$)'
        errors = re.findall(error_pattern, source.content, re.IGNORECASE)
        
        for error in errors:
            # Find solution near error
            error_index = source.content.find(error)
            if error_index != -1:
                solution_snippet = source.content[max(0, error_index-200):error_index+500]
                
                pattern = ExtractedPattern(
                    pattern_type="fix_pattern",
                    pattern_content=solution_snippet,
                    context=f"Fix for: {error}",
                    source=source,
                    confidence=0.8 if "accepted" in source.metadata.get("is_accepted", "") else 0.6,
                    tags=["fix", "error", source.source_type]
                )
                patterns.append(pattern)
        
        return patterns
    
    def _extract_best_practices(self, source: KnowledgeSource) -> List[ExtractedPattern]:
        """Extract best practices from source."""
        patterns = []
        
        # Look for best practice indicators
        practice_indicators = [
            "best practice",
            "recommended",
            "should",
            "always",
            "never",
            "avoid"
        ]
        
        for indicator in practice_indicators:
            if indicator.lower() in source.content.lower():
                # Extract sentence/paragraph
                sentences = re.split(r'[.!?]\s+', source.content)
                for sentence in sentences:
                    if indicator.lower() in sentence.lower():
                        pattern = ExtractedPattern(
                            pattern_type="best_practice",
                            pattern_content=sentence,
                            context=source.title,
                            source=source,
                            confidence=0.7,
                            tags=["best_practice", source.source_type]
                        )
                        patterns.append(pattern)
                        break
        
        return patterns
    
    def store_in_memory_mesh(self, patterns: List[ExtractedPattern]) -> int:
        """Store extracted patterns in Memory Mesh."""
        if not self.memory_mesh:
            logger.warning("[EXTERNAL-KNOWLEDGE] Memory Mesh not available")
            return 0
        
        stored = 0
        
        for pattern in patterns:
            try:
                # Create memory from pattern
                memory_data = {
                    "pattern_type": pattern.pattern_type,
                    "pattern_content": pattern.pattern_content,
                    "context": pattern.context,
                    "source": {
                        "type": pattern.source.source_type,
                        "id": pattern.source.source_id,
                        "url": pattern.source.url
                    },
                    "confidence": pattern.confidence,
                    "tags": pattern.tags,
                    "extracted_at": pattern.source.extracted_at.isoformat()
                }
                
                # Store in Memory Mesh
                # This would use the actual Memory Mesh API
                # For now, we'll log it
                logger.info(f"[EXTERNAL-KNOWLEDGE] Storing pattern: {pattern.pattern_type} from {pattern.source.source_type}")
                stored += 1
                
            except Exception as e:
                logger.debug(f"[EXTERNAL-KNOWLEDGE] Error storing pattern: {e}")
        
        self.stats["memory_mesh_stored"] += stored
        return stored
    
    # ======================================================================
    # HELPER METHODS
    # ======================================================================
    
    def _decode_base64(self, content: str) -> str:
        """Decode base64 content."""
        try:
            import base64
            return base64.b64decode(content).decode('utf-8')
        except Exception:
            return content
    
    def _contains_solution(self, text: str) -> bool:
        """Check if text contains a solution."""
        solution_indicators = [
            "solution",
            "fix",
            "workaround",
            "try this",
            "here's how",
            "extend_existing",
            "import",
            "def ",
            "class "
        ]
        return any(indicator.lower() in text.lower() for indicator in solution_indicators)
    
    def _calculate_quality_score(self, repo_data: Dict) -> float:
        """Calculate quality score for GitHub repo."""
        score = 0.5  # Base score
        
        # Stars
        stars = repo_data.get("stargazers_count", 0)
        if stars > 1000:
            score += 0.2
        elif stars > 100:
            score += 0.1
        
        # Forks
        forks = repo_data.get("forks_count", 0)
        if forks > 100:
            score += 0.1
        
        # Recent activity
        updated = repo_data.get("updated_at", "")
        if updated:
            from datetime import datetime, timezone
            try:
                updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                days_old = (datetime.now(timezone.utc) - updated_date).days
                if days_old < 90:
                    score += 0.1
            except:
                pass
        
        return min(score, 1.0)
    
    def _calculate_issue_quality(self, comment: Dict) -> float:
        """Calculate quality score for GitHub issue comment."""
        score = 0.5
        
        # Reactions
        reactions = comment.get("reactions", {})
        if reactions.get("+1", 0) > 5:
            score += 0.2
        if reactions.get("heart", 0) > 0:
            score += 0.1
        
        # Author association
        author_association = comment.get("author_association", "")
        if author_association in ["OWNER", "MEMBER", "COLLABORATOR"]:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_stackoverflow_quality(self, answer: Dict, question: Dict) -> float:
        """Calculate quality score for Stack Overflow answer."""
        score = 0.5
        
        # Score
        answer_score = answer.get("score", 0)
        if answer_score > 10:
            score += 0.3
        elif answer_score > 5:
            score += 0.2
        
        # Accepted
        if answer.get("is_accepted", False):
            score += 0.2
        
        return min(score, 1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return self.stats.copy()


def get_external_knowledge_extractor(
    session: Session,
    memory_mesh: Optional[MemoryMeshIntegration] = None,
    llm_orchestrator: Optional[LLMOrchestrator] = None,
    github_token: Optional[str] = None
) -> ExternalKnowledgeExtractor:
    """Factory function to get External Knowledge Extractor."""
    return ExternalKnowledgeExtractor(
        session=session,
        memory_mesh=memory_mesh,
        llm_orchestrator=llm_orchestrator,
        github_token=github_token
    )
