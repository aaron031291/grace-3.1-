"""
Document downloader service for web scraping.

This service handles downloading documents (PDFs, DOCXs, PPTs, etc.)
found during web scraping and storing them in the knowledge base.
"""

import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse, unquote
import logging
from datetime import datetime, timezone
import re
import json

logger = logging.getLogger(__name__)


class DocumentDownloader:
    """
    Service for downloading documents from URLs.
    """
    
    def __init__(self):
        """Initialize the document downloader."""
        self.timeout = 180  # seconds for document downloads (increased for large PDFs)
        self.max_size = 50 * 1024 * 1024  # 50 MB
        
    async def download_document(
        self,
        url: str,
        folder_path: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Download a document from URL and save to knowledge base.
        
        Args:
            url: URL of the document to download
            folder_path: Folder path within knowledge_base to save to
            
        Returns:
            Tuple of (success, metadata_dict)
            If successful, metadata contains:
                - file_path: Path to saved file
                - file_size: Size in bytes
                - file_type: File extension (e.g., 'pdf')
                - content_type: HTTP content type
            If failed, metadata is None
        """
        try:
            # Check if it's a Google Drive URL and convert to direct download URL
            from .url_validator import URLValidator
            
            original_url = url
            if URLValidator.is_google_drive_url(url):
                download_url = URLValidator.get_drive_download_url(url)
                if not download_url:
                    logger.error(f"Failed to extract Drive file ID from {url}")
                    return False, None
                
                logger.info(f"🔄 Converting Drive URL to direct download")
                logger.info(f"   Original: {url}")
                logger.info(f"   Download: {download_url}")
                url = download_url
            
            logger.info(f"📥 Downloading document: {url}")
            
            # Create aiohttp session with timeout
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.get(url, allow_redirects=True) as response:
                    # Check response status
                    if response.status != 200:
                        logger.error(f"Failed to download {url}: HTTP {response.status}")
                        return False, None
                    
                    # Validate content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not self._validate_content_type(content_type, url):
                        logger.warning(f"Invalid content type for {url}: {content_type}")
                        return False, None
                    
                    # Check content length
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_size:
                        logger.error(
                            f"Document too large: {int(content_length)} bytes "
                            f"(max: {self.max_size} bytes)"
                        )
                        return False, None
                    
                    # Download content in chunks to handle large files
                    content = bytearray()
                    async for chunk in response.content.iter_chunked(8192):
                        content.extend(chunk)
                        
                        # Check size during download
                        if len(content) > self.max_size:
                            logger.error(
                                f"Document exceeded size limit during download: "
                                f"{len(content)} bytes (max: {self.max_size} bytes)"
                            )
                            return False, None
                    
                    # Save document to file
                    file_path, file_type = self._save_document(
                        content=bytes(content),
                        url=url,
                        folder_path=folder_path,
                        content_type=content_type
                    )
                    
                    # Create metadata
                    metadata = {
                        'file_path': file_path,
                        'file_size': len(content),
                        'file_type': file_type,
                        'content_type': content_type,
                        'url': url,
                        'original_url': original_url,  # Store original Drive URL if converted
                        'downloaded_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Save metadata file
                    self._save_metadata(file_path, metadata)
                    
                    logger.info(
                        f"✓ Downloaded document: {file_path} "
                        f"({len(content)} bytes, type: {file_type})"
                    )
                    
                    return True, metadata
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading {url}")
            return False, None
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return False, None
    
    def _validate_content_type(self, content_type: str, url: str) -> bool:
        """
        Validate that content type is appropriate for a document.
        
        Args:
            content_type: HTTP Content-Type header
            url: URL being downloaded (for fallback validation)
            
        Returns:
            True if valid document content type
        """
        # Common document content types
        valid_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/csv',
            'text/html',  # HTML files
            'application/xhtml+xml',  # XHTML files
            'application/json',  # JSON files
            'application/rtf',
            'application/epub+zip',
            'application/x-mobipocket-ebook',
            'application/vnd.oasis.opendocument',
            'application/octet-stream',  # Generic binary, check URL extension
        ]
        
        # Check if content type matches
        for valid_type in valid_types:
            if valid_type in content_type:
                return True
        
        # Fallback: if content type is generic or missing, validate by URL extension
        if not content_type or 'octet-stream' in content_type:
            from .url_validator import URLValidator
            return URLValidator.is_downloadable_document(url)
        
        return False
    
    def _save_document(
        self,
        content: bytes,
        url: str,
        folder_path: str,
        content_type: str
    ) -> Tuple[str, str]:
        """
        Save document content to file.
        
        Args:
            content: Document content bytes
            url: Source URL
            folder_path: Folder path within knowledge_base
            content_type: HTTP content type
            
        Returns:
            Tuple of (file_path, file_type)
        """
        # Get backend directory
        backend_dir = Path(__file__).parent.parent
        knowledge_base_dir = backend_dir / "knowledge_base"
        
        # Create knowledge_base directory if it doesn't exist
        knowledge_base_dir.mkdir(exist_ok=True)
        
        # Create target directory
        target_dir = knowledge_base_dir / folder_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename, file_type = self._generate_filename(url, content_type)
        
        # Ensure unique filename
        file_path = target_dir / filename
        counter = 1
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        extension = filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        while file_path.exists():
            if extension:
                filename = f"{base_name}_{counter}.{extension}"
            else:
                filename = f"{base_name}_{counter}"
            file_path = target_dir / filename
            counter += 1
        
        # Write content to file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return str(file_path), file_type
    
    def _generate_filename(self, url: str, content_type: str) -> Tuple[str, str]:
        """
        Generate filename from URL and content type.
        
        Args:
            url: Source URL
            content_type: HTTP content type
            
        Returns:
            Tuple of (filename, file_type)
        """
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        # Try to extract filename from URL
        if path:
            # Get last part of path
            parts = path.strip('/').split('/')
            if parts and parts[-1]:
                potential_filename = parts[-1]
                
                # Check if it has a valid extension
                if '.' in potential_filename:
                    name, ext = potential_filename.rsplit('.', 1)
                    ext_lower = ext.lower()
                    
                    # Clean the name
                    clean_name = re.sub(r'[^\w\s-]', '', name)
                    clean_name = re.sub(r'[-\s]+', '_', clean_name)
                    clean_name = clean_name[:100]  # Limit length
                    
                    if clean_name:
                        return f"{clean_name}.{ext_lower}", ext_lower
        
        # Fallback: generate from content type
        extension_map = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.ms-powerpoint': 'ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'text/plain': 'txt',
            'text/csv': 'csv',
            'application/rtf': 'rtf',
            'application/epub+zip': 'epub',
        }
        
        for mime_type, ext in extension_map.items():
            if mime_type in content_type:
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                return f"document_{timestamp}.{ext}", ext
        
        # Ultimate fallback
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return f"document_{timestamp}.bin", "bin"
    
    def _save_metadata(self, file_path: str, metadata: Dict) -> None:
        """
        Save metadata to companion JSON file.
        
        Args:
            file_path: Path to the document file
            metadata: Metadata dictionary
        """
        try:
            meta_path = f"{file_path}.meta.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metadata for {file_path}: {e}")
