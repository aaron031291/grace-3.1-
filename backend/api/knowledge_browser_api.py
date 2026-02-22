"""
Knowledge Browser API

Exposes the organized knowledge base as a browsable file system.
The frontend can:
- Browse domain folders
- See documents per domain with Genesis keys and trust scores
- Upload documents to specific domains
- View coverage reports
- Trigger organization

Database Tables:
None (no DB tables)

Connects To:
- `librarian.knowledge_organizer`
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-browser", tags=["Knowledge Browser"])


@router.get("/domains")
async def get_domain_structure():
    """Get the full domain folder structure."""
    try:
        from librarian.knowledge_organizer import get_knowledge_organizer
        organizer = get_knowledge_organizer()
        return organizer.get_domain_structure()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coverage")
async def get_coverage_report():
    """Get coverage report — which domains are strong vs weak."""
    try:
        from librarian.knowledge_organizer import get_knowledge_organizer
        organizer = get_knowledge_organizer()
        return organizer.get_coverage_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/organize")
async def organize_all():
    """Organize all books into domain folders."""
    try:
        from librarian.knowledge_organizer import get_knowledge_organizer
        organizer = get_knowledge_organizer()
        result = organizer.organize_all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/{domain}")
async def upload_to_domain(
    domain: str,
    file: UploadFile = File(...),
    ingest: str = Form("true"),
):
    """Upload a document directly to a specific domain folder."""
    try:
        from librarian.knowledge_organizer import get_knowledge_organizer
        import os

        organizer = get_knowledge_organizer()
        domain_dir = organizer.kb_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        content = await file.read()
        dest = domain_dir / (file.filename or "uploaded_file")
        with open(str(dest), "wb") as f:
            f.write(content)

        # Also save to books/ for the auto-ingestion daemon
        books_dir = organizer.kb_path / "books"
        books_dir.mkdir(exist_ok=True)
        books_dest = books_dir / (file.filename or "uploaded_file")
        if not books_dest.exists():
            with open(str(books_dest), "wb") as f:
                f.write(content)

        # Update manifest
        organizer._update_manifest(domain, file.filename or "uploaded_file")

        result = {
            "status": "uploaded",
            "domain": domain,
            "filename": file.filename,
            "size": len(content),
            "path": str(dest),
            "will_ingest": ingest.lower() in ("true", "1", "yes"),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"[KB-BROWSER] Uploaded '{file.filename}' to domain '{domain}'")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain/{domain}")
async def get_domain_files(domain: str):
    """Get all files in a specific domain."""
    try:
        from librarian.knowledge_organizer import get_knowledge_organizer
        organizer = get_knowledge_organizer()
        structure = organizer.get_domain_structure()
        if domain in structure:
            return structure[domain]
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
