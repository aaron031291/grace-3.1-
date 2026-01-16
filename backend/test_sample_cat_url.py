import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from scraping.url_validator import URLValidator

# Test the sample.cat download URL
test_url = "https://disk.sample.cat/samples/pptx/sample1.pptx"

print(f"Testing URL: {test_url}\n")

is_doc = URLValidator.is_downloadable_document(test_url)
print(f"is_downloadable_document: {is_doc}")

is_valid, error = URLValidator.validate(test_url)
print(f"validate: {is_valid}")
if error:
    print(f"  Error: {error}")

is_binary = URLValidator.is_binary_file(test_url)
print(f"is_binary_file: {is_binary}")

is_drive = URLValidator.is_google_drive_url(test_url)
print(f"is_google_drive_url: {is_drive}")

print("\n" + "="*60)
print("Expected: is_downloadable_document=True, validate=True")
print("="*60)
