# Add Document Download Fields

**File:** `database/migrations/add_document_download_fields.py`

## Overview

Database migration: Add document download fields

This migration adds support for tracking downloaded documents in the scraping system.

New fields:
- scraping_jobs.pages_downloaded: Count of downloaded documents
- scraped_pages.file_path: Path to downloaded document file
- scraped_pages.file_size: Size of downloaded document in bytes
- scraped_pages.file_type: File extension (pdf, docx, etc.)

---
*Grace 3.1*
