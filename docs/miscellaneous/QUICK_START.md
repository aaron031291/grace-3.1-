# Quick Start Guide - File Management System

## 🚀 Quick Start (5 minutes)

### Step 1: Start Qdrant (Required)

```bash
docker start qdrant
```

Expected output:

```
qdrant
```

### Step 2: Start Backend (if not running)

```bash
cd backend
python app.py
```

Expected output:

```
🚀 Grace API starting up...
✓ Database connection initialized
✓ Database tables created/verified
✓ Ollama is running with X model(s)
✓ Qdrant is running with 1 collection(s)
```

### Step 3: Access Frontend

Open browser to: `http://localhost:3000`

### Step 4: Upload a File

1. Click **Documents** tab
2. Click **Files** subtab
3. Click **Choose File** button
4. Select a `.txt`, `.md`, or `.pdf` file
5. Click **Upload**
6. ✓ File appears in directory immediately

### Step 5: Search the File

1. Click **Search** subtab
2. Type in search box: `keywords from your file`
3. Press Enter or click Search
4. ✓ Results show matching chunks with scores

---

## 🔍 Understanding the Results

### Search Results Show

- **Score**: Relevance score (0.0 to 1.0)
  - 0.9+ = Very relevant (direct match)
  - 0.7-0.9 = Highly relevant
  - 0.5-0.7 = Moderately relevant
  - 0.3-0.5 = Weakly relevant
- **Chunk**: Text snippet from the document
- **Document**: Source file name

### Example

```
Query: "machine learning"

Result 1: Score 0.95
"Machine learning is a subset of artificial intelligence..."

Result 2: Score 0.78
"Learning algorithms require large datasets and proper..."

Result 3: Score 0.52
"The field of artificial intelligence encompasses many..."
```

---

## 📂 File Structure

### Backend File Paths

```
backend/
  └─ knowledge_base/          (Your uploaded files stored here)
     ├─ file1.txt
     ├─ file2.pdf
     └─ subfolder/
        └─ file3.md
```

### Database Files

```
backend/
  ├─ data/
  │  └─ grace.db              (SQLite database)
  └─ models/embedding/
     └─ qwen_4b/              (Embedding model)
```

---

## 🛠️ Troubleshooting

### Problem: "Cannot upload files" or "Search returns no results"

**Check 1: Is Qdrant running?**

```bash
curl http://localhost:6333/health
# Should return: {"status": "ok"}
```

If error: **Start Qdrant**

```bash
docker start qdrant
docker ps  # Verify running
```

**Check 2: Is backend running?**

```bash
curl http://localhost:8000/health
# Should return status 200
```

If error: **Start backend**

```bash
cd backend
python app.py
```

**Check 3: Is frontend running?**
Open http://localhost:3000 in browser

If error: **Start frontend** (from frontend directory)

```bash
npm run dev
```

---

## 📋 Supported File Types

### Text Files (.txt)

- Plain text
- Auto-detects encoding (UTF-8, Latin-1, etc.)
- Example: requirements.txt, README.txt, notes.txt

### Markdown Files (.md)

- Markdown formatted text
- Preserves formatting for readability
- Example: README.md, GUIDE.md, documentation.md

### PDF Files (.pdf)

- Multi-page PDFs supported
- Extracts all text automatically
- Example: whitepaper.pdf, report.pdf, thesis.pdf

---

## 🔧 Common Tasks

### Upload a PDF

1. Go to Files tab
2. Select a `.pdf` file
3. Click Upload
4. System extracts text automatically
5. Ready to search in 2-3 seconds

### Search Multiple Files

1. Upload 3+ PDF files
2. Go to Search tab
3. Enter search query
4. Results show across all files with relevance scores

### Delete a File

1. Go to Files tab
2. Find file in directory
3. Click trash icon
4. File deleted from disk
5. Metadata cleaned from database

### Create a Folder

1. Go to Files tab
2. Click "New Folder" button
3. Enter folder name
4. Click Create
5. Upload files into subfolder

---

## 📊 System Requirements

### Minimum

- CPU: 4 cores
- RAM: 8 GB (more is better - embedding model uses ~7GB)
- Storage: 5 GB free
- GPU: Optional (system falls back to CPU)

### Recommended

- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 10+ GB free
- GPU: NVIDIA with CUDA (optional, faster)

---

## 🔐 Security Notes

### Data Storage

- Files stored in `backend/knowledge_base/` on disk
- Metadata in SQLite database
- Vectors in Qdrant database
- All local, no cloud uploads

### Access Control

- No authentication configured (local development)
- Suitable for local/trusted networks only
- For production, add authentication layer

---

## 🎯 What Happens When You Upload a File

```
1. File Upload
   └─> POST /files/upload
       └─> Saves file to backend/knowledge_base/

2. Text Extraction
   └─> Reads file content
       └─> TXT/MD: Direct read
       └─> PDF: Extract with pdfplumber

3. Chunking
   └─> Split text into 512-char chunks
       └─> 50-char overlap for context

4. Embedding Generation
   └─> Qwen-4B model creates 2560-dim vector
       └─> One vector per chunk

5. Storage
   └─> SQL: Document + chunk metadata
   └─> Qdrant: Vectors for semantic search

6. Ready to Search
   └─> Index ready in Qdrant
   └─> Searchable within 2-3 seconds
```

---

## 💡 Tips & Best Practices

### Best Searches

- ✓ Use 3-5 word phrases: "machine learning algorithms"
- ✓ Be specific: "neural network training methods"
- ❌ Avoid: "about" "the" single words

### File Organization

- ✓ Use clear filenames: "ML_basics.pdf"
- ✓ Organize in folders: "AI/ML/", "Papers/"
- ❌ Avoid: "doc1.txt", "file123.pdf"

### Document Chunking

- System automatically splits documents into 512-char chunks
- Overlap of 50 chars maintains context
- Each chunk can be returned as a search result

---

## 📞 Still Stuck?

Check these files for detailed information:

- `RETRIEVAL_FIXED.md` - Technical details about the fix
- `FINAL_VERIFICATION.md` - Complete system status
- `backend/docs/` - API documentation

---

**Status**: System ready for use! Upload your first file to get started! 🎉
