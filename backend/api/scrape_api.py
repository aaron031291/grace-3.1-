"""
Web Scraping API — real implementation using scraping/service.py + trafilatura.

Endpoints:
  POST /scrape/submit   — start a scraping job (returns job_id)
  GET  /scrape/status/{job_id} — poll progress
  GET  /scrape/results/{job_id} — get scraped pages + markdown
  POST /scrape/cancel/{job_id} — cancel a running job
  DELETE /scrape/cancel/{job_id} — alias
"""

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from database.session import get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scrape", tags=["Web Scraper API"])


class ScrapeRequest(BaseModel):
    url: str
    depth: int = 1
    max_pages: int = 100
    same_domain_only: bool = True
    folder_path: Optional[str] = None


def _get_session():
    factory = get_session_factory()
    return factory()


def _run_scrape_job(job_id: int, url: str, depth: int, same_domain_only: bool, max_pages: int):
    """Background worker: run the scraping job, then auto-ingest results."""
    session = _get_session()
    try:
        from scraping.service import WebScrapingService
        svc = WebScrapingService(session)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                svc.start_scraping_job(
                    job_id=job_id,
                    url=url,
                    depth=depth,
                    same_domain_only=same_domain_only,
                    max_pages=max_pages,
                )
            )
        finally:
            loop.close()

        # Auto-ingest completed pages into the RAG pipeline
        _auto_ingest_scraped(session, job_id)
    except Exception as e:
        logger.exception("Scrape job %s failed: %s", job_id, e)
        from scraping.models import ScrapingJob
        from datetime import datetime, timezone
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        if job and job.status not in ("completed", "failed"):
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


def _auto_ingest_scraped(session, job_id: int):
    """Ingest every successfully scraped page into the document ingestion pipeline."""
    from scraping.models import ScrapedPage
    pages = session.query(ScrapedPage).filter_by(job_id=job_id, status="success").all()
    if not pages:
        return

    try:
        from api.ingest import get_ingestion_service
        svc = get_ingestion_service()
        if svc is None:
            logger.warning("[SCRAPE→INGEST] Ingestion service unavailable, skipping auto-ingest")
            return

        ingested = 0
        for page in pages:
            if not page.content or len(page.content.strip()) < 50:
                continue
            try:
                doc_id, msg = svc.ingest_text_fast(
                    text_content=page.content,
                    filename=page.title or page.url,
                    source=page.url,
                    upload_method="web-scrape",
                    source_type="unverified",
                    metadata={"scraped_from": page.url, "job_id": job_id},
                )
                if doc_id:
                    page.document_id = doc_id
                    ingested += 1
            except Exception as e:
                logger.debug("Auto-ingest failed for %s: %s", page.url, e)

        session.commit()
        logger.info("[SCRAPE→INGEST] Auto-ingested %d/%d pages from job %s", ingested, len(pages), job_id)
    except Exception as e:
        logger.warning("[SCRAPE→INGEST] Auto-ingest error: %s", e)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/submit")
async def submit_job(payload: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a scraping job in the background."""
    session = _get_session()
    try:
        from scraping.models import ScrapingJob
        job = ScrapingJob(
            url=payload.url,
            depth=payload.depth,
            status="pending",
            same_domain_only=1 if payload.same_domain_only else 0,
            max_pages=payload.max_pages,
            folder_path=payload.folder_path or None,
            total_pages=1,
        )
        session.add(job)
        session.commit()
        job_id = job.id
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

    background_tasks.add_task(
        _run_scrape_job,
        job_id=job_id,
        url=payload.url,
        depth=payload.depth,
        same_domain_only=payload.same_domain_only,
        max_pages=payload.max_pages,
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}")
async def get_job_status(job_id: int):
    """Get live status of a scraping job."""
    session = _get_session()
    try:
        from scraping.models import ScrapingJob
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.to_dict()
    finally:
        session.close()


@router.get("/results/{job_id}")
async def get_job_results(job_id: int):
    """Get all scraped pages for a completed job."""
    session = _get_session()
    try:
        from scraping.models import ScrapingJob, ScrapedPage
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        pages = session.query(ScrapedPage).filter_by(job_id=job_id).order_by(ScrapedPage.depth_level).all()

        return {
            "job": job.to_dict(),
            "pages": [p.to_dict() for p in pages],
            "total": len(pages),
            # Legacy field the frontend checks
            "markdown": "\n\n---\n\n".join(
                f"# {p.title or p.url}\n\n{p.content[:2000]}" for p in pages if p.status == "success" and p.content
            ),
        }
    finally:
        session.close()


@router.post("/cancel/{job_id}")
@router.delete("/cancel/{job_id}")
async def cancel_job(job_id: int):
    """Cancel a running scraping job."""
    session = _get_session()
    try:
        from scraping.models import ScrapingJob
        from datetime import datetime, timezone
        job = session.query(ScrapingJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in ("completed", "failed", "cancelled"):
            return {"status": job.status, "message": "Job already finished"}
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        session.commit()
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
