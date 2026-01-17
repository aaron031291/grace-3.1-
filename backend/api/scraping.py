from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import asyncio
import logging
from database.session import get_session
from scraping.service import WebScrapingService
from scraping.models import ScrapingJob, ScrapedPage
from scraping.url_validator import URLValidator
class ScrapeSubmitRequest(BaseModel):
    logger = logging.getLogger(__name__)
    """Request model for submitting a scraping job."""
    url: str = Field(..., description="URL to scrape")
    depth: int = Field(1, ge=0, le=5, description="Crawl depth (0-5)")
    folder_path: Optional[str] = Field(None, description="Folder path to store scraped content")
    max_pages: int = Field(100, ge=1, le=1000, description="Maximum number of pages to scrape")
    same_domain_only: bool = Field(True, description="Only scrape pages from the same domain")


class ScrapeSubmitResponse(BaseModel):
    """Response model for scrape submission."""
    job_id: int = Field(..., description="ID of the created scraping job")
    status: str = Field(..., description="Initial status of the job")
    message: str = Field(..., description="Success message")


class ScrapeStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: int
    url: str
    depth: int
    status: str
    total_pages: int
    pages_scraped: int
    pages_failed: int
    pages_filtered: int
    pages_downloaded: int
    progress_percentage: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


class ScrapedPageInfo(BaseModel):
    """Information about a scraped page."""
    url: str
    title: Optional[str]
    depth_level: int
    content_length: int
    status: str
    similarity_score: Optional[float]
    document_id: Optional[int]
    file_path: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]
    error_message: Optional[str]


class ScrapeResultsResponse(BaseModel):
    """Response model for scraping results."""
    job_id: int
    status: str
    pages: List[ScrapedPageInfo]
    summary: dict


# ==================== Helper Functions ====================

async def run_scraping_job(job_id: int, session):
    """
    Run scraping job in background.
    
    Args:
        job_id: ID of the job to run
        session: Database session
    """
    try:
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        service = WebScrapingService(session)
        await service.start_scraping_job(
            job_id=job_id,
            url=job.url,
            depth=job.depth,
            same_domain_only=bool(job.same_domain_only),
            max_pages=job.max_pages
        )
    except Exception as e:
        logger.error(f"Error running scraping job {job_id}: {str(e)}")


# ==================== API Endpoints ====================

@router.post("/submit", response_model=ScrapeSubmitResponse)
async def submit_scraping_job(
    request: ScrapeSubmitRequest,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
):
    """
    Submit a new web scraping job.
    
    The job will run in the background and scrape the specified URL
    up to the given depth, following relevant links.
    
    Args:
        request: Scraping job parameters
        background_tasks: FastAPI background tasks
        session: Database session
        
    Returns:
        Job ID and initial status
        
    Raises:
        HTTPException: If URL is invalid or job creation fails
    """
    try:
        # Validate URL
        is_valid, error_message = URLValidator.validate(request.url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Create scraping job
        job = ScrapingJob(
            url=request.url,
            depth=request.depth,
            status='pending',
            folder_path=request.folder_path or f"scraped/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            same_domain_only=1 if request.same_domain_only else 0,
            max_pages=request.max_pages,
            total_pages=1  # Start with at least the root URL
        )
        
        session.add(job)
        session.commit()
        session.refresh(job)
        
        logger.info(f"Created scraping job {job.id} for URL: {request.url}")
        
        # Start scraping in background
        background_tasks.add_task(run_scraping_job, job.id, session)
        
        return ScrapeSubmitResponse(
            job_id=job.id,
            status='pending',
            message=f"Scraping job created successfully. Job ID: {job.id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scraping job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create scraping job: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=ScrapeStatusResponse)
async def get_scraping_status(
    job_id: int,
    session=Depends(get_session)
):
    """
    Get the status of a scraping job.
    
    Args:
        job_id: ID of the scraping job
        session: Database session
        
    Returns:
        Current status and progress of the job
        
    Raises:
        HTTPException: If job not found
    """
    try:
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Scraping job {job_id} not found"
            )
        
        return ScrapeStatusResponse(
            job_id=job.id,
            url=job.url,
            depth=job.depth,
            status=job.status,
            total_pages=job.total_pages,
            pages_scraped=job.pages_scraped,
            pages_failed=job.pages_failed,
            pages_filtered=job.pages_filtered,
            pages_downloaded=job.pages_downloaded,
            progress_percentage=int((job.pages_scraped / job.total_pages * 100) if job.total_pages > 0 else 0),
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_message=job.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/results/{job_id}", response_model=ScrapeResultsResponse)
async def get_scraping_results(
    job_id: int,
    session=Depends(get_session)
):
    """
    Get the results of a completed scraping job.
    
    Args:
        job_id: ID of the scraping job
        session: Database session
        
    Returns:
        List of scraped pages and summary statistics
        
    Raises:
        HTTPException: If job not found
    """
    try:
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Scraping job {job_id} not found"
            )
        
        # Get all pages for this job
        pages = session.query(ScrapedPage).filter_by(job_id=job_id).all()
        
        page_infos = [
            ScrapedPageInfo(
                url=page.url,
                title=page.title,
                depth_level=page.depth_level,
                content_length=page.content_length,
                status=page.status,
                similarity_score=float(page.similarity_score) if page.similarity_score else None,
                document_id=page.document_id,
                file_path=page.file_path,
                file_size=page.file_size,
                file_type=page.file_type,
                error_message=page.error_message
            )
            for page in pages
        ]
        
        # Calculate summary
        total_content_size = sum(p.content_length for p in pages if p.content)
        successful_pages = [p for p in pages if p.status == 'success']
        failed_pages = [p for p in pages if p.status == 'failed']
        filtered_pages = [p for p in pages if p.status == 'filtered']
        downloaded_pages = [p for p in pages if p.status == 'downloaded']
        
        summary = {
            'total_pages': len(pages),
            'successful': len(successful_pages),
            'failed': len(failed_pages),
            'filtered': len(filtered_pages),
            'downloaded': len(downloaded_pages),
            'total_content_size': total_content_size,
            'average_content_size': total_content_size // len(successful_pages) if successful_pages else 0
        }
        
        return ScrapeResultsResponse(
            job_id=job.id,
            status=job.status,
            pages=page_infos,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job results: {str(e)}"
        )


@router.delete("/cancel/{job_id}")
async def cancel_scraping_job(
    job_id: int,
    session=Depends(get_session)
):
    """
    Cancel a running scraping job.
    
    Args:
        job_id: ID of the scraping job
        session: Database session
        
    Returns:
        Cancellation confirmation
        
    Raises:
        HTTPException: If job not found or cannot be cancelled
    """
    try:
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Scraping job {job_id} not found"
            )
        
        if job.status in ['completed', 'failed', 'cancelled']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status '{job.status}'"
            )
        
        job.status = 'cancelled'
        job.completed_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Cancelled scraping job {job_id}")
        
        return {
            'job_id': job.id,
            'status': 'cancelled',
            'message': f"Scraping job {job_id} cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )
