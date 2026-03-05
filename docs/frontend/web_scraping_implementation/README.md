# Web Scraping Feature Implementation

This directory contains all documentation related to the web scraping feature implementation in Grace.

## 📚 Documentation Files

### Core Documentation
- **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** - Original implementation plan with technical design decisions
- **[WALKTHROUGH.md](./WALKTHROUGH.md)** - Complete walkthrough of what was implemented and tested
- **[USER_GUIDE.md](./USER_GUIDE.md)** - User-facing guide for using the web scraper

### Configuration & Setup
- **[MODEL_SWITCHING_GUIDE.md](./MODEL_SWITCHING_GUIDE.md)** - How to switch between embedding models (lightweight vs production)
- **[ENV_UPDATE_INSTRUCTIONS.md](./ENV_UPDATE_INSTRUCTIONS.md)** - Environment variable configuration for embedding models
- **[SEMANTIC_FILTERING_GUIDE.md](./SEMANTIC_FILTERING_GUIDE.md)** - Guide to semantic relevance filtering

## 🎯 Feature Overview

The web scraping feature allows users to:
- Scrape web pages with configurable depth (0-5 levels)
- Filter pages by semantic relevance using embeddings
- Track scraping progress in real-time
- View filtered vs scraped pages with similarity scores
- Use lightweight models for local development

## 🔑 Key Components

### Backend
- `backend/scraping/service.py` - Core scraping logic with semantic filtering
- `backend/scraping/models.py` - Database models for jobs and pages
- `backend/api/scraping.py` - FastAPI endpoints
- `backend/embedding/embedder.py` - Embedding model wrapper

### Frontend
- `frontend/src/components/WebScraper.jsx` - React component
- `frontend/src/components/WebScraper.css` - Styling

### Database
- `scraping_jobs` table - Tracks scraping jobs
- `scraped_pages` table - Stores scraped page metadata

## 🚀 Quick Start

1. **Configure Environment** (see ENV_UPDATE_INSTRUCTIONS.md)
   ```bash
   EMBEDDING_DEFAULT=all-MiniLM-L6-v2
   EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2
   ```

2. **Download Lightweight Model** (for local dev)
   ```bash
   python backend/download_lightweight_model.py
   ```

3. **Start Services**
   ```bash
   # Backend
   cd backend && python app.py
   
   # Frontend
   cd frontend && npm run dev
   ```

4. **Use the Scraper**
   - Navigate to Documents tab
   - Enter URL and depth
   - Watch real-time progress
   - View results with similarity scores

## 📊 Features Implemented

- ✅ Web scraping with depth control (0-5)
- ✅ Semantic relevance filtering using embeddings
- ✅ Real-time progress tracking
- ✅ Filtered page tracking with similarity scores
- ✅ Lightweight model support (all-MiniLM-L6-v2)
- ✅ Production model support (Qwen-4B)
- ✅ Environment-based model switching
- ✅ Frontend visualization of filtered pages
- ✅ Loading spinner instead of misleading progress bar

## 🔧 Technical Details

### Semantic Filtering
- Uses cosine similarity between base page and candidate URLs
- Threshold: 0.3 (configurable)
- Filters out topically irrelevant pages
- Stores similarity scores for transparency

### Models
- **Lightweight**: all-MiniLM-L6-v2 (~90MB, ~500MB RAM)
- **Production**: Qwen-4B (~1.7GB, ~4GB RAM)
- Switch via `.env` configuration

### Database Schema
```sql
-- Added fields
scraping_jobs.pages_filtered INTEGER
scraped_pages.similarity_score TEXT
scraped_pages.status ('success', 'failed', 'filtered')
```

## 📝 Notes

- Semantic filtering requires embedding model to be loaded
- Falls back to keyword-based filtering if model unavailable
- Qdrant errors can be ignored if not using vector DB
- Model downloads automatically on first use (can be pre-downloaded)

## 🎓 Learning Resources

See the individual guide files for detailed information on specific topics.

---

**Created**: January 2026  
**Last Updated**: January 14, 2026
