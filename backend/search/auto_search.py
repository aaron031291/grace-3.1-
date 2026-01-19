"""
Auto-search orchestrator service.

Coordinates the workflow of searching Google via SerpAPI and scraping results
when no documents are found in the vector database.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .serpapi_service import SerpAPIService
from scraping.service import WebScrapingService
from database.session import SessionLocal
from scraping.models import ScrapingJob

logger = logging.getLogger(__name__)


class AutoSearchService:
    """Service for orchestrating auto-search and scrape workflow."""
    
    def __init__(self, serpapi_key: str):
        """
        Initialize auto-search service.
        
        Args:
            serpapi_key: SerpAPI API key
        """
        self.serpapi = SerpAPIService(serpapi_key)
    
    async def search_and_scrape(
        self,
        query: str,
        max_urls: int = 3,
        location: str = "United States",
        folder_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search Google and scrape top results.
        
        Workflow:
        1. Search Google using SerpAPI
        2. Extract top N URLs
        3. Create scraping jobs for each URL
        4. Return job IDs and URLs
        
        Args:
            query: Search query
            max_urls: Maximum number of URLs to scrape (default: 3)
            location: Geographic location for search
            
        Returns:
            Dictionary with:
            {
                "success": bool,
                "query": str,
                "urls": List[str],
                "job_ids": List[int],
                "message": str
            }
        """
        try:
            logger.info(f"[AUTO-SEARCH] Starting auto-search for query: {query}")
            
            # Step 1: Search Google via SerpAPI
            search_results = self.serpapi.search(
                query=query,
                num_results=max_urls,
                location=location
            )
            
            if not search_results:
                logger.warning(f"[AUTO-SEARCH] No search results found for: {query}")
                return {
                    "success": False,
                    "query": query,
                    "urls": [],
                    "job_ids": [],
                    "message": "No search results found"
                }
            
            # Step 2: Extract URLs
            urls = [result["link"] for result in search_results if result.get("link")]
            
            if not urls:
                logger.warning(f"[AUTO-SEARCH] No valid URLs extracted from search results")
                return {
                    "success": False,
                    "query": query,
                    "urls": [],
                    "job_ids": [],
                    "message": "No valid URLs found in search results"
                }
            
            logger.info(f"[AUTO-SEARCH] Found {len(urls)} URLs to scrape")
            
            # Determine save directory based on folder_path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if folder_path:
                base_save_dir = f"{folder_path}/auto_search/{timestamp}"
            else:
                base_save_dir = f"auto_search/{timestamp}"
            
            # Step 3: Create scraping jobs
            job_ids = []
            db = SessionLocal()
            
            try:
                for idx, url in enumerate(urls):
                    # Create scraping job
                    job = ScrapingJob(
                        url=url,
                        depth=0,  # Only scrape the main page
                        status="pending",
                        created_at=datetime.now(),
                        folder_path=base_save_dir  # Use the determined save directory
                    )
                    db.add(job)
                    db.flush()  # Get job ID
                    
                    job_ids.append(job.id)
                    logger.info(f"[AUTO-SEARCH] Created scraping job {job.id} for: {url}")
                
                db.commit()
                
                # Step 4: Start scraping jobs
                scraping_service = WebScrapingService(db)
                
                for job_id, url in zip(job_ids, urls):
                    try:
                        # Start scraping in background (async)
                        await scraping_service.start_scraping_job(
                            job_id=job_id,
                            url=url,
                            depth=0,  # Only main page
                            same_domain_only=False,
                            max_pages=1
                        )
                        logger.info(f"[AUTO-SEARCH] Started scraping job {job_id}")
                    except Exception as e:
                        logger.error(f"[AUTO-SEARCH] Failed to start job {job_id}: {e}")
                
                logger.info(f"[AUTO-SEARCH] [OK] Successfully created {len(job_ids)} scraping jobs")
                
                return {
                    "success": True,
                    "query": query,
                    "urls": urls,
                    "job_ids": job_ids,
                    "search_results": search_results,
                    "message": f"Started scraping {len(urls)} websites"
                }
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"[AUTO-SEARCH] Error in search_and_scrape: {e}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "urls": [],
                "job_ids": [],
                "message": f"Error: {str(e)}"
            }
    
    def get_scraping_status(self, job_ids: List[int]) -> Dict[str, Any]:
        """
        Get status of scraping jobs.
        
        Args:
            job_ids: List of job IDs to check
            
        Returns:
            Dictionary with job statuses
        """
        try:
            db = SessionLocal()
            try:
                jobs = db.query(ScrapingJob).filter(
                    ScrapingJob.id.in_(job_ids)
                ).all()
                
                statuses = []
                for job in jobs:
                    statuses.append({
                        "job_id": job.id,
                        "url": job.url,
                        "status": job.status,
                        "pages_scraped": job.pages_scraped or 0,
                        "pages_failed": job.pages_failed or 0
                    })
                
                # Determine overall status
                all_completed = all(j.status == "completed" for j in jobs)
                any_failed = any(j.status == "failed" for j in jobs)
                any_running = any(j.status in ["pending", "running"] for j in jobs)
                
                overall_status = "completed" if all_completed else \
                                "failed" if any_failed and not any_running else \
                                "running"
                
                return {
                    "overall_status": overall_status,
                    "jobs": statuses,
                    "total_jobs": len(jobs),
                    "completed": sum(1 for j in jobs if j.status == "completed"),
                    "failed": sum(1 for j in jobs if j.status == "failed"),
                    "running": sum(1 for j in jobs if j.status in ["pending", "running"])
                }
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"[AUTO-SEARCH] Error getting scraping status: {e}")
            return {
                "overall_status": "error",
                "jobs": [],
                "error": str(e)
            }
