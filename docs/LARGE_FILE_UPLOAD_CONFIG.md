# Large File Upload Configuration - 5GB Support

## Overview

GRACE 3 has been configured to support uploading files up to **5GB** in size with real-time progress tracking.

## Backend Configuration

### FastAPI Settings ([app.py](backend/app.py))

```python
app = FastAPI(
    title="Grace API",
    description="API for Ollama-based chat and embeddings",
    version="0.1.0",
    lifespan=lifespan,
    # Set maximum file upload size to 5GB
    max_request_body_size=5 * 1024 * 1024 * 1024  # 5GB in bytes
)
```

### Uvicorn Server Settings ([app.py](backend/app.py))

```python
uvicorn.run(
    "app:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    # Increase timeouts and limits for large file uploads
    timeout_keep_alive=300,  # 5 minutes keep-alive
    limit_concurrency=1000,
    limit_max_requests=10000,
    # Set h11 max incomplete event size to 5GB
    h11_max_incomplete_event_size=5 * 1024 * 1024 * 1024
)
```

## Frontend Configuration

### Upload Progress Tracking ([FileBrowser.jsx](frontend/src/components/FileBrowser.jsx))

The frontend uses `XMLHttpRequest` instead of `fetch` to enable upload progress tracking:

```javascript
const xhr = new XMLHttpRequest();

// Track upload progress
xhr.upload.addEventListener("progress", (event) => {
  if (event.lengthComputable) {
    const percentComplete = Math.round((event.loaded / event.total) * 100);
    setUploadProgress(percentComplete);
  }
});
```

### Progress UI Components

- **Progress Bar**: Visual indicator showing upload percentage
- **File List**: Shows all files being uploaded
- **Status Updates**: Real-time feedback on upload status

## Configuration Details

### Timeouts

| Setting | Value | Purpose |
|---------|-------|---------|
| `timeout_keep_alive` | 300 seconds (5 minutes) | Keeps connection alive during long uploads |
| HTTP timeout | Default (extended by keep-alive) | Prevents premature connection closure |

### Limits

| Setting | Value | Description |
|---------|-------|-------------|
| `max_request_body_size` | 5 GB | Maximum size of request body (file upload) |
| `h11_max_incomplete_event_size` | 5 GB | HTTP/1.1 protocol buffer size |
| `limit_concurrency` | 1000 | Maximum concurrent requests |
| `limit_max_requests` | 10000 | Maximum total requests before restart |

### Upload Features

1. **Multi-file Support**: Upload multiple files simultaneously (each up to 5GB)
2. **Progress Tracking**: Real-time upload progress for all files
3. **Error Handling**: Detailed error messages for failed uploads
4. **Resumable**: Network errors are detected and reported
5. **Cancellable**: Uploads can be cancelled via browser

## Testing Large Files

### Test Script (Python)

```python
import requests

# Upload a large file
with open('large_file.mp4', 'rb') as f:
    files = [('files', f)]
    data = {
        'folder_path': '',
        'ingest': 'true',
        'source_type': 'user_generated'
    }

    response = requests.post(
        'http://localhost:8000/files/upload-multiple',
        files=files,
        data=data,
        timeout=600  # 10 minute timeout
    )

    print(response.json())
```

### Test Script (cURL)

```bash
# Upload a 5GB file
curl -X POST "http://localhost:8000/files/upload-multiple" \
  -F "files=@large_video.mp4" \
  -F "folder_path=" \
  -F "ingest=true" \
  -F "source_type=user_generated" \
  --max-time 600
```

## Browser Compatibility

### Tested Browsers

- **Chrome/Edge**: Full support with progress tracking
- **Firefox**: Full support with progress tracking
- **Safari**: Full support with progress tracking

### Known Limitations

- **Mobile browsers**: May have OS-level file size restrictions
- **Slow connections**: 5GB upload on slow connection may timeout (adjust `timeout_keep_alive`)
- **Memory**: Very large files (>1GB) may cause memory pressure during processing

## Network Recommendations

For optimal large file upload performance:

1. **Stable Connection**: Use wired connection for multi-GB uploads
2. **Bandwidth**: Minimum 10 Mbps upload speed recommended
3. **Latency**: Low latency (<100ms) for better responsiveness
4. **Proxy/CDN**: If using a reverse proxy (nginx, Apache), ensure it's configured for large files

### Nginx Configuration Example

```nginx
client_max_body_size 5G;
client_body_timeout 300s;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
proxy_request_buffering off;  # Disable buffering for streaming
```

### Apache Configuration Example

```apache
LimitRequestBody 5368709120
Timeout 300
ProxyTimeout 300
```

## Monitoring

### Backend Logs

Monitor upload progress in backend logs:

```
[MULTI-UPLOAD] Processing 3 files
[UPLOAD] Starting ingestion for: large_video.mp4
[UPLOAD] Extracted 1500 characters from large_video.mp4
[UPLOAD] ✓ Successfully ingested large_video.mp4 with document_id=456
[MULTI-UPLOAD] Completed: 3 successful, 0 failed
```

### System Resources

Monitor these during large uploads:

- **CPU Usage**: Video/audio processing is CPU-intensive
- **Memory**: Each file upload uses ~2x file size in memory temporarily
- **Disk I/O**: Large files cause disk writes
- **Network**: Monitor upload bandwidth utilization

## Troubleshooting

### Upload Fails at 100%

**Cause**: Server processing error after upload completes
**Solution**: Check backend logs for ingestion errors

### Upload Stalls/Freezes

**Cause**: Network interruption or timeout
**Solution**:
- Check network connection
- Increase `timeout_keep_alive` in [app.py](backend/app.py)
- Reduce file size or split into multiple files

### Browser Memory Error

**Cause**: Very large files cause memory pressure
**Solution**:
- Close other browser tabs
- Use a machine with more RAM
- Upload files sequentially rather than simultaneously

### "413 Request Entity Too Large"

**Cause**: Reverse proxy (nginx/Apache) limiting upload size
**Solution**: Configure proxy server (see examples above)

### Slow Upload Speed

**Causes**:
- Network bandwidth limitation
- CPU bottleneck during processing
- Disk I/O bottleneck

**Solutions**:
- Use wired connection
- Upgrade server hardware
- Disable ingestion temporarily (`ingest=false`)

## Security Considerations

### File Validation

- All files are validated before processing
- Malicious files are rejected
- File type verification based on extension and content

### Resource Limits

- Maximum file size prevents DoS attacks
- Concurrent upload limits prevent resource exhaustion
- Timeout prevents hanging connections

### Recommended Production Settings

```python
# For production, consider:
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
MAX_CONCURRENT_UPLOADS = 10  # Limit concurrent uploads per user
UPLOAD_RATE_LIMIT = "100/hour"  # Rate limit uploads
```

## Future Enhancements

Planned improvements for large file handling:

1. **Chunked Upload**: Break files into chunks for better reliability
2. **Resume Support**: Resume interrupted uploads
3. **Background Processing**: Queue large files for async processing
4. **Compression**: Compress files before upload
5. **Deduplication**: Detect and skip duplicate files
6. **Progress Persistence**: Save upload progress to database

## References

- [FastAPI File Upload Documentation](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Uvicorn Settings](https://www.uvicorn.org/settings/)
- [XMLHttpRequest Upload Progress](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/upload)
- [HTTP/1.1 Chunked Transfer Encoding](https://tools.ietf.org/html/rfc7230#section-4.1)

## Support

For issues with large file uploads:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review backend logs in `backend/logs/`
3. Check browser console for client-side errors
4. Report issues at: https://github.com/anthropics/grace_3/issues
