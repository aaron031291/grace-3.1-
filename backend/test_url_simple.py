test_url = "https://disk.sample.cat/samples/pptx/sample1.pptx"

document_extensions = [
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    '.ppt', '.pptx', '.odp',
    '.xls', '.xlsx', '.csv', '.ods',
    '.epub', '.mobi'
]

url_lower = test_url.lower()

print(f"Testing: {test_url}\n")

# Check if URL contains document extension anywhere
for ext in document_extensions:
    if ext in url_lower:
        print(f"✓ Found extension: {ext}")
        print(f"  Result: is_downloadable_document = True")
        break
else:
    print("✗ No extension found")
    print("  Result: is_downloadable_document = False")

# Check download patterns
download_patterns = [
    '/download/', '/get/', '/file/', '/attachment/',
    'download?', 'file?', 'attachment?', '/api/download', '/api/file'
]

print("\nChecking download patterns:")
for pattern in download_patterns:
    if pattern in url_lower:
        print(f"✓ Matches pattern: {pattern}")
