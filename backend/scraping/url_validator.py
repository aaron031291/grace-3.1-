"""
URL validation and sanitization for web scraping.
"""

from urllib.parse import urlparse
from typing import Tuple, Optional
import re


class URLValidator:
    """Validate and sanitize URLs for web scraping."""
    
    # Blocked URL schemes
    BLOCKED_SCHEMES = ['file', 'ftp', 'data', 'javascript', 'mailto']
    
    # Cloud storage domains that should be rejected
    DRIVE_DOMAINS = [
        'drive.google.com',
        'docs.google.com',
        'sheets.google.com',
        'slides.google.com',
        'dropbox.com',
        'onedrive.live.com',
        '1drv.ms',
        'box.com',
        'icloud.com'
    ]
    
    # Internal/localhost patterns
    INTERNAL_PATTERNS = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1',
        '10.',  # Private network
        '172.16.',  # Private network
        '192.168.'  # Private network
    ]
    
    @staticmethod
    def validate(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL and return (is_valid, error_message).
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
            If invalid, error_message contains the reason
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            
            # Check if URL has a scheme
            if not parsed.scheme:
                return False, "URL must include a scheme (http:// or https://)"
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                if parsed.scheme in URLValidator.BLOCKED_SCHEMES:
                    return False, f"Scheme '{parsed.scheme}' is not allowed for security reasons"
                return False, "URL must use http or https protocol"
            
            # Check if URL has a netloc (domain)
            if not parsed.netloc:
                return False, "URL must include a domain name"
            
            # Check for cloud storage/drive links
            for domain in URLValidator.DRIVE_DOMAINS:
                if domain in parsed.netloc.lower():
                    return False, (
                        f"Cloud storage links ({domain}) are not supported. "
                        "Please use direct website URLs instead. "
                        "If you need to scrape content from cloud storage, "
                        "download the files first and upload them directly."
                    )
            
            # Check for localhost/internal IPs
            for pattern in URLValidator.INTERNAL_PATTERNS:
                if pattern in parsed.netloc.lower():
                    return False, "Localhost and internal network URLs are not allowed"
            
            # Check for obviously malformed URLs
            if '..' in parsed.netloc or '//' in parsed.path[1:]:
                return False, "URL appears to be malformed"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    @staticmethod
    def normalize(url: str) -> str:
        """
        Normalize URL by removing fragments and adding trailing slash if needed.
        
        Args:
            url: The URL to normalize
            
        Returns:
            Normalized URL
        """
        parsed = urlparse(url)
        
        # Remove fragment
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Add query if present
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """
        Check if two URLs are from the same domain.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            True if same domain, False otherwise
        """
        try:
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            
            # Remove www. prefix for comparison
            domain1 = domain1.replace('www.', '')
            domain2 = domain2.replace('www.', '')
            
            return domain1 == domain2
        except:
            return False
    
    @staticmethod
    def is_binary_file(url: str) -> bool:
        """
        Check if URL points to a binary file based on extension.
        
        Args:
            url: The URL to check
            
        Returns:
            True if binary file, False otherwise
        """
        binary_extensions = [
            '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
            '.exe', '.dmg', '.pkg', '.deb', '.rpm',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
            '.mp3', '.wav', '.flac', '.aac', '.ogg',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.iso', '.bin', '.apk'
        ]
        
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in binary_extensions)
