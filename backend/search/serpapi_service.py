"""
SerpAPI service for Google Search integration.

Provides interface to SerpAPI for searching Google and extracting organic results.
"""

import requests
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class SerpAPIService:
    """Service for interacting with SerpAPI Google Search."""
    
    def __init__(self, api_key: str):
        """
        Initialize SerpAPI service.
        
        Args:
            api_key: SerpAPI API key
        """
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    
    def search(
        self,
        query: str,
        num_results: int = 3,
        location: Optional[str] = None,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Search Google using SerpAPI and return organic results.
        
        Args:
            query: Search query
            num_results: Maximum number of results to return
            location: Geographic location for search (e.g., "United States")
            language: Language code (default: "en")
            
        Returns:
            List of search results with title, link, snippet
            Example: [
                {
                    "title": "Python Tutorial",
                    "link": "https://example.com/python",
                    "snippet": "Learn Python programming...",
                    "position": 1
                }
            ]
        """
        try:
            # Build request parameters
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "hl": language,
                "engine": "google"
            }
            
            if location:
                params["location"] = location
            
            logger.info(f"[SERPAPI] Searching Google for: {query}")
            logger.debug(f"[SERPAPI] Parameters: num={num_results}, location={location}")
            
            # Make API request
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"[SERPAPI] API error: {response.status_code} - {response.text}")
                return []
            
            # Parse response
            data = response.json()
            
            # Check for API errors in response
            if "error" in data:
                logger.error(f"[SERPAPI] API returned error: {data['error']}")
                return []
            
            # Extract organic results
            organic_results = data.get("organic_results", [])
            
            if not organic_results:
                logger.warning(f"[SERPAPI] No organic results found for query: {query}")
                return []
            
            # Format results
            formatted_results = []
            for idx, result in enumerate(organic_results[:num_results]):
                formatted_results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", idx + 1),
                    "displayed_link": result.get("displayed_link", ""),
                })
            
            logger.info(f"[SERPAPI] [OK] Found {len(formatted_results)} results")
            for idx, res in enumerate(formatted_results, 1):
                logger.info(f"[SERPAPI]   {idx}. {res['title'][:60]}... - {res['link']}")

            # Register each result in FlashCache for future fast lookup
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                for res in formatted_results:
                    if res.get("link"):
                        kw = fc.extract_keywords(
                            f"{query} {res.get('title', '')} {res.get('snippet', '')}"
                        )
                        fc.register(
                            source_uri=res["link"],
                            source_type="search",
                            source_name=res.get("title", "")[:100],
                            keywords=kw,
                            summary=res.get("snippet", ""),
                            trust_score=0.5,
                            ttl_hours=48,
                            metadata={"search_query": query, "position": res.get("position")},
                        )
            except Exception:
                pass

            return formatted_results
        
        except requests.exceptions.Timeout:
            logger.error("[SERPAPI] Request timed out")
            return []
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[SERPAPI] Request error: {e}")
            return []
        
        except Exception as e:
            logger.error(f"[SERPAPI] Unexpected error: {e}", exc_info=True)
            return []
    
    def test_connection(self) -> bool:
        """
        Test SerpAPI connection with a simple query.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            results = self.search("test", num_results=1)
            return len(results) > 0
        except Exception as e:
            logger.error(f"[SERPAPI] Connection test failed: {e}")
            return False
