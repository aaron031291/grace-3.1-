"""
External sources for knowledge gap filling — software engineering focus.

Used by reverse_knn.fill_gaps_actively to pull from:
- GitHub (repos; optional GITHUB_TOKEN)
- Stack Overflow (Stack Exchange API)
- arXiv (research papers)
- Wikipedia (concepts, algorithms, standards)
- Hacker News (Algolia)
- Dev.to (articles by tag)
- PyPI (Python packages, XML-RPC)
- MDN (Mozilla Developer Network: web APIs, JS, CSS, HTML)
- Semantic Scholar (CS/SE papers; optional API key)
- npm (JavaScript/Node packages)
- IETF RFC (protocols, standards, datatracker API)
"""

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def fetch_github(topic: str, max_results: int = 3, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search GitHub repositories by topic. Optional GITHUB_TOKEN for higher rate limit.
    Returns list of { title, link, snippet, source: "github" }.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(f"{topic} in:name,description,readme")
        url = f"https://api.github.com/search/repositories?q={q}&per_page={max_results}&sort=stars"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Grace/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = req.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            if r.status_code == 403 and "rate limit" in r.text.lower():
                logger.debug("GitHub rate limit hit; set GITHUB_TOKEN for higher limit")
            return results
        data = r.json()
        for item in data.get("items", [])[:max_results]:
            title = item.get("full_name", "") or item.get("name", "")
            link = item.get("html_url", "")
            snippet = (item.get("description") or "")[:500]
            if not snippet and item.get("topics"):
                snippet = "Topics: " + ", ".join(item.get("topics", [])[:5])
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "github",
            })
    except Exception as e:
        logger.debug("GitHub fetch failed: %s", e)
    return results


def fetch_stackoverflow(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search Stack Overflow via Stack Exchange API (no key required).
    Returns list of { title, link, snippet, source: "stackoverflow" }.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={q}&site=stackoverflow&pagesize={max_results}"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for item in data.get("items", [])[:max_results]:
            title = (item.get("title") or "")[:200]
            link = item.get("link", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("body", "") or "")[:400]
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "stackoverflow",
            })
    except Exception as e:
        logger.debug("Stack Overflow fetch failed: %s", e)
    return results


def fetch_arxiv(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search arXiv for research papers (no key required).
    Returns list of { title, link, snippet, source: "arxiv" }.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"http://export.arxiv.org/api/query?search_query=all:{q}&max_results={max_results}&sortBy=relevance"
        r = req.get(url, timeout=15, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        text = r.text
        # Minimal XML parse for <entry><title>, <summary>, <id>
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:max_results]:
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            title = (title_el.text or "").strip()[:200] if title_el is not None else ""
            snippet = (summary_el.text or "").strip()[:500] if summary_el is not None else ""
            link = (id_el.text or "").strip() if id_el is not None else ""
            if title or link:
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet or title,
                    "source": "arxiv",
                })
    except Exception as e:
        logger.debug("arXiv fetch failed: %s", e)
    return results


def fetch_wikipedia(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search Wikipedia (software engineering concepts, algorithms, standards). No key required.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit={max_results}&format=json"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for item in data.get("query", {}).get("search", [])[:max_results]:
            title = item.get("title", "")
            snippet = (item.get("snippet") or "").strip()
            snippet = re.sub(r"<[^>]+>", "", snippet)
            page_id = item.get("pageid", "")
            link = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}" if title else ""
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet[:500] if snippet else title,
                "source": "wikipedia",
            })
    except Exception as e:
        logger.debug("Wikipedia fetch failed: %s", e)
    return results


def fetch_hackernews(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search Hacker News via Algolia (no key required). Good for SWE discussions and tools.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://hn.algolia.com/api/v1/search?query={q}&hitsPerPage={max_results}"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for hit in data.get("hits", [])[:max_results]:
            title = (hit.get("title") or "")[:200]
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            snippet = (hit.get("story_text") or hit.get("comment_text") or title)[:400]
            snippet = re.sub(r"<[^>]+>", "", snippet)
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "hackernews",
            })
    except Exception as e:
        logger.debug("Hacker News fetch failed: %s", e)
    return results


