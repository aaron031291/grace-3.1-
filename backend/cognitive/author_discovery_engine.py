"""
Author Discovery Engine

Takes the highest-trust books in the knowledge base and automatically
discovers more works by those authors + related authors.

The logic:
1. Rank all ingested books by trust score
2. Extract author names from the top-trust books
3. Search GitHub, Google Scholar, and web for more works by those authors
4. Discover co-authors, cited works, and recommended reads
5. Generate acquisition recommendations ranked by predicted trust
6. Feed recommendations to the Oracle for tracking

This creates a virtuous cycle:
  High-trust book → Author identified → More works found →
  Ingested → KNN expands → New connections discovered → Repeat

Authors in our highest-trust books:
- Richard Bird & Jeremy Gibbons (Cambridge) — Algorithm Design
- Andrew Hunt & David Thomas — Pragmatic Programmer
- Bass, Clements & Kazman (CMU SEI) — Software Architecture
- Martin Fowler — Refactoring
- Scott Chacon — Pro Git
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

def _track_discovery(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("author_discovery", desc, **kw)
    except Exception:
        pass


@dataclass
class AuthorProfile:
    """Profile of a high-trust author."""
    name: str
    trust_score: float
    books_in_kb: List[str]
    known_works: List[Dict[str, Any]] = field(default_factory=list)
    co_authors: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    github_url: Optional[str] = None
    scholar_url: Optional[str] = None


@dataclass
class AcquisitionRecommendation:
    """A recommended resource to acquire for the knowledge base."""
    title: str
    author: str
    source_url: str
    predicted_trust: float
    reason: str
    category: str
    discovered_via: str  # which author led to this
    priority: int = 5  # 1=highest


# High-trust author database — extracted from our top books
KNOWN_AUTHORS: Dict[str, AuthorProfile] = {
    "richard_bird": AuthorProfile(
        name="Richard Bird",
        trust_score=0.95,
        books_in_kb=["Algorithm Design with Haskell"],
        known_works=[
            {"title": "Pearls of Functional Algorithm Design", "publisher": "Cambridge", "year": 2010},
            {"title": "Introduction to Functional Programming using Haskell", "publisher": "Prentice Hall", "year": 1998},
            {"title": "Algebra of Programming", "publisher": "Prentice Hall", "year": 1997},
        ],
        co_authors=["Jeremy Gibbons", "Oege de Moor", "Philip Wadler"],
        topics=["functional programming", "algorithm design", "program calculation"],
    ),
    "martin_fowler": AuthorProfile(
        name="Martin Fowler",
        trust_score=0.95,
        books_in_kb=["Refactoring"],
        known_works=[
            {"title": "Patterns of Enterprise Application Architecture", "publisher": "Addison-Wesley", "year": 2002},
            {"title": "UML Distilled", "publisher": "Addison-Wesley", "year": 2003},
            {"title": "Domain-Specific Languages", "publisher": "Addison-Wesley", "year": 2010},
            {"title": "NoSQL Distilled", "publisher": "Addison-Wesley", "year": 2012},
        ],
        co_authors=["Kent Beck", "Ralph Johnson", "Joshua Kerievsky"],
        topics=["refactoring", "enterprise patterns", "agile", "microservices"],
        github_url="https://github.com/martinfowler",
    ),
    "andrew_hunt": AuthorProfile(
        name="Andrew Hunt",
        trust_score=0.95,
        books_in_kb=["The Pragmatic Programmer"],
        known_works=[
            {"title": "Pragmatic Thinking and Learning", "publisher": "Pragmatic Bookshelf", "year": 2008},
            {"title": "Practices of an Agile Developer", "publisher": "Pragmatic Bookshelf", "year": 2006},
        ],
        co_authors=["David Thomas", "Andy Thomas"],
        topics=["software craft", "agile", "developer productivity"],
    ),
    "bass_clements_kazman": AuthorProfile(
        name="Len Bass, Paul Clements, Rick Kazman",
        trust_score=0.95,
        books_in_kb=["Software Architecture in Practice"],
        known_works=[
            {"title": "Documenting Software Architectures", "publisher": "Addison-Wesley", "year": 2010},
            {"title": "Evaluating Software Architectures", "publisher": "Addison-Wesley", "year": 2002},
            {"title": "Software Architecture in Practice 3rd Ed", "publisher": "Addison-Wesley", "year": 2012},
            {"title": "DevOps: A Software Architect's Perspective", "publisher": "Addison-Wesley", "year": 2015},
        ],
        co_authors=["Felix Bachmann", "Mark Klein", "Ipek Ozkaya"],
        topics=["software architecture", "quality attributes", "architecture evaluation", "devops"],
    ),
    "robert_c_martin": AuthorProfile(
        name="Robert C. Martin (Uncle Bob)",
        trust_score=0.90,
        books_in_kb=["Clean Code (referenced in Clean Code V2)"],
        known_works=[
            {"title": "Clean Code", "publisher": "Prentice Hall", "year": 2008},
            {"title": "Clean Architecture", "publisher": "Prentice Hall", "year": 2017},
            {"title": "The Clean Coder", "publisher": "Prentice Hall", "year": 2011},
            {"title": "Agile Software Development: Principles, Patterns, Practices", "publisher": "Prentice Hall", "year": 2002},
        ],
        co_authors=["Micah Martin"],
        topics=["clean code", "SOLID", "architecture", "agile"],
    ),
    "scott_chacon": AuthorProfile(
        name="Scott Chacon",
        trust_score=0.95,
        books_in_kb=["Pro Git"],
        co_authors=["Ben Straub"],
        topics=["git", "version control", "open source"],
        github_url="https://github.com/schacon",
    ),
    "kent_beck": AuthorProfile(
        name="Kent Beck",
        trust_score=0.90,
        books_in_kb=[],
        known_works=[
            {"title": "Test Driven Development: By Example", "publisher": "Addison-Wesley", "year": 2002},
            {"title": "Extreme Programming Explained", "publisher": "Addison-Wesley", "year": 1999},
            {"title": "Implementation Patterns", "publisher": "Addison-Wesley", "year": 2007},
            {"title": "Smalltalk Best Practice Patterns", "publisher": "Prentice Hall", "year": 1996},
        ],
        co_authors=["Martin Fowler", "Ward Cunningham", "Erich Gamma"],
        topics=["TDD", "extreme programming", "agile", "design patterns"],
    ),
    "gang_of_four": AuthorProfile(
        name="Gamma, Helm, Johnson, Vlissides (Gang of Four)",
        trust_score=0.95,
        books_in_kb=[],
        known_works=[
            {"title": "Design Patterns: Elements of Reusable Object-Oriented Software", "publisher": "Addison-Wesley", "year": 1994},
        ],
        co_authors=["Ralph Johnson", "Erich Gamma"],
        topics=["design patterns", "OOP", "creational", "structural", "behavioral"],
    ),
    "eric_evans": AuthorProfile(
        name="Eric Evans",
        trust_score=0.90,
        books_in_kb=["Referenced in DDD books"],
        known_works=[
            {"title": "Domain-Driven Design: Tackling Complexity in the Heart of Software", "publisher": "Addison-Wesley", "year": 2003},
        ],
        topics=["DDD", "bounded contexts", "ubiquitous language", "aggregates"],
    ),
}


class AuthorDiscoveryEngine:
    """
    Discovers new resources based on high-trust authors.

    Workflow:
    1. get_top_authors() — ranked by trust score
    2. get_missing_works() — works by known authors not yet in KB
    3. generate_recommendations() — prioritized acquisition list
    4. search_for_author() — web search for an author's works (needs SerpAPI)
    """

    def __init__(self):
        self.authors = dict(KNOWN_AUTHORS)

    def get_top_authors(self, min_trust: float = 0.85) -> List[AuthorProfile]:
        """Get authors ranked by trust score."""
        return sorted(
            [a for a in self.authors.values() if a.trust_score >= min_trust],
            key=lambda a: a.trust_score,
            reverse=True
        )

    def get_missing_works(self) -> List[AcquisitionRecommendation]:
        """Find works by high-trust authors that aren't in the knowledge base yet."""
        recommendations = []

        for author_key, author in self.authors.items():
            for work in author.known_works:
                title = work["title"]
                # Check if this title (or similar) is already in KB
                if not self._is_in_kb(title):
                    recommendations.append(AcquisitionRecommendation(
                        title=title,
                        author=author.name,
                        source_url=f"https://www.google.com/search?q={title.replace(' ', '+')}+{work.get('publisher', '')}",
                        predicted_trust=author.trust_score * 0.95,
                        reason=f"By {author.name} (trust: {author.trust_score:.0%}), published by {work.get('publisher', 'unknown')}",
                        category=author.topics[0] if author.topics else "general",
                        discovered_via=author_key,
                        priority=1 if author.trust_score >= 0.95 else 2,
                    ))

        # Also recommend co-author works
        for author_key, author in self.authors.items():
            for co_author in author.co_authors:
                co_key = co_author.lower().replace(" ", "_")
                if co_key in self.authors:
                    continue  # Already tracked
                recommendations.append(AcquisitionRecommendation(
                    title=f"Works by {co_author}",
                    author=co_author,
                    source_url=f"https://www.google.com/search?q={co_author.replace(' ', '+')}+books+software+engineering",
                    predicted_trust=author.trust_score * 0.8,
                    reason=f"Co-author of {author.name} (trust: {author.trust_score:.0%})",
                    category="co_author_discovery",
                    discovered_via=author_key,
                    priority=3,
                ))

        # Sort by predicted trust then priority
        recommendations.sort(key=lambda r: (-r.predicted_trust, r.priority))
        return recommendations

    def generate_search_queries(self) -> List[Dict[str, Any]]:
        """Generate search queries for discovering more resources."""
        queries = []

        for author in self.get_top_authors(min_trust=0.90):
            queries.append({
                "query": f"{author.name} books software engineering",
                "type": "author_works",
                "trust": author.trust_score,
                "author": author.name,
            })
            queries.append({
                "query": f"{author.name} github repositories",
                "type": "author_github",
                "trust": author.trust_score,
                "author": author.name,
            })
            for topic in author.topics[:2]:
                queries.append({
                    "query": f"{topic} best books recommended by {author.name}",
                    "type": "topic_expansion",
                    "trust": author.trust_score * 0.8,
                    "author": author.name,
                })

        queries.sort(key=lambda q: -q["trust"])
        return queries

    def search_for_author(self, author_name: str) -> List[Dict[str, Any]]:
        """
        Search the web for an author's works using SerpAPI.

        Requires SerpAPI key configured in settings.
        """
        try:
            from search.serpapi_service import SerpAPIService
            from settings import settings
            if not settings.SERPAPI_KEY:
                return [{"error": "SerpAPI key not configured"}]

            serp = SerpAPIService(api_key=settings.SERPAPI_KEY)
            results = serp.search(f"{author_name} books software engineering programming")
            _track_discovery(f"Searched for {author_name}", outcome="success")
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def get_report(self) -> Dict[str, Any]:
        """Get full discovery report."""
        top_authors = self.get_top_authors()
        missing = self.get_missing_works()
        queries = self.generate_search_queries()

        return {
            "top_authors": [
                {"name": a.name, "trust": a.trust_score, "books_in_kb": len(a.books_in_kb), "known_works": len(a.known_works)}
                for a in top_authors
            ],
            "missing_works": [
                {"title": r.title, "author": r.author, "predicted_trust": r.predicted_trust, "priority": r.priority}
                for r in missing[:20]
            ],
            "search_queries_ready": len(queries),
            "total_authors_tracked": len(self.authors),
            "total_missing_works": len(missing),
        }

    def _is_in_kb(self, title: str) -> bool:
        """Check if a title is already in the knowledge base."""
        import os
        kb_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge_base", "books")
        if not os.path.isdir(kb_dir):
            kb_dir = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base", "books")
        if not os.path.isdir(kb_dir):
            return False

        title_lower = title.lower()
        for f in os.listdir(kb_dir):
            f_lower = f.lower().replace("_", " ").replace("-", " ")
            # Fuzzy match — if most title words appear in filename
            title_words = set(title_lower.split())
            matches = sum(1 for w in title_words if w in f_lower)
            if matches >= len(title_words) * 0.6:
                return True
        return False


_engine: Optional[AuthorDiscoveryEngine] = None

def get_author_discovery_engine() -> AuthorDiscoveryEngine:
    global _engine
    if _engine is None:
        _engine = AuthorDiscoveryEngine()
    return _engine
