## Document Ingestion API Documentation

This document describes the text ingestion endpoints for uploading and managing documents with Qdrant vector storage.

### Overview

The ingestion API allows users to:

1. Upload and ingest text documents
2. Automatically chunk text and generate embeddings
3. Store document metadata in SQL database
4. Store vector embeddings in Qdrant vector database
5. Search for similar documents using semantic search
6. Manage documents (list, retrieve, delete)

### Architecture

```
User Input (Text/File)
    ↓
API Endpoint (/ingest/text or /ingest/file)
    ↓
TextIngestionService
    ├─→ TextChunker (splits text into chunks)
    ├─→ EmbeddingModel (generates embeddings for each chunk)
    ├─→ SQL Database (stores Document and DocumentChunk metadata)
    └─→ Qdrant Vector DB (stores chunk embeddings for semantic search)
```

### Database Schema

#### Documents Table

Stores metadata about ingested documents:

- `id`: Primary key
- `filename`: Name of the document
- `original_filename`: Original filename as uploaded
- `file_path`: Path where file is stored (optional)
- `file_size`: File size in bytes (optional)
- `content_hash`: SHA256 hash for deduplication
- `source`: Source type (upload, url, api, etc.)
- `mime_type`: MIME type of the file
- `status`: Processing status (pending, processing, completed, failed)
- `processing_error`: Error message if failed
- `total_chunks`: Number of chunks created
- `extracted_text_length`: Total text length
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

#### DocumentChunk Table

Stores individual text chunks and their embeddings:

- `id`: Primary key
- `document_id`: Foreign key to Documents
- `chunk_index`: Position of chunk in document
- `text_content`: The actual chunk text
- `token_count`: Number of tokens in chunk
- `embedding_vector_id`: ID in Qdrant
- `embedding_model`: Which model generated the embedding
- `char_start`: Starting character position
- `char_end`: Ending character position
- `metadata`: JSON metadata (page number, section, etc.)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### API Endpoints

#### 1. Ingest Text Content

**POST** `/ingest/text`

Ingest plain text content directly.

**Request Body:**

```json
{
  "text": "The text content to ingest...",
  "filename": "document_name.txt",
  "source": "upload",
  "metadata": {
    "author": "John Doe",
    "category": "research"
  }
}
```

**Parameters:**

- `text` (required): The text content to ingest
- `filename` (required): Name/identifier for the document
- `source` (optional): Source type, default "upload"
- `metadata` (optional): Additional metadata dictionary

**Response:**

```json
{
  "success": true,
  "message": "Document ingested successfully",
  "document_id": 1
}
```

**Status Codes:**

- `200`: Success
- `400`: Bad request (invalid input)
- `500`: Server error

---

#### 2. Ingest File Upload

**POST** `/ingest/file`

Upload and ingest a text file.

**Request:**

- `file` (required): Text file to upload (multipart/form-data)
- `source` (optional): Source identifier, default "upload"
- `metadata` (optional): JSON string with metadata

**Example using curl:**

```bash
curl -X POST "http://localhost:8000/ingest/file" \
  -F "file=@document.txt" \
  -F "source=upload" \
  -F 'metadata={"author":"John"}'
```

**Response:**

```json
{
  "success": true,
  "message": "Document ingested successfully",
  "document_id": 1
}
```

---

#### 3. Get Document Information

**GET** `/ingest/documents/{document_id}`

Retrieve information about a specific document and its chunks.

**Parameters:**

- `document_id`: ID of the document

**Response:**

```json
{
  "id": 1,
  "filename": "document.txt",
  "source": "upload",
  "status": "completed",
  "total_chunks": 10,
  "text_length": 5234,
  "created_at": "2025-12-12T10:30:00",
  "updated_at": "2025-12-12T10:30:05",
  "chunks": [
    {
      "id": 1,
      "index": 0,
      "text_length": 2048,
      "vector_id": "1000"
    },
    {
      "id": 2,
      "index": 1,
      "text_length": 2048,
      "vector_id": "1001"
    }
  ]
}
```

---

#### 4. List Documents

**GET** `/ingest/documents`

List all ingested documents with optional filtering.

**Query Parameters:**

- `status` (optional): Filter by status (pending, processing, completed, failed)
- `source` (optional): Filter by source (upload, url, api)
- `limit` (optional): Max results, default 100, max 1000
- `offset` (optional): Pagination offset, default 0

**Example:**

```
GET /ingest/documents?status=completed&limit=20&offset=0
```

**Response:**

```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document1.txt",
      "source": "upload",
      "status": "completed",
      "total_chunks": 10,
      "text_length": 5234,
      "created_at": "2025-12-12T10:30:00"
    },
    {
      "id": 2,
      "filename": "document2.txt",
      "source": "upload",
      "status": "completed",
      "total_chunks": 15,
      "text_length": 7654,
      "created_at": "2025-12-12T10:35:00"
    }
  ],
  "total": 2
}
```

---

#### 5. Delete Document

**DELETE** `/ingest/documents/{document_id}`

