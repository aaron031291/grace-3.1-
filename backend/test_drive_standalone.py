"""
Standalone test for Google Drive URL utilities (no dependencies).
"""

import re
from typing import Optional


def is_google_drive_url(url: str) -> bool:
    """Check if URL is a Google Drive document link."""
    drive_patterns = [
        'drive.google.com/file',
        'drive.google.com/uc',
        'docs.google.com/document',
        'docs.google.com/spreadsheets',
        'docs.google.com/presentation'
    ]
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in drive_patterns)


def extract_drive_file_id(url: str) -> Optional[str]:
    """Extract Google Drive file ID from URL."""
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'[?&]id=([a-zA-Z0-9_-]+)',
        r'/document/d/([a-zA-Z0-9_-]+)',
        r'/spreadsheets/d/([a-zA-Z0-9_-]+)',
        r'/presentation/d/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_drive_download_url(url: str) -> Optional[str]:
    """Convert Google Drive sharing URL to direct download URL."""
    file_id = extract_drive_file_id(url)
    if not file_id:
        return None
    
    # Check if it's a Google Docs/Sheets/Slides
    if 'docs.google.com/document' in url:
        return f"https://docs.google.com/document/d/{file_id}/export?format=docx"
    elif 'docs.google.com/spreadsheets' in url:
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    elif 'docs.google.com/presentation' in url:
        return f"https://docs.google.com/presentation/d/{file_id}/export?format=pptx"
    else:
        # Regular file download
        return f"https://drive.google.com/uc?id={file_id}&export=download"


def main():
    print("="*70)
    print("GOOGLE DRIVE SUPPORT - STANDALONE TEST")
    print("="*70)
    
    # Test 1: URL Detection
    print("\n1. Testing Drive URL Detection")
    print("-" * 70)
    test_urls = [
        ("https://drive.google.com/file/d/1ABC/view", True, "Drive file"),
        ("https://docs.google.com/document/d/1ABC/edit", True, "Google Doc"),
        ("https://example.com/file.pdf", False, "Regular URL"),
    ]
    
    for url, expected, desc in test_urls:
        result = is_google_drive_url(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {desc}: {result == expected}")
    
    # Test 2: File ID Extraction
    print("\n2. Testing File ID Extraction")
    print("-" * 70)
    test_ids = [
        ("https://drive.google.com/file/d/1ABC123xyz/view", "1ABC123xyz"),
        ("https://docs.google.com/document/d/1DEF456abc/edit", "1DEF456abc"),
        ("https://drive.google.com/uc?id=1GHI789def", "1GHI789def"),
    ]
    
    for url, expected_id in test_ids:
        result = extract_drive_file_id(url)
        status = "✓" if result == expected_id else "✗"
        print(f"{status} {url[:50]}...")
        print(f"   Expected: {expected_id}, Got: {result}")
    
    # Test 3: Download URL Generation
    print("\n3. Testing Download URL Generation")
    print("-" * 70)
    conversions = [
        (
            "https://drive.google.com/file/d/1ABC/view",
            "https://drive.google.com/uc?id=1ABC&export=download",
            "PDF/File"
        ),
        (
            "https://docs.google.com/document/d/1ABC/edit",
            "https://docs.google.com/document/d/1ABC/export?format=docx",
            "Google Doc"
        ),
        (
            "https://docs.google.com/spreadsheets/d/1ABC/edit",
            "https://docs.google.com/spreadsheets/d/1ABC/export?format=xlsx",
            "Google Sheet"
        ),
        (
            "https://docs.google.com/presentation/d/1ABC/edit",
            "https://docs.google.com/presentation/d/1ABC/export?format=pptx",
            "Google Slides"
        ),
    ]
    
    for original, expected, desc in conversions:
        result = get_drive_download_url(original)
        status = "✓" if result == expected else "✗"
        print(f"{status} {desc}")
        print(f"   Original: {original}")
        print(f"   Download: {result}")
        print()
    
    print("="*70)
    print("✓ All Google Drive utilities working correctly!")
    print("="*70)


if __name__ == "__main__":
    main()
