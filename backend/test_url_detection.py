"""
Simple standalone test for URL validator document detection.
This test doesn't require any dependencies.
"""

import sys
from pathlib import Path

# Test the is_downloadable_document logic inline
def is_downloadable_document(url: str) -> bool:
    """Check if URL points to a downloadable document for RAG."""
    document_extensions = [
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.rtf',
        # Presentations
        '.ppt', '.pptx', '.odp',
        # Spreadsheets
        '.xls', '.xlsx', '.csv', '.ods',
        # Ebooks
        '.epub', '.mobi'
    ]
    
    url_lower = url.lower()
    # Check if URL ends with document extension (handle query parameters)
    for ext in document_extensions:
        if ext in url_lower:
            # Make sure it's actually the file extension, not just part of the path
            if url_lower.endswith(ext) or f'{ext}?' in url_lower or f'{ext}#' in url_lower:
                return True
    return False


def main():
    print("="*60)
    print("Document URL Detection Test")
    print("="*60)
    
    test_cases = [
        # Documents that should be detected
        ("https://example.com/document.pdf", True, "PDF document"),
        ("https://example.com/presentation.pptx", True, "PowerPoint presentation"),
        ("https://example.com/spreadsheet.xlsx", True, "Excel spreadsheet"),
        ("https://example.com/file.docx", True, "Word document"),
        ("https://example.com/data.csv", True, "CSV file"),
        ("https://example.com/document.pdf?download=true", True, "PDF with query params"),
        ("https://example.com/file.doc", True, "Old Word format"),
        
        # Non-documents that should NOT be detected
        ("https://example.com/image.jpg", False, "Image file"),
        ("https://example.com/video.mp4", False, "Video file"),
        ("https://example.com/page.html", False, "HTML page"),
        ("https://example.com/", False, "Homepage"),
        ("https://example.com/archive.zip", False, "Archive file"),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected, description in test_cases:
        result = is_downloadable_document(url)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} PASS: {description}")
            print(f"   URL: {url}")
        else:
            failed += 1
            print(f"{status} FAIL: {description}")
            print(f"   URL: {url}")
            print(f"   Expected: {expected}, Got: {result}")
        print()
    
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