def fetch_devto(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch Dev.to articles by tag (software engineering). No key required for read.
    Uses first word of topic as tag; falls back to 'programming' if too short.
    """
    results = []
    try:
        import requests as req
        tag = topic.strip().split()[0] if len(topic.strip().split()) > 0 else "programming"
        tag = re.sub(r"[^a-zA-Z0-9]", "", tag).lower()[:20] or "programming"
        url = f"https://dev.to/api/articles?tag={tag}&per_page={max_results}&top=7"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0", "Accept": "application/json"})
        if r.status_code != 200:
            return results
        data = r.json()
        for item in (data if isinstance(data, list) else [])[:max_results]:
            title = (item.get("title") or "")[:200]
            link = item.get("url", "")
            snippet = (item.get("description") or item.get("body_markdown") or title)[:400]
            snippet = re.sub(r"<[^>]+>", "", snippet)
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "devto",
            })
    except Exception as e:
        logger.debug("Dev.to fetch failed: %s", e)
    return results


def fetch_pypi(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search PyPI for Python packages (XML-RPC search). No key required.
    """
    results = []
    try:
        import xmlrpc.client
        client = xmlrpc.client.ServerProxy("https://pypi.org/pypi", allow_none=True)
        # search returns list of dicts: name, summary, version, ...
        hits = client.search({"name": topic}, "or")[:max_results]
        for h in hits:
            name = h.get("name", "")
            summary = (h.get("summary") or "")[:400]
            link = f"https://pypi.org/project/{name}/" if name else ""
            results.append({
                "title": name,
                "link": link,
                "snippet": summary or name,
                "source": "pypi",
            })
    except Exception as e:
        logger.debug("PyPI fetch failed: %s", e)
    return results


def fetch_mdn(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search MDN (Mozilla Developer Network) for web APIs, JavaScript, CSS, HTML. No key required.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://developer.mozilla.org/en-US/search.json?q={q}&locale=en-US"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for doc in data.get("documents", [])[:max_results]:
            title = (doc.get("title") or "")[:200]
            snippet = (doc.get("summary") or "")[:400]
            slug = doc.get("slug", "")
            locale = doc.get("locale", "en-US")
            link = f"https://developer.mozilla.org/{locale}/docs/{slug}" if slug else ""
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "mdn",
            })
    except Exception as e:
        logger.debug("MDN fetch failed: %s", e)
    return results


def fetch_semantic_scholar(topic: str, max_results: int = 3, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar for CS/SE research papers. Optional API key for higher rate limit.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit={max_results}&fields=title,url,abstract,year"
        headers = {"User-Agent": "Grace/1.0"}
        if api_key:
            headers["x-api-key"] = api_key
        r = req.get(url, timeout=12, headers=headers)
        if r.status_code != 200:
            return results
        data = r.json()
        for item in data.get("data", [])[:max_results]:
            title = (item.get("title") or "")[:200]
            link = item.get("url", "")
            snippet = (item.get("abstract") or "")[:400]
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet or title,
                "source": "semantic_scholar",
            })
    except Exception as e:
        logger.debug("Semantic Scholar fetch failed: %s", e)
    return results


def fetch_npm(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search npm registry for JavaScript/Node packages. No key required.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        url = f"https://registry.npmjs.org/-/v1/search?text={q}&size={max_results}"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for obj in data.get("objects", [])[:max_results]:
            pkg = obj.get("package", {})
            name = pkg.get("name", "")
            summary = (pkg.get("description") or "")[:400]
            link = pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}")
            results.append({
                "title": name,
                "link": link,
                "snippet": summary or name,
                "source": "npm",
            })
    except Exception as e:
        logger.debug("npm fetch failed: %s", e)
    return results


def fetch_ietf_rfc(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search IETF datatracker for RFCs and drafts (protocols, standards). No key required.
    """
    results = []
    try:
        import requests as req
        q = urllib.parse.quote(topic)
        # Search documents by name/title
        url = f"https://datatracker.ietf.org/api/v1/doc/document/?title__icontains={q}&format=json&limit={max_results}"
        r = req.get(url, timeout=10, headers={"User-Agent": "Grace/1.0"})
        if r.status_code != 200:
            return results
        data = r.json()
        for doc in data.get("objects", data.get("results", []))[:max_results]:
            if isinstance(doc, dict):
                name = doc.get("name", "")
                title = (doc.get("title") or name)[:200]
                if not title:
                    continue
                link = f"https://datatracker.ietf.org/doc/{name}/" if name else ""
                snippet = (doc.get("abstract") or title)[:400]
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet or title,
                    "source": "ietf_rfc",
                })
    except Exception as e:
        logger.debug("IETF RFC fetch failed: %s", e)
    return results


def fetch_all_external(topic: str, max_per_source: int = 2,
                       github_token: Optional[str] = None,
                       include_github: bool = True,
                       include_stackoverflow: bool = True,
                       include_arxiv: bool = True,
                       include_wikipedia: bool = True,
                       include_hackernews: bool = True,
                       include_devto: bool = True,
                       include_pypi: bool = True,
                       include_mdn: bool = True,
                       include_semantic_scholar: bool = True,
                       include_npm: bool = True,
                       include_ietf_rfc: bool = True,
                       semantic_scholar_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch from all software-engineering sources. Returns combined list with source tag.
    """
    out: List[Dict[str, Any]] = []
    if include_github:
        out.extend(fetch_github(topic, max_results=max_per_source, token=github_token))
    if include_stackoverflow:
        out.extend(fetch_stackoverflow(topic, max_results=max_per_source))
    if include_arxiv:
        out.extend(fetch_arxiv(topic, max_results=max_per_source))
    if include_wikipedia:
        out.extend(fetch_wikipedia(topic, max_results=max_per_source))
    if include_hackernews:
        out.extend(fetch_hackernews(topic, max_results=max_per_source))
    if include_devto:
        out.extend(fetch_devto(topic, max_results=max_per_source))
    if include_pypi:
        out.extend(fetch_pypi(topic, max_results=max_per_source))
    if include_mdn:
        out.extend(fetch_mdn(topic, max_results=max_per_source))
    if include_semantic_scholar:
        out.extend(fetch_semantic_scholar(topic, max_results=max_per_source, api_key=semantic_scholar_key))
    if include_npm:
        out.extend(fetch_npm(topic, max_results=max_per_source))
    if include_ietf_rfc:
        out.extend(fetch_ietf_rfc(topic, max_results=max_per_source))
    return out
