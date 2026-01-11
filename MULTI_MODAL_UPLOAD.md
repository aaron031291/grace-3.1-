# Multi-Modal File Upload Documentation

## Overview

The GRACE 3 system now supports multi-file, multi-modal uploads with extensive file type support including documents, code files, audio, video, and more.

## Supported File Types

### Text & Documents
- **Plain Text**: `.txt`, `.md`
- **Structured Data**: `.json`, `.xml`, `.csv`, `.yaml`, `.yml`, `.toml`
- **Microsoft Office**: `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`
- **PDF Documents**: `.pdf`

### Code Files
The system supports all major programming languages:
- **Web**: `.html`, `.css`, `.scss`, `.js`, `.jsx`, `.ts`, `.tsx`
- **Backend**: `.py`, `.java`, `.php`, `.rb`, `.go`, `.rs`, `.cs`
- **Systems**: `.cpp`, `.c`, `.h`, `.sh`, `.bash`
- **Other**: `.swift`, `.kt`, `.scala`, `.sql`

### Audio Files
Audio files are transcribed using speech recognition:
- `.mp3` - MPEG Audio
- `.wav` - Waveform Audio
- `.m4a` - MPEG-4 Audio
- `.flac` - Free Lossless Audio Codec
- `.ogg` - Ogg Vorbis
- `.aac` - Advanced Audio Coding

### Video Files
Video files have their audio extracted and transcribed:
- `.mp4` - MPEG-4 Video
- `.avi` - Audio Video Interleave
- `.mov` - QuickTime Movie
- `.mkv` - Matroska Video
- `.webm` - WebM Video
- `.flv` - Flash Video

## Features

### Multi-File Upload
- Select and upload multiple files simultaneously
- Progress tracking for each file
- Individual success/failure reporting
- Automatic ingestion into vector database

### Text Extraction
Each file type has optimized text extraction:
- **Documents**: Full text with formatting preservation
- **Code Files**: Source code with syntax preserved
- **Audio**: Speech-to-text transcription
- **Video**: Audio extraction + speech-to-text transcription
- **Structured Data**: Content parsing and text extraction

### Error Handling
- Files that fail to upload are reported separately
- Partial success is supported (some files succeed, others fail)
- Detailed error messages for debugging
- Files are saved even if ingestion fails

## API Endpoints

### Multi-File Upload
```
POST /files/upload-multiple
```

**Parameters:**
- `files`: List of files to upload (multipart/form-data)
- `folder_path`: Target folder path (default: root)
- `ingest`: Whether to ingest into vector DB (default: "true")
- `source_type`: Source type for reliability (default: "user_generated")

**Response:**
```json
{
  "total_files": 5,
  "successful": 4,
  "failed": 1,
  "results": [
    {
      "filename": "document.pdf",
      "success": true,
      "message": "File uploaded and ingested successfully",
      "file_path": "document.pdf",
      "document_id": 123
    },
    {
      "filename": "video.mp4",
      "success": false,
      "message": "Upload failed: Unsupported format",
      "error": "Error details here"
    }
  ]
}
```

## Installation Requirements

To use all features, install the required Python packages:

```bash
pip install -r backend/requirements.txt
```

### Additional System Requirements

For audio/video processing, you also need:

1. **FFmpeg** (required for audio/video processing):
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **Linux**: `sudo apt-get install ffmpeg`
   - **macOS**: `brew install ffmpeg`

2. **PyAudio** (required for speech recognition):
   - **Windows**: `pip install pyaudio` (may need Visual C++ build tools)
   - **Linux**: `sudo apt-get install python3-pyaudio`
   - **macOS**: `brew install portaudio && pip install pyaudio`

## Usage Examples

### Frontend (React)
```javascript
const handleFileUpload = async (files) => {
  const formData = new FormData();

  // Add multiple files
  Array.from(files).forEach((file) => {
    formData.append("files", file);
  });

  formData.append("folder_path", currentPath);
  formData.append("ingest", "true");

  const response = await fetch("http://localhost:8000/files/upload-multiple", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  console.log(`Uploaded: ${data.successful}/${data.total_files}`);
};
```

### Python (API Client)
```python
import requests

files = [
    ("files", open("document.pdf", "rb")),
    ("files", open("code.py", "rb")),
    ("files", open("audio.mp3", "rb"))
]

data = {
    "folder_path": "my_folder",
    "ingest": "true"
}

response = requests.post(
    "http://localhost:8000/files/upload-multiple",
    files=files,
    data=data
)

result = response.json()
print(f"Success: {result['successful']}, Failed: {result['failed']}")
```

## Performance Considerations

### File Size Limits
- **Maximum file size: 5GB** per file
- Multiple files can be uploaded simultaneously (up to 5GB each)
- Large video files may take significant time to process
- Audio transcription time depends on audio length
- Upload progress tracking for all file sizes

### Processing Time
- **Text files**: Instant
- **Documents (PDF, DOCX)**: < 1 second per page
- **Code files**: Instant
- **Audio**: ~1-2x real-time (1 minute audio = 1-2 minutes processing)
- **Video**: Audio extraction + transcription time

### Optimization Tips
1. Compress large video/audio files before upload
2. Use batch upload for multiple small files
3. Audio transcription uses Google's free API (rate limited)
4. Consider disabling ingestion for non-searchable files

## Troubleshooting

### Audio/Video Processing Fails
1. Ensure FFmpeg is installed and in PATH
2. Check audio file has clear speech
3. Verify internet connection (for speech recognition API)

### File Not Supported
1. Check file extension is in supported list
2. Verify file is not corrupted
3. Check file has actual content

### Upload Fails
1. Check file size limits
2. Verify folder path exists
3. Check network connection
4. Review backend logs for detailed errors

## Future Enhancements

Planned features for future releases:
- Image OCR support (extract text from images)
- Advanced video processing (scene detection, subtitle extraction)
- Local speech recognition (offline mode)
- Parallel file processing for faster uploads
- Resume interrupted uploads
- Drag-and-drop folder upload

## Security Considerations

1. **File Validation**: All files are validated before processing
2. **Sandboxed Processing**: File extraction happens in isolated processes
3. **Malware Scanning**: Consider adding antivirus scanning for production
4. **Access Control**: Implement user permissions for file access
5. **Rate Limiting**: Prevent abuse with upload rate limits

## Contributing

To add support for new file types:

1. Add file extension to `FileHandler.SUPPORTED_TYPES` in `file_handler.py`
2. Implement extraction method (e.g., `_extract_newtype()`)
3. Add case to `extract_text()` method
4. Update frontend accept attribute in `FileBrowser.jsx`
5. Add tests for new file type
6. Update this documentation

## License

Part of the GRACE 3 project. See main LICENSE file for details.
