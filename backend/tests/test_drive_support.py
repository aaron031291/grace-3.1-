"""
Test Google Drive URL detection and conversion.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from scraping.url_validator import URLValidator


def test_drive_url_detection():
    """Test Google Drive URL detection."""
    print("\n" + "="*60)
    print("Testing Google Drive URL Detection")
    print("="*60)
    
    test_cases = [
        # Google Drive file URLs
        ("https://drive.google.com/file/d/1ABC123xyz/view?usp=sharing", True),
        ("https://drive.google.com/uc?id=1ABC123xyz&export=download", True),
        
        # Google Docs/Sheets/Slides
        ("https://docs.google.com/document/d/1ABC123xyz/edit", True),
        ("https://docs.google.com/spreadsheets/d/1ABC123xyz/edit", True),
        ("https://docs.google.com/presentation/d/1ABC123xyz/edit", True),
        
        # Non-Drive URLs
        ("https://example.com/document.pdf", False),
        ("https://dropbox.com/s/abc123/file.pdf", False),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected in test_cases:
        result = URLValidator.is_google_drive_url(url)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {url[:60]}...")
        print(f"   Expected: {expected}, Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_file_id_extraction():
    """Test Google Drive file ID extraction."""
    print("\n" + "="*60)
    print("Testing File ID Extraction")
    print("="*60)
    
    test_cases = [
        ("https://drive.google.com/file/d/1ABC123xyz/view", "1ABC123xyz"),
        ("https://drive.google.com/uc?id=1ABC123xyz", "1ABC123xyz"),
        ("https://docs.google.com/document/d/1ABC123xyz/edit", "1ABC123xyz"),
        ("https://docs.google.com/spreadsheets/d/1DEF456abc/edit", "1DEF456abc"),
        ("https://docs.google.com/presentation/d/1GHI789def/edit", "1GHI789def"),
        ("https://example.com/file.pdf", None),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected_id in test_cases:
        result = URLValidator.extract_drive_file_id(url)
        status = "✓" if result == expected_id else "✗"
        
        if result == expected_id:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {url[:50]}...")
        print(f"   Expected ID: {expected_id}, Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_download_url_generation():
    """Test download URL generation."""
    print("\n" + "="*60)
    print("Testing Download URL Generation")
    print("="*60)
    
    test_cases = [
        (
            "https://drive.google.com/file/d/1ABC123xyz/view",
            "https://drive.google.com/uc?id=1ABC123xyz&export=download"
        ),
        (
            "https://docs.google.com/document/d/1ABC123xyz/edit",
            "https://docs.google.com/document/d/1ABC123xyz/export?format=docx"
        ),
        (
            "https://docs.google.com/spreadsheets/d/1ABC123xyz/edit",
            "https://docs.google.com/spreadsheets/d/1ABC123xyz/export?format=xlsx"
        ),
        (
            "https://docs.google.com/presentation/d/1ABC123xyz/edit",
            "https://docs.google.com/presentation/d/1ABC123xyz/export?format=pptx"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for original_url, expected_download_url in test_cases:
        result = URLValidator.get_drive_download_url(original_url)
        status = "✓" if result == expected_download_url else "✗"
        
        if result == expected_download_url:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {original_url[:40]}...")
        print(f"   Expected: {expected_download_url}")
        print(f"   Got:      {result}")
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_url_validation():
    """Test that Drive URLs are now allowed."""
    print("\n" + "="*60)
    print("Testing URL Validation (Drive URLs Should Be Allowed)")
    print("="*60)
    
    test_cases = [
        ("https://drive.google.com/file/d/1ABC123xyz/view", True),
        ("https://docs.google.com/document/d/1ABC123xyz/edit", True),
        ("https://dropbox.com/s/abc123/file.pdf", False),  # Still blocked
        ("https://example.com/document.pdf", True),  # Regular URL
    ]
    
    passed = 0
    failed = 0
    
    for url, should_pass in test_cases:
        is_valid, error = URLValidator.validate(url)
        status = "✓" if is_valid == should_pass else "✗"
        
        if is_valid == should_pass:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {url[:50]}...")
        print(f"   Should pass: {should_pass}, Valid: {is_valid}")
        if error:
            print(f"   Error: {error}")
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("GOOGLE DRIVE SUPPORT - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Drive URL Detection
    results.append(("Drive URL Detection", test_drive_url_detection()))
    
    # Test 2: File ID Extraction
    results.append(("File ID Extraction", test_file_id_extraction()))
    
    # Test 3: Download URL Generation
    results.append(("Download URL Generation", test_download_url_generation()))
    
    # Test 4: URL Validation
    results.append(("URL Validation", test_url_validation()))
    
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