Delete a document and all its chunks from both SQL and Qdrant.

**Parameters:**

- `document_id`: ID of the document to delete

**Response:**

```json
{
  "success": true,
  "message": "Document deleted successfully",
  "document_id": 1
}
```

**Status Codes:**

- `200`: Success
- `404`: Document not found
- `500`: Server error

---

#### 6. Search Documents

**POST** `/ingest/search`

Search for similar document chunks using semantic search.

**Query Parameters:**

- `query` (required): Search query text
- `limit` (optional): Max results, default 10, max 100
- `threshold` (optional): Minimum similarity score (0-1), default 0.5

**Example:**

```
POST /ingest/search?query=machine%20learning&limit=10&threshold=0.6
```

**Response:**

```json
{
  "query": "machine learning",
  "results": [
    {
      "vector_id": 1000,
      "score": 0.92,
      "chunk_id": 1,
      "document_id": 1,
      "chunk_index": 0,
      "text": "Machine learning is a subset of artificial intelligence...",
      "metadata": {
        "document_id": 1,
        "chunk_index": 0,
        "filename": "document1.txt",
        "char_start": 0,
        "char_end": 150
      }
    },
    {
      "vector_id": 1002,
      "score": 0.87,
      "chunk_id": 3,
      "document_id": 1,
      "chunk_index": 2,
      "text": "Deep learning models learn representations through multiple layers...",
      "metadata": {
        "document_id": 1,
        "chunk_index": 2,
        "filename": "document1.txt",
        "char_start": 2048,
        "char_end": 12048
      }
    }
  ],
  "total": 2
}
```

---

#### 7. Get Service Status

**GET** `/ingest/status`

Get the status of the ingestion service and vector database.

**Response:**

```json
{
  "ingestion_service": "operational",
  "vector_db_connected": true,
  "collections": ["documents"],
  "timestamp": "2025-12-12T10:30:00"
}
```

---

### Configuration

Configure the ingestion service through environment variables in `.env`:

```bash
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Optional
QDRANT_COLLECTION_NAME=documents
QDRANT_TIMEOUT=30

# Ingestion Configuration
INGESTION_CHUNK_SIZE=2048        # Characters per chunk
INGESTION_CHUNK_OVERLAP=50      # Overlap between chunks
```

### Usage Examples

#### Example 1: Ingest Text Directly

```python
import requests

response = requests.post(
    "http://localhost:8000/ingest/text",
    json={
        "text": "This is a sample document about machine learning...",
        "filename": "ml_intro.txt",
        "source": "manual_input",
        "metadata": {"topic": "AI"}
    }
)

result = response.json()
print(f"Document ID: {result['document_id']}")
```

#### Example 2: Upload a File

```python
import requests

with open("document.txt", "rb") as f:
    files = {"file": f}
    data = {
        "source": "upload",
        "metadata": '{"category": "research"}'
    }
    response = requests.post(
        "http://localhost:8000/ingest/file",
        files=files,
        data=data
    )

result = response.json()
print(f"Document ID: {result['document_id']}")
```

#### Example 3: Search Documents

```python
import requests

response = requests.get(
    "http://localhost:8000/ingest/search",
    params={
        "query": "machine learning",
        "limit": 10,
        "threshold": 0.6
    }
)

results = response.json()
for result in results["results"]:
    print(f"Score: {result['score']}")
    print(f"Text: {result['text'][:100]}...")
```

#### Example 4: List All Documents

```python
import requests

response = requests.get(
    "http://localhost:8000/ingest/documents",
    params={
        "status": "completed",
        "limit": 50
    }
)

documents = response.json()
print(f"Total documents: {documents['total']}")
for doc in documents["documents"]:
    print(f"- {doc['filename']} ({doc['total_chunks']} chunks)")
```

### Performance Considerations

1. **Chunk Size**: Default 2048 characters balances granularity and embedding quality
2. **Embedding Generation**: Each chunk is embedded using Qwen3-4B model
3. **Deduplication**: Documents are deduplicated by SHA256 hash
4. **Batch Processing**: For large documents, consider chunking on the client side

### Error Handling

The API returns appropriate HTTP status codes and error messages:

```json
{
  "detail": "Document not found"
}
```

Common errors:

- `400`: Bad request (missing required fields)
- `404`: Resource not found
- `500`: Server error (Qdrant not running, embedding model unavailable)

### Integration with Chat API

Documents can be used with the chat API for RAG (Retrieval Augmented Generation):

1. Ingest documents using `/ingest/text` or `/ingest/file`
2. Search for relevant chunks using `/ingest/search`
3. Include search results in chat context for `/chat` endpoint
4. Model will have access to document knowledge

---

### Troubleshooting

**Qdrant not running:**

```bash
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Embedding model not available:**
Ensure the Qwen3-4B model is downloaded. It will be automatically downloaded on first use if `huggingface-hub` is installed.

**Out of memory during embedding:**
Reduce `INGESTION_CHUNK_SIZE` or process documents in smaller batches.
