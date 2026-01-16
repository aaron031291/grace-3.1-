"""
Test script for document download feature.

This script tests the new document download functionality by:
1. Testing URL detection for downloadable documents
2. Verifying database schema updates
3. Testing the document downloader service
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from scraping.url_validator import URLValidator
from scraping.document_downloader import DocumentDownloader
import sqlite3


def test_url_validator():
    """Test URL validator for document detection."""
    print("\n" + "="*60)
    print("Testing URL Validator - Document Detection")
    print("="*60)
    
    test_cases = [
        # Documents that should be detected
        ("https://example.com/document.pdf", True),
        ("https://example.com/presentation.pptx", True),
        ("https://example.com/spreadsheet.xlsx", True),
        ("https://example.com/file.docx", True),
        ("https://example.com/data.csv", True),
        ("https://example.com/document.pdf?download=true", True),
        
        # Non-documents that should NOT be detected
        ("https://example.com/image.jpg", False),
        ("https://example.com/video.mp4", False),
        ("https://example.com/page.html", False),
        ("https://example.com/", False),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected in test_cases:
        result = URLValidator.is_downloadable_document(url)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {url}")
        print(f"   Expected: {expected}, Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_database_schema():
    """Test that database schema has been updated."""
    print("\n" + "="*60)
    print("Testing Database Schema Updates")
    print("="*60)
    
    db_path = backend_dir / "data" / "grace.db"
    
    if not db_path.exists():
        print("✗ Database not found")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check scraping_jobs table
        cursor.execute("PRAGMA table_info(scraping_jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'pages_downloaded' in columns:
            print("✓ scraping_jobs.pages_downloaded exists")
        else:
            print("✗ scraping_jobs.pages_downloaded missing")
            return False
        
        # Check scraped_pages table
        cursor.execute("PRAGMA table_info(scraped_pages)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_fields = ['file_path', 'file_size', 'file_type']
        for field in required_fields:
            if field in columns:
                print(f"✓ scraped_pages.{field} exists")
            else:
                print(f"✗ scraped_pages.{field} missing")
                return False
        
        conn.close()
        print("\n✓ All database schema updates verified")
        return True
        
    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False


async def test_document_downloader():
    """Test document downloader with a small test file."""
    print("\n" + "="*60)
    print("Testing Document Downloader")
    print("="*60)
    
    downloader = DocumentDownloader()
    
    # Test with a small PDF (using a public test PDF)
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    test_folder = "test_downloads"
    
    print(f"Testing download from: {test_url}")
    print("(This may take a few seconds...)")
    
    try:
        success, metadata = await downloader.download_document(
            url=test_url,
            folder_path=test_folder
        )
        
        if success and metadata:
            print(f"✓ Download successful!")
            print(f"   File path: {metadata['file_path']}")
            print(f"   File size: {metadata['file_size']} bytes")
            print(f"   File type: {metadata['file_type']}")
            
            # Clean up test file
            import os
            if os.path.exists(metadata['file_path']):
                os.remove(metadata['file_path'])
                print(f"✓ Cleaned up test file")
            
            # Clean up metadata file
            meta_file = f"{metadata['file_path']}.meta.json"
            if os.path.exists(meta_file):
                os.remove(meta_file)
            
            # Remove test folder if empty
            folder_path = Path(metadata['file_path']).parent
            if folder_path.exists() and not any(folder_path.iterdir()):
                folder_path.rmdir()
                print(f"✓ Cleaned up test folder")
            
            return True
        else:
            print(f"✗ Download failed")
            return False
            
    except Exception as e:
        print(f"✗ Error during download test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DOCUMENT DOWNLOAD FEATURE - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: URL Validator
    results.append(("URL Validator", test_url_validator()))
    
    # Test 2: Database Schema
    results.append(("Database Schema", test_database_schema()))
    
    # Test 3: Document Downloader (async)
    print("\nRunning async test...")
    downloader_result = asyncio.run(test_document_downloader())
    results.append(("Document Downloader", downloader_result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
