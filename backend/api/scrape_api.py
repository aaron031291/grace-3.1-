import uuid
from fastapi import APIRouter

router = APIRouter(prefix="/scrape", tags=["Web Scraper API"])

jobs_db = {}

@router.post("/submit")
async def submit_job(payload: dict):
    """Submit a scraping job."""
    url = payload.get("url")
    job_id = f"JOB-{uuid.uuid4().hex[:8]}"
    jobs_db[job_id] = {
        "id": job_id,
        "url": url,
        "status": "completed",
        "markdown": f"# Scraped Content for {url}\n\nThis is mocked data.",
    }
    return {"id": job_id, "status": "processing"}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a scraping job."""
    if job_id in jobs_db:
        return {"id": job_id, "status": jobs_db[job_id]["status"], "progress": 100}
    return {"status": "not_found"}

@router.get("/results/{id}")
async def get_job_results(id: str):
    """Get the markdown results."""
    if id in jobs_db:
        return {
            "id": id,
            "markdown": jobs_db[id]["markdown"],
            "metadata": {"title": "Mock Title", "language": "en"}
        }
    return {"error": "Not found"}

@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a scraping job."""
    if job_id in jobs_db:
        jobs_db[job_id]["status"] = "cancelled"
    return {"status": "cancelled"}
