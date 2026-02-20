"""
Web scraping service using trafilatura.

This service handles the core scraping logic including:
- Fetching web pages
- Extracting content with trafilatura
- Following links with depth control
- Filtering relevant links
- Storing results
"""

import trafilatura
from typing import List, Set, Optional, Dict
from urllib.parse import urljoin, urlparse
import asyncio
from datetime import datetime
import logging
from sqlalchemy.orm import Session
import os
from pathlib import Path
import re
import requests

from .models import ScrapingJob, ScrapedPage
from .url_validator import URLValidator
from .document_downloader import DocumentDownloader

try:
    from settings import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)
def _record_time(op, ms):
    try:
        from cognitive.timesense_governance import get_timesense_governance
        get_timesense_governance().record(op, ms, 'service')
    except Exception:
        pass


def _track_scraping(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("web_scraping", desc, **kwargs)
    except Exception:
        pass


class WebScrapingService:
    """
    Service for scraping web content with depth control.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the scraping service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.session = db_session
        self.visited_urls: Set[str] = set()
        self.timeout = 30  # seconds
        self.max_content_size = 10 * 1024 * 1024  # 10 MB (increased for modern news sites)
        self.embedding_model = None
        self.base_page_embedding = None
        
        # Try to load embedding model for semantic filtering
        try:
            from embedding.embedder import get_embedding_model
            self.embedding_model = get_embedding_model()
            logger.info("✓ Embedding model loaded for semantic relevance filtering")
        except Exception as e:
            logger.warning(f"Embedding model not available: {e}. Using keyword-based filtering only.")
        
        # Initialize document downloader
        self.document_downloader = DocumentDownloader()
        
    async def start_scraping_job(
        self,
        job_id: int,
        url: str,
        depth: int,
        same_domain_only: bool = True,
        max_pages: int = 100
    ) -> None:
        """
        Start a scraping job asynchronously.
        
        Args:
            job_id: ID of the scraping job
            url: Starting URL to scrape
            depth: Maximum depth to crawl
            same_domain_only: Whether to stay on the same domain
            max_pages: Maximum number of pages to scrape
        """
        try:
            # Update job status to running
            job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            job.status = 'running'
            job.started_at = datetime.utcnow()
            self.session.commit()
            
            # Reset visited URLs for this job
            self.visited_urls.clear()
            
            # Start scraping from the root URL
            await self._scrape_url_recursive(
                job_id=job_id,
                url=url,
                depth=depth,
                current_depth=0,
                parent_url=None,
                same_domain_only=same_domain_only,
                max_pages=max_pages,
                base_url=url
            )
            
            # Mark job as completed
            job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
            if job:
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                self.session.commit()
                
        except Exception as e:
            logger.error(f"Error in scraping job {job_id}: {str(e)}")
            job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                self.session.commit()
    
    async def _scrape_url_recursive(
        self,
        job_id: int,
        url: str,
        depth: int,
        current_depth: int,
        parent_url: Optional[str],
        same_domain_only: bool,
        max_pages: int,
        base_url: str
    ) -> None:
        """
        Recursively scrape URL and follow links up to specified depth.
        
        Args:
            job_id: ID of the scraping job
            url: URL to scrape
            depth: Maximum depth to crawl
            current_depth: Current depth level
            parent_url: URL of the parent page
            same_domain_only: Whether to stay on same domain
            max_pages: Maximum number of pages to scrape
            base_url: The original starting URL
        """
        # Check if we've reached max pages
        job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
        if job and job.pages_scraped >= max_pages:
            logger.info(f"Reached max pages limit ({max_pages}) for job {job_id}")
            return
        
        # Check if already visited
        normalized_url = URLValidator.normalize(url)
        if normalized_url in self.visited_urls:
            return
        
        self.visited_urls.add(normalized_url)
        
        # Validate URL
        is_valid, error = URLValidator.validate(url)
        if not is_valid:
            self._mark_page_failed(job_id, url, current_depth, parent_url, error)
            return
        
        # Check if this is a Google Drive URL (needs special handling)
        if URLValidator.is_google_drive_url(url):
            logger.info(f"📥 Detected Google Drive URL: {url}")
            await self._download_and_store_document(
                job_id=job_id,
                url=url,
                depth_level=current_depth,
                parent_url=parent_url
            )
            return
        
        # Check if this is a downloadable document (PDF, DOCX, etc.)
        if URLValidator.is_downloadable_document(url):
            logger.info(f"📄 Detected downloadable document: {url}")
            await self._download_and_store_document(
                job_id=job_id,
                url=url,
                depth_level=current_depth,
                parent_url=parent_url
            )
            return
        
        # Check if binary file (non-document binaries like images, videos)
        if URLValidator.is_binary_file(url):
            self._mark_page_failed(
                job_id, url, current_depth, parent_url,
                "Skipped: Binary file detected"
            )
            return
        
        # Check same domain constraint
        if same_domain_only and not URLValidator.is_same_domain(url, base_url):
            logger.info(f"Skipping {url} - different domain")
            return
        
        try:
            # Fetch content using requests with headers to bypass 403s
            logger.info(f"Scraping {url} at depth {current_depth}")
            
            downloaded = None
            try:
                # Mimic a real browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/'
                }
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    downloaded = response.text
                else:
                    logger.warning(f"Request failed with status {response.status_code} for {url}")
            except Exception as e:
                logger.warning(f"Requests fetch failed for {url}: {e}")
            
            # Fallback to trafilatura if requests failed
            if downloaded is None:
                logger.info("Falling back to trafilatura native fetch...")
                downloaded = trafilatura.fetch_url(url)
            
            # Safe check for empty content (handles potential numpy array ambiguity)
            is_empty = False
            if downloaded is None:
                is_empty = True
            elif isinstance(downloaded, str):
                is_empty = len(downloaded) == 0
            else:
                # Fallback for unexpected types
                try:
                    is_empty = len(downloaded) == 0
                except:
                    is_empty = True

            if is_empty:
                self._mark_page_failed(
                    job_id, url, current_depth, parent_url,
                    "Failed to fetch content"
                )
                return
            
            # Check content size
            try:
                if len(downloaded) > self.max_content_size:
                    self._mark_page_failed(
                        job_id, url, current_depth, parent_url,
                        f"Content too large (>{self.max_content_size} bytes)"
                    )
                    return
            except:
                pass # Ignore size check if len() fails
            
            # Extract main content
            try:
                content = trafilatura.extract(
                    downloaded,
                    include_links=False,
                    include_images=False,
                    include_tables=True,
                    output_format='txt',
                    favor_precision=True
                )
            except Exception as e:
                logger.warning(f"Content extraction failed for {url}: {e}")
                content = None
            
            if not content:
                self._mark_page_failed(
                    job_id, url, current_depth, parent_url,
                    "No content extracted"
                )
                return
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(downloaded)
            title = metadata.title if metadata else url
            
            # Store base page embedding for semantic filtering (only for root page)
            # Use 'is None' check to avoid numpy array truth value ambiguity
            if current_depth == 0 and self.embedding_model and self.base_page_embedding is None:
                try:
                    logger.info(f"🔍 Creating base page embedding (depth={current_depth})...")
                    # Create embedding from title + first 500 chars of content
                    base_text = f"{title} {content[:500]}"
                    logger.info(f"🔍 Base text length: {len(base_text)} chars")
                    self.base_page_embedding = self.embedding_model.embed_text(base_text, batch_size=1)
                    logger.info(f"✓ Created base page embedding! Shape: {self.base_page_embedding.shape}")
                except Exception as e:
                    logger.error(f"❌ Failed to create base embedding: {e}")
                    import traceback
                    traceback.print_exc()
            elif current_depth == 0:
                logger.info(f"⚠️ Skipping base embedding: model={self.embedding_model is not None}, existing={self.base_page_embedding is not None}")
            
            # Store page content
            self._store_page_success(
                job_id=job_id,
                url=url,
                depth_level=current_depth,
                parent_url=parent_url,
                title=title,
                content=content
            )
            
            # If we haven't reached max depth, extract and follow links
            if current_depth < depth:
                links = self._extract_links(downloaded, url)
                
                # Filter relevant links
                relevant_links = self._filter_relevant_links(
                    links=links,
                    base_url=url,
                    same_domain_only=same_domain_only,
                    original_url=base_url,
                    job_id=job_id,
                    current_depth=current_depth
                )
                
                # Update total pages estimate
                job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
                if job:
                    job.total_pages = max(job.total_pages, len(self.visited_urls) + len(relevant_links))
                    self.session.commit()
                
                # Scrape child pages (limit concurrency)
                for link in relevant_links[:max_pages - len(self.visited_urls)]:
                    await self._scrape_url_recursive(
                        job_id=job_id,
                        url=link,
                        depth=depth,
                        current_depth=current_depth + 1,
                        parent_url=url,
                        same_domain_only=same_domain_only,
                        max_pages=max_pages,
                        base_url=base_url
                    )
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            self._mark_page_failed(job_id, url, current_depth, parent_url, str(e))
    
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """
        Extract all links from HTML content.
        
        Args:
            html_content: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        try:
            # Use trafilatura's link extraction
            from lxml import html as lxml_html
            
            tree = lxml_html.fromstring(html_content)
            links = tree.xpath('//a/@href')
            
            # Convert to absolute URLs
            absolute_links = []
            for link in links:
                try:
                    absolute_url = urljoin(base_url, link)
                    absolute_links.append(absolute_url)
                except:
                    continue
            
            return absolute_links
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return []
    
    def _filter_relevant_links(
        self,
        links: List[str],
        base_url: str,
        same_domain_only: bool,
        original_url: str,
        job_id: int,
        current_depth: int
    ) -> List[str]:
        """
        Filter links to only include relevant ones.
        
        Args:
            links: List of URLs to filter
            base_url: Current page URL
            same_domain_only: Whether to filter by domain
            original_url: The original starting URL
            job_id: ID of the scraping job
            current_depth: Current depth level
            
        Returns:
            List of filtered URLs
        """
        filtered = []
        
        for link in links:
            # Validate URL
            is_valid, _ = URLValidator.validate(link)
            if not is_valid:
                continue
            
            # Normalize URL
            normalized = URLValidator.normalize(link)
            
            # Skip if already visited
            if normalized in self.visited_urls:
                continue
            
            # Check same domain constraint
            if same_domain_only and not URLValidator.is_same_domain(link, original_url):
                continue
            
            # Check if this is a downloadable document or Drive URL
            # These should ALWAYS be included, bypassing semantic filtering
            is_document = URLValidator.is_downloadable_document(link)
            is_drive = URLValidator.is_google_drive_url(link)
            
            if is_document or is_drive:
                logger.info(f"📥 Including document/Drive URL (bypassing filters): {link}")
                filtered.append(normalized)
                continue
            
            # Skip binary files (images, videos, etc.) - but NOT documents
            if URLValidator.is_binary_file(link):
                continue
            
            # Skip common non-content paths
            skip_patterns = [
                '/login', '/signup', '/register', '/auth',
                '/logout', '/account', '/profile', '/settings',
                '/cart', '/checkout', '/payment',
                '/admin', '/wp-admin', '/wp-login'
            ]
            
            parsed = urlparse(link)
            if any(pattern in parsed.path.lower() for pattern in skip_patterns):
                continue
            
            # Semantic relevance filtering (if embedding model available)
            # NOTE: Documents bypass this check above
            if self.embedding_model and self.base_page_embedding is not None:
                try:
                    # Quick check: extract title/text from URL for preliminary filtering
                    # We'll do a full check when we actually scrape the page
                    url_text = parsed.path.replace('/', ' ').replace('-', ' ').replace('_', ' ')
                    
                    # Skip if URL text is too short or generic
                    if len(url_text.strip()) < 3:
                        logger.debug(f"Skipping {link}: URL text too short")
                        continue
                    
                    # Create embedding for URL text
                    url_embedding = self.embedding_model.embed_text(url_text, batch_size=1)
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(self.base_page_embedding, url_embedding)
                    
                    # Filter out pages with very low similarity (threshold: 0.3)
                    # This is a loose filter - we mainly want to avoid completely unrelated pages
                    if similarity < 0.3:
                        logger.info(f"🔍 Filtered: {parsed.path} (similarity: {similarity:.2f})")
                        # Store filtered page in database
                        self._store_filtered_page(
                            job_id=job_id,
                            url=link,
                            depth_level=current_depth + 1,
                            parent_url=base_url,
                            similarity_score=similarity
                        )
                        continue
                        
                except Exception as e:
                    # If semantic filtering fails, fall back to including the link
                    logger.error(f"❌ Semantic filtering failed for {link}: {e}")
                    import traceback
                    traceback.print_exc()
            elif self.embedding_model:
                logger.debug(f"⚠️ No base embedding yet, skipping semantic filter for {link}")
            
            filtered.append(normalized)
        
        return filtered
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            import numpy as np
            
            # Flatten arrays to ensure 1D vectors
            vec1 = np.array(vec1).flatten()
            vec2 = np.array(vec2).flatten()
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure we return a Python float, not numpy scalar or array
            if hasattr(similarity, 'item'):
                return float(similarity.item())
            if hasattr(similarity, '__len__') and len(similarity) > 1:
                # Fallback: take mean if we somehow got multiple values
                return float(np.mean(similarity))
                
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.5  # Default to neutral if calculation fails
    
    def _store_page_success(
        self,
        job_id: int,
        url: str,
        depth_level: int,
        parent_url: Optional[str],
        title: str,
        content: str
    ) -> int:
        """
        Store successfully scraped page in database and save as file.
        
        Args:
            job_id: ID of the scraping job
            url: Page URL
            depth_level: Depth level of this page
            parent_url: URL of parent page
            title: Page title
            content: Extracted content
            
        Returns:
            ID of the created page record
        """
        # Get job to find folder path
        job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
        
        # Save content to file in knowledge_base
        file_path = None
        try:
            file_path = self._save_content_to_file(
                content=content,
                title=title,
                url=url,
                folder_path=job.folder_path if job else None
            )
            logger.info(f"Saved content to file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save content to file: {str(e)}")
        
        # Store in database
        page = ScrapedPage(
            job_id=job_id,
            url=url,
            depth_level=depth_level,
            parent_url=parent_url,
            title=title,
            content=content,
            content_length=len(content),
            status='success',
            scraped_at=datetime.utcnow()
        )
        
        self.session.add(page)
        
        # Update job statistics
        if job:
            job.pages_scraped += 1
            job.total_pages = max(job.total_pages, job.pages_scraped)
        
        self.session.commit()
        
        logger.info(f"Stored page: {url} ({len(content)} chars)")
        return page.id
    
    def _save_content_to_file(
        self,
        content: str,
        title: str,
        url: str,
        folder_path: Optional[str] = None
    ) -> str:
        """
        Save scraped content to a text file in knowledge_base folder.
        
        Args:
            content: The scraped content
            title: Page title
            url: Page URL
            folder_path: Optional subfolder path
            
        Returns:
            Path to the saved file
        """
        # Get backend directory
        backend_dir = Path(__file__).parent.parent
        knowledge_base_dir = backend_dir / "knowledge_base"
        
        # Create knowledge_base directory if it doesn't exist
        knowledge_base_dir.mkdir(exist_ok=True)
        
        # Create subfolder if specified
        if folder_path:
            target_dir = knowledge_base_dir / folder_path
        else:
            # Use default folder based on domain
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '').replace('.', '_')
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            target_dir = knowledge_base_dir / f"scraped_{domain}_{timestamp}"
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename from title or URL
        if title:
            # Clean title for filename
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{safe_title[:50]}.txt"
        else:
            # Use URL path as filename
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[-1]:
                filename = f"{path_parts[-1][:50]}.txt"
            else:
                filename = "index.txt"
        
        # Ensure unique filename
        file_path = target_dir / filename
        counter = 1
        while file_path.exists():
            name_without_ext = filename.rsplit('.', 1)[0]
            file_path = target_dir / f"{name_without_ext}_{counter}.txt"
            counter += 1
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write metadata header
            f.write(f"Source: {url}\n")
            f.write(f"Title: {title}\n")
            f.write(f"Scraped: {datetime.utcnow().isoformat()}\n")
            f.write(f"{'-' * 80}\n\n")
            # Write content
            f.write(content)
        
        return str(file_path)
    
    async def _download_and_store_document(
        self,
        job_id: int,
        url: str,
        depth_level: int,
        parent_url: Optional[str]
    ) -> None:
        """
        Download a document and store it in the knowledge base.
        
        Args:
            job_id: ID of the scraping job
            url: Document URL
            depth_level: Depth level of this document
            parent_url: URL of parent page
        """
        try:
            # Get job to find folder path
            job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Download the document
            success, metadata = await self.document_downloader.download_document(
                url=url,
                folder_path=job.folder_path
            )
            
            if success and metadata:
                # Store in database with 'downloaded' status
                page = ScrapedPage(
                    job_id=job_id,
                    url=url,
                    depth_level=depth_level,
                    parent_url=parent_url,
                    title=metadata.get('file_type', 'document').upper(),
                    status='downloaded',
                    file_path=metadata['file_path'],
                    file_size=metadata['file_size'],
                    file_type=metadata['file_type'],
                    scraped_at=datetime.utcnow()
                )
                
                self.session.add(page)
                
                # Update job statistics
                job.pages_downloaded += 1
                job.total_pages = max(job.total_pages, job.pages_scraped + job.pages_downloaded)
                
                self.session.commit()
                
                logger.info(
                    f"✓ Stored document: {url} -> {metadata['file_path']} "
                    f"({metadata['file_size']} bytes)"
                )
            else:
                # Mark as failed if download unsuccessful
                self._mark_page_failed(
                    job_id=job_id,
                    url=url,
                    depth_level=depth_level,
                    parent_url=parent_url,
                    error_message="Failed to download document"
                )
                
        except Exception as e:
            logger.error(f"Error downloading document {url}: {str(e)}")
            self._mark_page_failed(
                job_id=job_id,
                url=url,
                depth_level=depth_level,
                parent_url=parent_url,
                error_message=f"Document download error: {str(e)}"
            )
    
    def _store_filtered_page(
        self,
        job_id: int,
        url: str,
        depth_level: int,
        parent_url: Optional[str],
        similarity_score: float
    ) -> None:
        """
        Store a page that was filtered out by semantic similarity.
        
        Args:
            job_id: ID of the scraping job
            url: Page URL
            depth_level: Depth level of this page
            parent_url: URL of parent page
            similarity_score: Semantic similarity score
        """
        page = ScrapedPage(
            job_id=job_id,
            url=url,
            depth_level=depth_level,
            parent_url=parent_url,
            status='filtered',
            similarity_score=f"{similarity_score:.3f}",
            scraped_at=datetime.utcnow()
        )
        
        self.session.add(page)
        
        # Update job statistics
        job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
        if job:
            job.pages_filtered += 1
        
        self.session.commit()
    
    def _mark_page_failed(
        self,
        job_id: int,
        url: str,
        depth_level: int,
        parent_url: Optional[str],
        error_message: str
    ) -> None:
        """
        Mark a page as failed in database.
        
        Args:
            job_id: ID of the scraping job
            url: Page URL
            depth_level: Depth level of this page
            parent_url: URL of parent page
            error_message: Error message
        """
        page = ScrapedPage(
            job_id=job_id,
            url=url,
            depth_level=depth_level,
            parent_url=parent_url,
            status='failed',
            error_message=error_message,
            scraped_at=datetime.utcnow()
        )
        
        self.session.add(page)
        
        # Update job statistics
        job = self.session.query(ScrapingJob).filter_by(id=job_id).first()
        if job:
            job.pages_failed += 1
            job.total_pages = max(job.total_pages, job.pages_scraped + job.pages_failed)
        
        self.session.commit()
        
        logger.warning(f"Failed to scrape {url}: {error_message}")
