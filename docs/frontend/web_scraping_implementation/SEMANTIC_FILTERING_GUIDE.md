# Semantic Relevance Filtering - Implementation Summary

## What Was Added

Added intelligent semantic filtering to the web scraper that only scrapes pages topically related to the original page.

## How It Works

### 1. Base Page Embedding
When scraping the first page (depth 0):
- Extracts title + first 500 characters of content
- Creates an embedding vector using the embedding model
- Stores this as the "base page embedding" for comparison

### 2. Link Filtering
For each discovered link:
- Extracts text from the URL path (e.g., `/blog/machine-learning` → "blog machine learning")
- Creates an embedding for the URL text
- Calculates cosine similarity with base page embedding
- **Filters out links with similarity < 0.3** (very unrelated topics)

### 3. Graceful Fallback
- If embedding model is not loaded → uses basic keyword filtering only
- If semantic filtering fails → includes the link anyway (fail-open)
- Logs warnings when model unavailable

## Configuration

### Enable Semantic Filtering

1. **Download lightweight model:**
   ```bash
   cd backend
   ./venv/bin/python download_lightweight_model.py
   ```

2. **Update `.env` file:**
   ```bash
   SKIP_EMBEDDING_LOAD=false
   EMBEDDING_DEFAULT=all-MiniLM-L6-v2
   EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2
   EMBEDDING_DEVICE=cpu
   ```

3. **Restart backend**

### Disable Semantic Filtering

Set in `.env`:
```bash
SKIP_EMBEDDING_LOAD=true
```

## Model Options

| Model | Size | RAM | Similarity Quality |
|-------|------|-----|-------------------|
| **all-MiniLM-L6-v2** (laptop) | 90 MB | 500 MB | Good |
| **Qwen-4B** (production) | 8 GB | 10 GB | Excellent |

## Example Behavior

### Without Semantic Filtering
Starting URL: `https://docs.python.org/tutorial/`

Scraped pages might include:
- ✅ `/tutorial/introduction.html` (relevant)
- ✅ `/tutorial/controlflow.html` (relevant)
- ❌ `/download.html` (not relevant)
- ❌ `/about/legal.html` (not relevant)
- ❌ `/community/merchandise.html` (not relevant)

### With Semantic Filtering
Starting URL: `https://docs.python.org/tutorial/`

Scraped pages:
- ✅ `/tutorial/introduction.html` (similarity: 0.85)
- ✅ `/tutorial/controlflow.html` (similarity: 0.78)
- ❌ `/download.html` (similarity: 0.15 - filtered)
- ❌ `/about/legal.html` (similarity: 0.10 - filtered)
- ❌ `/community/merchandise.html` (similarity: 0.05 - filtered)

## Similarity Threshold

Current threshold: **0.3** (loose filtering)

- **0.0 - 0.3**: Very unrelated → Filtered out
- **0.3 - 0.6**: Somewhat related → Included
- **0.6 - 1.0**: Highly related → Included

You can adjust this in `scraping/service.py` line ~378:
```python
if similarity < 0.3:  # Change this threshold
```

## Benefits

1. **Focused Scraping**: Only scrapes pages about the same topic
2. **Saves Time**: Fewer irrelevant pages = faster completion
3. **Better Quality**: Knowledge base contains only relevant content
4. **Saves Storage**: Less disk space used for scraped content

## Limitations

1. **URL-Based**: Only checks URL text, not full page content (for speed)
2. **Threshold Tuning**: May need adjustment for different use cases
3. **Model Required**: Needs embedding model loaded (uses RAM)

## Code Changes

**Modified Files:**
- `backend/scraping/service.py` - Added semantic filtering logic

**New Files:**
- `backend/download_lightweight_model.py` - Model download script
- `backend/MODEL_SWITCHING_GUIDE.md` - Model switching instructions
- `backend/ENV_UPDATE_INSTRUCTIONS.md` - .env update guide

**No Breaking Changes**: Works with or without embedding model loaded!
