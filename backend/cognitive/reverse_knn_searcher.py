import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
import time
from cognitive.gap_detector import KnowledgeGap
class SimilarProblem:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """A similar problem found via reverse KNN."""
    source: str  # "stackoverflow", "github", etc.
    error_message: str
    solution: str
    similarity_score: float  # 0.0 - 1.0
    url: str
    upvotes: int = 0
    is_accepted: bool = False


class ReverseKNNSearcher:
    """
    Uses reverse KNN to find similar problems and solutions.
    
    Concept:
    - Given an error (query point)
    - Find K nearest neighbors in problem space (similar errors)
    - Extract solutions from those neighbors
    - Learn from solutions
    """
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.search_cache: Dict[str, List[SimilarProblem]] = {}
    
    def find_similar_problems(
        self,
        gap: KnowledgeGap,
        k: int = 5,
        sources: List[str] = None
    ) -> List[SimilarProblem]:
        """
        Find K similar problems using reverse KNN.
        
        Args:
            gap: Knowledge gap to find similar problems for
            k: Number of neighbors to find
            sources: Sources to search ("stackoverflow", "github")
        
        Returns:
            List of similar problems with solutions
        """
        if sources is None:
            sources = ["stackoverflow", "github"]
        
        # Check cache
        cache_key = f"{gap.error_message[:100]}"
        if cache_key in self.search_cache:
            logger.debug(f"[REVERSE-KNN] Using cached results for: {cache_key[:50]}")
            return self.search_cache[cache_key][:k]
        
        similar_problems = []
        
        # Search each source
        if "stackoverflow" in sources:
            so_problems = self._search_stackoverflow(gap, k)
            similar_problems.extend(so_problems)
        
        if "github" in sources:
            gh_problems = self._search_github(gap, k)
            similar_problems.extend(gh_problems)
        
        # Sort by similarity score (reverse KNN - most similar first)
        similar_problems.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Take top K
        top_k = similar_problems[:k]
        
        # Cache results
        self.search_cache[cache_key] = top_k
        
        logger.info(
            f"[REVERSE-KNN] Found {len(top_k)} similar problems for gap: "
            f"{gap.error_message[:50]}..."
        )
        
        return top_k
    
    def _search_stackoverflow(self, gap: KnowledgeGap, k: int) -> List[SimilarProblem]:
        """Search Stack Overflow for similar problems."""
        similar_problems = []
        
        try:
            # Extract key terms from error message
            query = self._extract_search_terms(gap.error_message)
            
            url = "https://api.stackexchange.com/2.3/search"
            params = {
                "order": "desc",
                "sort": "relevance",  # Relevance = similarity in problem space
                "tagged": "python",
                "intitle": query,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": k * 2  # Get more to filter
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return similar_problems
            
            questions = response.json().get("items", [])
            
            for question in questions:
                # Calculate similarity score
                similarity = self._calculate_similarity(
                    gap.error_message,
                    question.get("title", "") + " " + question.get("body", "")
                )
                
                # Get accepted answer if available
                if question.get("accepted_answer_id"):
                    answer_id = question["accepted_answer_id"]
                    answer = self._get_stackoverflow_answer(answer_id)
                    if answer:
                        solution = self._extract_solution(answer["body"])
                        if solution:
                            similar_problems.append(SimilarProblem(
                                source="stackoverflow",
                                error_message=question.get("title", ""),
                                solution=solution,
                                similarity_score=similarity,
                                url=answer["link"],
                                upvotes=answer.get("score", 0),
                                is_accepted=True
                            ))
                
                # Also check top answers
                if question.get("answer_count", 0) > 0:
                    answers_url = f"https://api.stackexchange.com/2.3/questions/{question['question_id']}/answers"
                    answers_params = {
                        "order": "desc",
                        "sort": "votes",
                        "site": "stackoverflow",
                        "filter": "withbody",
                        "pagesize": 3
                    }
                    answers_response = requests.get(answers_url, params=answers_params, timeout=10)
                    if answers_response.status_code == 200:
                        answers = answers_response.json().get("items", [])
                        for answer in answers[:2]:  # Top 2 answers
                            if answer.get("score", 0) > 5:  # Only high-quality answers
                                solution = self._extract_solution(answer["body"])
                                if solution:
                                    similarity = self._calculate_similarity(
                                        gap.error_message,
                                        question.get("title", "") + " " + answer["body"]
                                    )
                                    similar_problems.append(SimilarProblem(
                                        source="stackoverflow",
                                        error_message=question.get("title", ""),
                                        solution=solution,
                                        similarity_score=similarity,
                                        url=answer["link"],
                                        upvotes=answer.get("score", 0),
                                        is_accepted=answer.get("is_accepted", False)
                                    ))
            
            time.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] Stack Overflow search failed: {e}")
        
        return similar_problems
    
    def _search_github(self, gap: KnowledgeGap, k: int) -> List[SimilarProblem]:
        """Search GitHub Issues for similar problems."""
        similar_problems = []
        
        try:
            query = self._extract_search_terms(gap.error_message)
            
            url = "https://api.github.com/search/issues"
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            params = {
                "q": f"{query} is:closed language:python",
                "sort": "reactions",  # Most reactions = most similar/helpful
                "order": "desc",
                "per_page": k
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                return similar_problems
            
            issues = response.json().get("items", [])
            
            for issue in issues:
                # Calculate similarity
                similarity = self._calculate_similarity(
                    gap.error_message,
                    issue.get("title", "") + " " + issue.get("body", "")
                )
                
                # Get comments (solutions)
                if issue.get("comments", 0) > 0:
                    comments_url = issue["comments_url"]
                    comments_response = requests.get(comments_url, headers=headers, timeout=10)
                    if comments_response.status_code == 200:
                        comments = comments_response.json()
                        for comment in comments[:3]:  # Top 3 comments
                            if self._contains_solution(comment["body"]):
                                solution = self._extract_solution(comment["body"])
                                if solution:
                                    similar_problems.append(SimilarProblem(
                                        source="github",
                                        error_message=issue.get("title", ""),
                                        solution=solution,
                                        similarity_score=similarity,
                                        url=comment["html_url"],
                                        upvotes=comment.get("reactions", {}).get("+1", 0),
                                        is_accepted=False
                                    ))
            
            time.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] GitHub search failed: {e}")
        
        return similar_problems
    
    def _extract_search_terms(self, error_message: str) -> str:
        """Extract key search terms from error message."""
        # Remove common words
        common_words = {"the", "a", "an", "is", "are", "was", "were", "error", "exception"}
        
        # Extract error type
        error_type_match = re.search(r'(\w+Error|\w+Exception)', error_message)
        if error_type_match:
            error_type = error_type_match.group(1)
        else:
            error_type = ""
        
        # Extract key phrases (words in quotes or after colons)
        phrases = re.findall(r'["\']([^"\']+)["\']', error_message)
        phrases.extend(re.findall(r':\s*([^\n]+)', error_message))
        
        # Combine
        terms = [error_type] + phrases[:3]  # Error type + top 3 phrases
        
        # Clean and join
        clean_terms = []
        for term in terms:
            words = term.lower().split()
            clean_words = [w for w in words if w not in common_words and len(w) > 3]
            if clean_words:
                clean_terms.append(" ".join(clean_words[:5]))  # Max 5 words per term
        
        return " ".join(clean_terms[:10])  # Max 10 terms
    
    def _calculate_similarity(self, error1: str, error2: str) -> float:
        """
        Calculate similarity between two error messages.
        
        Simple word overlap similarity (can be enhanced with embeddings).
        """
        # Normalize
        words1 = set(re.findall(r'\w+', error1.lower()))
        words2 = set(re.findall(r'\w+', error2.lower()))
        
        # Remove common words
        common_words = {"the", "a", "an", "is", "are", "was", "were", "error", "exception", "python"}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        similarity = intersection / union
        
        # Boost for error type matches
        error_types1 = set(re.findall(r'(\w+Error|\w+Exception)', error1))
        error_types2 = set(re.findall(r'(\w+Error|\w+Exception)', error2))
        if error_types1 & error_types2:
            similarity += 0.2  # Boost for same error type
        
        return min(1.0, similarity)
    
    def _get_stackoverflow_answer(self, answer_id: int) -> Optional[Dict]:
        """Get a Stack Overflow answer by ID."""
        try:
            url = f"https://api.stackexchange.com/2.3/answers/{answer_id}"
            params = {
                "site": "stackoverflow",
                "filter": "withbody"
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    return items[0]
        except Exception as e:
            logger.debug(f"Failed to get answer {answer_id}: {e}")
        return None
    
    def _contains_solution(self, text: str) -> bool:
        """Check if text contains a solution."""
        indicators = [
            "extend_existing", "import", "fix", "solution", "workaround",
            "try this", "here's how", "add", "change", "replace", "install"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in indicators)
    
    def _extract_solution(self, markdown: str) -> Optional[str]:
        """Extract code solution from markdown."""
        # Look for code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', markdown, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for code blocks without language
        code_blocks = re.findall(r'```\n(.*?)\n```', markdown, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Look for inline code with key terms
        key_terms = ["extend_existing", "import", "pip install", "from", "def", "class"]
        inline_code = re.findall(r'`([^`]+)`', markdown)
        for code in inline_code:
            if any(term in code.lower() for term in key_terms):
                return code
        
        return None


# Global instance
_reverse_knn_searcher: Optional[ReverseKNNSearcher] = None


def get_reverse_knn_searcher(github_token: Optional[str] = None) -> ReverseKNNSearcher:
    """Get global reverse KNN searcher instance."""
    global _reverse_knn_searcher
    if _reverse_knn_searcher is None:
        _reverse_knn_searcher = ReverseKNNSearcher(github_token=github_token)
    return _reverse_knn_searcher
